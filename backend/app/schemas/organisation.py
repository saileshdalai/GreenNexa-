"""
GreenNexa — Pydantic schemas for Organisation Management API.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.dashboard_style import DEFAULT_DASHBOARD_STYLE, DASHBOARD_STYLE_VALUES


# ---------------------------------------------------------------------------
# Request — Create Organisation
# ---------------------------------------------------------------------------
class OrganisationCreateRequest(BaseModel):
    id: Optional[str] = Field(
        None,
        description="Organisation ID e.g. ORG-00027. Auto-generated if omitted.",
        max_length=50,
    )
    name: str = Field(..., description="Organisation name", min_length=1, max_length=200)
    ownership_type: Optional[str] = Field(None, description="Organisation ownership type: GOVERNMENT or PRIVATE", max_length=50)
    org_type: Optional[str] = Field(None, description="Facility / Org type e.g. School, Hospital, College", max_length=100)
    facility_name: Optional[str] = Field(None, description="Facility / Campus Name", max_length=200)
    state: Optional[str] = Field(None, description="State", max_length=100)
    district: Optional[str] = Field(None, description="District", max_length=100)
    city: Optional[str] = Field(None, description="City", max_length=100)
    address: Optional[str] = Field(None, description="Full address", max_length=300)
    org_code: Optional[str] = Field(None, description="Optional Organisation Code", max_length=50)
    location: Optional[str] = Field(None, description="Location summary", max_length=300)
    contact_email: Optional[str] = Field(None, description="Contact email address", max_length=255)
    contact_phone: Optional[str] = Field(None, description="Contact phone number", max_length=50)
    is_active: bool = Field(True, description="Active status")


# ---------------------------------------------------------------------------
# Request — Update Organisation
# ---------------------------------------------------------------------------
class OrganisationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    ownership_type: Optional[str] = Field(None, description="Organisation ownership type: GOVERNMENT or PRIVATE", max_length=50)
    org_type: Optional[str] = Field(None, max_length=100)
    facility_name: Optional[str] = Field(None, max_length=200)
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=300)
    org_code: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=300)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Response — Single Organisation
# ---------------------------------------------------------------------------
class OrganisationResponse(BaseModel):
    id: str
    name: str
    ownership_type: Optional[str] = None
    org_type: Optional[str] = None
    facility_name: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    org_code: Optional[str] = None
    location: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    enabled_modules: List[str] = Field(default_factory=list)
    iot_devices_count: int = 0
    admin_name: Optional[str] = None
    admin_email: Optional[str] = None
    dashboard_style: str = Field(
        DEFAULT_DASHBOARD_STYLE,
        description="Persisted dashboard presentation style for this organisation.",
    )
    available_dashboard_styles: List[str] = Field(default_factory=lambda: list(DASHBOARD_STYLE_VALUES))

    model_config = {"from_attributes": True}

    @field_validator("dashboard_style", mode="before")
    @classmethod
    def _normalise_dashboard_style(cls, value: object) -> str:
        """
        Read-path guard: rows created before the Dashboard Style system existed
        (or any unknown value) always resolve to a valid style.
        """
        if isinstance(value, str) and value.strip().upper() in DASHBOARD_STYLE_VALUES:
            return value.strip().upper()
        return DEFAULT_DASHBOARD_STYLE


# ---------------------------------------------------------------------------
# Response — Paginated List of Organisations
# ---------------------------------------------------------------------------
class OrganisationListResponse(BaseModel):
    total: int
    items: list[OrganisationResponse]
