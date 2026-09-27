"""
GreenNexa — Notifications & Read State Management API Router.

Routes:
  GET  /api/v1/notifications/unread           — Get unread notification status for modules, blocks, and sections
  POST /api/v1/notifications/mark-read        — Mark specific or filtered anomalies as seen
  POST /api/v1/notifications/read/{anomaly_id} — Mark a single anomaly record as seen
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, verify_organisation_access
from app.db.database import get_db
from app.db.models import AnomalyRecord, EventReadState, FacilityBlock, Organisation, User, _utcnow
from app.schemas.notification import (
    MarkReadRequest,
    MarkReadResponse,
    UnreadNotificationsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notification Read State Management"])

SUPPORTED_MODULES = [
    "energy",
    "water",
    "waste",
    "air_quality",
    "traffic",
    "parking",
    "assets",
    "safety",
    "climate",
    "street_lighting",
    "roads",
    "parks",
    "sewage",
    "water_flow",
]

CANONICAL_MODULE_MAP = {
    "energy": "energy",
    "power": "energy",
    "electricity": "energy",
    "water": "water",
    "waste": "waste",
    "waste_level": "waste",
    "waste_weight": "waste",
    "air_quality": "air_quality",
    "air": "air_quality",
    "pm25": "air_quality",
    "pm10": "air_quality",
    "traffic": "traffic",
    "traffic_parking": "traffic",
    "parking": "parking",
    "assets": "assets",
    "asset": "assets",
    # The catalog's canonical asset sensor is `equipment_asset`; the navigation
    # module id is `assets`. Without this alias an `equipment_asset` anomaly lit
    # a key no UI reads, so the Municipal Assets red dot stayed dark.
    "equipment_asset": "assets",
    "equipment": "assets",
    "asset_health": "assets",
    "safety": "safety",
    "climate": "climate",
    "temperature": "climate",
    "humidity": "climate",
    "co2": "climate",
    "environment": "climate",
    "environmental": "climate",
    "street_lighting": "street_lighting",
    "street_light": "street_lighting",
    "roads": "roads",
    "road": "roads",
    "parks": "parks",
    "park": "parks",
    "sewage": "sewage",
    "sewage_level": "sewage",
    "drainage": "sewage",
    "water_flow": "water_flow",
    "waterflow": "water_flow",
    "water_level": "water_flow",
}


# ---------------------------------------------------------------------------
# GET /notifications/unread
# ---------------------------------------------------------------------------
@router.get(
    "/unread",
    response_model=UnreadNotificationsResponse,
    summary="Get unread notifications status",
    description=(
        "Retrieves current unread state for the authenticated user and organisation. "
        "Returns module-level and block-level red dot indicators strictly isolated per organisation."
    ),
)
def get_unread_notifications(
    organisation_id: Optional[str] = Query(None, description="Optional org ID filter (SUPER_ADMIN only)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Query active unseen anomalies for current user's organisation.
    """
    target_org_id = current_user.organisation_id
    if current_user.role == User.ROLE_SUPER_ADMIN:
        if organisation_id and organisation_id.strip():
            target_org_id = organisation_id.strip()

    if not target_org_id:
        return UnreadNotificationsResponse(
            has_unread=False,
            total_unread=0,
            modules={m: False for m in SUPPORTED_MODULES},
            blocks={},
            wards={},
            module_blocks={},
            sections={"anomalies": False, "recommendations": False},
            unseen_anomaly_ids=[],
        )

    # 1. Fetch all active/open anomalies for this organisation
    anomalies = (
        db.query(AnomalyRecord)
        .filter(
            AnomalyRecord.organisation_id == target_org_id,
            AnomalyRecord.status.in_([AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED]),
        )
        .all()
    )

    if not anomalies:
        return UnreadNotificationsResponse(
            has_unread=False,
            total_unread=0,
            modules={m: False for m in SUPPORTED_MODULES},
            blocks={},
            wards={},
            module_blocks={},
            sections={"anomalies": False, "recommendations": False},
            unseen_anomaly_ids=[],
        )

    # 2. Fetch read event IDs for current user in this organisation
    read_event_rows = (
        db.query(EventReadState.event_id)
        .filter(
            EventReadState.user_id == current_user.id,
            EventReadState.organisation_id == target_org_id,
            EventReadState.event_type == "anomaly",
        )
        .all()
    )
    read_event_ids = {r[0] for r in read_event_rows}

    # 3. Identify unseen anomalies (neither directly seen nor marked in EventReadState)
    unseen_anomalies: List[AnomalyRecord] = [
        a for a in anomalies if a.id not in read_event_ids and not getattr(a, "is_seen", False)
    ]

    # Pre-fetch organisation facility blocks to map between block_id and block_name
    facility_blocks = db.query(FacilityBlock).filter(FacilityBlock.organisation_id == target_org_id).all()
    block_id_to_name = {fb.block_id: fb.block_name for fb in facility_blocks if fb.block_id and fb.block_name}
    block_name_to_id = {fb.block_name: fb.block_id for fb in facility_blocks if fb.block_id and fb.block_name}

    modules_unread: Dict[str, bool] = {m: False for m in SUPPORTED_MODULES}
    blocks_unread: Dict[str, bool] = {}
    wards_unread: Dict[str, bool] = {}
    module_blocks_unread: Dict[str, Dict[str, bool]] = {m: {} for m in SUPPORTED_MODULES}
    unseen_ids: List[str] = []

    for anom in unseen_anomalies:
        unseen_ids.append(anom.id)
        m_raw = (anom.metric or anom.sensor_type or "").lower().strip()
        m_canonical = CANONICAL_MODULE_MAP.get(m_raw, m_raw)

        if m_raw:
            modules_unread[m_raw] = True
        if m_canonical:
            modules_unread[m_canonical] = True

        # Ward-level red dots for municipality civic anomalies
        if anom.ward_id and str(anom.ward_id).strip():
            wards_unread[str(anom.ward_id).strip()] = True

        # Collect all valid block keys for this anomaly
        b_candidates = set()
        if anom.block_id and anom.block_id.strip():
            b_candidates.add(anom.block_id.strip())
        if anom.facility_id and anom.facility_id.strip():
            b_candidates.add(anom.facility_id.strip())

        extra_b = set()
        for b in b_candidates:
            if b in block_id_to_name:
                extra_b.add(block_id_to_name[b])
            if b in block_name_to_id:
                extra_b.add(block_name_to_id[b])
        b_candidates.update(extra_b)

        for b_id in b_candidates:
            blocks_unread[b_id] = True
            for m_key in {m_canonical, m_raw}:
                if m_key:
                    if m_key not in module_blocks_unread:
                        module_blocks_unread[m_key] = {}
                    module_blocks_unread[m_key][b_id] = True

    has_unread = len(unseen_anomalies) > 0

    return UnreadNotificationsResponse(
        has_unread=has_unread,
        total_unread=len(unseen_anomalies),
        modules=modules_unread,
        blocks=blocks_unread,
        wards=wards_unread,
        module_blocks=module_blocks_unread,
        sections={"anomalies": has_unread, "recommendations": False},
        unseen_anomaly_ids=unseen_ids,
    )


