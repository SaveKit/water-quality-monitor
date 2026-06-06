from enum import Enum
from datetime import datetime
from pydantic import BaseModel

class NodeID(str, Enum):
    NODE01 = "Node01"  # Sample (Bacillus spp.)
    NODE02 = "Node02"  # Control

class RealTimeRecord(BaseModel):
    node_id: NodeID
    ph: float
    co2: float
    tds: float
    turbidity: float
    temp: float
    timestamp: datetime

class FDEIResult(BaseModel):
    node_id: NodeID
    fdei: float             # 0 - 100%
    co2_cumulative: float   # ppm·s
    timestamp: datetime

class ForecastResult(BaseModel):
    node_id: NodeID
    forecasted_co2: float   # predicted CO2 (ppm)
    forecasted_fdei: float  # predicted FDEI (%)
    timestamp: datetime

class HistoricalDataPoint(BaseModel):
    node_id: NodeID
    sensor_type: str     # "ph" | "co2" | "tds" | "turbidity" | "temp" | "fdei"
    value: float
    unit: str
    timestamp: datetime

class Alert(BaseModel):
    node_id: NodeID
    fdei_value: float
    alert_type: str         # "PLATEAU" | "TARGET_REACHED" | "ABNORMAL"
    timestamp: datetime

class SystemSettings(BaseModel):
    fog_day0: float = 2892.0
    fdei_alert_threshold: float = 80.0
