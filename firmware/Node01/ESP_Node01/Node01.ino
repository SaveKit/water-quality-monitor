#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <MQTTClient.h>
#include "secrets.h"

// ==========================================
// 📌 ตั้งค่าประจำตัวบอร์ด
// ==========================================
#define NODE_NAME "Node01"

// กำหนดขา Serial2 สำหรับคุยกับ Arduino UNO
#define RXD2 16
#define TXD2 17

WiFiClientSecure net = WiFiClientSecure(); 
MQTTClient client = MQTTClient(512);       

// ==========================================
// ฟังก์ชันเชื่อมต่อ (Wi-Fi, NTP, AWS)
// ==========================================
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return; 
  Serial.print("Connecting to Wi-Fi");
  WiFi.begin(SECRET_SSID, SECRET_PASS); 
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nConnected to Wi-Fi!"); 
}

void syncTime() {
  Serial.print("Setting time using SNTP");
  configTime(0, 0, "pool.ntp.org", "time.nist.gov"); 
  time_t now = time(nullptr);
  while (now < 1000000000L) { 
    delay(500); Serial.print(".");
    now = time(nullptr);
  }
  Serial.println("\nTime synchronized!"); 
}

void connectAWS() {
  if (client.connected()) return; 
  Serial.print("Connecting to AWS IoT");
  while (!client.connect(NODE_NAME)) { 
    Serial.print("."); delay(1000);
  }
  Serial.println("\nConnected to AWS IoT!"); 
}

// ==========================================
// SETUP
// ==========================================
void setup() {
  // Serial หลักสำหรับดู Debug ในคอมพิวเตอร์
  Serial.begin(115200); 
  
  // Serial2 สำหรับรับ JSON จาก Arduino UNO
  Serial2.begin(115200, SERIAL_8N1, RXD2, TXD2); 

  Serial.println("=== ESP32 Cloud Gateway Started ===");
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
  // 1. ระบบกู้ชีพ (Reconnect)
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi disconnected! Reconnecting...");
    connectWiFi();
    syncTime(); 
  }
  
  if (!client.connected() && WiFi.status() == WL_CONNECTED) {
    Serial.println("AWS IoT disconnected! Reconnecting...");
    connectAWS();
  }

  client.loop(); 

  // 2. รอรับข้อความจาก Arduino UNO
  if (Serial2.available()) {
    // อ่านข้อความมาจนกว่าจะเจอการขึ้นบรรทัดใหม่ (\n) ที่ UNO ส่งมา
    String incomingData = Serial2.readStringUntil('\n');
    incomingData.trim(); // ลบช่องว่างขยะหัวท้าย

    // เช็คคร่าวๆ ว่าใช่ JSON หรือไม่ (ต้องเปิดด้วย { และปิดด้วย })
    if (incomingData.startsWith("{") && incomingData.endsWith("}")) {
      Serial.print("[Received from UNO] : ");
      Serial.println(incomingData);

      // 3. ยิงขึ้น AWS ทันที
      if (client.connected()) {
        bool success = client.publish(AWS_IOT_TOPIC, incomingData);
        if (success) {
          Serial.println("-> Published to AWS: SUCCESS");
        } else {
          Serial.println("-> Published to AWS: FAILED");
        }
      } else {
        Serial.println("-> Drop Data: AWS not connected.");
      }
      Serial.println("-----------------------------------");
    } 
    // ถ้าไม่ใช่ JSON แต่มีข้อความหลุดมา (เผื่อ UNO สั่ง Serial.print ธรรมดา)
    else if (incomingData.length() > 0) {
      Serial.print("[Debug from UNO] : ");
      Serial.println(incomingData);
    }
  }
}