"""
GreenNexa — Future Anomaly Risk Estimation Service.

Projects short-term ML time-series forecasts against facility baselines,
warning thresholds, and critical limits to compute the predictive risk
of upcoming threshold violations over the next 24 hours.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import OrganisationSensorConfig, SensorReading
from app.services.forecasting import forecasting_service

logger = logging.getLogger(__name__)


class FutureAnomalyRiskService:
    """
    Estimates upcoming anomaly risk (0.0 to 1.0) and time-to-breach
    by analyzing ML forecast trajectories and expanding confidence envelopes.
    """

    def evaluate_future_risk(
        self,
        db: Session,
        organisation_id: str,
        metric: str,
        horizon: str = "24h",
    ) -> Dict[str, Any]:
        """
        Calculates upcoming threshold breach risk over the specified horizon.
        """
        metric_clean = metric.lower().strip()

        # 1. Fetch organization sensor configuration
        config = (
            db.query(OrganisationSensorConfig)
            .filter(OrganisationSensorConfig.organisation_id == organisation_id)
            .first()
        )

        DEFAULT_BASELINES = {
            "energy": 1000.0,
            "water": 400.0,
            "waste": 50.0,
            "temperature": 28.0,
            "indoor_temperature": 28.0,
            "humidity": 60.0,
            "co2": 800.0,
            "air_quality": 45.0,
            "traffic": 120.0,
            "parking": 65.0,
            "assets": 95.0,
            "safety": 90.0,
            "climate": 75.0,
        }

        cfg_dict = config.sensor_configs_dict.get(metric_clean, {}) if config else {}
        baseline = float(cfg_dict.get("baseline", DEFAULT_BASELINES.get(metric_clean, 100.0)))
        warning_thresh = float(cfg_dict.get("warning_threshold", baseline * 1.15))
        critical_thresh = float(cfg_dict.get("critical_threshold", baseline * 1.30))
        unit = cfg_dict.get("unit", "")

        # 2. Query ML Forecast
        try:
            fc_resp = forecasting_service.get_forecast(
                db=db,
                organisation_id=organisation_id,
                sensor_type=metric_clean,
                horizon=horizon,
                mode="last",
            )
        except Exception as e:
            logger.info("Forecast unavailable for risk evaluation on %s: %s", metric_clean, e)
            return self._fallback_risk(metric_clean, baseline, warning_thresh, critical_thresh, unit, reason=str(e))

        if not fc_resp or not fc_resp.forecast or not fc_resp.is_available:
            return self._fallback_risk(
                metric_clean, baseline, warning_thresh, critical_thresh, unit,
                reason="Forecast unavailable or insufficient telemetry"
            )

        forecast_points = fc_resp.forecast
        predicted_values = [pt.predicted_value for pt in forecast_points]
        upper_bounds = [pt.upper_bound if pt.upper_bound is not None else pt.predicted_value for pt in forecast_points]
        lower_bounds = [pt.lower_bound if pt.lower_bound is not None else pt.predicted_value for pt in forecast_points]

        # 3. Analyze trajectory and breach points
        breach_hour: Optional[int] = None
        warning_hour: Optional[int] = None
        max_upper = max(upper_bounds) if upper_bounds else baseline
        max_pred = max(predicted_values) if predicted_values else baseline

        for idx, (p_val, u_val) in enumerate(zip(predicted_values, upper_bounds), start=1):
            if u_val >= critical_thresh or p_val >= critical_thresh:
                if breach_hour is None:
                    breach_hour = idx
            elif u_val >= warning_thresh or p_val >= warning_thresh:
                if warning_hour is None:
                    warning_hour = idx

        # 4. Trajectory slope (rate of change across horizon)
        if len(predicted_values) >= 2:
            slope = (predicted_values[-1] - predicted_values[0]) / len(predicted_values)
        else:
            slope = 0.0

        # 5. Continuous Risk Score Calculation [0.0 - 1.0]
        # Base factor: how close is max projected upper bound to critical threshold
        headroom = critical_thresh - max_upper
        total_span = critical_thresh - baseline if critical_thresh > baseline else 1.0

        if max_upper >= critical_thresh:
            # Probability scaled by predicted vs upper bound
            if max_pred >= critical_thresh:
                risk_score = 0.85 + min(0.15, (max_pred - critical_thresh) / total_span * 0.15)
            else:
                risk_score = 0.65 + min(0.20, (max_upper - critical_thresh) / total_span * 0.20)
        elif max_upper >= warning_thresh:
            pct_into_warn = (max_upper - warning_thresh) / (critical_thresh - warning_thresh) if critical_thresh > warning_thresh else 0.5
            risk_score = 0.35 + (pct_into_warn * 0.25)
        else:
            dist_to_warn = warning_thresh - max_upper
            risk_score = max(0.05, 0.35 - (dist_to_warn / total_span * 0.30))

        # Adjust for positive rising acceleration
        if slope > 0:
            risk_score = min(1.0, risk_score + min(0.10, slope / baseline * 0.5))

        risk_score = round(max(0.0, min(1.0, risk_score)), 3)

        # 6. Categorical Risk Level
        if risk_score >= 0.75:
            risk_level = "CRITICAL"
        elif risk_score >= 0.50:
            risk_level = "HIGH"
        elif risk_score >= 0.25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # 7. Explainable Driver Breakdown
        explanation_parts = []
        if breach_hour is not None:
            explanation_parts.append(
                f"Projected critical breach within {breach_hour}h (peak projection: {max_pred:.1f} {unit}, upper envelope: {max_upper:.1f} {unit} vs limit {critical_thresh:.1f} {unit})."
            )
        elif warning_hour is not None:
            explanation_parts.append(
                f"Projected warning threshold breach within {warning_hour}h (upper envelope {max_upper:.1f} {unit} exceeds warning threshold {warning_thresh:.1f} {unit})."
            )
        else:
            explanation_parts.append(
                f"Trajectory stable within safe operating envelope (peak projection {max_pred:.1f} {unit}, headroom to critical limit: {headroom:.1f} {unit})."
            )

        if slope > 0.5:
            explanation_parts.append(f"Metric shows steep upward trend (+{slope:.2f} {unit}/h).")
        elif slope < -0.5:
            explanation_parts.append(f"Metric shows cooling/declining trend ({slope:.2f} {unit}/h).")

        return {
            "metric": metric_clean,
            "organisation_id": organisation_id,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "risk_level": risk_level,
            "risk_score": risk_score,
            "projected_breach": breach_hour is not None,
            "estimated_time_to_breach_hours": breach_hour or warning_hour,
            "baseline": baseline,
            "warning_threshold": warning_thresh,
            "critical_threshold": critical_thresh,
            "unit": unit,
            "peak_projected_value": round(max_pred, 2),
            "peak_upper_bound": round(max_upper, 2),
            "trajectory_slope_per_hour": round(slope, 3),
            "explanation": " ".join(explanation_parts),
        }

    def _fallback_risk(
        self,
        metric: str,
        baseline: float,
        warning_thresh: float,
        critical_thresh: float,
        unit: str,
        reason: str,
    ) -> Dict[str, Any]:
        return {
            "metric": metric,
            "organisation_id": "unknown",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "risk_level": "LOW",
            "risk_score": 0.10,
            "projected_breach": False,
            "estimated_time_to_breach_hours": None,
            "baseline": baseline,
            "warning_threshold": warning_thresh,
            "critical_threshold": critical_thresh,
            "unit": unit,
            "peak_projected_value": baseline,
            "peak_upper_bound": warning_thresh,
            "trajectory_slope_per_hour": 0.0,
            "explanation": f"Baseline heuristic estimation (Reason: {reason}).",
        }


future_anomaly_service = FutureAnomalyRiskService()
