#!/bin/bash
set -e

echo "============================================================"
echo "  🌾 Launching AgriSense Localhost Server"
echo "============================================================"

# Create venv if missing
if [ ! -d "venv" ]; then
    echo "[INFO] Creating Python virtual environment (venv)..."
    python3 -m venv venv
fi

# Activate venv
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "[INFO] Installing / Updating dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo "============================================================"
echo "  AgriSense Dashboard URL : http://localhost:8000"
echo "  Interactive API Docs   : http://localhost:8000/docs"
echo "============================================================"
echo ""

# Launch Uvicorn Server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
