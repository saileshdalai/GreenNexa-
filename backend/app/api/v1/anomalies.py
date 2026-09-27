"""
GreenNexa — Anomaly Detection API endpoints.

Routes:
  POST /api/v1/anomalies/detect                — run detection on a new reading
  POST /api/v1/anomalies/detect/{organisation_id} — run detection for an organisation
  POST /api/v1/anomalies/classify              — classify without saving (preview)
  GET  /api/v1/anomalies                       — list anomalies (filtered by org/severity)
  GET  /api/v1/anomalies/{organisation_id}      — list anomalies for an organisation or single record by ID
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai import anomaly_detector
from app.core.dependencies import (
    get_current_user,
    require_roles,
    verify_organisation_access,
    verify_oversight_read_access,
)
from app.db.database import get_db
from app.db.models import AnomalyRecord, Organisation, User
from app.schemas.anomaly import (
    AnomalyClassifyRequest,
    AnomalyClassifyResponse,
    AnomalyDetectRequest,
    AnomalyListResponse,
    AnomalyResponse,
    AnomalyStatusUpdateRequest,
)
from app.services.anomaly_detection import anomaly_detection_service
from app.services.priority_engine import PriorityEngineResponse, priority_engine_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/anomalies", tags=["Anomaly Detection"])


# ---------------------------------------------------------------------------
# GET /anomalies/priority
# ---------------------------------------------------------------------------
@router.get(
    "/priority",
    response_model=PriorityEngineResponse,
    summary="Get Priority Engine state and urgent anomalies",
    description="Returns Priority Engine state. Active ONLY when active_anomaly_count > 3.",
)
def get_priority_engine(
    organisation_id: Optional[str] = Query(None, description="Organisation ID (defaults to user's org)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_org_id = verify_organisation_access(organisation_id, current_user)
    return priority_engine_service.evaluate_organisation_priority(db, target_org_id)


# ---------------------------------------------------------------------------
# GET /anomalies/{organisation_id}/priority
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}/priority",
    response_model=PriorityEngineResponse,
    summary="Get Priority Engine state and urgent anomalies for organisation",
    description="Returns Priority Engine state. Active ONLY when active_anomaly_count > 3.",
)
def get_organisation_priority_engine(
    organisation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_org_id = verify_organisation_access(organisation_id, current_user)
    return priority_engine_service.evaluate_organisation_priority(db, target_org_id)


# ---------------------------------------------------------------------------
# POST /anomalies/detect
# ---------------------------------------------------------------------------
@router.post(
    "/detect",
    response_model=Optional[AnomalyResponse],
    summary="Detect anomaly for a new sensor reading",
    description=(
        "Runs statistical anomaly detection for the provided reading. "
        "Saves the result to the database if severity >= LOW. "
        "Requires ADMIN or SUPER_ADMIN role."
    ),
)
def detect_anomaly(
    body: AnomalyDetectRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Analyse a single sensor reading and detect anomalies.
    Requires ADMIN or SUPER_ADMIN role and valid organisation access.
    """
    target_org_id = verify_organisation_access(body.organisation_id, current_user)

    try:
        record = anomaly_detector.detect_and_save(
            db=db,
            organisation_id=target_org_id,
            facility_id=body.facility_id,
            metric=body.metric,
            sensor_type=body.sensor_type,
            value=body.value,
            unit=body.unit,
            timestamp=body.timestamp,
        )
    except Exception as exc:
        logger.exception("Error during anomaly detection: %s", exc)
        raise HTTPException(status_code=500, detail="Anomaly detection failed.") from exc

    if record is None:
        return None

    return AnomalyResponse.model_validate(record)


