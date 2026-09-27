"""
GreenNexa — Priority Engine Service.

Activation rule:
  active_anomaly_count >= 3

Therefore:
  0–2 active anomalies = INACTIVE
  3+ active anomalies = ACTIVE

When active:
  - Compares all ACTIVE anomalies (STATUS_OPEN, STATUS_ACKNOWLEDGED)
  - Ignores RESOLVED and DISMISSED anomalies
  - Identifies whether any anomaly truly requires high/urgent/immediate action
  - If a high-priority anomaly exists: shows ONLY the most important one
  - If 3+ active anomalies exist but none qualifies as high priority:
    shows exactly "No high-priority anomaly detected."
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    Organisation,
    OrganisationSensorConfig,
)
from app.services.anomaly_detection import anomaly_detection_service

logger = logging.getLogger(__name__)


class PriorityEngineItem(BaseModel):
    id: str
    priority_level: str  # "CRITICAL" | "HIGH" | "URGENT"
    priority_score: float
    organisation_id: str
    organisation_name: Optional[str] = None
    module: str
    block: str
    block_name: Optional[str] = None
    block_id: Optional[str] = None
    anomaly_name: str
    current_value: float
    unit: str
    baseline: float
    warning_threshold: float
    critical_threshold: float
    why_priority: str
    recommended_action: str
    recommendation_status: Optional[str] = None
    timestamp: str
    anomaly_status: str
    ml_risk_probability: Optional[float] = None
    ml_model_used: Optional[str] = None
    ml_risk_factors: Optional[dict] = None


class PriorityEngineResponse(BaseModel):
    is_active: bool
    active_anomaly_count: int
    active_count: int = 0
    threshold: int = 3
    message: str
    status_message: Optional[str] = None
    items: List[PriorityEngineItem] = []
    top_priority: Optional[PriorityEngineItem] = None
    optimal_score: Optional[int] = None


class PriorityEngineService:
    """Deterministic Priority Ranking and Triage Engine."""

    THRESHOLD: int = 3

    def get_priority_anomalies(
        self,
        db: Session,
        organisation_id: str,
    ) -> PriorityEngineResponse:
        return self.evaluate_organisation_priority(db, organisation_id)

    def evaluate_organisation_priority(
        self,
        db: Session,
        organisation_id: str,
    ) -> PriorityEngineResponse:
        """
        Evaluate active anomalies for the organisation.
        Activates when active_anomaly_count >= 3.
        """
        active_statuses = (AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED)

        # 1. Fetch only currently ACTIVE anomalies for this organisation (exclude RESOLVED and DISMISSED)
        active_anomalies = (
            db.query(AnomalyRecord)
            .filter(
                AnomalyRecord.organisation_id == organisation_id,
                AnomalyRecord.status.in_(active_statuses),
            )
            .order_by(AnomalyRecord.created_at.desc())
            .all()
        )

        active_count = len(active_anomalies)
        optimal_score = anomaly_detection_service.calculate_optimal_score(active_anomalies)

        # Inactive rule: 0–2 active anomalies (count < 3)
        if active_count < self.THRESHOLD:
            msg = f"Priority Engine is inactive ({active_count}/{self.THRESHOLD} active anomalies). Activates when >= {self.THRESHOLD} active anomalies."
            return PriorityEngineResponse(
                is_active=False,
                active_anomaly_count=active_count,
                active_count=active_count,
                threshold=self.THRESHOLD,
                message=msg,
                status_message=msg,
                items=[],
                top_priority=None,
                optimal_score=optimal_score,
            )

        # Active rule: 3 or more active anomalies
        # Load sensor config for baseline & threshold references
        cfg = (
            db.query(OrganisationSensorConfig)
            .filter(OrganisationSensorConfig.organisation_id == organisation_id)
            .first()
        )
        sensor_configs = cfg.sensor_configs_dict if cfg else {}

        # Look up organisation name
        org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
        org_name = org.name if org else organisation_id

        # Count per-block active occurrences to detect recurrence
        block_counts: dict[str, int] = {}
        for a in active_anomalies:
            b_key = a.facility_id or a.block_id or "Main"
            block_counts[b_key] = block_counts.get(b_key, 0) + 1

        now = datetime.now(timezone.utc)
        qualified_items: List[tuple[float, PriorityEngineItem]] = []

        for a in active_anomalies:
            s_type = (a.sensor_type or a.metric or "energy").lower().strip()
            s_cfg = sensor_configs.get(s_type, {})
            baseline = float(s_cfg.get("baseline", 100.0))
            warn_raw = float(s_cfg.get("warning_threshold", 15.0))
            crit_raw = float(s_cfg.get("critical_threshold", 30.0))
            unit = s_cfg.get("unit", "") or "units"

            if warn_raw > baseline and warn_raw > 100.0:
                warn_thresh = round(warn_raw, 2)
            else:
                warn_thresh = round(baseline * (1.0 + warn_raw / 100.0), 2)

            if crit_raw > baseline and crit_raw > 100.0:
                crit_thresh = round(crit_raw, 2)
            else:
                crit_thresh = round(baseline * (1.0 + crit_raw / 100.0), 2)

            val = float(a.value) if a.value is not None else baseline
            dev_pct = abs((val - baseline) / baseline * 100.0) if baseline > 0 else 0.0

            # Threshold breach evaluation
            is_critical_breach = val >= crit_thresh or (baseline > 0 and (baseline - val) >= (crit_thresh - baseline))
            is_warning_breach = val >= warn_thresh or (baseline > 0 and (baseline - val) >= (warn_thresh - baseline))

            sev = (a.severity or "HIGH").upper()

            # Linked recommendation action
            rec = (
                db.query(AIRecommendation)
                .filter(AIRecommendation.anomaly_id == a.id)
                .first()
            )
            has_urgent_rec = rec is not None and getattr(rec, "status", None) == AIRecommendation.STATUS_ACTIVE

            b_name = a.facility_id or a.block_id or "Facility"
            is_recurrent = block_counts.get(b_name, 0) > 1

            # Determine whether this anomaly truly qualifies as high priority / action required:
            # Low/Medium anomalies do NOT qualify unless there is a critical threshold breach or urgent escalation.
            qualifies = False
            if sev == "CRITICAL" or is_critical_breach:
                qualifies = True
            elif sev == "HIGH":
                qualifies = True
            elif is_warning_breach and (dev_pct >= 20.0 or is_recurrent or has_urgent_rec):
                qualifies = True

            if not qualifies:
                continue

            # Deterministic Explainable Scoring for ranking qualified items
            score = 0.0

            if sev == "CRITICAL":
                score += 100.0
            elif sev == "HIGH":
                score += 60.0
            elif sev == "MEDIUM":
                score += 30.0
            else:
                score += 10.0

            if is_critical_breach:
                score += 50.0
            elif is_warning_breach:
                score += 25.0

            score += min(40.0, dev_pct * 0.8)

            if is_recurrent:
                score += 15.0

            if a.created_at:
                created_dt = a.created_at
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                hours_open = max(0.0, (now - created_dt).total_seconds() / 3600.0)
                score += min(20.0, hours_open * 2.0)

            if a.status == AnomalyRecord.STATUS_OPEN:
                score += 10.0

            if has_urgent_rec:
                score += 10.0

            priority_level = "CRITICAL" if (sev == "CRITICAL" or is_critical_breach or score >= 140.0) else "HIGH"

            reasons = []
            if is_critical_breach:
                reasons.append(f"Critical threshold ({crit_thresh} {unit}) exceeded significantly (+{dev_pct:.1f}%)")
            elif is_warning_breach:
                reasons.append(f"Warning threshold ({warn_thresh} {unit}) breached (+{dev_pct:.1f}%)")
            else:
                reasons.append(f"Elevated deviation of +{dev_pct:.1f}% from baseline ({baseline} {unit})")

            if is_recurrent:
                reasons.append(f"recurrent anomaly cluster in {b_name} ({block_counts[b_name]} active events)")

            why_priority = f"{'; '.join(reasons)} requiring faster operational intervention."

            rec_action = (
                rec.summary
                if rec and rec.summary
                else f"Inspect {b_name} for abnormal {s_type} usage and verify sub-metering telemetry."
            )
            rec_status = rec.status if rec else None

            from app.services.priority_ml_service import priority_ml_service
            risk_eval = priority_ml_service.evaluate_escalation_risk(
                db=db,
                organisation_id=organisation_id,
                anomaly=a,
                baseline=baseline,
                warning_thresh=warn_thresh,
                critical_thresh=crit_thresh,
            )

            anom_name = getattr(a, "title", None) or getattr(a, "reason", None) or f"{s_type.capitalize()} Anomaly"

            item = PriorityEngineItem(
                id=a.id,
                priority_level=priority_level,
                priority_score=round(score, 1),
                organisation_id=organisation_id,
                organisation_name=org_name,
                module=s_type.capitalize(),
                block=b_name,
                block_name=b_name,
                block_id=a.block_id,
                anomaly_name=anom_name,
                current_value=round(val, 2),
                unit=unit,
                baseline=round(baseline, 2),
                warning_threshold=round(warn_thresh, 2),
                critical_threshold=round(crit_thresh, 2),
                why_priority=why_priority,
                recommended_action=rec_action,
                recommendation_status=rec_status,
                timestamp=a.created_at.isoformat() if a.created_at else now.isoformat(),
                anomaly_status=a.status,
                ml_risk_probability=risk_eval["ml_risk_probability"],
                ml_model_used=risk_eval["model_used"],
                ml_risk_factors=risk_eval["risk_factors"],
            )
            qualified_items.append((score, item))

        # If 3+ active anomalies exist but none qualifies as high priority:
        if not qualified_items:
            no_high_msg = "No high-priority anomaly detected."
            return PriorityEngineResponse(
                is_active=True,
                active_anomaly_count=active_count,
                active_count=active_count,
                threshold=self.THRESHOLD,
                message=no_high_msg,
                status_message=no_high_msg,
                items=[],
                top_priority=None,
                optimal_score=optimal_score,
            )

        # Sort descending by priority score and show ONLY the most important one
        qualified_items.sort(key=lambda x: x[0], reverse=True)
        top_item = qualified_items[0][1]

        active_msg = f"Priority Engine is ACTIVE ({active_count} active anomalies). Prioritizing top operational issue."
        return PriorityEngineResponse(
            is_active=True,
            active_anomaly_count=active_count,
            active_count=active_count,
            threshold=self.THRESHOLD,
            message=active_msg,
            status_message=active_msg,
            items=[top_item],
            top_priority=top_item,
            optimal_score=optimal_score,
        )


priority_engine_service = PriorityEngineService()
