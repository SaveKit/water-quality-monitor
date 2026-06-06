import os
import sys
import json

# เพิ่ม path เพื่อให้ค้นหาโมดูลใน ml_pipeline เจอ
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

# ฟังก์ชันโหลด .env แบบแมนนวลกรณีไม่ได้ติดตั้ง python-dotenv
def load_env_manually():
    env_path = os.path.join(base_dir, '.env')
    if os.path.exists(env_path):
        print("[Local Test] โหลดตัวแปรสภาพแวดล้อมจาก .env...")
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    # ลบเครื่องหมายคำพูด (ถ้ามี)
                    val_str = val.strip().strip("'\"")
                    os.environ[key.strip()] = val_str
    else:
        print("[Local Test] ไม่พบไฟล์ .env กรุณาสร้างจาก .env.example")

# เรียกโหลด env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(base_dir, '.env'))
    print("[Local Test] โหลด env ผ่าน python-dotenv สำเร็จ")
except ImportError:
    load_env_manually()

# ตรวจสอบตัวแปรสภาพแวดล้อมเบื้องต้น
required_vars = ['AWS_REGION', 'DYNAMODB_TABLE_SENSOR', 'DYNAMODB_TABLE_FORECAST', 'DYNAMODB_TABLE_ALERTS']
missing = [var for var in required_vars if not os.environ.get(var)]
if missing:
    print(f"[Warning] ตัวแปรสภาพแวดล้อมที่จำเป็นเหล่านี้ยังไม่ถูกตั้งค่า: {missing}")
    print("กรุณาสร้างไฟล์ .env และใส่ข้อมูลให้ครบก่อนทำการรันจริง\n")

from lambda_function.app import lambda_handler

if __name__ == '__main__':
    print("\n[Local Test] เริ่มทดสอบเรียกใช้ Lambda Handler แบบ Local...")
    # ส่ง event จำลอง
    mock_event = {"source": "local-testing"}
    
    try:
        result = lambda_handler(mock_event, None)
        print("\n[Local Test] ผลลัพธ์จากการรัน:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\n[Local Test] เกิดข้อผิดพลาดขณะรัน Handler: {e}")
