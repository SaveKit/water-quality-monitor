# Machine Learning Pipeline (CNN-GRU-SVR)

โมดูลปัญญาประดิษฐ์สำหรับการประเมินและพยากรณ์ประสิทธิภาพการย่อยสลายไขมัน (FDEI) ของเชื้อแบคทีเรีย *Bacillus spp.* ในถังปฏิกรณ์ชีวภาพแบบปิด (Closed Bioreactor)

---

## 📂 โครงสร้างโฟลเดอร์ (Directory Structure)

```
ml_pipeline/
├── data/                       # ข้อมูลดิบสำหรับการทดสอบ (.csv)
├── models/                     # ไฟล์โมเดลและ Scalers ที่ฝึกสอนเสร็จแล้ว
│   ├── cnn_gru_model.keras     # โครงข่ายหลัก CNN-GRU
│   ├── svr_model.pkl           # โมเดล Regression ชั้นนอก SVR
│   ├── scaler_X.pkl            # ตัวปรับสเกลข้อมูลนำเข้า (Features)
│   ├── scaler_y.pkl            # ตัวปรับสเกลผลลัพธ์ (Target - CO2)
│   └── metadata.json           # เก็บค่าคงที่ Yield Coefficient (Y) และการตั้งค่าอื่นๆ
├── notebooks/                  # Jupyter notebooks สำหรับการทดลองในแล็บ
├── lambda_function/            # 📂 โครงสร้างสำหรับ Deploy บน AWS Lambda (Docker Container)
│   ├── app.py                  # Lambda handler จัดการคิวรีและเขียนข้อมูลลง DynamoDB
│   ├── Dockerfile              # Dockerfile สำหรับ Build ไปยัง AWS ECR
│   └── requirements.txt        # dependencies สำหรับการทำงานบน Lambda
├── src/                        # 📂 โค้ดหลักแบบแยกส่วน (Modular Source Code)
│   ├── preprocess.py           # การกรองค่าว่าง, Winsorization, และ Resampling
│   ├── features.py             # การคำนวณ Cumulative CO2, Yield Y, และ FDEI
│   ├── model.py                # นิยามโครงสร้างชั้น CNN-GRU ของโมเดล Keras
│   ├── train.py                # สคริปต์หลักในการเทรนโมเดลแบบ Local
│   └── inference.py            # ตรรกะการทำนายผลล่วงหน้าแบบ Recursive
├── requirements.txt            # dependencies สำหรับพัฒนาบนเครื่องเครื่อง Local
└── README.md                   # คู่มือแนะนำฉบับนี้
```

---

## 🚀 วิธีการติดตั้งและการใช้งานแบบ Local

### 1. ติดตั้ง Dependencies
เปิด Terminal ในโฟลเดอร์ `ml_pipeline` และติดตั้งชุดไลบรารีด้วยคำสั่ง:
```bash
pip install -r requirements.txt
```

### 2. รันสคริปต์ฝึกสอนโมเดล (Training)
คุณสามารถรันการเทรนโมเดล CNN-GRU-SVR ใหม่จากข้อมูลประวัติย้อนหลังในโฟลเดอร์ `data/` ด้วยคำสั่ง:
```bash
python -m src.train
```
**ผลลัพธ์ที่จะได้รับ:**
- ไฟล์โมเดลที่อัปเดตใหม่ในโฟลเดอร์ `models/`
- กราฟเปรียบเทียบผลการพยากรณ์และค่าความสูญเสีย (Loss) ชื่อ `training_results.png` ใน root โฟลเดอร์ของโปรเจกต์

---

## ☁️ การนำไปใช้งานบน AWS Lambda (Container Deployment)

ระบบนี้ใช้ Docker Container เพื่อให้ AWS Lambda สามารถเรียกใช้งานแบบจำลองโครงข่ายประสาทเทียมที่มีขนาดใหญ่ได้อย่างราบรื่น

### 1. โครงสร้างไฟล์ใน Lambda Container
เมื่อทำการ build อิมเมจด้วย Dockerfile ระบบจะทำการรวบรวมไฟล์:
- โค้ดหลักจาก `src/` ไปไว้ในสภาพแวดล้อมจำลอง
- ไฟล์โมเดลและ scalers ใน `models/` ไปแพ็คไว้เป็นไฟล์เริ่มต้นของฟังก์ชัน
- โค้ด `app.py` เป็น handler หลักเชื่อมต่อกับ DynamoDB `SensorReadings`, `ForecastResults`, และ `AlertHistory`

### 2. ตัวแปรสภาพแวดล้อม (Environment Variables) ที่ต้องตั้งค่าใน Lambda:
- `AWS_REGION`: ภูมิภาคของ AWS เช่น `ap-southeast-1`
- `DYNAMODB_TABLE_SENSOR`: ชื่อตารางเก็บข้อมูลดิบเซนเซอร์ (เช่น `SensorReadings`)
- `DYNAMODB_TABLE_FORECAST`: ชื่อตารางเก็บผลการพยากรณ์ (เช่น `ForecastResults`)
- `DYNAMODB_TABLE_ALERTS`: ชื่อตารางเก็บประวัติการแจ้งเตือน (เช่น `AlertHistory`)
- `TELEGRAM_BOT_TOKEN`: Token สำหรับส่งการแจ้งเตือนทาง Telegram
- `TELEGRAM_CHAT_ID`: ID ของกลุ่มหรือแชทที่ต้องการให้แจ้งเตือน
