import boto3
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

dynamodb = boto3.client("dynamodb", region_name="ap-southeast-1")
db_resource = boto3.resource("dynamodb", region_name="ap-southeast-1")

def table_exists(table_name):
    try:
        dynamodb.describe_table(TableName=table_name)
        return True
    except dynamodb.exceptions.ResourceNotFoundException:
        return False
    except Exception as e:
        print(f"Error checking table {table_name}: {e}")
        return False

def create_table(table_name):
    print(f"Creating table {table_name}...")
    try:
        table = db_resource.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "node_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "node_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        print(f"Waiting for table {table_name} to be active...")
        table.meta.client.get_waiter("table_exists").wait(TableName=table_name)
        print(f"Table {table_name} is active!")
    except Exception as e:
        print(f"Error creating table {table_name}: {e}")

def seed_forecast_data():
    table = db_resource.Table("ForecastResults")
    now = datetime.now(timezone.utc)
    
    # Check if there are already items
    try:
        count = table.scan(Limit=1).get("Count", 0)
        if count > 0:
            print("ForecastResults table already has data. Skipping seeding.")
            return
    except Exception:
        pass

    print("Seeding ForecastResults...")
    # Add forecast data points for the next 24 hours (simulated)
    # Using Decimal for float values
    forecasts = [
        {
            "node_id": "Node01",
            "timestamp": now.isoformat(),
            "forecasted_wqi": Decimal("42.8"), # GOOD
            "wqi_status": "GOOD",
            "recommendation": "เฝ้าระวัง"
        },
        {
            "node_id": "Node02",
            "timestamp": now.isoformat(),
            "forecasted_wqi": Decimal("79.5"), # POOR -> Needs Alert
            "wqi_status": "POOR",
            "recommendation": "บำบัดขั้นที่สอง (Secondary)"
        }
    ]
    for item in forecasts:
        table.put_item(Item=item)
    print("ForecastResults seeded successfully!")

def seed_alert_data():
    table = db_resource.Table("AlertHistory")
    now = datetime.now(timezone.utc)
    
    # Check if there are already items
    try:
        count = table.scan(Limit=1).get("Count", 0)
        if count > 0:
            print("AlertHistory table already has data. Skipping seeding.")
            return
    except Exception:
        pass

    print("Seeding AlertHistory...")
    # Insert multiple historical alerts
    alerts = [
        {
            "node_id": "Node02",
            "timestamp": (now - timedelta(hours=2)).isoformat(),
            "wqi_value": Decimal("78.5"),
            "status": "POOR",
            "recommendation": "บำบัดขั้นที่สอง (Secondary)"
        },
        {
            "node_id": "Node02",
            "timestamp": (now - timedelta(hours=6)).isoformat(),
            "wqi_value": Decimal("81.2"),
            "status": "POOR",
            "recommendation": "บำบัดขั้นที่สอง (Secondary)"
        },
        {
            "node_id": "Node01",
            "timestamp": (now - timedelta(days=1, hours=3)).isoformat(),
            "wqi_value": Decimal("115.0"),
            "status": "CRITICAL",
            "recommendation": "บำบัดขั้นสูง (Advanced)"
        },
        {
            "node_id": "Node02",
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "wqi_value": Decimal("52.3"),
            "status": "FAIR",
            "recommendation": "บำบัดขั้นต้น (Primary)"
        }
    ]
    for item in alerts:
        table.put_item(Item=item)
    print("AlertHistory seeded successfully!")

if __name__ == "__main__":
    tables = ["ForecastResults", "AlertHistory"]
    for table_name in tables:
        if not table_exists(table_name):
            create_table(table_name)
        else:
            print(f"Table {table_name} already exists.")
            
    # Seed data
    try:
        seed_forecast_data()
        seed_alert_data()
    except Exception as e:
        print(f"Error seeding data: {e}")
    print("Database setup script finished.")
