"""
GreenNexa — Pydantic schemas for AI Recommendation API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request — generate a recommendation for an existing anomaly
# ---------------------------------------------------------------------------
class RecommendationGenerateRequest(BaseModel):
    anomaly_id: str = Field(..., description="ID of the anomaly record to generate a recommendation for")

    model_config = {"json_schema_extra": {
        "example": {"anomaly_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}
    }}


class RecommendationStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Updated status: OPEN | ACTIVE | ACKNOWLEDGED | RESOLVED | DISMISSED | ACTIONED")

    model_config = {"json_schema_extra": {
        "example": {"status": "ACKNOWLEDGED"}
    }}



# ---------------------------------------------------------------------------
# Request — preview recommendation without saving (for testing)
# ---------------------------------------------------------------------------
class RecommendationPreviewRequest(BaseModel):
    organisation_id: str = Field("ORG-DEFAULT", description="Organisation ID")
    facility_id: Optional[str] = None
    metric: str = Field(..., description="Metric name: energy | water | temperature | …")
    severity: str = Field(..., description="NORMAL | LOW | MEDIUM | HIGH | CRITICAL")
    current_value: float = Field(..., description="The anomalous reading value")
    expected_min: Optional[float] = Field(None, description="Lower bound of expected range")
    expected_max: Optional[float] = Field(None, description="Upper bound of expected range")
    history_values: list[float] = Field(
        default_factory=list,
        description="Recent historical values for trend analysis (empty = insufficient data)",
    )
    unit: str = ""

    model_config = {"json_schema_extra": {
        "example": {
            "organisation_id": "ORG-COL-001",
            "metric": "energy",
            "severity": "HIGH",
            "current_value": 1950.0,
            "expected_min": 900.0,
            "expected_max": 1300.0,
            "history_values": [1100, 1050, 1200, 1150, 1080, 1130, 1200, 1180, 1090, 1220],
            "unit": "kWh",
        }
    }}


# ---------------------------------------------------------------------------
# Response — full recommendation record
# ---------------------------------------------------------------------------
class RecommendationResponse(BaseModel):
    id: str
    organisation_id: str
    facility_id: Optional[str] = None
    block_id: Optional[str] = None
    anomaly_id: str
    metric: str
    current_value: float
    expected_range_min: Optional[float] = None
    expected_range_max: Optional[float] = None
    severity: str
    historical_trend: Optional[str] = None
    possible_causes: list[str]
    recommended_actions: list[str]
    summary: str
    confidence_note: str
    priority: str
    status: str
    data_sufficient: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, obj) -> "RecommendationResponse":
        """Convert ORM model to response schema, splitting pipe-delimited fields."""
        return cls(
            id=obj.id,
            organisation_id=obj.organisation_id,
            facility_id=obj.facility_id,
            block_id=getattr(obj, "block_id", None),
            anomaly_id=obj.anomaly_id,
            metric=obj.metric,
            current_value=obj.current_value,
            expected_range_min=obj.expected_range_min,
            expected_range_max=obj.expected_range_max,
            severity=obj.severity,
            historical_trend=obj.historical_trend,
            possible_causes=obj.possible_causes_list,
            recommended_actions=obj.recommended_actions_list,
            summary=obj.summary,
            confidence_note=obj.confidence_note,
            priority=obj.priority,
            status=obj.status,
            data_sufficient=obj.data_sufficient,
            created_at=obj.created_at,
        )


# ---------------------------------------------------------------------------
# Response — list of recommendations
# ---------------------------------------------------------------------------
class RecommendationListResponse(BaseModel):
    total: int
    items: list[RecommendationResponse]


# ---------------------------------------------------------------------------
# Response — preview (no DB write)
# ---------------------------------------------------------------------------
class RecommendationPreviewResponse(BaseModel):
    generated: bool
    data_sufficient: Optional[bool] = None
    metric: Optional[str] = None
    current_value: Optional[float] = None
    expected_range: Optional[str] = None
    severity: Optional[str] = None
    historical_trend: Optional[str] = None
    possible_causes: list[str] = []
    recommended_actions: list[str] = []
    summary: Optional[str] = None
    confidence_note: Optional[str] = None
    priority: Optional[str] = None
    reason: Optional[str] = None  # only when generated=False
