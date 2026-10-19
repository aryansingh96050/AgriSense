from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.schemas import IrrigationAdviceResponse, FertilizerAdviceResponse
from ..services.irrigation_advisor import irrigation_advisor
from ..services.fertilizer_advisor import fertilizer_advisor
from ..services.weather_service import weather_service

router = APIRouter(prefix="/advisory", tags=["Smart Agronomic Advisory"])

@router.get("/irrigation", response_model=IrrigationAdviceResponse)
def get_irrigation_advisory(device_id: str = "ESP32_NODE_01", db: Session = Depends(get_db)):
    """
    Get live AI/Rule-based smart irrigation advisory based on soil moisture,
    evapotranspiration, and weather forecasting.
    """
    return irrigation_advisor.evaluate(db, device_id=device_id)

@router.get("/fertilizer", response_model=FertilizerAdviceResponse)
def get_fertilizer_advisory(device_id: str = "ESP32_NODE_01", db: Session = Depends(get_db)):
    """
    Get comprehensive NPK soil nutrient analysis and commercial & organic fertilizer dosage.
    """
    return fertilizer_advisor.evaluate(db, device_id=device_id)

@router.get("/weather")
def get_weather_forecast():
    """
    Get local microclimate forecast and rain probability.
    """
    return weather_service.get_forecast()

@router.get("/summary")
def get_combined_advisory_summary(device_id: str = "ESP32_NODE_01", db: Session = Depends(get_db)):
    """
    Get a complete snapshot of both irrigation and fertilization status for the dashboard.
    """
    irr_advice = irrigation_advisor.evaluate(db, device_id=device_id)
    fert_advice = fertilizer_advisor.evaluate(db, device_id=device_id)
    weather = weather_service.get_forecast()
    
    return {
        "irrigation": irr_advice,
        "fertilizer": fert_advice,
        "weather": weather
    }
