"""
GreenNexa — AI Anomaly Detection Service.

Provides reusable statistical anomaly detection across supported sensor metrics
(energy, water, temperature, humidity, co2, waste) using rolling historical baselines.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    OrganisationSensorConfig,
    SensorReading,
    User,
)

logger = logging.getLogger(__name__)

SUPPORTED_ANOMALY_SENSORS = {
    "energy",
    "water",
    "temperature",
    "humidity",
    "co2",
    "waste",
}

MIN_HISTORY_READINGS = 5
DEFAULT_LOOKBACK_DAYS = 7


class AnomalyDetectionService:
    """
    Service handling statistical Z-score anomaly detection, severity classification,
    deduplication, and database persistence.
    """

    def detect_anomalies_for_organisation(
        self,
        db: Session,
        organisation_id: str,
        sensor_type: Optional[str] = None,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ) -> Dict:
        """
        Run statistical anomaly detection for an organisation's enabled sensors.
        """
        # 1. Get organisation sensor configuration
        config = (
            db.query(OrganisationSensorConfig)
            .filter(OrganisationSensorConfig.organisation_id == organisation_id)
            .first()
        )
        enabled_sensors = config.enabled_sensors_list if config else list(SUPPORTED_ANOMALY_SENSORS)

        # Filter target sensors
        if sensor_type:
            clean_sensor = sensor_type.lower().strip()
            if clean_sensor not in SUPPORTED_ANOMALY_SENSORS:
                raise ValueError(
                    f"Unsupported sensor type '{sensor_type}' for anomaly detection. "
                    f"Supported types: {', '.join(sorted(SUPPORTED_ANOMALY_SENSORS))}."
                )
            if clean_sensor not in enabled_sensors:
                raise ValueError(
                    f"Sensor '{sensor_type}' is disabled for organisation '{organisation_id}'."
                )
            target_sensors = [clean_sensor]
        else:
            target_sensors = [s for s in enabled_sensors if s in SUPPORTED_ANOMALY_SENSORS]

        results = []
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=lookback_days)

        for s_type in target_sensors:
            # Query recent readings
            readings = (
                db.query(SensorReading)
                .filter(
                    SensorReading.organisation_id == organisation_id,
                    SensorReading.sensor_type == s_type,
                    SensorReading.timestamp >= cutoff,
                )
                .order_by(SensorReading.timestamp.asc())
                .all()
            )

            if len(readings) < MIN_HISTORY_READINGS:
                results.append({
                    "sensor_type": s_type,
                    "anomaly_detected": False,
                    "reason": "Insufficient historical data for anomaly detection.",
                    "reading_count": len(readings),
                })
                continue

            latest_reading = readings[-1]
            history_values = [r.value for r in readings[:-1] if r.value is not None and math.isfinite(r.value)]

            if len(history_values) < MIN_HISTORY_READINGS:
                results.append({
                    "sensor_type": s_type,
                    "anomaly_detected": False,
                    "reason": "Insufficient historical data for anomaly detection.",
                    "reading_count": len(history_values),
                })
                continue

            # Evaluate reading using ML Isolation Forest + Statistical Z-score + Rule thresholds
            mean_val = float(np.mean(history_values)) if history_values else 100.0
            has_custom_cfg = bool(config and config.sensor_configs)
            cfg_dict = config.sensor_configs_dict.get(s_type, {}) if config else {}
            if has_custom_cfg and "baseline" in cfg_dict:
                s_base = float(cfg_dict["baseline"])
            else:
                s_base = mean_val
            s_warn = float(cfg_dict.get("warning_threshold", 15.0)) if cfg_dict else 15.0
            s_crit = float(cfg_dict.get("critical_threshold", 30.0)) if cfg_dict else 30.0

            from app.services.anomaly_ml_service import anomaly_ml_service
            eval_res = anomaly_ml_service.evaluate_reading(
                current_value=latest_reading.value,
                history_values=history_values,
                metric=s_type,
                unit=latest_reading.unit or "",
                timestamp=latest_reading.timestamp,
                baseline=s_base,
                warning_threshold_pct=s_warn,
                critical_threshold_pct=s_crit,
            )

            severity = eval_res["severity"]
            expected_min = eval_res["expected_min"]
            expected_max = eval_res["expected_max"]
            score = eval_res["anomaly_score"]
            z_score = eval_res["z_score"]
            reason_str = eval_res["reason"]
            curr_val = latest_reading.value

            record_id = None
            if eval_res["is_anomaly"]:
                # Deduplication check: check if record already exists for latest_reading
                existing_anomaly = (
                    db.query(AnomalyRecord)
                    .filter(
                        AnomalyRecord.organisation_id == organisation_id,
                        AnomalyRecord.sensor_type == s_type,
                        AnomalyRecord.value == curr_val,
                        AnomalyRecord.timestamp >= latest_reading.timestamp - timedelta(minutes=5),
                        AnomalyRecord.timestamp <= latest_reading.timestamp + timedelta(minutes=5),
                    )
                    .first()
                )

                if existing_anomaly:
                    record_id = existing_anomaly.id
                else:
                    new_record = AnomalyRecord(
                        organisation_id=organisation_id,
                        block_id=latest_reading.block_id,
                        ward_id=latest_reading.ward_id,
                        facility_id=latest_reading.facility_id,
                        metric=s_type,
                        sensor_type=s_type,
                        value=curr_val,
                        expected_min=expected_min,
                        expected_max=expected_max,
                        anomaly_score=score,
                        severity=severity,
                        reason=reason_str,
                        status=AnomalyRecord.STATUS_OPEN,
                        timestamp=latest_reading.timestamp,
                    )
                    db.add(new_record)
                    db.commit()
                    db.refresh(new_record)
                    record_id = new_record.id

                    # Mark reading as anomaly
                    latest_reading.is_anomaly = True
                    latest_reading.anomaly_severity = severity
                    db.commit()

            results.append({
                "sensor_type": s_type,
                "anomaly_detected": eval_res["is_anomaly"],
                "current_value": curr_val,
                "expected_min": expected_min,
                "expected_max": expected_max,
                "score": score,
                "z_score": z_score,
                "ml_anomaly_score": eval_res["ml_anomaly_score"],
                "ml_evaluated": eval_res["ml_evaluated"],
                "detection_method": eval_res["detection_method"],
                "model_name": eval_res["model_name"],
                "severity": severity,
                "reason": reason_str,
                "timestamp": latest_reading.timestamp,
                "anomaly_id": record_id,
            })

        return {
            "organisation_id": organisation_id,
            "evaluated_at": now,
            "results": results,
        }

    def process_single_reading(
        self,
        db: Session,
        reading: SensorReading,
        config: Optional[OrganisationSensorConfig] = None,
        force_new: bool = False,
    ) -> Optional[AnomalyRecord]:
        """
        Process a single incoming sensor reading (from IoT hardware or synthetic simulator)
        through the unified ML Isolation Forest + Statistical Z-score + Rule Threshold pipeline.
        If an anomaly is detected, creates AnomalyRecord and generates linked AIRecommendation.
        Guarantees non-blocking, exception-safe behavior.

        When force_new=True (used for Demo scenario anomalies), the 5-minute same-location
        dedup is bypassed so EVERY completed demo cycle persists a brand-new AnomalyRecord
        (and a linked recommendation via skip_recent_dedup).
        """
        try:
            org_id = reading.organisation_id
            s_type = reading.sensor_type.lower().strip()

            if config is None:
                config = (
                    db.query(OrganisationSensorConfig)
                    .filter(OrganisationSensorConfig.organisation_id == org_id)
                    .first()
                )

            # Query historical readings prior to this reading
            cutoff = (reading.timestamp or datetime.now(timezone.utc)) - timedelta(days=DEFAULT_LOOKBACK_DAYS)
            query = (
                db.query(SensorReading.value)
                .filter(
                    SensorReading.organisation_id == org_id,
                    SensorReading.sensor_type == s_type,
                    SensorReading.timestamp >= cutoff,
                    SensorReading.timestamp < reading.timestamp,
                )
            )
            if reading.block_id:
                query = query.filter(SensorReading.block_id == reading.block_id)
            elif reading.ward_id:
                # Ward readings carry block_id=None, so a `facility_id` fallback
                # compared names across every ward. Scope to the exact ward.
                query = query.filter(SensorReading.ward_id == reading.ward_id)
            elif reading.facility_id:
                query = query.filter(SensorReading.facility_id == reading.facility_id)

            history_rows = query.order_by(SensorReading.timestamp.asc()).all()
            history_values = [r[0] for r in history_rows if r[0] is not None and math.isfinite(r[0])]

            mean_val = float(np.mean(history_values)) if history_values else None
            has_custom_cfg = bool(config and config.sensor_configs)
            cfg_dict = config.sensor_configs_dict.get(s_type, {}) if config else {}
            if has_custom_cfg and "baseline" in cfg_dict:
                baseline = float(cfg_dict["baseline"])
            elif mean_val is not None:
                baseline = mean_val
            else:
                baseline = float(cfg_dict.get("baseline", 100.0))
            warn_pct = float(cfg_dict.get("warning_threshold", 15.0))
            crit_pct = float(cfg_dict.get("critical_threshold", 30.0))

            from app.services.anomaly_ml_service import anomaly_ml_service
            eval_res = anomaly_ml_service.evaluate_reading(
                current_value=reading.value,
                history_values=history_values,
                metric=s_type,
                unit=reading.unit or "",
                timestamp=reading.timestamp,
                baseline=baseline,
                warning_threshold_pct=warn_pct,
                critical_threshold_pct=crit_pct,
            )

            is_anom = eval_res["is_anomaly"] or bool(reading.is_anomaly)
            if not is_anom:
                return None

            severity = reading.anomaly_severity or eval_res["severity"] or AnomalyRecord.SEVERITY_HIGH

            recent_anom = None
            if not force_new:
                # Deduplication: check recent open anomaly for same metric and same location
                # (block, ward, or org level) in the last 5 minutes.
                recent_query = (
                    db.query(AnomalyRecord)
                    .filter(
                        AnomalyRecord.organisation_id == org_id,
                        AnomalyRecord.sensor_type == s_type,
                        AnomalyRecord.status == AnomalyRecord.STATUS_OPEN,
                        AnomalyRecord.timestamp >= reading.timestamp - timedelta(minutes=5),
                        AnomalyRecord.timestamp <= reading.timestamp + timedelta(minutes=5),
                    )
                )
                if reading.block_id:
                    recent_query = recent_query.filter(AnomalyRecord.block_id == reading.block_id)
                elif reading.ward_id:
                    recent_query = recent_query.filter(AnomalyRecord.ward_id == reading.ward_id)
                recent_anom = recent_query.first()
                if recent_anom:
                    return recent_anom

            new_record = AnomalyRecord(
                organisation_id=org_id,
                block_id=reading.block_id,
                ward_id=reading.ward_id,
                facility_id=reading.facility_id,
                metric=s_type,
                sensor_type=s_type,
                value=reading.value,
                expected_min=eval_res["expected_min"],
                expected_max=eval_res["expected_max"],
                anomaly_score=eval_res["anomaly_score"],
                severity=severity,
                reason=eval_res["reason"],
                status=AnomalyRecord.STATUS_OPEN,
                timestamp=reading.timestamp or datetime.now(timezone.utc),
            )
            db.add(new_record)
            reading.is_anomaly = True
            reading.anomaly_severity = severity
            db.commit()
            db.refresh(new_record)

            # Automatically trigger linked AI recommendation generation
            try:
                from app.services.recommendation import recommendation_service
                recommendation_service.generate_recommendations_for_organisation(
                    db=db, organisation_id=org_id, sensor_type=s_type,
                    skip_recent_dedup=force_new,
                )
            except Exception as rec_err:
                logger.warning("Recommendation generation warning following anomaly: %s", rec_err)

            return new_record
        except Exception as e:
            logger.error("Error processing single reading for anomaly detection: %s", e, exc_info=True)
            return None

    def update_anomaly_status(
        self,
        db: Session,
        anomaly_id: str,
        new_status: str,
        organisation_id: Optional[str] = None,
    ) -> AnomalyRecord:
        """
        Update anomaly lifecycle status (OPEN, ACKNOWLEDGED, RESOLVED, DISMISSED).
        Enforces duplicate action prevention and terminal status protection.
        Synchronizes linked AI recommendations where applicable.
        """
        query = db.query(AnomalyRecord).filter(AnomalyRecord.id == anomaly_id)
        if organisation_id is not None:
            query = query.filter(AnomalyRecord.organisation_id == organisation_id)
        anomaly = query.first()
        if not anomaly:
            raise ValueError(f"Anomaly record '{anomaly_id}' not found.")

        clean_status = new_status.upper().strip()
        valid_statuses = {
            AnomalyRecord.STATUS_OPEN,
            AnomalyRecord.STATUS_ACKNOWLEDGED,
            AnomalyRecord.STATUS_RESOLVED,
            AnomalyRecord.STATUS_DISMISSED,
        }
        if clean_status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{new_status}'. Allowed statuses: {', '.join(sorted(valid_statuses))}."
            )

        # Duplicate action prevention: already in this status
        if anomaly.status == clean_status:
            raise ValueError(f"Anomaly '{anomaly_id}' is already {clean_status}.")

        # Terminal status prevention: cannot re-resolve/dismiss or oscillate back to OPEN
        if anomaly.status in {AnomalyRecord.STATUS_RESOLVED, AnomalyRecord.STATUS_DISMISSED}:
            raise ValueError(
                f"Anomaly '{anomaly_id}' is already {anomaly.status} and cannot transition to {clean_status}."
            )

        now = datetime.now(timezone.utc)
        anomaly.status = clean_status

        target_rec_status = (
            AIRecommendation.STATUS_RESOLVED
            if clean_status == AnomalyRecord.STATUS_RESOLVED
            else AIRecommendation.STATUS_DISMISSED
            if clean_status == AnomalyRecord.STATUS_DISMISSED
            else AIRecommendation.STATUS_ACKNOWLEDGED
            if clean_status == AnomalyRecord.STATUS_ACKNOWLEDGED
            else clean_status
        )

        if clean_status == AnomalyRecord.STATUS_RESOLVED:
            anomaly.resolved_at = now
        elif clean_status == AnomalyRecord.STATUS_DISMISSED:
            anomaly.resolved_at = now
        elif clean_status == AnomalyRecord.STATUS_ACKNOWLEDGED:
            anomaly.acknowledged_at = now

        # Synchronize all linked recommendations in database
        rec_query = db.query(AIRecommendation).filter(AIRecommendation.anomaly_id == anomaly.id)
        if anomaly.organisation_id:
            rec_query = rec_query.filter(AIRecommendation.organisation_id == anomaly.organisation_id)
        linked_recs = rec_query.all()
        for r in linked_recs:
            r.status = target_rec_status

        # Synchronize via ORM relationship if loaded
        if anomaly.recommendation:
            anomaly.recommendation.status = target_rec_status

        db.commit()
        db.refresh(anomaly)
        logger.info("Anomaly %s status updated to %s (synced %d recommendations)", anomaly_id, clean_status, len(linked_recs))
        return anomaly

    SEVERITY_PENALTIES: dict[str, int] = {
        AnomalyRecord.SEVERITY_CRITICAL: 20,
        AnomalyRecord.SEVERITY_HIGH: 10,
        AnomalyRecord.SEVERITY_MEDIUM: 5,
        AnomalyRecord.SEVERITY_LOW: 2,
    }

    def calculate_optimal_score(
        self,
        anomalies_or_db: Union[Session, List[Any]],
        organisation_id: Optional[str] = None,
    ) -> int:
        """
        Dynamically calculates facility Optimal Score from current ACTIVE anomalies.
        Start from 100%. For every active anomaly, subtract its severity penalty:
          Critical = -20%
          High = -10%
          Medium = -5%
          Low = -2%
        Common across all anomaly types/modules.
        Score is NOT forced to zero (can go negative).
        Resolved and dismissed anomalies do NOT contribute penalty.
        """
        active_statuses = (AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED)
        if hasattr(anomalies_or_db, "query"):
            active = (
                anomalies_or_db.query(AnomalyRecord)
                .filter(
                    AnomalyRecord.organisation_id == organisation_id,
                    AnomalyRecord.status.in_(active_statuses),
                )
                .all()
            )
        else:
            active = []
            for a in anomalies_or_db:
                status = a.get("status") if isinstance(a, dict) else getattr(a, "status", None)
                if status in active_statuses:
                    active.append(a)
                elif status not in (AnomalyRecord.STATUS_RESOLVED, AnomalyRecord.STATUS_DISMISSED) and status is not None:
                    active.append(a)

        score = 100
        for a in active:
            if isinstance(a, dict):
                sev = (a.get("severity") or "").upper().strip()
            else:
                sev = (getattr(a, "severity", "") or "").upper().strip()
            penalty = self.SEVERITY_PENALTIES.get(sev, 0)
            score -= penalty

        return score

    def calculate_health_score(
        self,
        anomalies_or_db: Union[Session, List[Any]],
        organisation_id: Optional[str] = None,
    ) -> int:
        """Backward-compatible alias for calculate_optimal_score."""
        return self.calculate_optimal_score(anomalies_or_db, organisation_id)


# Singleton instance
anomaly_detection_service = AnomalyDetectionService()
anomaly_service = anomaly_detection_service

SEVERITY_PENALTIES = AnomalyDetectionService.SEVERITY_PENALTIES


def calculate_optimal_score(
    anomalies_or_db: Union[Session, List[Any]],
    organisation_id: Optional[str] = None,
) -> int:
    return anomaly_detection_service.calculate_optimal_score(anomalies_or_db, organisation_id)


