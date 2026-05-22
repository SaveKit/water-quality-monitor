import boto3
import pandas as pd
from boto3.dynamodb.conditions import Key
from datetime import datetime
import pytz


def export_dynamodb_to_csv(
    table_name, node_id, output_filename, start_time=None, end_time=None
):
    print(f"กำลังเชื่อมต่อกับตาราง: {table_name}...")

    # 1. เชื่อมต่อ AWS DynamoDB
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # 2. จัดการเงื่อนไขการค้นหา (Key Condition)
    condition = Key("node_id").eq(node_id)

    # หากมีการระบุช่วงเวลา ให้แปลงจาก String (เวลาไทย) เป็น Milliseconds (UTC)
    if start_time and end_time:
        bkk_tz = pytz.timezone("Asia/Bangkok")

        start_dt = bkk_tz.localize(datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S"))
        end_dt = bkk_tz.localize(datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S"))

        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)

        print(f"กรองข้อมูลตั้งแต่: {start_time} ถึง {end_time}")
        condition = condition & Key("timestamp").between(start_ms, end_ms)
    else:
        print("ดึงข้อมูลทั้งหมด (ไม่ได้ระบุช่วงเวลา)")

    items = []

    # 3. คิวรีข้อมูลรอบแรก
    print(f"เริ่มดึงข้อมูลของ {node_id}...")
    response = table.query(KeyConditionExpression=condition)
    items.extend(response.get("Items", []))

    # 4. ลูปดึงข้อมูลหน้าถัดไป (กรณีข้อมูลเยอะ)
    while "LastEvaluatedKey" in response:
        print("ดึงข้อมูลหน้าถัดไป...")
        response = table.query(
            KeyConditionExpression=condition,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    if not items:
        print("❌ ไม่พบข้อมูลในระบบ (หรือไม่มีข้อมูลในช่วงเวลาที่กำหนด)")
        return

    print(f"✅ ดึงข้อมูลสำเร็จทั้งหมด: {len(items)} แถว")

    # 5. แปลงข้อมูลเป็น Pandas DataFrame
    df = pd.DataFrame(items)

    # 6. แปลงชนิดข้อมูลและจัดการเวลา (เพิ่ม co2 แล้ว)
    if "timestamp" in df.columns:
        # แปลงเป็น float เพื่อให้ pandas นำไปพล็อตกราฟหรือคำนวณต่อได้
        for col in ["timestamp", "ph", "tds", "turbidity", "temperature", "co2"]:
            if col in df.columns:
                df[col] = df[col].astype(float)

        # แปลงเวลาหน่วยมิลลิวินาที ให้เป็นวัน-เวลา Timezone ประเทศไทย (UTC+7)
        df["datetime"] = (
            pd.to_datetime(df["timestamp"], unit="ms")
            .dt.tz_localize("UTC")
            .dt.tz_convert("Asia/Bangkok")
        )
        # ลบ timezone info ออกเพื่อให้เซฟลง csv ได้ง่าย
        df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # 7. จัดเรียงคอลัมน์ให้สวยงาม (เพิ่ม co2 ต่อท้าย)
    cols = [
        "node_id",
        "datetime",
        "timestamp",
        "ph",
        "tds",
        "turbidity",
        "temperature",
        "co2",
    ]
    df = df[[c for c in cols if c in df.columns]]

    # 8. บันทึกเป็นไฟล์ CSV
    df.to_csv(output_filename, index=False)
    print(f"📁 บันทึกไฟล์สำเร็จ: {output_filename}")


# ==========================================
# ส่วนสำหรับตั้งค่าและรันสคริปต์
# ==========================================
if __name__ == "__main__":

    # ตัวอย่างการใช้งาน: ระบุช่วงเวลาที่ต้องการ (ปี-เดือน-วัน ชั่วโมง:นาที:วินาที)
    # หากต้องการดึงทั้งหมด ให้เปลี่ยนเป็น: start_time=None, end_time=None

    export_dynamodb_to_csv(
        table_name="WaterQualityData",
        node_id="Node02",
        output_filename="node02_experiment2_data_7days.csv",
        # start_time="2026-03-31 00:00:00",  # เวลาเริ่มต้น
        # end_time="2026-04-08 08:00:00",  # เวลาสิ้นสุด
        start_time="2026-05-13 14:45:00",  # เวลาเริ่มต้น
        end_time="2026-05-20 12:30:00",  # เวลาสิ้นสุด
    )
