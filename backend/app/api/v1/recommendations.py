"""
GreenNexa — AI Recommendation Engine API endpoints.

Routes:
  POST  /api/v1/recommendations/generate                 — generate + save for an anomaly
  POST  /api/v1/recommendations/generate/{organisation_id}— generate recommendations for an organisation
  POST  /api/v1/recommendations/preview                  — preview without saving
  GET   /api/v1/recommendations                          — list recommendations (filtered by org)
  GET   /api/v1/recommendations/{organisation_id}        — list recommendations for an organisation or get by ID
  PATCH /api/v1/recommendations/{recommendation_id}      — update recommendation status
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai import recommender
from app.core.dependencies import (
    get_current_user,
    require_roles,
    verify_organisation_access,
    verify_oversight_read_access,
)
from app.db.database import get_db
from app.db.models import AIRecommendation, AnomalyRecord, Organisation, User
from app.schemas.recommendation import (
    RecommendationGenerateRequest,
    RecommendationListResponse,
    RecommendationPreviewRequest,
    RecommendationPreviewResponse,
    RecommendationResponse,
    RecommendationStatusUpdateRequest,
)
from app.services.recommendation import recommendation_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendations", tags=["AI Recommendations"])


# ---------------------------------------------------------------------------
# POST /recommendations/generate
# ---------------------------------------------------------------------------
@router.post(
    "/generate",
    response_model=Optional[RecommendationResponse],
    summary="Generate and save a recommendation for an anomaly",
    description=(
        "Generates an AI recommendation for the given anomaly and persists it. "
        "Requires ADMIN or SUPER_ADMIN role."
    ),
)
def generate_recommendation(
    body: RecommendationGenerateRequest,
    organisation_id: Optional[str] = Query(None, description="Organisation ID (for access control)"),
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Generate and persist a recommendation for an existing anomaly record.
    Requires ADMIN or SUPER_ADMIN role and valid organisation access.
    """
    if organisation_id:
        verify_organisation_access(organisation_id, current_user)

    # Load anomaly
    anomaly = (
        db.query(AnomalyRecord)
        .filter(AnomalyRecord.id == body.anomaly_id)
        .first()
    )
    if anomaly is None:
        raise HTTPException(status_code=404, detail="Anomaly record not found.")

    # Organisation isolation for the target anomaly
    verify_organisation_access(anomaly.organisation_id, current_user)

    # Check if a recommendation already exists for this anomaly
    existing = (
        db.query(AIRecommendation)
        .filter(AIRecommendation.anomaly_id == body.anomaly_id)
        .first()
    )
    if existing:
        logger.info(
            "Recommendation already exists for anomaly_id=%s — returning existing.",
            body.anomaly_id,
        )
        return RecommendationResponse.from_orm_model(existing)

    # Generate
    try:
        rec = recommender.generate_and_save(db=db, anomaly=anomaly)
    except Exception as exc:
        logger.exception("Error generating recommendation: %s", exc)
        raise HTTPException(
            status_code=500, detail="Recommendation generation failed."
        ) from exc

    if rec is None:
        return None

    return RecommendationResponse.from_orm_model(rec)


