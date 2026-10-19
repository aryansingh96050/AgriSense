/*
 * =====================================================================================
 *  AgriSense: IoT Smart Irrigation & Fertilization Node
 *  Hardware Target: ESP32 DevKit V1 (38-pin or 30-pin)
 *  Sensors:
 *    - Capacitive Soil Moisture Sensor v1.2 (ADC Pin 34)
 *    - DHT22 Ambient Temp & Humidity Sensor (Pin 4)
 *    - RS485 / Analog NPK sensor simulation
 *  Actuators:
 *    - 5V Relay Channel 1: Submersible Water Pump (Pin 26)
 *    - 5V Relay Channel 2: Solenoid Drip Valve (Pin 27)
 *    - Onboard Status LED (Pin 2)
 *
 *  Libraries Required:
 *    - WiFi.h (ESP32 Built-in)
 *    - HTTPClient.h (ESP32 Built-in)
 *    - ArduinoJson (by Benoit Blanchon, v6 or v7)
 *    - DHT sensor library (by Adafruit)
 * =====================================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ==================== Pin Configurations ====================
#define SOIL_PIN        34   // Capacitive Moisture Sensor (ADC1 CH6)
#define DHT_PIN         4    // DHT22 Data Pin
#define DHT_TYPE        DHT22
#define RELAY_PUMP_PIN  26   // Active LOW or HIGH depending on relay board
#define RELAY_VALVE_PIN 27   // Solenoid Valve
#define STATUS_LED_PIN  2    // Built-in Blue LED

// Relay Logic (Most 5V relay modules are active LOW)
#define RELAY_ON        LOW
#define RELAY_OFF       HIGH

// ==================== Network & Server Credentials ====================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Server URL (Replace with your local computer IP or deployed cloud URL)
// Example Local: "http://192.168.1.15:8000/api/v1/telemetry"
// Example Cloud: "https://agrisense-app.onrender.com/api/v1/telemetry"
const char* SERVER_ENDPOINT = "http://192.168.1.100:8000/api/v1/telemetry";

const char* DEVICE_ID = "ESP32_NODE_01";
const unsigned long TELEMETRY_INTERVAL_MS = 5000; // Send reading every 5 seconds
unsigned long lastTransmission = 0;

// Capacitive Sensor Calibration Values
// Measure analogRead() in dry air (AirValue) and submerged in water (WaterValue)
const int AIR_VALUE   = 3200; // Dry air analog reading
const int WATER_VALUE = 1400; // In water analog reading

DHT dht(DHT_PIN, DHT_TYPE);

// ==================== Setup Function ====================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- Initializing AgriSense IoT Node ---");

  // Initialize GPIOs
  pinMode(RELAY_PUMP_PIN, OUTPUT);
  pinMode(RELAY_VALVE_PIN, OUTPUT);
  pinMode(STATUS_LED_PIN, OUTPUT);

  // Default state: Actuators turned OFF
  digitalWrite(RELAY_PUMP_PIN, RELAY_OFF);
  digitalWrite(RELAY_VALVE_PIN, RELAY_OFF);
  digitalWrite(STATUS_LED_PIN, LOW);

  // Initialize DHT Sensor
  dht.begin();

  // Connect to WiFi
  connectWiFi();
}

// ==================== Main Loop ====================
void loop() {
  // Ensure WiFi remains connected
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // Transmit telemetry periodically
  if (millis() - lastTransmission >= TELEMETRY_INTERVAL_MS) {
    lastTransmission = millis();
    sendTelemetryAndActuate();
  }
}

// ==================== Helper Functions ====================

void connectWiFi() {
  Serial.printf("Connecting to WiFi: %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(500);
    Serial.print(".");
    digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN)); // Blink while connecting
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected successfully!");
    Serial.printf("[WiFi] IP Address: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("[WiFi] RSSI Signal: %d dBm\n", WiFi.RSSI());
    digitalWrite(STATUS_LED_PIN, HIGH);
  } else {
    Serial.println("\n[WiFi] Connection Failed! Will retry in next loop.");
    digitalWrite(STATUS_LED_PIN, LOW);
  }
}

float readSoilMoisture() {
  // Read analog value with multiple samples for smoothing
  long sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += analogRead(SOIL_PIN);
    delay(10);
  }
  int rawValue = sum / 10;

  // Map analog range to 0.0 - 100.0%
  float moisture = map(rawValue, AIR_VALUE, WATER_VALUE, 0, 100);
  moisture = constrain(moisture, 0.0, 100.0);
  return moisture;
}

void sendTelemetryAndActuate() {
  float soilMoisture = readSoilMoisture();
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  // Validate DHT readings
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("[Sensor] Warning: Failed to read from DHT22 sensor! Using fallback.");
    temperature = 26.5;
    humidity = 55.0;
  }

  // NPK Readings (from RS485 Modbus or sensor baseline)
  float nitrogen = 45.0;
  float phosphorus = 30.0;
  float potassium = 150.0;
  float phLevel = 6.8;
  int rssi = WiFi.RSSI();

  // Create JSON Document
  StaticJsonDocument<512> doc;
  doc["device_id"] = DEVICE_ID;
  doc["soil_moisture"] = round(soilMoisture * 10) / 10.0;
  doc["temperature"] = round(temperature * 10) / 10.0;
  doc["humidity"] = round(humidity * 10) / 10.0;
  doc["nitrogen"] = nitrogen;
  doc["phosphorus"] = phosphorus;
  doc["potassium"] = potassium;
  doc["ph_level"] = phLevel;
  doc["battery_level"] = 100.0;
  doc["signal_rssi"] = rssi;

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  Serial.println("\n[HTTP] Transmitting Telemetry Payload:");
  Serial.println(jsonPayload);

  // Send HTTP POST Request
  HTTPClient http;
  http.begin(SERVER_ENDPOINT);
  http.addHeader("Content-Type", "application/json");

  int httpCode = http.POST(jsonPayload);

  if (httpCode == HTTP_CODE_OK) {
    String response = http.getString();
    Serial.println("[HTTP] Server Response:");
    Serial.println(response);

    // Parse Cloud Actuation Command
    StaticJsonDocument<512> respDoc;
    DeserializationError err = deserializeJson(respDoc, response);
    if (!err) {
      const char* pumpCmd = respDoc["pump_command"] | "OFF";
      const char* valveCmd = respDoc["valve_command"] | "CLOSED";

      // Execute Pump Command on Relay
      if (strcmp(pumpCmd, "ON") == 0) {
        digitalWrite(RELAY_PUMP_PIN, RELAY_ON);
        Serial.println(">>> ACTUATOR TRIGGER: Water Pump [ON] <<<");
      } else {
        digitalWrite(RELAY_PUMP_PIN, RELAY_OFF);
        Serial.println(">>> ACTUATOR TRIGGER: Water Pump [OFF] <<<");
      }

      // Execute Solenoid Valve Command
      if (strcmp(valveCmd, "OPEN") == 0) {
        digitalWrite(RELAY_VALVE_PIN, RELAY_ON);
      } else {
        digitalWrite(RELAY_VALVE_PIN, RELAY_OFF);
      }
    }
  } else {
    Serial.printf("[HTTP] POST failed, error code: %d\n", httpCode);
  }

  http.end();
}
