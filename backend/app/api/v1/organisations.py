"""
GreenNexa — Organisation Management API Router.

Routes:
  POST   /api/v1/organisations                 — Create new organisation (SUPER_ADMIN only)
  GET    /api/v1/organisations                 — List organisations (SUPER_ADMIN gets all, ADMIN gets own)
  GET    /api/v1/organisations/{organisation_id} — Get organisation profile
  PUT    /api/v1/organisations/{organisation_id} — Update organisation details (SUPER_ADMIN only)
  DELETE /api/v1/organisations/{organisation_id} — Deactivate organisation (SUPER_ADMIN only)
"""

from __future__ import annotations

import logging
import json as _json
import uuid
from typing import List, Optional

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_current_user,
    require_roles,
    verify_organisation_access,
)
from app.db.database import get_db, safe_vacuum_sqlite, engine as db_engine
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    EventReadState,
    FacilityBlock,
    Message,
    MunicipalityWard,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
    _utcnow,
)
from app.schemas.ward import (
    WardCreateItem,
    WardDetailResponse,
    WardForecastItem,
    WardForecastPoint,
    WardListResponse,
    WardMetricItem,
    WardRecommendationItem,
    WardResponse,
    WardUpdateRequest,
)
from app.services.forecasting import forecasting_service
from app.services.synthetic_simulator import simulator_instance
from app.schemas.facility_block import (
    BlockCreateItem,
    BlockListResponse,
    BlockResponse,
    BlockUpdateRequest,
)
from app.schemas.organisation import (
    OrganisationCreateRequest,
    OrganisationListResponse,
    OrganisationResponse,
    OrganisationUpdateRequest,
)
from app.schemas.sensor_config import (
    DataSourceUpdatePayload,
    SensorConfigResponse,
    SensorConfigUpdateRequest,
    SensorsUpdatePayload,
)
from app.schemas.dashboard_style import (
    DASHBOARD_STYLE_VALUES,
    DashboardStyleResponse,
    DashboardStyleUpdateRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organisations", tags=["Organisation Management"])


# ---------------------------------------------------------------------------
# POST /organisations (Create Organisation — SUPER_ADMIN only)
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=OrganisationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organisation",
    description="Creates a new customer organisation. Requires SUPER_ADMIN role.",
)
def create_organisation(
    body: OrganisationCreateRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Create a new organisation record."""
    org_id = body.id.strip() if body.id else f"ORG-{uuid.uuid4().hex[:8].upper()}"

    # Duplicate check
    existing = db.query(Organisation).filter(Organisation.id == org_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organisation with ID '{org_id}' already exists.",
        )

    ownership_type = None
    if body.ownership_type:
        clean_ownership = body.ownership_type.strip().upper()
        if clean_ownership not in (Organisation.OWNERSHIP_GOVERNMENT, Organisation.OWNERSHIP_PRIVATE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organisation ownership type. Allowed values are GOVERNMENT or PRIVATE.",
            )
        ownership_type = clean_ownership

    new_org = Organisation(
        id=org_id,
        name=body.name.strip(),
        ownership_type=ownership_type,
        org_type=body.org_type.strip() if body.org_type else None,
        location=body.location.strip() if body.location else None,
        contact_email=body.contact_email.strip() if body.contact_email else None,
        contact_phone=body.contact_phone.strip() if body.contact_phone else None,
        is_active=body.is_active,
    )

    db.add(new_org)
    db.commit()
    db.refresh(new_org)

    logger.info("Organisation created: id=%s name=%s by superadmin=%s", new_org.id, new_org.name, current_user.email)
    return OrganisationResponse.model_validate(new_org)


# ---------------------------------------------------------------------------
# GET /organisations (List Organisations)
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=OrganisationListResponse,
    summary="List organisations",
    description=(
        "Returns organisations. SUPER_ADMIN gets all organisations. "
        "ADMIN and VIEWER receive only their own organisation profile."
    ),
)
def list_organisations(
    organisation_id: Optional[str] = Query(None, description="Organisation ID filter"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List organisations based on user role and access permissions."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    query = db.query(Organisation)

    if current_user.role == User.ROLE_SUPER_ADMIN:
        if organisation_id and organisation_id.strip():
            query = query.filter(Organisation.id == organisation_id.strip())
    else:
        query = query.filter(Organisation.id == target_org_id)

    total = query.count()
    items = (
        query.order_by(Organisation.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return OrganisationListResponse(
        total=total,
        items=[OrganisationResponse.model_validate(o) for o in items],
    )


# ---------------------------------------------------------------------------
# GET /organisations/government (List all Government Organisations)
# ---------------------------------------------------------------------------
@router.get(
    "/government",
    summary="List all government organisations (accessible to Super Admin and Municipality Admin)",
)
def list_government_organisations_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all GOVERNMENT-owned organisations for municipality association."""
    gov_orgs = (
        db.query(Organisation)
        .filter(Organisation.ownership_type == Organisation.OWNERSHIP_GOVERNMENT)
        .order_by(Organisation.name.asc())
        .all()
    )
    loc_parts_fn = lambda o: ", ".join(p for p in [o.city, o.state] if p) or (o.location or "")
    return [
        {
            "id": o.id,
            "name": o.name,
            "org_type": o.org_type,
            "ownership_type": o.ownership_type,
            "location": loc_parts_fn(o),
            "is_active": o.is_active,
        }
        for o in gov_orgs
    ]


# ---------------------------------------------------------------------------
# GET /organisations/{organisation_id} (Get Single Organisation Profile)
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}",
    response_model=OrganisationResponse,
    summary="Get organisation profile",
    description="Retrieve details for a single organisation by ID.",
)
def get_organisation(
    organisation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve organisation details for authorized users."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    org = db.query(Organisation).filter(Organisation.id == target_org_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation with ID '{target_org_id}' not found.",
        )

    return OrganisationResponse.model_validate(org)


