from enum import Enum
from datetime import datetime
from pydantic import BaseModel

class NodeID(str, Enum):
    NODE01 = "Node01"
    NODE02 = "Node02"

class WQIStatus(str, Enum):
    GOOD     = "GOOD"      # 0–50
    FAIR     = "FAIR"      # 51–75
    POOR     = "POOR"      # 76–100
    CRITICAL = "CRITICAL"  # >100

class RealTimeRecord(BaseModel):
    node_id: NodeID
    ph: float
    co2: float
    tds: float
    turbidity: float
    temp: float
    timestamp: datetime

class WQIResult(BaseModel):
    node_id: NodeID
    wqi: float
    status: WQIStatus
    status_label: str   # ภาษาไทย เช่น "ดีเยี่ยม / ดี", "พอใช้"
    timestamp: datetime

class ForecastResult(BaseModel):
    node_id: NodeID
    forecasted_wqi: float
    wqi_status: WQIStatus
    recommendation: str  # เช่น "เฝ้าระวัง", "บำบัดขั้นที่สอง"
    timestamp: datetime

class HistoricalDataPoint(BaseModel):
    node_id: NodeID
    sensor_type: str     # "ph" | "co2" | "tds" | "turbidity" | "temp"
    value: float
    unit: str
    timestamp: datetime

class Alert(BaseModel):
    node_id: NodeID
    wqi_value: float
    status: WQIStatus
    recommendation: str
    timestamp: datetime
