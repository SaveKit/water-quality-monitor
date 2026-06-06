import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

def compute_cumulative_co2(df, interval_seconds):
    """
    Cumulative CO2 = Σ CO2(t) × Δt (พื้นที่ใต้กราฟสะสม มีหน่วยเป็น ppm·s)
    ใช้เป็นหลักในการคำนวณ Yield Coefficient (Y) และ FDEI
    """
    df = df.copy()
    # หาค่าผลรวมสะสมคูณด้วยระยะเวลาช่วง sampling (วินาที)
    df['co2_cumulative'] = df['co2'].cumsum() * interval_seconds
    return df

def compute_yield_coefficient(df, fog_day0, fog_day7):
    """
    Y = Cumulative CO2 (รวม 7 วัน) / ΔFOG
    หน่วย: (ppm·s) ต่อ (mg/L)
    คำนวณ Calibrate 1 ครั้งต่อ 1 รอบการทดลอง เพื่อหาประสิทธิภาพของ Bacillus ในรอบนั้นๆ
    """
    delta_fog = fog_day0 - fog_day7
    co2_cum_total = df['co2_cumulative'].iloc[-1]
    Y = co2_cum_total / delta_fog
    print(f"\n[Features Calibration]")
    print(f"  ΔFOG (Day0→Day7) : {delta_fog:.3f} mg/L")
    print(f"  Cumulative CO2   : {co2_cum_total:.2f} ppm·s")
    print(f"  Yield Coeff Y    : {Y:.4f} (ppm·s per mg/L)")
    return Y

def compute_fdei(df, fog_day0, Y):
    """
    FOG_estimated(t) = FOG_Day0 - (Cumulative_CO2(t) / Y)
    FDEI(t) = (FOG_Day0 - FOG_estimated(t)) / FOG_Day0 × 100%
    จะได้ค่า FDEI แบบต่อเนื่องทุกๆ แถว (0% - 100%)
    """
    df = df.copy()
    fog_est = fog_day0 - (df['co2_cumulative'] / Y)
    fog_est = np.clip(fog_est, 0, fog_day0)
    df['fdei'] = ((fog_day0 - fog_est) / fog_day0 * 100).clip(0, 100)
    print(f"[Features FDEI] Range: {df['fdei'].min():.2f}% → {df['fdei'].max():.2f}%")
    return df

def validate_fdei_against_lab(fdei_series, df, fog_lab, fog_day0):
    """
    ตรวจทานค่า FDEI ที่ได้จากโมเดลกับผลวิเคราะห์แล็บจริง (Day 3 และ Day 7)
    เพื่อตรวจสอบความคลาดเคลื่อน (Sanity Check)
    fog_lab: dict ในรูป {3: FOG_val, 7: FOG_val}
    """
    print("\n[FDEI Validation vs Lab]")
    for day, fog_val in fog_lab.items():
        fog_removal_lab = (fog_day0 - fog_val) / fog_day0 * 100
        # หา index แถวที่เวลาใกล้เคียงกับวันตรวจแล็บ
        mask = df['elapsed_days'].between(day - 0.1, day + 0.1)
        fdei_model = fdei_series[mask].mean() if mask.sum() > 0 else None
        if fdei_model is not None:
            err = abs(fdei_model - fog_removal_lab)
            print(f"  Day {day}: Lab={fog_removal_lab:.1f}%  "
                  f"Model={fdei_model:.1f}%  Error={err:.1f}%")

def create_sequences_1step(data, targets, time_step):
    """
    สร้าง Sliding Window (X, y) สำหรับป้อนโมเดล AI
    X shape: (n_samples, time_step, n_features)
    y shape: (n_samples,)
    """
    X, y = [], []
    for i in range(len(data) - time_step):
        X.append(data[i : i + time_step])
        y.append(targets[i + time_step])
    return np.array(X), np.array(y)