# ---------------------------------------------------------------------------
# PUT /organisations/{organisation_id} (Update Organisation — SUPER_ADMIN only)
# ---------------------------------------------------------------------------
@router.put(
    "/{organisation_id}",
    response_model=OrganisationResponse,
    summary="Update organisation details",
    description="Updates an organisation record. Requires SUPER_ADMIN role.",
)
def update_organisation(
    organisation_id: str,
    body: OrganisationUpdateRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Update an existing organisation profile."""
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation with ID '{organisation_id}' not found.",
        )

    if body.name is not None:
        org.name = body.name.strip()
    if body.ownership_type is not None:
        clean_ownership = body.ownership_type.strip().upper()
        if clean_ownership not in (Organisation.OWNERSHIP_GOVERNMENT, Organisation.OWNERSHIP_PRIVATE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organisation ownership type. Allowed values are GOVERNMENT or PRIVATE.",
            )
        org.ownership_type = clean_ownership
    if body.org_type is not None:
        org.org_type = body.org_type.strip()
    if body.location is not None:
        org.location = body.location.strip()
    if body.contact_email is not None:
        org.contact_email = body.contact_email.strip()
    if body.contact_phone is not None:
        org.contact_phone = body.contact_phone.strip()
    if body.is_active is not None:
        org.is_active = body.is_active
        for u in org.users:
            u.is_active = body.is_active

    org.updated_at = _utcnow()

    db.commit()
    db.refresh(org)

    logger.info("Organisation updated: id=%s by superadmin=%s", org.id, current_user.email)
    return OrganisationResponse.model_validate(org)


# ---------------------------------------------------------------------------
# DELETE /organisations/{organisation_id} (Deactivate Organisation — SUPER_ADMIN only)
# ---------------------------------------------------------------------------
@router.delete(
    "/{organisation_id}",
    response_model=OrganisationResponse,
    summary="Deactivate an organisation",
    description="Deactivates an organisation. Requires SUPER_ADMIN role.",
)
def deactivate_organisation(
    organisation_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Deactivate an organisation profile and suspend admin access."""
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation with ID '{organisation_id}' not found.",
        )

    org.is_active = False
    for u in org.users:
        u.is_active = False
    org.updated_at = _utcnow()

    db.commit()
    db.refresh(org)

    logger.info("Organisation deactivated: id=%s by superadmin=%s", org.id, current_user.email)
    return OrganisationResponse.model_validate(org)


# ---------------------------------------------------------------------------
# POST /organisations/{organisation_id}/reactivate (Reactivate Organisation — SUPER_ADMIN only)
# ---------------------------------------------------------------------------
@router.post(
    "/{organisation_id}/reactivate",
    response_model=OrganisationResponse,
    summary="Reactivate a deactivated organisation",
    description="Reactivates an organisation and its administrators. Requires SUPER_ADMIN role.",
)
def reactivate_organisation(
    organisation_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Reactivate an organisation and restore admin access."""
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation with ID '{organisation_id}' not found.",
        )

    org.is_active = True
    for u in org.users:
        u.is_active = True
    org.updated_at = _utcnow()

    db.commit()
    db.refresh(org)

    logger.info("Organisation reactivated: id=%s by superadmin=%s", org.id, current_user.email)
    return OrganisationResponse.model_validate(org)


# ---------------------------------------------------------------------------
# Sensor Configuration Helpers
# ---------------------------------------------------------------------------
def _get_or_create_sensor_config(db: Session, organisation_id: str) -> OrganisationSensorConfig:
    """Retrieve existing sensor configuration or initialize default synthetic config."""
    config = (
        db.query(OrganisationSensorConfig)
        .filter(OrganisationSensorConfig.organisation_id == organisation_id)
        .first()
    )
    if not config:
        config = OrganisationSensorConfig(
            organisation_id=organisation_id,
            data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
            enabled_sensors="energy|water|temperature|humidity",
            is_active=True,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _build_sensor_config_response(config: OrganisationSensorConfig) -> SensorConfigResponse:
    """Convert OrganisationSensorConfig ORM model to Pydantic response."""
    sensors = config.enabled_sensors_list
    return SensorConfigResponse(
        organisation_id=config.organisation_id,
        data_source=config.data_source,
        enabled_sensors=sensors,
        enabled_modules=sensors,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /organisations/sensor-config & GET /organisations/me/sensor-config
# ---------------------------------------------------------------------------
@router.get(
    "/sensor-config",
    response_model=SensorConfigResponse,
    summary="Get authenticated user's organisation sensor configuration",
)
@router.get(
    "/me/sensor-config",
    response_model=SensorConfigResponse,
    summary="Get authenticated user's organisation sensor configuration",
)
def get_current_user_sensor_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve sensor/module configuration for the currently authenticated user's organisation."""
    target_org_id = current_user.organisation_id
    if not target_org_id:
        if current_user.role == User.ROLE_SUPER_ADMIN:
            all_modules = list(OrganisationSensorConfig.ALLOWED_SENSOR_TYPES)
            return SensorConfigResponse(
                organisation_id="SUPER_ADMIN",
                data_source="synthetic",
                enabled_sensors=all_modules,
                enabled_modules=all_modules,
                is_active=True,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user is not associated with an organisation.",
        )

    config = _get_or_create_sensor_config(db, target_org_id)
    return _build_sensor_config_response(config)


# ---------------------------------------------------------------------------
# GET /organisations/{organisation_id}/sensor-config
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}/sensor-config",
    response_model=SensorConfigResponse,
    summary="Get sensor configuration for an organisation",
    description="Retrieve enabled sensor types and active data source mode (synthetic vs iot).",
)
def get_sensor_config(
    organisation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve sensor configuration for authorized organisation users."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    org = db.query(Organisation).filter(Organisation.id == target_org_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation with ID '{target_org_id}' not found.",
        )

    config = _get_or_create_sensor_config(db, target_org_id)
    return _build_sensor_config_response(config)


