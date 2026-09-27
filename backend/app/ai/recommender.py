"""
GreenNexa — AI Recommendation Engine.

Generates practical, hedged recommendations from anomaly results.

Design Principles (NON-NEGOTIABLE):
  - NEVER assert an unverified root cause as a fact.
  - Use careful language: "Consider checking...", "Possible cause...",
    "Recommended action..."
  - If data is insufficient, return an explicit insufficient-data response.
    Do NOT invent a recommendation.
  - Recommendations are decision-support only. Always attach the
    confidence_note disclaimer.
  - NORMAL severity → no recommendation generated.
  - Scoped strictly to organisation_id / facility_id.

Output structure mirrors AIRecommendation ORM model.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.anomaly_detector import MIN_HISTORY_POINTS, compute_trend
from app.db.models import AIRecommendation, AnomalyRecord, SensorReading

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mandatory disclaimer — always included in every recommendation
# ---------------------------------------------------------------------------
CONFIDENCE_NOTE = (
    "These are decision-support suggestions based on statistical analysis. "
    "They are not verified diagnoses. Please investigate before taking action."
)

# Minimum historical points required to generate a recommendation.
# Without enough context we return an explicit insufficient-data response.
MIN_POINTS_FOR_RECOMMENDATION = MIN_HISTORY_POINTS  # 5


# ---------------------------------------------------------------------------
# Rule table
# ---------------------------------------------------------------------------
# Structure: { metric: { direction: { severity_bucket: (causes, actions) } } }
#
# direction: "high" (value above expected), "low" (below), "any"
# severity_bucket: "low_medium" | "high_critical"
#
# All causes and actions use hedged language.

_RULES: dict[str, dict[str, dict[str, tuple[list[str], list[str]]]]] = {
    # ── ENERGY ────────────────────────────────────────────────────────────
    "energy": {
        "high": {
            "low_medium": (
                [
                    "Possible increase in equipment usage or occupancy levels.",
                    "Possible inefficiency in HVAC or lighting systems.",
                ],
                [
                    "Consider reviewing recent changes to occupancy or equipment schedules.",
                    "Consider checking HVAC operation and thermostat settings.",
                    "Consider reviewing lighting schedules and occupancy sensors.",
                ],
            ),
            "high_critical": (
                [
                    "Possible HVAC system anomaly or malfunction.",
                    "Possible lighting left on outside operational hours.",
                    "Possible major electrical load operating unexpectedly.",
                    "Possible metering or sensor error.",
                ],
                [
                    "Consider checking HVAC operation immediately.",
                    "Review lighting schedules and ensure lights are off outside hours.",
                    "Inspect major electrical loads (chillers, motors, industrial equipment).",
                    "Verify the energy meter reading and sensor connectivity.",
                    "Recommended action: If deviation persists, escalate to facilities team.",
                ],
            ),
        },
        "low": {
            "low_medium": (
                [
                    "Possible reduced occupancy or scheduled equipment shutdown.",
                    "Possible sensor disconnection or temporary outage.",
                ],
                [
                    "Consider verifying sensor connectivity and data feed.",
                    "Check if a planned shutdown or holiday schedule is in effect.",
                ],
            ),
            "high_critical": (
                [
                    "Possible sensor disconnection or power supply fault.",
                    "Possible unexpected facility shutdown.",
                ],
                [
                    "Consider verifying energy meter connectivity and power supply.",
                    "Confirm whether a planned outage is scheduled.",
                    "Recommended action: Inspect sensor and device status.",
                ],
            ),
        },
    },

    # ── WATER ─────────────────────────────────────────────────────────────
    "water": {
        "high": {
            "low_medium": (
                [
                    "Possible increase in water usage due to occupancy or operations.",
                    "Possible minor leak or dripping fixture.",
                ],
                [
                    "Consider reviewing recent occupancy and operational schedules.",
                    "Consider checking taps, fixtures, and visible plumbing for leaks.",
                ],
            ),
            "high_critical": (
                [
                    "Possible pipe leak or burst within the facility.",
                    "Possible irrigation system fault or valve left open.",
                    "Possible high-flow fixture (e.g., cooling tower) operating abnormally.",
                    "Possible water meter or sensor error.",
                ],
                [
                    "Consider checking for visible pipe leaks or wet areas immediately.",
                    "Inspect irrigation systems and check for open or stuck valves.",
                    "Review high-flow fixtures such as cooling towers and boilers.",
                    "Verify the water meter reading and sensor connectivity.",
                    "Recommended action: If a leak is suspected, consider isolating the supply and contacting maintenance.",
                ],
            ),
        },
        "low": {
            "low_medium": (
                [
                    "Possible reduced demand due to lower occupancy.",
                    "Possible water supply interruption.",
                ],
                [
                    "Consider verifying water sensor connectivity.",
                    "Check for any reported supply interruptions or planned maintenance.",
                ],
            ),
            "high_critical": (
                [
                    "Possible water supply failure or main valve shut.",
                    "Possible sensor disconnection or meter fault.",
                ],
                [
                    "Consider verifying the water supply and main shut-off valve status.",
                    "Inspect sensor connectivity and meter integrity.",
                    "Recommended action: Contact the water utility or maintenance team.",
                ],
            ),
        },
    },

    # ── TEMPERATURE ───────────────────────────────────────────────────────
    "temperature": {
        "high": {
            "low_medium": (
                [
                    "Possible HVAC cooling system underperforming.",
                    "Possible increased heat load from occupancy or equipment.",
                ],
                [
                    "Consider checking HVAC cooling settings and thermostat calibration.",
                    "Ensure ventilation is adequate for current occupancy levels.",
                ],
            ),
            "high_critical": (
                [
                    "Possible HVAC cooling failure or refrigerant issue.",
                    "Possible ventilation blockage or duct obstruction.",
                    "Possible heat source (server room, kitchen equipment) operating abnormally.",
                    "Possible temperature sensor fault.",
                ],
                [
                    "Consider checking HVAC cooling system for faults or alarms.",
                    "Inspect ventilation ducts and air handling units for blockages.",
                    "Check windows, doors, and insulation for unexpected heat ingress.",
                    "Verify temperature sensor calibration and placement.",
                    "Recommended action: Ensure the space is safe for occupancy; escalate if cooling cannot be restored.",
                ],
            ),
        },
        "low": {
            "low_medium": (
                [
                    "Possible HVAC heating system operating below set point.",
                    "Possible cold infiltration through windows or doors.",
                ],
                [
                    "Consider checking HVAC heating settings and thermostat.",
                    "Inspect windows and doors for gaps or open status.",
                ],
            ),
            "high_critical": (
                [
                    "Possible HVAC heating failure.",
                    "Possible significant cold infiltration or heating fuel issue.",
                    "Possible temperature sensor fault.",
                ],
                [
                    "Consider checking HVAC heating system for faults.",
                    "Inspect insulation, windows, and doors for major heat loss.",
                    "Verify temperature sensor accuracy.",
                    "Recommended action: Ensure the space meets safe temperature requirements for occupants.",
                ],
            ),
        },
    },

    # ── HUMIDITY ──────────────────────────────────────────────────────────
    "humidity": {
        "high": {
            "low_medium": (
                [
                    "Possible HVAC dehumidification underperforming.",
                    "Possible condensation from temperature differential.",
                ],
                [
                    "Consider checking HVAC dehumidification settings.",
                    "Inspect for signs of condensation on surfaces.",
                ],
            ),
            "high_critical": (
                [
                    "Possible water ingress, leak, or flooding.",
                    "Possible HVAC dehumidification failure.",
                    "Possible humidity sensor fault.",
                ],
                [
                    "Consider inspecting the area for signs of water ingress or leaks.",
                    "Check HVAC dehumidification system for faults.",
                    "Verify humidity sensor calibration.",
                    "Recommended action: High humidity can promote mould growth; escalate if persistent.",
                ],
            ),
        },
        "low": {
            "low_medium": (
                [
                    "Possible HVAC over-drying or heating without humidification.",
                    "Possible low occupancy reducing moisture load.",
                ],
                [
                    "Consider reviewing HVAC heating and humidification settings.",
                    "Check if humidifiers are operational where installed.",
                ],
            ),
            "high_critical": (
                [
                    "Possible significant HVAC malfunction affecting humidity control.",
                    "Possible humidity sensor fault.",
                ],
                [
                    "Consider checking HVAC humidity control systems.",
                    "Verify humidity sensor accuracy.",
                    "Recommended action: Very low humidity can affect occupant comfort and equipment; escalate if persistent.",
                ],
            ),
        },
    },

    # ── CO2 ───────────────────────────────────────────────────────────────
    "co2": {
        "high": {
            "low_medium": (
                [
                    "Possible increased occupancy reducing air quality.",
                    "Possible ventilation system underperforming.",
                ],
                [
                    "Consider increasing ventilation or fresh air supply.",
                    "Review occupancy levels and schedules.",
                ],
            ),
            "high_critical": (
                [
                    "Possible ventilation failure or blocked air handling unit.",
                    "Possible very high occupancy in a confined space.",
                    "Possible CO2 sensor requiring calibration.",
                ],
                [
                    "Consider increasing ventilation immediately.",
                    "Inspect air handling units and ventilation ducts for faults or blockages.",
                    "Review occupancy to ensure the space is not overcrowded.",
                    "Verify CO2 sensor calibration — sensors can drift over time.",
                    "Recommended action: Elevated CO2 can affect occupant health; escalate if ventilation cannot be restored.",
                ],
            ),
        },
        "low": {
            "low_medium": (
                [
                    "Possible low occupancy or efficient ventilation.",
                ],
                [
                    "Consider verifying CO2 sensor calibration if the reading seems unexpectedly low.",
                ],
            ),
            "high_critical": (
                [
                    "Possible CO2 sensor fault or disconnection.",
                ],
                [
                    "Consider verifying CO2 sensor calibration and connectivity.",
                ],
            ),
        },
    },

    # ── AIR QUALITY ───────────────────────────────────────────────────────
    "air_quality": {
        "high": {
            "low_medium": (
                [
                    "Possible increase in particulates or pollutants.",
                    "Possible ventilation underperformance.",
                ],
                [
                    "Consider reviewing ventilation settings.",
                    "Check for nearby sources of dust, smoke, or chemical fumes.",
                ],
            ),
            "high_critical": (
                [
                    "Possible significant air quality event (smoke, dust, chemical release).",
                    "Possible air quality sensor fault.",
                ],
                [
                    "Inspect for sources of smoke, dust, or chemical activity.",
                    "Check air filters and ventilation systems.",
                    "Verify air quality sensor calibration.",
                    "Recommended action: Ensure occupant safety; consider temporary evacuation if values are extreme.",
                ],
            ),
        },
        "low": {
            "any": (
                ["Possible sensor reading error."],
                ["Consider verifying air quality sensor connectivity and calibration."],
            ),
        },
    },

    # ── WASTE ─────────────────────────────────────────────────────────────
    "waste_level": {
        "high": {
            "low_medium": (
                ["Possible increase in waste generation."],
                ["Consider reviewing waste collection schedules."],
            ),
            "high_critical": (
                [
                    "Possible waste collection missed or delayed.",
                    "Possible waste level sensor fault.",
                ],
                [
                    "Consider contacting waste management for urgent collection.",
                    "Verify waste level sensor accuracy.",
                    "Recommended action: Overflow risk — escalate to facilities team.",
                ],
            ),
        },
        "low": {
            "any": (
                ["Possible sensor reading error or recent collection."],
                ["Consider verifying sensor connectivity."],
            ),
        },
    },

    "waste_weight": {
        "high": {
            "low_medium": (
                ["Possible increase in waste generation."],
                ["Consider reviewing waste generation patterns."],
            ),
            "high_critical": (
                ["Possible abnormal waste event."],
                [
                    "Consider reviewing waste collection schedules.",
                    "Inspect for unusual waste events.",
                ],
            ),
        },
        "low": {
            "any": (
                ["Possible sensor fault or very low waste volume."],
                ["Consider verifying waste sensor connectivity."],
            ),
        },
    },

    "waste": {
        "high": {
            "low_medium": (
                ["Possible increase in waste generation."],
                ["Consider reviewing waste disposal schedules."],
            ),
            "high_critical": (
                ["Possible abnormal waste accumulation."],
                [
                    "Consider reviewing waste collection urgency.",
                    "Verify waste sensor readings.",
                ],
            ),
        },
        "low": {
            "any": (
                ["Possible sensor fault or low operational activity."],
                ["Consider verifying waste sensor connectivity."],
            ),
        },
    },
}

# Fallback when metric not in rule table
_DEFAULT_RULE_HIGH = (
    ["Possible sensor or system anomaly."],
    [
        "Consider verifying sensor connectivity and calibration.",
        "Review recent operational changes that may have affected this metric.",
    ],
)
_DEFAULT_RULE_LOW = (
    ["Possible sensor disconnection or reduced operational activity."],
    ["Consider verifying sensor connectivity."],
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_and_save(
    db: Session,
    anomaly: AnomalyRecord,
) -> Optional[AIRecommendation]:
    """
    Generate a recommendation for the given anomaly and persist it.

    Returns:
        AIRecommendation if generated (severity >= LOW).
        None if severity is NORMAL (no recommendation needed).
    """
    # ── Guard: no recommendation for NORMAL ─────────────────────────────
    if anomaly.severity == AnomalyRecord.SEVERITY_NORMAL:
        logger.debug(
            "No recommendation for NORMAL anomaly org=%s metric=%s.",
            anomaly.organisation_id, anomaly.metric,
        )
        return None

    # ── Load historical data for trend ──────────────────────────────────
    history_values = _load_history_values(
        db=db,
        organisation_id=anomaly.organisation_id,
        facility_id=anomaly.facility_id,
        sensor_type=anomaly.sensor_type or anomaly.metric,
    )

    data_sufficient = len(history_values) >= MIN_POINTS_FOR_RECOMMENDATION
    trend = compute_trend(history_values) if data_sufficient else "insufficient_data"

    # ── Build recommendation content ────────────────────────────────────
    if not data_sufficient:
        rec = _build_insufficient_data_recommendation(anomaly, trend)
    else:
        rec = _build_recommendation(anomaly, history_values, trend)

    # ── Persist ─────────────────────────────────────────────────────────
    db_rec = AIRecommendation(
        organisation_id=anomaly.organisation_id,
        facility_id=anomaly.facility_id,
        anomaly_id=anomaly.id,
        metric=anomaly.metric,
        current_value=anomaly.value,
        expected_range_min=anomaly.expected_min,
        expected_range_max=anomaly.expected_max,
        severity=anomaly.severity,
        historical_trend=trend,
        possible_causes=rec["possible_causes_str"],
        recommended_actions=rec["recommended_actions_str"],
        summary=rec["summary"],
        confidence_note=CONFIDENCE_NOTE,
        priority=anomaly.severity,
        data_sufficient=data_sufficient,
    )
    db.add(db_rec)
    db.commit()
    db.refresh(db_rec)

    logger.info(
        "Recommendation saved: org=%s metric=%s severity=%s data_sufficient=%s.",
        anomaly.organisation_id, anomaly.metric, anomaly.severity, data_sufficient,
    )
    return db_rec


def generate_without_saving(
    anomaly_severity: str,
    metric: str,
    current_value: float,
    expected_min: Optional[float],
    expected_max: Optional[float],
    history_values: list[float],
    unit: str = "",
    organisation_id: str = "",
    facility_id: Optional[str] = None,
) -> dict:
    """
    Generate a recommendation dict without touching the database.
    Useful for testing and preview endpoints.

    Returns a dict with all recommendation fields.
    """
    if anomaly_severity == AnomalyRecord.SEVERITY_NORMAL:
        return {
            "generated": False,
            "reason": "No recommendation generated for NORMAL severity readings.",
        }

    data_sufficient = len(history_values) >= MIN_POINTS_FOR_RECOMMENDATION
    trend = compute_trend(history_values) if data_sufficient else "insufficient_data"

    # Build a lightweight anomaly-like dict
    anomaly_like = _FakeAnomaly(
        severity=anomaly_severity,
        metric=metric,
        sensor_type=metric,
        value=current_value,
        expected_min=expected_min,
        expected_max=expected_max,
        organisation_id=organisation_id,
        facility_id=facility_id,
    )

    if not data_sufficient:
        rec = _build_insufficient_data_recommendation(anomaly_like, trend)
    else:
        rec = _build_recommendation(anomaly_like, history_values, trend)

    return {
        "generated": True,
        "data_sufficient": data_sufficient,
        "metric": metric,
        "current_value": current_value,
        "expected_range": f"{expected_min}–{expected_max}" if expected_min is not None else "unknown",
        "severity": anomaly_severity,
        "historical_trend": trend,
        "possible_causes": rec["possible_causes_list"],
        "recommended_actions": rec["recommended_actions_list"],
        "summary": rec["summary"],
        "confidence_note": CONFIDENCE_NOTE,
        "priority": anomaly_severity,
    }


# ---------------------------------------------------------------------------
# Internal: recommendation building
# ---------------------------------------------------------------------------

def _build_recommendation(
    anomaly,
    history_values: list[float],
    trend: str,
) -> dict:
    """Build recommendation content from the rule table."""
    metric = anomaly.metric.lower().replace(" ", "_")
    direction = "high" if anomaly.value > (anomaly.expected_max or anomaly.value - 1) else "low"
    severity_bucket = _severity_bucket(anomaly.severity)

    causes, actions = _lookup_rules(metric, direction, severity_bucket)

    # Add trend-based context
    trend_note = _trend_context(trend, metric, direction)

    summary = _build_summary(
        metric=anomaly.metric,
        value=anomaly.value,
        expected_min=anomaly.expected_min,
        expected_max=anomaly.expected_max,
        severity=anomaly.severity,
        direction=direction,
        trend=trend,
        trend_note=trend_note,
        causes=causes,
        actions=actions,
        n_history=len(history_values),
    )

    return {
        "possible_causes_list": causes,
        "recommended_actions_list": actions,
        "possible_causes_str": " | ".join(causes),
        "recommended_actions_str": " | ".join(actions),
        "summary": summary,
    }


def _build_insufficient_data_recommendation(anomaly, trend: str) -> dict:
    """
    Return an explicit 'Insufficient data' response.
    Do NOT invent causes or actions.
    """
    summary = (
        f"A {anomaly.severity} severity anomaly was detected for '{anomaly.metric}' "
        f"(current value: {anomaly.value:.2f}). "
        "However, insufficient historical data is available to generate a specific recommendation. "
        "Please review the reading manually and compare against known operational baselines."
    )
    return {
        "possible_causes_list": [],
        "recommended_actions_list": [
            "Manually review this reading against known operational baselines.",
            "Consider collecting more historical data before relying on automated recommendations.",
        ],
        "possible_causes_str": "",
        "recommended_actions_str": (
            "Manually review this reading against known operational baselines. | "
            "Consider collecting more historical data before relying on automated recommendations."
        ),
        "summary": summary,
    }


def _build_summary(
    metric: str,
    value: float,
    expected_min: Optional[float],
    expected_max: Optional[float],
    severity: str,
    direction: str,
    trend: str,
    trend_note: str,
    causes: list[str],
    actions: list[str],
    n_history: int,
) -> str:
    """Build the full human-readable summary string."""
    range_str = (
        f"{expected_min:.2f}–{expected_max:.2f}"
        if expected_min is not None and expected_max is not None
        else "unknown"
    )

    lines = [
        f"Issue: {severity} {metric.upper()} anomaly detected.",
        f"",
        f"Evidence:",
        f"  Current value: {value:.2f}",
        f"  Expected range: {range_str}",
        f"  Severity: {severity}",
        f"  Historical trend: {trend}",
        f"  Based on {n_history} historical readings.",
    ]

    if trend_note:
        lines.append(f"  {trend_note}")

    if causes:
        lines.append("")
        lines.append("Possible areas to check:")
        for c in causes:
            lines.append(f"  • {c}")

    if actions:
        lines.append("")
        lines.append("Recommended actions:")
        for a in actions:
            lines.append(f"  • {a}")

    lines.append("")
    lines.append(f"Note: {CONFIDENCE_NOTE}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal: rule lookup helpers
# ---------------------------------------------------------------------------

def _lookup_rules(
    metric: str,
    direction: str,
    severity_bucket: str,
) -> tuple[list[str], list[str]]:
    """
    Look up causes and actions from the rule table.
    Falls back gracefully if metric/direction/bucket not found.
    """
    metric_rules = _RULES.get(metric, {})

    # Try exact direction
    dir_rules = metric_rules.get(direction, metric_rules.get("any", {}))

    # Try exact severity bucket, then fall through to any bucket
    bucket_entry = dir_rules.get(severity_bucket, None)
    if bucket_entry is None:
        # Try the other bucket
        other_bucket = "high_critical" if severity_bucket == "low_medium" else "low_medium"
        bucket_entry = dir_rules.get(other_bucket, dir_rules.get("any", None))

    if bucket_entry:
        causes, actions = bucket_entry
        return list(causes), list(actions)

    # Global fallback
    if direction == "high":
        return list(_DEFAULT_RULE_HIGH[0]), list(_DEFAULT_RULE_HIGH[1])
    return list(_DEFAULT_RULE_LOW[0]), list(_DEFAULT_RULE_LOW[1])


def _severity_bucket(severity: str) -> str:
    """Map severity to the two-bucket system used in the rule table."""
    if severity in (AnomalyRecord.SEVERITY_HIGH, AnomalyRecord.SEVERITY_CRITICAL):
        return "high_critical"
    return "low_medium"


def _trend_context(trend: str, metric: str, direction: str) -> str:
    """Return a sentence contextualising the historical trend."""
    if trend == "insufficient_data":
        return ""
    if trend == "rising" and direction == "high":
        return (
            f"Note: Historical {metric} readings have been trending upward, "
            "which may indicate a developing issue rather than an isolated event."
        )
    if trend == "falling" and direction == "low":
        return (
            f"Note: Historical {metric} readings have been trending downward. "
            "This may warrant investigation into whether demand has dropped unexpectedly."
        )
    if trend == "rising" and direction == "low":
        return (
            f"Note: Historical {metric} readings were previously trending upward "
            "before this unexpected low reading."
        )
    if trend == "stable":
        return (
            f"Note: Historical {metric} readings have been stable, "
            "making this deviation more notable."
        )
    return ""


# ---------------------------------------------------------------------------
# Internal: load history
# ---------------------------------------------------------------------------

def _load_history_values(
    db: Session,
    organisation_id: str,
    facility_id: Optional[str],
    sensor_type: str,
) -> list[float]:
    """Load recent historical sensor values for trend analysis."""
    from datetime import timedelta

    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).replace(tzinfo=None)

    query = (
        db.query(SensorReading.value)
        .filter(
            SensorReading.organisation_id == organisation_id,
            SensorReading.sensor_type == sensor_type,
            SensorReading.timestamp >= cutoff,
        )
    )
    if facility_id:
        query = query.filter(SensorReading.facility_id == facility_id)

    rows = query.order_by(SensorReading.timestamp.asc()).all()

    values = []
    for (v,) in rows:
        try:
            fv = float(v)
            if not (fv != fv):  # exclude NaN
                values.append(fv)
        except (TypeError, ValueError):
            pass

    return values


# ---------------------------------------------------------------------------
# Internal: lightweight anomaly-like duck-typed class for generate_without_saving
# ---------------------------------------------------------------------------

class _FakeAnomaly:
    """Duck-typed anomaly record for in-memory recommendation generation."""
    __slots__ = (
        "severity", "metric", "sensor_type", "value",
        "expected_min", "expected_max", "organisation_id", "facility_id",
    )

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
