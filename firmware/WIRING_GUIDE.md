# AgriSense: ESP32 Hardware Wiring & Calibration Guide

This guide details the physical hardware wiring between the ESP32 microcontroller, sensors, and actuators.

---

## 1. Components Bill of Materials (BOM)

| Component | Specification | Quantity |
| :--- | :--- | :--- |
| **Microcontroller** | ESP32 DevKit V1 (30-pin or 38-pin) | 1 |
| **Soil Moisture Sensor** | Capacitive Soil Moisture Sensor v1.2 (Corrosion resistant) | 1 |
| **Temp & Humidity Sensor** | DHT22 / AM2302 (Digital) | 1 |
| **Relay Module** | 5V 2-Channel Optocoupler Relay Module | 1 |
| **Water Pump** | 5V / 12V Mini Submersible Water Pump | 1 |
| **Power Supply** | 5V 2A DC Adapter or 18650 Battery Pack with BMS | 1 |
| **Flyback Diode** | 1N4007 (for inductive kickback protection) | 1 |
| **Resistor** | 10kΩ (pull-up for DHT22 data pin) | 1 |

---

## 2. Pin Connection Diagram

```
                 +-----------------------------------+
                 |           ESP32 DevKit            |
                 |                                   |
 (Analog Input)  | GPIO 34 (ADC1_CH6)                | <--- AOUT (Capacitive Moisture)
 (Digital I/O)   | GPIO 4                            | <--- DATA (DHT22)
 (Digital Output)| GPIO 26                           | ---> IN1 (Relay Channel 1: Pump)
 (Digital Output)| GPIO 27                           | ---> IN2 (Relay Channel 2: Valve)
 (Power Output)  | 3V3                               | ---> VCC (Sensors)
 (Power Output)  | VIN (5V)                          | ---> VCC (Relay Board)
 (Ground)        | GND                               | ---> Common GND
                 +-----------------------------------+
```

### Detailed Pin-by-Pin Table

| Sensor / Module | Module Pin | ESP32 Pin | Notes |
| :--- | :--- | :--- | :--- |
| **Capacitive Moisture v1.2** | VCC | 3V3 | Power with 3.3V to protect ADC |
| | GND | GND | Common ground |
| | AOUT | GPIO 34 | Analog-to-Digital input |
| **DHT22** | VCC (Pin 1) | 3V3 or 5V | Add 10kΩ pull-up between VCC & DATA |
| | DATA (Pin 2)| GPIO 4 | Digital bidirectional data |
| | NC (Pin 3) | Not connected | Leave floating |
| | GND (Pin 4) | GND | Common ground |
| **2-Channel Relay Module** | VCC | VIN (5V) | Power relay coils with 5V |
| | GND | GND | Common ground |
| | IN1 | GPIO 26 | Controls Submersible Pump |
| | IN2 | GPIO 27 | Controls Solenoid Valve |

---

## 3. Soil Moisture Sensor Calibration Procedure

Capacitive soil moisture sensors output an analog voltage inversely proportional to moisture. To calibrate:

1. **Air Measurement (0% Moisture)**:
   - Hold the clean probe dry in the air.
   - Note the serial monitor value for `analogRead(34)`. Typical reading: `~3100 - 3300`.
   - Update `AIR_VALUE` in `agrisense_esp32.ino`.

2. **Water Measurement (100% Moisture)**:
   - Dip the sensor blade up to the white marker line in a cup of clean tap water (do not submerge electronic components above the line).
   - Note the serial monitor reading. Typical reading: `~1350 - 1500`.
   - Update `WATER_VALUE` in `agrisense_esp32.ino`.

---

## 4. Relay & Water Pump Safety Notes
- Never power the water pump motor directly from the ESP32 GPIO pins. ESP32 pins provide max 12mA, whereas motors draw 500mA - 1500mA. Always switch power through the relay contacts (COM and NO).
- Keep 220V AC wiring isolated if you use an AC water pump.
