"""
GreenNexa — Super Admin Platform Management Router.

Endpoints:
  GET    /api/v1/super-admin/overview            — Platform Overview metrics & organisation matrix
  GET    /api/v1/super-admin/facility-types      — List configurable facility types
  GET    /api/v1/super-admin/next-org-id         — Auto-generate next Organisation ID (e.g. ORG-00027)
  POST   /api/v1/super-admin/organisations/create-full — Multi-step atomic organisation & admin creation
  GET    /api/v1/super-admin/users               — List platform users / admins
  POST   /api/v1/super-admin/users               — Create admin user
  PUT    /api/v1/super-admin/users/{user_id}     — Update user or toggle active status
  POST   /api/v1/super-admin/users/{user_id}/reset-password — Reset user password with secure hash
  GET    /api/v1/super-admin/sensors             — Organisation-wise sensor configuration matrix
  PUT    /api/v1/super-admin/sensors/{org_id}    — Update organisation enabled sensors/modules
  GET    /api/v1/super-admin/iot                 — Platform-wide IoT devices overview
  GET    /api/v1/super-admin/alerts              — Platform-wide alerts overview
  GET    /api/v1/super-admin/reports             — Platform summary reports
"""

from __future__ import annotations

import json as _json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from pydantic import BaseModel, Field

