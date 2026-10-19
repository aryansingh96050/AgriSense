import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# ================= SQLALCHEMY ORM MODELS =================

class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    device_id = Column(String, index=True)
    moisture = Column(Float)
    temperature = Column(Float)
    ph = Column(Float)
    nitrogen = Column(Float)
    phosphorus = Column(Float)
    potassium = Column(Float)
    ec = Column(Float, default=0.0)
    battery_voltage = Column(Float, default=3.9)
    battery_percentage = Column(Integer, default=85)
    pump_active = Column(Boolean, default=False)
    sensor_status = Column(String, default="OK")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    device_id = Column(String, index=True)
    alert_type = Column(String)  # IRRIGATION, FERTILIZER, PH, SYSTEM
    severity = Column(String)    # INFO, WARNING, CRITICAL
    message_en = Column(String)
    message_hi = Column(String)
    channels_sent = Column(String, default="SMS,WHATSAPP")
    delivery_status = Column(String, default="SIMULATED")


class NodeSettings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    active_crop = Column(String, default="wheat")
    active_stage = Column(String, default="crown_root")
    auto_pump_enabled = Column(Boolean, default=True)
    pump_override_state = Column(Boolean, default=False)
    farmer_phone = Column(String, default="+919876543210")
    farmer_name = Column(String, default="Ramesh Kumar (रमेश कुमार)")
    field_size_acres = Column(Float, default=2.5)
    alert_cooldown_mins = Column(Integer, default=120)
    last_irrigation_alert = Column(DateTime, nullable=True)
    last_fertilizer_alert = Column(DateTime, nullable=True)


# ================= PYDANTIC SCHEMAS =================

class TelemetryIn(BaseModel):
    device_id: str = "AGRI-NODE-001"
    moisture: float = Field(..., ge=0.0, le=100.0, description="Soil Moisture %")
    temperature: float = Field(..., description="Soil Temperature °C")
    ph: float = Field(..., ge=1.0, le=14.0, description="Soil pH")
    nitrogen: float = Field(..., ge=0, description="Nitrogen level mg/kg")
    phosphorus: float = Field(..., ge=0, description="Phosphorus level mg/kg")
    potassium: float = Field(..., ge=0, description="Potassium level mg/kg")
    ec: Optional[float] = 0.0
    battery_voltage: Optional[float] = 3.9
    battery_percentage: Optional[int] = 85
    pump_active: Optional[bool] = False
    sensor_status: Optional[str] = "MODBUS_OK"


class TelemetryOut(TelemetryIn):
    id: int
    timestamp: datetime.datetime

    class Config:
        from_attributes = True


class FertilizerRecommendation(BaseModel):
    fertilizer_name_en: str
    fertilizer_name_hi: str
    dose_per_acre_kg: float
    total_field_dose_kg: float
    timing_guidance: str
    priority: str  # HIGH, MEDIUM, OPTIMAL


class AdvisoryResult(BaseModel):
    timestamp: datetime.datetime
    crop: str
    crop_name_hi: str
    stage: str
    stage_name_hi: str
    
    # Irrigation
    moisture_current: float
    moisture_target_min: float
    moisture_target_max: float
    irrigation_needed: bool
    irrigation_urgency: str # URGENT, NORMAL, NOT_NEEDED, WATERLOGGED
    recommended_pump_run_minutes: int
    irrigation_advice_en: str
    irrigation_advice_hi: str
    
    # Fertilization
    ph_current: float
    ph_status: str # ACIDIC, OPTIMAL, ALKALINE
    ph_advice_en: str
    ph_advice_hi: str
    
    n_current: float
    n_target: float
    p_current: float
    p_target: float
    k_current: float
    k_target: float
    
    fertilizer_action_needed: bool
    fertilizer_recommendations: List[FertilizerRecommendation]
    fertilizer_advice_en: str
    fertilizer_advice_hi: str
    
    # Ready-to-send SMS / WhatsApp payloads
    sms_text_hi: str
    sms_text_en: str
    whatsapp_text_hi: str
    whatsapp_text_en: str


class SettingsUpdate(BaseModel):
    active_crop: Optional[str] = None
    active_stage: Optional[str] = None
    auto_pump_enabled: Optional[bool] = None
    farmer_phone: Optional[str] = None
    farmer_name: Optional[str] = None
    field_size_acres: Optional[float] = None


class PumpOverrideRequest(BaseModel):
    state: bool  # True = ON, False = OFF