# ---------------------------------------------------------------------------
# PUT /organisations/{organisation_id}/sensor-config
# ---------------------------------------------------------------------------
@router.put(
    "/{organisation_id}/sensor-config",
    response_model=SensorConfigResponse,
    summary="Update full sensor configuration",
    description="Update data source mode, enabled sensors, or active status. Requires ADMIN or SUPER_ADMIN role.",
)
def update_sensor_config(
    organisation_id: str,
    body: SensorConfigUpdateRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Update sensor configuration for an organisation."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    org = db.query(Organisation).filter(Organisation.id == target_org_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation with ID '{target_org_id}' not found.",
        )

    config = _get_or_create_sensor_config(db, target_org_id)

    if body.data_source is not None:
        config.data_source = body.data_source
    if body.enabled_sensors is not None:
        config.set_enabled_sensors(body.enabled_sensors)
    if body.is_active is not None:
        config.is_active = body.is_active

    config.updated_at = _utcnow()
    db.commit()
    db.refresh(config)

    logger.info("Sensor config updated for org=%s by user=%s", target_org_id, current_user.email)
    return _build_sensor_config_response(config)


# ---------------------------------------------------------------------------
# PATCH /organisations/{organisation_id}/sensor-config/data-source
# ---------------------------------------------------------------------------
@router.patch(
    "/{organisation_id}/sensor-config/data-source",
    response_model=SensorConfigResponse,
    summary="Change organisation data source mode (synthetic vs iot)",
    description="Toggles data source mode between 'synthetic' and 'iot'. Requires ADMIN or SUPER_ADMIN role.",
)
def update_data_source(
    organisation_id: str,
    body: DataSourceUpdatePayload,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Toggle data source mode for an organisation."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    org = db.query(Organisation).filter(Organisation.id == target_org_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation with ID '{target_org_id}' not found.",
        )

    config = _get_or_create_sensor_config(db, target_org_id)
    config.data_source = body.data_source
    config.updated_at = _utcnow()

    db.commit()
    db.refresh(config)

    logger.info("Data source mode changed to '%s' for org=%s by user=%s", body.data_source, target_org_id, current_user.email)
    return _build_sensor_config_response(config)


# ---------------------------------------------------------------------------
# PATCH /organisations/{organisation_id}/sensor-config/sensors
# ---------------------------------------------------------------------------
@router.patch(
    "/{organisation_id}/sensor-config/sensors",
    response_model=SensorConfigResponse,
    summary="Enable or disable sensor types",
    description="Updates list of enabled sensor types for an organisation. Requires ADMIN or SUPER_ADMIN role.",
)
def update_enabled_sensors(
    organisation_id: str,
    body: SensorsUpdatePayload,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Enable or disable sensor types for an organisation."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    org = db.query(Organisation).filter(Organisation.id == target_org_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation with ID '{target_org_id}' not found.",
        )

    config = _get_or_create_sensor_config(db, target_org_id)
    config.set_enabled_sensors(body.enabled_sensors)
    config.updated_at = _utcnow()

    db.commit()
    db.refresh(config)

    logger.info("Enabled sensors updated for org=%s by user=%s", target_org_id, current_user.email)
    return _build_sensor_config_response(config)


# ---------------------------------------------------------------------------
# Facility Block Management Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/{organisation_id}/blocks",
    response_model=BlockListResponse,
    summary="List facility blocks for an organisation",
)
def list_facility_blocks(
    organisation_id: str,
    active_only: bool = Query(True, description="Filter active blocks only"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List facility blocks for an organisation."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    query = db.query(FacilityBlock).filter(FacilityBlock.organisation_id == target_org_id)
    if active_only:
        query = query.filter(FacilityBlock.is_active == True)

    blocks = query.order_by(FacilityBlock.block_id.asc()).all()
    return BlockListResponse(
        total=len(blocks),
        items=[BlockResponse.model_validate(b) for b in blocks],
    )


@router.post(
    "/{organisation_id}/blocks",
    response_model=BlockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new facility block to organisation",
)
def create_facility_block(
    organisation_id: str,
    body: BlockCreateItem,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Add a new block to an organisation."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    name_clean = body.block_name.strip()
    if not name_clean:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Block name cannot be empty.")

    # Duplicate check within organisation
    existing_name = (
        db.query(FacilityBlock)
        .filter(
            FacilityBlock.organisation_id == target_org_id,
            FacilityBlock.block_name.ilike(name_clean),
            FacilityBlock.is_active == True,
        )
        .first()
    )
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Block with name '{name_clean}' already exists in this organisation.",
        )

    # Assign block_id if omitted
    if body.block_id and body.block_id.strip():
        b_id = body.block_id.strip()
        existing_id = (
            db.query(FacilityBlock)
            .filter(FacilityBlock.organisation_id == target_org_id, FacilityBlock.block_id == b_id)
            .first()
        )
        if existing_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Block with ID '{b_id}' already exists in this organisation.",
            )
    else:
        count = db.query(FacilityBlock).filter(FacilityBlock.organisation_id == target_org_id).count()
        b_id = f"BLK-{count + 1:03d}"
        while db.query(FacilityBlock).filter(FacilityBlock.organisation_id == target_org_id, FacilityBlock.block_id == b_id).first() is not None:
            count += 1
            b_id = f"BLK-{count + 1:03d}"

    block_obj = FacilityBlock(
        organisation_id=target_org_id,
        block_id=b_id,
        block_name=name_clean,
        is_active=True,
    )
    db.add(block_obj)
    db.commit()
    db.refresh(block_obj)

    logger.info("Facility block created: block_id=%s name=%s org=%s", b_id, name_clean, target_org_id)
    return BlockResponse.model_validate(block_obj)


@router.put(
    "/{organisation_id}/blocks/{block_id}",
    response_model=BlockResponse,
    summary="Update facility block name or active status",
)
def update_facility_block(
    organisation_id: str,
    block_id: str,
    body: BlockUpdateRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Update a facility block's name or status."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    block_obj = (
        db.query(FacilityBlock)
        .filter(FacilityBlock.organisation_id == target_org_id, FacilityBlock.block_id == block_id)
        .first()
    )
    if not block_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block '{block_id}' not found in organisation '{target_org_id}'.",
        )

    if body.block_name is not None:
        name_clean = body.block_name.strip()
        if not name_clean:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Block name cannot be empty.")
        # Duplicate check excluding self
        dup = (
            db.query(FacilityBlock)
            .filter(
                FacilityBlock.organisation_id == target_org_id,
                FacilityBlock.block_name.ilike(name_clean),
                FacilityBlock.block_id != block_id,
                FacilityBlock.is_active == True,
            )
            .first()
        )
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another block with name '{name_clean}' already exists.",
            )
        block_obj.block_name = name_clean

    if body.is_active is not None:
        block_obj.is_active = body.is_active

    block_obj.updated_at = _utcnow()
    db.commit()
    db.refresh(block_obj)

    logger.info("Facility block updated: block_id=%s org=%s", block_id, target_org_id)
    return BlockResponse.model_validate(block_obj)


