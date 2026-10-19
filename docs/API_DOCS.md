# AgriSense REST & WebSocket API Documentation

Base URL: `http://localhost:8000`

---

## 1. IoT Sensor Telemetry Ingestion

### `POST /api/telemetry`
Called by the ESP32 field node or IoT Simulator every 5-15 minutes.

#### Request Headers
```http
Content-Type: application/json
X-Device-Token: agrisense_secret_token_123
```

#### Request Body
```json
{
  "device_id": "AGRI-NODE-001",
  "moisture": 24.5,
  "temperature": 27.2,
  "ph": 6.8,
  "nitrogen": 85.0,
  "phosphorus": 32.0,
  "potassium": 38.0,
  "ec": 410.0,
  "battery_voltage": 4.02,
  "battery_percentage": 89,
  "pump_active": false,
  "sensor_status": "MODBUS_OK"
}
```

#### Response (`200 OK`)
```json
{
  "status": "success",
  "command_pump": true,
  "recorded_id": 42,
  "irrigation_needed": true,
  "pump_minutes": 55
}
```
*The ESP32 reads `command_pump` to immediately switch the onboard relay ON or OFF.*

---

## 2. Farmer Advisory & Status Endpoints

### `GET /api/telemetry/latest`
Fetches the latest field telemetry reading along with real-time agronomic calculations.

### `GET /api/telemetry/history?limit=30`
Returns historical records for 24-hour charting.

### `GET /api/crops`
Returns supported crop profiles (Wheat, Rice, Tomato, Cotton, Potato, Sugarcane) with optimal moisture and NPK targets per growth stage.

### `GET /api/settings` & `POST /api/settings`
Updates active crop, stage, field size in acres, and farmer phone number.

### `POST /api/pump/toggle`
Manual remote override for the water pump.
```json
{
  "state": true
}
```

### `POST /api/alerts/test`
Manually triggers an on-demand test alert to the farmer's WhatsApp and SMS inbox.

### `GET /api/alerts/inbox`
Returns simulated smartphone message history for immediate dashboard verification.

---

## 3. Real-Time WebSocket Streaming

### `WebSocket /ws/live`
Clients (Dashboard) connect to receive live pushes whenever new telemetry is received or pump status changes.
```json
{
  "type": "TELEMETRY_UPDATE",
  "telemetry": { ... },
  "advisory": { ... }
}
```
