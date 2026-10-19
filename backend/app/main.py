import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .database import engine, Base, SessionLocal
from .api import telemetry, advisory, actuators, crops
from .api.crops import seed_default_crops
from .services.websocket_manager import ws_manager

# Ensure tables are created
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed crop database
    db = SessionLocal()
    try:
        seed_default_crops(db)
    finally:
        db.close()
    yield
    # Shutdown logic if needed

app = FastAPI(
    title="AgriSense: IoT + Cloud Smart Irrigation & Fertilization Advisor",
    description="Intelligent Precision Agriculture Backend with IoT Ingestion, ETc Calculations, NPK Diagnostics, and Automated Actuators.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(telemetry.router, prefix=settings.API_V1_PREFIX)
app.include_router(advisory.router, prefix=settings.API_V1_PREFIX)
app.include_router(actuators.router, prefix=settings.API_V1_PREFIX)
app.include_router(crops.router, prefix=settings.API_V1_PREFIX)

# WebSocket for real-time telemetry streaming
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open; receive ping/messages if any
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

# Health Probe
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0"
    }

# Mount Static UI Files
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "AgriSense API is running. Visit /docs for the interactive API explorer."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
