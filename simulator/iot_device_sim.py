"""
AgriSense Virtual IoT Node Simulator
Simulates a physical ESP32 connected to:
- Capacitive Soil Moisture Sensor v1.2
- DHT22 (Temperature & Humidity)
- RS485 Soil NPK Sensor
- 5V Relay Actuator (Submersible Pump)

Streams realistic telemetry to AgriSense Cloud / Localhost API every N seconds.
"""

import time
import math
import random
import requests
import sys
import os

# Configuration
SERVER_URL = os.getenv("AGRISENSE_SERVER_URL", "http://localhost:8000")
TELEMETRY_ENDPOINT = f"{SERVER_URL}/api/v1/telemetry"
DEVICE_ID = "ESP32_NODE_01"
INTERVAL_SECONDS = 3.5

# Initial Simulation State
soil_moisture = 48.0
temperature = 27.5
humidity = 58.0
nitrogen = 44.0
phosphorus = 28.0
potassium = 145.0
ph_level = 6.7
battery_level = 98.0
pump_is_running = False

print("=" * 65)
print("  🌾 AGRISENSE VIRTUAL IOT NODE SIMULATOR (ESP32)  ")
print(f"  Target Endpoint : {TELEMETRY_ENDPOINT}")
print(f"  Simulated Node  : {DEVICE_ID}")
print(f"  Stream Interval : {INTERVAL_SECONDS}s")
print("=" * 65)

step = 0
try:
    while True:
        step += 1
        
        # 1. Physics update based on pump status
        if pump_is_running:
            # Water is being pumped: moisture increases rapidly
            soil_moisture += random.uniform(2.2, 4.0)
            if soil_moisture > 92.0:
                soil_moisture = 92.0
            status_symbol = "💧 [PUMP ACTIVE - WATERING]"
        else:
            # Water evaporates slowly, faster if hot
            evap_rate = 0.15 + (max(0, temperature - 25.0) * 0.04)
            soil_moisture -= random.uniform(evap_rate * 0.8, evap_rate * 1.4)
            if soil_moisture < 15.0:
                soil_moisture = 15.0
            status_symbol = "☀️ [PUMP IDLE - EVAPORATING]"

        # 2. Ambient diurnal temperature & humidity variation
        temperature = 26.0 + 5.0 * math.sin(step * 0.08) + random.uniform(-0.3, 0.3)
        humidity = max(30.0, min(90.0, 85.0 - (temperature - 20.0) * 2.8 + random.uniform(-1.0, 1.0)))

        # 3. Slow NPK & pH drift
        nitrogen = max(10.0, min(180.0, nitrogen + random.uniform(-0.4, 0.3)))
        phosphorus = max(5.0, min(90.0, phosphorus + random.uniform(-0.2, 0.2)))
        potassium = max(40.0, min(240.0, potassium + random.uniform(-0.5, 0.5)))
        ph_level = round(max(5.5, min(8.2, 6.7 + random.uniform(-0.05, 0.05))), 2)
        battery_level = max(10.0, battery_level - 0.005)

        # 4. Construct Telemetry JSON Payload
        payload = {
            "device_id": DEVICE_ID,
            "soil_moisture": round(soil_moisture, 1),
            "temperature": round(temperature, 1),
            "humidity": round(humidity, 1),
            "nitrogen": round(nitrogen, 1),
            "phosphorus": round(phosphorus, 1),
            "potassium": round(potassium, 1),
            "ph_level": ph_level,
            "battery_level": round(battery_level, 1),
            "signal_rssi": random.randint(-68, -55)
        }

        # 5. Transmit packet via HTTP POST
        try:
            resp = requests.post(TELEMETRY_ENDPOINT, json=payload, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                pump_cmd = data.get("pump_command", "OFF")
                pump_is_running = (pump_cmd == "ON")
                advice_status = data.get("advice_status", "NORMAL")

                print(
                    f"[{time.strftime('%H:%M:%S')}] #{step:03d} | "
                    f"Moist: {payload['soil_moisture']:4.1f}% | "
                    f"Temp: {payload['temperature']:4.1f}°C | "
                    f"NPK: {int(payload['nitrogen'])}/{int(payload['phosphorus'])}/{int(payload['potassium'])} | "
                    f"Cmd: {pump_cmd:3s} | "
                    f"Advice: {advice_status:<16s} | {status_symbol}"
                )
            else:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Server responded with HTTP {resp.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"[{time.strftime('%H:%M:%S')}] ⏳ Waiting for AgriSense server at {SERVER_URL}...")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ❌ Transmission error: {e}")

        time.sleep(INTERVAL_SECONDS)

except KeyboardInterrupt:
    print("\nSimulator stopped gracefully.")
    sys.exit(0)
