from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.db_models import CropProfile
from ..models.schemas import CropProfileSchema

router = APIRouter(prefix="/crops", tags=["Crop Profiles"])

# Default preset crop data
DEFAULT_CROPS = [
    {
        "crop_name": "Wheat",
        "category": "Cereal",
        "optimal_moisture_min": 50.0,
        "optimal_moisture_max": 70.0,
        "wilting_point": 30.0,
        "temp_min": 12.0,
        "temp_max": 30.0,
        "n_target_ppm": 120.0,
        "p_target_ppm": 60.0,
        "k_target_ppm": 40.0,
        "kc_factor": 1.05,
        "growth_stage": "Tillering / Crown Root",
        "notes": "Critical irrigation stages: Crown Root Initiation (21 DAS), Flowering, and Dough stage."
    },
    {
        "crop_name": "Rice",
        "category": "Cereal (Paddy)",
        "optimal_moisture_min": 70.0,
        "optimal_moisture_max": 90.0,
        "wilting_point": 45.0,
        "temp_min": 20.0,
        "temp_max": 38.0,
        "n_target_ppm": 150.0,
        "p_target_ppm": 60.0,
        "k_target_ppm": 60.0,
        "kc_factor": 1.25,
        "growth_stage": "Vegetative / Tillering",
        "notes": "Requires standing water or alternate wetting and drying (AWD) to save up to 30% water."
    },
    {
        "crop_name": "Maize",
        "category": "Cereal",
        "optimal_moisture_min": 55.0,
        "optimal_moisture_max": 75.0,
        "wilting_point": 32.0,
        "temp_min": 18.0,
        "temp_max": 35.0,
        "n_target_ppm": 140.0,
        "p_target_ppm": 65.0,
        "k_target_ppm": 50.0,
        "kc_factor": 1.15,
        "growth_stage": "Knee-High Stage",
        "notes": "Extremely sensitive to waterlogging and drought during tasseling & silking."
    },
    {
        "crop_name": "Cotton",
        "category": "Fiber",
        "optimal_moisture_min": 45.0,
        "optimal_moisture_max": 65.0,
        "wilting_point": 28.0,
        "temp_min": 21.0,
        "temp_max": 38.0,
        "n_target_ppm": 120.0,
        "p_target_ppm": 60.0,
        "k_target_ppm": 60.0,
        "kc_factor": 0.85,
        "growth_stage": "Squaring / Flowering",
        "notes": "Deep root system. Moderate moisture required during boll development."
    },
    {
        "crop_name": "Tomato",
        "category": "Vegetable",
        "optimal_moisture_min": 60.0,
        "optimal_moisture_max": 80.0,
        "wilting_point": 35.0,
        "temp_min": 18.0,
        "temp_max": 32.0,
        "n_target_ppm": 150.0,
        "p_target_ppm": 100.0,
        "k_target_ppm": 120.0,
        "kc_factor": 1.15,
        "growth_stage": "Flowering / Fruit Set",
        "notes": "Even moisture prevents fruit cracking and blossom-end rot."
    },
    {
        "crop_name": "Potato",
        "category": "Tuber / Cash Crop",
        "optimal_moisture_min": 65.0,
        "optimal_moisture_max": 80.0,
        "wilting_point": 35.0,
        "temp_min": 15.0,
        "temp_max": 25.0,
        "n_target_ppm": 180.0,
        "p_target_ppm": 100.0,
        "k_target_ppm": 150.0,
        "kc_factor": 1.10,
        "growth_stage": "Tuber Bulking",
        "notes": "Shallow root system; requires frequent, light irrigations to keep ridges moist."
    },
    {
        "crop_name": "Sugarcane",
        "category": "Cash Crop",
        "optimal_moisture_min": 60.0,
        "optimal_moisture_max": 85.0,
        "wilting_point": 35.0,
        "temp_min": 20.0,
        "temp_max": 40.0,
        "n_target_ppm": 250.0,
        "p_target_ppm": 100.0,
        "k_target_ppm": 120.0,
        "kc_factor": 1.25,
        "growth_stage": "Grand Growth",
        "notes": "High water and nutrient demanding crop. Drip fertigation increases yield by 40%."
    }
]

def seed_default_crops(db: Session):
    for crop_data in DEFAULT_CROPS:
        existing = db.query(CropProfile).filter(CropProfile.crop_name == crop_data["crop_name"]).first()
        if not existing:
            crop = CropProfile(**crop_data)
            db.add(crop)
    db.commit()

@router.get("", response_model=List[CropProfileSchema])
def list_crops(db: Session = Depends(get_db)):
    """List all supported crops and their agronomic profiles."""
    crops = db.query(CropProfile).all()
    if not crops:
        seed_default_crops(db)
        crops = db.query(CropProfile).all()
    return crops

@router.get("/{crop_name}", response_model=CropProfileSchema)
def get_crop(crop_name: str, db: Session = Depends(get_db)):
    """Retrieve optimal moisture and fertilizer profile for a given crop."""
    crop = db.query(CropProfile).filter(CropProfile.crop_name.ilike(crop_name)).first()
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_name}' not found.")
    return crop