from app.core import security
from app.core.dependencies import get_current_user, require_roles
import app.db.database as db_database
from app.db.database import get_db, safe_vacuum_sqlite, get_active_db_path, get_db_physical_size_bytes
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    EventReadState,
    FacilityBlock,
    IoTDevice,
    Message,
    MunicipalityWard,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
    _utcnow,
)
from app.services.forecasting import forecasting_service
from app.services.synthetic_simulator import simulator_instance
from app.services.otp_service import validate_and_normalize_indian_phone
from app.services.sms_service import mask_phone
from app.db.seed_demo import set_platform_data_cleared
from app.schemas.facility_block import BlockResponse
from app.schemas.ward import WardResponse
from app.schemas.super_admin import (
    FacilityTypeItem,
    FullOrganisationConfigResponse,
    FullOrganisationCreateRequest,
    FullOrganisationCreateResponse,
    FullOrganisationUpdateRequest,
    GovernmentOrgItem,
    MunicipalityAssociationRequest,
    MunicipalityAssociationResponse,
    OrganisationOverviewItem,
    OrganisationStorageItem,
    PasswordResetRequest,
    PlatformAlertItem,
    PlatformIoTDeviceItem,
    SensorConfigOverviewItem,
    StorageOverviewResponse,
    SuperAdminOverviewResponse,
    SuperAdminUserCreateRequest,
    SuperAdminUserItem,
    SuperAdminUserUpdateRequest,
    UpdateSensorConfigRequest,
    VerifyConfirmationPasswordRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/super-admin", tags=["Super Admin Platform Management"])


DEFAULT_FACILITY_TYPES = [
    {"id": "school", "name": "School", "description": "Primary and secondary educational campuses"},
    {"id": "college_university", "name": "College / University", "description": "Higher education institutions & university campuses"},
    {"id": "hospital", "name": "Hospital", "description": "Healthcare facilities and medical centres"},
    {"id": "municipality", "name": "Municipality / Municipal Campus", "description": "Local civic bodies, city halls, municipal zones"},
    {"id": "industrial_estate", "name": "Industrial Estate", "description": "Manufacturing hubs, industrial parks, tech parks"},
    {"id": "public_sector", "name": "Public Sector Facility", "description": "Government offices, public utility buildings"},
    {"id": "other_facility", "name": "Other Facility", "description": "Commercial complexes, private facilities, multi-tenant sites"},
]


# ---------------------------------------------------------------------------
# GET /super-admin/facility-types
# ---------------------------------------------------------------------------
@router.get(
    "/facility-types",
    response_model=List[FacilityTypeItem],
    summary="List configurable facility types",
)
def list_facility_types(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
):
    """Return available facility types for organisation creation."""
    return [FacilityTypeItem(**f) for f in DEFAULT_FACILITY_TYPES]


# ---------------------------------------------------------------------------
# GET /super-admin/next-org-id
# ---------------------------------------------------------------------------
@router.get(
    "/next-org-id",
    summary="Generate next Organisation ID",
)
def get_next_org_id(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Generate sequential unique Organisation ID e.g. ORG-00027."""
    count = db.query(Organisation).count()
    org_id = f"ORG-{count + 1:05d}"
    # Ensure no collision with existing custom IDs
    while db.query(Organisation).filter(Organisation.id == org_id).first() is not None:
        count += 1
        org_id = f"ORG-{count + 1:05d}"
    return {"next_id": org_id}


# ---------------------------------------------------------------------------
# GET /super-admin/overview
# ---------------------------------------------------------------------------
@router.get(
    "/overview",
    response_model=SuperAdminOverviewResponse,
    summary="Get platform overview KPIs and organisation list",
)
def get_platform_overview(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Return platform KPIs and full organisation management overview."""
    orgs = db.query(Organisation).order_by(Organisation.created_at.desc()).all()

    total_orgs = len(orgs)
    active_orgs = sum(1 for o in orgs if o.is_active)
    total_admins = db.query(User).filter(User.role == User.ROLE_ADMIN).count()
    active_iot_devices = db.query(IoTDevice).filter(IoTDevice.is_active == True).count()

    # Alerts calculation
    open_anomalies_count = db.query(AnomalyRecord).filter(AnomalyRecord.status == "OPEN").count()
    critical_alerts_count = (
        db.query(AnomalyRecord)
        .filter(AnomalyRecord.severity == "CRITICAL", AnomalyRecord.status == "OPEN")
        .count()
    )

    overview_items: List[OrganisationOverviewItem] = []

    for org in orgs:
        # Find primary admin for org
        admin = (
            db.query(User)
            .filter(User.organisation_id == org.id, User.role == User.ROLE_ADMIN)
            .first()
        )
        admin_name = admin.full_name if admin else (org.name + " Admin")
        admin_email = admin.email if admin else (org.contact_email or "N/A")

        # Enabled modules
        cfg = (
            db.query(OrganisationSensorConfig)
            .filter(OrganisationSensorConfig.organisation_id == org.id)
            .first()
        )
        enabled_modules = cfg.enabled_sensors_list if cfg else ["energy", "water", "temperature", "humidity"]

        # IoT devices count
        device_count = db.query(IoTDevice).filter(IoTDevice.organisation_id == org.id).count()

        # Build location string
        loc_parts = [p for p in [org.city, org.state] if p]
        location_str = ", ".join(loc_parts) if loc_parts else (org.location or "Location Not Set")

        overview_items.append(
            OrganisationOverviewItem(
                id=org.id,
                name=org.name,
                ownership_type=org.ownership_type,
                facility_type=org.org_type or "Facility",
                location=location_str,
                admin_name=admin_name,
                admin_email=admin_email,
                enabled_modules=enabled_modules,
                iot_devices_count=device_count,
                status="Active" if org.is_active else "Inactive",
                created_at=org.created_at,
            )
        )

    return SuperAdminOverviewResponse(
        total_organisations=total_orgs,
        active_organisations=active_orgs,
        total_admins=total_admins,
        active_iot_devices=active_iot_devices,
        platform_alerts=open_anomalies_count,
        critical_alerts=critical_alerts_count,
        organisations=overview_items,
    )


# ---------------------------------------------------------------------------
# POST /super-admin/organisations/create-full
# ---------------------------------------------------------------------------
@router.post(
    "/organisations/create-full",
    response_model=FullOrganisationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Multi-step creation of organisation, admin account, and sensor config",
)
def create_organisation_full(
    payload: FullOrganisationCreateRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Create a new organisation, generate its Admin user, and set up sensor config atomically."""
    # 1. Generate unique Organisation ID
    count = db.query(Organisation).count()
    org_id = f"ORG-{count + 1:05d}"
    while db.query(Organisation).filter(Organisation.id == org_id).first() is not None:
        count += 1
        org_id = f"ORG-{count + 1:05d}"

    admin_id = payload.admin_user_id.strip() if payload.admin_user_id else f"{org_id}_ADMIN"
    admin_email = payload.admin_email.strip().lower() if payload.admin_email else f"{admin_id.lower()}@greennexa.local"

    # Check if admin email or user ID already exists
    existing_user = (
        db.query(User)
        .filter((User.email == admin_email) | (User.id == admin_id))
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with ID '{admin_id}' or email '{admin_email}' already exists.",
        )

    # 2. Build Organisation
    raw_ownership = (payload.ownership_type or "PRIVATE").strip().upper()
    if raw_ownership not in (Organisation.OWNERSHIP_GOVERNMENT, Organisation.OWNERSHIP_PRIVATE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organisation ownership type. Allowed values are GOVERNMENT or PRIVATE.",
        )

    location_parts = [payload.city, payload.district, payload.state]
    location_str = ", ".join([p for p in location_parts if p])
    if payload.address:
        location_str = f"{payload.address}, {location_str}"

    # Validate mandatory Indian mobile number
    clean_phone = validate_and_normalize_indian_phone(payload.admin_phone)
    if not clean_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid 10-digit Indian mobile number is required (starting with 6, 7, 8, or 9).",
        )

    new_org = Organisation(
        id=org_id,
        name=payload.name.strip(),
        ownership_type=raw_ownership,
        org_type=payload.facility_type.strip(),
        facility_name=payload.facility_name.strip() if payload.facility_name else payload.name.strip(),
        state=payload.state.strip(),
        district=payload.district.strip(),
        city=payload.city.strip(),
        address=payload.address.strip(),
        org_code=payload.org_code.strip() if payload.org_code else None,
        location=location_str,
        contact_email=admin_email,
        contact_phone=clean_phone,
        is_active=True,
    )
    db.add(new_org)

    # 3. Build Admin User
    hashed_pwd = security.hash_password(payload.admin_password)

    new_admin = User(
        id=admin_id,
        organisation_id=org_id,
        email=admin_email,
        hashed_password=hashed_pwd,
        full_name=payload.admin_name.strip(),
        phone=clean_phone,
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    db.add(new_admin)

    # 4. Build Facility Blocks / Municipality Wards
    is_municipality = "municipality" in payload.facility_type.lower()
    setup_mode = (payload.municipality_setup_type or "NORMAL_MUNICIPALITY").strip().upper() if is_municipality else None

    created_blocks: List[FacilityBlock] = []
    created_wards: List[MunicipalityWard] = []

    if is_municipality:
        if setup_mode == "OWN_OFFICE":
            # In OWN_OFFICE setup, blocks represent the physical wings of the Municipality Own Office
            if payload.blocks:
                seen_names = set()
                for idx, blk_item in enumerate(payload.blocks, start=1):
                    name_clean = blk_item.block_name.strip()
                    if not name_clean:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Office block {idx} has an empty name.",
                        )
                    name_lower = name_clean.lower()
                    if name_lower in seen_names:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Duplicate office block name '{name_clean}' found.",
                        )
                    seen_names.add(name_lower)
                    b_id = blk_item.block_id.strip() if blk_item.block_id else f"BLK-{idx:03d}"
                    block_obj = FacilityBlock(
                        organisation_id=org_id,
                        block_id=b_id,
                        block_name=name_clean,
                        is_active=True,
                    )
                    db.add(block_obj)
                    created_blocks.append(block_obj)
        else:
            # NORMAL_MUNICIPALITY setup:
            # Wards are created in municipality_wards table ONLY.
            # Never create FacilityBlocks for wards!
            ward_inputs = payload.wards if payload.wards else payload.blocks
            if ward_inputs:
                seen_names = set()
                for idx, w_item in enumerate(ward_inputs, start=1):
                    w_name = getattr(w_item, "ward_name", None) or getattr(w_item, "block_name", None)
                    if not w_name or not w_name.strip():
                        continue
                    w_name_clean = w_name.strip()
                    if w_name_clean.lower() in seen_names:
                        continue
                    seen_names.add(w_name_clean)
                    w_num = getattr(w_item, "ward_number", None) or getattr(w_item, "block_id", None)
                    if not w_num or not w_num.strip():
                        w_num = f"{idx}"
                    else:
                        w_num = w_num.strip()

                    ward_obj = MunicipalityWard(
                        municipality_id=org_id,
                        ward_number=w_num,
                        ward_name=w_name_clean,
                        zone=getattr(w_item, "zone", None),
                        population=getattr(w_item, "population", None),
                        area_sq_km=getattr(w_item, "area_sq_km", None),
                        is_active=True,
                    )
                    db.add(ward_obj)
                    created_wards.append(ward_obj)
    else:
        # Standard organisation (Hospital, School, College, etc.)
        if payload.blocks:
            seen_names = set()
            for idx, blk_item in enumerate(payload.blocks, start=1):
                name_clean = blk_item.block_name.strip()
                if not name_clean:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Block {idx} has an empty name.",
                    )
                name_lower = name_clean.lower()
                if name_lower in seen_names:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Duplicate block name '{name_clean}' found.",
                    )
                seen_names.add(name_lower)

                b_id = blk_item.block_id.strip() if blk_item.block_id else f"BLK-{idx:03d}"
                block_obj = FacilityBlock(
                    organisation_id=org_id,
                    block_id=b_id,
                    block_name=name_clean,
                    is_active=True,
                )
                db.add(block_obj)
                created_blocks.append(block_obj)

    # 5. Build Sensor Config
    from app.core.sensor_catalog import (
        get_recommended_sensors_for_type,
        get_default_configs_for_sensors,
    )
    if payload.enabled_modules:
        # Explicit module selection is honored exactly; recommended extras are NOT added.
        combined = list(dict.fromkeys(m.lower().strip() for m in payload.enabled_modules if m and m.strip()))
    else:
        combined = list(get_recommended_sensors_for_type(payload.facility_type))
    if payload.sensor_configs:
        sensor_keys = list(payload.sensor_configs.keys())
        sensors_str = "|".join([s.lower().strip() for s in sensor_keys])
    else:
        sensors_str = "|".join(combined)

    new_cfg = OrganisationSensorConfig(
        organisation_id=org_id,
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        enabled_sensors=sensors_str,
        is_active=True,
    )

    if payload.sensor_configs:
        formatted_configs = {}
        for k, v in payload.sensor_configs.items():
            if isinstance(v, dict):
                formatted_configs[k] = v
            elif hasattr(v, "model_dump"):
                formatted_configs[k] = v.model_dump()
            elif hasattr(v, "dict"):
                formatted_configs[k] = v.dict()
        new_cfg.set_sensor_configs(formatted_configs)
    else:
        new_cfg.set_sensor_configs(get_default_configs_for_sensors(combined))

    if payload.associated_gov_org_ids:
        try:
            curr_configs = new_cfg.sensor_configs_dict
            curr_configs["associated_gov_org_ids"] = payload.associated_gov_org_ids
            curr_configs["_municipality_assoc"] = payload.associated_gov_org_ids
            new_cfg.set_sensor_configs(curr_configs)
        except Exception:
            pass

    db.add(new_cfg)

    db.commit()
    db.refresh(new_org)
    db.refresh(new_admin)
    db.refresh(new_cfg)

    for b in created_blocks:
        db.refresh(b)
    for w in created_wards:
        db.refresh(w)

    logger.info(
        "Organisation created full: org_id=%s admin_id=%s blocks=%d wards=%d by superadmin=%s",
        org_id,
        admin_id,
        len(created_blocks),
        len(created_wards),
        current_user.email,
    )

    return FullOrganisationCreateResponse(
        organisation_id=new_org.id,
        organisation_name=new_org.name,
        ownership_type=new_org.ownership_type,
        facility_type=new_org.org_type or payload.facility_type,
        admin_user_id=new_admin.id,
        admin_email=new_admin.email,
        enabled_modules=new_cfg.enabled_sensors_list,
        sensor_configs=new_cfg.sensor_configs_dict,
        blocks=[BlockResponse.model_validate(b) for b in created_blocks],
        wards=[WardResponse.model_validate(w) for w in created_wards],
        municipality_setup_type=setup_mode,
        created_at=new_org.created_at,
    )


# ---------------------------------------------------------------------------
# GET /super-admin/organisations/{organisation_id}/full-config
# ---------------------------------------------------------------------------
@router.get(
    "/organisations/{organisation_id}/full-config",
    response_model=FullOrganisationConfigResponse,
    summary="Get full organisation configuration for editing (Super Admin)",
)
def get_organisation_full_config(
    organisation_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieve full configuration of an existing organisation for editing."""
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{organisation_id}' not found.",
        )

    # Primary Admin
    admin = (
        db.query(User)
        .filter(User.organisation_id == org.id, User.role == User.ROLE_ADMIN)
        .order_by(User.created_at.asc())
        .first()
    )
    admin_name = admin.full_name if admin else (org.name + " Admin")
    admin_user_id = admin.id if admin else f"{org.id}_ADMIN"
    admin_email = admin.email if admin else (org.contact_email or f"{org.id.lower()}_admin@greennexa.local")
    admin_phone = admin.phone if admin else org.contact_phone

    # Blocks (active only)
    blocks = (
        db.query(FacilityBlock)
        .filter(FacilityBlock.organisation_id == org.id, FacilityBlock.is_active == True)
        .order_by(FacilityBlock.block_id.asc())
        .all()
    )

    # Sensor config
    cfg = (
        db.query(OrganisationSensorConfig)
        .filter(OrganisationSensorConfig.organisation_id == org.id)
        .first()
    )
    enabled_modules = cfg.enabled_sensors_list if cfg else ["energy", "water", "temperature", "humidity"]
    sensor_configs = cfg.sensor_configs_dict if cfg else {}

    return FullOrganisationConfigResponse(
        organisation_id=org.id,
        organisation_name=org.name,
        ownership_type=org.ownership_type,
        facility_type=org.org_type or "School",
        facility_name=org.facility_name or org.name,
        state=org.state or "",
        district=org.district or "",
        city=org.city or "",
        address=org.address or "",
        org_code=org.org_code,
        location=org.location or "",
        contact_email=org.contact_email,
        contact_phone=org.contact_phone,
        is_active=org.is_active,
        admin_name=admin_name,
        admin_user_id=admin_user_id,
        admin_email=admin_email,
        admin_phone=admin_phone,
        enabled_modules=enabled_modules,
        sensor_configs=sensor_configs,
        blocks=[BlockResponse.model_validate(b) for b in blocks],
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


# ---------------------------------------------------------------------------
# PUT /super-admin/organisations/{organisation_id}/edit-full
# ---------------------------------------------------------------------------
@router.put(
    "/organisations/{organisation_id}/edit-full",
    response_model=FullOrganisationConfigResponse,
    summary="Edit existing organisation configuration atomically (Super Admin)",
)
def edit_organisation_full(
    organisation_id: str,
    payload: FullOrganisationUpdateRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Update an existing organisation's configuration atomically.
    Preserves untouched fields, maintains historical operational records,
    and safely deactivates facility blocks if historical records reference them.
    """
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{organisation_id}' not found.",
        )

    # 1. Update basic organisation profile fields if provided
    if payload.name is not None:
        clean_name = payload.name.strip()
        if not clean_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organisation name cannot be empty.")
        org.name = clean_name

    if payload.ownership_type is not None:
        clean_ownership = payload.ownership_type.strip().upper()
        if clean_ownership not in (Organisation.OWNERSHIP_GOVERNMENT, Organisation.OWNERSHIP_PRIVATE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organisation ownership type. Allowed values are GOVERNMENT or PRIVATE.",
            )
        org.ownership_type = clean_ownership

    if payload.facility_type is not None:
        clean_type = payload.facility_type.strip()
        if not clean_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Facility type cannot be empty.")
        org.org_type = clean_type

    if payload.facility_name is not None:
        org.facility_name = payload.facility_name.strip() or org.name

    if payload.state is not None:
        org.state = payload.state.strip()
    if payload.district is not None:
        org.district = payload.district.strip()
    if payload.city is not None:
        org.city = payload.city.strip()
    if payload.address is not None:
        org.address = payload.address.strip()
    if payload.org_code is not None:
        org.org_code = payload.org_code.strip() or None

    # Recompute location string if location fields provided
    loc_parts = [p for p in [org.city, org.district, org.state] if p]
    new_loc = ", ".join(loc_parts)
    if org.address:
        new_loc = f"{org.address}, {new_loc}"
    org.location = new_loc

    # 2. Update Admin metadata if provided
    admin = (
        db.query(User)
        .filter(User.organisation_id == org.id, User.role == User.ROLE_ADMIN)
        .order_by(User.created_at.asc())
        .first()
    )
    if admin:
        if payload.admin_name is not None and payload.admin_name.strip():
            admin.full_name = payload.admin_name.strip()
        if payload.admin_phone is not None:
            admin.phone = payload.admin_phone.strip() or None
            org.contact_phone = admin.phone

    # 3. Update Facility Blocks if provided
    if payload.blocks is not None:
        if len(payload.blocks) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organisation must have at least 1 facility block.",
            )

        # Validate unique block names and non-empty
        seen_names = set()
        for idx, blk_item in enumerate(payload.blocks, start=1):
            name_clean = blk_item.block_name.strip()
            if not name_clean:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Block {idx} has an empty name.",
                )
            name_lower = name_clean.lower()
            if name_lower in seen_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate block name '{name_clean}' found.",
                )
            seen_names.add(name_lower)

        # Existing blocks in database for this org
        existing_blocks = db.query(FacilityBlock).filter(FacilityBlock.organisation_id == org.id).all()
        existing_by_id = {b.block_id: b for b in existing_blocks}

        keep_block_ids = set()

        for idx, blk_item in enumerate(payload.blocks, start=1):
            b_id = blk_item.block_id.strip() if blk_item.block_id else f"BLK-{idx:03d}"
            name_clean = blk_item.block_name.strip()
            keep_block_ids.add(b_id)

            if b_id in existing_by_id:
                # Update existing block
                existing_block = existing_by_id[b_id]
                existing_block.block_name = name_clean
                existing_block.is_active = True
                existing_block.updated_at = _utcnow()
            else:
                # Add new block
                new_block = FacilityBlock(
                    organisation_id=org.id,
                    block_id=b_id,
                    block_name=name_clean,
                    is_active=True,
                )
                db.add(new_block)

        # For existing blocks NOT in payload:
        # Check if historical records reference this block
        for b_id, old_blk in existing_by_id.items():
            if b_id not in keep_block_ids:
                has_history = (
                    db.query(SensorReading).filter(SensorReading.organisation_id == org.id, SensorReading.block_id == b_id).first() is not None
                    or db.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == org.id, AnomalyRecord.block_id == b_id).first() is not None
                    or db.query(AIRecommendation).filter(AIRecommendation.organisation_id == org.id, AIRecommendation.block_id == b_id).first() is not None
                )
                if has_history:
                    # Safe deactivation to preserve historical records
                    old_blk.is_active = False
                    old_blk.updated_at = _utcnow()
                else:
                    # Safe to delete since no historical data references it
                    db.delete(old_blk)

    # 4. Update Enabled Modules & Sensor Config if provided
    cfg = (
        db.query(OrganisationSensorConfig)
        .filter(OrganisationSensorConfig.organisation_id == org.id)
        .first()
    )
    if not cfg:
        cfg = OrganisationSensorConfig(
            organisation_id=org.id,
            data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
            is_active=True,
        )
        db.add(cfg)

    if payload.enabled_modules is not None:
        if len(payload.enabled_modules) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one module must be enabled.",
            )
        cfg.set_enabled_sensors(payload.enabled_modules)

    if payload.sensor_configs is not None:
        current_dict = cfg.sensor_configs_dict
        formatted_configs = dict(current_dict)
        for k, v in payload.sensor_configs.items():
            k_clean = k.lower().strip()
            v_dict = v.model_dump() if hasattr(v, "model_dump") else (v.dict() if hasattr(v, "dict") else dict(v))
            baseline_val = float(v_dict.get("baseline", 100))
            if baseline_val <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Baseline for '{k}' must be greater than 0.",
                )
            warn_val = float(v_dict.get("warning_threshold", 15))
            crit_val = float(v_dict.get("critical_threshold", 30))
            if warn_val < 0 or crit_val < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Thresholds for '{k}' cannot be negative.",
                )
            if warn_val > crit_val:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Warning threshold ({warn_val}%) cannot exceed critical threshold ({crit_val}%) for '{k}'.",
                )
            formatted_configs[k_clean] = v_dict

        cfg.set_sensor_configs(formatted_configs)

    org.updated_at = _utcnow()
    cfg.updated_at = _utcnow()

    db.commit()
    db.refresh(org)
    db.refresh(cfg)

    # Return refreshed configuration
    active_blocks = (
        db.query(FacilityBlock)
        .filter(FacilityBlock.organisation_id == org.id, FacilityBlock.is_active == True)
        .order_by(FacilityBlock.block_id.asc())
        .all()
    )

    admin_name = admin.full_name if admin else (org.name + " Admin")
    admin_user_id = admin.id if admin else f"{org.id}_ADMIN"
    admin_email = admin.email if admin else (org.contact_email or f"{org.id.lower()}_admin@greennexa.local")
    admin_phone = admin.phone if admin else org.contact_phone

    logger.info("Organisation %s full configuration updated by SuperAdmin %s", org.id, current_user.email)

    return FullOrganisationConfigResponse(
        organisation_id=org.id,
        organisation_name=org.name,
        ownership_type=org.ownership_type,
        facility_type=org.org_type or "School",
        facility_name=org.facility_name or org.name,
        state=org.state or "",
        district=org.district or "",
        city=org.city or "",
        address=org.address or "",
        org_code=org.org_code,
        location=org.location or "",
        contact_email=org.contact_email,
        contact_phone=org.contact_phone,
        is_active=org.is_active,
        admin_name=admin_name,
        admin_user_id=admin_user_id,
        admin_email=admin_email,
        admin_phone=admin_phone,
        enabled_modules=cfg.enabled_sensors_list,
        sensor_configs=cfg.sensor_configs_dict,
        blocks=[BlockResponse.model_validate(b) for b in active_blocks],
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /super-admin/organisations/government
# ---------------------------------------------------------------------------
@router.get(
    "/organisations/government",
    response_model=List[GovernmentOrgItem],
    summary="List all GOVERNMENT-owned organisations for association browsing",
)
def list_government_organisations(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Return all GOVERNMENT organisations for municipality association."""
    gov_orgs = (
        db.query(Organisation)
        .filter(Organisation.ownership_type == Organisation.OWNERSHIP_GOVERNMENT)
        .order_by(Organisation.name.asc())
        .all()
    )
    return [
        GovernmentOrgItem(
            id=o.id,
            name=o.name,
            org_type=o.org_type,
            location=o.location,
            is_active=o.is_active,
        )
        for o in gov_orgs
    ]


# ---------------------------------------------------------------------------
# GET /super-admin/organisations/{organisation_id} (alias for full-config)
# ---------------------------------------------------------------------------
@router.get(
    "/organisations/{organisation_id}",
    response_model=FullOrganisationConfigResponse,
    summary="Get full organisation configuration (Super Admin alias)",
)
def get_organisation_by_id(
    organisation_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieve full configuration of an existing organisation."""
    return get_organisation_full_config(organisation_id=organisation_id, current_user=current_user, db=db)


# ---------------------------------------------------------------------------
# GET /super-admin/organisations/{org_id}/municipality-associations
# ---------------------------------------------------------------------------
@router.get(
    "/organisations/{org_id}/municipality-associations",
    response_model=MunicipalityAssociationResponse,
    summary="Get associated government organisations for a municipality",
)
def get_municipality_associations(
    org_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieve list of GOVERNMENT organisation IDs associated with this municipality."""
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organisation '{org_id}' not found.")

    cfg = db.query(OrganisationSensorConfig).filter(OrganisationSensorConfig.organisation_id == org_id).first()
    assoc_ids: List[str] = []
    if cfg and cfg.sensor_configs:
        try:
            stored = _json.loads(cfg.sensor_configs)
            assoc_ids = stored.get("associated_gov_org_ids") or stored.get("_municipality_assoc") or []
            if not isinstance(assoc_ids, list):
                assoc_ids = []
        except Exception:
            assoc_ids = []

    return MunicipalityAssociationResponse(
        organisation_id=org_id,
        associated_gov_org_ids=assoc_ids,
        message="Associations retrieved successfully.",
    )


# ---------------------------------------------------------------------------
# PUT /super-admin/organisations/{org_id}/municipality-associations
# ---------------------------------------------------------------------------
@router.put(
    "/organisations/{org_id}/municipality-associations",
    response_model=MunicipalityAssociationResponse,
    summary="Update associated government organisations for a municipality",
)
def update_municipality_associations(
    org_id: str,
    payload: MunicipalityAssociationRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Update list of GOVERNMENT organisations associated with this municipality."""
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organisation '{org_id}' not found.")

    target_ids = list(dict.fromkeys(payload.associated_gov_org_ids))
    if target_ids:
        valid_gov_orgs = (
            db.query(Organisation.id)
            .filter(
                Organisation.id.in_(target_ids),
                Organisation.ownership_type == Organisation.OWNERSHIP_GOVERNMENT,
            )
            .all()
        )
        valid_ids = {row[0] for row in valid_gov_orgs}
        invalid_ids = [t_id for t_id in target_ids if t_id not in valid_ids]
        if invalid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The following organisations are not valid GOVERNMENT organisations: {', '.join(invalid_ids)}",
            )

    cfg = db.query(OrganisationSensorConfig).filter(OrganisationSensorConfig.organisation_id == org_id).first()
    if not cfg:
        cfg = OrganisationSensorConfig(
            organisation_id=org_id,
            data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
            is_active=True,
        )
        db.add(cfg)

    stored = {}
    if cfg.sensor_configs:
        try:
            stored = _json.loads(cfg.sensor_configs)
        except Exception:
            stored = {}

    stored["associated_gov_org_ids"] = target_ids
    stored["_municipality_assoc"] = target_ids
    cfg.sensor_configs = _json.dumps(stored)
    cfg.updated_at = _utcnow()

    db.commit()
    db.refresh(cfg)

    logger.info(
        "Updated municipality associations for %s: %d orgs by superadmin %s",
        org_id,
        len(target_ids),
        current_user.email,
    )

    return MunicipalityAssociationResponse(
        organisation_id=org_id,
        associated_gov_org_ids=target_ids,
        message="Municipality government associations updated successfully.",
    )


# ---------------------------------------------------------------------------
# GET /super-admin/users
# ---------------------------------------------------------------------------
@router.get(
    "/users",
    response_model=List[SuperAdminUserItem],
    summary="List platform users / admins",
)
def list_platform_users(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """List all user and admin accounts across all organisations."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    res: List[SuperAdminUserItem] = []

    for u in users:
        org_name = u.organisation.name if u.organisation else "Platform Wide"
        res.append(
            SuperAdminUserItem(
                id=u.id,
                full_name=u.full_name,
                email=u.email,
                phone=u.phone,
                role=u.role,
                organisation_id=u.organisation_id,
                organisation_name=org_name,
                is_active=u.is_active,
                created_at=u.created_at,
                last_login_at=u.last_login_at,
            )
        )
    return res


# ---------------------------------------------------------------------------
# POST /super-admin/users
# ---------------------------------------------------------------------------
@router.post(
    "/users",
    response_model=SuperAdminUserItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Admin user account",
)
def create_user(
    payload: SuperAdminUserCreateRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Create an admin user account for a specific organisation."""
    if payload.role not in (User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{payload.role}'. Only SUPER_ADMIN and ADMIN are allowed.",
        )

    existing = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{payload.email}' already exists.",
        )

    org = db.query(Organisation).filter(Organisation.id == payload.organisation_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{payload.organisation_id}' not found.",
        )

    user_id = payload.user_id.strip() if payload.user_id else str(uuid.uuid4())
    hashed_pwd = security.hash_password(payload.password)

    new_user = User(
        id=user_id,
        organisation_id=payload.organisation_id,
        email=payload.email.strip().lower(),
        hashed_password=hashed_pwd,
        full_name=payload.full_name.strip(),
        phone=payload.phone.strip() if payload.phone else None,
        role=payload.role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info("User created: id=%s email=%s role=%s org=%s", new_user.id, new_user.email, new_user.role, new_user.organisation_id)

    return SuperAdminUserItem(
        id=new_user.id,
        full_name=new_user.full_name,
        email=new_user.email,
        phone=new_user.phone,
        role=new_user.role,
        organisation_id=new_user.organisation_id,
        organisation_name=org.name,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        last_login_at=new_user.last_login_at,
    )


# ---------------------------------------------------------------------------
# PUT /super-admin/users/{user_id}
# ---------------------------------------------------------------------------
@router.put(
    "/users/{user_id}",
    response_model=SuperAdminUserItem,
    summary="Update user profile or toggle status",
)
def update_user(
    user_id: str,
    payload: SuperAdminUserUpdateRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Update user details or active status."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    if payload.full_name is not None:
        target_user.full_name = payload.full_name.strip()
    if payload.email is not None:
        target_user.email = payload.email.strip().lower()
    if payload.phone is not None:
        target_user.phone = payload.phone.strip()
    if payload.is_active is not None:
        target_user.is_active = payload.is_active
    if payload.role is not None:
        target_user.role = payload.role

    db.commit()
    db.refresh(target_user)

    org_name = target_user.organisation.name if target_user.organisation else "Platform Wide"
    return SuperAdminUserItem(
        id=target_user.id,
        full_name=target_user.full_name,
        email=target_user.email,
        phone=target_user.phone,
        role=target_user.role,
        organisation_id=target_user.organisation_id,
        organisation_name=org_name,
        is_active=target_user.is_active,
        created_at=target_user.created_at,
        last_login_at=target_user.last_login_at,
    )


# ---------------------------------------------------------------------------
# POST /super-admin/verify-confirmation-password
# ---------------------------------------------------------------------------
@router.post(
    "/verify-confirmation-password",
    summary="Verify destructive action confirmation password",
)
def verify_destructive_confirmation_password(
    payload: VerifyConfirmationPasswordRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
):
    """
    Authoritatively verify the product owner's confirmation password for
    destructive/security-sensitive operations (Reset Password and Clear All Data).
    """
    if not security.verify_confirmation_password(payload.confirmation_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation password",
        )
    return {"valid": True, "message": "Confirmation password verified."}


# ---------------------------------------------------------------------------
# POST /super-admin/users/{user_id}/reset-password
# ---------------------------------------------------------------------------
@router.post(
    "/users/{user_id}/reset-password",
    summary="Reset user password safely with mandatory confirmation password",
)
def reset_user_password(
    user_id: str,
    payload: PasswordResetRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Reset user password using PBKDF2 hashing.
    Requires mandatory confirmation password verification before execution.
    """
    # 1. Authoritative verification of confirmation password
    if not security.verify_confirmation_password(payload.confirmation_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation password",
        )

    # 2. Check confirm_new_password if provided
    if payload.confirm_new_password is not None and payload.new_password != payload.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    # 3. Locate target user (by ID or Email, case-insensitive)
    target_user = db.query(User).filter(
        or_(
            User.id == user_id,
            func.lower(User.email) == user_id.lower().strip(),
            func.lower(User.id) == user_id.lower().strip(),
        )
    ).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    # 4. Hash and persist to actual database record
    target_user.hashed_password = security.hash_password(payload.new_password)
    db.commit()
    db.refresh(target_user)

    logger.info("Password reset for user_id=%s (%s) by superadmin=%s", target_user.id, target_user.email, current_user.email)
    return {"message": f"Password reset successfully for user '{target_user.email}'."}


# ---------------------------------------------------------------------------
# GET /super-admin/sensors
# ---------------------------------------------------------------------------
@router.get(
    "/sensors",
    response_model=List[SensorConfigOverviewItem],
    summary="Organisation-wise sensor configuration matrix",
)
def list_sensor_configs(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieve sensor configurations for all organisations."""
    orgs = db.query(Organisation).all()
    res: List[SensorConfigOverviewItem] = []

    for org in orgs:
        cfg = (
            db.query(OrganisationSensorConfig)
            .filter(OrganisationSensorConfig.organisation_id == org.id)
            .first()
        )
        if not cfg:
            cfg = OrganisationSensorConfig(
                organisation_id=org.id,
                data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
                enabled_sensors="energy|water|temperature|humidity",
                is_active=True,
            )
            db.add(cfg)
            db.commit()
            db.refresh(cfg)

        res.append(
            SensorConfigOverviewItem(
                organisation_id=org.id,
                organisation_name=org.name,
                facility_type=org.org_type or "Facility",
                data_source=cfg.data_source,
                enabled_modules=cfg.enabled_sensors_list,
                sensor_configs=cfg.sensor_configs_dict,
                is_active=cfg.is_active,
                updated_at=cfg.updated_at or cfg.created_at,
            )
        )
    return res


# ---------------------------------------------------------------------------
# GET /super-admin/sensors/{org_id}
# ---------------------------------------------------------------------------
@router.get(
    "/sensors/{org_id}",
    response_model=SensorConfigOverviewItem,
    summary="Get sensor configuration for a specific organisation",
)
def get_organisation_sensor_config(
    org_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieve sensor configuration for a specific organisation."""
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{org_id}' not found.",
        )

    cfg = (
        db.query(OrganisationSensorConfig)
        .filter(OrganisationSensorConfig.organisation_id == org_id)
        .first()
    )
    if not cfg:
        cfg = OrganisationSensorConfig(
            organisation_id=org_id,
            data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
            enabled_sensors="energy|water|temperature|humidity",
            is_active=True,
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)

    return SensorConfigOverviewItem(
        organisation_id=org.id,
        organisation_name=org.name,
        facility_type=org.org_type or "Facility",
        data_source=cfg.data_source,
        enabled_modules=cfg.enabled_sensors_list,
        sensor_configs=cfg.sensor_configs_dict,
        is_active=cfg.is_active,
        updated_at=cfg.updated_at or cfg.created_at,
    )


# ---------------------------------------------------------------------------
# PUT /super-admin/sensors/{org_id}
# ---------------------------------------------------------------------------
@router.put(
    "/sensors/{org_id}",
    response_model=SensorConfigOverviewItem,
    summary="Update organisation enabled sensors/modules and threshold configuration",
)
def update_organisation_sensor_config(
    org_id: str,
    payload: Any = Body(...),
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Update enabled modules and baseline/threshold settings for an organisation without deleting historical data."""
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{org_id}' not found.",
        )

    cfg = (
        db.query(OrganisationSensorConfig)
        .filter(OrganisationSensorConfig.organisation_id == org_id)
        .first()
    )
    if not cfg:
        cfg = OrganisationSensorConfig(
            organisation_id=org_id,
            data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
            is_active=True,
        )
        db.add(cfg)

    # Parse payload (list of modules or config object)
    enabled_modules: List[str] = []
    sensor_configs: Optional[dict] = None

    if isinstance(payload, list):
        enabled_modules = payload
    elif isinstance(payload, dict):
        enabled_modules = payload.get("enabled_modules", payload.get("enabled_sensors", []))
        sensor_configs = payload.get("sensor_configs")
        for col_name, col_val in payload.items():
            if hasattr(cfg, col_name) and col_name not in {"id", "organisation_id", "created_at", "updated_at", "enabled_sensors", "sensor_configs"}:
                try:
                    setattr(cfg, col_name, col_val)
                except Exception:
                    pass
    elif hasattr(payload, "enabled_modules"):
        enabled_modules = getattr(payload, "enabled_modules", [])
        sensor_configs = getattr(payload, "sensor_configs", None)

    if enabled_modules:
        cfg.set_enabled_sensors(enabled_modules)

    if sensor_configs is not None:
        # Format dictionary safely
        formatted_configs = {}
        for k, v in sensor_configs.items():
            if isinstance(v, dict):
                formatted_configs[k] = v
            elif hasattr(v, "dict"):
                formatted_configs[k] = v.dict()
        cfg.set_sensor_configs(formatted_configs)

    cfg.updated_at = _utcnow()
    db.commit()
    db.refresh(cfg)

    return SensorConfigOverviewItem(
        organisation_id=org.id,
        organisation_name=org.name,
        facility_type=org.org_type or "Facility",
        data_source=cfg.data_source,
        enabled_modules=cfg.enabled_sensors_list,
        sensor_configs=cfg.sensor_configs_dict,
        is_active=cfg.is_active,
        updated_at=cfg.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /super-admin/sensor-catalog
# ---------------------------------------------------------------------------
@router.get(
    "/sensor-catalog",
    summary="Get master sensor catalog and recommended defaults by type",
)
def get_sensor_catalog_route(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
):
    from app.core.sensor_catalog import (
        MASTER_SENSOR_CATALOG,
        RECOMMENDED_SENSORS_BY_TYPE,
    )
    return {
        "catalog": MASTER_SENSOR_CATALOG,
        "categories": ["CORE", "MUNICIPALITY / OUTDOOR", "ASSET / UTILISATION", "INDUSTRIAL"],
        "recommended_by_type": RECOMMENDED_SENSORS_BY_TYPE,
        "recommendations": RECOMMENDED_SENSORS_BY_TYPE,
    }


# ---------------------------------------------------------------------------
# GET /super-admin/sensor-catalog/defaults
# ---------------------------------------------------------------------------
@router.get(
    "/sensor-catalog/defaults",
    summary="Get recommended sensor IDs and default settings for an organisation/facility type",
)
def get_sensor_defaults_route(
    type: str = Query(..., description="Organisation or Facility type e.g. Hospital, Municipality"),
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
):
    from app.core.sensor_catalog import (
        get_recommended_sensors_for_type,
        get_default_configs_for_sensors,
        normalize_type_key,
    )
    recommended = get_recommended_sensors_for_type(type)
    default_configs = get_default_configs_for_sensors(recommended)
    return {
        "type": type,
        "normalized_key": normalize_type_key(type),
        "recommended_sensors": recommended,
        "default_configs": default_configs,
        "default_sensor_configs": default_configs,
    }


# ---------------------------------------------------------------------------
# POST /super-admin/sensors/{org_id}/reset-recommended
# ---------------------------------------------------------------------------
@router.post(
    "/sensors/{org_id}/reset-recommended",
    response_model=SensorConfigOverviewItem,
    summary="Reset an organisation's sensors and thresholds to recommended defaults for its type",
)
def reset_organisation_sensors_to_recommended(
    org_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Restore recommended default sensors and thresholds for the organisation's facility type."""
    from app.core.sensor_catalog import (
        get_recommended_sensors_for_type,
        get_default_configs_for_sensors,
    )

    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{org_id}' not found.",
        )

    cfg = (
        db.query(OrganisationSensorConfig)
        .filter(OrganisationSensorConfig.organisation_id == org_id)
        .first()
    )
    if not cfg:
        cfg = OrganisationSensorConfig(
            organisation_id=org_id,
            data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
            is_active=True,
        )
        db.add(cfg)

    recommended = get_recommended_sensors_for_type(org.org_type)
    default_configs = get_default_configs_for_sensors(recommended)

    cfg.set_enabled_sensors(recommended)
    cfg.set_sensor_configs(default_configs)
    cfg.updated_at = _utcnow()
    db.commit()
    db.refresh(cfg)

    return SensorConfigOverviewItem(
        organisation_id=org.id,
        organisation_name=org.name,
        facility_type=org.org_type or "Facility",
        data_source=cfg.data_source,
        enabled_modules=cfg.enabled_sensors_list,
        sensor_configs=cfg.sensor_configs_dict,
        is_active=cfg.is_active,
        updated_at=cfg.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /super-admin/iot
# ---------------------------------------------------------------------------
@router.get(
    "/iot",
    response_model=List[PlatformIoTDeviceItem],
    summary="Platform-wide IoT devices overview",
)
def list_platform_iot_devices(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """List all IoT devices registered across organisations."""
    devices = db.query(IoTDevice).order_by(IoTDevice.created_at.desc()).all()
    res: List[PlatformIoTDeviceItem] = []

    now_dt = datetime.now(timezone.utc)

    for dev in devices:
        org_name = dev.organisation.name if dev.organisation else "Unassigned"
        # Determine status (online if seen in last 10 minutes)
        status_str = "OFFLINE"
        if dev.last_seen_at:
            last_seen_utc = dev.last_seen_at.replace(tzinfo=timezone.utc) if dev.last_seen_at.tzinfo is None else dev.last_seen_at
            if (now_dt - last_seen_utc).total_seconds() <= 600:
                status_str = "ONLINE"

        res.append(
            PlatformIoTDeviceItem(
                id=dev.id,
                device_id=dev.device_id,
                device_name=dev.device_name,
                organisation_id=dev.organisation_id,
                organisation_name=org_name,
                device_type=dev.device_type,
                sensor_type="Multi-Sensor",
                status=status_str if dev.is_active else "DISABLED",
                last_seen_at=dev.last_seen_at,
                source="iot",
            )
        )
    return res


# ---------------------------------------------------------------------------
# GET /super-admin/alerts
# ---------------------------------------------------------------------------
@router.get(
    "/alerts",
    response_model=List[PlatformAlertItem],
    summary="Platform-wide alerts overview",
)
def list_platform_alerts(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """List system-level and critical organisation alerts."""
    alerts: List[PlatformAlertItem] = []

    # 1. Fetch recent open anomalies across platform
    anomalies = (
        db.query(AnomalyRecord)
        .filter(AnomalyRecord.status == "OPEN")
        .order_by(AnomalyRecord.timestamp.desc())
        .limit(20)
        .all()
    )

    for anom in anomalies:
        org_name = anom.organisation.name if anom.organisation else "Unknown Org"
        alerts.append(
            PlatformAlertItem(
                id=anom.id,
                title=f"{anom.metric.upper()} Anomaly Detected ({anom.severity})",
                severity=anom.severity,
                category="SENSOR",
                organisation_id=anom.organisation_id,
                organisation_name=org_name,
                description=anom.reason or f"Abnormal metric reading value {anom.value}",
                created_at=anom.timestamp,
            )
        )

    # 2. Check for offline IoT devices
    offline_devices = db.query(IoTDevice).filter(IoTDevice.is_active == True).all()
    now_dt = datetime.now(timezone.utc)
    for dev in offline_devices:
        if dev.last_seen_at:
            last_seen_utc = dev.last_seen_at.replace(tzinfo=timezone.utc) if dev.last_seen_at.tzinfo is None else dev.last_seen_at
            if (now_dt - last_seen_utc).total_seconds() > 3600:
                org_name = dev.organisation.name if dev.organisation else "Unknown Org"
                alerts.append(
                    PlatformAlertItem(
                        id=f"dev-off-{dev.id}",
                        title=f"IoT Device Offline: {dev.device_name}",
                        severity="HIGH",
                        category="DEVICE",
                        organisation_id=dev.organisation_id,
                        organisation_name=org_name,
                        description=f"Device '{dev.device_id}' has not sent telemetry for over 1 hour.",
                        created_at=dev.last_seen_at,
                    )
                )

    return alerts


# ---------------------------------------------------------------------------
# GET /super-admin/reports
# ---------------------------------------------------------------------------
@router.get(
    "/reports",
    summary="Platform summary reports",
)
def get_platform_reports(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Return downloadable/viewable platform summary reports data."""
    orgs_count = db.query(Organisation).count()
    users_count = db.query(User).count()
    devices_count = db.query(IoTDevice).count()
    readings_count = db.query(SensorReading).count()

    return {
        "generated_at": _utcnow().isoformat(),
        "summary": {
            "total_organisations": orgs_count,
            "total_users": users_count,
            "total_iot_devices": devices_count,
            "total_sensor_readings": readings_count,
        },
        "available_reports": [
            {"id": "org_list", "title": "Organisation Directory Report", "description": "Complete list of registered organisations and admin contacts"},
            {"id": "device_inventory", "title": "IoT Device Inventory Report", "description": "Platform-wide hardware and simulator device status"},
            {"id": "sensor_config", "title": "Sensor Configuration Audit", "description": "Enabled modules matrix per organisation"},
            {"id": "platform_alerts", "title": "Platform Security & Anomaly Audit", "description": "Historical anomaly and system alert logs"},
        ],
    }


# ---------------------------------------------------------------------------
# GET /super-admin/organisations/government
# — List all GOVERNMENT-owned organisations (for municipality association)
# ---------------------------------------------------------------------------
@router.get(
    "/organisations/government",
    response_model=List[GovernmentOrgItem],
    summary="List all GOVERNMENT-owned organisations (for municipality association)",
)
def list_government_organisations(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Return all GOVERNMENT-owned organisations for Super Admin or Municipality Admin to associate with a municipality."""
    gov_orgs = (
        db.query(Organisation)
        .filter(Organisation.ownership_type == Organisation.OWNERSHIP_GOVERNMENT)
        .order_by(Organisation.name.asc())
        .all()
    )
    loc_parts_fn = lambda o: ", ".join(p for p in [o.city, o.state] if p) or (o.location or "")
    return [
        GovernmentOrgItem(
            id=o.id,
            name=o.name,
            org_type=o.org_type,
            location=loc_parts_fn(o),
            is_active=o.is_active,
        )
        for o in gov_orgs
    ]


# ---------------------------------------------------------------------------
# GET /super-admin/organisations/{org_id}/municipality-associations
# — Retrieve associated government orgs for a municipality
# ---------------------------------------------------------------------------
@router.get(
    "/organisations/{org_id}/municipality-associations",
    response_model=MunicipalityAssociationResponse,
    summary="Get associated government organisations for a municipality",
)
def get_municipality_associations(
    org_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Return the list of associated GOVERNMENT org IDs stored in a municipality's sensor config."""
    if current_user.role == User.ROLE_ADMIN and current_user.organisation_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only view associations for your own municipality.",
        )

    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organisation '{org_id}' not found.")

    cfg = db.query(OrganisationSensorConfig).filter(OrganisationSensorConfig.organisation_id == org_id).first()
    assoc_ids: List[str] = []
    if cfg and cfg.sensor_configs:
        import json as _json
        try:
            stored = _json.loads(cfg.sensor_configs)
            assoc_ids = stored.get("_municipality_assoc", [])
            if not isinstance(assoc_ids, list):
                assoc_ids = []
        except Exception:
            assoc_ids = []

    return MunicipalityAssociationResponse(
        organisation_id=org_id,
        associated_gov_org_ids=assoc_ids,
        message="ok",
    )


# ---------------------------------------------------------------------------
# PUT /super-admin/organisations/{org_id}/municipality-associations
# — Update associated government orgs for a municipality
# ---------------------------------------------------------------------------
@router.put(
    "/organisations/{org_id}/municipality-associations",
    response_model=MunicipalityAssociationResponse,
    summary="Update associated government organisations for a municipality",
)
def update_municipality_associations(
    org_id: str,
    payload: MunicipalityAssociationRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Store the list of GOVERNMENT org IDs associated with a municipality.
    All provided org IDs must exist and have ownership_type = GOVERNMENT.
    """
    if current_user.role == User.ROLE_ADMIN and current_user.organisation_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only update associations for your own municipality.",
        )
    import json as _json

    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organisation '{org_id}' not found.")

    # Validate each provided org ID is a real GOVERNMENT org
    clean_ids: List[str] = []
    for gov_id in payload.associated_gov_org_ids:
        gov_id = gov_id.strip()
        if not gov_id:
            continue
        gov_org = db.query(Organisation).filter(Organisation.id == gov_id).first()
        if not gov_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organisation '{gov_id}' not found.",
            )
        if gov_org.ownership_type != Organisation.OWNERSHIP_GOVERNMENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organisation '{gov_id}' is not a GOVERNMENT-owned organisation.",
            )
        clean_ids.append(gov_id)

    # Persist in OrganisationSensorConfig.sensor_configs under key '_municipality_assoc'
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
    stored["_municipality_assoc"] = clean_ids
    cfg.sensor_configs = _json.dumps(stored)
    cfg.updated_at = _utcnow()
    db.commit()

    logger.info(
        "Municipality '%s' associations updated by SuperAdmin %s: %s",
        org_id, current_user.email, clean_ids,
    )
    return MunicipalityAssociationResponse(
        organisation_id=org_id,
        associated_gov_org_ids=clean_ids,
        message="Associations updated successfully.",
    )


# ---------------------------------------------------------------------------
# DELETE /super-admin/organisations/{organisation_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/organisations/{organisation_id}",
    summary="Deactivate an organisation (Super Admin)",
)
def super_admin_deactivate_org(
    organisation_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Deactivate an organisation and suspend its administrator accounts."""
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
    return {
        "status": "success",
        "message": f"Organisation {organisation_id} deactivated",
        "organisation_id": org.id,
        "is_active": False,
    }


# ---------------------------------------------------------------------------
# POST /super-admin/organisations/{organisation_id}/reactivate
# ---------------------------------------------------------------------------
@router.post(
    "/organisations/{organisation_id}/reactivate",
    summary="Reactivate an organisation (Super Admin)",
)
def super_admin_reactivate_org(
    organisation_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Reactivate an organisation and restore administrator accounts."""
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
    return {
        "status": "success",
        "message": f"Organisation {organisation_id} reactivated",
        "organisation_id": org.id,
        "is_active": True,
    }


class ClearAllDataPayload(BaseModel):
    confirmation_password: str = Field(..., description="Mandatory confirmation password for destructive action")
    confirmation: str = Field(..., description="Must match 'CLEAR ALL DATA' exactly")


# ---------------------------------------------------------------------------
# POST /super-admin/clear-all-data (Super Admin Clear All Data)
# ---------------------------------------------------------------------------
@router.post(
    "/clear-all-data",
    summary="Clear all platform data (Full Platform Reset)",
    description=(
        "Permanently deletes all organisations, organisation admin accounts, facility blocks, "
        "sensor configurations, IoT devices, telemetry, anomalies, and recommendations. "
        "Preserves ONLY the fixed Super Admin demo account. Requires SUPER_ADMIN role, "
        "mandatory confirmation password, and confirmation phrase 'CLEAR ALL DATA'."
    ),
)
def super_admin_clear_all_data(
    payload: ClearAllDataPayload,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Perform full platform reset.
    Requires mandatory confirmation password verification before execution.
    """
    # 0. Authoritative verification of confirmation password
    if not security.verify_confirmation_password(payload.confirmation_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation password",
        )

    phrase = (payload.confirmation or "").strip()
    if phrase != "CLEAR ALL DATA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation phrase must match 'CLEAR ALL DATA' exactly.",
        )

    # 1. Delete all messages
    del_messages = db.query(Message).delete(synchronize_session=False)

    # 1b. Delete all notification read states
    del_read_states = db.query(EventReadState).delete(synchronize_session=False)

    # 2. Delete all recommendations
    del_recs = db.query(AIRecommendation).delete(synchronize_session=False)

    # 3. Delete all anomalies
    del_anomalies = db.query(AnomalyRecord).delete(synchronize_session=False)

    # 4. Delete all sensor readings
    del_readings = db.query(SensorReading).delete(synchronize_session=False)

    # 5. Delete all IoT devices
    del_devices = db.query(IoTDevice).delete(synchronize_session=False)

    # 6. Delete all facility blocks
    del_blocks = db.query(FacilityBlock).delete(synchronize_session=False)

    # 7. Delete all sensor configs
    del_configs = db.query(OrganisationSensorConfig).delete(synchronize_session=False)

    # 8. Delete all Users EXCEPT the fixed Super Admin demo account
    del_users = (
        db.query(User)
        .filter(
            User.email != "superadmin@greennexa.com",
            User.id != "superadmin_demo",
        )
        .delete(synchronize_session=False)
    )

    # 9. Delete all Organisations
    del_orgs = db.query(Organisation).delete(synchronize_session=False)

    # 9b. Mark platform as destructively cleared so restarts do not recreate default organisations
    set_platform_data_cleared(db, True)

    db.commit()

    # 10. Perform safe SQLite VACUUM compaction to reclaim disk space
    safe_vacuum_sqlite(db_database.engine)

    # 11. Clear forecasting cache and reset all simulator state
    forecasting_service.clear_cache()
    simulator_instance.reset_all_simulator_state()

    logger.warning(
        "FULL PLATFORM RESET executed by SuperAdmin %s: orgs=%d users=%d readings=%d anomalies=%d recs=%d blocks=%d configs=%d devices=%d msgs=%d",
        current_user.email,
        del_orgs,
        del_users,
        del_readings,
        del_anomalies,
        del_recs,
        del_blocks,
        del_configs,
        del_devices,
        del_messages,
    )

    return {
        "message": "Platform data cleared successfully. Fixed Super Admin demo account preserved.",
        "preserved_user": "superadmin@greennexa.com",
        "deleted": {
            "organisations": del_orgs,
            "users": del_users,
            "sensor_readings": del_readings,
            "anomaly_records": del_anomalies,
            "recommendations": del_recs,
            "blocks": del_blocks,
            "configs": del_configs,
            "devices": del_devices,
            "messages": del_messages,
        },
    }


def format_storage_bytes(num_bytes: int) -> str:
    """Format bytes into clean, human-readable string."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.2f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


# ---------------------------------------------------------------------------
# GET /super-admin/storage (Super Admin Manage Storage)
# ---------------------------------------------------------------------------
@router.get(
    "/storage",
    response_model=StorageOverviewResponse,
    summary="Real database storage overview and organisation-wise breakdown",
    description=(
        "Returns real physical database file size, environment disk allocation, and "
        "deterministic organisation-attributed logical storage breakdown separated by Government and Private."
    ),
)
def get_platform_storage_overview(
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Retrieve authoritative storage metrics:
    - Real physical database file size
    - System disk allocation and usage
    - Organisation-wise logical storage estimate (Government vs Private)
    """
    # 1. Physical DB file size and path
    db_path = get_active_db_path(db_database.engine)
    physical_db_size = get_db_physical_size_bytes(db_database.engine)

    # 2. Disk allocation
    disk_total = None
    disk_available = None
    usage_pct = None
    try:
        drive_path = os.path.dirname(db_path) if (db_path and os.path.exists(db_path)) else os.getcwd()
        du = shutil.disk_usage(drive_path)
        disk_total = du.total
        disk_available = du.free
        if du.total > 0:
            usage_pct = round(((du.total - du.free) / du.total) * 100, 1)
    except Exception as e:
        logger.warning("Could not read disk usage: %s", e)

    # 3. Calculate organisation-wise logical data sizes
    orgs = db.query(Organisation).order_by(Organisation.name.asc()).all()

    org_items: List[OrganisationStorageItem] = []
    gov_logical_total = 0
    pvt_logical_total = 0

    for o in orgs:
        sr_count = db.query(func.count(SensorReading.id)).filter(SensorReading.organisation_id == o.id).scalar() or 0
        ar_count = db.query(func.count(AnomalyRecord.id)).filter(AnomalyRecord.organisation_id == o.id).scalar() or 0
        rec_count = db.query(func.count(AIRecommendation.id)).filter(AIRecommendation.organisation_id == o.id).scalar() or 0
        fb_count = db.query(func.count(FacilityBlock.id)).filter(FacilityBlock.organisation_id == o.id).scalar() or 0
        mw_count = db.query(func.count(MunicipalityWard.id)).filter(MunicipalityWard.municipality_id == o.id).scalar() or 0
        dev_count = db.query(func.count(IoTDevice.id)).filter(IoTDevice.organisation_id == o.id).scalar() or 0
        msg_count = db.query(func.count(Message.id)).filter(Message.organisation_id == o.id).scalar() or 0
        cfg_count = db.query(func.count(OrganisationSensorConfig.id)).filter(OrganisationSensorConfig.organisation_id == o.id).scalar() or 0

        # Detailed record text sizes for recommendations
        rec_rows = db.query(AIRecommendation).filter(AIRecommendation.organisation_id == o.id).all()
        rec_bytes = sum(len(r.summary or "") + len(r.recommended_actions or "") + len(r.possible_causes or "") + 128 for r in rec_rows)

        # Deterministic byte footprint:
        # Sensor reading: ~128 bytes/row
        # Anomaly record: ~256 bytes/row
        # Recommendation: text lengths + 128 bytes
        # Blocks / Wards: ~96 bytes/row
        # Devices: ~128 bytes/row
        # Messages: ~256 bytes/row
        # Sensor Configs: ~512 bytes/row
        org_bytes = (
            (sr_count * 128) +
            (ar_count * 256) +
            rec_bytes +
            (fb_count * 96) +
            (mw_count * 96) +
            (dev_count * 128) +
            (msg_count * 256) +
            (cfg_count * 512)
        )

        own_type = (o.ownership_type or "GOVERNMENT").upper()
        if own_type == Organisation.OWNERSHIP_PRIVATE:
            pvt_logical_total += org_bytes
        else:
            gov_logical_total += org_bytes

        org_items.append(
            OrganisationStorageItem(
                organisation_id=o.id,
                organisation_name=o.name,
                ownership_type=own_type,
                logical_storage_bytes=org_bytes,
                logical_storage_formatted=format_storage_bytes(org_bytes),
                percentage_of_total=0.0,  # Will be calculated after total is known
                readings_count=sr_count,
                anomalies_count=ar_count,
                recommendations_count=rec_count,
                blocks_count=fb_count,
                wards_count=mw_count,
                devices_count=dev_count,
                messages_count=msg_count,
            )
        )

    total_logical_bytes = gov_logical_total + pvt_logical_total

    # Update percentage of total
    for item in org_items:
        if total_logical_bytes > 0:
            item.percentage_of_total = round((item.logical_storage_bytes / total_logical_bytes) * 100, 2)
        else:
            item.percentage_of_total = 0.0

    return StorageOverviewResponse(
        database_size_bytes=physical_db_size,
        database_size_formatted=format_storage_bytes(physical_db_size),
        total_allocated_bytes=disk_total,
        total_allocated_formatted=format_storage_bytes(disk_total) if disk_total else None,
        available_bytes=disk_available,
        available_formatted=format_storage_bytes(disk_available) if disk_available else None,
        usage_percentage=usage_pct,
        government_total_logical_bytes=gov_logical_total,
        government_total_logical_formatted=format_storage_bytes(gov_logical_total),
        private_total_logical_bytes=pvt_logical_total,
        private_total_logical_formatted=format_storage_bytes(pvt_logical_total),
        total_logical_bytes=total_logical_bytes,
        total_logical_formatted=format_storage_bytes(total_logical_bytes),
        organisations=org_items,
        database_path=db_path or (
            f"postgresql://{db_database.engine.url.host or 'localhost'}:{db_database.engine.url.port or 5432}/{db_database.engine.url.database or ''}"
            if not str(db_database.engine.url).startswith("sqlite")
            else "sqlite"
        ),
        database_engine="PostgreSQL" if not str(db_database.engine.url).startswith("sqlite") else "SQLite",
    )