@router.delete(
    "/{organisation_id}/blocks/{block_id}",
    response_model=BlockResponse,
    summary="Soft-deactivate a facility block",
)
def deactivate_facility_block(
    organisation_id: str,
    block_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Deactivate block without deleting historical telemetry."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    block_obj = (
        db.query(FacilityBlock)
        .filter(FacilityBlock.organisation_id == target_org_id, FacilityBlock.block_id == block_id)
        .first()
    )
    if not block_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block '{block_id}' not found in organisation '{target_org_id}'.",
        )

    block_obj.is_active = False
    block_obj.updated_at = _utcnow()
    db.commit()
    db.refresh(block_obj)

    logger.info("Facility block deactivated: block_id=%s org=%s", block_id, target_org_id)
    return BlockResponse.model_validate(block_obj)


# ---------------------------------------------------------------------------
# Municipality Ward Management Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/{organisation_id}/wards",
    response_model=WardListResponse,
    summary="List administrative wards for a municipality",
)
def list_municipality_wards(
    organisation_id: str,
    active_only: bool = Query(True, description="Filter active wards only"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List administrative wards for a municipality. Never returns facility blocks."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    query = db.query(MunicipalityWard).filter(MunicipalityWard.municipality_id == target_org_id)
    if active_only:
        query = query.filter(MunicipalityWard.is_active == True)

    wards = query.order_by(MunicipalityWard.ward_number.asc()).all()
    return WardListResponse(
        total=len(wards),
        items=[WardResponse.model_validate(w) for w in wards],
    )


@router.post(
    "/{organisation_id}/wards",
    response_model=WardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new municipality ward",
)
def create_municipality_ward(
    organisation_id: str,
    body: WardCreateItem,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Add a new municipality ward.
    Only creates ONE MunicipalityWard record. Never creates FacilityBlocks.
    """
    target_org_id = verify_organisation_access(organisation_id, current_user)

    org = db.query(Organisation).filter(Organisation.id == target_org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organisation '{target_org_id}' not found.")

    name_clean = body.ward_name.strip()
    if not name_clean:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ward name cannot be empty.")

    # Duplicate check by name within this municipality
    existing_name = (
        db.query(MunicipalityWard)
        .filter(
            MunicipalityWard.municipality_id == target_org_id,
            MunicipalityWard.ward_name.ilike(name_clean),
            MunicipalityWard.is_active == True,
        )
        .first()
    )
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ward with name '{name_clean}' already exists in this municipality.",
        )

    # Determine ward_number
    if body.ward_number and body.ward_number.strip():
        w_num = body.ward_number.strip()
        existing_num = (
            db.query(MunicipalityWard)
            .filter(
                MunicipalityWard.municipality_id == target_org_id,
                MunicipalityWard.ward_number == w_num,
            )
            .first()
        )
        if existing_num:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ward with number/code '{w_num}' already exists in this municipality.",
            )
    else:
        # Check if number is in name e.g. "Ward 5", "Ward 11"
        import re
        m = re.search(r'\b(?:ward\s*)?(\d+)\b', name_clean, re.IGNORECASE)
        if m:
            w_num = m.group(1)
            collision = db.query(MunicipalityWard).filter(
                MunicipalityWard.municipality_id == target_org_id,
                MunicipalityWard.ward_number == w_num,
            ).first()
            if collision:
                count = db.query(MunicipalityWard).filter(MunicipalityWard.municipality_id == target_org_id).count()
                w_num = f"{count + 1}"
        else:
            count = db.query(MunicipalityWard).filter(MunicipalityWard.municipality_id == target_org_id).count()
            w_num = f"{count + 1}"

    ward_obj = MunicipalityWard(
        municipality_id=target_org_id,
        ward_number=w_num,
        ward_name=name_clean,
        zone=body.zone.strip() if body.zone else None,
        population=body.population,
        area_sq_km=body.area_sq_km,
        is_active=True,
    )
    db.add(ward_obj)
    db.commit()
    db.refresh(ward_obj)

    logger.info("Municipality ward created: ward_num=%s name=%s muni=%s by=%s", w_num, name_clean, target_org_id, current_user.email)
    return WardResponse.model_validate(ward_obj)


def build_ward_forecast_items(
    db: Session,
    org_id: str,
    ward: MunicipalityWard,
    metrics_map: dict,
) -> List[WardForecastItem]:
    """
    Build ward-scoped forecast estimates strictly from the ward's own persisted
    sensor readings (least-squares trend projected forward). A forecast is only
    produced when enough real ward history exists — no values are fabricated.
    """
    items: List[WardForecastItem] = []
    order = [
        "energy", "water", "waste", "traffic", "parking", "air_quality",
        "temperature", "humidity", "water_flow", "water_level", "safety", "sewage",
    ]
    for s_type in order:
        metric = metrics_map.get(s_type)
        if not metric or not metric.has_data:
            continue
        readings = (
            db.query(SensorReading)
            .filter(
                SensorReading.organisation_id == org_id,
                SensorReading.sensor_type == s_type,
                or_(SensorReading.ward_id == ward.ward_number, SensorReading.ward_id == ward.id),
            )
            .order_by(SensorReading.timestamp.asc())
            .all()
        )
        pts = [
            (r.timestamp, float(r.value))
            for r in readings
            if r.timestamp is not None and r.value is not None
        ]
        latest_ts = max((ts for ts, _ in pts), default=None)
        if len(pts) < 3:
            items.append(
                WardForecastItem(
                    sensor_type=s_type,
                    label=metric.label,
                    current_value=metric.latest_value,
                    unit=metric.unit,
                    is_available=False,
                    message="Insufficient ward history for a forecast estimate (need at least 3 readings).",
                )
            )
            continue

        t0 = pts[0][0]
        xs = [(p[0] - t0).total_seconds() / 3600.0 for p in pts]
        ys = [p[1] for p in pts]
        n = len(ys)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        denom = sum((x - mean_x) ** 2 for x in xs)
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom if denom else 0.0
        intercept = mean_y - slope * mean_x
        resid = [abs(y - (slope * x + intercept)) for x, y in zip(xs, ys)]
        band = (sum(r2 ** 2 for r2 in resid) / max(n - 1, 1)) ** 0.5 * 1.96

        base_h = (latest_ts - t0).total_seconds() / 3600.0
        is_pct = (metric.unit == "%") or (s_type in ("waste", "parking", "humidity"))
        points = []
        for ahead_h in (6.0, 12.0, 24.0):
            pred = slope * (base_h + ahead_h) + intercept
            p_val = max(pred, 0.0)
            lb_val = max(pred - band, 0.0)
            ub_val = max(pred + band, 0.0)
            if is_pct:
                p_val = min(100.0, p_val)
                lb_val = min(100.0, lb_val)
                ub_val = min(100.0, max(p_val, ub_val))
            points.append(
                WardForecastPoint(
                    timestamp=latest_ts + timedelta(hours=ahead_h),
                    predicted_value=round(p_val, 2),
                    lower_bound=round(lb_val, 2),
                    upper_bound=round(ub_val, 2),
                )
            )
        items.append(
            WardForecastItem(
                sensor_type=s_type,
                label=metric.label,
                current_value=metric.latest_value,
                unit=metric.unit,
                horizon="24h",
                is_available=True,
                points=points,
                message="Estimate projected from this ward's own recent readings (least-squares trend).",
            )
        )
    return items


@router.get(
    "/{organisation_id}/wards/{ward_id}",
    response_model=WardDetailResponse,
    summary="Get detailed ward civic data (scopely mapped operational data)",
)
def get_ward_detail(
    organisation_id: str,
    ward_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns legitimate operational civic data for an actual Municipality Ward.
    If no telemetry exists, returns clear 'has_data: false' and empty state.
    Does NOT manufacture fake data. Does NOT show facility blocks.
    """
    target_org_id = verify_organisation_access(organisation_id, current_user)

    ward = (
        db.query(MunicipalityWard)
        .filter(
            MunicipalityWard.municipality_id == target_org_id,
            or_(
                MunicipalityWard.id == ward_id,
                MunicipalityWard.ward_number == ward_id,
            ),
        )
        .first()
    )
    if not ward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ward '{ward_id}' not found in municipality '{target_org_id}'.",
        )

    # Standard civic modules to check for this ward
    CIVIC_MODULES_SPECS = [
        ("energy", "Energy / Street Lighting"),
        ("water", "Water Supply"),
        ("waste", "Waste Management"),
        ("sewage", "Sewage & Drainage"),
        ("sewage_level", "Drainage Water Level"),
        ("air_quality", "Air Quality"),
        ("traffic", "Traffic & Parking"),
        ("parking", "Parking"),
        ("street_lighting", "Street Lighting"),
        ("roads", "Roads & Infrastructure"),
        ("parks", "Parks & Public Spaces"),
        ("safety", "Safety & Incidents"),
        ("water_flow", "Water Flow / Pumps"),
        ("water_level", "Water Level"),
        ("rainfall", "Rainfall"),
        ("climate", "Climate & Environment"),
        ("temperature", "Temperature"),
        ("humidity", "Humidity"),
    ]

    metrics_map = {}
    has_any_data = False

    # Legitimate sensor readings mapped to this ward
    for s_type, label in CIVIC_MODULES_SPECS:
        latest = (
            db.query(SensorReading)
            .filter(
                SensorReading.organisation_id == target_org_id,
                SensorReading.sensor_type == s_type,
                or_(
                    SensorReading.ward_id == ward.ward_number,
                    SensorReading.ward_id == ward.id,
                ),
            )
            .order_by(SensorReading.timestamp.desc())
            .first()
        )
        if latest is not None:
            has_any_data = True
            ts = latest.timestamp.replace(tzinfo=timezone.utc) if latest.timestamp.tzinfo is None else latest.timestamp
            # Freshness uses the reading's own simulated calendar day + the live
            # UTC time-of-day (mirrors the simulator's authoritative stamping),
            # so ward data dated on the simulated calendar is never misread as
            # OFFLINE because the wall-clock date differs (BUG-19).
            ref_now = datetime(
                ts.year, ts.month, ts.day,
                _utcnow().hour, _utcnow().minute, _utcnow().second,
                tzinfo=timezone.utc,
            )
            gap = (ref_now - ts).total_seconds()
            s_status = "ONLINE" if gap <= 600.0 else "OFFLINE"
            metrics_map[s_type] = WardMetricItem(
                sensor_type=s_type,
                label=label,
                latest_value=latest.value,
                unit=latest.unit,
                status=s_status,
                timestamp=latest.timestamp,
                has_data=True,
                is_anomaly=latest.is_anomaly,
                anomaly_severity=latest.anomaly_severity,
            )
        else:
            metrics_map[s_type] = WardMetricItem(
                sensor_type=s_type,
                label=label,
                latest_value=None,
                unit=None,
                status="NO_DATA",
                timestamp=None,
                has_data=False,
                is_anomaly=False,
                anomaly_severity=None,
            )

    # Active anomalies mapped to this ward
    ward_anomalies_db = (
        db.query(AnomalyRecord)
        .filter(
            AnomalyRecord.organisation_id == target_org_id,
            or_(
                AnomalyRecord.ward_id == ward.ward_number,
                AnomalyRecord.ward_id == ward.id,
            ),
            AnomalyRecord.status.in_((AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED)),
        )
        .all()
    )
    anom_items = [
        {
            "id": a.id,
            "metric": a.metric,
            "severity": a.severity,
            "reason": a.reason,
            "timestamp": a.timestamp,
            "trigger_value": a.value,
            "expected_min": a.expected_min,
            "expected_max": a.expected_max,
            "anomaly_score": a.anomaly_score,
            "unit": (
                (metrics_map.get(a.metric) or metrics_map.get(a.sensor_type)).unit
                if (metrics_map.get(a.metric) or metrics_map.get(a.sensor_type))
                else ("%" if a.metric == "waste" else "")
            ),
        }
        for a in ward_anomalies_db
    ]

    # AI recommendations linked to this ward (ward_id column, plus any legacy
    # recommendations whose anomaly record still resolves to this ward)
    ward_recs_db = (
        db.query(AIRecommendation)
        .filter(
            AIRecommendation.organisation_id == target_org_id,
            or_(AIRecommendation.ward_id == ward.ward_number, AIRecommendation.ward_id == ward.id),
            AIRecommendation.status.in_((AIRecommendation.STATUS_ACTIVE, AIRecommendation.STATUS_OPEN)),
        )
        .order_by(AIRecommendation.created_at.desc())
        .all()
    )
    ward_anom_ids = [a.id for a in ward_anomalies_db]
    rec_map = {r.id: r for r in ward_recs_db}
    if ward_anom_ids:
        legacy_recs = (
            db.query(AIRecommendation)
            .filter(
                AIRecommendation.organisation_id == target_org_id,
                AIRecommendation.anomaly_id.in_(ward_anom_ids),
                AIRecommendation.status.in_((AIRecommendation.STATUS_ACTIVE, AIRecommendation.STATUS_OPEN)),
            )
            .all()
        )
        for r in legacy_recs:
            rec_map.setdefault(r.id, r)
    rec_sorted = sorted(rec_map.values(), key=lambda r: r.created_at or _utcnow(), reverse=True)

    rec_items = [
        WardRecommendationItem(
            id=r.id,
            anomaly_id=r.anomaly_id,
            metric=r.metric,
            severity=r.severity,
            priority=r.priority,
            status=r.status,
            facility_id=r.facility_id,
            summary=r.summary,
            possible_causes=r.possible_causes_list,
            recommended_actions=r.recommended_actions_list,
            current_value=r.current_value,
            expected_range_min=r.expected_range_min,
            expected_range_max=r.expected_range_max,
            created_at=r.created_at,
        )
        for r in rec_sorted
    ]

    forecast_items = build_ward_forecast_items(db, target_org_id, ward, metrics_map)

    msg = None if has_any_data else f"No current data available for {ward.ward_name} (Ward {ward.ward_number}). Waiting for civic telemetry ingestion."

    return WardDetailResponse(
        ward=WardResponse.model_validate(ward),
        has_data=has_any_data,
        metrics=metrics_map,
        anomalies=anom_items,
        recommendations=rec_items,
        forecasts=forecast_items,
        message=msg,
    )


@router.put(
    "/{organisation_id}/wards/{ward_id}",
    response_model=WardResponse,
    summary="Update municipality ward details",
)
def update_municipality_ward(
    organisation_id: str,
    ward_id: str,
    body: WardUpdateRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Update ward details."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    ward = (
        db.query(MunicipalityWard)
        .filter(
            MunicipalityWard.municipality_id == target_org_id,
            or_(
                MunicipalityWard.id == ward_id,
                MunicipalityWard.ward_number == ward_id,
            ),
        )
        .first()
    )
    if not ward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ward '{ward_id}' not found in municipality '{target_org_id}'.",
        )

    if body.ward_name is not None:
        name_clean = body.ward_name.strip()
        if not name_clean:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ward name cannot be empty.")
        ward.ward_name = name_clean

    if body.ward_number is not None:
        w_clean = body.ward_number.strip()
        if not w_clean:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ward number cannot be empty.")
        dup = db.query(MunicipalityWard).filter(
            MunicipalityWard.municipality_id == target_org_id,
            MunicipalityWard.ward_number == w_clean,
            MunicipalityWard.id != ward.id,
        ).first()
        if dup:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ward number '{w_clean}' already in use.")
        ward.ward_number = w_clean

    if body.zone is not None:
        ward.zone = body.zone.strip() if body.zone else None
    if body.population is not None:
        ward.population = body.population
    if body.area_sq_km is not None:
        ward.area_sq_km = body.area_sq_km
    if body.is_active is not None:
        ward.is_active = body.is_active

    ward.updated_at = _utcnow()
    db.commit()
    db.refresh(ward)
    return WardResponse.model_validate(ward)


@router.delete(
    "/{organisation_id}/wards/{ward_id}",
    response_model=WardResponse,
    summary="Soft-deactivate a municipality ward",
)
def deactivate_municipality_ward(
    organisation_id: str,
    ward_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Soft-deactivate a municipality ward."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    ward = (
        db.query(MunicipalityWard)
        .filter(
            MunicipalityWard.municipality_id == target_org_id,
            or_(
                MunicipalityWard.id == ward_id,
                MunicipalityWard.ward_number == ward_id,
            ),
        )
        .first()
    )
    if not ward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ward '{ward_id}' not found in municipality '{target_org_id}'.",
        )

    ward.is_active = False
    ward.updated_at = _utcnow()
    db.commit()
    db.refresh(ward)
    return WardResponse.model_validate(ward)


