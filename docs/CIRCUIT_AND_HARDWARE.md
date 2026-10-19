# AgriSense Hardware & Circuit Design Specification

Low-Cost IoT Edge Node for Soil Moisture, Temperature, pH, and NPK Sensing.

---

## 1. Bill of Materials (BOM) & Low-Cost Analysis

| Component | Specification | Estimated Cost (INR) | Estimated Cost (USD) | Function |
| :--- | :--- | :--- | :--- | :--- |
| **Microcontroller** | ESP32-WROOM-32 (NodeMCU-32S) | ₹380 | $4.50 | Wi-Fi/BLE, Ultra-Low Deep Sleep (<10µA), Dual Core |
| **Soil NPK + pH Probe** | RS485 Modbus RTU 7-in-1 / 5-in-1 Soil Sensor | ₹1,800 | $21.50 | Measures N, P, K, pH, Moisture, Temp, EC simultaneously |
| **RS485 Transceiver** | MAX485 TTL to RS485 Module | ₹35 | $0.45 | Converts ESP32 UART TTL levels to RS485 differential signals |
| **Backup Moisture Sensor** | Capacitive Soil Moisture Sensor v1.2 | ₹80 | $0.95 | Corrosion-resistant analog moisture verification |
| **Actuator Control** | 1-Channel 5V/3.3V Optocoupler Relay Module | ₹65 | $0.80 | Controls 12V DC Solenoid Valve or 220V AC Submersible Pump |
| **Power Management** | TP4056 1A Li-ion Charger with BMS protection | ₹30 | $0.35 | Protects battery against overcharge and overdischarge |
| **Battery** | 18650 Rechargeable Li-ion (3.7V, 2600mAh) | ₹160 | $1.90 | Powers node during night and cloudy days |
| **Solar Panel** | 5V / 6V 3W Monocrystalline Mini Solar Panel | ₹250 | $3.00 | Continuous solar energy harvesting in the field |
| **Passive Components** | 100kΩ Resistors (x2), 0.1µF Caps, Terminal Blocks | ₹20 | $0.25 | Battery voltage divider & decoupling filter |
| **Weatherproof Enclosure** | IP65 Waterproof Electrical Junction Box | ₹180 | $2.20 | Protects electronics from rain, dust, and direct sunlight |
| **Total Estimated Cost** | **Complete Smart Field Node** | **~₹3,000** | **~$36.00** | **Ready for deployment** |

---

## 2. Wiring & Pinout Mapping

### A. ESP32 to MAX485 & 7-in-1 RS485 Soil Sensor
| ESP32 Pin | MAX485 Pin | NPK Sensor Wire Color | Notes |
| :--- | :--- | :--- | :--- |
| **3.3V / 5V** | VCC | - | Power supply for MAX485 module |
| **GND** | GND | Black (GND) | Common ground reference |
| **GPIO 16 (RX2)** | RO (Receiver Output) | - | UART2 Data In |
| **GPIO 17 (TX2)** | DI (Driver Input) | - | UART2 Data Out |
| **GPIO 4** | DE & RE (shorted together) | - | HIGH = Transmit, LOW = Receive |
| - | **A+** | Yellow (A / 485-A) | RS485 Differential A |
| - | **B-** | Blue (B / 485-B) | RS485 Differential B |
| **External 5V-12V**| - | Brown (VCC+) | Sensor supply voltage (DC 5V-30V) |

### B. Relay & Backup Sensors
| ESP32 Pin | Component Pin | Function |
| :--- | :--- | :--- |
| **GPIO 18** | Relay IN | Triggers irrigation solenoid valve or pump relay |
| **GPIO 34 (ADC1_CH6)** | Capacitive Sensor AOUT | Analog backup soil moisture percentage |
| **GPIO 35 (ADC1_CH7)** | Battery Voltage Divider (Center) | Reads battery voltage (100kΩ to VBAT, 100kΩ to GND) |
| **GPIO 2** | Built-in LED | Visual status indicator (Blinks on telemetry transmission) |

---

## 3. Power Consumption & Battery Life Analysis

- **Active State (Sensor Reading + WiFi Transmit)**: ~120 mA for 4 seconds.
- **Deep Sleep State (RTC Only)**: ~15 µA (0.015 mA) for 15 minutes (896 seconds).
- **Average Current Calculation**:
  $$\text{Duty Cycle} = \frac{4}{900} = 0.00444$$
  $$I_{\text{avg}} = (120 \times 0.00444) + (0.015 \times 0.99556) \approx 0.533 \text{ mA} + 0.015 \text{ mA} \approx 0.55 \text{ mA}$$
- **Run-time without Solar Charging**:
  $$\text{Hours} = \frac{2600 \text{ mAh}}{0.55 \text{ mA}} \approx 4,727 \text{ hours} \approx \mathbf{197 \text{ days!}}$$
- **With 3W Solar Panel**: The node operates **perpetually self-powered** without requiring manual recharging.

---

## 4. ASCII Circuit Schematic

```
               +---------------------------------------------------+
               |               SOLAR HARVESTING                    |
               |                                                   |
               |   [ 6V 3W Solar Panel ]                           |
               |           |                                       |
               |           v                                       |
               |   [ TP4056 Charger & BMS ] <---> [ 18650 Li-ion ] |
               |           |                         (3.7V 2600mAh)|
               |           +-------------------+                   |
               |                               |                   |
               +-------------------------------|-------------------+
                                               | (3.7V - 4.2V VBAT)
                                               v
        +--------------------------------------------------------------+
        |                                                              |
        |                      ESP32 DEVKIT V1                         |
        |                                                              |
        |  [3.3V]       [GND]      [GPIO 16/17]     [GPIO 4]  [GPIO 18]|
        +---|-------------|-------------|--------------|----------|----+
            |             |             |              |          |
            |             |        RO / DI          DE + RE       |
            |             |             |              |          |
            v             v             v              v          v
       +-----------------------+                            [ 5V Relay ]
       |     MAX485 MODULE     |                                  |
       |  VCC  GND   A+   B-   |                                  v
       +---|----|----|----|----+                          [ Solenoid Valve ]
           |    |    |    |
           |    +----+----|--------------------+
           |         |    |                    |
           |         v    v                    v
           |     [ Yellow | Blue ]        [ Black/GND ]
           |            |                      |
           |            +----------------------+
           |                       |
           +------------> [ 7-in-1 Soil Sensor ] <--- External 9V-12V (Brown)
                          (NPK + pH + Moisture + Temp + EC)
```
