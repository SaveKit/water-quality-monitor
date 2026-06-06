# AGENT.md — FOG Degradation Monitoring Dashboard

## Project Overview

ระบบเฝ้าระวังและพยากรณ์ประสิทธิภาพการย่อยสลายไขมัน (Fat, Oil, and Grease — FOG) ของเชื้อแบคทีเรีย *Bacillus spp.* ในถังปฏิกรณ์ชีวภาพแบบปิด (Closed Bioreactor) แบบเรียลไทม์ 
ระบบรับข้อมูลจากเซ็นเซอร์ IoT (MQ-135 CO₂, pH, TDS, Turbidity, Temp) ผ่าน AWS และแสดงผลผ่าน Web Dashboard พร้อมผลพยากรณ์จาก AI Model (CNN-GRU-SVR) 
โดยพยากรณ์ค่า CO₂ ล่วงหน้า 24 ชั่วโมง แล้วนำมาแปลงเป็นดัชนีประสิทธิภาพการย่อยสลายไขมัน (FDEI) ด้วยสมการ Yield Coefficient (Y) ที่ผ่านการคาลิเบรตกับผลวิเคราะห์แล็บ

---

## Repository Structure

```
.
├── backend/                  # FastAPI — deployed on AWS App Runner
│   ├── main.py
│   ├── routers/
│   │   └── data.py           # API endpoints
│   ├── services/
│   │   └── auth_service.py   # AWS Cognito JWT verification
│   ├── repositories/
│   │   └── dynamodb_repo.py
│   ├── models/
│   │   └── schemas.py        # Pydantic models
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                 # Vite + React + TailwindCSS — hosted on AWS S3 + CloudFront
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Overview.jsx
│   │   │   ├── Forecast.jsx
│   │   │   ├── Analytics.jsx
│   │   │   └── AlertHistory.jsx
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── FDEICard.jsx
│   │   │   ├── SensorTable.jsx
│   │   │   ├── TimeSeriesChart.jsx
│   │   │   └── AlertTable.jsx
│   │   ├── api/
│   │   │   └── client.js     # axios instance + JWT interceptor
│   │   └── utils/
│   │       └── fdei.js       # Utility and calculation formulas for FDEI
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── package.json
│
├── ml_pipeline/              # 📂 Machine Learning Pipeline (CNN-GRU-SVR)
│   ├── data/                 # Raw test data .csv files
│   ├── models/               # Saved model weights (.keras, .pkl, metadata.json)
│   ├── notebooks/            # Research and EDA notebooks
│   ├── lambda_function/      # AWS Lambda deployment container files
│   │   ├── app.py            # Lambda inference handler
│   │   ├── Dockerfile        # Lambda deployment Dockerfile
│   │   └── requirements.txt  # Dependencies for Lambda
│   ├── src/                  # Modular source code
│   │   ├── preprocess.py     # Data cleaning, winsorization, resampling
│   │   ├── features.py       # Yield Y calibration, cumulative calculation, sequencing
│   │   ├── model.py          # CNN-GRU structure
│   │   ├── train.py          # Local model training script
│   │   └── inference.py      # Core inference logic
│   └── requirements.txt      # Local dev dependencies
│
├── infra/                    # AWS CDK or Terraform (optional)
└── AGENT.md
```

---

## Tech Stack

| Layer         | Technology                      | Hosting              |
| ------------- | ------------------------------- | -------------------- |
| Frontend      | Vite + React 18 + TailwindCSS   | AWS S3 + CloudFront  |
| Backend API   | FastAPI (Python 3.11+)          | AWS App Runner       |
| Database      | Amazon DynamoDB                 | AWS (ap-southeast-1) |
| Auth          | AWS Cognito (JWT / RS256)       | AWS                  |
| IoT Ingestion | AWS IoT Core → Rules Engine     | AWS                  |
| AI Inference  | AWS Lambda (CNN-GRU-SVR container) | AWS Lambda        |
| Notifications | Telegram Bot API                | via AWS Lambda       |

**AWS Region:** `ap-southeast-1`

---

## Domain Data

### Sensor Nodes (ถังปฏิกรณ์ชีวภาพ)

