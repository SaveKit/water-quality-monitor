import boto3
import pandas as pd
from boto3.dynamodb.conditions import Key
import time


def export_dynamodb_to_csv(table_name, node_id, output_filename):
    print(f"กำลังเชื่อมต่อกับตาราง: {table_name}...")

    # 1. เชื่อมต่อ AWS DynamoDB (ใช้ credentials เดียวกับใช้รันคำสั่ง sam deploy)
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    items = []

    # 2. คิวรีข้อมูลเฉพาะของ Node01
    print(f"เริ่มดึงข้อมูลของ {node_id}...")
    response = table.query(KeyConditionExpression=Key("node_id").eq(node_id))
    items.extend(response.get("Items", []))

    # 3. ลูปดึงข้อมูลหน้าถัดไป (กรณีข้อมูลใหญ่เกิน 1MB)
    while "LastEvaluatedKey" in response:
        print("ดึงข้อมูลหน้าถัดไป...")
        response = table.query(
            KeyConditionExpression=Key("node_id").eq(node_id),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))

    if not items:
        print("❌ ไม่พบข้อมูลในระบบ")
        return

    print(f"✅ ดึงข้อมูลสำเร็จทั้งหมด: {len(items)} แถว")

    # 4. แปลงข้อมูลเป็น Pandas DataFrame
    df = pd.DataFrame(items)

    # 5. แปลงชนิดข้อมูลและจัดการเวลา
    if "timestamp" in df.columns:
        # แปลง Decimal เป็น float ก่อนเพื่อให้ pandas ทำงานได้ (แก้ Error ตรงนี้!)
        for col in ["timestamp", "ph", "tds", "turbidity", "temperature"]:
            if col in df.columns:
                df[col] = df[col].astype(float)

        # แปลงเวลาหน่วยมิลลิวินาที ให้เป็นวัน-เวลา Timezone ประเทศไทย (UTC+7)
        df["datetime"] = (
            pd.to_datetime(df["timestamp"], unit="ms")
            .dt.tz_localize("UTC")
            .dt.tz_convert("Asia/Bangkok")
        )
        # ลบ timezone info ออกเพื่อให้เซฟลง csv ได้ง่าย หรือจัดฟอร์แมตใหม่
        df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # 6. จัดเรียงคอลัมน์ให้สวยงาม (เอา datetime ขึ้นก่อน ตามด้วยเซ็นเซอร์)
    cols = ["node_id", "datetime", "timestamp", "ph", "tds", "turbidity", "temperature"]
    # กรองเอาเฉพาะคอลัมน์ที่มีจริงใน df ป้องกัน error
    df = df[[c for c in cols if c in df.columns]]

    # 7. บันทึกเป็นไฟล์ CSV
    df.to_csv(output_filename, index=False, encoding="utf-8")
    print(f"บันทึกไฟล์เสร็จสิ้น: {output_filename}")


if __name__ == "__main__":
    # ตั้งค่าตัวแปรให้ตรงกับโปรเจกต์ของคุณ
    TARGET_TABLE = "WaterQualityData"
    TARGET_NODE = "Node01"
    OUTPUT_FILE = "node01_24h_data.csv"

    export_dynamodb_to_csv(TARGET_TABLE, TARGET_NODE, OUTPUT_FILE)
