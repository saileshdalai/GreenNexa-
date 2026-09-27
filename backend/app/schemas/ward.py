"""
GreenNexa — Pydantic schemas for Municipality Ward Management & Ward Detail.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class WardCreateItem(BaseModel):
    ward_name: str = Field(..., min_length=1, max_length=200, description="Ward descriptive name (e.g. nilesh sahi)")
    ward_number: Optional[str] = Field(None, max_length=50, description="Ward number or code (e.g. 11, WRD-001)")
    zone: Optional[str] = Field(None, max_length=100, description="Administrative civic zone")
    population: Optional[int] = Field(None, ge=0, description="Estimated ward population")
    area_sq_km: Optional[float] = Field(None, ge=0, description="Ward geographical area in sq km")


class WardUpdateRequest(BaseModel):
    ward_name: Optional[str] = Field(None, min_length=1, max_length=200)
    ward_number: Optional[str] = Field(None, max_length=50)
    zone: Optional[str] = Field(None, max_length=100)
    population: Optional[int] = Field(None, ge=0)
    area_sq_km: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None


class WardResponse(BaseModel):
    id: str
    municipality_id: str
    ward_number: str
    ward_name: str
    zone: Optional[str] = None
    population: Optional[int] = None
    area_sq_km: Optional[float] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WardListResponse(BaseModel):
    total: int
    items: List[WardResponse]


class WardMetricItem(BaseModel):
    sensor_type: str
    label: str
    latest_value: Optional[float] = None
    unit: Optional[str] = None
    status: str = "NO_DATA"  # ONLINE | OFFLINE | NO_DATA
    timestamp: Optional[datetime] = None
    has_data: bool = False
    is_anomaly: bool = False
    anomaly_severity: Optional[str] = None


class WardAnomalyItem(BaseModel):
    id: str
    metric: str
    severity: str
    reason: Optional[str] = None
    timestamp: Optional[datetime] = None
    trigger_value: Optional[float] = None
    expected_min: Optional[float] = None
    expected_max: Optional[float] = None
    anomaly_score: Optional[float] = None
    unit: Optional[str] = None


class WardRecommendationItem(BaseModel):
    id: str
    anomaly_id: str
    metric: str
    severity: str
    priority: str
    status: str
    facility_id: Optional[str] = None
    summary: Optional[str] = None
    possible_causes: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    current_value: Optional[float] = None
    expected_range_min: Optional[float] = None
    expected_range_max: Optional[float] = None
    created_at: Optional[datetime] = None


class WardForecastPoint(BaseModel):
    timestamp: datetime
    predicted_value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class WardForecastItem(BaseModel):
    sensor_type: str
    label: str
    current_value: Optional[float] = None
    unit: Optional[str] = None
    horizon: str = "24h"
    is_available: bool = False
    points: List[WardForecastPoint] = Field(default_factory=list)
    message: Optional[str] = None


class WardDetailResponse(BaseModel):
    ward: WardResponse
    has_data: bool = False
    metrics: Dict[str, WardMetricItem] = Field(default_factory=dict)
    anomalies: List[WardAnomalyItem] = Field(default_factory=list)
    recommendations: List[WardRecommendationItem] = Field(default_factory=list)
    forecasts: List[WardForecastItem] = Field(default_factory=list)
    message: Optional[str] = None