| Node ID  | Description                                                 | Role    |
| -------- | ----------------------------------------------------------- | ------- |
| `Node01` | **Sample** (เติมจุลินทรีย์ *Bacillus spp.* เพื่อย่อยสลาย FOG) | Active  |
| `Node02` | **Control** (ถังควบคุมกระบวนการย่อยตามธรรมชาติ ไม่เติม Bacillus) | Control |

### Parameters (5 ชนิด)

| Field       | Unit | Sensor Type               | AI Input Feature |
| ----------- | ---- | ------------------------- | :--------------: |
| `ph`        | —    | pH Sensor (Analog)        |        ✅        |
| `co2`       | ppm  | MQ-135 CO₂ Sensor (Analog)|        ✅        |
| `tds`       | ppm  | TDS Sensor (Analog)       |        ✅        |
| `turbidity` | NTU  | Turbidity Sensor (Analog) |        ✅        |
| `temp`      | °C   | DS18B20 (Digital 1-Wire)  |  ❌ (ตัวแปรควบคุม)|

*หมายเหตุ: `temp` บันทึกในฐานข้อมูลเพื่อติดตามสถานะการควบคุมของแล็บ แต่ไม่นำไปใช้เทรนหรือพยากรณ์ด้วยโมเดล AI*

---

## FDEI Formula — Fat Degradation Efficiency Index

FDEI (%) คือ ดัชนีที่แสดงประสิทธิภาพในการย่อยสลายไขมันแบบเรียลไทม์ คำนวณโดยใช้ค่า CO₂ สะสม (Cumulative CO₂) และสัมประสิทธิ์ผลผลิตคาร์บอนไดออกไซด์ต่อการสลายไขมัน (Yield Coefficient: Y) ซึ่งอิงจากผลการทดลองแล็บ FOG

### 1. การคำนวณ Yield Coefficient (Y)
คำนวณในขั้นตอนการ Calibrate กับผลแล็บ ณ สิ้นสุดการทดลองรอบ 7 วัน:
$$Y = \frac{CO_{2,\text{cumulative, 7d}}}{\Delta FOG_{7d}}$$
โดยที่:
- $\Delta FOG_{7d} = FOG_{Day0} - FOG_{Day7}$ (หน่วย mg/L ได้จากห้องแล็บด้วย Gravimetric method)
- $CO_{2,\text{cumulative, 7d}}$ คือ ผลรวมพื้นที่ใต้กราฟของ CO₂ ตลอดระยะเวลา 7 วัน (หน่วย ppm·s)

### 2. การประมาณค่า FOG และคำนวณ FDEI ณ เวลา t
$$FOG_{\text{estimated}}(t) = FOG_{Day0} - \frac{CO_{2,\text{cumulative}}(t)}{Y}$$
$$\text{FDEI}(t) = \frac{FOG_{Day0} - FOG_{\text{estimated}}(t)}{FOG_{Day0}} \times 100\%$$
*โดยค่า FDEI จะถูกจำกัดให้อยู่ในช่วง 0% ถึง 100% เสมอ*

> **Alert Rule:** ส่ง Telegram notification แจ้งเตือนเมื่อแนวโน้มการย่อยสลาย FDEI เกิดการ **ชะลอตัว/หยุดนิ่ง (Plateau)** หรือลดระดับความชันอย่างผิดปกติ (Bacillus activity ตกหรือสภาพแวดล้อมไม่เอื้ออำนวย)

---

## Backend — FastAPI

### Pydantic Models (`models/schemas.py`)

```python
from enum import Enum
from datetime import datetime
from pydantic import BaseModel

class NodeID(str, Enum):
    NODE01 = "Node01" # Sample
    NODE02 = "Node02" # Control

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
    forecasted_co2: float   # ค่า CO2 ที่ AI ทำนาย (ppm)
    forecasted_fdei: float  # ค่า FDEI ที่แปลงแล้ว (%)
    timestamp: datetime

class HistoricalDataPoint(BaseModel):
    node_id: NodeID
    sensor_type: str        # "ph" | "co2" | "tds" | "turbidity" | "temp" | "fdei"
    value: float
    unit: str
    timestamp: datetime

class Alert(BaseModel):
    node_id: NodeID
    fdei_value: float
    alert_type: str         # เช่น "PLATEAU" (การย่อยชะลอตัว) | "ABNORMAL" (พารามิเตอร์เคมีผิดปกติ)
    recommendation: str     # คำแนะนำในการแก้ไข เช่น "ปรับปรุงค่า pH หรือเติมสารอาหารให้แบคทีเรีย"
    timestamp: datetime
```

