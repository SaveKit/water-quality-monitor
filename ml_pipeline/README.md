# Machine Learning Pipeline (CNN-GRU-SVR)

โมดูลปัญญาประดิษฐ์สำหรับการประเมินและพยากรณ์ประสิทธิภาพการย่อยสลายไขมัน (FDEI) ของเชื้อแบคทีเรีย *Bacillus spp.* ในถังปฏิกรณ์ชีวภาพแบบปิด (Closed Bioreactor)

---

## 📂 โครงสร้างโฟลเดอร์ (Directory Structure)

```
ml_pipeline/
├── data/                       # 📂 ข้อมูลสำหรับการทดสอบ (.csv) และคอนฟิกการเทรน
│   ├── node01_new_data_7days.csv               # ข้อมูลจริง Experiment 1 (Node 1 - Sample)
│   ├── node02_new_data_7days.csv               # ข้อมูลจริง Experiment 1 (Node 2 - Control)
│   ├── node01_experiment2_data_7days.csv       # ข้อมูล Experiment 2 ที่เติมเต็มเรียบร้อยแล้ว
│   ├── node02_experiment2_data_7days.csv       # ข้อมูล Experiment 2 Control ที่เติมเต็มเรียบร้อยแล้ว
│   ├── node01_experiment2_data_7days_backup.csv # ข้อมูลดั้งเดิมก่อนเติมเต็ม (มีเพียง 4.5 วันแรก)
│   ├── node02_experiment2_data_7days_backup.csv # ข้อมูลดั้งเดิม Control ก่อนเติมเต็ม
│   ├── node01_experiment3_data_7days.csv       # ข้อมูลจริง Experiment 3 (Node 1 - Sample)
│   ├── node02_experiment3_data_7days.csv       # ข้อมูลจริง Experiment 3 (Node 2 - Control)
│   └── runs_config.json                        # ค่าการวิเคราะห์แล็บ FOG และการตั้งค่าแต่ละ Run
├── models/                     # 📂 ไฟล์โมเดลและ Scalers ที่ฝึกสอนเสร็จแล้ว
│   ├── cnn_gru_model.keras     # โครงข่ายหลัก CNN-GRU
│   ├── svr_model.pkl           # โมเดล Regression ชั้นนอก SVR
│   ├── scaler_X.pkl            # ตัวปรับสเกลข้อมูลนำเข้า (Features)
│   ├── scaler_y.pkl            # ตัวปรับสเกลผลลัพธ์ (Target - CO2)
│   └── metadata.json           # เก็บค่าคงที่ Yield Coefficient (Y), Features, Metrics และการตั้งค่าอื่นๆ
├── notebooks/                  # 📂 Jupyter notebooks สำหรับวิเคราะห์และวิจัย
│   ├── eda_and_preprocessing.ipynb           # การวิเคราะห์ข้อมูลดิบเบื้องต้นและออกแบบวิธี Preprocessing
│   ├── model_evaluation_and_inference.ipynb  # การประเมินผลลัพธ์โมเดลและทดสอบ Recursive Forecast
│   └── model_research_report.ipynb           # รายงานวิจัยเปรียบเทียบสถาปัตยกรรมโมเดลและประสิทธิภาพ
├── lambda_function/            # 📂 โครงสร้างสำหรับ Deploy บน AWS Lambda (Docker Container)
│   ├── app.py                  # Lambda handler จัดการดึงข้อมูลดิบจาก DynamoDB ทำนายผล และบันทึก/แจ้งเตือน
│   ├── Dockerfile              # Dockerfile สำหรับการ Build Image ไปยัง AWS ECR
│   └── requirements.txt        # dependencies สำหรับการทำงานบน AWS Lambda
├── src/                        # 📂 โค้ดหลักแบบแยกส่วน (Modular Source Code)
│   ├── preprocess.py           # การกรองค่าว่าง, Winsorization, และ Resampling ข้อมูล
│   ├── features.py             # การประมวลผล Cumulative CO2, Yield Y, FDEI และจัดเตรียม Dataset แยกราย Run
│   ├── model.py                # นิยามสถาปัตยกรรมโครงข่ายประสาทเทียมผสม CNN-GRU
│   ├── train.py                # สคริปต์หลักในการดึงข้อมูลทุก Run มาเทรนโมเดลแบบ Local
│   ├── inference.py            # ตรรกะการพยากรณ์แบบ Recursive (Autoregressive) และการแปลงค่า FDEI ล่วงหน้า
│   ├── impute_data.py          # สคริปต์เติมเต็มข้อมูลที่สูญหายของ Experiment 2 (ด้วยเทคนิค Blending & Scaling)
│   ├── data_pipeline.py        # Facade สำหรับเชื่อมโยงการทำงานด้าน Preprocess/Features (Backward Compatible)
│   └── fog_cnn_gru_svr_pipeline.py # Facade สำหรับเชื่อมโยงการทำงานด้าน Model/Train (Backward Compatible)
├── reports/                    # 📂 สรุปและรายงานผลการวิเคราะห์
│   ├── graph_summary_th.md     # รายงานเปรียบเทียบคุณภาพของข้อมูลและการพยากรณ์ (ภาษาไทย)
│   ├── figures/                # โฟลเดอร์เก็บรูปภาพกราฟผลลัพธ์
│   └── tables/                 # โฟลเดอร์เก็บตารางผลการประเมิน
├── requirements.txt            # dependencies สำหรับพัฒนาและทดสอบบนเครื่อง Local
└── README.md                   # คู่มือแนะนำฉบับนี้
```

