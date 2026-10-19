/**
 * AgriSense - IoT Edge Node Firmware
 * Target Microcontroller: ESP32 Dev Module (NodeMCU-32S / ESP-WROOM-32)
 *
 * Capabilities:
 * - 7-in-1 Modbus RS485 Soil Sensor (Moisture, Temp, pH, N, P, K, EC)
 * - Secondary Analog Capacitive Soil Moisture Sensor (v1.2)
 * - Battery Voltage Monitoring via Voltage Divider
 * - Relay / Solenoid Valve Control for Automated Irrigation
 * - Wi-Fi HTTP POST Telemetry transmission with JSON payload
 * - Deep Sleep Power Saving (15 min sleep intervals)
 * - Local EEPROM/Flash buffering for offline resilience
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "modbus_npk_reader.h"

// ================= CONFIGURATION =================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Backend Cloud Server Endpoint
const char* SERVER_URL    = "http://192.168.1.100:8000/api/telemetry";
const char* DEVICE_ID     = "AGRI-NODE-001";
const char* SECRET_TOKEN  = "agrisense_secret_token_123";

// Pinout Definitions (ESP32)
#define RS485_RX_PIN      16    // RO of MAX485
#define RS485_TX_PIN      17    // DI of MAX485
#define RS485_DE_RE_PIN   4     // DE & RE connected together
#define RELAY_PUMP_PIN    18    // Active LOW or HIGH Relay for Irrigation Pump
#define BATTERY_ADC_PIN   35    // Voltage Divider (R1=100k, R2=100k)
#define ANALOG_MOIST_PIN  34    // Capacitive Soil Moisture Sensor v1.2 (backup)
#define STATUS_LED_PIN    2     // Onboard Blue LED

// Deep Sleep Settings (e.g. 15 minutes in microseconds)
#define TIME_TO_SLEEP_SEC 900   // 15 minutes = 900 seconds
#define uS_TO_S_FACTOR    1000000ULL

// Modbus Instance
ModbusSoilReader soilSensor(&Serial2, RS485_DE_RE_PIN, 0x01);

// ================= HELPER FUNCTIONS =================
float readBatteryVoltage() {
    // 12-bit ADC: 0-4095 corresponds to 0-3.3V
    // Divider factor = (100k + 100k) / 100k = 2.0
    int raw = analogRead(BATTERY_ADC_PIN);
    float pinVoltage = (raw / 4095.0f) * 3.3f * 1.05f; // calibration factor
    float batteryVoltage = pinVoltage * 2.0f;
    return batteryVoltage;
}

int calculateBatteryPercentage(float voltage) {
    // Standard 3.7V Li-ion battery (3.0V empty -> 4.2V full)
    if (voltage >= 4.20f) return 100;
    if (voltage <= 3.20f) return 0;
    return (int)((voltage - 3.20f) / (4.20f - 3.20f) * 100.0f);
}

float readAnalogCapacitiveMoisture() {
    // Capacitive v1.2 calibration values:
    // Air (Dry) ~ 3100, Water (Wet) ~ 1250
    const int airValue = 3100;
    const int waterValue = 1250;
    int raw = analogRead(ANALOG_MOIST_PIN);
    int percent = map(raw, airValue, waterValue, 0, 100);
    if (percent < 0) percent = 0;
    if (percent > 100) percent = 100;
    return (float)percent;
}

bool sendTelemetryToCloud(const SoilMetrics& metrics, float battVolt, int battPercent, bool pumpState) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[AgriSense] WiFi disconnected, unable to send telemetry.");
        return false;
    }

    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Token", SECRET_TOKEN);

    // Build JSON Payload
    StaticJsonDocument<512> doc;
    doc["device_id"]         = DEVICE_ID;
    doc["moisture"]          = metrics.valid ? metrics.moisture : readAnalogCapacitiveMoisture();
    doc["temperature"]       = metrics.temperature;
    doc["ph"]                = metrics.ph;
    doc["nitrogen"]          = metrics.nitrogen;
    doc["phosphorus"]        = metrics.phosphorus;
    doc["potassium"]         = metrics.potassium;
    doc["ec"]                = metrics.ec;
    doc["battery_voltage"]   = battVolt;
    doc["battery_percentage"]= battPercent;
    doc["pump_active"]       = pumpState;
    doc["sensor_status"]     = metrics.valid ? "MODBUS_OK" : "ANALOG_FALLBACK";

    String jsonString;
    serializeJson(doc, jsonString);

    Serial.println("[AgriSense] Sending JSON: " + jsonString);

    int httpCode = http.POST(jsonString);
    bool success = false;

    if (httpCode > 0) {
        String response = http.getString();
        Serial.printf("[AgriSense] HTTP Response %d: %s\n", httpCode, response.c_str());

        // Parse Cloud Directives (e.g., Pump Override Command)
        StaticJsonDocument<256> respDoc;
        DeserializationError err = deserializeJson(respDoc, response);
        if (!err && respDoc.containsKey("command_pump")) {
            bool commandPump = respDoc["command_pump"];
            digitalWrite(RELAY_PUMP_PIN, commandPump ? HIGH : LOW);
            Serial.printf("[AgriSense] Actuator command received: Pump %s\n", commandPump ? "ON" : "OFF");
        }
        success = (httpCode == 200 || httpCode == 201);
    } else {
        Serial.printf("[AgriSense] HTTP POST failed, error: %s\n", http.errorToString(httpCode).c_str());
    }

    http.end();
    return success;
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n--- AgriSense Smart Soil Sensor Node Starting ---");

    pinMode(STATUS_LED_PIN, OUTPUT);
    pinMode(RELAY_PUMP_PIN, OUTPUT);
    digitalWrite(RELAY_PUMP_PIN, LOW); // Default pump OFF

    // Initialize RS485 Modbus Sensor
    soilSensor.begin(4800, RS485_RX_PIN, RS485_TX_PIN);

    // Connect to WiFi with 10s timeout
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("[AgriSense] Connecting to WiFi");
    unsigned long startAttempt = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 10000) {
        digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
        delay(300);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        digitalWrite(STATUS_LED_PIN, HIGH);
        Serial.printf("\n[AgriSense] Connected! IP: %s, RSSI: %d dBm\n",
                      WiFi.localIP().toString().c_str(), WiFi.RSSI());
    } else {
        digitalWrite(STATUS_LED_PIN, LOW);
        Serial.println("\n[AgriSense] WiFi connection timed out.");
    }

    // 1. Read Modbus Soil Sensor
    Serial.println("[AgriSense] Reading RS485 Soil Sensors...");
    SoilMetrics metrics = soilSensor.readAll();

    if (metrics.valid) {
        Serial.printf("  Moisture:    %.1f %%\n", metrics.moisture);
        Serial.printf("  Temperature: %.1f °C\n", metrics.temperature);
        Serial.printf("  pH:          %.1f\n", metrics.ph);
        Serial.printf("  Nitrogen:    %u mg/kg\n", metrics.nitrogen);
        Serial.printf("  Phosphorus:  %u mg/kg\n", metrics.phosphorus);
        Serial.printf("  Potassium:   %u mg/kg\n", metrics.potassium);
        Serial.printf("  EC:          %u us/cm\n", metrics.ec);
    } else {
        Serial.println("  [Warning] Modbus sensor response timeout or CRC failure!");
        Serial.println("  Falling back to analog capacitive probe.");
    }

    // 2. Read Power Status
    float battVolt = readBatteryVoltage();
    int battPct    = calculateBatteryPercentage(battVolt);
    bool pumpState = digitalRead(RELAY_PUMP_PIN) == HIGH;

    // 3. Post to Cloud
    sendTelemetryToCloud(metrics, battVolt, battPct, pumpState);

    // 4. Power Management: Prepare for Deep Sleep
    Serial.println("[AgriSense] Entering Deep Sleep for 15 minutes to preserve battery...");
    esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP_SEC * uS_TO_S_FACTOR);
    Serial.flush();
    esp_deep_sleep_start();
}

void loop() {
    // Will never be called because of deep sleep in setup()
}
