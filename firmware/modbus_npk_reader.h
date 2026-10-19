#ifndef MODBUS_NPK_READER_H
#define MODBUS_NPK_READER_H

#include <Arduino.h>

/**
 * AgriSense - Modbus RTU Reader for Soil Sensors
 * Supports standard Chinese 5-in-1 / 7-in-1 RS485 Soil Sensors:
 * - Nitrogen (N) (mg/kg or mg/L)
 * - Phosphorus (P) (mg/kg)
 * - Potassium (K) (mg/kg)
 * - Soil pH (0.1 resolution)
 * - Soil Moisture (%)
 * - Soil Temperature (°C)
 * - Soil Electrical Conductivity (EC) (us/cm)
 */

struct SoilMetrics {
    float moisture;     // in % (0 - 100%)
    float temperature;  // in °C (-40 to +80°C)
    float ph;           // pH scale (3.0 - 10.0)
    uint16_t nitrogen;  // mg/kg
    uint16_t phosphorus;// mg/kg
    uint16_t potassium; // mg/kg
    uint16_t ec;        // us/cm
    bool valid;         // true if CRC and read succeeded
};

class ModbusSoilReader {
private:
    HardwareSerial* _serial;
    uint8_t _deRePin;
    uint8_t _slaveId;

    // Calculate Modbus RTU CRC16
    uint16_t calculateCRC(const uint8_t *buf, int len) {
        uint16_t crc = 0xFFFF;
        for (int pos = 0; pos < len; pos++) {
            crc ^= (uint16_t)buf[pos];
            for (int i = 8; i != 0; i--) {
                if ((crc & 0x0001) != 0) {
                    crc >>= 1;
                    crc ^= 0xA001;
                } else {
                    crc >>= 1;
                }
            }
        }
        return crc;
    }

public:
    ModbusSoilReader(HardwareSerial* serialPort, uint8_t deRePin, uint8_t slaveAddress = 0x01) {
        _serial = serialPort;
        _deRePin = deRePin;
        _slaveId = slaveAddress;
    }

    void begin(unsigned long baudRate = 4800, int rxPin = 16, int txPin = 17) {
        pinMode(_deRePin, OUTPUT);
        digitalWrite(_deRePin, LOW); // Set MAX485 to receiver mode
        _serial->begin(baudRate, SERIAL_8N1, rxPin, txPin);
    }

    SoilMetrics readAll() {
        SoilMetrics result = {0.0f, 0.0f, 0.0f, 0, 0, 0, 0, false};

        // Query frame to read 7 holding registers starting at 0x0000:
        // [Slave ID, Function Code 0x03, Start High, Start Low, Reg Count High, Reg Count Low, CRC Low, CRC High]
        uint8_t query[8] = {_slaveId, 0x03, 0x00, 0x00, 0x00, 0x07, 0x00, 0x00};
        uint16_t crc = calculateCRC(query, 6);
        query[6] = crc & 0xFF;
        query[7] = (crc >> 8) & 0xFF;

        // Flush input buffer
        while (_serial->available()) {
            _serial->read();
        }

        // Enable TX mode
        digitalWrite(_deRePin, HIGH);
        delayMicroseconds(200);
        _serial->write(query, sizeof(query));
        _serial->flush();
        digitalWrite(_deRePin, LOW); // Return to RX mode
        delayMicroseconds(200);

        // Wait for response: 1 (ID) + 1 (FC) + 1 (Byte count = 14) + 14 (Data) + 2 (CRC) = 19 bytes
        uint8_t response[25];
        unsigned long startTime = millis();
        int bytesRead = 0;

        while (millis() - startTime < 1000 && bytesRead < 19) {
            if (_serial->available()) {
                response[bytesRead++] = _serial->read();
            }
        }

        if (bytesRead >= 19 && response[0] == _slaveId && response[1] == 0x03 && response[2] == 14) {
            uint16_t recvCrc = response[17] | (response[18] << 8);
            uint16_t calcCrc = calculateCRC(response, 17);

            if (recvCrc == calcCrc) {
                // High byte | Low byte parsing
                result.moisture    = ((response[3] << 8) | response[4]) * 0.1f;
                int16_t rawTemp    = ((response[5] << 8) | response[6]);
                result.temperature = rawTemp * 0.1f;
                result.ec          = ((response[7] << 8) | response[8]);
                result.ph          = ((response[9] << 8) | response[10]) * 0.1f;
                result.nitrogen    = ((response[11] << 8) | response[12]);
                result.phosphorus  = ((response[13] << 8) | response[14]);
                result.potassium   = ((response[15] << 8) | response[16]);
                result.valid       = true;
            }
        }

        return result;
    }
};

#endif // MODBUS_NPK_READER_H
