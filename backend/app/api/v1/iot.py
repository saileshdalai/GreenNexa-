"""
GreenNexa — IoT Device Management & Sensor Data Ingestion Router.

Routes:
  POST  /api/v1/iot/devices                   — Register new IoT device (SUPER_ADMIN / org ADMIN)
  GET   /api/v1/iot/devices                   — List IoT devices
  GET   /api/v1/iot/devices/{device_id}       — Get IoT device profile
  PATCH /api/v1/iot/devices/{device_id}/status — Activate or deactivate IoT device
  POST  /api/v1/iot/sensor-data              — Ingest sensor data payload (Device X-Device-ID / X-API-Key auth)
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core import security
from app.core.dependencies import get_current_user, require_roles, verify_organisation_access
from app.db.database import get_db
from app.db.models import (
    IoTDevice,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
)
from app.schemas.iot import (
    IoTDeviceListResponse,
    IoTDeviceRegisterRequest,
    IoTDeviceRegisterResponse,
    IoTDeviceResponse,
    IoTDeviceStatusUpdate,
    IoTSensorDataIngestPayload,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/iot", tags=["IoT Ingestion & Device Management"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Device Authentication Helper (Header-based: X-Device-ID + X-API-Key)
# ---------------------------------------------------------------------------
def _authenticate_iot_device(
    request: Request,
    db: Session,
) -> tuple[IoTDevice, OrganisationSensorConfig]:
    """
    Authenticate an IoT device using X-Device-ID and X-API-Key HTTP headers.
    Validates device exists, device is active, organisation is active,
    and organisation configuration data_source == 'iot'.
    """
    device_id_hdr = request.headers.get("X-Device-ID") or request.headers.get("x-device-id")
    api_key_hdr = request.headers.get("X-API-Key") or request.headers.get("x-api-key")

    if not device_id_hdr or not api_key_hdr:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing device authentication headers (X-Device-ID and X-API-Key required).",
        )

    clean_dev_id = device_id_hdr.strip()
    clean_api_key = api_key_hdr.strip()

    device = db.query(IoTDevice).filter_by(device_id=clean_dev_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials.",
        )

    if not security.verify_password(clean_api_key, device.api_key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials.",
        )

    if not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device is inactive.",
        )

    org = db.query(Organisation).filter_by(id=device.organisation_id).first()
    if not org or not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisation is inactive.",
        )

    config = db.query(OrganisationSensorConfig).filter_by(organisation_id=device.organisation_id).first()
    if not config or not config.is_active or config.data_source != OrganisationSensorConfig.DATA_SOURCE_IOT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organisation is not configured for IoT data.",
        )

    return device, config


# ---------------------------------------------------------------------------
# Ingestion Route: POST /iot/sensor-data
# ---------------------------------------------------------------------------
@router.post(
    "/sensor-data",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest real sensor / IoT data payload",
    description=(
        "Endpoint for IoT hardware devices (e.g. ESP32 / Wokwi) to send sensor readings.\n\n"
        "**Authentication:** Requires `X-Device-ID` and `X-API-Key` HTTP headers.\n"
        "**Constraint:** Accepted ONLY when organisation sensor config `data_source = 'iot'`."
    ),
)
def ingest_sensor_data(
    payload: IoTSensorDataIngestPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    # 1. Authenticate Device & Validate Data Source Mode
    device, config = _authenticate_iot_device(request, db)

    # 2. Prevent Device ID Spoofing between Header and Payload
    if payload.device_id.strip() != device.device_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header X-Device-ID does not match payload device_id.",
        )

    # 3. Validate Sensor Types & Enabled Configurations
    enabled_sensors = config.enabled_sensors_list
    for reading in payload.readings:
        st = reading.sensor_type
        if st not in OrganisationSensorConfig.ALLOWED_SENSOR_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported sensor type '{st}'. Allowed types: {sorted(list(OrganisationSensorConfig.ALLOWED_SENSOR_TYPES))}",
            )
        if st not in enabled_sensors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Sensor type '{st}' is not enabled for organisation '{device.organisation_id}'.",
            )

    # 4. Ingestion timestamp
    ts = payload.timestamp or _utcnow()
    ingested_count = 0

    # 5. Insert Sensor Readings with Duplicate Protection
    added_readings = []
    for reading in payload.readings:
        # Check duplicate idempotency
        duplicate = db.query(SensorReading).filter_by(
            organisation_id=device.organisation_id,
            device_id=device.device_id,
            sensor_type=reading.sensor_type,
            timestamp=ts,
        ).first()

        if not duplicate:
            sr = SensorReading(
                organisation_id=device.organisation_id,
                device_id=device.device_id,
                sensor_type=reading.sensor_type,
                value=round(reading.value, 2),
                unit=reading.unit,
                source=OrganisationSensorConfig.DATA_SOURCE_IOT,
                timestamp=ts,
                created_at=_utcnow(),
            )
            db.add(sr)
            added_readings.append(sr)
            ingested_count += 1

    # 6. Update Device Last Seen Timestamp
    device.last_seen_at = _utcnow()
    db.commit()

    # 7. Real-Time Anomaly & ML Detection Pipeline (Safe & Non-blocking)
    try:
        from app.services.anomaly_detection import anomaly_detection_service
        for sr in added_readings:
            anomaly_detection_service.process_single_reading(db=db, reading=sr, config=config)
    except Exception as anom_err:
        logger.warning("Post-ingestion anomaly check failed gracefully: %s", anom_err)

    logger.info(
        "Ingested %d IoT readings from device=%s for org=%s",
        ingested_count,
        device.device_id,
        device.organisation_id,
    )

    return {
        "status": "success",
        "device_id": device.device_id,
        "organisation_id": device.organisation_id,
        "ingested_count": ingested_count,
        "timestamp": ts.isoformat(),
    }


# ---------------------------------------------------------------------------
# Device Management Routes (User Bearer Token Authenticated)
# ---------------------------------------------------------------------------
@router.post(
    "/devices",
    response_model=IoTDeviceRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new IoT device",
    description="Registers an IoT device for an organisation and issues a plaintext API key (shown ONCE).",
)
def register_device(
    body: IoTDeviceRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # RBAC: Only SUPER_ADMIN and ADMIN allowed
    if current_user.role not in (User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Insufficient role permissions for device registration.",
        )

    # Org Isolation: ADMIN can register devices ONLY for their own organisation
    if current_user.role == User.ROLE_ADMIN and body.organisation_id != current_user.organisation_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only register devices for your own organisation.",
        )

    # Check organisation exists
    org = db.query(Organisation).filter_by(id=body.organisation_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation with ID '{body.organisation_id}' not found.",
        )

    # Check duplicate device_id
    existing = db.query(IoTDevice).filter_by(device_id=body.device_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device ID '{body.device_id}' is already registered.",
        )

    # Generate plaintext API key and store secure PBKDF2 hash
    raw_api_key = f"iot_key_{secrets.token_urlsafe(24)}"
    api_key_hash = security.hash_password(raw_api_key)

    device = IoTDevice(
        device_id=body.device_id,
        organisation_id=body.organisation_id,
        device_name=body.device_name,
        device_type=body.device_type,
        api_key_hash=api_key_hash,
        is_active=True,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    logger.info(
        "Registered IoT device=%s org=%s by user=%s",
        device.device_id,
        device.organisation_id,
        current_user.email,
    )

    return IoTDeviceRegisterResponse(
        device_id=device.device_id,
        organisation_id=device.organisation_id,
        device_name=device.device_name,
        device_type=device.device_type,
        api_key=raw_api_key,
        is_active=device.is_active,
        created_at=device.created_at,
    )


@router.get(
    "/devices",
    response_model=IoTDeviceListResponse,
    summary="List IoT devices",
    description="Lists IoT devices. SUPER_ADMIN views all; ADMIN and VIEWER view own org devices.",
)
def list_devices(
    organisation_id: Optional[str] = Query(None, description="Optional organisation ID filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(IoTDevice)

    if current_user.role == User.ROLE_SUPER_ADMIN:
        if organisation_id:
            query = query.filter(IoTDevice.organisation_id == organisation_id)
    else:
        # ADMIN & VIEWER restricted to own organisation
        target_org = current_user.organisation_id
        if organisation_id and organisation_id != target_org:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view devices for your own organisation.",
            )
        query = query.filter(IoTDevice.organisation_id == target_org)

    devices = query.order_by(IoTDevice.created_at.desc()).all()
    return IoTDeviceListResponse(total=len(devices), items=devices)


@router.get(
    "/devices/{device_id}",
    response_model=IoTDeviceResponse,
    summary="Get IoT device details",
    description="Gets profile details of a single IoT device.",
)
def get_device_details(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = db.query(IoTDevice).filter_by(device_id=device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IoT Device '{device_id}' not found.",
        )

    verify_organisation_access(device.organisation_id, current_user)
    return device


@router.patch(
    "/devices/{device_id}/status",
    response_model=IoTDeviceResponse,
    summary="Activate or deactivate IoT device",
    description="Updates operational active status of an IoT device.",
)
def update_device_status(
    device_id: str,
    body: IoTDeviceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only SUPER_ADMIN and ADMIN allowed
    if current_user.role not in (User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Insufficient role permissions to modify device status.",
        )

    device = db.query(IoTDevice).filter_by(device_id=device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IoT Device '{device_id}' not found.",
        )

    verify_organisation_access(device.organisation_id, current_user)

    device.is_active = body.is_active
    device.updated_at = _utcnow()
    db.commit()
    db.refresh(device)

    logger.info("Updated IoT device=%s status is_active=%s by user=%s", device_id, body.is_active, current_user.email)
    return device
