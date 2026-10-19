import time
import math
import random
import argparse
import requests
from datetime import datetime

DEFAULT_SERVER_URL = "http://localhost:8000/api/telemetry"

class SoilSensorSimulator:
    def __init__(self, server_url=DEFAULT_SERVER_URL, device_id="AGRI-NODE-001"):
        self.server_url = server_url
        self.device_id = device_id
        
        # State variables
        self.moisture = 45.0       # %
        self.temperature = 24.5    # °C
        self.ph = 6.6              # pH
        self.nitrogen = 110.0      # mg/kg
        self.phosphorus = 45.0     # mg/kg
        self.potassium = 40.0      # mg/kg
        self.ec = 420.0            # us/cm
        self.battery_voltage = 4.12 # Volts
        self.battery_pct = 95      # %
        self.pump_active = False
        self.iteration = 0

    def tick(self):
        """Simulates 1 time step of realistic field physics"""
        self.iteration += 1

        # 1. Temperature variation based on time of day
        hour = (datetime.now().hour + datetime.now().minute / 60.0)
        # Peak at 2:00 PM (14.0), lowest at 5:00 AM (5.0)
        temp_cycle = 24.0 + 8.0 * math.sin((hour - 9.0) * math.pi / 12.0)
        self.temperature = round(temp_cycle + random.uniform(-0.5, 0.5), 1)

        # 2. Soil Moisture dynamics:
        # If pump is active -> soil moisture increases!
        if self.pump_active:
            self.moisture += random.uniform(2.5, 4.0)
            if self.moisture > 75.0:
                self.moisture = 75.0
        else:
            # Natural drying due to evapotranspiration
            drying_rate = 0.4 if self.temperature > 28.0 else 0.2
            self.moisture -= (drying_rate + random.uniform(0.0, 0.1))
            if self.moisture < 15.0:
                self.moisture = 15.0
        self.moisture = round(self.moisture, 1)

        # 3. Nutrient slow depletion
        self.nitrogen = max(20.0, round(self.nitrogen - random.uniform(0.05, 0.2), 1))
        self.phosphorus = max(10.0, round(self.phosphorus - random.uniform(0.02, 0.08), 1))
        self.potassium = max(15.0, round(self.potassium - random.uniform(0.03, 0.1), 1))

        # 4. pH slight natural drift
        self.ph = round(self.ph + random.uniform(-0.02, 0.02), 2)
        if self.ph < 5.5: self.ph = 5.5
        if self.ph > 8.2: self.ph = 8.2

        # 5. Battery slight solar recharge or discharge
        if 8 <= datetime.now().hour <= 17:
            # Solar panel charging
            self.battery_voltage = min(4.20, round(self.battery_voltage + 0.002, 3))
        else:
            # Night discharge
            self.battery_voltage = max(3.50, round(self.battery_voltage - 0.001, 3))
        self.battery_pct = int((self.battery_voltage - 3.20) / (4.20 - 3.20) * 100)

        # 6. Electrical conductivity correlates with moisture and nutrients
        self.ec = round(200.0 + (self.nitrogen + self.potassium) * 1.5 + (self.moisture * 2.0), 1)

    def send_telemetry(self):
        payload = {
            "device_id": self.device_id,
            "moisture": self.moisture,
            "temperature": self.temperature,
            "ph": self.ph,
            "nitrogen": self.nitrogen,
            "phosphorus": self.phosphorus,
            "potassium": self.potassium,
            "ec": self.ec,
            "battery_voltage": self.battery_voltage,
            "battery_percentage": self.battery_pct,
            "pump_active": self.pump_active,
            "sensor_status": "SIMULATED_MODBUS_OK"
        }

        try:
            resp = requests.post(self.server_url, json=payload, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                cloud_pump = data.get("command_pump", False)
                # Sync pump state with cloud controller directive
                self.pump_active = cloud_pump
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Telemetry Sent -> "
                      f"Moisture: {self.moisture}% | Temp: {self.temperature}°C | "
                      f"pH: {self.ph} | NPK: {self.nitrogen:.0f}/{self.phosphorus:.0f}/{self.potassium:.0f} | "
                      f"Pump: {'ON (Watering)' if self.pump_active else 'OFF'}")
                return True
            else:
                print(f"Server responded with status {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            print(f"Connection error to {self.server_url}: {e}")
            return False

    def run_continuous(self, interval=5):
        print(f"=== AgriSense Virtual Soil Node Started ===")
        print(f"Streaming data to: {self.server_url}")
        print(f"Update interval: {interval} seconds\n")
        try:
            while True:
                self.tick()
                self.send_telemetry()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nSimulator stopped by user.")

    def trigger_preset(self, scenario: str):
        """Allows testing custom extreme scenarios instantly"""
        if scenario == "drought":
            self.moisture = 19.5
            self.temperature = 33.0
            print("Set scenario: DROUGHT / DRY SOIL (Moisture: 19.5%)")
        elif scenario == "rain":
            self.moisture = 72.0
            self.temperature = 22.0
            print("Set scenario: HEAVY RAIN / WET SOIL (Moisture: 72.0%)")
        elif scenario == "low_nitrogen":
            self.nitrogen = 35.0
            print("Set scenario: NITROGEN DEFICIENCY (N: 35 mg/kg)")
        elif scenario == "acidic":
            self.ph = 5.2
            print("Set scenario: ACIDIC SOIL (pH: 5.2)")
        elif scenario == "alkaline":
            self.ph = 8.4
            print("Set scenario: ALKALINE SOIL (pH: 8.4)")
        elif scenario == "optimal":
            self.moisture = 52.0
            self.ph = 6.7
            self.nitrogen = 130.0
            self.phosphorus = 48.0
            self.potassium = 45.0
            print("Set scenario: ALL OPTIMAL")
        self.send_telemetry()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgriSense IoT Sensor Node Simulator")
    parser.add_argument("--url", default=DEFAULT_SERVER_URL, help="Backend URL")
    parser.add_argument("--interval", type=int, default=5, help="Seconds between readings")
    parser.add_argument("--scenario", choices=["drought", "rain", "low_nitrogen", "acidic", "alkaline", "optimal"], help="Trigger single test scenario")
    
    args = parser.parse_args()
    sim = SoilSensorSimulator(server_url=args.url)
    
    if args.scenario:
        sim.trigger_preset(args.scenario)
    else:
        sim.run_continuous(interval=args.interval)
