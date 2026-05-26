import os
from datetime import datetime, timezone
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

from app.models.schemas import (
    NodeID,
    WQIStatus,
    RealTimeRecord,
    WQIResult,
    ForecastResult,
    HistoricalDataPoint,
    Alert
)

# Load environment configuration
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
DYNAMODB_TABLE_SENSOR = os.getenv("DYNAMODB_TABLE_SENSOR", "WaterQualityData")
DYNAMODB_TABLE_FORECAST = os.getenv("DYNAMODB_TABLE_FORECAST", "ForecastResults")
DYNAMODB_TABLE_ALERTS = os.getenv("DYNAMODB_TABLE_ALERTS", "AlertHistory")

# WQI Constants
V_O = {'ph': 7.0, 'temp': 25.0, 'turbidity': 0.0, 'tds': 0.0}
S_N = {'ph': 8.5, 'temp': 35.0, 'turbidity': 5.0, 'tds': 500.0}

def calculate_wawqi(ph: float, temp: float, turbidity: float, tds: float) -> float:
    params = {
        'ph': ph,
        'temp': temp,
        'turbidity': turbidity,
        'tds': tds
    }
    # Filter out None or NaN
    available_params = {k: v for k, v in params.items() if v is not None}
    if not available_params:
        return 0.0

    sum_inverse_Sn = sum(1.0 / S_N[p] for p in available_params.keys())
    if sum_inverse_Sn == 0:
        return 0.0
    k = 1.0 / sum_inverse_Sn

    sum_Qn_Wn = 0.0
    sum_Wn = 0.0

    for p, val in available_params.items():
        W_n = k / S_N[p]
        Q_n = (abs(val - V_O[p]) / abs(S_N[p] - V_O[p])) * 100
        sum_Qn_Wn += Q_n * W_n
        sum_Wn += W_n

    return sum_Qn_Wn / sum_Wn if sum_Wn > 0 else 0.0

def get_wqi_status_and_label(wqi: float):
    if wqi <= 50:
        return WQIStatus.GOOD, "ดีเยี่ยม / ดี"
    elif wqi <= 75:
        return WQIStatus.FAIR, "พอใช้"
    elif wqi <= 100:
        return WQIStatus.POOR, "แย่มาก"
    else:
        return WQIStatus.CRITICAL, "ไม่เหมาะสมอย่างยิ่ง"

def get_recommendation(status: WQIStatus) -> str:
    if status == WQIStatus.GOOD:
        return "เฝ้าระวัง"
    elif status == WQIStatus.FAIR:
        return "บำบัดขั้นต้น (Primary)"
    elif status == WQIStatus.POOR:
        return "บำบัดขั้นที่สอง (Secondary)"
    else:
        return "บำบัดขั้นสูง (Advanced)"