---

## 🚀 วิธีการติดตั้งและการใช้งานแบบ Local

### 1. ติดตั้ง Dependencies
เปิด Terminal ในโฟลเดอร์ `ml_pipeline` และติดตั้งชุดไลบรารีด้วยคำสั่ง:
```bash
pip install -r requirements.txt
```

### 2. การจัดการเติมเต็มข้อมูลดิบ (Data Imputation)
คุณสามารถสั่งรันการเติมเต็มข้อมูลการทดลองรอบที่ 2 (Experiment 2) ที่ขาดหายไปช่วงท้ายให้ครบถ้วน 7 วันได้ด้วยสคริปต์:
```bash
python -m src.impute_data
```
**ผลลัพธ์ที่จะได้รับ:**
- ไฟล์ข้อมูลที่สมบูรณ์ในโฟลเดอร์ `data/` (เช่น `node01_experiment2_data_7days.csv`)
- กราฟเปรียบเทียบก่อน-หลังเติมข้อมูลเพื่อตรวจทานความเนียนเรียบใน `reports/figures/imputation_comparison_node0*.png`

### 3. รันสคริปต์ฝึกสอนโมเดล (Training)
คุณสามารถเริ่มต้นการประมวลผลข้อมูลใหม่ทุกๆ Runs และฝึกสอนโมเดล CNN-GRU-SVR ใหม่ได้ด้วยคำสั่ง:
```bash
python -m src.train
```
**ผลลัพธ์ที่จะได้รับ:**
- ไฟล์น้ำหนักโมเดล, Scalers และ Metadata อัปเดตล่าสุดในโฟลเดอร์ `models/`
- กราฟสรุปความก้าวหน้าการเรียนรู้ (Loss) และการเทียบผลทำนาย `training_results.png` ใน root ของโปรเจกต์

---

## ☁️ การนำไปใช้งานบน AWS Lambda (Container Deployment)

ระบบนี้ใช้งานในรูปแบบ Docker Container เพื่อให้ AWS Lambda สามารถโหลด TensorFlow และจัดเตรียมเครื่องมือพยากรณ์ขนาดใหญ่ได้สะดวก

### ⚠️ คำเตือนสำคัญเรื่อง Build Context
เนื่องจากโฟลเดอร์ `models/` และ `src/` อยู่ในระดับเดียวกับโฟลเดอร์ `lambda_function/` หากคุณใช้คำสั่ง `docker build` ภายในโฟลเดอร์ `lambda_function` โดยตรง **จะส่งผลให้ Build Fail** เนื่องจาก Docker ไม่สามารถเข้าถึงโฟลเดอร์ Parent ด้านนอก context ได้

