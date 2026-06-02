import os
import sys
import datetime
import boto3
import numpy as np
import pandas as pd
import urllib3
import json

# เพิ่ม root dir เข้า sys.path เพื่อให้อิมพอร์ต src ได้เมื่อรันใน Lambda
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import preprocess as dp
from src import features as feat
from src import inference as inf

# ดึงชื่อตารางและ config จาก environment variables
AWS_REGION = os.getenv('AWS_REGION', 'ap-southeast-1')
DYNAMODB_TABLE_SENSOR = os.getenv('DYNAMODB_TABLE_SENSOR', 'SensorReadings')
DYNAMODB_TABLE_FORECAST = os.getenv('DYNAMODB_TABLE_FORECAST', 'ForecastResults')
DYNAMODB_TABLE_ALERTS = os.getenv('DYNAMODB_TABLE_ALERTS', 'AlertHistory')

# Telegram configuration (ดึงจาก env)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Alert] ข้ามการส่ง Telegram: ไม่ได้กำหนด Token หรือ Chat ID")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    http = urllib3.PoolManager()
    try:
        response = http.request(
            'POST', 
            url, 
            headers={'Content-Type': 'application/json'},
            body=json.dumps(payload)
        )
        print(f"[Alert] ส่ง Telegram สำเร็จ Status Code: {response.status}")
    except Exception as e:
        print(f"[Alert] ส่ง Telegram ล้มเหลว: {e}")

def get_latest_sensor_data(node_id, limit=120):
    """
    ดึงข้อมูลย้อนหลังล่าสุดจาก DynamoDB
    120 records @ 30s sampling rate = ~60 นาที ซึ่งเกินพอสำหรับ lookback window 7 steps ของ 5min resample
    """
    table = dynamodb.Table(DYNAMODB_TABLE_SENSOR)
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('node_id').eq(node_id),
        ScanIndexForward=False, # เรียง DESC (เอาใหม่ล่าสุดขึ้นก่อน)
        Limit=limit
    )
    items = response.get('Items', [])
    if not items:
        return pd.DataFrame()
        
    df = pd.DataFrame(items)
    # แปลงชนิดข้อมูล
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['ph'] = df['ph'].astype(float)
    df['co2'] = df['co2'].astype(float)
    df['tds'] = df['tds'].astype(float)
    df['turbidity'] = df['turbidity'].astype(float)
    df['temp'] = df['temp'].astype(float)
    
    df.rename(columns={'timestamp': 'datetime'}, inplace=True)
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True) # เรียง ASC กลับคืนตามเวลาจริง
    return df

def save_forecast_results(node_id, timestamps, co2_pred, fdei_pred):
    """
    บันทึกผลการพยากรณ์ลงตาราง ForecastResults
    """
    table = dynamodb.Table(DYNAMODB_TABLE_FORECAST)
    
    # ดำเนินการแบบ Batch Write เพื่อความรวดเร็ว
    with table.batch_writer() as batch:
        for ts, co2, fdei in zip(timestamps, co2_pred, fdei_pred):
            # บันทึกข้อมูลพยากรณ์
            batch.put_item(
                Item={
                    'node_id': node_id,
                    'timestamp': ts.isoformat(),
                    'forecasted_co2': decimal_to_float_fix(co2),
                    'forecasted_fdei': decimal_to_float_fix(fdei)
                }
            )

def save_alert_history(node_id, fdei_val, alert_type, rec):
    """
    บันทึกประวัติการแจ้งเตือนลงตาราง AlertHistory
    """
    table = dynamodb.Table(DYNAMODB_TABLE_ALERTS)
    now = datetime.datetime.now(datetime.timezone.utc)
    table.put_item(
        Item={
            'node_id': node_id,
            'timestamp': now.isoformat(),
            'fdei_value': decimal_to_float_fix(fdei_val),
            'alert_type': alert_type,
            'recommendation': rec
        }
    )

