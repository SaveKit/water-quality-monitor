import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # สำหรับการรันแบบไม่มี GUI
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error

# เพิ่ม path เพื่อเชื่อมเข้าหาโฟลเดอร์หลัก
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

from src import preprocess as dp
from src import features as feat
from src import inference as inf

def evaluate_unseen_data(csv_path, fog_day0, fog_day7, run_id='unseen_run'):
    print(f"\n{'=' * 60}")
    print(f" เริ่มต้นการทดสอบโมเดลกับข้อมูลใหม่ (Unseen Run): {run_id}")
    print(f" ไฟล์ข้อมูล: {csv_path}")
    print(f"{'=' * 60}")

    # 1. ตรวจสอบไฟล์โมเดลที่บันทึกไว้
    models_dir = os.path.join(base_dir, 'models')
    try:
        artifacts = inf.load_inference_artifacts(models_dir)
        print("[Load] โหลดโมเดลและ Scalers จากโฟลเดอร์ models/ สำเร็จ")
    except Exception as e:
        print(f"[Error] ไม่สามารถโหลดโมเดลได้: {e}")
        print("กรุณาตรวจสอบว่ามีโมเดลอยู่ในโฟลเดอร์ models/ หรือไม่ (รัน train.py ก่อน)")
        return

    # 2. โหลดและเตรียมข้อมูลดิบ (Preprocessing)
    if not os.path.exists(csv_path):
        print(f"[Error] ไม่พบไฟล์ข้อมูลที่: {csv_path}")
        return

    # โหลด
    df = dp.load_data(csv_path)
    
    # ทำความสะอาดข้อมูล
    df = dp.handle_turbidity_zeros(df)
    df = dp.winsorize_outliers(df, cols=['ph', 'tds'], iqr_factor=3.0)
    
    # ดาวน์แซมพลิงข้อมูลเหลือ 5 นาที
    resample_interval = artifacts['metadata'].get('resample_interval', '5min')
    df_resampled = dp.resample_data(df, resample_interval)
    interval_sec = int(pd.Timedelta(resample_interval).total_seconds())

    # 3. คำนวณค่าจริงของ FDEI โดยใช้ Yield (Y) เฉพาะตัวของ Run นี้ (Calibrate)
    df_resampled = feat.compute_cumulative_co2(df_resampled, interval_seconds=interval_sec)
    
    # หาค่า Y ของรันใหม่จากผลแล็บ
    Y_calibrated = feat.compute_yield_coefficient(df_resampled, fog_day0, fog_day7)
    df_resampled = feat.compute_fdei(df_resampled, fog_day0, Y_calibrated)

    # 4. ทดสอบพยากรณ์ล่วงหน้าด้วยโมเดลปัจจุบัน (1-step-ahead Prediction)
    features = artifacts['metadata']['features']
    target = artifacts['metadata']['target']
    time_step = artifacts['metadata']['time_step']

    scaler_X = artifacts['scaler_X']
    scaler_y = artifacts['scaler_y']
    svr = artifacts['svr']
    extractor = artifacts['extractor']

    # ปรับสเกล Features ข้อมูลจริงทั้งหมด
    X_scaled = scaler_X.transform(df_resampled[features].values)
    y_scaled = scaler_y.transform(df_resampled[[target]].values).flatten()

    # สร้าง Window sequences
    X_seq, y_seq = feat.create_sequences_1step(X_scaled, y_scaled, time_step)

    # สกัด Features และทำนายค่า CO2
    extracted_feats = extractor.predict(X_seq, verbose=0)
    y_pred_scaled = svr.predict(extracted_feats)

    # แปลงสเกลกลับเป็นค่าจริง
    y_true_co2 = scaler_y.inverse_transform(y_seq.reshape(-1, 1)).flatten()
    y_pred_co2 = scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()

    # 5. คำนวณความแม่นยำ (Metrics)
    mae = mean_absolute_error(y_true_co2, y_pred_co2)
    rmse = np.sqrt(mean_squared_error(y_true_co2, y_pred_co2))
    mape = np.mean(np.abs((y_true_co2 - y_pred_co2) / (y_true_co2 + 1e-8))) * 100

    print("\n" + "=" * 45)
    print(f" ดัชนีวัดประสิทธิภาพการทำนาย CO2 (สำหรับ {run_id})")
    print("=" * 45)
    print(f"  MAE  : {mae:.4f} ppm")
    print(f"  RMSE : {rmse:.4f} ppm")
    print(f"  MAPE : {mape:.2f}%")
    print("=" * 45)

    # 6. เปรียบเทียบ FDEI
    # คำนวณ FDEI สะสมล่วงหน้าที่ได้จาก CO2 พยากรณ์ เปรียบเทียบกับ FDEI จริง
    # เราจะจำลองการพยากรณ์สะสมจากจุดสิ้นสุด lookback เสมือนเราเริ่มพยากรณ์ไปเรื่อยๆ
    predicted_fdei = []
    # ใช้ Y เฉลี่ยถ่วงน้ำหนักจากโมเดลหลัก เพื่อทดสอบประสิทธิภาพการเอาโมเดลกลางไปใช้จริง
    Y_model = artifacts['metadata']['Y']
    print(f"[Model Y] ใช้ค่าคงที่ Y กลางจากโมเดล : {Y_model:.4f}")
    
    # ประมาณค่า FDEI ที่ทำนายได้จาก CO2 ที่พยากรณ์ได้
    # fdei_pred = 100 * (1 - FOG_est / FOG_day0)
    cum_co2_pred = np.cumsum(y_pred_co2) * interval_sec
    fog_est_pred = fog_day0 - (cum_co2_pred / Y_model)
    fog_est_pred = np.clip(fog_est_pred, 0, fog_day0)
    y_pred_fdei = ((fog_day0 - fog_est_pred) / fog_day0 * 100).clip(0, 100)

    # ตัด FDEI จริงให้มีความยาวเท่ากับช่วงทำนาย
    y_true_fdei = df_resampled['fdei'].iloc[time_step:].values

    # 7. พลอตกราฟผลการทดสอบ
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # กราฟ CO2
    axes[0].plot(df_resampled['datetime'].iloc[time_step:], y_true_co2, label='Actual CO₂ (ข้อมูลจริง)', color='#1D9E75', lw=1.5)
    axes[0].plot(df_resampled['datetime'].iloc[time_step:], y_pred_co2, label='Predicted CO₂ (โมเดลทำนาย)', color='#534AB7', lw=1.5, linestyle='--')
    axes[0].set_title(f'CO₂ Prediction Performance ({run_id})', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('CO₂ (ppm)')
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    # กราฟ FDEI
    axes[1].plot(df_resampled['datetime'].iloc[time_step:], y_true_fdei, label='Actual FDEI (จริงจากแล็บและเซนเซอร์)', color='#1D9E75', lw=1.5)
    axes[1].plot(df_resampled['datetime'].iloc[time_step:], y_pred_fdei, label='Predicted FDEI (โมเดลพยากรณ์ + Y กลาง)', color='#FF9800', lw=1.5, linestyle='-.')
    axes[1].set_title('FDEI Performance Comparison', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('FDEI (%)')
    axes[1].set_xlabel('Time')
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    output_dir = os.path.join(base_dir, 'reports', 'figures')
    os.makedirs(output_dir, exist_ok=True)
    fig_path = os.path.join(output_dir, f'unseen_evaluation_{run_id}.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n[Plot Success] บันทึกกราฟเปรียบเทียบผลการประเมินแล้วที่: {fig_path}")

if __name__ == '__main__':
    # หากผู้ใช้ระบุอาร์กิวเมนต์ผ่าน CLI
    if len(sys.argv) >= 4:
        csv_path = sys.argv[1]
        fog_day0 = float(sys.argv[2])
        fog_day7 = float(sys.argv[3])
        run_id = sys.argv[4] if len(sys.argv) > 4 else 'unseen_run'
        evaluate_unseen_data(csv_path, fog_day0, fog_day7, run_id)
    else:
        # หากไม่ได้ระบุ ให้ใช้ข้อมูลของ Run 3 ที่อยู่ในโฟลเดอร์ data เป็นตัวอย่างทดสอบ
        data_dir = os.path.join(base_dir, 'data')
        example_csv = os.path.join(data_dir, 'node01_experiment3_data_7days.csv')
        
        # ตัวอย่างกรณีรันตัวเปล่า
        print("[Demo Mode] เนื่องจากคุณไม่ได้ส่งพารามิเตอร์ CLI ระบบจะสาธิตการทำงานโดยจำลองดึงไฟล์ Experiment 3:")
        evaluate_unseen_data(
            csv_path=example_csv,
            fog_day0=2892.0,
            fog_day7=993.333,
            run_id='experiment3_demo'
        )
        print("\n💡 คุณสามารถใช้งานสคริปต์นี้เพื่อตรวจข้อมูลใหม่ได้ตามตัวอย่าง:")
        print("python evaluate_unseen_run.py <path_to_csv> <fog_day0> <fog_day7> [run_id]")
