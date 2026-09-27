"""
GreenNexa — AI Insight & Sustainability Executive Briefing Service.

Synthesizes telemetry, ML Isolation Forest anomaly scores, Ridge/RandomForest
forecast trajectories, upcoming breach risks, and open-data weather context
into clear, actionable executive summaries with transparent uncertainty hedging.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import AnomalyRecord, Organisation, OrganisationSensorConfig
from app.services.future_anomaly_service import future_anomaly_service
from app.services.geospatial_service import geospatial_service

logger = logging.getLogger(__name__)


class InsightService:
    """
    Generative AI and template-synthesis engine for executive facility intelligence.
    """

    CONFIDENCE_DISCLAIMER = (
        "Generated for decision-support using Machine Learning time-series models and facility telemetry. "
        "All projections and anomaly scores should be verified before irreversible operational interventions."
    )

    def generate_sustainability_briefing(
        self,
        db: Session,
        organisation_id: str,
    ) -> Dict[str, Any]:
        """
        Synthesizes an executive overview of campus sustainability and operational risk.
        """
        org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
        org_name = org.name if org else organisation_id

        # 1. Fetch active anomalies
        active_anomalies = (
            db.query(AnomalyRecord)
            .filter(
                AnomalyRecord.organisation_id == organisation_id,
                AnomalyRecord.status.in_((AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED)),
            )
            .order_by(AnomalyRecord.created_at.desc())
            .all()
        )

        critical_count = sum(1 for a in active_anomalies if a.severity == AnomalyRecord.SEVERITY_CRITICAL)
        high_count = sum(1 for a in active_anomalies if a.severity == AnomalyRecord.SEVERITY_HIGH)

        # 2. Evaluate future risks across primary sensors
        energy_risk = future_anomaly_service.evaluate_future_risk(db, organisation_id, "energy")
        water_risk = future_anomaly_service.evaluate_future_risk(db, organisation_id, "water")

        # 3. Geospatial context
        geo_ctx = geospatial_service.get_facility_context(organisation_id, facility_name=org_name)

        # 4. Formulate executive narrative
        key_findings = []
        action_priorities = []

        if critical_count > 0:
            key_findings.append(f"{critical_count} critical anomaly event(s) currently active requiring immediate triage.")
            action_priorities.append("Despatch maintenance engineers to investigate critical alert zones.")
        elif high_count > 0:
            key_findings.append(f"{high_count} high-severity anomaly event(s) identified by the unified ML detection pipeline.")
            action_priorities.append("Review sub-metering telemetry in affected facility blocks.")
        else:
            key_findings.append("Facility operations currently stable with zero critical anomaly alerts.")

        if energy_risk.get("projected_breach"):
            key_findings.append(f"Energy forecast projects a threshold breach within {energy_risk['estimated_time_to_breach_hours']} hours.")
            action_priorities.append("Pre-cool thermal zones or shed non-essential HVAC loads before peak tariff window.")
        else:
            key_findings.append(f"24h energy load forecast indicates {energy_risk['risk_level']} risk of threshold violation.")

        if water_risk.get("projected_breach"):
            key_findings.append(f"Water consumption forecast indicates continuous elevated draw (+{water_risk['peak_projected_value']} L).")
            action_priorities.append("Inspect secondary plumbing distribution loops for persistent leakage.")

        executive_summary = (
            f"Sustainability operations review for {org_name}. "
            f"Current campus status is {'URGENT' if critical_count > 0 else ('ATTENTION_REQUIRED' if high_count > 0 else 'OPTIMAL')}. "
            f"{' '.join(key_findings[:2])}"
        )

        return {
            "organisation_id": organisation_id,
            "organisation_name": org_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_status": "URGENT" if critical_count > 0 else ("ATTENTION_REQUIRED" if high_count > 0 else "OPTIMAL"),
            "executive_summary": executive_summary,
            "active_anomaly_summary": {
                "total_active": len(active_anomalies),
                "critical": critical_count,
                "high": high_count,
                "medium_or_low": len(active_anomalies) - critical_count - high_count,
            },
            "predictive_risks": {
                "energy": {
                    "risk_level": energy_risk.get("risk_level"),
                    "risk_score": energy_risk.get("risk_score"),
                    "projected_breach": energy_risk.get("projected_breach"),
                    "time_to_breach_hours": energy_risk.get("estimated_time_to_breach_hours"),
                },
                "water": {
                    "risk_level": water_risk.get("risk_level"),
                    "risk_score": water_risk.get("risk_score"),
                    "projected_breach": water_risk.get("projected_breach"),
                    "time_to_breach_hours": water_risk.get("estimated_time_to_breach_hours"),
                },
            },
            "environmental_context": geo_ctx.get("environmental_context"),
            "key_findings": key_findings,
            "recommended_priorities": action_priorities,
            "confidence_disclaimer": self.CONFIDENCE_DISCLAIMER,
        }


insight_service = InsightService()
