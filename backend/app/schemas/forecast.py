"""
GreenNexa — Pydantic schemas for AI/ML Forecasting Engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ForecastPoint(BaseModel):
    """
    A single hourly forecast data point with confidence bounds.
    """
    timestamp: datetime
    predicted_value: float = Field(..., description="Short-term predicted value")
    lower_bound: Optional[float] = Field(None, description="95% confidence lower estimate bound")
    upper_bound: Optional[float] = Field(None, description="95% confidence upper estimate bound")


class ForecastResponse(BaseModel):
    """
    Response schema for time-series forecasting API.
    """
    organisation_id: str
    sensor_type: str
    horizon: str
    model: str = Field("exponential_smoothing", description="Algorithm used for forecasting")
    data_source: str = Field("synthetic", description="Active data source (synthetic | iot)")
    unit: Optional[str] = Field(None, description="Measurement unit (e.g. kWh, L)")
    generated_at: datetime
    disclaimer: str = Field(
        "Forecast estimates are short-term AI projections and not guaranteed future values.",
        description="Disclaimer note on forecast uncertainty",
    )
    is_available: bool = Field(True, description="Whether forecast generation was successful")
    status_message: Optional[str] = Field(None, description="Status or reason if incomplete / unavailable")
    mode: Optional[str] = Field("default", description="Selected forecast mode (default, last, 7d, 15d, 30d)")
    selected_window: Optional[str] = Field(None, description="Description of the selected observation window")
    available_days: Optional[int] = Field(None, description="Number of complete days with data available")
    required_days: Optional[int] = Field(None, description="Number of days required for the selected mode")
    current_value: Optional[float] = Field(None, description="Latest observed reading value")
    historical_comparison: Optional[str] = Field(None, description="Comparison against historical average / previous day")
    basis: Optional[str] = Field(None, description="Basis of forecast calculation")
    assumptions: Optional[str] = Field(None, description="Model assumptions and caveats")
    model_family: Optional[str] = Field(None, description="Model tier (machine_learning | statistical | rule_heuristic)")
    metrics: Optional[dict] = Field(None, description="Chronological holdout backtesting metrics (MAE, RMSE, R2, MAPE)")
    feature_importances: Optional[dict] = Field(None, description="Predictive importance scores of ML features")
    forecast: List[ForecastPoint] = Field(default_factory=list)
