import os
import sys
import pickle
import json
import numpy as np

# เพิ่มพาธสำหรับรันแบบสคริปต์เดี่ยว
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ฟังก์ชันสำหรับโหลดโมเดลและเครื่องมือประมวลผล
def load_inference_artifacts(models_dir=None):
    if models_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        models_dir = os.path.join(base_dir, 'models')

    import tensorflow as tf
    
    # 1. โหลด Keras model (CNN-GRU)
    model_path = os.path.join(models_dir, 'cnn_gru_model.keras')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"ไม่พบไฟล์ CNN-GRU model ที่: {model_path}")
    model = tf.keras.models.load_model(model_path)

    # 2. โหลด SVR model
    svr_path = os.path.join(models_dir, 'svr_model.pkl')
    if not os.path.exists(svr_path):
        raise FileNotFoundError(f"ไม่พบไฟล์ SVR model ที่: {svr_path}")
    with open(svr_path, 'rb') as f:
        svr = pickle.load(f)

    # 3. โหลด Scaler X และ Scaler y
    scaler_x_path = os.path.join(models_dir, 'scaler_X.pkl')
    scaler_y_path = os.path.join(models_dir, 'scaler_y.pkl')
    with open(scaler_x_path, 'rb') as f:
        scaler_X = pickle.load(f)
    with open(scaler_y_path, 'rb') as f:
        scaler_y = pickle.load(f)

    # 4. โหลด Metadata
    meta_path = os.path.join(models_dir, 'metadata.json')
    with open(meta_path, 'r') as f:
        metadata = json.load(f)

    # สร้าง Feature Extractor จากโมเดล CNN-GRU ที่โหลดมา
    from src import model as am
    extractor = am.get_feature_extractor(model)

    return {
        'model': model,
        'svr': svr,
        'extractor': extractor,
        'scaler_X': scaler_X,
        'scaler_y': scaler_y,
        'metadata': metadata
    }

def predict_recursive_forecast(recent_data, steps, artifacts):
    """
    ทำนายผลลัพธ์ CO2 ล่วงหน้าแบบ Recursive (Autoregressive)
    recent_data: pandas DataFrame หรือ numpy array ขนาด [time_step, n_features] ที่เป็นข้อมูลดิบล่าสุด
    steps: จำนวน steps ที่ต้องการทำนายไปในอนาคต (เช่น 288 steps สำหรับ 24 ชม. ของความละเอียด 5 นาที)
    """
    scaler_X = artifacts['scaler_X']
    scaler_y = artifacts['scaler_y']
    svr = artifacts['svr']
    extractor = artifacts['extractor']
    time_step = artifacts['metadata']['time_step']
    features = artifacts['metadata']['features']
    
    # ตรวจสอบขนาดข้อมูล
    if len(recent_data) < time_step:
        raise ValueError(f"ข้อมูลล่าสุดมีจำนวนแถวไม่พอสำหรับ lookback window: ต้องมีอย่างน้อย {time_step} แถว (พบ {len(recent_data)})")

    # ดึงเฉพาะข้อมูลย้อนหลังตามขนาด lookback window และกรองเฉพาะคอลัมน์ฟีเจอร์หลัก
    if isinstance(recent_data, np.ndarray):
        current_seq_raw = recent_data[-time_step:].copy()
    else:
        current_seq_raw = recent_data[features].iloc[-time_step:].values.copy()

    # สเกลข้อมูลเข้า
    current_seq_scaled = scaler_X.transform(current_seq_raw)

    co2_predictions_scaled = []
    
    # วนลูปพยากรณ์ทีละ step
    for _ in range(steps):
        # ปรับมิติข้อมูลให้เหมาะกับโมเดล [1, time_step, n_features]
        model_input = np.expand_dims(current_seq_scaled, axis=0)
        
        # 1. สกัด Feature ผ่าน CNN-GRU
        extracted_feat = extractor.predict(model_input, verbose=0)
        
        # 2. พยากรณ์ค่า CO2 ถัดไปผ่าน SVR
        pred_scaled = svr.predict(extracted_feat)[0]
        co2_predictions_scaled.append(pred_scaled)
        
        # 3. เตรียมข้อมูลสำหรับ Step ถัดไป:
        # เลื่อน window ของข้อมูลเข้าในอนาคต โดยป้อนค่าทำนายล่าสุดของ CO2 (ตำแหน่ง index 0 ใน FEATURES)
        # และใช้ฟังก์ชันคงค่าตัวแปรอื่น (ph, tds, turbidity) ไว้ให้มีค่าเท่ากับจุดเวลาล่าสุด
        new_row = current_seq_scaled[-1].copy()
        new_row[0] = pred_scaled  # อัปเดตเฉพาะค่า CO2 ที่ทำนายได้ลงในช่องแรกของฟีเจอร์
        
        # เลื่อนข้อมูลเก่าออกและใส่แถวพยากรณ์ใหม่เข้า
        current_seq_scaled = np.vstack([current_seq_scaled[1:], new_row])

    # ทำ Inverse Scale เพื่อแปลงค่ากลับเป็น ppm
    co2_predictions_scaled = np.array(co2_predictions_scaled).reshape(-1, 1)
    co2_forecast = scaler_y.inverse_transform(co2_predictions_scaled).flatten()
    
    return co2_forecast

def calculate_fdei_forecast(co2_forecast, current_co2_cum, interval_seconds, artifacts):
    """
    แปลงค่า CO2 ที่พยากรณ์ได้ในอนาคต ให้กลายเป็นเปอร์เซ็นต์ประสิทธิภาพการย่อยสลาย FDEI ล่วงหน้า
    """
    Y = artifacts['metadata']['Y']
    fog_day0 = artifacts['metadata']['fog_day0']
    
    # คำนวณ Cumulative CO2 สะสมของอนาคต (Cumulative sum ของค่าทำนายรวมกับยอดสะสมปัจจุบัน)
    future_cum = current_co2_cum + np.cumsum(co2_forecast) * interval_seconds
    
    # ประเมินปริมาณ FOG ที่เหลืออยู่
    fog_est = fog_day0 - (future_cum / Y)
    fog_est = np.clip(fog_est, 0, fog_day0)
    
    # คำนวณ FDEI (%)
    fdei_forecast = (fog_day0 - fog_est) / fog_day0 * 100
    return np.clip(fdei_forecast, 0, 100)
