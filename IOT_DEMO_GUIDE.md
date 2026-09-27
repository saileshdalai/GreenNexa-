# GreenNexa — Wokwi & ESP32 Live IoT Integration Guide

This guide provides instructions and reference code for connecting physical or simulated microcontrollers (such as ESP32 devices on Wokwi or real hardware) to the GreenNexa IoT API.

---

## 1. System Architecture

```
+------------------+         +------------------+         +-------------------------+
|  ESP32 / Wokwi   |  Wi-Fi  |  GreenNexa API   |  HTTPS  |    GreenNexa Database   |
|   Sensors Node   | ------> | /api/v1/iot/...  | ------> | & Intelligent Dashboard |
+------------------+         +------------------+         +-------------------------+
```

1. **Microcontroller**: Measures environmental metrics (Energy, Water, Temp, Humidity, CO2, Waste) or simulates sensor hardware.
2. **Transport**: Sends HTTP POST requests over Wi-Fi / HTTPS.
3. **Authentication**: Authenticates using secure per-device headers (`X-Device-ID` and `X-API-Key`).
4. **Ingestion**: GreenNexa API validates device credentials, stores readings in the database, and processes anomaly detection in real time.

---

## 2. Ingestion API Endpoint Specification

- **Endpoint**: `POST /api/v1/iot/sensor-data`
- **Content-Type**: `application/json`

### Required HTTP Headers
| Header Name | Value / Description |
|-------------|---------------------|
| `Content-Type` | `application/json` |
| `X-Device-ID` | Your registered IoT Device ID (e.g., `DEV-CAMPUS-01`) |
| `X-API-Key` | Secret API key associated with the device |

### JSON Payload Schema
```json
{
  "device_id": "DEV-CAMPUS-01",
  "readings": [
    {
      "sensor_type": "energy",
      "value": 1150.5,
      "unit": "kWh"
    },
    {
      "sensor_type": "water",
      "value": 340.0,
      "unit": "L"
    },
    {
      "sensor_type": "temperature",
      "value": 24.5,
      "unit": "°C"
    },
    {
      "sensor_type": "humidity",
      "value": 55.0,
      "unit": "%"
    },
    {
      "sensor_type": "co2",
      "value": 620.0,
      "unit": "ppm"
    },
    {
      "sensor_type": "waste",
      "value": 25.0,
      "unit": "kg"
    }
  ]
}
```

---

## 3. ESP32 Arduino / C++ Reference Code (Wokwi Compatible)

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Wi-Fi Credentials
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// GreenNexa IoT API Configuration
const char* serverUrl = "http://YOUR_SERVER_HOST:8000/api/v1/iot/sensor-data";
const char* deviceId = "YOUR_DEVICE_ID";
const char* apiKey = "YOUR_DEVICE_API_KEY";

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to Wi-Fi");
}

void sendSensorReadings() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    
    // Add Authentication Headers
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-ID", deviceId);
    http.addHeader("X-API-Key", apiKey);
    
    // Construct JSON Payload
    StaticJsonDocument<512> doc;
    doc["device_id"] = deviceId;
    
    JsonArray readings = doc.createNestedArray("readings");
    
    JsonObject r1 = readings.createNestedObject();
    r1["sensor_type"] = "energy";
    r1["value"] = random(800, 1500);
    r1["unit"] = "kWh";

    JsonObject r2 = readings.createNestedObject();
    r2["sensor_type"] = "temperature";
    r2["value"] = 24.2 + (random(-20, 20) / 10.0);
    r2["unit"] = "°C";

    String requestBody;
    serializeJson(doc, requestBody);
    
    int httpResponseCode = http.POST(requestBody);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("HTTP Response Code: " + String(httpResponseCode));
      Serial.println("Response: " + response);
    } else {
      Serial.println("Error on sending POST: " + String(httpResponseCode));
    }
    
    http.end();
  }
}

void loop() {
  sendSensorReadings();
  delay(180000); // 3 minute interval
}
```

---

## 4. MicroPython Reference Code

```python
import network
import urequests
import ujson
import time
import random

# Wi-Fi Setup
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('Wokwi-GUEST', '')

while not wlan.isconnected():
    time.sleep(0.5)

SERVER_URL = "http://YOUR_SERVER_HOST:8000/api/v1/iot/sensor-data"
DEVICE_ID = "YOUR_DEVICE_ID"
API_KEY = "YOUR_DEVICE_API_KEY"

def send_data():
    headers = {
        "Content-Type": "application/json",
        "X-Device-ID": DEVICE_ID,
        "X-API-Key": API_KEY
    }
    
    payload = {
        "device_id": DEVICE_ID,
        "readings": [
            {"sensor_type": "energy", "value": round(random.uniform(800, 1500), 2), "unit": "kWh"},
            {"sensor_type": "temperature", "value": round(random.uniform(20, 30), 2), "unit": "°C"}
        ]
    }
    
    try:
        response = urequests.post(SERVER_URL, data=ujson.dumps(payload), headers=headers)
        print("Status:", response.status_code)
        print("Response:", response.text)
        response.close()
    except Exception as e:
        print("Error sending IoT payload:", e)

while True:
    send_data()
    time.sleep(180)
```

---

## 5. Security & Isolation

- Devices send data using authenticated headers.
- Each device is registered to an organisation ID and cannot submit data for other organisations.
- Data mode for the organisation must be set to `iot` for sensor readings to ingest via IoT API.