### API Endpoints (`routers/data.py`)

ทุก endpoint ต้อง **verify JWT** ผ่าน `AuthService.get_current_user(token)` ก่อน

```
GET /api/data/realtime
  → List[RealTimeRecord]
  → ดึงข้อมูล raw sensor ล่าสุดของถังทั้งสอง (5 parameters × 2 nodes)

GET /api/data/fdei
  → List[FDEIResult]
  → ดึง raw data ของการทดลองรอบปัจจุบันเพื่อคำนวณและคืนค่า FDEI และ CO2 สะสมเรียลไทม์

GET /api/data/forecast
  → List[ForecastResult]
  → ดึงผลการพยากรณ์ CO2 และ FDEI ล่วงหน้า 24 ชม. ที่ Lambda บันทึกในตาราง ForecastResults

GET /api/data/historical
  Query params: node_id, sensor_type, start_time (ISO8601), end_time (ISO8601)
  → List[HistoricalDataPoint]

GET /api/data/export/csv
  Query params: node_id, sensor_type, start_time, end_time
  → FileResponse (Content-Type: text/csv)
  → ใช้ logic เดียวกับ /historical แต่ส่งกลับไฟล์ CSV แทน JSON

GET /api/data/alerts
  → List[Alert]
  → ดึงข้อมูลประวัติการแจ้งเตือนความผิดปกติของการย่อยสลาย เรียงตาม timestamp DESC
```

### DynamoDBRepository (`repositories/dynamodb_repo.py`)

**Tables (DynamoDB):**

| Table             | Partition Key | Sort Key                 | Attributes                                       |
| ----------------- | ------------- | ------------------------ | ------------------------------------------------ |
| `SensorReadings`  | `node_id` (S) | `timestamp` (S, ISO8601) | `ph`, `co2`, `tds`, `turbidity`, `temp`          |
| `ForecastResults` | `node_id` (S) | `timestamp` (S)          | `forecasted_co2`, `forecasted_fdei`              |
| `AlertHistory`    | `node_id` (S) | `timestamp` (S)          | `fdei_value`, `alert_type`, `recommendation`     |

**Methods ที่ต้อง implement:**

```python
def fetch_latest_data(self) -> list[RealTimeRecord]
def fetch_fdei_latest(self) -> list[FDEIResult]        # โหลด raw data มาหา CO2 cumulative และ FDEI
def fetch_latest_forecast(self) -> list[ForecastResult]
def fetch_historical_range(
    self, node_id: NodeID, sensor_type: str,
    start_time: datetime, end_time: datetime
) -> list[HistoricalDataPoint]
def fetch_alerts(self) -> list[Alert]
```

### AuthService (`services/auth_service.py`)

- Verify JWT token จาก AWS Cognito
- JWKS endpoint: `https://cognito-idp.ap-southeast-1.amazonaws.com/<USER_POOL_ID>/.well-known/jwks.json`
- คืนค่า `User` object เมื่อ token valid
- Raise `HTTPException(401)` เมื่อ token invalid/expired

---

## Frontend — Vite + React + TailwindCSS

### Thai Font

ใช้ **Sarabun** (Google Fonts) เป็น font หลักของ UI