def decimal_to_float_fix(val):
    # ปรับแต่งค่าทศนิยมเพื่อเลี่ยงปัญหา Decimal ใน DynamoDB
    import decimal
    return decimal.Decimal(str(round(float(val), 4)))

def check_for_plateau(fdei_forecast, recent_fdei_history):
    """
    ตรวจสอบสัญญาณการชะลอตัวของการย่อยสลายไขมัน (FDEI Plateau)
    เกณฑ์: 
    - FDEI ปัจจุบันต่ำกว่า 85% (ยังย่อยไม่เสร็จ)
    - อัตราการเพิ่มของ FDEI ในการทำนาย 2 ชั่วโมงข้างหน้า (24 steps) เพิ่มขึ้นน้อยกว่า 0.5%
    """
    if len(fdei_forecast) < 24:
        return False
        
    current_fdei = recent_fdei_history[-1] if len(recent_fdei_history) > 0 else 0.0
    future_fdei_2h = fdei_forecast[23] # จุดเวลา 2 ชั่วโมงข้างหน้า
    
    # หากย่อยเกือบเสร็จแล้ว (>85%) ความชันจะลดลงโดยธรรมชาติ ไม่ถือว่าผิดปกติ
    if current_fdei > 85.0:
        return False
        
    diff = future_fdei_2h - current_fdei
    if diff < 0.5: # เพิ่มขึ้นน้อยกว่า 0.5% ใน 2 ชม. บ่งชี้ว่าเริ่มเกิด Plateau (หยุดนิ่ง)
        return True
    return False

