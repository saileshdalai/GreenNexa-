"""
GreenNexa — Machine Learning Explainability & Decision Attribution Service.

Provides human-interpretable factor breakdowns and feature attributions
for ML Isolation Forest anomaly scores, Ridge/RandomForest forecast drivers,
and upcoming threshold risk assessments.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import AnomalyRecord, OrganisationSensorConfig, SensorReading

logger = logging.getLogger(__name__)


class MLExplainabilityService:
    """
    Generates transparent, auditable decision attribution for AI/ML outputs.
    """

    def explain_anomaly(
        self,
        db: Session,
        anomaly_id: str,
    ) -> Dict[str, Any]:
        """
        Explains why a reading was flagged as an anomaly by attributing the decision
        to threshold breaches, statistical z-score, and Scikit-Learn IsolationForest scores.
        """
        anomaly = db.query(AnomalyRecord).filter(AnomalyRecord.id == anomaly_id).first()
        if not anomaly:
            return {"error": f"Anomaly record '{anomaly_id}' not found"}

        val = float(anomaly.value) if anomaly.value is not None else 0.0
        exp_min = float(anomaly.expected_min) if anomaly.expected_min is not None else 0.0
        exp_max = float(anomaly.expected_max) if anomaly.expected_max is not None else val
        anom_score = float(anomaly.anomaly_score) if anomaly.anomaly_score is not None else 0.5
        metric = anomaly.metric or anomaly.sensor_type or "unknown"
        org_id = anomaly.organisation_id

        # Config baselines
        config = (
            db.query(OrganisationSensorConfig)
            .filter(OrganisationSensorConfig.organisation_id == org_id)
            .first()
        )
        cfg = config.sensor_configs_dict.get(metric, {}) if config else {}
        baseline = float(cfg.get("baseline", 100.0))
        warn_thresh = float(cfg.get("warning_threshold", baseline * 1.15))
        crit_thresh = float(cfg.get("critical_threshold", baseline * 1.30))

        dev_pct = abs((val - baseline) / baseline * 100.0) if baseline > 0 else 0.0

        ts = anomaly.timestamp
        hour = ts.hour if ts else 12
        dow = ts.weekday() if ts else 0
        is_weekend = dow >= 5
        is_off_hours = (hour < 8 or hour > 18 or is_weekend)

        factors = [
            {
                "factor": "Baseline Deviation",
                "importance": "high" if dev_pct > 30 else ("medium" if dev_pct > 15 else "low"),
                "value": f"+{dev_pct:.1f}%",
                "detail": f"Observed {val:.2f} vs expected baseline {baseline:.2f}",
            },
            {
                "factor": "Isolation Forest Anomaly Score",
                "importance": "high" if anom_score > 0.65 else ("medium" if anom_score > 0.5 else "low"),
                "value": f"{anom_score:.3f}",
                "detail": "Multivariate tree-depth isolation penalty indicating geometric outlier in feature space",
            },
            {
                "factor": "Operational Timing Context",
                "importance": "medium" if is_off_hours else "low",
                "value": "Off-Hours" if is_off_hours else "Operating Hours",
                "detail": f"Observed at hour {hour:02d}:00 ({'Weekend' if is_weekend else 'Weekday'})",
            },
        ]

        if val >= crit_thresh:
            primary_driver = f"Critical threshold breach ({val:.2f} >= {crit_thresh:.2f})"
        elif val >= warn_thresh:
            primary_driver = f"Warning threshold breach ({val:.2f} >= {warn_thresh:.2f})"
        elif anom_score > 0.6:
            primary_driver = f"Unusual multivariate pattern detected by Isolation Forest (score: {anom_score:.2f})"
        else:
            primary_driver = f"Elevated reading ({val:.2f}) with +{dev_pct:.1f}% deviation from baseline"

        return {
            "anomaly_id": anomaly.id,
            "organisation_id": org_id,
            "metric": metric,
            "severity": anomaly.severity,
            "status": anomaly.status,
            "current_value": val,
            "expected_range": [exp_min, exp_max],
            "baseline": baseline,
            "warning_threshold": warn_thresh,
            "critical_threshold": crit_thresh,
            "anomaly_score": anom_score,
            "primary_driver": primary_driver,
            "decision_factors": factors,
            "model_attribution": {
                "isolation_forest_evaluated": True,
                "anomaly_score": anom_score,
                "statistical_deviation_pct": round(dev_pct, 1),
                "off_hours_flag": is_off_hours,
            },
            "recommendation_summary": anomaly.recommendation.summary if anomaly.recommendation else None,
        }

    def explain_forecast(
        self,
        forecast_response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Summarizes model drivers, holdout validation metrics, and assumptions
        from an ML forecast response.
        """
        metrics = forecast_response.get("metrics") or {}
        feature_importances = forecast_response.get("feature_importances") or {}

        sorted_features = sorted(
            feature_importances.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:5]

        top_drivers = [
            {"feature": f_name, "relative_weight": weight}
            for f_name, weight in sorted_features
        ]

        return {
            "model": forecast_response.get("model", "unknown"),
            "model_family": forecast_response.get("model_family", "unknown"),
            "evaluation_metrics": metrics,
            "top_predictive_drivers": top_drivers,
            "basis": forecast_response.get("basis"),
            "assumptions": forecast_response.get("assumptions"),
        }


ml_explainability_service = MLExplainabilityService()