```html
<!-- index.html -->
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link
  href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap"
  rel="stylesheet"
/>
```

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      fontFamily: {
        sans: ["Sarabun", "sans-serif"],
      },
    },
  },
};
```

### Pages (4 หน้าหลัก)

#### 1. Overview (`/`) — หน้าภาพรวมระบบ

- **FDEI Cards (2 ใบ):** แสดงเปอร์เซ็นต์สะสมของ FDEI ปัจจุบันของ Node01 (Sample) และ Node02 (Control)
  - ค่า FDEI (%) ตัวเลขเด่นชัดแบบ Real-time พร้อมกราฟเข็มบ่งชี้ความก้าวหน้า
  - ป้ายแสดงค่า CO₂ Cumulative (พื้นที่ใต้กราฟสะสม ณ ปัจจุบัน)
- **Sensor Table:** ตารางแสดงผลค่าเซนเซอร์ดิบล่าสุด: Node ID × pH, CO₂ (ppm), TDS (ppm), Turbidity (NTU), Temp (°C)
- Data source: `GET /api/data/realtime` + `GET /api/data/fdei`
- Auto-refresh ทุก 5 นาที (อ้างอิงตาม Sampling Rate ของถังตกตะกอนสะสม)

#### 2. Forecast (`/forecast`) — หน้าผลการพยากรณ์

- **FDEI Forecast Graph:** กราฟทำนายทิศทาง FDEI ล่วงหน้า 24 ชม. ของถังทดลองเปรียบเทียบกับถังควบคุม
  - แสดงผลทำนาย CO₂ ที่ปล่อยและ FDEI ที่จะสูงขึ้น
  - มีแถบสถานะการเติบโตของ Bacillus: (Lag Phase -> Log Phase -> Stationary Phase -> Decline Phase)
- Info bar: "แบบจำลองการทำนาย CNN-GRU-SVR v2.0 — ค่า MAPE: X%"
- Data source: `GET /api/data/forecast`

#### 3. Analytics (`/analytics`) — หน้าวิเคราะห์เชิงลึก

- **Control Panel (Filter):**
  - Date Range Picker (start/end)
  - Multi-select Nodes (Node01-Sample / Node02-Control)
  - Multi-select Parameters (pH, CO₂, TDS, Turbidity, Temp, FDEI)
- **Time-Series Chart:** กราฟย่อยแสดงทิศทางเปรียบเทียบแนวโน้มค่าระหว่างทั้ง 2 ถัง
- **Export Button:** "Export to CSV" ดึงไฟล์ตารางพารามิเตอร์ดิบผ่าน `/api/data/export/csv`
- Data source: `GET /api/data/historical`

#### 4. Alert History (`/alerts`) — หน้าประวัติการแจ้งเตือน

- ตารางรายการแจ้งเตือนเรียงตาม timestamp ล่าสุด (DESC)
- Columns: Timestamp | Node ID | FDEI Value | Alert Type | Recommendation
- แสดงประวัติเหตุการณ์เมื่อกิจกรรมของ Bacillus ชะงักงัน (Plateau) หรือสารเคมีเป็นพิษต่อแบคทีเรีย
- Data source: `GET /api/data/alerts`

### FDEI Utility (`utils/fdei.js`)

```javascript
// sensor_type values ที่ใช้ใน API
export const SENSOR_TYPES = [
  { key: "ph", label: "pH", unit: "" },
  { key: "co2", label: "CO₂ (MQ-135)", unit: "ppm" },
  { key: "tds", label: "TDS", unit: "ppm" },
  { key: "turbidity", label: "Turbidity", unit: "NTU" },
  { key: "temp", label: "อุณหภูมิ (ควบคุม)", unit: "°C" },
  { key: "fdei", label: "FDEI (ประสิทธิภาพการย่อย)", unit: "%" },
];
```

---

## Auth Flow

1. ผู้ใช้กรอก username/password ที่หน้า Login
2. Frontend เรียก AWS Cognito `InitiateAuth` → ได้ `IdToken` (JWT)
3. เก็บ token ใน React context / sessionStorage
4. `client.js` interceptor แนบ `Authorization: Bearer <token>` ทุก API call
5. Backend `AuthService.get_current_user(token)` verify กับ Cognito JWKS
6. Token หมดอายุ → 401 → redirect กลับหน้า Login

---

## Development Order (แนะนำ)

```
1. ปรับปรุงโครงสร้างโฟลเดอร์ของ ml_pipeline เป็นแบบ Modular
   └─ แยก logic preprocess, features, model, train, inference

2. เขียน AWS Lambda code และสร้าง Dockerfile สำหรับ deployment

3. Backend skeleton + mock data (สำหรับ FDEI และ Forecast CO2)

4. พัฒนาหน้าจอ Overview และหน้า Forecast บน Frontend

