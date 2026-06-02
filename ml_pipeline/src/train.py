import os
import sys
import pickle
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg') # รันโหมด headless เพื่อเลี่ยงการเปิดหน้าต่าง UI
import matplotlib.pyplot as plt

from sklearn.svm import SVR
from sklearn.metrics import mean_absolute_error, mean_squared_error
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

# เพิ่มพาธสำหรับรันแบบสคริปต์เดี่ยว
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import preprocess as dp
from src import features as feat
from src import model as am

# ── Hyperparameters (ตั้งค่าคงที่สำหรับรันโมเดล) ──
CONFIG = {
    'CNN_FILTERS'    : 64,
    'KERNEL_SIZE'    : 5,
    'MAXPOOL_SIZE'   : 2,
    'GRU_UNITS'      : 32,
    'DROPOUT'        : 0.2,
    'SVR_KERNEL'     : 'rbf',
    'SVR_C'          : 10000,
    'TIME_STEP'      : 7,          # lookback window (steps)
    'OPTIMIZER'      : 'adam',
    'LR'             : 0.0008,
    'EPOCHS'         : 100,
    'BATCH_SIZE'     : 64,
    'RESAMPLE'       : '5min',     # หรือ None หากต้องการใช้ 30s ดิบ
    'TRAIN_RATIO'    : 0.70,
    'VAL_RATIO'      : 0.15,
    'FOG_DAY0'       : 2250.667,   # FOG mg/L จากห้องแล็บเริ่มต้น
    'FOG_DAY7'       : 166.667,    # FOG mg/L จากห้องแล็บวันที่ 7
}

FEATURES = ['co2', 'ph', 'tds', 'turbidity']
TARGET   = 'co2'

def train_cnn_gru(X_train, y_train, X_val, y_val, cfg):
    input_shape = (X_train.shape[1], X_train.shape[2])
    model = am.build_cnn_gru(input_shape, cfg)
    model.summary()

    callbacks = [
        EarlyStopping(monitor='val_loss', patience=10,
                      restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', patience=5,
                          factor=0.5, min_lr=1e-6, verbose=1)
    ]

    print("\n[Train] เริ่มต้นเทรน CNN-GRU...")
    history = model.fit(
        X_train, y_train,
        validation_data = (X_val, y_val),
        epochs          = cfg['EPOCHS'],
        batch_size      = cfg['BATCH_SIZE'],
        callbacks       = callbacks,
        verbose         = 1
    )
    return model, history

def train_svr(model, X_train, y_train, cfg):
    # สกัด Features จาก CNN-GRU เพื่อส่งให้ SVR
    extractor = am.get_feature_extractor(model)
    features_train = extractor.predict(X_train, verbose=0)

    print(f"\n[Train] เริ่มต้นเทรน SVR บน Features shape: {features_train.shape}")
    svr = SVR(kernel=cfg['SVR_KERNEL'], C=cfg['SVR_C'], epsilon=0.01)
    svr.fit(features_train, y_train)
    print("[Train] SVR เทรนเสร็จสิ้น")
    return svr, extractor

def full_train_pipeline(X_train, y_train, X_val, y_val, cfg):
    model, history = train_cnn_gru(X_train, y_train, X_val, y_val, cfg)
    svr, extractor = train_svr(model, X_train, y_train, cfg)
    return model, svr, extractor, history

def evaluate_model(svr, extractor, X_test, y_test, scaler_y):
    features_test = extractor.predict(X_test, verbose=0)
    y_pred_scaled = svr.predict(features_test)

    # Inverse scale เพื่อนำค่าจริงกลับมา
    y_true = scaler_y.inverse_transform(y_test.reshape(-1, 1)).flatten()
    y_pred = scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()

    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100

    print("\n" + "=" * 40)
    print("ผลการทดสอบโมเดล (Evaluation Results)")
    print("=" * 40)
    print(f"MAE  : {mae:.4f} ppm")
    print(f"RMSE : {rmse:.4f} ppm")
    print(f"MAPE : {mape:.2f}%")
    print("=" * 40)
    return mae, rmse, mape, y_true, y_pred

def plot_results(y_true, y_pred, history):
    fig, axes = plt.subplots(1, 2, figsize=(14, 4))

    # กราฟเปรียบเทียบค่าพยากรณ์กับค่าจริง
    axes[0].plot(y_true[:200], label='Actual CO₂', color='#1D9E75', lw=1.5)
    axes[0].plot(y_pred[:200], label='Predicted CO₂', color='#534AB7',
                 lw=1.5, linestyle='--')
    axes[0].set_title('CO₂ Prediction vs Actual (First 200 points)')
    axes[0].set_xlabel('Timestep')
    axes[0].set_ylabel('CO₂ (ppm)')
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    # กราฟแสดง loss ระหว่างเทรน
    axes[1].plot(history.history['loss'],     label='Train Loss', color='#1D9E75')
    axes[1].plot(history.history['val_loss'], label='Val Loss',   color='#534AB7')
    axes[1].set_title('Training Loss (MSE)')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Loss')
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    output_plot = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'training_results.png')
    plt.savefig(output_plot, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Plot] บันทึกกราฟสรุปผลการเทรน → {output_plot}")

