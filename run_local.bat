@echo off
TITLE AgriSense: Smart Irrigation & Fertilization Advisor
echo ============================================================
echo   🌾 Launching AgriSense Localhost Server
echo ============================================================

REM Check if venv exists
IF NOT EXIST "venv" (
    echo [INFO] Creating Python virtual environment (venv)...
    python -m venv venv
)

echo [INFO] Activating virtual environment...
CALL venv\Scripts\activate

echo [INFO] Installing / Updating dependencies...
pip install -r requirements.txt --quiet

echo.
echo ============================================================
echo   AgriSense Dashboard URL : http://localhost:8000
echo   Interactive API Docs   : http://localhost:8000/docs
echo ============================================================
echo.

REM Open browser in 2 seconds
start "" http://localhost:8000

REM Run FastAPI Uvicorn Server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

pause