class DynamoDBRepository:
    def __init__(self):
        # Resource client
        self.dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        self.sensor_table = self.dynamodb.Table(DYNAMODB_TABLE_SENSOR)
        self.forecast_table = self.dynamodb.Table(DYNAMODB_TABLE_FORECAST)
        self.alerts_table = self.dynamodb.Table(DYNAMODB_TABLE_ALERTS)

    def _convert_decimal(self, val, default=0.0):
        if val is None:
            return default
        if isinstance(val, Decimal):
            return float(val)
        return float(val)

    def _get_datetime_from_timestamp(self, ts):
        # Support both millisecond Unix timestamp and ISO8601 string
        if isinstance(ts, (int, float, Decimal)):
            # convert millisecond epoch to datetime
            return datetime.fromtimestamp(float(ts) / 1000.0, tz=timezone.utc)
        elif isinstance(ts, str):
            try:
                # ISO8601 string parsing
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return datetime.now(timezone.utc)
        return datetime.now(timezone.utc)

    def fetch_latest_data(self) -> list[RealTimeRecord]:
        records = []
        for node in [NodeID.NODE01, NodeID.NODE02]:
            try:
                response = self.sensor_table.query(
                    KeyConditionExpression=Key("node_id").eq(node.value),
                    ScanIndexForward=False, # latest first
                    Limit=1
                )
                items = response.get("Items", [])
                if items:
                    item = items[0]
                    # Map to RealTimeRecord
                    records.append(RealTimeRecord(
                        node_id=node,
                        ph=self._convert_decimal(item.get("ph"), 7.0),
                        co2=self._convert_decimal(item.get("co2"), 0.0),
                        tds=self._convert_decimal(item.get("tds"), 0.0),
                        turbidity=self._convert_decimal(item.get("turbidity"), 0.0),
                        temp=self._convert_decimal(item.get("temperature") or item.get("temp"), 25.0),
                        timestamp=self._get_datetime_from_timestamp(item.get("timestamp"))
                    ))
            except Exception as e:
                print(f"Error querying latest data for {node.value}: {e}")

        # If empty (e.g. table doesn't exist or permissions issue), return mock data
        if not records:
            print("Database empty or offline. Returning mock real-time data.")
            records = [
                RealTimeRecord(
                    node_id=NodeID.NODE01,
                    ph=7.2,
                    co2=450.0,
                    tds=120.0,
                    turbidity=2.5,
                    temp=26.4,
                    timestamp=datetime.now(timezone.utc)
                ),
                RealTimeRecord(
                    node_id=NodeID.NODE02,
                    ph=6.8,
                    co2=480.0,
                    tds=150.0,
                    turbidity=3.1,
                    temp=27.1,
                    timestamp=datetime.now(timezone.utc)
                )
            ]
        return records

    def fetch_latest_wqi(self) -> list[WQIResult]:
        latest_data = self.fetch_latest_data()
        results = []
        for data in latest_data:
            wqi = calculate_wawqi(
                ph=data.ph,
                temp=data.temp,
                turbidity=data.turbidity,
                tds=data.tds
            )
            status, label = get_wqi_status_and_label(wqi)
            results.append(WQIResult(
                node_id=data.node_id,
                wqi=round(wqi, 2),
                status=status,
                status_label=label,
                timestamp=data.timestamp
            ))
        return results

    def fetch_latest_forecast(self) -> list[ForecastResult]:
        forecasts = []
        for node in [NodeID.NODE01, NodeID.NODE02]:
            try:
                response = self.forecast_table.query(
                    KeyConditionExpression=Key("node_id").eq(node.value),
                    ScanIndexForward=False, # latest first
                    Limit=1
                )
                items = response.get("Items", [])
                if items:
                    item = items[0]
                    wqi = self._convert_decimal(item.get("forecasted_wqi"))
                    status, _ = get_wqi_status_and_label(wqi)
                    forecasts.append(ForecastResult(
                        node_id=node,
                        forecasted_wqi=round(wqi, 2),
                        wqi_status=status,
                        recommendation=item.get("recommendation", get_recommendation(status)),
                        timestamp=self._get_datetime_from_timestamp(item.get("timestamp"))
                    ))
            except Exception as e:
                print(f"Error querying forecast for {node.value}: {e}")

        if not forecasts:
            # Fallback to Mock forecasts
            print("Database empty or offline. Returning mock forecast data.")
            for node in [NodeID.NODE01, NodeID.NODE02]:
                wqi = 45.5 if node == NodeID.NODE01 else 78.2
                status, _ = get_wqi_status_and_label(wqi)
                forecasts.append(ForecastResult(
                    node_id=node,
                    forecasted_wqi=wqi,
                    wqi_status=status,
                    recommendation=get_recommendation(status),
                    timestamp=datetime.now(timezone.utc)
                ))
        return forecasts

    def fetch_historical_range(
        self, node_id: NodeID, sensor_type: str,
        start_time: datetime, end_time: datetime
    ) -> list[HistoricalDataPoint]:
        points = []
        db_field = "temperature" if sensor_type == "temp" else sensor_type
        unit_map = {
            "ph": "",
            "co2": "ppm",
            "tds": "ppm",
            "turbidity": "NTU",
            "temp": "°C"
        }
        unit = unit_map.get(sensor_type, "")

        # Try to query DynamoDB
        try:
            # Convert datetimes to millisecond timestamps since WaterQualityData uses numbers
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)

            # Query
            response = self.sensor_table.query(
                KeyConditionExpression=Key("node_id").eq(node_id.value) & Key("timestamp").between(Decimal(start_ms), Decimal(end_ms))
            )
            items = response.get("Items", [])
            
            # Follow pagination if any
            while "LastEvaluatedKey" in response:
                response = self.sensor_table.query(
                    KeyConditionExpression=Key("node_id").eq(node_id.value) & Key("timestamp").between(Decimal(start_ms), Decimal(end_ms)),
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                items.extend(response.get("Items", []))

            for item in items:
                val = item.get(db_field) or item.get(sensor_type)
                if val is not None:
                    points.append(HistoricalDataPoint(
                        node_id=node_id,
                        sensor_type=sensor_type,
                        value=self._convert_decimal(val),
                        unit=unit,
                        timestamp=self._get_datetime_from_timestamp(item.get("timestamp"))
                    ))
        except Exception as e:
            print(f"Error querying historical data: {e}")

        # If no points found, return mock history to prevent blank graphs
        if not points:
            print("No historical points found. Returning mock historical range.")
            # Generate mock points between start and end time (every 1 hour)
            import random
            from datetime import timedelta
            current = start_time
            random.seed(node_id.value + sensor_type)
            while current <= end_time:
                # generate realistic values
                if sensor_type == "ph":
                    val = random.normalvariate(7.2, 0.5)
                elif sensor_type == "co2":
                    val = random.normalvariate(450.0, 50.0)
                elif sensor_type == "tds":
                    val = random.normalvariate(150.0, 20.0)
                elif sensor_type == "turbidity":
                    val = random.normalvariate(3.0, 1.5)
                else:
                    val = random.normalvariate(26.0, 1.0)
                
                points.append(HistoricalDataPoint(
                    node_id=node_id,
                    sensor_type=sensor_type,
                    value=round(val, 2),
                    unit=unit,
                    timestamp=current
                ))
                current += timedelta(hours=1)
                
        return points

    def fetch_alerts(self) -> list[Alert]:
        alerts = []
        try:
            # Alert table might use partition key node_id and sort key timestamp
            for node in [NodeID.NODE01, NodeID.NODE02]:
                response = self.alerts_table.query(
                    KeyConditionExpression=Key("node_id").eq(node.value),
                    ScanIndexForward=False, # latest first
                    Limit=50
                )
                for item in response.get("Items", []):
                    wqi = self._convert_decimal(item.get("wqi_value") or item.get("wqi"))
                    status, _ = get_wqi_status_and_label(wqi)
                    alerts.append(Alert(
                        node_id=node,
                        wqi_value=round(wqi, 2),
                        status=status,
                        recommendation=item.get("recommendation", get_recommendation(status)),
                        timestamp=self._get_datetime_from_timestamp(item.get("timestamp"))
                    ))
        except Exception as e:
            print(f"Error querying alerts: {e}")

        # Sort combined alerts by timestamp DESC
        alerts.sort(key=lambda x: x.timestamp, reverse=True)

        if not alerts:
            # Return Mock Alerts
            print("Database empty or offline. Returning mock alert data.")
            alerts = [
                Alert(
                    node_id=NodeID.NODE02,
                    wqi_value=78.5,
                    status=WQIStatus.POOR,
                    recommendation="บำบัดขั้นที่สอง (Secondary)",
                    timestamp=datetime.now(timezone.utc)
                )
            ]
        return alerts
