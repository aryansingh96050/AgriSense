from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

# ==================== Telemetry Schemas ====================

class TelemetryCreate(BaseModel):
    device_id: Optional[str] = "ESP32_NODE_01"
    soil_moisture: float = Field(..., ge=0.0, le=100.0, description="Soil moisture percentage")
    temperature: float = Field(..., ge=-20.0, le=65.0, description="Ambient temperature in °C")
    humidity: float = Field(..., ge=0.0, le=100.0, description="Relative humidity percentage")
    nitrogen: Optional[float] = Field(default=45.0, ge=0.0, description="Nitrogen level in mg/kg")
    phosphorus: Optional[float] = Field(default=30.0, ge=0.0, description="Phosphorus level in mg/kg")
    potassium: Optional[float] = Field(default=150.0, ge=0.0, description="Potassium level in mg/kg")
    ph_level: Optional[float] = Field(default=6.8, ge=0.0, le=14.0, description="Soil pH level")
    battery_level: Optional[float] = Field(default=95.0, ge=0.0, le=100.0, description="Node battery %")
    signal_rssi: Optional[int] = Field(default=-65, description="WiFi RSSI dBm")

class TelemetryResponse(TelemetryCreate):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

# ==================== Actuator Schemas ====================

class ActuatorCommand(BaseModel):
    pump_on: Optional[bool] = None
    valve_open: Optional[bool] = None
    auto_mode: Optional[bool] = None
    active_crop: Optional[str] = None
    field_area_acres: Optional[float] = Field(default=None, gt=0.0)

class ActuatorResponse(BaseModel):
    device_id: str
    pump_on: bool
    valve_open: bool
    auto_mode: bool
    last_switched: datetime
    active_crop: str
    field_area_acres: float
    accumulated_seconds_today: int

    model_config = ConfigDict(from_attributes=True)

# ==================== Advisory Schemas ====================

class IrrigationAdviceResponse(BaseModel):
    device_id: str
    timestamp: datetime
    active_crop: str
    growth_stage: str
    current_moisture: float
    target_min: float
    target_max: float
    status: str # "OPTIMAL", "DRY_NEEDS_WATER", "CRITICAL_DROUGHT", "RAIN_PREDICTED_SKIP", "SATURATED"
    urgency: str # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    pump_recommended: bool
    recommended_duration_minutes: float
    estimated_water_liters: float
    rain_probability_pct: float
    forecast_summary: str
    advice_text: str
    auto_executed: bool

class FertilizerAdviceResponse(BaseModel):
    crop_name: str
    growth_stage: str
    field_area_acres: float
    soil_ph: float
    ph_status: str # "Acidic", "Neutral (Optimal)", "Alkaline"
    
    current_n: float
    target_n: float
    n_status: str
    
    current_p: float
    target_p: float
    p_status: str
    
    current_k: float
    target_k: float
    k_status: str
    
    # Recommended commercial fertilizers (kg and standard 45kg/50kg bags)
    urea_kg: float
    urea_bags: float
    dap_kg: float
    dap_bags: float
    mop_kg: float
    mop_bags: float
    
    organic_options: List[str]
    split_application_guide: str
    key_precautions: List[str]

# ==================== Crop Profile Schemas ====================

class CropProfileSchema(BaseModel):
    crop_name: str
    category: str
    optimal_moisture_min: float
    optimal_moisture_max: float
    wilting_point: float
    temp_min: float
    temp_max: float
    n_target_ppm: float
    p_target_ppm: float
    k_target_ppm: float
    kc_factor: float
    growth_stage: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# ==================== Simulation Schema ====================

class SimulationTrigger(BaseModel):
    scenario: str # "HEATWAVE", "HEAVY_RAIN", "SOIL_DROUGHT", "LOW_NITROGEN", "OPTIMAL"