if __name__ == '__main__':
    # ── รัน Pipeline หลักสำหรับเทรนโมเดล ──
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_PATH = os.path.join(base_dir, 'data', 'node01_new_data_7days.csv')
    
    if not os.path.exists(DATA_PATH):
        print(f"ไม่พบไฟล์ข้อมูลดิบที่: {DATA_PATH} กำลังตรวจหาในโฟลเดอร์หลัก...")
        DATA_PATH = 'node01_new_data_7days.csv'

    if not os.path.exists(DATA_PATH):
        print("ไม่พบไฟล์สำหรับการเทรน กรุณาตรวจสอบตำแหน่งไฟล์ข้อมูลใหม่")
        sys.exit(1)

    print("\n==========================================")
    print(" เริ่มรันระบบฝึกสอนโมเดล (ML Training Pipeline)")
    print("==========================================")

    # 1. โหลดข้อมูล
    df = dp.load_data(DATA_PATH)
    
    # 2. ทำความสะอาดข้อมูลดิบ
    df = dp.handle_turbidity_zeros(df)
    df = dp.winsorize_outliers(df, cols=['ph', 'tds'], iqr_factor=3.0)

    # 3. Resampling (ลดความละเอียดข้อมูล)
    if CONFIG['RESAMPLE']:
        df = dp.resample_data(df, CONFIG['RESAMPLE'])
        interval_sec = 300   # 5 min = 300s
    else:
        interval_sec = 30    # 30s raw

    # 4. Feature Engineering
    df = feat.compute_cumulative_co2(df, interval_seconds=interval_sec)
    Y = feat.compute_yield_coefficient(df, CONFIG['FOG_DAY0'], CONFIG['FOG_DAY7'])
    df = feat.compute_fdei(df, CONFIG['FOG_DAY0'], Y)

    # Sanity Check เปรียบเทียบกับค่าวิเคราะห์แล็บที่วันที่ 3 และ 7
    feat.validate_fdei_against_lab(
        fdei_series = df['fdei'],
        df          = df,
        fog_lab     = {3: 1121.333, 7: 166.667},
        fog_day0    = CONFIG['FOG_DAY0']
    )

    # 5. สร้าง Sequence Sliding Windows
    (X_train, y_train,
     X_val,   y_val,
     X_test,  y_test,
     scaler_X, scaler_y) = feat.prepare_dataset(
        df,
        features   = FEATURES,
        target     = TARGET,
        time_step  = CONFIG['TIME_STEP'],
        train_ratio= CONFIG['TRAIN_RATIO'],
        val_ratio  = CONFIG['VAL_RATIO']
    )

    # 6. เทรนโมเดล CNN-GRU-SVR
    model, svr, extractor, history = full_train_pipeline(
        X_train, y_train, X_val, y_val, CONFIG
    )

    # 7. ประเมินผล
    mae, rmse, mape, y_true, y_pred = evaluate_model(
        svr, extractor, X_test, y_test, scaler_y
    )

    # 8. บันทึกผลกราฟ
    plot_results(y_true, y_pred, history)

    # 9. เซฟโมเดลและ configuration
    models_dir = os.path.join(base_dir, 'models')
    os.makedirs(models_dir, exist_ok=True)

    # เซฟ Keras CNN-GRU
    model.save(os.path.join(models_dir, 'cnn_gru_model.keras'))

    # เซฟ SVR และ Scalers
    with open(os.path.join(models_dir, 'svr_model.pkl'), 'wb') as f:
        pickle.dump(svr, f)
    with open(os.path.join(models_dir, 'scaler_X.pkl'), 'wb') as f:
        pickle.dump(scaler_X, f)
    with open(os.path.join(models_dir, 'scaler_y.pkl'), 'wb') as f:
        pickle.dump(scaler_y, f)

    # เซฟ metadata สำหรับงาน inference
    meta = {
        'Y': float(Y),
        'features': FEATURES,
        'target': TARGET,
        'time_step': int(CONFIG['TIME_STEP']),
        'fog_day0': float(CONFIG['FOG_DAY0'])
    }
    with open(os.path.join(models_dir, 'metadata.json'), 'w') as f:
        json.dump(meta, f, indent=4)
        
    print(f"\n[Save] บันทึกโมเดลและ Scalers เรียบร้อยแล้วในโฟลเดอร์: {models_dir}")
    print("\n==========================================")
    print("เสร็จสิ้นขั้นตอนการเทรนอย่างสมบูรณ์")
    print("==========================================")
