"""
GreenNexa — Pydantic schemas for Module Intelligence & Block Drill-Down Views.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrendPointItem(BaseModel):
    timestamp: str
    value: float
    is_anomaly: Optional[bool] = False
    anomaly_severity: Optional[str] = None
    baseline: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None


class BlockComparisonItem(BaseModel):
    block_id: str
    block_name: str
    current_value: float
    unit: str
    status: str  # Normal | Warning | Critical


class PredictionRowItem(BaseModel):
    location: str       # Overall | Academic Block | Science Block ...
    block_id: Optional[str] = None
    current_value: float
    predicted_value: float
    change_pct_str: str  # e.g. +7.1%
    status: str          # Normal | Warning | Critical


class ModuleOverallResponse(BaseModel):
    organisation_id: str
    organisation_name: str
    module_id: str
    module_title: str
    unit: str
    current_value: float
    average: float
    peak: float
    change_pct_str: str
    status: str
    open_anomalies_count: int
    has_sufficient_history: bool
    trend_points: List[TrendPointItem]
    block_comparison: List[BlockComparisonItem]
    prediction_table: List[PredictionRowItem]
    baseline: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None


class ModuleBlockDetailResponse(BaseModel):
    organisation_id: str
    organisation_name: str
    module_id: str
    module_title: str
    block_id: str
    block_name: str
    unit: str
    current_value: float
    average: float
    peak: float
    change_pct_str: str
    status: str
    has_sufficient_history: bool
    trend_points: List[TrendPointItem]
    prediction: Optional[PredictionRowItem] = None
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    active_anomalies_count: int = 0
    active_recommendations_count: int = 0
    baseline: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
