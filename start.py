import os
import sys
import time
import threading
import webbrowser
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable

def start_backend():
    print("[AgriSense] Launching FastAPI Backend on http://localhost:8000 ...")
    backend_cmd = [
        VENV_PYTHON, "-m", "uvicorn", "backend.main:app",
        "--host", "0.0.0.0", "--port", "8000"
    ]
    return subprocess.Popen(backend_cmd, cwd=PROJECT_DIR)

def start_simulator():
    print("[AgriSense] Launching Virtual IoT Soil Sensor Node Simulator ...")
    sim_script = os.path.join(PROJECT_DIR, "iot_simulator", "sensor_simulator.py")
    sim_cmd = [VENV_PYTHON, sim_script, "--interval", "6"]
    return subprocess.Popen(sim_cmd, cwd=PROJECT_DIR)

def main():
    print("=" * 65)
    print("  🌾 AgriSense: IoT + Cloud Smart Irrigation & Fertilization Advisor")
    print("=" * 65)
    
    # 1. Start Backend
    backend_proc = start_backend()
    time.sleep(3)  # Wait for uvicorn to initialize

    # 2. Open Web Dashboard in default browser
    url = "http://localhost:8000"
    print(f"\n[AgriSense] Opening dashboard at {url} ...")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")

    # 3. Start IoT Node Simulator
    time.sleep(1)
    sim_proc = start_simulator()

    print("\n✅ AgriSense System is LIVE and fully active!")
    print("👉 Web Dashboard: http://localhost:8000")
    print("👉 API Documentation: http://localhost:8000/docs")
    print("👉 Press Ctrl+C in this terminal to safely stop the system.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[AgriSense] Shutting down services...")
        sim_proc.terminate()
        backend_proc.terminate()
        print("[AgriSense] Stopped.")

if __name__ == "__main__":
    main()