def prepare_dataset(df, features, target, time_step, train_ratio=0.70, val_ratio=0.15):
    """
    เตรียม dataset และปรับสเกลข้อมูล (Fit Scaler บน Train set และ Transform ทุกเซ็ต)
    ส่งคืน Scalers และเซ็ตข้อมูลเพื่อไปรันการ Train
    """
    n = len(df)
    n_train = int(n * train_ratio)
    n_val   = int(n * val_ratio)

    df_train = df.iloc[:n_train]
    df_val   = df.iloc[n_train : n_train + n_val]
    df_test  = df.iloc[n_train + n_val :]

    print(f"\n[Dataset Split] Train: {len(df_train)} | Val: {len(df_val)} | Test: {len(df_test)}")

    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()

    X_train_raw = scaler_X.fit_transform(df_train[features].values)
    X_val_raw   = scaler_X.transform(df_val[features].values)
    X_test_raw  = scaler_X.transform(df_test[features].values)

    y_train_raw = scaler_y.fit_transform(df_train[[target]].values).flatten()
    y_val_raw   = scaler_y.transform(df_val[[target]].values).flatten()
    y_test_raw  = scaler_y.transform(df_test[[target]].values).flatten()

    X_train, y_train = create_sequences_1step(X_train_raw, y_train_raw, time_step)
    X_val,   y_val   = create_sequences_1step(X_val_raw,   y_val_raw,   time_step)
    X_test,  y_test  = create_sequences_1step(X_test_raw,  y_test_raw,  time_step)

    print(f"[Dataset Windows] Train: {X_train.shape} | Val: {X_val.shape} | Test: {X_test.shape}")
    return (X_train, y_train,
            X_val,   y_val,
            X_test,  y_test,
            scaler_X, scaler_y)


# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
# Multi-Batch Support Functions
# ══════════════════════════════════════════════════════════════

def process_single_batch(csv_path, fog_day0, fog_day7, fog_lab_checkpoints,
                         resample_interval, features, batch_id='unknown'):
    """
    ประมวลผลข้อมูลของ 1 Batch ทั้งหมด:
    Load → Clean → Resample → Cumulative CO₂ → Y → FDEI → Validate

    Parameters
    ----------
    csv_path : str
        Path ไปยังไฟล์ CSV ของ Batch นี้
    fog_day0 : float
        ค่า FOG Day0 (mg/L) จากห้องแล็บ
    fog_day7 : float
        ค่า FOG Day7 (mg/L) จากห้องแล็บ
    fog_lab_checkpoints : dict
        ค่า FOG ตรวจแล็บระหว่างทาง เช่น {"3": 1121.333}
    resample_interval : str or None
        ช่วง resampling เช่น '5min' หรือ None (ใช้ 30s ดิบ)
    features : list[str]
        รายชื่อคอลัมน์ฟีเจอร์ เช่น ['co2', 'ph', 'tds', 'turbidity']
    batch_id : str
        ชื่อ Batch สำหรับ log

    Returns
    -------
    df : pd.DataFrame
        DataFrame ที่ประมวลผลแล้ว (มีคอลัมน์ co2_cumulative, fdei)
    Y : float
        Yield Coefficient ของ Batch นี้
    interval_sec : int
        ระยะเวลาช่วง sampling (วินาที) หลัง resampling
    """
    # Lazy import เพื่อหลีกเลี่ยง circular dependency
    from src import preprocess as dp

    print(f"\n{'─' * 50}")
    print(f"  Processing Batch: {batch_id}")
    print(f"  File: {csv_path}")
    print(f"  FOG Day0={fog_day0:.3f}  Day7={fog_day7:.3f}")
    print(f"{'─' * 50}")

    # 1. โหลดข้อมูล
    df = dp.load_data(csv_path)

    # 2. ทำความสะอาดข้อมูลดิบ
    df = dp.handle_turbidity_zeros(df)
    df = dp.winsorize_outliers(df, cols=['ph', 'tds'], iqr_factor=3.0)

    # 3. Resampling
    if resample_interval:
        df = dp.resample_data(df, resample_interval)
        interval_sec = int(pd.Timedelta(resample_interval).total_seconds())
    else:
        interval_sec = 30  # raw sampling rate

    # 4. Feature Engineering
    df = compute_cumulative_co2(df, interval_seconds=interval_sec)
    Y = compute_yield_coefficient(df, fog_day0, fog_day7)
    df = compute_fdei(df, fog_day0, Y)

    # 5. Sanity Check กับค่าแล็บ (ถ้ามี)
    if fog_lab_checkpoints:
        fog_lab = {int(k): v for k, v in fog_lab_checkpoints.items()}
        validate_fdei_against_lab(
            fdei_series=df['fdei'],
            df=df,
            fog_lab=fog_lab,
            fog_day0=fog_day0
        )

    print(f"[Batch {batch_id}] ประมวลผลสำเร็จ: {len(df):,} แถว | Y={Y:.4f}")
    return df, Y, interval_sec


