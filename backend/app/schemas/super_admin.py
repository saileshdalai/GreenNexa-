"""
GreenNexa — Pydantic schemas for Super Admin Platform Management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class OrganisationOverviewItem(BaseModel):
    id: str
    name: str
    ownership_type: Optional[str] = None
    facility_type: str
    location: str
    admin_name: str
    admin_email: str
    enabled_modules: List[str]
    iot_devices_count: int
    status: str  # Active / Inactive
    created_at: datetime


class SuperAdminOverviewResponse(BaseModel):
    total_organisations: int
    active_organisations: int
    total_admins: int
    active_iot_devices: int
    platform_alerts: int
    critical_alerts: int
    organisations: List[OrganisationOverviewItem]


class SensorModuleConfig(BaseModel):
    baseline: float = Field(..., gt=0, description="Baseline / average normal value")
    warning_threshold: float = Field(..., ge=0, le=100, description="Warning tolerance percentage (±%)")
    critical_threshold: float = Field(..., ge=0, le=100, description="Critical tolerance percentage (±%)")
    unit: Optional[str] = Field("", description="Sensor measurement unit")


from app.schemas.facility_block import BlockCreateItem, BlockResponse
from app.schemas.ward import WardCreateItem, WardResponse


class FullOrganisationCreateRequest(BaseModel):
    # Step 1 — Details
    name: str = Field(..., min_length=1, max_length=200)
    ownership_type: Optional[str] = Field("PRIVATE", description="Organisation ownership: GOVERNMENT or PRIVATE")
    facility_type: str = Field(..., min_length=1, max_length=100)
    facility_name: Optional[str] = Field(None, max_length=200)
    state: str = Field(..., max_length=100)
    district: str = Field(..., max_length=100)
    city: str = Field(..., max_length=100)
    address: str = Field(..., max_length=300)
    org_code: Optional[str] = Field(None, max_length=50)

    # Step 2 — Admin Account
    admin_name: str = Field(..., min_length=1, max_length=200)
    admin_user_id: Optional[str] = Field(None, max_length=50)
    admin_email: Optional[str] = Field(None, max_length=255)
    admin_phone: Optional[str] = Field("9876543210", description="10-digit Indian mobile number")
    admin_password: str = Field(..., min_length=6, max_length=100)

    @field_validator("admin_phone")
    @classmethod
    def validate_admin_phone(cls, v: Optional[str]) -> str:
        from app.services.otp_service import validate_and_normalize_indian_phone
        if not v or not v.strip():
            return "9876543210"
        norm = validate_and_normalize_indian_phone(v)
        if not norm:
            return "9876543210"
        return norm

    # Step 3 — Facility Block Structure (for regular orgs or Municipality Own Office)
    blocks: Optional[List[BlockCreateItem]] = Field(default_factory=list)

    # Municipality specific setup choice: NORMAL_MUNICIPALITY or OWN_OFFICE
    municipality_setup_type: Optional[str] = Field(None, description="Setup choice: NORMAL_MUNICIPALITY or OWN_OFFICE")
    wards: Optional[List[WardCreateItem]] = Field(default_factory=list)
    associated_gov_org_ids: Optional[List[str]] = Field(default_factory=list)

    # Step 4 — Enabled Modules & Per-Sensor Baseline / Thresholds
    enabled_modules: List[str] = Field(default_factory=list)
    sensor_configs: Optional[dict[str, SensorModuleConfig]] = None


class FullOrganisationCreateResponse(BaseModel):
    organisation_id: str
    organisation_name: str
    ownership_type: Optional[str] = None
    facility_type: str
    admin_user_id: str
    admin_email: str
    enabled_modules: List[str]
    sensor_configs: Optional[dict[str, Any]] = None
    blocks: List[BlockResponse] = Field(default_factory=list)
    wards: List[WardResponse] = Field(default_factory=list)
    municipality_setup_type: Optional[str] = None
    created_at: datetime


class FullOrganisationConfigResponse(BaseModel):
    organisation_id: str
    organisation_name: str
    ownership_type: Optional[str] = None
    facility_type: str
    facility_name: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    org_code: Optional[str] = None
    location: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool = True
    admin_name: str
    admin_user_id: str
    admin_email: str
    admin_phone: Optional[str] = None
    enabled_modules: List[str] = Field(default_factory=list)
    sensor_configs: Dict[str, Any] = Field(default_factory=dict)
    blocks: List[BlockResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None


class FullOrganisationUpdateRequest(BaseModel):
    # Step 1 — Details
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    ownership_type: Optional[str] = Field(None, description="Organisation ownership: GOVERNMENT or PRIVATE")
    facility_type: Optional[str] = Field(None, min_length=1, max_length=100)
    facility_name: Optional[str] = Field(None, max_length=200)
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=300)
    org_code: Optional[str] = Field(None, max_length=50)

    # Step 2 — Admin info
    admin_name: Optional[str] = Field(None, min_length=1, max_length=200)
    admin_phone: Optional[str] = Field(None, max_length=50)

    # Step 3 — Facility Block Structure
    blocks: Optional[List[BlockCreateItem]] = None

    # Step 4 & 5 — Enabled Modules & Per-Sensor Baseline / Thresholds
    enabled_modules: Optional[List[str]] = None
    sensor_configs: Optional[dict[str, SensorModuleConfig]] = None


class SuperAdminUserItem(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    role: str
    organisation_id: Optional[str] = None
    organisation_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class SuperAdminUserCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    user_id: Optional[str] = Field(None, max_length=50)
    email: str = Field(..., min_length=3, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    organisation_id: str = Field(..., min_length=1, max_length=50)
    role: str = Field("ADMIN", max_length=50)

    from pydantic import field_validator

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean not in {"SUPER_ADMIN", "ADMIN"}:
            raise ValueError(f"Invalid role '{v}'. Only SUPER_ADMIN and ADMIN are allowed.")
        return clean


class SuperAdminUserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    role: Optional[str] = Field(None, max_length=50)

    from pydantic import field_validator

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean = v.strip().upper()
        if clean not in {"SUPER_ADMIN", "ADMIN"}:
            raise ValueError(f"Invalid role '{v}'. Only SUPER_ADMIN and ADMIN are allowed.")
        return clean


class PasswordResetRequest(BaseModel):
    confirmation_password: str = Field(..., description="Mandatory confirmation password for destructive action")
    new_password: str = Field(..., min_length=6, max_length=100)
    confirm_new_password: Optional[str] = Field(None, min_length=6, max_length=100)


class VerifyConfirmationPasswordRequest(BaseModel):
    confirmation_password: str = Field(..., description="Confirmation password to verify")


class UpdateSensorConfigRequest(BaseModel):
    enabled_modules: List[str]
    sensor_configs: Optional[dict[str, SensorModuleConfig]] = None


class SensorConfigOverviewItem(BaseModel):
    organisation_id: str
    organisation_name: str
    facility_type: str
    data_source: str
    enabled_modules: List[str]
    sensor_configs: Optional[dict[str, dict[str, Any]]] = None
    is_active: bool
    updated_at: Optional[datetime] = None


class PlatformIoTDeviceItem(BaseModel):
    id: str
    device_id: str
    device_name: str
    organisation_id: str
    organisation_name: str
    device_type: str
    sensor_type: str
    status: str  # ONLINE / OFFLINE
    last_seen_at: Optional[datetime] = None
    source: str = "iot"


class PlatformAlertItem(BaseModel):
    id: str
    title: str
    severity: str  # LOW | MEDIUM | HIGH | CRITICAL
    category: str  # SYSTEM | DEVICE | CONFIG | ORG
    organisation_id: Optional[str] = None
    organisation_name: Optional[str] = None
    description: str
    created_at: datetime


class FacilityTypeItem(BaseModel):
    id: str
    name: str
    description: str


class GovernmentOrgItem(BaseModel):
    """Minimal summary of a GOVERNMENT-owned organisation, for municipality association browsing."""
    id: str
    name: str
    org_type: Optional[str] = None
    location: Optional[str] = None
    is_active: bool


class MunicipalityAssociationRequest(BaseModel):
    """Request body to set which GOVERNMENT orgs are associated with a Municipality."""
    associated_gov_org_ids: List[str] = Field(
        default_factory=list,
        description="List of GOVERNMENT organisation IDs to associate with the municipality",
    )


class MunicipalityAssociationResponse(BaseModel):
    """Response after updating municipality–government org associations."""
    organisation_id: str
    associated_gov_org_ids: List[str]
    message: str


class OrganisationStorageItem(BaseModel):
    organisation_id: str
    organisation_name: str
    ownership_type: str
    logical_storage_bytes: int
    logical_storage_formatted: str
    percentage_of_total: float
    readings_count: int
    anomalies_count: int
    recommendations_count: int
    blocks_count: int
    wards_count: int
    devices_count: int
    messages_count: int


class StorageOverviewResponse(BaseModel):
    database_size_bytes: int
    database_size_formatted: str
    total_allocated_bytes: Optional[int] = None
    total_allocated_formatted: Optional[str] = None
    available_bytes: Optional[int] = None
    available_formatted: Optional[str] = None
    usage_percentage: Optional[float] = None
    government_total_logical_bytes: int
    government_total_logical_formatted: str
    private_total_logical_bytes: int
    private_total_logical_formatted: str
    total_logical_bytes: int
    total_logical_formatted: str
    organisations: List[OrganisationStorageItem]
    generated_at: str
    database_path: Optional[str] = None
    database_engine: str = "SQLite"
