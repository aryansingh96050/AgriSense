from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.db_models import ActuatorState, IrrigationLog
from ..models.schemas import ActuatorCommand, ActuatorResponse
from ..services.websocket_manager import ws_manager

router = APIRouter(prefix="/actuators", tags=["Actuators & Control"])

@router.get("/status", response_model=ActuatorResponse)
def get_actuator_status(device_id: str = "ESP32_NODE_01", db: Session = Depends(get_db)):
    """Fetch the current state of pump, valve, and automated control mode."""
    actuator = db.query(ActuatorState).filter(ActuatorState.device_id == device_id).first()
    if not actuator:
        actuator = ActuatorState(
            device_id=device_id,
            pump_on=False,
            valve_open=False,
            auto_mode=True,
            active_crop="Wheat",
            field_area_acres=1.0
        )
        db.add(actuator)
        db.commit()
        db.refresh(actuator)
    return actuator

@router.post("/control", response_model=ActuatorResponse)
async def update_actuator_state(
    cmd: ActuatorCommand,
    device_id: str = "ESP32_NODE_01",
    db: Session = Depends(get_db)
):
    """
    Control actuators manually or adjust automation parameters (crop, field size, auto mode).
    """
    actuator = db.query(ActuatorState).filter(ActuatorState.device_id == device_id).first()
    if not actuator:
        actuator = ActuatorState(device_id=device_id)
        db.add(actuator)

    if cmd.auto_mode is not None:
        actuator.auto_mode = cmd.auto_mode

    if cmd.pump_on is not None and cmd.pump_on != actuator.pump_on:
        actuator.pump_on = cmd.pump_on
        actuator.last_switched = datetime.now(timezone.utc)
        # Log manual override
        db.add(IrrigationLog(
            device_id=device_id,
            event_type="MANUAL_ON" if cmd.pump_on else "MANUAL_OFF",
            trigger_reason="User manual toggle from AgriSense Dashboard"
        ))

    if cmd.valve_open is not None:
        actuator.valve_open = cmd.valve_open

    if cmd.active_crop is not None:
        actuator.active_crop = cmd.active_crop

    if cmd.field_area_acres is not None:
        actuator.field_area_acres = cmd.field_area_acres

    db.commit()
    db.refresh(actuator)

    # Broadcast actuator update to all clients
    await ws_manager.broadcast_json({
        "event": "ACTUATOR_UPDATED",
        "actuator": {
            "device_id": actuator.device_id,
            "pump_on": actuator.pump_on,
            "valve_open": actuator.valve_open,
            "auto_mode": actuator.auto_mode,
            "active_crop": actuator.active_crop,
            "field_area_acres": actuator.field_area_acres
        }
    })

    return actuator