# ---------------------------------------------------------------------------
# POST /recommendations/generate/{organisation_id}
# ---------------------------------------------------------------------------
@router.post(
    "/generate/{organisation_id}",
    summary="Generate recommendations for an organisation",
    description=(
        "Generates decision-support recommendations from available anomalies and forecasts "
        "for an organisation's enabled sensors. Requires ADMIN or SUPER_ADMIN role."
    ),
)
def generate_organisation_recommendations(
    organisation_id: str,
    sensor_type: Optional[str] = Query(None, description="Optional sensor metric filter"),
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Generate recommendations for an organisation's open anomalies and trends.
    """
    verify_organisation_access(organisation_id, current_user)

    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{organisation_id}' not found.",
        )

    try:
        recs = recommendation_service.generate_recommendations_for_organisation(
            db=db,
            organisation_id=organisation_id,
            sensor_type=sensor_type,
        )
        return {
            "organisation_id": organisation_id,
            "generated_count": len(recs),
            "recommendations": [RecommendationResponse.from_orm_model(r) for r in recs],
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Error generating organisation recommendations: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recommendation generation failed.",
        )


# ---------------------------------------------------------------------------
# POST /recommendations/preview  (no DB write)
# ---------------------------------------------------------------------------
@router.post(
    "/preview",
    response_model=RecommendationPreviewResponse,
    summary="Preview a recommendation without saving",
    description=(
        "Generate a recommendation preview using supplied data. "
        "Nothing is written to the database. Useful for testing and UI demonstrations."
    ),
)
def preview_recommendation(
    body: RecommendationPreviewRequest,
    current_user: User = Depends(get_current_user),
):
    """Preview a recommendation without persisting."""
    if body.organisation_id:
        verify_organisation_access(body.organisation_id, current_user)

    result = recommender.generate_without_saving(
        anomaly_severity=body.severity,
        metric=body.metric,
        current_value=body.current_value,
        expected_min=body.expected_min,
        expected_max=body.expected_max,
        history_values=body.history_values,
        unit=body.unit,
        organisation_id=body.organisation_id,
        facility_id=body.facility_id,
    )
    return RecommendationPreviewResponse(**result)


def _apply_recommendation_status_filter(query, status_val: Optional[str]):
    if not status_val:
        return query
    st = status_val.strip().upper()
    if st in ("OPEN", "ACTIVE"):
        return query.filter(AIRecommendation.status.in_(["ACTIVE", "OPEN"]))
    elif st in ("RESOLVED", "ACTIONED"):
        return query.filter(AIRecommendation.status.in_(["RESOLVED", "ACTIONED"]))
    elif st == "DISMISSED":
        return query.filter(AIRecommendation.status == "DISMISSED")
    elif st == "ACKNOWLEDGED":
        return query.filter(AIRecommendation.status == "ACKNOWLEDGED")
    elif st != "ALL":
        return query.filter(AIRecommendation.status == st)
    return query


# ---------------------------------------------------------------------------
# GET /recommendations
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=RecommendationListResponse,
    summary="List AI recommendations",
    description=(
        "Return AI recommendation records for the authenticated user's organisation. "
        "Optional filters: status, facility_id, severity, metric, data_sufficient."
    ),
)
def list_recommendations(
    organisation_id: Optional[str] = Query(None, description="Organisation ID (defaults to user's org)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: OPEN | ACTIVE | RESOLVED | DISMISSED | ALL"),
    facility_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH | CRITICAL"),
    metric: Optional[str] = Query(None),
    data_sufficient: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated recommendations, scoped strictly to organisation_id."""
    target_org_id = verify_oversight_read_access(organisation_id, current_user, db)

    query = db.query(AIRecommendation).filter(
        AIRecommendation.organisation_id == target_org_id
    )

    query = _apply_recommendation_status_filter(query, status_filter)

    if facility_id:
        query = query.filter(AIRecommendation.facility_id == facility_id)
    if severity:
        query = query.filter(AIRecommendation.severity == severity.upper())
    if metric:
        query = query.filter(AIRecommendation.metric == metric.lower())
    if data_sufficient is not None:
        query = query.filter(AIRecommendation.data_sufficient == data_sufficient)

    total = query.count()
    items = (
        query.order_by(AIRecommendation.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return RecommendationListResponse(
        total=total,
        items=[RecommendationResponse.from_orm_model(r) for r in items],
    )


# ---------------------------------------------------------------------------
# GET /recommendations/{organisation_id}
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}",
    summary="Get organisation recommendations or single recommendation record",
)
def get_organisation_recommendations_or_single(
    organisation_id: str,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: OPEN | ACTIVE | RESOLVED | DISMISSED | ALL"),
    sensor_type: Optional[str] = Query(None, description="Filter by sensor type"),
    priority: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH | CRITICAL"),
    metric: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve recommendations for an organisation, or get a single recommendation by ID.
    """
    # 1. Check if organisation_id is an existing Organisation
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if org:
        verify_oversight_read_access(organisation_id, current_user, db)
        query = db.query(AIRecommendation).filter(AIRecommendation.organisation_id == organisation_id)
        query = _apply_recommendation_status_filter(query, status_filter)

        filter_sensor = sensor_type or metric
        if filter_sensor:
            query = query.filter(AIRecommendation.metric == filter_sensor.lower())
        if priority:
            query = query.filter(AIRecommendation.priority == priority.upper())

        total = query.count()
        items = (
            query.order_by(AIRecommendation.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return RecommendationListResponse(
            total=total,
            items=[RecommendationResponse.from_orm_model(r) for r in items],
        )

    # 2. Fallback to single recommendation lookup
    rec = db.query(AIRecommendation).filter(AIRecommendation.id == organisation_id).first()
    if rec:
        verify_organisation_access(rec.organisation_id, current_user)
        return RecommendationResponse.from_orm_model(rec)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Organisation or Recommendation '{organisation_id}' not found.",
    )


# ---------------------------------------------------------------------------
# PATCH /recommendations/{recommendation_id}
# ---------------------------------------------------------------------------
@router.patch(
    "/{recommendation_id}",
    response_model=RecommendationResponse,
    summary="Update recommendation status",
    description="Update recommendation status (OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED, ACTIONED). Requires ADMIN or SUPER_ADMIN role.",
)
@router.patch(
    "/{recommendation_id}/status",
    response_model=RecommendationResponse,
    include_in_schema=False,
)
def update_recommendation_status(
    recommendation_id: str,
    body: RecommendationStatusUpdateRequest,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Update recommendation status.
    """
    rec = db.query(AIRecommendation).filter(AIRecommendation.id == recommendation_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{recommendation_id}' not found.",
        )

    verify_organisation_access(rec.organisation_id, current_user)

    try:
        updated = recommendation_service.update_recommendation_status(
            db=db,
            recommendation_id=recommendation_id,
            new_status=body.status,
        )
        return RecommendationResponse.from_orm_model(updated)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


# ---------------------------------------------------------------------------
# POST /recommendations/{recommendation_id}/action
# ---------------------------------------------------------------------------
@router.post(
    "/{recommendation_id}/action",
    response_model=RecommendationResponse,
    summary="Mark recommendation as actioned",
    description="Mark a recommendation as ACTIONED. Requires ADMIN or SUPER_ADMIN role.",
)
def action_recommendation_endpoint(
    recommendation_id: str,
    current_user: User = Depends(require_roles(User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Mark a recommendation as ACTIONED (convenience alias for PATCH status=ACTIONED)."""
    rec = db.query(AIRecommendation).filter(AIRecommendation.id == recommendation_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{recommendation_id}' not found.",
        )

    verify_organisation_access(rec.organisation_id, current_user)

    try:
        updated = recommendation_service.update_recommendation_status(
            db=db,
            recommendation_id=recommendation_id,
            new_status=AIRecommendation.STATUS_ACTIONED,
        )
        return RecommendationResponse.from_orm_model(updated)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
