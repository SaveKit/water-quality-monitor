#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <MQTTClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include "secrets.h"

// ==========================================
// 📌 ตั้งค่าประจำตัวบอร์ด
// ==========================================
#define NODE_NAME "Node01"
const float CALIBRATION_PH = 0.0;

// ==========================================
// กำหนด Hardware
// ==========================================
const int PIN_PH = 36;          // ขา Analog สำหรับ pH (VP)
const int PIN_TDS = 39;         // ขา Analog สำหรับ TDS (VN)
const int PIN_TURBIDITY = 34;   // ขา Analog สำหรับ Turbidity
const int PIN_TEMP = 4;         // ขา Digital สำหรับ DS18B20

// ตัวต้านทานสำหรับ Voltage Divider ของ pH
const float R1 = 10000.0; // 10k
const float R2 = 20000.0; // 20k (10k+10k)

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

// สร้าง Client และ Object สำหรับเซ็นเซอร์
WiFiClientSecure net = WiFiClientSecure(); 
MQTTClient client = MQTTClient(512);       
OneWire oneWire(PIN_TEMP);
DallasTemperature tempSensor(&oneWire);

// ==========================================
// ฟังก์ชันเชื่อมต่อ Wi-Fi
// ==========================================
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return; 

  Serial.print("Connecting to Wi-Fi");
  WiFi.begin(SECRET_SSID, SECRET_PASS); 
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to Wi-Fi!"); 
}

// ==========================================
// ฟังก์ชันตั้งเวลาจาก Internet (NTP)
// ==========================================
void syncTime() {
  Serial.print("Setting time using SNTP");
  configTime(0, 0, "pool.ntp.org", "time.nist.gov"); 
  time_t now = time(nullptr);
  while (now < 1000000000L) { 
    delay(500);
    Serial.print(".");
    now = time(nullptr);
  }
  Serial.println("\nTime synchronized!"); 
}

// ==========================================
// ฟังก์ชันเชื่อมต่อ AWS IoT
// ==========================================
void connectAWS() {
  if (client.connected()) return; 

  Serial.print("Connecting to AWS IoT");
  // ใช้ NODE_NAME เป็น Client ID เพื่อไม่ให้ซ้ำกันตอนต่อ AWS
  while (!client.connect(NODE_NAME)) { 
    Serial.print(".");
    delay(1000);
  }
  Serial.println("\nConnected to AWS IoT!"); 
}

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
  return (avgADC / 4095.0) * 3.3; // คืนค่าเป็น Voltage ของ ESP32
}

// ==========================================
// ฟังก์ชันอ่านค่าและคำนวณเซ็นเซอร์ทั้งหมด
// ==========================================
void readSensors() {
  Serial.println("--- Reading Sensors ---");

  // 1. อ่านค่าอุณหภูมิ (DS18B20)
  tempSensor.requestTemperatures(); 
  tempValue = tempSensor.getTempCByIndex(0);
  Serial.print("Temp: "); Serial.print(tempValue); Serial.println(" C");

  // 2. อ่านค่า pH
  float espPhVoltage = getStableVoltage(PIN_PH);
  phVoltage = espPhVoltage * ((R1 + R2) / R2); // ชดเชย Voltage Divider
  phValue = 3.5 * phVoltage + CALIBRATION_PH;
  Serial.print("pH: "); Serial.print(phValue); Serial.print(" (V: "); Serial.print(phVoltage); Serial.println(")");

  // 3. อ่านค่า TDS (ชดเชยอุณหภูมิด้วย)
  tdsVoltage = getStableVoltage(PIN_TDS);
  // สูตรคำนวณ TDS มาตรฐาน (ต้องสอบเทียบค่าคงที่อีกครั้ง)
  float compensationCoefficient = 1.0 + 0.02 * (tempValue - 25.0);
  float compensationVolatge = tdsVoltage / compensationCoefficient;
  tdsValue = (133.42 * pow(compensationVolatge, 3) - 255.86 * pow(compensationVolatge, 2) + 857.39 * compensationVolatge) * 0.5;
  Serial.print("TDS: "); Serial.print(tdsValue); Serial.print(" ppm (V: "); Serial.print(tdsVoltage); Serial.println(")");

  // 4. อ่านค่าความขุ่น (Turbidity)
  turbidityVoltage = getStableVoltage(PIN_TURBIDITY);
  // สูตรคำนวณความขุ่นมาตรฐาน (ต้องสอบเทียบอีกครั้ง)
  if(turbidityVoltage < 2.5){
    turbidityValue = 3000;
  } else {
    turbidityValue = -1120.4 * pow(turbidityVoltage, 2) + 5742.3 * turbidityVoltage - 4352.9;
    if(turbidityValue < 0) turbidityValue = 0;
  }
  Serial.print("Turbidity: "); Serial.print(turbidityValue); Serial.print(" NTU (V: "); Serial.print(turbidityVoltage); Serial.println(")");
  Serial.println("-----------------------");
}

// ==========================================
// ฟังก์ชันสร้าง JSON และ Publish
// ==========================================
void publishData() {
  StaticJsonDocument<300> doc;
  doc["node_id"] = NODE_NAME; 
  doc["ph"] = phValue;
  doc["tds"] = tdsValue;
  doc["turbidity"] = turbidityValue;
  doc["temperature"] = tempValue;
  
  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer);

  Serial.print("Publishing to AWS: ");
  Serial.println(jsonBuffer); 
  
  client.publish(AWS_IOT_TOPIC, jsonBuffer);
}

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(115200); 
  analogReadResolution(12); 
  
  tempSensor.begin(); // เริ่มต้นการทำงานเซ็นเซอร์อุณหภูมิ

  Serial.print("Target Board: ");
  Serial.println(NODE_NAME);

  connectWiFi();
  syncTime();

  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);
  client.begin(AWS_IOT_ENDPOINT, 8883, net); 
  
  connectAWS();
}

// ==========================================
// LOOP
// ==========================================
void loop() {
  // 1. เช็คและต่อเน็ตใหม่ถ้าหลุด
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi disconnected! Reconnecting...");
    connectWiFi();
    // ถ้าเพิ่งต่อ Wi-Fi ติดใหม่ ต้องตั้งเวลาใหม่ด้วยเพื่อกัน SSL Error
    syncTime(); 
  }
  
  // 2. เช็คและต่อ AWS ใหม่ถ้าหลุด
  if (!client.connected() && WiFi.status() == WL_CONNECTED) {
    Serial.println("AWS IoT disconnected! Reconnecting...");
    connectAWS();
  }

  client.loop(); 
  readSensors();

  // 3. ยิงข้อมูลทุก 10 วินาที
  if (millis() - lastMillis > 10000) {
    lastMillis = millis();
    
    if (client.connected()) {
      publishData();
    } else {
      Serial.println("Failed to publish: AWS disconnected.");
    }
  }
}