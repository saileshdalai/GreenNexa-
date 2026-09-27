"""
GreenNexa AI Assistant — Controlled Data Retrieval & Tools Layer.

Enforces strict tenant isolation and role-based data boundaries.
Only permitted queries execute against the GreenNexa database.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    IoTDevice,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
)
from app.services.forecasting import forecasting_service

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GreenNexaDataTools:
    """
    Controlled tool execution layer for GreenNexa operational queries.
    """

    @staticmethod
    def get_current_metric(
        db: Session,
        organisation_id: str,
        metric: str,
        block_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch current telemetry and baseline for a given metric and optional block."""
        clean_metric = metric.lower().strip()
        query = (
            db.query(SensorReading)
            .filter(
                SensorReading.organisation_id == organisation_id,
                SensorReading.sensor_type == clean_metric,
            )
        )
        if block_id:
            query = query.filter(
                (SensorReading.block_id == block_id) | (SensorReading.facility_id == block_id)
            )

        latest_reading = query.order_by(SensorReading.timestamp.desc()).first()

        # Config & baseline
        config = db.query(OrganisationSensorConfig).filter_by(organisation_id=organisation_id).first()
        sensor_configs = config.sensor_configs_dict if config else {}
        metric_cfg = sensor_configs.get(clean_metric, {})

        baseline = metric_cfg.get("baseline", 100.0)
        warning_pct = metric_cfg.get("warning_threshold", 15.0)
        critical_pct = metric_cfg.get("critical_threshold", 30.0)
        unit = metric_cfg.get("unit", latest_reading.unit if latest_reading else "")

        if not latest_reading:
            return {
                "available": False,
                "metric": clean_metric,
                "block_id": block_id,
                "baseline": baseline,
                "unit": unit,
                "message": f"No recent telemetry recorded for {clean_metric}" + (f" in block {block_id}" if block_id else "") + ".",
            }

        val = latest_reading.value
        diff = val - baseline
        pct_diff = ((val - baseline) / baseline * 100.0) if baseline > 0 else 0.0

        return {
            "available": True,
            "metric": clean_metric,
            "block_id": latest_reading.block_id or latest_reading.facility_id,
            "value": round(val, 2),
            "baseline": round(baseline, 2),
            "diff_from_baseline": round(diff, 2),
            "pct_diff_from_baseline": round(pct_diff, 1),
            "unit": unit or latest_reading.unit,
            "is_anomaly": latest_reading.is_anomaly,
            "severity": latest_reading.anomaly_severity,
            "timestamp": latest_reading.timestamp.isoformat() if latest_reading.timestamp else None,
            "warning_threshold_pct": warning_pct,
            "critical_threshold_pct": critical_pct,
        }

    @staticmethod
    def get_block_comparison(
        db: Session,
        organisation_id: str,
        metric: str,
    ) -> Dict[str, Any]:
        """Rank facility blocks by metric consumption/reading to identify highest/lowest blocks."""
        clean_metric = metric.lower().strip()
        blocks = (
            db.query(FacilityBlock)
            .filter(FacilityBlock.organisation_id == organisation_id, FacilityBlock.is_active.is_(True))
            .all()
        )

        results_map: Dict[str, Dict[str, Any]] = {}
        for b in blocks:
            latest = (
                db.query(SensorReading)
                .filter(
                    SensorReading.organisation_id == organisation_id,
                    SensorReading.sensor_type == clean_metric,
                    (SensorReading.block_id == b.block_id)
                    | (SensorReading.facility_id == b.block_name)
                    | (SensorReading.block_id == b.block_name)
                    | (SensorReading.facility_id == b.block_id),
                )
                .order_by(SensorReading.timestamp.desc())
                .first()
            )
            if latest:
                results_map[b.block_name] = {
                    "block_id": b.block_id,
                    "block_name": b.block_name,
                    "value": round(latest.value, 2),
                    "unit": latest.unit or "",
                    "is_anomaly": latest.is_anomaly,
                }

        # Also search for distinct block_id / facility_id from SensorReading table directly
        readings = (
            db.query(SensorReading)
            .filter(
                SensorReading.organisation_id == organisation_id,
                SensorReading.sensor_type == clean_metric,
            )
            .order_by(SensorReading.timestamp.desc())
            .limit(100)
            .all()
        )

        for r in readings:
            b_label = r.facility_id or r.block_id or "Main Building"
            if b_label not in results_map:
                results_map[b_label] = {
                    "block_id": r.block_id or b_label,
                    "block_name": b_label,
                    "value": round(r.value, 2),
                    "unit": r.unit or "",
                    "is_anomaly": r.is_anomaly,
                }

        results = list(results_map.values())
        results.sort(key=lambda x: x["value"], reverse=True)

        highest = results[0] if results and results[0]["value"] > 0 else (results[0] if results else None)
        lowest = results[-1] if results else None

        return {
            "metric": clean_metric,
            "blocks": results,
            "highest_block": highest,
            "lowest_block": lowest,
            "total_blocks": len(results),
        }

    @staticmethod
    def get_active_anomalies(
        db: Session,
        organisation_id: str,
        metric: Optional[str] = None,
        block_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch current OPEN or ACKNOWLEDGED anomalies for an organisation."""
        query = db.query(AnomalyRecord).filter(
            AnomalyRecord.organisation_id == organisation_id,
            AnomalyRecord.status.in_([AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED]),
        )
        if metric:
            query = query.filter(AnomalyRecord.metric == metric.lower().strip())
        if block_id:
            query = query.filter(
                (AnomalyRecord.block_id == block_id) | (AnomalyRecord.facility_id == block_id)
            )

        records = query.order_by(AnomalyRecord.timestamp.desc()).all()

        crit_count = sum(1 for a in records if a.severity == AnomalyRecord.SEVERITY_CRITICAL)
        high_count = sum(1 for a in records if a.severity == AnomalyRecord.SEVERITY_HIGH)

        items = []
        for a in records:
            items.append({
                "id": a.id,
                "metric": a.metric,
                "block": a.facility_id or a.block_id or "Facility",
                "value": round(a.value, 2),
                "expected_min": round(a.expected_min, 2) if a.expected_min is not None else None,
                "expected_max": round(a.expected_max, 2) if a.expected_max is not None else None,
                "severity": a.severity,
                "reason": a.reason,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            })

        return {
            "total_active": len(records),
            "critical_count": crit_count,
            "high_count": high_count,
            "anomalies": items,
        }

    @staticmethod
    def get_recommendations(
        db: Session,
        organisation_id: str,
        metric: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch active AI recommendations for an organisation."""
        query = db.query(AIRecommendation).filter(
            AIRecommendation.organisation_id == organisation_id,
            AIRecommendation.status.in_(["ACTIVE", "OPEN"]),
        )
        if metric:
            query = query.filter(AIRecommendation.metric == metric.lower().strip())

        recs = query.order_by(AIRecommendation.created_at.desc()).limit(5).all()

        items = []
        for r in recs:
            items.append({
                "id": r.id,
                "metric": r.metric,
                "block": r.facility_id or r.block_id or "Facility",
                "priority": r.priority,
                "summary": r.summary,
                "actions": r.recommended_actions_list,
                "causes": r.possible_causes_list,
            })

        return {
            "total_active": len(recs),
            "recommendations": items,
        }

    @staticmethod
    def get_forecast(
        db: Session,
        organisation_id: str,
        metric: str,
    ) -> Dict[str, Any]:
        """Retrieve 24h AI time-series forecast for energy or water."""
        clean_metric = metric.lower().strip()
        if clean_metric not in ("energy", "water"):
            return {
                "available": False,
                "reason": f"AI time-series forecasting is currently configured for energy and water metrics.",
            }

        try:
            fc = forecasting_service.get_forecast(db, organisation_id, clean_metric, horizon="24h")
            if not fc or not fc.forecast:
                return {
                    "available": False,
                    "reason": "Insufficient historical telemetry points to fit forecasting model.",
                }

            vals = [p.predicted_value for p in fc.forecast]
            avg_pred = sum(vals) / len(vals)
            first_val = vals[0]
            last_val = vals[-1]
            trend = "upward" if last_val > first_val * 1.03 else "downward" if last_val < first_val * 0.97 else "stable"

            return {
                "available": True,
                "metric": clean_metric,
                "horizon": "24h",
                "points_count": len(fc.forecast),
                "average_predicted": round(avg_pred, 2),
                "unit": fc.unit,
                "trend": trend,
                "model_name": fc.model_name,
            }
        except Exception as e:
            logger.debug("Forecast retrieval exception: %s", e)
            return {
                "available": False,
                "reason": "Forecast data is currently insufficient for this metric.",
            }

    @staticmethod
    def get_organisation_summary(
        db: Session,
        organisation_id: str,
    ) -> Dict[str, Any]:
        """Summary of organisation health, sensor metrics, and operational counts."""
        org = db.query(Organisation).filter_by(id=organisation_id).first()
        if not org:
            return {"found": False}

        cfg = db.query(OrganisationSensorConfig).filter_by(organisation_id=organisation_id).first()
        enabled_sensors = cfg.enabled_sensors_list if cfg else []

        active_anomalies_count = (
            db.query(AnomalyRecord)
            .filter(
                AnomalyRecord.organisation_id == organisation_id,
                AnomalyRecord.status.in_([AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED]),
            )
            .count()
        )

        active_recs_count = (
            db.query(AIRecommendation)
            .filter(
                AIRecommendation.organisation_id == organisation_id,
                AIRecommendation.status.in_(["ACTIVE", "OPEN"]),
            )
            .count()
        )

        blocks_count = (
            db.query(FacilityBlock)
            .filter(FacilityBlock.organisation_id == organisation_id, FacilityBlock.is_active.is_(True))
            .count()
        )

        return {
            "found": True,
            "id": org.id,
            "name": org.name,
            "org_type": org.org_type or "Facility",
            "location": org.location or "Campus",
            "enabled_sensors": enabled_sensors,
            "data_source": cfg.data_source if cfg else "synthetic",
            "active_anomalies": active_anomalies_count,
            "active_recommendations": active_recs_count,
            "total_blocks": blocks_count,
        }

    # =========================================================================
    # SUPER_ADMIN ONLY PLATFORM TOOLS
    # =========================================================================

    @staticmethod
    def get_total_organisations(db: Session) -> Dict[str, Any]:
        """Fetch exact count of registered organisations from database."""
        count = db.query(func.count(Organisation.id)).scalar() or 0
        active_count = db.query(func.count(Organisation.id)).filter(Organisation.is_active.is_(True)).scalar() or 0
        return {
            "total_organisations": count,
            "active_organisations": active_count,
        }

    @staticmethod
    def count_organisations_by_facility_type(db: Session, facility_type: str) -> Dict[str, Any]:
        """
        Fetch exact count of registered organisations matching a specific facility type.
        Uses normalization for terms such as 'school', 'college', 'hospital', 'municipality'.
        """
        raw_term = (facility_type or "").lower().strip()
        
        # Canonical term mapping & display labels
        if "school" in raw_term:
            match_key = "school"
            display_type = "School"
        elif "college" in raw_term or "university" in raw_term:
            match_key = "college"
            display_type = "College / University"
        elif "hospital" in raw_term or "medical" in raw_term:
            match_key = "hospital"
            display_type = "Hospital"
        elif "municipal" in raw_term or "civic" in raw_term or "city" in raw_term:
            match_key = "municipal"
            display_type = "Municipality"
        elif "industrial" in raw_term or "factory" in raw_term:
            match_key = "industrial"
            display_type = "Industrial Estate"
        elif "public" in raw_term or "govt" in raw_term or "government" in raw_term:
            match_key = "public"
            display_type = "Public Sector"
        else:
            match_key = raw_term
            display_type = raw_term.capitalize() if raw_term else "Facility"

        all_orgs = db.query(Organisation).all()
        matching_items = []
        for o in all_orgs:
            o_type = (o.org_type or "").lower()
            o_name = (o.name or "").lower()
            if match_key in o_type or match_key in o_name:
                matching_items.append({
                    "id": o.id,
                    "name": o.name,
                    "org_type": o.org_type or display_type,
                    "is_active": o.is_active,
                })

        total_match = len(matching_items)
        active_match = sum(1 for item in matching_items if item["is_active"])

        return {
            "facility_type": display_type,
            "match_key": match_key,
            "total_organisations": total_match,
            "active_organisations": active_match,
            "organisations": matching_items,
            "total_registered_in_db": len(all_orgs),
        }

    @staticmethod
    def get_total_admins(db: Session) -> Dict[str, Any]:
        """Fetch total number of admin accounts across all organisations."""
        count = db.query(func.count(User.id)).filter(User.role == User.ROLE_ADMIN).scalar() or 0
        return {
            "total_admins": count,
        }

    @staticmethod
    def get_organisation_list(db: Session) -> Dict[str, Any]:
        """Retrieve overview list of registered organisations."""
        orgs = db.query(Organisation).all()
        items = []
        for o in orgs:
            items.append({
                "id": o.id,
                "name": o.name,
                "org_type": o.org_type or "Facility",
                "location": o.location or "Campus",
                "is_active": o.is_active,
            })
        return {
            "total_organisations": len(items),
            "organisations": items,
        }

    @staticmethod
    def get_platform_summary(db: Session) -> Dict[str, Any]:
        """Platform-wide aggregation across all customer organisations (Super Admin only)."""
        orgs = db.query(Organisation).all()
        total_orgs = len(orgs)
        active_orgs = sum(1 for o in orgs if o.is_active)

        total_readings = db.query(func.count(SensorReading.id)).scalar() or 0
        total_anomalies = (
            db.query(func.count(AnomalyRecord.id))
            .filter(AnomalyRecord.status.in_([AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED]))
            .scalar()
            or 0
        )
        total_devices = db.query(func.count(IoTDevice.id)).scalar() or 0
        total_users = db.query(func.count(User.id)).scalar() or 0

        # Organisation breakdown with active anomaly counts
        org_details = []
        for o in orgs:
            anom_cnt = (
                db.query(func.count(AnomalyRecord.id))
                .filter(
                    AnomalyRecord.organisation_id == o.id,
                    AnomalyRecord.status.in_([AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED]),
                )
                .scalar()
                or 0
            )
            org_details.append({
                "id": o.id,
                "name": o.name,
                "is_active": o.is_active,
                "active_anomalies": anom_cnt,
            })

        return {
            "total_organisations": total_orgs,
            "active_organisations": active_orgs,
            "total_telemetry_readings": total_readings,
            "platform_active_anomalies": total_anomalies,
            "total_iot_devices": total_devices,
            "total_users": total_users,
            "organisations": org_details,
        }

    @staticmethod
    def compare_organisations(
        db: Session,
        metric: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare metric consumption or anomaly volume across organisations (Super Admin only)."""
        orgs = db.query(Organisation).filter_by(is_active=True).all()
        clean_metric = metric.lower().strip() if metric else "energy"

        comparison = []
        for o in orgs:
            latest = (
                db.query(SensorReading)
                .filter(SensorReading.organisation_id == o.id, SensorReading.sensor_type == clean_metric)
                .order_by(SensorReading.timestamp.desc())
                .first()
            )
            anom_cnt = (
                db.query(func.count(AnomalyRecord.id))
                .filter(
                    AnomalyRecord.organisation_id == o.id,
                    AnomalyRecord.metric == clean_metric,
                    AnomalyRecord.status.in_([AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED]),
                )
                .scalar()
                or 0
            )
            comparison.append({
                "org_id": o.id,
                "org_name": o.name,
                "latest_value": round(latest.value, 2) if latest else 0.0,
                "unit": latest.unit if latest else "",
                "active_anomalies": anom_cnt,
            })

        comparison.sort(key=lambda x: x["latest_value"], reverse=True)
        return {
            "metric": clean_metric,
            "ranked_organisations": comparison,
        }
