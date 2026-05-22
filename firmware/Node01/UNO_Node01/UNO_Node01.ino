#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ==========================================
// ตั้งค่าประจำตัวบอร์ด
// ==========================================
#define NODE_NAME "Node01"
const float CALIBRATION_PH = -4.80;     // ค่าชดเชยสำหรับเซ็นเซอร์ pH
const float CALIBRATION_K_TDS = 0.8330; // K ที่ได้จากการ Calibrate TDS

// ==========================================
// กำหนดขา Hardware สำหรับ Arduino UNO
// ==========================================
const int PIN_PH = A0;                // ขา Analog A0 สำหรับ pH
const int PIN_TDS = A1;               // ขา Analog A1 สำหรับ TDS
const int PIN_TURBIDITY = A2;         // ขา Analog A2 สำหรับ Turbidity
const int PIN_MQ135 = A3;             // ขา Analog A3 สำหรับ MQ-135 (CO2)
const int PIN_TEMP = 2;               // ขา Digital 2 สำหรับ DS18B20

// ==========================================
// ตั้งค่าคงที่สำหรับ MQ-135
// ==========================================
const float RL_VALUE = 1.0;           // ค่า R load บนบอร์ด (1k ohm)
float Ro = 2.685;                      // ค่า Ro ในอากาศสะอาด (ต้อง Calibrate ใหม่ในพื้นที่จริง)

// ==========================================
// ตัวแปร Global สำหรับเก็บค่าเซ็นเซอร์
// ==========================================
float tempValue = 25.0;               // ค่าอุณหภูมิ (ค่าเริ่มต้น 25 องศาเซลเซียส)
float phVoltage = 0.0;
float phValue = 0.0;                  // ค่า pH
float tdsVoltage = 0.0;
float tdsValue = 0.0;                 // ค่า TDS (ppm)
float turbidityVoltage = 0.0;
float turbidityValue = 0.0;           // ค่าความขุ่น (NTU)
float mq135Voltage = 0.0;
float co2Value = 0.0;                 // ค่า CO2 (ppm)

unsigned long lastMillis = 0;         // ตัวแปรจับเวลาสำหรับส่งข้อมูล

// สร้าง Object สำหรับเซ็นเซอร์อุณหภูมิ DS18B20
OneWire oneWire(PIN_TEMP);
DallasTemperature tempSensor(&oneWire);

// ==========================================
// ฟังก์ชัน Median Filter: กรองสัญญาณรบกวนและแก้ไฟค้าง (ADC Ghosting)
// ==========================================
float getStableVoltage(int pin) {
  const int numSamples = 30;          // จำนวนรอบที่ใช้อ่านค่าเพื่อหาค่ามัธยฐาน
  int analogBuffer[numSamples];

  // --- 1. อ่านทิ้ง 1 ครั้ง เพื่อล้างประจุไฟจากขาเซ็นเซอร์ก่อนหน้า (ADC Ghosting) ---
  analogRead(pin);
  delay(15);

  // --- 2. อ่านค่าจากเซ็นเซอร์มาเก็บไว้ใน Array ---
  for (int i = 0; i < numSamples; i++) {
    analogBuffer[i] = analogRead(pin);
    delay(10); 
  }

  // --- 3. เรียงลำดับข้อมูลจากน้อยไปมาก (Bubble Sort) ---
  for (int j = 0; j < numSamples - 1; j++) {
    for (int i = 0; i < numSamples - j - 1; i++) {
      if (analogBuffer[i] > analogBuffer[i + 1]) {
        int temp = analogBuffer[i];
        analogBuffer[i] = analogBuffer[i + 1];
        analogBuffer[i + 1] = temp;
      }
    }
  }

  // --- 4. หาค่ามัธยฐาน (Median) ---
  int medianValue = 0;
  if ((numSamples % 2) != 0) {
    medianValue = analogBuffer[numSamples / 2];
  } else {
    medianValue = (analogBuffer[numSamples / 2] + analogBuffer[(numSamples / 2) - 1]) / 2;
  }
  
  // --- 5. แปลงค่า Analog (0-1023) เป็นแรงดันไฟฟ้า (0-5V) ---
  return (medianValue / 1024.0) * 5.0;
}

