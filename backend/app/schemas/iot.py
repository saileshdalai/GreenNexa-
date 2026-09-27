"""
GreenNexa — Pydantic schemas for IoT Device Management and Ingestion.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Device Registration Schemas
# ---------------------------------------------------------------------------
class IoTDeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100, description="Unique IoT device identifier (e.g. 'ESP32-COL-001')")
    organisation_id: str = Field(..., min_length=1, max_length=50, description="Organisation ID to associate device with")
    device_name: str = Field(..., min_length=1, max_length=200, description="Human-readable device name")
    device_type: str = Field("ESP32", max_length=100, description="Device hardware type (e.g. 'ESP32')")

    @field_validator("device_id", "organisation_id")
    @classmethod
    def clean_ids(cls, v: str) -> str:
        return v.strip()


class IoTDeviceRegisterResponse(BaseModel):
    device_id: str
    organisation_id: str
    device_name: str
    device_type: str
    api_key: str = Field(..., description="Plaintext API key — shown ONLY ONCE at creation time.")
    is_active: bool
    created_at: datetime
    note: str = "Save this API key securely. It will NOT be displayed again."


class IoTDeviceResponse(BaseModel):
    id: str
    device_id: str
    organisation_id: str
    device_name: str
    device_type: str
    is_active: bool
    last_seen_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IoTDeviceListResponse(BaseModel):
    total: int
    items: List[IoTDeviceResponse]


class IoTDeviceStatusUpdate(BaseModel):
    is_active: bool


# ---------------------------------------------------------------------------
# IoT Sensor Data Ingestion Schemas
# ---------------------------------------------------------------------------
class SingleSensorReadingPayload(BaseModel):
    sensor_type: str = Field(..., min_length=1, description="Sensor type e.g. energy, water, temperature")
    value: float = Field(..., description="Sensor numeric measurement value")
    unit: Optional[str] = Field(None, max_length=20, description="Measurement unit (e.g. kWh, L, °C, %, ppm, kg)")

    @field_validator("value")
    @classmethod
    def validate_numeric_value(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Sensor value must be a finite numeric value (NaN or Inf not permitted).")
        return v

    @field_validator("sensor_type")
    @classmethod
    def validate_sensor_type_str(cls, v: str) -> str:
        clean = v.strip().lower()
        if not clean:
            raise ValueError("sensor_type cannot be empty.")
        return clean


class IoTSensorDataIngestPayload(BaseModel):
    device_id: str = Field(..., min_length=1, description="Device ID sending the payload")
    readings: List[SingleSensorReadingPayload] = Field(..., min_length=1, max_length=50, description="List of 1 to 50 sensor readings")
    timestamp: Optional[datetime] = Field(None, description="Optional ISO timestamp from device (default: receive time)")

    @field_validator("readings")
    @classmethod
    def validate_readings_non_empty(cls, v: List[SingleSensorReadingPayload]) -> List[SingleSensorReadingPayload]:
        if not v:
            raise ValueError("Readings list cannot be empty.")
        if len(v) > 50:
            raise ValueError("Exceeded maximum payload limit of 50 readings per request.")
        return v
