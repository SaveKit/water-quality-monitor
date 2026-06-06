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
    # ══════════════════════════════════════════════════════════
    # Multi-Batch Training Pipeline
    # ══════════════════════════════════════════════════════════
    base_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir  = os.path.join(base_dir, 'data')
    config_path = os.path.join(data_dir, 'batches_config.json')

    # ── โหลด Batches Configuration ──
    if not os.path.exists(config_path):
        print(f"[Error] ไม่พบไฟล์ batches_config.json ที่: {config_path}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        batches_config = json.load(f)

    batches = batches_config['batches']
    print("\n" + "=" * 56)
    print(" เริ่มรันระบบฝึกสอนโมเดล (Multi-Batch Training Pipeline)")
    print(f" จำนวน Batches: {len(batches)}")
    print("=" * 56)

    # ── ประมวลผลแต่ละ Batch ──
    batch_dataframes = []
    Y_per_batch      = {}
    fog_day0_latest = None

    for batch_info in batches:
        csv_path = os.path.join(data_dir, batch_info['csv_file'])

        if not os.path.exists(csv_path):
            print(f"\n[Warning] ไม่พบไฟล์ {batch_info['csv_file']} — ข้าม Batch นี้")
            continue

        fog_day0 = batch_info['fog_day0']
        fog_day7 = batch_info['fog_day7']

        if fog_day0 is None or fog_day7 is None:
            print(f"\n[Warning] Batch '{batch_info['batch_id']}' ไม่มีค่า FOG Lab — ข้าม Batch นี้")
            continue

        df_batch, Y_batch, _ = feat.process_single_batch(
            csv_path            = csv_path,
            fog_day0            = fog_day0,
            fog_day7            = fog_day7,
            fog_lab_checkpoints = batch_info.get('fog_lab_checkpoints', {}),
            resample_interval   = CONFIG['RESAMPLE'],
            features            = FEATURES,
            batch_id            = batch_info['batch_id']
        )

        batch_dataframes.append(df_batch)
        Y_per_batch[batch_info['batch_id']] = Y_run = Y_batch
        fog_day0_latest = fog_day0

    if len(batch_dataframes) == 0:
        print("\n[Error] ไม่มี Batch ที่สามารถประมวลผลได้ กรุณาตรวจสอบไฟล์ข้อมูลและ batches_config.json")
        sys.exit(1)

    print(f"\n{'═' * 56}")
    print(f" สรุป Yield Coefficient (Y) ต่อ Batch:")
    for bid, yval in Y_per_batch.items():
        print(f"   {bid}: Y = {yval:.4f} (ppm·s per mg/L)")
    print(f"{'═' * 56}")

    # ── สร้าง Dataset รวมจากทุก Batch ──
    (X_train, y_train,
     X_val,   y_val,
     X_test,  y_test,
     scaler_X, scaler_y) = feat.prepare_multi_batch_dataset(
        batch_dataframes = batch_dataframes,
        features       = FEATURES,
        target         = TARGET,
        time_step      = CONFIG['TIME_STEP'],
        train_ratio    = CONFIG['TRAIN_RATIO'],
        val_ratio      = CONFIG['VAL_RATIO']
    )

    # ── เทรนโมเดล CNN-GRU-SVR ──
    model, svr, extractor, history = full_train_pipeline(
        X_train, y_train, X_val, y_val, CONFIG
    )

    # ── ประเมินผล ──
    mae, rmse, mape, y_true, y_pred = evaluate_model(
        svr, extractor, X_test, y_test, scaler_y
    )

    # ── บันทึกผลกราฟ ──
    plot_results(y_true, y_pred, history)

    # ── เซฟโมเดลและ configuration ──
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

    # ── คำนวณ Y เฉลี่ยถ่วงน้ำหนักสำหรับ Inference ──
    # ใช้จำนวนแถวของแต่ละ Batch เป็นน้ำหนัก
    Y_values = list(Y_per_batch.values())
    batch_sizes = [len(df) for df in batch_dataframes]
    Y_weighted_avg = float(np.average(Y_values, weights=batch_sizes))

    # เซฟ metadata สำหรับงาน inference
    meta = {
        'Y': Y_weighted_avg,
        'Y_per_batch': {k: float(v) for k, v in Y_per_batch.items()},
        'features': FEATURES,
        'target': TARGET,
        'time_step': int(CONFIG['TIME_STEP']),
        'fog_day0': float(fog_day0_latest),
        'batches_used': list(Y_per_batch.keys()),
        'total_sequences': int(X_train.shape[0] + X_val.shape[0] + X_test.shape[0]),
        'metrics': {
            'MAE': float(mae),
            'RMSE': float(rmse),
            'MAPE': float(mape)
        }
    }
    with open(os.path.join(models_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)
        
    print(f"\n[Save] บันทึกโมเดลและ Scalers เรียบร้อยแล้วในโฟลเดอร์: {models_dir}")
    print(f"[Save] Y (ถ่วงน้ำหนัก) = {Y_weighted_avg:.4f}")
    print(f"[Save] Batches ที่ใช้เทรน: {list(Y_per_batch.keys())}")
    print("\n" + "=" * 56)
    print(" เสร็จสิ้นขั้นตอนการเทรนอย่างสมบูรณ์ (Multi-Batch)")
    print("=" * 56)