**วิธีการที่ถูกต้อง:** ต้องสั่งรัน Docker Build จากโฟลเดอร์ **`ml_pipeline/`** (Root ของโมดูลปัญญาประดิษฐ์) เท่านั้น โดยใช้พารามิเตอร์ `-f` ชี้ไปยัง Dockerfile:
```bash
# รันจากโฟลเดอร์ ml_pipeline/ เท่านั้น
docker build -t fog-lambda-inference -f lambda_function/Dockerfile .
```

### 📦 ขั้นตอนการ Push ขึ้น AWS ECR และอัปเดต Lambda
1. **เข้าสู่ระบบ AWS ECR (Authenticate):**
   ```bash
   aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com
   ```
2. **สร้าง/ผูก Tag ของ Image เข้ากับ ECR repository:**
   ```bash
   docker tag fog-lambda-inference:latest <AWS_ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/fog-lambda-inference:latest
   ```
3. **Push Image ไปยัง ECR:**
   ```bash
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/fog-lambda-inference:latest
   ```
4. **อัปเดตโค้ดของฟังก์ชัน Lambda:**
   ```bash
   aws lambda update-function-code --function-name FogDegradationInference --image-uri <AWS_ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/fog-lambda-inference:latest
   ```

### ⚙️ ตัวแปรสภาพแวดล้อม (Environment Variables) ที่ต้องตั้งค่าใน Lambda:
- `AWS_REGION`: ภูมิภาคของ AWS เช่น `ap-southeast-1`
- `DYNAMODB_TABLE_SENSOR`: ชื่อตารางเก็บข้อมูลดิบเซนเซอร์ (ค่าเริ่มต้น: `SensorReadings`)
- `DYNAMODB_TABLE_FORECAST`: ชื่อตารางเก็บผลการพยากรณ์ (ค่าเริ่มต้น: `ForecastResults`)
- `DYNAMODB_TABLE_ALERTS`: ชื่อตารางเก็บประวัติการแจ้งเตือน (ค่าเริ่มต้น: `AlertHistory`)
- `TELEGRAM_BOT_TOKEN`: Token สำหรับส่งการแจ้งเตือนทาง Telegram
- `TELEGRAM_CHAT_ID`: ID ของกลุ่มหรือแชทที่ต้องการให้ส่งข้อความแจ้งเตือน

---

## 🧪 การจำลองและทดสอบการทำงานระดับ Local (Local Testing)

เพื่อตรวจสอบการทำงานของ Lambda Handler (`app.py`) และการเรียกใช้แบบจำลอง AI ก่อนทำการ Deploy ขึ้นระบบคลาวด์จริง คุณสามารถสร้างสคริปต์เพื่อส่ง mock event เข้าหา Lambda ฟังก์ชันแบบจำลองในเครื่องได้ ดังนี้:

สร้างสคริปต์ทดสอบระดับ Local ไว้ที่ `ml_pipeline/test_lambda_local.py`:
```python
import os
import sys

# ตั้งค่า mock environments
os.environ['AWS_REGION'] = 'ap-southeast-1'
os.environ['DYNAMODB_TABLE_SENSOR'] = 'SensorReadings'
os.environ['DYNAMODB_TABLE_FORECAST'] = 'ForecastResults'
os.environ['DYNAMODB_TABLE_ALERTS'] = 'AlertHistory'
# ละเว้นการส่ง Telegram จริง หรือใส่ของจริงเพื่อทดสอบ
os.environ['TELEGRAM_BOT_TOKEN'] = ''
os.environ['TELEGRAM_CHAT_ID'] = ''

# เพิ่มพาธสำหรับรันแบบสคริปต์เดี่ยว
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lambda_function.app import lambda_handler

# ส่ง Event จำลอง
mock_event = {"source": "local-testing"}
result = lambda_handler(mock_event, None)
print("\nผลการทดสอบ:")
print(result)
```
และสั่งรันเพื่อทดสอบโมเดล:
```bash
python test_lambda_local.py
```
*(หมายเหตุ: การรันแบบ Local ต้องกำหนดสิทธิ์ AWS Credentials ของเครื่องให้สามารถดึง/เขียนตาราง DynamoDB จริงได้)*