5. เชื่อมต่อ Backend API กับ DynamoDB Repository จริง

6. พัฒนาหน้า Analytics (Filter + Multi-series chart) และหน้า Alerts

7. รวมระบบ Cognito Auth และทดสอบ Deployment บน AWS
```

---

## Environment Variables

### Backend (`.env`)

```env
AWS_REGION=ap-southeast-1
DYNAMODB_TABLE_SENSOR=SensorReadings
DYNAMODB_TABLE_FORECAST=ForecastResults
DYNAMODB_TABLE_ALERTS=AlertHistory
COGNITO_USER_POOL_ID=ap-southeast-1_XXXXXXX
COGNITO_APP_CLIENT_ID=XXXXXXXXXXXXXXXX
```

### Frontend (`.env`)

```env
VITE_API_BASE_URL=https://api.your-domain.com
VITE_COGNITO_REGION=ap-southeast-1
VITE_COGNITO_USER_POOL_ID=ap-southeast-1_XXXXXXX
VITE_COGNITO_APP_CLIENT_ID=XXXXXXXXXXXXXXXX
```

---

## Key Constraints & Decisions

- **ไม่มี write endpoint ใน FastAPI** — ข้อมูลส่งเข้า DynamoDB ผ่าน AWS IoT Core เท่านั้น
- **FDEI คำนวณใน backend/lambda** บนหลักการสะสมพลังงาน (Cumulative CO2) และโมเดล AI พยากรณ์ CO2 เท่านั้น
- **การวิเคราะห์การย่อยสลายไขมันแบบปิด** จะทำเฉพาะ Node01 (Sample) เท่านั้น ส่วน Node02 (Control) จะใช้สังเกตการไม่ย่อยสลายเพื่อยืนยันพฤติกรรม
- **Sampling rate** ของ ESP32 คือ **ทุก 30 วินาที** สำหรับการทดสอบ 7 วัน แต่อาจดาวน์แซมพลิงเหลือ **5 นาที** ในส่วนประมวลผลโมเดลและ Dashboard
- **Thai Font:** ใช้ Sarabun (Google Fonts) ทั้งโปรเจกต์
- **ภาษา:** UI ภาษาไทย, code และ API เป็นภาษาอังกฤษ
- **คำศัพท์เชิงโดเมน (Naming Convention):** ให้ใช้คำว่า **Batch** แทนคำว่า "Run" เพื่อระบุรอบของการทดลอง เช่น `batch1`, `batch2`, `batch3` (แทน `run1`, `run2`, `run3`) ในทุกส่วนงาน ทั้งชื่อไฟล์คอนฟิก ตัวแปร และโครงสร้างข้อมูลของ ML Pipeline เพื่อความสอดคล้องเชิงความหมายเชิงวิทยาศาสตร์


---

## Testing Checklist

### Backend
- [ ] `GET /api/data/realtime` — คืนค่า 2 records (Node01 = Sample, Node02 = Control) รวมค่า `co2`
- [ ] `GET /api/data/fdei` — คืนค่า FDEI (0-100%) และ Cumulative CO2 ที่คำนวณได้ถูกต้อง
- [ ] `GET /api/data/forecast` — คืนค่าพยากรณ์ CO2 ล่วงหน้า 24 ชม. และค่า FDEI พยากรณ์
- [ ] `GET /api/data/historical` — กรองข้อมูลตาม node, sensor และช่วงเวลาทดลองได้ถูกต้อง
- [ ] `GET /api/data/alerts` — คืนรายการประวัติการหยุดทำงานหรือการชะลอตัวของการย่อย

### Frontend
- [ ] Overview หน้าจอแสดงผล FDEI (%) ของ Node01 และ Node02 แยกกันอย่างชัดเจน
- [ ] หน้า Forecast แสดงผลกราฟทำนายอนาคต 24 ชั่วโมง
- [ ] Export CSV สามารถดาวน์โหลดข้อมูล raw ได้จริง
- [ ] หน้า Login เชื่อมต่อและกรองสิทธิ์ด้วย Cognito สำเร็จ
- [ ] ระบบแจ้งเตือนแสดงประเภทความผิดปกติ (Plateau/Abnormal) ได้ถูกต้อง
