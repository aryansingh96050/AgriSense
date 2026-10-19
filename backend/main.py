import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import init_db, get_db
from models import (
    Telemetry, Alert, NodeSettings,
    TelemetryIn, TelemetryOut, AdvisoryResult,
    SettingsUpdate, PumpOverrideRequest
)
from agronomy_engine import AgronomyEngine, CROPS_DB
from notifier import notifier

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agrisense.main")

# Initialize database
init_db()

app = FastAPI(
    title="AgriSense: Smart Irrigation & Fertilization Advisor",
    description="IoT + Cloud API for Precision Agriculture & Farmer Advisory",
    version="1.0.0"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

manager = ConnectionManager()

# Global state for pump command
CURRENT_PUMP_COMMAND = False

# ================= REST ENDPOINTS =================

@app.get("/api/health")
def health_check():
    return {"status": "online", "service": "AgriSense Core API", "version": "1.0.0"}

@app.get("/api/crops")
def get_crops():
    """Returns database of supported crops and their growth stages"""
    return CROPS_DB

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(NodeSettings).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings

@app.post("/api/settings")
def update_settings(update: SettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(NodeSettings).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    if update.active_crop is not None:
        if update.active_crop in CROPS_DB:
            settings.active_crop = update.active_crop
            # set default stage for this crop
            first_stage = next(iter(CROPS_DB[update.active_crop]["stages"].keys()))
            settings.active_stage = first_stage
    if update.active_stage is not None:
        settings.active_stage = update.active_stage
    if update.auto_pump_enabled is not None:
        settings.auto_pump_enabled = update.auto_pump_enabled
    if update.farmer_phone is not None:
        settings.farmer_phone = update.farmer_phone
    if update.farmer_name is not None:
        settings.farmer_name = update.farmer_name
    if update.field_size_acres is not None:
        settings.field_size_acres = update.field_size_acres

    db.commit()
    db.refresh(settings)
    return settings

@app.post("/api/telemetry")
async def receive_telemetry(payload: TelemetryIn, db: Session = Depends(get_db)):
    """
    Ingests sensor readings from the ESP32 node or Simulator,
    runs the Agronomy Advisory Engine, controls pump if auto mode is ON,
    and dispatches bilingual SMS/WhatsApp if necessary.
    """
    global CURRENT_PUMP_COMMAND
    settings = db.query(NodeSettings).first()

    # 1. Run Agronomy Advisory Engine
    advisory = AgronomyEngine.evaluate(
        crop_key=settings.active_crop,
        stage_key=settings.active_stage,
        moisture=payload.moisture,
        temperature=payload.temperature,
        ph=payload.ph,
        n=payload.nitrogen,
        p=payload.phosphorus,
        k=payload.potassium,
        field_size_acres=settings.field_size_acres,
        farmer_name=settings.farmer_name
    )

    # 2. Automated Irrigation Logic
    pump_state = payload.pump_active
    if settings.auto_pump_enabled:
        if advisory.irrigation_urgency in ("URGENT", "NORMAL"):
            CURRENT_PUMP_COMMAND = True
            pump_state = True
        elif advisory.irrigation_urgency in ("NOT_NEEDED", "WATERLOGGED"):
            CURRENT_PUMP_COMMAND = False
            pump_state = False
    else:
        # Manual override state
        pump_state = settings.pump_override_state
        CURRENT_PUMP_COMMAND = settings.pump_override_state

    # 3. Save Telemetry Record to Database
    record = Telemetry(
        device_id=payload.device_id,
        moisture=payload.moisture,
        temperature=payload.temperature,
        ph=payload.ph,
        nitrogen=payload.nitrogen,
        phosphorus=payload.phosphorus,
        potassium=payload.potassium,
        ec=payload.ec or 0.0,
        battery_voltage=payload.battery_voltage or 3.9,
        battery_percentage=payload.battery_percentage or 85,
        pump_active=pump_state,
        sensor_status=payload.sensor_status or "OK"
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # 4. Check for Alert Dispatch conditions (with cooldown to prevent spamming)
    now = datetime.utcnow()
    cooldown = timedelta(minutes=settings.alert_cooldown_mins)
    
    # Irrigation Alert Trigger
    should_alert_irrig = (
        advisory.irrigation_needed and 
        (settings.last_irrigation_alert is None or (now - settings.last_irrigation_alert) > cooldown)
    )

    if should_alert_irrig:
        settings.last_irrigation_alert = now
        # Dispatch SMS & WhatsApp
        notifier.send_sms(settings.farmer_phone, advisory.sms_text_hi)
        notifier.send_whatsapp(settings.farmer_phone, advisory.whatsapp_text_hi)
        
        # Log alert to DB
        alert_db = Alert(
            device_id=payload.device_id,
            alert_type="IRRIGATION",
            severity="CRITICAL" if advisory.irrigation_urgency == "URGENT" else "WARNING",
            message_en=advisory.sms_text_en,
            message_hi=advisory.sms_text_hi,
            channels_sent="SMS,WHATSAPP",
            delivery_status="DISPATCHED"
        )
        db.add(alert_db)

    # Fertilizer Alert Trigger
    should_alert_fert = (
        advisory.fertilizer_action_needed and
        (settings.last_fertilizer_alert is None or (now - settings.last_fertilizer_alert) > cooldown)
    )

    if should_alert_fert:
        settings.last_fertilizer_alert = now
        notifier.send_whatsapp(settings.farmer_phone, advisory.whatsapp_text_hi)
        alert_db2 = Alert(
            device_id=payload.device_id,
            alert_type="FERTILIZER",
            severity="WARNING",
            message_en=advisory.fertilizer_advice_en,
            message_hi=advisory.fertilizer_advice_hi,
            channels_sent="WHATSAPP",
            delivery_status="DISPATCHED"
        )
        db.add(alert_db2)

    db.commit()

    # 5. Broadcast to WebSockets
    ws_payload = {
        "type": "TELEMETRY_UPDATE",
        "telemetry": {
            "id": record.id,
            "timestamp": record.timestamp.isoformat(),
            "device_id": record.device_id,
            "moisture": record.moisture,
            "temperature": record.temperature,
            "ph": record.ph,
            "nitrogen": record.nitrogen,
            "phosphorus": record.phosphorus,
            "potassium": record.potassium,
            "ec": record.ec,
            "battery_voltage": record.battery_voltage,
            "battery_percentage": record.battery_percentage,
            "pump_active": pump_state,
            "sensor_status": record.sensor_status
        },
        "advisory": advisory.dict()
    }
    await manager.broadcast(ws_payload)

    # 6. Response returned to ESP32 node
    return {
        "status": "success",
        "command_pump": CURRENT_PUMP_COMMAND,
        "recorded_id": record.id,
        "irrigation_needed": advisory.irrigation_needed,
        "pump_minutes": advisory.recommended_pump_run_minutes
    }

@app.get("/api/telemetry/latest")
def get_latest_telemetry(db: Session = Depends(get_db)):
    record = db.query(Telemetry).order_by(Telemetry.id.desc()).first()
    settings = db.query(NodeSettings).first()
    
    if not record:
        # Default mock if empty
        return {
            "telemetry": None,
            "advisory": None,
            "settings": settings
        }

    advisory = AgronomyEngine.evaluate(
        crop_key=settings.active_crop,
        stage_key=settings.active_stage,
        moisture=record.moisture,
        temperature=record.temperature,
        ph=record.ph,
        n=record.nitrogen,
        p=record.phosphorus,
        k=record.potassium,
        field_size_acres=settings.field_size_acres,
        farmer_name=settings.farmer_name
    )

    return {
        "telemetry": record,
        "advisory": advisory,
        "settings": settings
    }

@app.get("/api/telemetry/history")
def get_telemetry_history(limit: int = 40, db: Session = Depends(get_db)):
    records = db.query(Telemetry).order_by(Telemetry.id.desc()).limit(limit).all()
    return list(reversed(records))

@app.post("/api/pump/toggle")
async def toggle_pump(req: PumpOverrideRequest, db: Session = Depends(get_db)):
    global CURRENT_PUMP_COMMAND
    settings = db.query(NodeSettings).first()
    settings.auto_pump_enabled = False  # Switch to manual override
    settings.pump_override_state = req.state
    CURRENT_PUMP_COMMAND = req.state
    db.commit()

    # Broadcast pump state change
    await manager.broadcast({
        "type": "PUMP_OVERRIDE",
        "pump_active": req.state,
        "auto_pump_enabled": False
    })

    return {
        "status": "success",
        "pump_active": req.state,
        "auto_pump_enabled": False,
        "message": f"Pump manually switched {'ON' if req.state else 'OFF'}"
    }

@app.post("/api/alerts/test")
def send_test_alert(channel: str = "both", db: Session = Depends(get_db)):
    """Triggers an on-demand test alert to the farmer's WhatsApp and SMS inbox"""
    settings = db.query(NodeSettings).first()
    latest = db.query(Telemetry).order_by(Telemetry.id.desc()).first()
    
    m = latest.moisture if latest else 28.5
    t = latest.temperature if latest else 26.0
    ph = latest.ph if latest else 6.5
    n = latest.nitrogen if latest else 85.0
    p = latest.phosphorus if latest else 28.0
    k = latest.potassium if latest else 32.0

    advisory = AgronomyEngine.evaluate(
        crop_key=settings.active_crop,
        stage_key=settings.active_stage,
        moisture=m,
        temperature=t,
        ph=ph,
        n=n,
        p=p,
        k=k,
        field_size_acres=settings.field_size_acres,
        farmer_name=settings.farmer_name
    )

    sms_res = None
    wa_res = None

    if channel in ("both", "sms"):
        sms_res = notifier.send_sms(settings.farmer_phone, advisory.sms_text_hi)
    if channel in ("both", "whatsapp"):
        wa_res = notifier.send_whatsapp(settings.farmer_phone, advisory.whatsapp_text_hi)

    return {
        "status": "success",
        "sms_sent": sms_res,
        "whatsapp_sent": wa_res
    }

@app.get("/api/alerts/inbox")
def get_simulated_inbox():
    return notifier.get_simulated_inbox()

@app.get("/api/alerts/history")
def get_alerts_history(db: Session = Depends(get_db)):
    alerts = db.query(Alert).order_by(Alert.id.desc()).limit(30).all()
    return alerts

# ================= WEBSOCKET STREAM =================

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for ping or client commands
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# ================= STATIC FRONTEND FILES =================

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "AgriSense Frontend is being assembled."}
