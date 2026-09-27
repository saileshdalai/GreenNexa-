"""
GreenNexa — Pydantic schemas for Organisation Sensor Configuration & Data Source Management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

ALLOWED_SENSOR_TYPES = {
    "energy",
    "water",
    "waste",
    "air_quality",
    "temperature",
    "humidity",
    "co2",
    "traffic",
    "parking",
    "water_flow",
    "water_level",
    "sewage_level",
    "rainfall",
    "equipment_asset",
    "occupancy",
    "vibration",
    "pressure",
    "flow",
    "current_voltage",
    "rpm",
    "machine_temperature",
    "runtime_hours",
    "acoustic_sound",
    "gas",
    "dust_pm",
    "fire_smoke",
    "oil_fluid_level",
    # Legacy supported types
    "assets",
    "safety",
    "climate",
}
ALLOWED_DATA_SOURCES = {"synthetic", "iot"}


# ---------------------------------------------------------------------------
# Response — Sensor Configuration Profile
# ---------------------------------------------------------------------------
class SensorConfigResponse(BaseModel):
    organisation_id: str
    data_source: str
    enabled_sensors: list[str]
    enabled_modules: list[str] = Field(default_factory=list)
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "organisation_id": "ORG-COL-001",
                "data_source": "synthetic",
                "enabled_sensors": ["energy", "water", "temperature", "humidity"],
                "enabled_modules": ["energy", "water", "temperature", "humidity"],
                "is_active": True,
            }
        },
    }


# ---------------------------------------------------------------------------
# Request — Full Update Sensor Configuration
# ---------------------------------------------------------------------------
class SensorConfigUpdateRequest(BaseModel):
    data_source: Optional[str] = Field(None, description="'synthetic' | 'iot'")
    enabled_sensors: Optional[list[str]] = Field(None, description="List of enabled sensor types")
    is_active: Optional[bool] = Field(None, description="Active status flag")

    @field_validator("data_source")
    @classmethod
    def validate_data_source(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean = v.strip().lower()
        if clean not in ALLOWED_DATA_SOURCES:
            raise ValueError(
                f"Invalid data_source '{v}'. Allowed values: {sorted(list(ALLOWED_DATA_SOURCES))}"
            )
        return clean

    @field_validator("enabled_sensors")
    @classmethod
    def validate_enabled_sensors(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        if len(v) == 0:
            raise ValueError("At least one valid sensor type must be enabled.")
        clean_list = []
        for sensor in v:
            clean = sensor.strip().lower()
            if clean not in ALLOWED_SENSOR_TYPES:
                raise ValueError(
                    f"Unsupported sensor type '{sensor}'. Allowed types: {sorted(list(ALLOWED_SENSOR_TYPES))}"
                )
            if clean not in clean_list:
                clean_list.append(clean)
        if not clean_list:
            raise ValueError("At least one valid sensor type must be enabled.")
        return clean_list


# ---------------------------------------------------------------------------
# Request — Data Source Mode Toggle Payload
# ---------------------------------------------------------------------------
class DataSourceUpdatePayload(BaseModel):
    data_source: str = Field(..., description="'synthetic' | 'iot'")

    @field_validator("data_source")
    @classmethod
    def validate_data_source(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ALLOWED_DATA_SOURCES:
            raise ValueError(
                f"Invalid data_source '{v}'. Allowed values: {sorted(list(ALLOWED_DATA_SOURCES))}"
            )
        return clean


# ---------------------------------------------------------------------------
# Request — Sensors Toggle Payload
# ---------------------------------------------------------------------------
class SensorsUpdatePayload(BaseModel):
    enabled_sensors: list[str] = Field(..., description="List of enabled sensor types")

    @field_validator("enabled_sensors")
    @classmethod
    def validate_enabled_sensors(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one valid sensor type must be enabled.")
        clean_list = []
        for sensor in v:
            clean = sensor.strip().lower()
            if clean not in ALLOWED_SENSOR_TYPES:
                raise ValueError(
                    f"Unsupported sensor type '{sensor}'. Allowed types: {sorted(list(ALLOWED_SENSOR_TYPES))}"
                )
            if clean not in clean_list:
                clean_list.append(clean)
        if not clean_list:
            raise ValueError("At least one valid sensor type must be enabled.")
        return clean_list