def prepare_multi_batch_dataset(batch_dataframes, features, target,
                                time_step, train_ratio=0.70, val_ratio=0.15):
    """
    รวมข้อมูลจากหลาย Batch เพื่อเตรียมชุดเทรน:
    1. Fit Scaler บนข้อมูลรวมทุก Batch (global normalization)
    2. สร้าง Sliding Window แยกต่อ Batch (ไม่ข้ามขอบเขต)
    3. Concat sequences ทั้งหมดแล้วแบ่ง Train/Val/Test

    Parameters
    ----------
    batch_dataframes : list[pd.DataFrame]
        List ของ DataFrame ที่ผ่าน process_single_batch() แล้ว
    features : list[str]
        รายชื่อคอลัมน์ฟีเจอร์
    target : str
        ชื่อคอลัมน์ target
    time_step : int
        ขนาด lookback window
    train_ratio : float
        สัดส่วนข้อมูล Train
    val_ratio : float
        สัดส่วนข้อมูล Validation

    Returns
    -------
    tuple: (X_train, y_train, X_val, y_val, X_test, y_test, scaler_X, scaler_y)
    """
    from sklearn.preprocessing import MinMaxScaler

    # ── Step 1: รวมข้อมูลดิบทุก Batch เพื่อ Fit Scaler แบบ Global ──
    all_features_raw = pd.concat([df[features] for df in batch_dataframes], ignore_index=True)
    all_target_raw   = pd.concat([df[[target]] for df in batch_dataframes], ignore_index=True)

    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()

    scaler_X.fit(all_features_raw.values)
    scaler_y.fit(all_target_raw.values)

    total_rows = len(all_features_raw)
    print(f"\n[Multi-Batch] รวมข้อมูลทั้งหมด: {total_rows:,} แถว จาก {len(batch_dataframes)} batches")
    print(f"[Multi-Batch] Fit Scaler (Global) สำเร็จ")

    # ── Step 2: สร้าง Sequences แยกต่อ Batch (ป้องกันข้ามขอบเขต) ──
    all_X, all_y = [], []
    for i, df in enumerate(batch_dataframes):
        X_scaled = scaler_X.transform(df[features].values)
        y_scaled = scaler_y.transform(df[[target]].values).flatten()

        X_seq, y_seq = create_sequences_1step(X_scaled, y_scaled, time_step)
        all_X.append(X_seq)
        all_y.append(y_seq)
        print(f"  Batch {i+1}: {len(df):,} แถว → {X_seq.shape[0]:,} sequences")

    X_all = np.concatenate(all_X, axis=0)
    y_all = np.concatenate(all_y, axis=0)
    print(f"[Multi-Batch] รวม Sequences ทั้งหมด: {X_all.shape[0]:,}")

    # ── Step 3: แบ่ง Train / Val / Test ──
    n = X_all.shape[0]
    n_train = int(n * train_ratio)
    n_val   = int(n * val_ratio)

    # Shuffle เพื่อให้แต่ละ split มีตัวแทนจากทุก Batch
    indices = np.random.RandomState(42).permutation(n)
    X_all = X_all[indices]
    y_all = y_all[indices]

    X_train = X_all[:n_train]
    y_train = y_all[:n_train]
    X_val   = X_all[n_train:n_train+n_val]
    y_val   = y_all[n_train:n_train+n_val]
    X_test  = X_all[n_train+n_val:]
    y_test  = y_all[n_train+n_val:]

    print(f"[Multi-Batch Split] Train: {X_train.shape} | Val: {X_val.shape} | Test: {X_test.shape}")
    return (X_train, y_train,
            X_val,   y_val,
            X_test,  y_test,
            scaler_X, scaler_y)
