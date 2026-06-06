import os
import json
from datetime import datetime, timezone, timedelta
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

from app.models.schemas import (
    NodeID,
    RealTimeRecord,
    FDEIResult,
    ForecastResult,
    HistoricalDataPoint,
    Alert
)

# Load environment configuration
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
DYNAMODB_TABLE_SENSOR = os.getenv("DYNAMODB_TABLE_SENSOR", "SensorReadings")
DYNAMODB_TABLE_FORECAST = os.getenv("DYNAMODB_TABLE_FORECAST", "ForecastResults")
DYNAMODB_TABLE_ALERTS = os.getenv("DYNAMODB_TABLE_ALERTS", "AlertHistory")
DYNAMODB_TABLE_SETTINGS = os.getenv("DYNAMODB_TABLE_SETTINGS", "SystemSettings")

# FDEI Calibration Constants (from ML pipeline metadata.json)
DEFAULT_Y = 2268.177375117046   # Yield Coefficient (ppm·s / mg/L)
DEFAULT_FOG_DAY0 = 2892.0       # mg/L


class DynamoDBRepository:
    def __init__(self):
        # Resource client
        self.dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        self.sensor_table = self.dynamodb.Table(DYNAMODB_TABLE_SENSOR)
        self.forecast_table = self.dynamodb.Table(DYNAMODB_TABLE_FORECAST)
        self.alerts_table = self.dynamodb.Table(DYNAMODB_TABLE_ALERTS)
        self.settings_table = self.dynamodb.Table(DYNAMODB_TABLE_SETTINGS)
        # Local JSON cache fallback for settings when AWS DynamoDB is offline or table does not exist
        self.settings_file = os.path.join(os.path.dirname(__file__), "..", "..", "settings_cache.json")

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

    # ------------------------------------------------------------------
    # Settings (SystemSettings table with local file cache fallback)
    # ------------------------------------------------------------------

    def _save_local_settings(self, data: dict):
        try:
            with open(self.settings_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving local settings cache: {e}")

    def fetch_settings(self) -> dict:
        """Fetch system settings from SystemSettings table.
        Returns local cache/defaults if table is empty or unavailable."""
        defaults = {
            "fog_day0": DEFAULT_FOG_DAY0,
            "fdei_alert_threshold": 80.0
        }
        
        # Load from local cache first if available as baseline
        local_cache = {}
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    local_cache = json.load(f)
            except Exception as e:
                print(f"Error loading local settings cache: {e}")

        current_settings = {**defaults, **local_cache}

        try:
            response = self.settings_table.get_item(
                Key={"setting_id": "global"}
            )
            item = response.get("Item")
            if item:
                db_settings = {
                    "fog_day0": self._convert_decimal(
                        item.get("fog_day0"), DEFAULT_FOG_DAY0
                    ),
                    "fdei_alert_threshold": self._convert_decimal(
                        item.get("fdei_alert_threshold"), 80.0
                    ),
                }
                # Sync DynamoDB settings back to local cache
                self._save_local_settings(db_settings)
                return db_settings
        except Exception as e:
            print(f"Error fetching settings from DynamoDB: {e}. Falling back to local cache.")
        
        return current_settings

    def update_settings(self, fog_day0: float, fdei_alert_threshold: float) -> dict:
        """Write system settings to SystemSettings table & local cache."""
        settings_dict = {
            "fog_day0": fog_day0,
            "fdei_alert_threshold": fdei_alert_threshold,
        }
        # Always write to local cache file first
        self._save_local_settings(settings_dict)

        try:
            self.settings_table.put_item(
                Item={
                    "setting_id": "global",
                    "fog_day0": Decimal(str(fog_day0)),
                    "fdei_alert_threshold": Decimal(str(fdei_alert_threshold)),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as e:
            print(f"Error updating settings in DynamoDB: {e}")
            
        return settings_dict

    # ------------------------------------------------------------------
    # Real-time sensor data
    # ------------------------------------------------------------------

    def fetch_latest_data(self) -> list[RealTimeRecord]:
        records = []
        for node in [NodeID.NODE01, NodeID.NODE02]:
            try:
                response = self.sensor_table.query(
                    KeyConditionExpression=Key("node_id").eq(node.value),
                    ScanIndexForward=False,  # latest first
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

    # ------------------------------------------------------------------
    # FDEI — Fat Degradation Efficiency Index
    # ------------------------------------------------------------------

    def _compute_co2_cumulative(self, items: list) -> float:
        """Compute cumulative CO2 using trapezoidal integration over sorted items.
        Items must already be sorted by timestamp ASC.
        Returns cumulative value in ppm·s."""
        if len(items) < 2:
            return 0.0

        cumulative = 0.0
        for i in range(1, len(items)):
            co2_prev = self._convert_decimal(items[i - 1].get("co2"), 0.0)
            co2_curr = self._convert_decimal(items[i].get("co2"), 0.0)
            ts_prev = self._get_datetime_from_timestamp(items[i - 1].get("timestamp"))
            ts_curr = self._get_datetime_from_timestamp(items[i].get("timestamp"))
            delta_seconds = (ts_curr - ts_prev).total_seconds()
            if delta_seconds > 0:
                cumulative += (co2_prev + co2_curr) / 2.0 * delta_seconds
        return cumulative

    def fetch_fdei_latest(self) -> list[FDEIResult]:
        """Compute current FDEI for each node using last 7 days of sensor data.

        FDEI formula:
            FOG_estimated(t) = FOG_Day0 - CO2_cumulative(t) / Y
            FDEI(t) = (FOG_Day0 - FOG_estimated(t)) / FOG_Day0 * 100
                     = CO2_cumulative(t) / (Y * FOG_Day0) * 100
        """
        settings = self.fetch_settings()
        fog_day0 = settings.get("fog_day0", DEFAULT_FOG_DAY0)

        results = []
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        seven_days_ago_ms = int(seven_days_ago.timestamp() * 1000)

        for node in [NodeID.NODE01, NodeID.NODE02]:
            try:
                # Query last 7 days of sensor data (millisecond timestamp sort key)
                response = self.sensor_table.query(
                    KeyConditionExpression=(
                        Key("node_id").eq(node.value)
                        & Key("timestamp").gte(Decimal(seven_days_ago_ms))
                    ),
                    ScanIndexForward=True  # chronological order for integration
                )
                items = response.get("Items", [])

                # Follow pagination
                while "LastEvaluatedKey" in response:
                    response = self.sensor_table.query(
                        KeyConditionExpression=(
                            Key("node_id").eq(node.value)
                            & Key("timestamp").gte(Decimal(seven_days_ago_ms))
                        ),
                        ScanIndexForward=True,
                        ExclusiveStartKey=response["LastEvaluatedKey"]
                    )
                    items.extend(response.get("Items", []))

                if items:
                    co2_cumulative = self._compute_co2_cumulative(items)
                    fdei = (co2_cumulative / DEFAULT_Y) / fog_day0 * 100.0
                    fdei = max(0.0, min(100.0, fdei))  # clamp 0-100

                    results.append(FDEIResult(
                        node_id=node,
                        fdei=round(fdei, 2),
                        co2_cumulative=round(co2_cumulative, 2),
                        timestamp=self._get_datetime_from_timestamp(
                            items[-1].get("timestamp")
                        )
                    ))
            except Exception as e:
                print(f"Error computing FDEI for {node.value}: {e}")

        # Mock data fallback when DB is unavailable
        if not results:
            print("Database empty or offline. Returning mock FDEI data.")
            results = [
                FDEIResult(
                    node_id=NodeID.NODE01,
                    fdei=42.15,
                    co2_cumulative=2764800.0,  # realistic 7-day cumulative ppm·s
                    timestamp=datetime.now(timezone.utc)
                ),
                FDEIResult(
                    node_id=NodeID.NODE02,
                    fdei=8.73,
                    co2_cumulative=572400.0,
                    timestamp=datetime.now(timezone.utc)
                )
            ]
        return results

    # ------------------------------------------------------------------
    # Forecast
    # ------------------------------------------------------------------

    def fetch_latest_forecast(self) -> list[ForecastResult]:
        forecasts = []
        for node in [NodeID.NODE01, NodeID.NODE02]:
            try:
                response = self.forecast_table.query(
                    KeyConditionExpression=Key("node_id").eq(node.value),
                    ScanIndexForward=False,  # latest first
                    Limit=1
                )
                items = response.get("Items", [])
                if items:
                    item = items[0]
                    forecasts.append(ForecastResult(
                        node_id=node,
                        forecasted_co2=round(
                            self._convert_decimal(item.get("forecasted_co2"), 0.0), 2
                        ),
                        forecasted_fdei=round(
                            self._convert_decimal(item.get("forecasted_fdei"), 0.0), 2
                        ),
                        timestamp=self._get_datetime_from_timestamp(
                            item.get("timestamp")
                        )
                    ))
            except Exception as e:
                print(f"Error querying forecast for {node.value}: {e}")

        if not forecasts:
            # Fallback to mock forecasts with realistic FDEI values
            print("Database empty or offline. Returning mock forecast data.")
            forecasts = [
                ForecastResult(
                    node_id=NodeID.NODE01,
                    forecasted_co2=520.0,
                    forecasted_fdei=55.8,
                    timestamp=datetime.now(timezone.utc)
                ),
                ForecastResult(
                    node_id=NodeID.NODE02,
                    forecasted_co2=390.0,
                    forecasted_fdei=12.4,
                    timestamp=datetime.now(timezone.utc)
                )
            ]
        return forecasts

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------

    def fetch_historical_range(
        self, node_id: NodeID, sensor_type: str,
        start_time: datetime, end_time: datetime
    ) -> list[HistoricalDataPoint]:
        points = []
        unit_map = {
            "ph": "",
            "co2": "ppm",
            "tds": "ppm",
            "turbidity": "NTU",
            "temp": "°C",
            "fdei": "%"
        }
        unit = unit_map.get(sensor_type, "")

        # ------- FDEI virtual sensor: compute dynamically from CO2 -------
        if sensor_type == "fdei":
            return self._fetch_historical_fdei(node_id, start_time, end_time)

        db_field = "temperature" if sensor_type == "temp" else sensor_type

        # Try to query DynamoDB
        try:
            # Convert datetimes to millisecond timestamps since table uses numbers
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)

            # Query
            response = self.sensor_table.query(
                KeyConditionExpression=(
                    Key("node_id").eq(node_id.value)
                    & Key("timestamp").between(Decimal(start_ms), Decimal(end_ms))
                )
            )
            items = response.get("Items", [])

            # Follow pagination if any
            while "LastEvaluatedKey" in response:
                response = self.sensor_table.query(
                    KeyConditionExpression=(
                        Key("node_id").eq(node_id.value)
                        & Key("timestamp").between(Decimal(start_ms), Decimal(end_ms))
                    ),
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

    def _fetch_historical_fdei(
        self, node_id: NodeID, start_time: datetime, end_time: datetime
    ) -> list[HistoricalDataPoint]:
        """Compute FDEI dynamically from historical CO2 data.
        Uses cumulative trapezoidal integration from the experiment start
        (7 days before start_time or earliest available data) up to each point."""
        settings = self.fetch_settings()
        fog_day0 = settings.get("fog_day0", DEFAULT_FOG_DAY0)
        points = []

        try:
            # Fetch from experiment start (7 days before requested start) for full cumulative
            experiment_start = start_time - timedelta(days=7)
            start_ms = int(experiment_start.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)

            response = self.sensor_table.query(
                KeyConditionExpression=(
                    Key("node_id").eq(node_id.value)
                    & Key("timestamp").between(Decimal(start_ms), Decimal(end_ms))
                ),
                ScanIndexForward=True
            )
            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = self.sensor_table.query(
                    KeyConditionExpression=(
                        Key("node_id").eq(node_id.value)
                        & Key("timestamp").between(Decimal(start_ms), Decimal(end_ms))
                    ),
                    ScanIndexForward=True,
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                items.extend(response.get("Items", []))

            if len(items) >= 2:
                cumulative = 0.0
                for i in range(1, len(items)):
                    co2_prev = self._convert_decimal(items[i - 1].get("co2"), 0.0)
                    co2_curr = self._convert_decimal(items[i].get("co2"), 0.0)
                    ts_prev = self._get_datetime_from_timestamp(items[i - 1].get("timestamp"))
                    ts_curr = self._get_datetime_from_timestamp(items[i].get("timestamp"))
                    delta_s = (ts_curr - ts_prev).total_seconds()
                    if delta_s > 0:
                        cumulative += (co2_prev + co2_curr) / 2.0 * delta_s

                    # Only emit points that fall within the requested range
                    if ts_curr >= start_time:
                        fdei = (cumulative / DEFAULT_Y) / fog_day0 * 100.0
                        fdei = max(0.0, min(100.0, fdei))
                        points.append(HistoricalDataPoint(
                            node_id=node_id,
                            sensor_type="fdei",
                            value=round(fdei, 2),
                            unit="%",
                            timestamp=ts_curr
                        ))
        except Exception as e:
            print(f"Error computing historical FDEI: {e}")

        # Mock fallback
        if not points:
            print("No historical FDEI points. Returning mock FDEI history.")
            import random
            random.seed(node_id.value + "fdei")
            current = start_time
            fdei_val = 0.0
            while current <= end_time:
                fdei_val += random.uniform(0.3, 1.2)
                fdei_val = min(fdei_val, 100.0)
                points.append(HistoricalDataPoint(
                    node_id=node_id,
                    sensor_type="fdei",
                    value=round(fdei_val, 2),
                    unit="%",
                    timestamp=current
                ))
                current += timedelta(hours=1)

        return points

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def fetch_alerts(self) -> list[Alert]:
        alerts = []
        try:
            # Alert table uses partition key node_id and sort key timestamp
            for node in [NodeID.NODE01, NodeID.NODE02]:
                response = self.alerts_table.query(
                    KeyConditionExpression=Key("node_id").eq(node.value),
                    ScanIndexForward=False,  # latest first
                    Limit=50
                )
                for item in response.get("Items", []):
                    fdei_val = self._convert_decimal(
                        item.get("fdei_value") or item.get("fdei"), 0.0
                    )
                    alerts.append(Alert(
                        node_id=node,
                        fdei_value=round(fdei_val, 2),
                        alert_type=item.get("alert_type", "ABNORMAL"),
                        timestamp=self._get_datetime_from_timestamp(
                            item.get("timestamp")
                        )
                    ))
        except Exception as e:
            print(f"Error querying alerts: {e}")

        # Sort combined alerts by timestamp DESC
        alerts.sort(key=lambda x: x.timestamp, reverse=True)

        if not alerts:
            # Return mock alerts
            print("Database empty or offline. Returning mock alert data.")
            alerts = [
                Alert(
                    node_id=NodeID.NODE01,
                    fdei_value=78.5,
                    alert_type="PLATEAU",
                    timestamp=datetime.now(timezone.utc) - timedelta(hours=2)
                ),
                Alert(
                    node_id=NodeID.NODE02,
                    fdei_value=5.2,
                    alert_type="ABNORMAL",
                    timestamp=datetime.now(timezone.utc) - timedelta(hours=1)
                )
            ]
        return alerts
