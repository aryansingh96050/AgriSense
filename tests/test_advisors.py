import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.database import Base
from backend.app.models.db_models import TelemetryReading, ActuatorState, CropProfile
from backend.app.services.irrigation_advisor import irrigation_advisor
from backend.app.services.fertilizer_advisor import fertilizer_advisor
from backend.app.main import app

# Test SQLite in-memory database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Seed default crop
    crop = CropProfile(
        crop_name="Wheat",
        category="Cereal",
        optimal_moisture_min=50.0,
        optimal_moisture_max=70.0,
        wilting_point=30.0,
        temp_min=15.0,
        temp_max=32.0,
        n_target_ppm=120.0,
        p_target_ppm=60.0,
        k_target_ppm=40.0,
        kc_factor=1.05,
        growth_stage="Tillering"
    )
    actuator = ActuatorState(
        device_id="ESP32_TEST_01",
        pump_on=False,
        valve_open=False,
        auto_mode=True,
        active_crop="Wheat",
        field_area_acres=1.0
    )
    session.add(crop)
    session.add(actuator)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)

def test_irrigation_advisor_optimal(db):
    reading = TelemetryReading(
        device_id="ESP32_TEST_01",
        soil_moisture=60.0,
        temperature=25.0,
        humidity=60.0,
        nitrogen=50.0,
        phosphorus=30.0,
        potassium=150.0,
        ph_level=6.8
    )
    db.add(reading)
    db.commit()

    advice = irrigation_advisor.evaluate(db, device_id="ESP32_TEST_01")
    assert advice.status == "OPTIMAL"
    assert advice.pump_recommended is False
    assert advice.urgency == "NONE"

def test_irrigation_advisor_critical_drought(db):
    reading = TelemetryReading(
        device_id="ESP32_TEST_01",
        soil_moisture=18.0, # Below wilting point of 30%
        temperature=35.0,
        humidity=30.0,
        nitrogen=30.0,
        phosphorus=15.0,
        potassium=100.0,
        ph_level=6.5
    )
    db.add(reading)
    db.commit()

    advice = irrigation_advisor.evaluate(db, device_id="ESP32_TEST_01")
    assert advice.status == "CRITICAL_DROUGHT"
    assert advice.pump_recommended is True
    assert advice.urgency == "CRITICAL"
    assert advice.estimated_water_liters > 0
    assert advice.recommended_duration_minutes > 0

def test_fertilizer_advisor_dosage_calculation(db):
    reading = TelemetryReading(
        device_id="ESP32_TEST_01",
        soil_moisture=55.0,
        temperature=26.0,
        humidity=55.0,
        nitrogen=20.0, # Low N
        phosphorus=10.0, # Low P
        potassium=50.0, # Low K
        ph_level=6.5
    )
    db.add(reading)
    db.commit()

    fert = fertilizer_advisor.evaluate(db, device_id="ESP32_TEST_01")
    assert fert.crop_name == "Wheat"
    assert fert.urea_kg > 0
    assert fert.dap_kg > 0
    assert fert.mop_kg > 0
    assert len(fert.organic_options) > 0

def test_health_check_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