def lambda_handler(event, context):
    """
    AWS Lambda Main Entrypoint
    """
    print(f"ได้รับ Event: {json.dumps(event)}")
    
    # ตรวจสอบว่ามีโมเดลและเครื่องมือพร้อมใช้งาน
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(base_dir, 'models')
    
    try:
        artifacts = inf.load_inference_artifacts(models_dir)
    except Exception as e:
        print(f"[Error] ไม่สามารถโหลดโมเดลได้: {e}")
        return {'statusCode': 500, 'body': f"Model load error: {str(e)}"}

    # ประมวลผลสำหรับแต่ละ Node (Node01 = Sample, Node02 = Control)
    nodes = ['Node01', 'Node02']
    
    for node in nodes:
        print(f"\n--- เริ่มต้นประมวลผลโมเดลสำหรับ {node} ---")
        
        # 1. ดึงข้อมูลจาก DynamoDB
        df_raw = get_latest_sensor_data(node, limit=120)
        if df_raw.empty or len(df_raw) < 10:
            print(f"[Warning] ข้อมูลของ {node} มีไม่เพียงพอ ข้ามขั้นตอน...")
            continue
            
        # 2. Preprocessing
        df_clean = dp.handle_turbidity_zeros(df_raw)
        df_clean = dp.winsorize_outliers(df_clean, cols=['ph', 'tds'], iqr_factor=3.0)
        
        # Resample ให้เป็น 5 นาที
        df_resampled = dp.resample_data(df_clean, interval='5min')
        
        # ตรวจสอบว่ามีข้อมูลเพียงพอตาม Lookback window (7 steps = 35 นาที)
        time_step = artifacts['metadata']['time_step']
        if len(df_resampled) < time_step:
            print(f"[Warning] ข้อมูลหลัง Resample ของ {node} มีเพียง {len(df_resampled)} แถว (ต้องการ {time_step}) ข้าม...")
            continue
            
        # 3. คำนวณ Cumulative CO2 ของข้อมูลสะสมรอบปัจจุบัน
        # ในระบบปิด 7 วัน เราสามารถหา Cumulative sum ตั้งแต่เริ่มต้นรอบการทดลองได้
        # โดยการหาค่าสะสมรวมตั้งแต่วินาทีแรกของรัน
        # สำหรับ Lambda เราสามารถใช้ค่าเฉลี่ย sample interval = 300 วินาที (5 นาที)
        df_feat = feat.compute_cumulative_co2(df_resampled, interval_seconds=300)
        
        # คำนวณ FDEI ปัจจุบัน
        Y = artifacts['metadata']['Y']
        df_fdei = feat.compute_fdei(df_feat, artifacts['metadata']['fog_day0'], Y)
        
        current_cum = df_fdei['co2_cumulative'].iloc[-1]
        current_fdei = df_fdei['fdei'].iloc[-1]
        
        # 4. พยากรณ์ CO2 ล่วงหน้า 24 ชม. (288 steps ของความละเอียด 5 นาที)
        forecast_steps = 288
        try:
            # ใช้ 7 แถวสุดท้ายป้อนเข้าโมเดล
            recent_seq = df_fdei.iloc[-time_step:]
            co2_forecast = inf.predict_recursive_forecast(recent_seq, steps=forecast_steps, artifacts=artifacts)
            
            # คำนวณ FDEI ล่วงหน้าจากผลการพยากรณ์ CO2
            fdei_forecast = inf.calculate_fdei_forecast(co2_forecast, current_cum, interval_seconds=300, artifacts=artifacts)
        except Exception as e:
            print(f"[Error] การพยากรณ์ของ {node} ผิดพลาด: {e}")
            continue
            
        # 5. บันทึกผลพยากรณ์
        # สร้างคีย์เวลาในอนาคต (t+5min, t+10min, ...)
        last_timestamp = df_fdei['datetime'].iloc[-1]
        future_timestamps = [last_timestamp + datetime.timedelta(minutes=5 * (i+1)) for i in range(forecast_steps)]
        
        save_forecast_results(node, future_timestamps, co2_forecast, fdei_forecast)
        print(f"[Success] พยากรณ์และบันทึกผลสำเร็จ: {forecast_steps} จุดเวลาข้างหน้า")
        
        # 6. ระบบส่งการแจ้งเตือน (ตรวจจับสภาวะ Plateau เฉพาะถังทดลอง Node01)
        if node == 'Node01':
            recent_fdei_history = df_fdei['fdei'].values
            is_plateau = check_for_plateau(fdei_forecast, recent_fdei_history)
            
            if is_plateau:
                alert_type = "PLATEAU"
                rec = "กรุณาตรวจสอบสภาวะของถังปฏิกรณ์ชีวภาพ: ตรวจเช็คค่า pH (อาจมีความเป็นกรดจาก fatty acids สะสมมากเกินไป), เติมสารอาหาร หรือควบคุมอุณหภูมิให้เหมาะสมเพื่อรักษากิจกรรมของแบคทีเรีย Bacillus spp."
                
                print(f"[Alert] ตรวจพบการชะลอตัวในการย่อยสลาย FOG (FDEI Plateau) ณ FDEI = {current_fdei:.2f}%")
                
                # บันทึกลงตาราง AlertHistory
                save_alert_history(node, current_fdei, alert_type, rec)
                
                # ส่ง Telegram Alert
                msg = (
                    f"🚨 *แจ้งเตือนระบบบำบัดน้ำเสีย FOG (ถังทดลอง Node01)* 🚨\n\n"
                    f"พบสัญญาณ *การชะลอตัวในการย่อยสลายไขมัน (Plateau)*\n"
                    f"• *FDEI ปัจจุบัน:* {current_fdei:.2f}%\n"
                    f"• *สถานะ:* กิจกรรมการย่อยสลายเกือบจะหยุดนิ่งในอีก 2 ชั่วโมงข้างหน้า\n\n"
                    f"💡 *คำแนะนำ:* {rec}"
                )
                send_telegram_alert(msg)

    return {
        'statusCode': 200,
        'body': json.dumps('ประมวลผลและอัปเดตข้อมูลพยากรณ์เรียบร้อยแล้ว')
    }
