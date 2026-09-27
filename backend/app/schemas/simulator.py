"""
GreenNexa — Pydantic schemas for Synthetic Data Simulator API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SimulatorStartRequest(BaseModel):
    interval_seconds: Optional[int] = Field(
        180,
        ge=1,
        le=86400,
        description="Data generation cycle interval in seconds (default: 180s / 3 minutes)",
    )
    demo_mode: bool = Field(
        False,
        description="Enable Demo Mode scenario anomalies on a fast cadence "
        "(first event on the next 30s cycle (~30-40s), then staggered every 60-120s "
        "per organisation). Scoped to the request's organisation when provided.",
    )
    module: Optional[str] = Field(
        None,
        description="Optional target module to scope demo mode to (e.g. 'energy', 'water')",
    )


class SimulatorStatusResponse(BaseModel):
    running: bool
    interval_seconds: int
    organisations_processed: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    total_readings_generated: int = 0
    total_anomalies_generated: int = 0
    demo_mode: bool = False
    active_modules: Optional[list[str]] = None
    generation_active: bool = True

    model_config = {
        "json_schema_extra": {
            "example": {
                "running": True,
                "interval_seconds": 180,
                "organisations_processed": 2,
                "last_run_at": "2026-09-14T22:40:00+00:00",
                "next_run_at": "2026-09-14T22:43:00+00:00",
                "total_readings_generated": 12,
                "total_anomalies_generated": 0,
            }
        }
    }


class SetSimulatedDateRequest(BaseModel):
    date: str = Field(..., description="Target simulated date in YYYY-MM-DD format")
    organisation_id: Optional[str] = None


class ChangeSimulatedDayRequest(BaseModel):
    days: Optional[int] = Field(1, description="Number of days to advance")
    date: Optional[str] = Field(None, description="Optional explicit date in YYYY-MM-DD format")
    organisation_id: Optional[str] = None