# ---------------------------------------------------------------------------
# POST /organisations/{organisation_id}/clear-data (Admin Clear Data)
# ---------------------------------------------------------------------------
@router.post(
    "/{organisation_id}/clear-data",
    summary="Clear organisation operational data",
    description=(
        "Deletes all operational telemetry, anomaly records, AI recommendations, "
        "and organisation messages for the specified organisation. Preserves organisation identity, "
        "Admin user account, facility blocks, sensor configurations, baselines, thresholds, and IoT devices."
    ),
)
def clear_organisation_operational_data(
    organisation_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Perform organisation-level operational reset.
    """
    target_org_id = verify_organisation_access(organisation_id, current_user)

    org = db.query(Organisation).filter(Organisation.id == target_org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{target_org_id}' not found.",
        )

    # 1. Delete recommendations
    deleted_recs = db.query(AIRecommendation).filter(AIRecommendation.organisation_id == target_org_id).delete(synchronize_session=False)

    # 2. Delete anomalies
    deleted_anomalies = db.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == target_org_id).delete(synchronize_session=False)

    # 3. Delete sensor readings
    deleted_readings = db.query(SensorReading).filter(SensorReading.organisation_id == target_org_id).delete(synchronize_session=False)

    # 4. Delete messages associated with this organisation
    deleted_messages = db.query(Message).filter(Message.organisation_id == target_org_id).delete(synchronize_session=False)

    # 5. Delete event read states associated with this organisation
    deleted_read_states = db.query(EventReadState).filter(EventReadState.organisation_id == target_org_id).delete(synchronize_session=False)

    db.commit()

    # 5b. Perform safe SQLite VACUUM compaction to reclaim disk space
    safe_vacuum_sqlite(db_engine)

    # 6. Clear forecasting cache and reset simulator runtime state
    forecasting_service.clear_cache()
    simulator_instance.reset_simulator_state(target_org_id)

    logger.info(
        "Admin clear data executed for org %s by user %s: readings=%d anomalies=%d recs=%d msgs=%d",
        target_org_id,
        current_user.email,
        deleted_readings,
        deleted_anomalies,
        deleted_recs,
        deleted_messages,
    )

    return {
        "message": f"Operational data cleared successfully for organisation '{target_org_id}'.",
        "organisation_id": target_org_id,
        "deleted": {
            "sensor_readings": deleted_readings,
            "anomaly_records": deleted_anomalies,
            "recommendations": deleted_recs,
            "messages": deleted_messages,
        },
    }


# ---------------------------------------------------------------------------
# GET /organisations/{org_id}/associated-government-orgs
# — Municipality Admin: read-only list of associated government organisations
# ---------------------------------------------------------------------------
@router.get(
    "/{org_id}/associated-government-orgs",
    summary="Get associated government organisations for a municipality (Municipality Admin R/O)",
)
def get_associated_government_orgs(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return Government organisations associated with a Municipality organisation.
    Only accessible by the Municipality Admin (ROLE_ADMIN of the municipality org)
    or a SUPER_ADMIN. Returns read-only summaries — no write access granted.
    """
    # SUPER_ADMIN may query any org; ADMIN must be requesting their own municipality
    if current_user.role != User.ROLE_SUPER_ADMIN:
        if current_user.organisation_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only view associated organisations for your own municipality.",
            )

    # Fetch the municipality organisation
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organisation '{org_id}' not found.")

    # Verify it is a municipality (only super_admin bypass)
    is_municipality = org.org_type and "municipality" in org.org_type.lower()
    if not is_municipality and current_user.role != User.ROLE_SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for Municipality organisations.",
        )

    # Read associated gov org IDs from sensor config
    cfg = db.query(OrganisationSensorConfig).filter(OrganisationSensorConfig.organisation_id == org_id).first()
    assoc_ids: List[str] = []
    if cfg and cfg.sensor_configs:
        try:
            stored = _json.loads(cfg.sensor_configs)
            assoc_ids = stored.get("associated_gov_org_ids") or stored.get("_municipality_assoc", [])
            if not isinstance(assoc_ids, list):
                assoc_ids = []
        except Exception:
            assoc_ids = []

    # Fetch full summaries for each associated government org
    result = []
    for gov_id in assoc_ids:
        gov_org = db.query(Organisation).filter(Organisation.id == gov_id).first()
        if gov_org:
            loc = ", ".join(p for p in [gov_org.city, gov_org.state] if p) or (gov_org.location or "")
            result.append({
                "id": gov_org.id,
                "name": gov_org.name,
                "org_type": gov_org.org_type,
                "ownership_type": gov_org.ownership_type,
                "location": loc,
                "is_active": gov_org.is_active,
                "contact_email": gov_org.contact_email,
                "org_code": gov_org.org_code,
            })

    return {"municipality_id": org_id, "associated_government_orgs": result}


