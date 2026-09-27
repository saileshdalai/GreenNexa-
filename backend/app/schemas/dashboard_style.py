"""
GreenNexa — Pydantic schemas for the Dashboard Style System.

The dashboard style is a *presentation-only* preference stored per organisation.
It never influences sensor data, anomalies, forecasts, recommendations, RBAC,
Demo Mode, the simulator, IoT mode or enabled modules.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.db.models import Organisation

DASHBOARD_STYLE_VALUES: List[str] = list(Organisation.VALID_DASHBOARD_STYLES)
DEFAULT_DASHBOARD_STYLE: str = Organisation.DEFAULT_DASHBOARD_STYLE


def normalise_dashboard_style(raw: Optional[str]) -> str:
    """
    Normalise a user supplied style string to one of the four allowed values.

    Accepts light formatting variants (case, spaces, dashes) but NEVER accepts
    unknown values. Raises ValueError for anything outside the allowed set.
    """
    if raw is None:
        raise ValueError("dashboard_style is required.")

    cleaned = raw.strip().upper().replace(" ", "_").replace("-", "_")
    if cleaned not in DASHBOARD_STYLE_VALUES:
        raise ValueError(
            f"Invalid dashboard_style '{raw}'. Allowed values: {DASHBOARD_STYLE_VALUES}"
        )
    return cleaned


class DashboardStyleUpdateRequest(BaseModel):
    """Request body for selecting the dashboard style of one organisation."""

    dashboard_style: str = Field(
        ...,
        description="One of EXECUTIVE, OPERATIONS, ANALYTICS, COMMAND_CENTER.",
    )

    @field_validator("dashboard_style")
    @classmethod
    def _validate_style(cls, value: str) -> str:
        return normalise_dashboard_style(value)


class DashboardStyleResponse(BaseModel):
    """Response describing the active dashboard style for one organisation."""

    organisation_id: str
    dashboard_style: str = DEFAULT_DASHBOARD_STYLE
    available_styles: List[str] = Field(default_factory=lambda: list(DASHBOARD_STYLE_VALUES))
    is_default: bool = False

    model_config = {"from_attributes": True}
