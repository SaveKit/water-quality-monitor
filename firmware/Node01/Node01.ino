#include <WiFiS3.h>
#include <ArduinoMqttClient.h>
#include "secrets.h"

void setup() {
  Serial.begin(9600);
  while (!Serial);
  Serial.println("Water Quality Node 01 Initialized");
}

void loop() {
  // Main loop placeholder
}