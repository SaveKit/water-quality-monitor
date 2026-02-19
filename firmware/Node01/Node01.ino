#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <MQTTClient.h>
#include <ArduinoJson.h>
#include "secrets.h"

// ==========================================
// 📌 ตั้งค่าประจำตัวบอร์ด (เปลี่ยนตรงนี้เมื่อใช้ Node อื่น)
// ==========================================
#define NODE_NAME "Node01"
const float CALIBRATION_VALUE = 0.0; // ใส่ค่า Calibration ของบอร์ดนี้

// ==========================================
// กำหนด Hardware
// ==========================================
const int PIN_PH = 36;    // ขา VP (GPIO 36) 
const float R1 = 10000.0; // 10k
const float R2 = 20000.0; // 20k (10k+10k)

// ตัวแปร Global
float sensorVoltage = 0.0; 
float phValue = 0.0;
unsigned long lastMillis = 0;

// สร้าง Client
WiFiClientSecure net = WiFiClientSecure(); 
MQTTClient client = MQTTClient(512);       

// ==========================================
// 1. ฟังก์ชันเชื่อมต่อ Wi-Fi
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
// 2. ฟังก์ชันตั้งเวลาจาก Internet (NTP)
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
// 3. ฟังก์ชันเชื่อมต่อ AWS IoT
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
// 4. ฟังก์ชันอ่านค่าและคำนวณเซ็นเซอร์
// ==========================================
void readSensor() {
  unsigned long adcSum = 0;
  int samples = 20; 
  
  for (int i = 0; i < samples; i++) {
    adcSum += analogRead(PIN_PH);
    delay(10); 
  }
  
  float avgADC = (float)adcSum / samples;
  float espVoltage = (avgADC / 4095.0) * 3.3;
  
  // ชดเชย Voltage Divider กลับเป็นไฟ 5V
  sensorVoltage = espVoltage * ((R1 + R2) / R2);
  
  // แปลงเป็น pH
  phValue = 3.5 * sensorVoltage + CALIBRATION_VALUE;

  Serial.print("ADC: "); Serial.print(avgADC, 0);
  Serial.print(" | ESP V: "); Serial.print(espVoltage, 2);
  Serial.print("V | Sensor V: "); Serial.print(sensorVoltage, 2); 
  Serial.print("V | pH: "); Serial.println(phValue, 2);
}

// ==========================================
// 5. ฟังก์ชันสร้าง JSON และ Publish
// ==========================================
void publishData() {
  StaticJsonDocument<200> doc;
  doc["node_id"] = NODE_NAME; 
  doc["ph"] = phValue;
  doc["voltage"] = sensorVoltage; 
  
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
  readSensor();

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