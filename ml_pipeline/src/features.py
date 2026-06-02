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