// ==========================================
// ฟังก์ชันอ่านค่าและคำนวณเซ็นเซอร์ทั้งหมด
// ==========================================
void readSensors() {
  
  // ---------------------------------------------------------
  // 1. อ่านค่าอุณหภูมิ (DS18B20)
  // ---------------------------------------------------------
  tempSensor.requestTemperatures();
  float currentTemp = tempSensor.getTempCByIndex(0);
  
  // ป้องกันค่า error (-127) ถ้าสายหลุดให้ยึดค่า 25 องศาไว้ชั่วคราวเพื่อให้เซ็นเซอร์อื่นคำนวณต่อได้
  if(currentTemp != DEVICE_DISCONNECTED_C) {
    tempValue = currentTemp;
  }

  // ---------------------------------------------------------
  // 2. อ่านค่า pH
  // ---------------------------------------------------------
  phVoltage = getStableVoltage(PIN_PH);
  phValue = 3.5 * phVoltage + CALIBRATION_PH;

  // ---------------------------------------------------------
  // 3. อ่านค่า TDS (พร้อมชดเชยอุณหภูมิ Real-time)
  // ---------------------------------------------------------
  tdsVoltage = getStableVoltage(PIN_TDS);
  // คำนวณสัมประสิทธิ์ชดเชยอุณหภูมิ
  float compensationCoefficient = 1.0 + 0.02 * (tempValue - 25.0);
  // ปรับแรงดันไฟฟ้ากลับสู่มาตรฐาน 25 องศา
  float compensationVolatge = tdsVoltage / compensationCoefficient;
  // เข้าสมการแปลงค่าโวลต์เป็น rawTDS (ppm)
  float rawTDS = 133.42 * pow(compensationVolatge, 3) - 255.86 * pow(compensationVolatge, 2) + 857.39 * compensationVolatge;
  // คำนวณ TDS จริงโดยใช้ค่าคงที่ K
  tdsValue = (rawTDS * 0.5) * CALIBRATION_K_TDS;


  // ---------------------------------------------------------
  // 4. อ่านค่าความขุ่น (Turbidity)
  // ---------------------------------------------------------
  turbidityVoltage = getStableVoltage(PIN_TURBIDITY);
  
  // ตั้งค่าอ้างอิงของ Hardware จริง (ปรับได้ตามการคาริเบรท)
  float vClearUser = 1.41; // โวลต์สูงสุดที่บอร์ดอ่านได้ตอนน้ำใสสุด
  float vDirtyUser = 0.1;  // โวลต์ตอนน้ำขุ่นสุด (หรือเซ็นเซอร์โดนบัง)
  
  // ตั้งค่าอ้างอิงตามสมการมาตรฐานของเซ็นเซอร์
  float vClearStd = 4.20;  
  float vDirtyStd = 2.50;

  // ปรับระบบ Deadband ให้หักลบจาก vClearUser ไป 0.02V เพื่อป้องกันเลขแกว่งตอนน้ำใส
  if (turbidityVoltage >= (vClearUser - 0.02)) { 
    turbidityValue = 0.0;
  } else {
    // ป้องกันค่าโวลต์ติดลบ
    if (turbidityVoltage < vDirtyUser) turbidityVoltage = vDirtyUser;
    
    // Mapping โวลต์จากฮาร์ดแวร์จำกัด ให้ขยายเต็มสเกลมาตรฐาน (Linear Interpolation)
    float mappedVoltage = (turbidityVoltage - vDirtyUser) * (vClearStd - vDirtyStd) / (vClearUser - vDirtyUser) + vDirtyStd;

    // เข้าสมการคำนวณ NTU มาตรฐาน
    if(mappedVoltage < 2.5){
      turbidityValue = 3000.0; // ขุ่นสุดขีดจำกัด
    } else {
      turbidityValue = -1120.4 * pow(mappedVoltage, 2) + 5742.3 * mappedVoltage - 4352.9;
      if(turbidityValue < 0) turbidityValue = 0.0; // ป้องกันค่าติดลบ
    }
  }

  // ---------------------------------------------------------
  // 5. อ่านค่า CO2 (MQ-135)
  // ---------------------------------------------------------
  mq135Voltage = getStableVoltage(PIN_MQ135);
  
  if(mq135Voltage > 0) { // ป้องกัน division by zero กรณีที่อ่านค่าได้ 0V
    // 1. คำนวณความต้านทานของเซ็นเซอร์ (Rs)
    float Rs = ((5.0 / mq135Voltage) - 1.0) * RL_VALUE;
    // 2. คำนวณอัตราส่วน Rs/Ro
    float ratio = Rs / Ro;
    // 3. ประมาณค่า CO2 (ppm) จากสมการ Curve Fitting ของ MQ-135
    co2Value = 116.6020682 * pow(ratio, -2.769034857);
  } else {
    co2Value = 0.0;
  }
}

// ==========================================
// ฟังก์ชันแพ็กข้อมูลเป็น JSON และส่งออกทาง Serial
// ==========================================
void sendDataToESP32() {
  StaticJsonDocument<256> doc;
  doc["node_id"] = NODE_NAME; 
  doc["ph"] = phValue;
  doc["tds"] = tdsValue;
  doc["turbidity"] = turbidityValue;
  // doc["turbidity_v"] = turbidityVoltage;
  doc["temperature"] = tempValue;
  doc["co2"] = co2Value;

  // แปลงข้อมูลให้อยู่ในรูปแบบบรรทัดเดียว แล้วพ่นออกทางพอร์ต Serial
  serializeJson(doc, Serial);
  Serial.println(); // เคาะบรรทัดใหม่เพื่อให้ ESP32 รู้ว่าจบข้อความ 1 ชุด
}

// ==========================================
// SETUP & LOOP
// ==========================================
void setup() {
  Serial.begin(115200);
  tempSensor.begin(); 
  
  // ปกติ MQ-135 ต้องใช้เวลาวอร์มฮีตเตอร์ แต่เนื่องจาก loop ทำงานทุกๆ 30 วินาที 
  // มันจึงเปรียบเสมือนการวอร์มฮีตเตอร์ไปในตัวอยู่แล้วครับ
}

void loop() {
  // ทำงานแบบ Non-blocking: อ่านค่าและส่งข้อมูลทุกๆ 30 วินาที
  if (millis() - lastMillis > 30000) {
    lastMillis = millis();

    readSensors();          // สั่งอ่านเซ็นเซอร์ทั้งหมด
    sendDataToESP32();      // ส่ง JSON ออกไปหา Gateway
  }
}