"""
GreenNexa — Pydantic schemas for Dashboard APIs, KPIs, and Time-Series Data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# KPI Metric Summary Schema
# ---------------------------------------------------------------------------
class KPIMetricSummary(BaseModel):
    sensor_type: str
    unit: Optional[str] = None
    latest_value: Optional[float] = None
    average: Optional[float] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    reading_count: int = 0
    latest_timestamp: Optional[datetime] = None
    is_anomaly: bool = False
    anomaly_severity: Optional[str] = None


# ---------------------------------------------------------------------------
# Latest Sensor Reading Schema
# ---------------------------------------------------------------------------
class LatestSensorReading(BaseModel):
    sensor_type: str
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    source: Optional[str] = None
    is_anomaly: bool = False
    anomaly_severity: Optional[str] = None
    status: str = Field("NO_DATA", description="ONLINE | OFFLINE | NO_DATA")


class LatestSensorValuesResponse(BaseModel):
    organisation_id: str
    data_source: str
    readings: List[LatestSensorReading]


# ---------------------------------------------------------------------------
# Historical Time-Series Schemas
# ---------------------------------------------------------------------------
class TimeSeriesItem(BaseModel):
    timestamp: datetime
    value: float
    is_anomaly: bool = False
    anomaly_severity: Optional[str] = None
    source: str = "synthetic"


class TimeSeriesResponse(BaseModel):
    organisation_id: str
    sensor_type: str
    unit: Optional[str] = None
    period: str
    total_points: int
    data: List[TimeSeriesItem]


# ---------------------------------------------------------------------------
# Sensor-wise Statistics Schemas
# ---------------------------------------------------------------------------
class SensorStatisticsItem(BaseModel):
    sensor_type: str
    count: int
    average: Optional[float] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    unit: Optional[str] = None


class SensorStatisticsResponse(BaseModel):
    organisation_id: str
    period: str
    statistics: Dict[str, SensorStatisticsItem]


# ---------------------------------------------------------------------------
# Recent Readings Schemas
# ---------------------------------------------------------------------------
class RecentReadingItem(BaseModel):
    id: str
    sensor_type: str
    value: float
    unit: Optional[str] = None
    source: str
    device_id: Optional[str] = None
    timestamp: datetime
    is_anomaly: bool = False
    anomaly_severity: Optional[str] = None

    model_config = {"from_attributes": True}


class RecentReadingsResponse(BaseModel):
    organisation_id: str
    total: int
    readings: List[RecentReadingItem]


# ---------------------------------------------------------------------------
# Data Source & Sensor Status Schemas
# ---------------------------------------------------------------------------
class DataSourceStatusResponse(BaseModel):
    organisation_id: str
    data_source: str
    enabled_sensors: List[str]
    simulator_running: bool
    iot_devices_count: int
    last_updated_at: Optional[datetime] = None


class SensorStatusItem(BaseModel):
    sensor_type: str
    status: str = Field(..., description="ONLINE | OFFLINE | NO_DATA")
    last_value: Optional[float] = None
    unit: Optional[str] = None
    last_updated_at: Optional[datetime] = None
    source: Optional[str] = None


class SensorStatusResponse(BaseModel):
    organisation_id: str
    sensors: List[SensorStatusItem]


class BlockInfo(BaseModel):
    block_id: str
    block_name: str


class OwnOfficeSummary(BaseModel):
    office_name: str
    location: Optional[str] = None
    blocks: List[BlockInfo] = Field(default_factory=list)
    kpis: Dict[str, KPIMetricSummary] = Field(default_factory=dict)
    total_energy_kwh: Optional[float] = None
    total_water_liters: Optional[float] = None
    total_waste_kg: Optional[float] = None
    avg_aqi: Optional[float] = None
    occupancy_pct: Optional[float] = None
    safety_score: Optional[float] = None
    active_anomalies_count: int = 0
    recommendations_count: int = 0
    status: str = "ONLINE"
    data_source: str = "synthetic"
    config: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Main Dashboard Summary Schema
# ---------------------------------------------------------------------------
class DashboardSummaryResponse(BaseModel):
    organisation_id: str
    organisation_name: str
    org_type: Optional[str] = None
    facility_name: Optional[str] = None
    data_source: str
    period: str = "24h"
    last_updated_at: Optional[datetime] = None
    kpis: Dict[str, KPIMetricSummary]
    current_values: List[LatestSensorReading]
    recent_readings: List[RecentReadingItem]
    sensor_status: List[SensorStatusItem]
    optimal_score: Optional[int] = 100
    active_anomaly_count: Optional[int] = 0
    blocks: Optional[List[BlockInfo]] = None
    wards: Optional[List[Any]] = None
    total_wards: Optional[int] = None
    own_office: Optional[OwnOfficeSummary] = None
    # Persisted presentation preference of the organisation being viewed.
    # Only populated for the caller's own organisation (or for SUPER_ADMIN),
    # so a style preference never leaks across organisations.
    dashboard_style: Optional[str] = None
