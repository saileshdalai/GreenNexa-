"""
GreenNexa — Pydantic schemas for Anomaly Detection API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schema — detect an anomaly for a new reading
# ---------------------------------------------------------------------------
class AnomalyDetectRequest(BaseModel):
    organisation_id: str = Field(..., description="Organisation ID (e.g. ORG-COL-001)")
    facility_id: Optional[str] = Field(None, description="Facility/building ID (optional)")
    metric: str = Field(..., description="Metric category: energy | water | temperature | humidity | co2 | air_quality | waste")
    sensor_type: str = Field(..., description="Sensor type identifier")
    value: float = Field(..., description="Current sensor reading value")
    unit: str = Field("", description="Unit of measurement (kWh, L, °C, %, ppm …)")
    timestamp: Optional[datetime] = Field(None, description="Reading timestamp (UTC). Defaults to now.")

    model_config = {"json_schema_extra": {
        "example": {
            "organisation_id": "ORG-COL-001",
            "facility_id": "BUILDING-A",
            "metric": "energy",
            "sensor_type": "energy",
            "value": 1950.0,
            "unit": "kWh",
        }
    }}


# ---------------------------------------------------------------------------
# Response schema — single anomaly record
# ---------------------------------------------------------------------------
class AnomalyResponse(BaseModel):
    id: str
    organisation_id: str
    facility_id: Optional[str] = None
    block_id: Optional[str] = None
    metric: str
    sensor_type: Optional[str] = None
    value: float
    expected_min: Optional[float] = None
    expected_max: Optional[float] = None
    anomaly_score: Optional[float] = None
    severity: str
    reason: Optional[str] = None
    status: str
    timestamp: datetime
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    is_seen: bool = False
    seen_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Request schema — update anomaly status
# ---------------------------------------------------------------------------
class AnomalyStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: OPEN | ACKNOWLEDGED | RESOLVED | DISMISSED")

    model_config = {"json_schema_extra": {
        "example": {"status": "RESOLVED"}
    }}


# ---------------------------------------------------------------------------
# Response schema — list of anomalies
# ---------------------------------------------------------------------------
class AnomalyListResponse(BaseModel):
    total: int
    items: list[AnomalyResponse]


# ---------------------------------------------------------------------------
# Request schema — classify a reading without persisting (preview)
# ---------------------------------------------------------------------------
class AnomalyClassifyRequest(BaseModel):
    metric: str
    value: float
    history_values: list[float] = Field(
        ..., description="List of recent historical values for the same metric"
    )
    unit: str = ""

    model_config = {"json_schema_extra": {
        "example": {
            "metric": "energy",
            "value": 1950.0,
            "history_values": [1100, 1050, 1200, 1150, 1080, 1130, 1200],
            "unit": "kWh",
        }
    }}


# ---------------------------------------------------------------------------
# Response schema — classification only (no DB write)
# ---------------------------------------------------------------------------
class AnomalyClassifyResponse(BaseModel):
    severity: str
    anomaly_score: Optional[float]
    reason: str
    expected_min: Optional[float]
    expected_max: Optional[float]
    historical_mean: Optional[float]
    historical_std: Optional[float]
    z_score: Optional[float]