# ---------------------------------------------------------------------------
# POST /organisations/{org_id}/associated-government-orgs
# — Add an existing Government organisation to Municipality associations
# ---------------------------------------------------------------------------
@router.post(
    "/{org_id}/associated-government-orgs",
    summary="Associate a government organisation with a municipality",
)
def associate_government_org_with_municipality(
    org_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Associate an existing GOVERNMENT organisation with a municipality.
    Accessible to SUPER_ADMIN or ADMIN of the municipality.
    Does NOT create a new organisation record.
    Prevents duplicate associations.
    """
    if current_user.role != User.ROLE_SUPER_ADMIN:
        if current_user.organisation_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only associate organisations for your own municipality.",
            )

    muni_org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not muni_org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Municipality '{org_id}' not found.")

    target_gov_id = (
        payload.get("target_org_id")
        or payload.get("associated_org_id")
        or payload.get("org_id")
        or payload.get("id")
    )
    if not target_gov_id:
        ids_list = payload.get("associated_gov_org_ids")
        if ids_list and len(ids_list) > 0:
            target_gov_id = ids_list[0]

    if not target_gov_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target organisation ID is required.")

    target_gov_id = str(target_gov_id).strip()
    if target_gov_id == org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A municipality cannot be associated with itself.")

    # Validate target organisation exists and is GOVERNMENT
    target_org = db.query(Organisation).filter(Organisation.id == target_gov_id).first()
    if not target_org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organisation '{target_gov_id}' not found.")

    if target_org.ownership_type != Organisation.OWNERSHIP_GOVERNMENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organisation '{target_gov_id}' is not a GOVERNMENT-owned organisation.",
        )

    # Read existing config
    cfg = db.query(OrganisationSensorConfig).filter(OrganisationSensorConfig.organisation_id == org_id).first()
    if not cfg:
        cfg = OrganisationSensorConfig(
            organisation_id=org_id,
            data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
            enabled_sensors="energy|water",
            is_active=True,
        )
        db.add(cfg)

    stored: dict = {}
    if cfg.sensor_configs:
        try:
            stored = _json.loads(cfg.sensor_configs)
        except Exception:
            stored = {}

    current_assocs: list = stored.get("_municipality_assoc", [])
    if not isinstance(current_assocs, list):
        current_assocs = []

    # Check for duplicate association
    if target_gov_id in current_assocs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organisation '{target_org.name}' ({target_gov_id}) is already associated with this municipality.",
        )

    current_assocs.append(target_gov_id)
    stored["_municipality_assoc"] = current_assocs
    stored["associated_gov_org_ids"] = current_assocs
    cfg.sensor_configs = _json.dumps(stored)
    cfg.updated_at = _utcnow()
    db.commit()

    logger.info("Organisation %s associated with municipality %s by %s", target_gov_id, org_id, current_user.email)
    return {
        "status": "success",
        "message": f"Organisation '{target_org.name}' successfully associated with municipality.",
        "associated_gov_org_ids": current_assocs,
    }


# ---------------------------------------------------------------------------
# Dashboard Style Alias Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/{organisation_id}/dashboard-style",
    response_model=DashboardStyleResponse,
    summary="Get the persisted dashboard style for an organisation (alias)",
)
def get_organisation_dashboard_style(
    organisation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Read the dashboard style preference (own organisation, or any for SUPER_ADMIN)."""
    target_org_id = verify_organisation_access(organisation_id, current_user)
    org = db.query(Organisation).filter(Organisation.id == target_org_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{target_org_id}' not found.",
        )
    style = org.effective_dashboard_style
    return DashboardStyleResponse(
        organisation_id=org.id,
        dashboard_style=style,
        available_styles=list(DASHBOARD_STYLE_VALUES),
        is_default=style == Organisation.DEFAULT_DASHBOARD_STYLE,
    )


@router.put(
    "/{organisation_id}/dashboard-style",
    response_model=DashboardStyleResponse,
    summary="Update the persisted dashboard style for an organisation (alias)",
)
def update_organisation_dashboard_style(
    organisation_id: str,
    body: DashboardStyleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist the dashboard style for an organisation (EXECUTIVE, OPERATIONS, ANALYTICS, COMMAND_CENTER)."""
    if current_user.role not in (User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Insufficient role permissions for this operation.",
        )
    target_org_id = verify_organisation_access(organisation_id, current_user)
    org = db.query(Organisation).filter(Organisation.id == target_org_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{target_org_id}' not found.",
        )
    desired = body.dashboard_style.strip().upper()
    org.dashboard_style = desired
    db.commit()
    db.refresh(org)
    return DashboardStyleResponse(
        organisation_id=org.id,
        dashboard_style=org.effective_dashboard_style,
        available_styles=list(DASHBOARD_STYLE_VALUES),
        is_default=org.effective_dashboard_style == Organisation.DEFAULT_DASHBOARD_STYLE,
    )


