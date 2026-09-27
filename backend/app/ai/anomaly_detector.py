"""
GreenNexa — Statistical Anomaly Detector.

Approach:
  1. Load recent historical readings for the same metric + org + facility.
  2. Compute mean and standard deviation of historical values.
  3. Compare the current value against the historical distribution.
  4. Classify severity: NORMAL / LOW / MEDIUM / HIGH / CRITICAL.
  5. Generate a human-readable reason explaining the finding.
  6. Save the result to `anomaly_records` (only if severity > NORMAL).

Design principles:
  - Do NOT create anomalies artificially on every cycle.
  - Handle missing / insufficient data gracefully.
  - Maintain organisation_id / facility_id isolation.
  - Never assert an unverified root cause.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import AnomalyRecord, SensorReading

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — can be overridden via environment variables
# ---------------------------------------------------------------------------
HISTORY_DAYS = 30          # Look back this many days for historical context
MIN_HISTORY_POINTS = 5     # Minimum readings before statistical detection runs
FALLBACK_STD_RATIO = 0.2   # If std is 0, use 20% of mean as std (avoids division by zero)

# Z-score thresholds for severity classification
Z_LOW = 1.5
Z_MEDIUM = 2.0
Z_HIGH = 2.8
Z_CRITICAL = 3.5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_and_save(
    db: Session,
    organisation_id: str,
    facility_id: Optional[str],
    metric: str,
    sensor_type: str,
    value: float,
    unit: str = "",
    timestamp: Optional[datetime] = None,
) -> Optional[AnomalyRecord]:
    """
    Run anomaly detection for a single reading.

    Returns:
        AnomalyRecord if severity >= LOW and anomaly was saved.
        None if reading is NORMAL or data is insufficient.
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.replace(tzinfo=None)

    # ------------------------------------------------------------------
    # 1. Load historical data for this metric / org / facility
    # ------------------------------------------------------------------
    history_df = _load_history(db, organisation_id, facility_id, sensor_type, timestamp)

    # ------------------------------------------------------------------
    # Check organisation-specific baseline and thresholds
    # ------------------------------------------------------------------
    from app.db.models import OrganisationSensorConfig
    config = db.query(OrganisationSensorConfig).filter_by(organisation_id=organisation_id).first()
    if config:
        s_clean = (sensor_type or metric).lower().strip()
        scfg = config.sensor_configs_dict.get(s_clean)
        if scfg and "baseline" in scfg:
            baseline = float(scfg["baseline"])
            warn_pct = float(scfg.get("warning_threshold", 15.0))
            crit_pct = float(scfg.get("critical_threshold", 30.0))
            sensor_unit = scfg.get("unit") or unit
            warn_delta = baseline * (warn_pct / 100.0)
            crit_delta = baseline * (crit_pct / 100.0)
            expected_min = round(baseline - warn_delta, 2)
            expected_max = round(baseline + warn_delta, 2)
            dev_val = abs(value - baseline)
            dev_pct = (dev_val / baseline * 100.0) if baseline != 0 else 0.0

            if dev_pct > crit_pct:
                severity = AnomalyRecord.SEVERITY_CRITICAL
                score = round(min(dev_pct / (crit_pct * 1.5), 1.0), 4)
                direction = "above" if value > baseline else "below"
                reason = (
                    f"Reading {value:.2f} {sensor_unit} is {direction} critical threshold "
                    f"(±{crit_pct:.1f}%). Baseline: {baseline:.2f} {sensor_unit}, Deviation: {dev_pct:.1f}%."
                )
                record = AnomalyRecord(
                    organisation_id=organisation_id,
                    facility_id=facility_id,
                    metric=metric,
                    sensor_type=sensor_type,
                    value=value,
                    expected_min=expected_min,
                    expected_max=expected_max,
                    anomaly_score=score,
                    severity=severity,
                    reason=reason,
                    status=AnomalyRecord.STATUS_OPEN,
                    timestamp=timestamp,
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                return record
            elif dev_pct > warn_pct:
                severity = AnomalyRecord.SEVERITY_HIGH
                score = round(min(dev_pct / crit_pct, 1.0), 4)
                direction = "above" if value > baseline else "below"
                reason = (
                    f"Reading {value:.2f} {sensor_unit} is {direction} warning threshold "
                    f"(±{warn_pct:.1f}%). Baseline: {baseline:.2f} {sensor_unit}, Deviation: {dev_pct:.1f}%."
                )
                record = AnomalyRecord(
                    organisation_id=organisation_id,
                    facility_id=facility_id,
                    metric=metric,
                    sensor_type=sensor_type,
                    value=value,
                    expected_min=expected_min,
                    expected_max=expected_max,
                    anomaly_score=score,
                    severity=severity,
                    reason=reason,
                    status=AnomalyRecord.STATUS_OPEN,
                    timestamp=timestamp,
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                return record
            elif len(history_df) < MIN_HISTORY_POINTS:
                return None

    if len(history_df) < MIN_HISTORY_POINTS:
        logger.debug(
            "Skipping anomaly detection for org=%s metric=%s: "
            "only %d historical points (need %d).",
            organisation_id, metric, len(history_df), MIN_HISTORY_POINTS,
        )
        return None

    # ------------------------------------------------------------------
    # 2. Compute statistics
    # ------------------------------------------------------------------
    result = _classify(value, history_df, metric, unit)
    severity = result["severity"]

    # Only persist anomalies — not normal readings
    if severity == AnomalyRecord.SEVERITY_NORMAL:
        logger.debug(
            "Reading is NORMAL for org=%s metric=%s value=%s.",
            organisation_id, metric, value,
        )
        return None

    # ------------------------------------------------------------------
    # 3. Persist the anomaly record
    # ------------------------------------------------------------------
    record = AnomalyRecord(
        organisation_id=organisation_id,
        facility_id=facility_id,
        metric=metric,
        sensor_type=sensor_type,
        value=value,
        expected_min=result["expected_min"],
        expected_max=result["expected_max"],
        anomaly_score=result["anomaly_score"],
        severity=severity,
        reason=result["reason"],
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=timestamp,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        "Anomaly saved: org=%s metric=%s severity=%s value=%s (expected %.1f–%.1f).",
        organisation_id, metric, severity, value,
        result["expected_min"], result["expected_max"],
    )
    return record


def classify_value(
    value: float,
    history_values: list[float],
    metric: str,
    unit: str = "",
) -> dict:
    """
    Classify a single value without touching the database.
    Useful for testing and in-memory checks.

    Returns a dict with keys:
        severity, anomaly_score, reason, expected_min, expected_max,
        historical_mean, historical_std, z_score
    """
    if not history_values or len(history_values) < MIN_HISTORY_POINTS:
        return {
            "severity": AnomalyRecord.SEVERITY_NORMAL,
            "anomaly_score": 0.0,
            "reason": "Insufficient historical data for anomaly detection.",
            "expected_min": None,
            "expected_max": None,
            "historical_mean": None,
            "historical_std": None,
            "z_score": None,
        }

    history_df = pd.DataFrame({"value": history_values})
    return _classify(value, history_df, metric, unit)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_history(
    db: Session,
    organisation_id: str,
    facility_id: Optional[str],
    sensor_type: str,
    before: datetime,
) -> pd.DataFrame:
    """
    Load sensor readings for the specified org/facility/sensor prior to `before`.
    Returns a DataFrame with column 'value'.
    """
    if before.tzinfo is not None:
        before = before.replace(tzinfo=None)

    cutoff = before - timedelta(days=HISTORY_DAYS)

    query = (
        db.query(SensorReading.value, SensorReading.timestamp)
        .filter(
            SensorReading.organisation_id == organisation_id,
            SensorReading.sensor_type == sensor_type,
            SensorReading.timestamp >= cutoff,
            SensorReading.timestamp < before,
        )
    )

    # Scope to facility if provided
    if facility_id:
        query = query.filter(SensorReading.facility_id == facility_id)

    rows = query.order_by(SensorReading.timestamp.asc()).all()

    if not rows:
        return pd.DataFrame(columns=["value", "timestamp"])

    df = pd.DataFrame(rows, columns=["value", "timestamp"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    return df


def _classify(
    value: float,
    history_df: pd.DataFrame,
    metric: str,
    unit: str,
) -> dict:
    """
    Core classification logic using z-score against historical distribution.
    """
    values = history_df["value"].values
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0

    # Avoid zero std — use a percentage of the mean as a floor
    if std < 1e-9:
        std = max(abs(mean) * FALLBACK_STD_RATIO, 1e-6)

    z_score = abs(value - mean) / std

    # Expected "normal" band: mean ± 1.5 σ (LOW threshold)
    expected_min = mean - Z_LOW * std
    expected_max = mean + Z_LOW * std

    # Anomaly score: normalised z-score clamped to [0, 1]
    anomaly_score = min(z_score / (Z_CRITICAL + 1.0), 1.0)

    # Classify
    if z_score < Z_LOW:
        severity = AnomalyRecord.SEVERITY_NORMAL
    elif z_score < Z_MEDIUM:
        severity = AnomalyRecord.SEVERITY_LOW
    elif z_score < Z_HIGH:
        severity = AnomalyRecord.SEVERITY_MEDIUM
    elif z_score < Z_CRITICAL:
        severity = AnomalyRecord.SEVERITY_HIGH
    else:
        severity = AnomalyRecord.SEVERITY_CRITICAL

    reason = _build_reason(
        metric=metric,
        value=value,
        mean=mean,
        std=std,
        z_score=z_score,
        expected_min=expected_min,
        expected_max=expected_max,
        severity=severity,
        unit=unit,
        n_samples=len(values),
    )

    return {
        "severity": severity,
        "anomaly_score": round(anomaly_score, 4),
        "reason": reason,
        "expected_min": round(expected_min, 4),
        "expected_max": round(expected_max, 4),
        "historical_mean": round(mean, 4),
        "historical_std": round(std, 4),
        "z_score": round(z_score, 4),
    }


def _build_reason(
    metric: str,
    value: float,
    mean: float,
    std: float,
    z_score: float,
    expected_min: float,
    expected_max: float,
    severity: str,
    unit: str,
    n_samples: int,
) -> str:
    """
    Build a human-readable, factual (non-assertive) explanation for the anomaly.
    """
    direction = "above" if value > mean else "below"
    deviation_pct = abs((value - mean) / mean * 100) if mean != 0 else 0.0
    unit_label = f" {unit}" if unit else ""

    if severity == AnomalyRecord.SEVERITY_NORMAL:
        return (
            f"Current {metric} reading of {value:.2f}{unit_label} is within "
            f"the expected range ({expected_min:.2f}–{expected_max:.2f}{unit_label}) "
            f"based on {n_samples} historical readings."
        )

    severity_words = {
        AnomalyRecord.SEVERITY_LOW: "slightly",
        AnomalyRecord.SEVERITY_MEDIUM: "noticeably",
        AnomalyRecord.SEVERITY_HIGH: "significantly",
        AnomalyRecord.SEVERITY_CRITICAL: "extremely",
    }
    adverb = severity_words.get(severity, "")

    return (
        f"Current {metric} reading of {value:.2f}{unit_label} is {adverb} {direction} "
        f"the expected range ({expected_min:.2f}–{expected_max:.2f}{unit_label}). "
        f"Historical average: {mean:.2f}{unit_label} "
        f"(±{std:.2f}, based on {n_samples} readings). "
        f"Deviation: {deviation_pct:.1f}% (z-score: {z_score:.2f}). "
        f"Severity: {severity}."
    )


def compute_trend(history_values: list[float]) -> str:
    """
    Compute a simple linear trend from a sequence of historical values.

    Returns: 'rising' | 'falling' | 'stable' | 'insufficient_data'
    """
    if not history_values or len(history_values) < MIN_HISTORY_POINTS:
        return "insufficient_data"

    x = np.arange(len(history_values), dtype=float)
    y = np.array(history_values, dtype=float)

    # Remove NaN
    mask = ~np.isnan(y)
    if mask.sum() < MIN_HISTORY_POINTS:
        return "insufficient_data"

    x, y = x[mask], y[mask]

    # Linear regression slope
    slope, _ = np.polyfit(x, y, 1)
    mean_y = np.mean(y)

    # Classify slope relative to mean (5% threshold)
    rel_slope = slope / mean_y if abs(mean_y) > 1e-9 else 0.0

    if rel_slope > 0.005:
        return "rising"
    elif rel_slope < -0.005:
        return "falling"
    else:
        return "stable"
