from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text
from ..database import Base

def utc_now():
    return datetime.now(timezone.utc)

class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    device_id = Column(String(50), default="ESP32_NODE_01", index=True)
    soil_moisture = Column(Float, nullable=False) # In % (0 - 100%)
    temperature = Column(Float, nullable=False)   # In °C
    humidity = Column(Float, nullable=False)      # In %
    nitrogen = Column(Float, default=45.0)        # In mg/kg (ppm)
    phosphorus = Column(Float, default=30.0)      # In mg/kg (ppm)
    potassium = Column(Float, default=150.0)      # In mg/kg (ppm)
    ph_level = Column(Float, default=6.8)         # 0 - 14 scale
    battery_level = Column(Float, default=95.0)   # In %
    signal_rssi = Column(Integer, default=-65)    # In dBm

class ActuatorState(Base):
    __tablename__ = "actuator_states"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(50), default="ESP32_NODE_01", unique=True, index=True)
    pump_on = Column(Boolean, default=False)
    valve_open = Column(Boolean, default=False)
    auto_mode = Column(Boolean, default=True)     # Auto irrigation based on AI/rules
    last_switched = Column(DateTime, default=utc_now)
    active_crop = Column(String(50), default="Wheat")
    field_area_acres = Column(Float, default=1.0)
    accumulated_seconds_today = Column(Integer, default=0)

class CropProfile(Base):
    __tablename__ = "crop_profiles"

    id = Column(Integer, primary_key=True, index=True)
    crop_name = Column(String(50), unique=True, index=True)
    category = Column(String(50), default="Cereal")
    optimal_moisture_min = Column(Float, default=50.0) # %
    optimal_moisture_max = Column(Float, default=70.0) # %
    wilting_point = Column(Float, default=30.0)        # %
    temp_min = Column(Float, default=15.0)             # °C
    temp_max = Column(Float, default=32.0)             # °C
    n_target_ppm = Column(Float, default=120.0)        # Required Soil N
    p_target_ppm = Column(Float, default=50.0)         # Required Soil P
    k_target_ppm = Column(Float, default=180.0)        # Required Soil K
    kc_factor = Column(Float, default=1.05)            # Crop ET coefficient
    growth_stage = Column(String(50), default="Vegetative")
    notes = Column(Text, nullable=True)

class IrrigationLog(Base):
    __tablename__ = "irrigation_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    device_id = Column(String(50), default="ESP32_NODE_01")
    event_type = Column(String(50)) # AUTO_ON, AUTO_OFF, MANUAL_ON, MANUAL_OFF, RAIN_ABORT
    duration_seconds = Column(Integer, default=0)
    water_liters = Column(Float, default=0.0)
    trigger_reason = Column(String(255))

class AdvisoryLog(Base):
    __tablename__ = "advisory_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    advisory_type = Column(String(50)) # IRRIGATION or FERTILIZATION
    severity = Column(String(20))      # OPTIMAL, INFO, WARNING, CRITICAL
    title = Column(String(255))
    message = Column(Text)
    action_suggested = Column(String(255))