# ---------------------------------------------------------------------------
# POST /notifications/mark-read
# ---------------------------------------------------------------------------
@router.post(
    "/mark-read",
    response_model=MarkReadResponse,
    summary="Mark anomalies / events as seen",
    description="Marks specified or filtered unseen events as viewed by the authenticated Admin user.",
)
def mark_notifications_read(
    body: MarkReadRequest,
    organisation_id: Optional[str] = Query(None, description="Optional target organisation ID filter (SUPER_ADMIN)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Record persistent read state for operational anomalies.
    """
    target_org_id = current_user.organisation_id
    if current_user.role == User.ROLE_SUPER_ADMIN:
        if organisation_id and organisation_id.strip():
            target_org_id = organisation_id.strip()
        elif getattr(body, "organisation_id", None) and body.organisation_id.strip():
            target_org_id = body.organisation_id.strip()
        elif not target_org_id:
            first_org = db.query(Organisation.id).first()
            target_org_id = first_org[0] if first_org else "ORG-TEST-A"
    elif not target_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organisation.",
        )

    query = db.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == target_org_id)

    # Pre-fetch block mappings
    facility_blocks = db.query(FacilityBlock).filter(FacilityBlock.organisation_id == target_org_id).all()
    b_id_map = {fb.block_id: fb.block_name for fb in facility_blocks if fb.block_id and fb.block_name}
    b_name_map = {fb.block_name: fb.block_id for fb in facility_blocks if fb.block_id and fb.block_name}

    if body.anomaly_ids:
        query = query.filter(AnomalyRecord.id.in_(body.anomaly_ids))
    elif body.metric and body.block_id:
        m_clean = body.metric.lower().strip()
        m_canon = CANONICAL_MODULE_MAP.get(m_clean, m_clean)
        metric_variants = {m_clean, m_canon}
        for k, v in CANONICAL_MODULE_MAP.items():
            if v == m_canon:
                metric_variants.add(k)

        b_clean = body.block_id.strip()
        block_variants = {b_clean}
        if b_clean in b_id_map:
            block_variants.add(b_id_map[b_clean])
        if b_clean in b_name_map:
            block_variants.add(b_name_map[b_clean])

        query = query.filter(
            (func.lower(AnomalyRecord.metric).in_(metric_variants)) | (func.lower(AnomalyRecord.sensor_type).in_(metric_variants)),
            (AnomalyRecord.block_id.in_(block_variants)) | (AnomalyRecord.facility_id.in_(block_variants)),
        )
    elif body.metric:
        m_clean = body.metric.lower().strip()
        m_canon = CANONICAL_MODULE_MAP.get(m_clean, m_clean)
        metric_variants = {m_clean, m_canon}
        for k, v in CANONICAL_MODULE_MAP.items():
            if v == m_canon:
                metric_variants.add(k)

        query = query.filter(
            (func.lower(AnomalyRecord.metric).in_(metric_variants)) | (func.lower(AnomalyRecord.sensor_type).in_(metric_variants)),
        )
    elif body.block_id:
        b_clean = body.block_id.strip()
        block_variants = {b_clean}
        if b_clean in b_id_map:
            block_variants.add(b_id_map[b_clean])
        if b_clean in b_name_map:
            block_variants.add(b_name_map[b_clean])

        query = query.filter(
            (AnomalyRecord.block_id.in_(block_variants)) | (AnomalyRecord.facility_id.in_(block_variants))
        )
    elif body.ward_id:
        w_clean = body.ward_id.strip()
        query = query.filter(AnomalyRecord.ward_id == w_clean)
    elif body.all_unseen or body.mark_all:
        # Match all active anomalies
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide anomaly_ids, metric, block_id, ward_id, or all_unseen=True.",
        )

    matched_anomalies = query.all()
    if not matched_anomalies:
        return MarkReadResponse(status="success", marked_count=0, message="No matching anomalies found.")

    # Check which ones are already read
    matched_ids = [a.id for a in matched_anomalies]
    existing_read = (
        db.query(EventReadState.event_id)
        .filter(
            EventReadState.user_id == current_user.id,
            EventReadState.event_id.in_(matched_ids),
        )
        .all()
    )
    already_read_ids = {r[0] for r in existing_read}

    now_dt = _utcnow()
    marked_count = 0

    for anom in matched_anomalies:
        if anom.id not in already_read_ids:
            read_record = EventReadState(
                user_id=current_user.id,
                organisation_id=target_org_id,
                event_type="anomaly",
                event_id=anom.id,
                metric=(anom.metric or anom.sensor_type or "").lower().strip(),
                block_id=anom.block_id,
                read_at=now_dt,
            )
            db.add(read_record)

            anom.is_seen = True
            anom.seen_at = now_dt
            anom.seen_by = current_user.id
            marked_count += 1

    db.commit()
    logger.info("Marked %d anomalies as seen for user %s org %s", marked_count, current_user.email, target_org_id)

    return MarkReadResponse(
        status="success",
        marked_count=marked_count,
        message=f"{marked_count} events marked as seen successfully.",
    )


# ---------------------------------------------------------------------------
# POST /notifications/read/{anomaly_id}
# ---------------------------------------------------------------------------
@router.post(
    "/read/{anomaly_id}",
    response_model=MarkReadResponse,
    summary="Mark single anomaly as read",
)
def mark_single_anomaly_read(
    anomaly_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a specific anomaly record as seen by the current Admin."""
    record = db.query(AnomalyRecord).filter(AnomalyRecord.id == anomaly_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly '{anomaly_id}' not found.",
        )
    if current_user.role != User.ROLE_SUPER_ADMIN:
        if record.organisation_id != current_user.organisation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anomaly '{anomaly_id}' not found for your organisation.",
            )

    return mark_notifications_read(
        body=MarkReadRequest(anomaly_ids=[anomaly_id]),
        current_user=current_user,
        db=db,
    )
