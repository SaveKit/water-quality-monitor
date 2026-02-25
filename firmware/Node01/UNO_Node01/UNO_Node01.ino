#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ==========================================
// 📌 ตั้งค่าประจำตัวบอร์ด
// ==========================================
#define NODE_NAME "Node01"
const float CALIBRATION_PH = 0.0; // ค่าสอบเทียบ pH

// ==========================================
// 📌 กำหนดขา Hardware สำหรับ Arduino UNO
// ==========================================
// เปลี่ยนมาใช้ขา Analog และ Digital มาตรฐานของ UNO
const int PIN_PH = A0;          // ขา Analog A0 สำหรับ pH
const int PIN_TDS = A1;         // ขา Analog A1 สำหรับ TDS
const int PIN_TURBIDITY = A2;   // ขา Analog A2 สำหรับ Turbidity
const int PIN_TEMP = 2;         // ขา Digital 2 สำหรับ DS18B20

// ==========================================
// ตัวแปร Global สำหรับเก็บค่าเซ็นเซอร์
// ==========================================
float phValue = 0.0;
float phVoltage = 0.0;
float tdsValue = 0.0;
float tdsVoltage = 0.0;
float turbidityValue = 0.0;
float turbidityVoltage = 0.0;
float tempValue = 0.0;

unsigned long lastMillis = 0;

// สร้าง Object สำหรับเซ็นเซอร์อุณหภูมิ
OneWire oneWire(PIN_TEMP);
DallasTemperature tempSensor(&oneWire);

// ==========================================
// ฟังก์ชันตัวช่วยอ่านค่า Analog ให้นิ่งขึ้น
// ==========================================
float getStableVoltage(int pin) {
  unsigned long adcSum = 0;
  int samples = 20; 
  for (int i = 0; i < samples; i++) {
    adcSum += analogRead(pin);
    delay(10); 
  }
  float avgADC = (float)adcSum / samples;
  
  // ⚠️ จุดสำคัญที่เปลี่ยนไป:
  // Arduino UNO ใช้ ADC 10-bit (อ่านค่าได้ 0-1023) และใช้ไฟอ้างอิง 5V
  return (avgADC / 1023.0) * 5.0; 
}

// ==========================================
// ฟังก์ชันอ่านค่าและคำนวณเซ็นเซอร์ทั้งหมด
// ==========================================
void readSensors() {
  // 1. อ่านค่าอุณหภูมิ (DS18B20)
  tempSensor.requestTemperatures(); 
  tempValue = tempSensor.getTempCByIndex(0);

  // 2. อ่านค่า pH (ไม่ต้องคำนวณชดเชยตัวต้านทาน R1, R2 แล้ว!)
  phVoltage = getStableVoltage(PIN_PH);
  phValue = 3.5 * phVoltage + CALIBRATION_PH;

  // 3. อ่านค่า TDS (ชดเชยอุณหภูมิ)
  tdsVoltage = getStableVoltage(PIN_TDS);
  float compensationCoefficient = 1.0 + 0.02 * (tempValue - 25.0);
  float compensationVolatge = tdsVoltage / compensationCoefficient;
  tdsValue = (133.42 * pow(compensationVolatge, 3) - 255.86 * pow(compensationVolatge, 2) + 857.39 * compensationVolatge) * 0.5;

  // 4. อ่านค่าความขุ่น (Turbidity)
  turbidityVoltage = getStableVoltage(PIN_TURBIDITY);
  if(turbidityVoltage < 2.5){
    turbidityValue = 3000;
  } else {
    turbidityValue = -1120.4 * pow(turbidityVoltage, 2) + 5742.3 * turbidityVoltage - 4352.9;
    if(turbidityValue < 0) turbidityValue = 0;
  }
}

// ==========================================
// ฟังก์ชันแพ็กข้อมูลเป็น JSON และส่งออกทาง Serial
// ==========================================
void sendDataToESP32() {
  StaticJsonDocument<200> doc;
  doc["node_id"] = NODE_NAME; 
  doc["ph"] = phValue;
  doc["tds"] = tdsValue;
  doc["turbidity"] = turbidityValue;
  doc["temperature"] = tempValue;
  
  // แปลงข้อมูลให้อยู่ในรูปแบบบรรทัดเดียว แล้วพ่นออกทางพอร์ต Serial
  serializeJson(doc, Serial);
  Serial.println(); // เคาะบรรทัดใหม่เพื่อให้ ESP32 รู้ว่าจบข้อความ 1 ชุด
}

// ==========================================
// SETUP & LOOP
// ==========================================
void setup() {
  // ตั้งความเร็วการสื่อสารให้ตรงกับ ESP32
  Serial.begin(115200); 
  tempSensor.begin(); 
}

void loop() {
  // อ่านค่าและส่งข้อมูลทุกๆ 10 วินาที
  if (millis() - lastMillis > 10000) {
    lastMillis = millis();
    readSensors();
    sendDataToESP32();
  }
}