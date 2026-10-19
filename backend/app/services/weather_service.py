import random
import math
from datetime import datetime, timezone
from ..config import settings
import requests

class WeatherService:
    def __init__(self):
        self.lat = settings.DEFAULT_LATITUDE
        self.lon = settings.DEFAULT_LONGITUDE
        self.use_api = settings.USE_REAL_WEATHER_API

    def get_forecast(self) -> dict:
        """
        Retrieves weather data & 12h rain forecast.
        Falls back to realistic micro-climate simulation if offline or API disabled.
        """
        if self.use_api:
            try:
                url = f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}&current=temperature_2m,relative_humidity_2m,precipitation&hourly=precipitation_probability,precipitation&forecast_days=1"
                resp = requests.get(url, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    curr = data.get("current", {})
                    hourly = data.get("hourly", {})
                    
                    next_12h_probs = hourly.get("precipitation_probability", [0]*12)[:12]
                    max_rain_prob = max(next_12h_probs) if next_12h_probs else 0.0
                    rain_sum = sum(hourly.get("precipitation", [0.0]*12)[:12])
                    
                    return {
                        "temperature": curr.get("temperature_2m", 28.5),
                        "humidity": curr.get("relative_humidity_2m", 60.0),
                        "rain_probability": float(max_rain_prob),
                        "expected_rain_mm": round(float(rain_sum), 2),
                        "summary": "Cloudy with chance of rain" if max_rain_prob > 50 else "Clear / Mild",
                        "source": "Open-Meteo Live API"
                    }
            except Exception:
                pass # fallback to simulation

        # Realistic diurnal simulation based on current hour
        current_hour = datetime.now(timezone.utc).hour
        # Diurnal temperature cycle: peak around 14:00, coolest at 05:00
        diurnal_temp = 25.0 + 7.0 * math.sin((current_hour - 8) * math.pi / 12)
        sim_temp = round(diurnal_temp + random.uniform(-1.0, 1.0), 1)
        sim_humidity = round(max(30.0, min(95.0, 90.0 - (sim_temp - 18.0) * 3.5 + random.uniform(-3, 3))), 1)
        
        # Weather events generator
        rain_prob = round(random.choice([5.0, 10.0, 15.0, 25.0, 40.0, 75.0, 15.0]), 1)
        expected_rain = round(rain_prob * 0.15, 1) if rain_prob > 50 else 0.0

        if rain_prob > 60:
            summary = "Monsoon showers / heavy rain likely within 6h"
        elif rain_prob > 30:
            summary = "Partly cloudy with slight rain possibility"
        else:
            summary = "Sunny & clear conditions"

        return {
            "temperature": sim_temp,
            "humidity": sim_humidity,
            "rain_probability": rain_prob,
            "expected_rain_mm": expected_rain,
            "summary": summary,
            "source": "AgriSense Microclimate Simulator"
        }

    def calculate_et0(self, temp: float, humidity: float, solar_radiation: float = 18.0) -> float:
        """
        Approximates Reference Evapotranspiration ET0 (mm/day) using Hargreaves-Samani method.
        """
        # Average baseline ET0 in semi-arid/tropical agriculture ranges between 3.5 - 6.5 mm/day
        et0 = 0.0023 * (temp + 17.8) * math.sqrt(max(5.0, 38.0 - temp)) * (solar_radiation / 2.45)
        return round(max(1.5, min(9.0, et0)), 2)

weather_service = WeatherService()
