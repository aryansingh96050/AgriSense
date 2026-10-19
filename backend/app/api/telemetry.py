from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import random

from ..database import get_db
from ..models.db_models import TelemetryReading, ActuatorState
from ..models.schemas import TelemetryCreate, TelemetryResponse, SimulationTrigger
from ..services.websocket_manager import ws_manager
from ..services.irrigation_advisor import irrigation_advisor

router = APIRouter(prefix="/telemetry", tags=["IoT Telemetry"])

@router.post("", response_model=dict)
async def ingest_telemetry(payload: TelemetryCreate, db: Session = Depends(get_db)):
    """
    Ingest live sensor telemetry from ESP32 hardware or IoT simulator.
    Evaluates irrigation rules and returns pump command status to the device.
    """
    reading = TelemetryReading(
        device_id=payload.device_id or "ESP32_NODE_01",
        soil_moisture=payload.soil_moisture,
        temperature=payload.temperature,
        humidity=payload.humidity,
        nitrogen=payload.nitrogen or 45.0,
        phosphorus=payload.phosphorus or 30.0,
        potassium=payload.potassium or 150.0,
        ph_level=payload.ph_level or 6.8,
        battery_level=payload.battery_level or 95.0,
        signal_rssi=payload.signal_rssi or -65,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # Evaluate intelligent irrigation logic
    advice = irrigation_advisor.evaluate(db, device_id=payload.device_id or "ESP32_NODE_01")

    # Fetch updated actuator state for hardware command response
    actuator = db.query(ActuatorState).filter(ActuatorState.device_id == (payload.device_id or "ESP32_NODE_01")).first()
    pump_status = actuator.pump_on if actuator else False

    # Broadcast via WebSocket to dashboard
    broadcast_payload = {
        "event": "NEW_TELEMETRY",
        "data": {
            "id": reading.id,
            "timestamp": reading.timestamp.isoformat(),
            "device_id": reading.device_id,
            "soil_moisture": reading.soil_moisture,
            "temperature": reading.temperature,
            "humidity": reading.humidity,
            "nitrogen": reading.nitrogen,
            "phosphorus": reading.phosphorus,
            "potassium": reading.potassium,
            "ph_level": reading.ph_level,
            "battery_level": reading.battery_level,
            "signal_rssi": reading.signal_rssi
        },
        "actuator": {
            "pump_on": pump_status,
            "valve_open": actuator.valve_open if actuator else False,
            "auto_mode": actuator.auto_mode if actuator else True
        },
        "advice_summary": {
            "status": advice.status,
            "urgency": advice.urgency,
            "advice_text": advice.advice_text
        }
    }
    await ws_manager.broadcast_json(broadcast_payload)

    return {
        "status": "success",
        "id": reading.id,
        "device_id": reading.device_id,
        "pump_command": "ON" if pump_status else "OFF",
        "valve_command": "OPEN" if (actuator and actuator.valve_open) else "CLOSED",
        "advice_status": advice.status
    }

@router.get("/latest", response_model=TelemetryResponse)
def get_latest_telemetry(device_id: str = "ESP32_NODE_01", db: Session = Depends(get_db)):
    """Fetch the latest telemetry packet for an IoT node."""
    reading = (
        db.query(TelemetryReading)
        .filter(TelemetryReading.device_id == device_id)
        .order_by(TelemetryReading.timestamp.desc())
        .first()
    )
    if not reading:
        # Generate initial reading if database is empty
        reading = TelemetryReading(
            device_id=device_id,
            soil_moisture=48.5,
            temperature=27.2,
            humidity=58.0,
            nitrogen=42.0,
            phosphorus=28.0,
            potassium=145.0,
            ph_level=6.7,
            battery_level=98.0,
            signal_rssi=-62
        )
        db.add(reading)
        db.commit()
        db.refresh(reading)
    return reading

@router.get("/history", response_model=List[TelemetryResponse])
def get_telemetry_history(
    limit: int = Query(default=25, ge=5, le=100),
    device_id: str = "ESP32_NODE_01",
    db: Session = Depends(get_db)
):
    """Fetch chronological history for visualization graphs."""
    readings = (
        db.query(TelemetryReading)
        .filter(TelemetryReading.device_id == device_id)
        .order_by(TelemetryReading.timestamp.desc())
        .limit(limit)
        .all()
    )
    # Return in ascending order for charts
    return list(reversed(readings))

@router.post("/simulate")
async def trigger_simulation_scenario(scenario: SimulationTrigger, db: Session = Depends(get_db)):
    """
    Inject a simulated environmental condition to test system response.
    """
    s = scenario.scenario.upper()
    if s == "HEATWAVE":
        moist, temp, hum, n, p, k = 28.0, 41.5, 24.0, 38.0, 22.0, 130.0
    elif s == "HEAVY_RAIN":
        moist, temp, hum, n, p, k = 88.0, 22.0, 94.0, 35.0, 20.0, 125.0
    elif s == "SOIL_DROUGHT":
        moist, temp, hum, n, p, k = 18.5, 34.0, 35.0, 30.0, 18.0, 110.0
    elif s == "LOW_NITROGEN":
        moist, temp, hum, n, p, k = 55.0, 28.0, 60.0, 12.0, 35.0, 160.0
    else: # OPTIMAL
        moist, temp, hum, n, p, k = 62.0, 26.5, 62.0, 65.0, 38.0, 175.0

    reading = TelemetryReading(
        device_id="ESP32_NODE_01",
        soil_moisture=moist,
        temperature=temp,
        humidity=hum,
        nitrogen=n,
        phosphorus=p,
        potassium=k,
        ph_level=6.8,
        battery_level=94.0,
        signal_rssi=-64
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    advice = irrigation_advisor.evaluate(db, device_id="ESP32_NODE_01")
    actuator = db.query(ActuatorState).filter(ActuatorState.device_id == "ESP32_NODE_01").first()

    broadcast_payload = {
        "event": "NEW_TELEMETRY",
        "data": {
            "id": reading.id,
            "timestamp": reading.timestamp.isoformat(),
            "device_id": reading.device_id,
            "soil_moisture": reading.soil_moisture,
            "temperature": reading.temperature,
            "humidity": reading.humidity,
            "nitrogen": reading.nitrogen,
            "phosphorus": reading.phosphorus,
            "potassium": reading.potassium,
            "ph_level": reading.ph_level,
            "battery_level": reading.battery_level,
            "signal_rssi": reading.signal_rssi
        },
        "actuator": {
            "pump_on": actuator.pump_on if actuator else False,
            "valve_open": actuator.valve_open if actuator else False,
            "auto_mode": actuator.auto_mode if actuator else True
        },
        "advice_summary": {
            "status": advice.status,
            "urgency": advice.urgency,
            "advice_text": advice.advice_text
        }
    }
    await ws_manager.broadcast_json(broadcast_payload)

    return {
        "status": "scenario_applied",
        "scenario": s,
        "values": {"moisture": moist, "temp": temp, "humidity": hum, "N": n, "P": p, "K": k},
        "advice_status": advice.status
    }