# ---------------------------------------------------------------------------
# POST /anomalies/detect/{organisation_id}
# ---------------------------------------------------------------------------
@router.post(
    "/detect/{organisation_id}",
    summary="Run anomaly detection for an organisation",
    description=(
        "Runs statistical anomaly detection across enabled sensors for an organisation. "
        "Requires ADMIN or SUPER_ADMIN role."
    ),
)
def detect_organisation_anomalies(
    organisation_id: str,
    sensor_type: Optional[str] = Query(None, description="Optional sensor metric filter"),
    lookback_days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Run anomaly detection for an organisation's enabled sensors.
    """
    verify_organisation_access(organisation_id, current_user)

    # Check org exists
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{organisation_id}' not found.",
        )

    try:
        res = anomaly_detection_service.detect_anomalies_for_organisation(
            db=db,
            organisation_id=organisation_id,
            sensor_type=sensor_type,
            lookback_days=lookback_days,
        )
        return res
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Error in detect_organisation_anomalies: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Anomaly detection failed.",
        )


# ---------------------------------------------------------------------------
# POST /anomalies/classify  (preview — no DB write)
# ---------------------------------------------------------------------------
@router.post(
    "/classify",
    response_model=AnomalyClassifyResponse,
    summary="Classify a value without saving (preview)",
    description=(
        "Classify a reading against provided historical values without writing "
        "to the database. Useful for testing and UI previews."
    ),
)
def classify_anomaly(
    body: AnomalyClassifyRequest,
    current_user: User = Depends(get_current_user),
):
    """Classify a reading without persisting anything."""
    result = anomaly_detector.classify_value(
        value=body.value,
        history_values=body.history_values,
        metric=body.metric,
        unit=body.unit,
    )
    return AnomalyClassifyResponse(**result)


# ---------------------------------------------------------------------------
# GET /anomalies
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=AnomalyListResponse,
    summary="List anomaly records",
    description=(
        "Return anomaly records for the authenticated user's organisation. "
        "Optional filters: facility_id, severity, status, metric."
    ),
)
def list_anomalies(
    organisation_id: Optional[str] = Query(None, description="Organisation ID (defaults to user's org)"),
    facility_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH | CRITICAL"),
    status: Optional[str] = Query(None, description="OPEN | ACKNOWLEDGED | RESOLVED"),
    metric: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated anomaly records, scoped strictly to organisation_id."""
    target_org_id = verify_oversight_read_access(organisation_id, current_user, db)

    query = db.query(AnomalyRecord).filter(
        AnomalyRecord.organisation_id == target_org_id
    )

    if facility_id:
        query = query.filter(AnomalyRecord.facility_id == facility_id)
    if severity:
        query = query.filter(AnomalyRecord.severity == severity.upper())
    if status:
        query = query.filter(AnomalyRecord.status == status.upper())
    if metric:
        query = query.filter(AnomalyRecord.metric == metric.lower())

    total = query.count()
    items = (
        query.order_by(AnomalyRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return AnomalyListResponse(
        total=total,
        items=[AnomalyResponse.model_validate(r) for r in items],
    )


# ---------------------------------------------------------------------------
# GET /anomalies/{organisation_id}
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}",
    summary="Get organisation anomalies or single anomaly record",
)
def get_organisation_anomalies_or_single(
    organisation_id: str,
    sensor_type: Optional[str] = Query(None, description="Filter by sensor type"),
    severity: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH | CRITICAL"),
    status: Optional[str] = Query(None, description="OPEN | ACKNOWLEDGED | RESOLVED"),
    metric: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve anomaly records for an organisation, or get a single anomaly by ID.
    """
    # 1. Check if organisation_id corresponds to an existing Organisation
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if org:
        verify_oversight_read_access(organisation_id, current_user, db)
        query = db.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == organisation_id)

        filter_sensor = sensor_type or metric
        if filter_sensor:
            query = query.filter(
                (AnomalyRecord.sensor_type == filter_sensor.lower())
                | (AnomalyRecord.metric == filter_sensor.lower())
            )
        if severity:
            query = query.filter(AnomalyRecord.severity == severity.upper())
        if status:
            query = query.filter(AnomalyRecord.status == status.upper())

        total = query.count()
        items = (
            query.order_by(AnomalyRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return AnomalyListResponse(
            total=total,
            items=[AnomalyResponse.model_validate(r) for r in items],
        )

    # 2. Fallback to single anomaly record lookup
    record = db.query(AnomalyRecord).filter(AnomalyRecord.id == organisation_id).first()
    if record:
        verify_organisation_access(record.organisation_id, current_user)
        return AnomalyResponse.model_validate(record)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Organisation or Anomaly record '{organisation_id}' not found.",
    )


# ---------------------------------------------------------------------------
# PATCH /anomalies/{anomaly_id} — Update Anomaly Lifecycle Status
# ---------------------------------------------------------------------------
@router.patch(
    "/{anomaly_id}",
    response_model=AnomalyResponse,
    summary="Update anomaly lifecycle status",
    description="Update anomaly status (OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED). Requires ADMIN or SUPER_ADMIN role.",
)
@router.patch(
    "/{anomaly_id}/status",
    response_model=AnomalyResponse,
    include_in_schema=False,
)
def update_anomaly_status(
    anomaly_id: str,
    body: AnomalyStatusUpdateRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Update anomaly status with lifecycle validation and duplicate prevention.
    """
    record = db.query(AnomalyRecord).filter(AnomalyRecord.id == anomaly_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly record '{anomaly_id}' not found.",
        )

    verify_organisation_access(record.organisation_id, current_user)

    try:
        updated = anomaly_detection_service.update_anomaly_status(
            db=db,
            anomaly_id=anomaly_id,
            new_status=body.status,
        )
        return AnomalyResponse.model_validate(updated)
    except ValueError as e:
        msg = str(e)
        if "already" in msg.lower() or "cannot" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=msg,
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=msg,
        )


# ---------------------------------------------------------------------------
# POST /anomalies/{anomaly_id}/acknowledge
# ---------------------------------------------------------------------------
@router.post(
    "/{anomaly_id}/acknowledge",
    response_model=AnomalyResponse,
    summary="Acknowledge anomaly",
    description="Acknowledge an active anomaly record. Requires ADMIN or SUPER_ADMIN role.",
)
def acknowledge_anomaly_endpoint(
    anomaly_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    return update_anomaly_status(
        anomaly_id=anomaly_id,
        body=AnomalyStatusUpdateRequest(status=AnomalyRecord.STATUS_ACKNOWLEDGED),
        current_user=current_user,
        db=db,
    )


# ---------------------------------------------------------------------------
# POST /anomalies/{anomaly_id}/resolve
# ---------------------------------------------------------------------------
@router.post(
    "/{anomaly_id}/resolve",
    response_model=AnomalyResponse,
    summary="Resolve anomaly",
    description="Resolve an active anomaly record. Requires ADMIN or SUPER_ADMIN role.",
)
def resolve_anomaly_endpoint(
    anomaly_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    return update_anomaly_status(
        anomaly_id=anomaly_id,
        body=AnomalyStatusUpdateRequest(status=AnomalyRecord.STATUS_RESOLVED),
        current_user=current_user,
        db=db,
    )


# ---------------------------------------------------------------------------
# POST /anomalies/{anomaly_id}/dismiss
# ---------------------------------------------------------------------------
@router.post(
    "/{anomaly_id}/dismiss",
    response_model=AnomalyResponse,
    summary="Dismiss anomaly",
    description="Dismiss an active anomaly record. Requires ADMIN or SUPER_ADMIN role.",
)
def dismiss_anomaly_endpoint(
    anomaly_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    return update_anomaly_status(
        anomaly_id=anomaly_id,
        body=AnomalyStatusUpdateRequest(status=AnomalyRecord.STATUS_DISMISSED),
        current_user=current_user,
        db=db,
    )

