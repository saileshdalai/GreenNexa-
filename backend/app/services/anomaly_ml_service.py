"""
GreenNexa — Machine Learning Anomaly Detection Service.

Implements unsupervised anomaly detection using Scikit-Learn's IsolationForest,
combined with descriptive Z-score statistics and Super Admin baseline threshold rules.

Decision Policy:
  1. Priority 1 (Rule Breach): Critical / Warning configuration threshold exceeded.
  2. Priority 2 (Statistical Extreme): Absolute Z-score >= 3.0 (3 sigma deviation).
  3. Priority 3 (Multivariate ML Outlier): Isolation Forest flags outlier (score < 0)
     accompanied by elevated deviation (|Z| >= 1.8), catching subtle multi-feature anomalies.
  4. Fallback Cascade: If history < 24 points, gracefully falls back to Z-score + Rule threshold.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.services.ml_pipeline import ml_pipeline

logger = logging.getLogger(__name__)

MIN_ML_HISTORY_POINTS = 24
DEFAULT_CONTAMINATION = 0.05


class AnomalyMLService:
    """
    Service managing Scikit-Learn IsolationForest anomaly detection,
    feature preparation, model fitting, scoring, and explainability.
    """

    FEATURE_COLUMNS = [
        "current_value",
        "lag_1",
        "lag_2",
        "rolling_mean_6",
        "rolling_std_6",
        "hour_sin",
        "hour_cos",
        "baseline_dev_pct",
    ]

    def evaluate_reading(
        self,
        current_value: float,
        history_values: List[float],
        metric: str,
        unit: str = "",
        timestamp: Optional[datetime] = None,
        baseline: Optional[float] = None,
        warning_threshold_pct: Optional[float] = None,
        critical_threshold_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate a single sensor reading against historical distribution and configuration rules.
        """
        now = timestamp or datetime.now(timezone.utc)
        clean_history = [v for v in history_values if v is not None and math.isfinite(v)]
        n_history = len(clean_history)

        # Baseline & threshold fallback defaults
        base_val = baseline if (baseline is not None and baseline > 0) else (
            float(np.mean(clean_history)) if clean_history else current_value
        )
        warn_pct = warning_threshold_pct if warning_threshold_pct is not None else 15.0
        crit_pct = critical_threshold_pct if critical_threshold_pct is not None else 30.0

        dev_pct = abs((current_value - base_val) / base_val * 100.0) if base_val > 0 else 0.0
        direction = "above" if current_value > base_val else "below"
        unit_str = f" {unit}" if unit else ""

        # -------------------------------------------------------------------
        # 1. Rule-Based Evaluation (Super Admin Thresholds)
        # -------------------------------------------------------------------
        is_rule_critical = dev_pct > crit_pct
        is_rule_warning = dev_pct > warn_pct

        # -------------------------------------------------------------------
        # 2. Statistical Z-score Evaluation
        # -------------------------------------------------------------------
        mean_val = float(np.mean(clean_history)) if clean_history else current_value
        std_val = float(np.std(clean_history, ddof=1)) if len(clean_history) > 1 else 0.0

        if std_val < 1e-6:
            std_val = max(abs(mean_val) * 0.15, 1e-3)

        z_score = abs(current_value - mean_val) / std_val
        expected_min = round(mean_val - 1.5 * std_val, 2)
        expected_max = round(mean_val + 1.5 * std_val, 2)

        # -------------------------------------------------------------------
        # 3. Machine Learning Evaluation (Isolation Forest)
        # -------------------------------------------------------------------
        ml_evaluated = False
        is_ml_anomaly = False
        ml_anomaly_score = 0.0
        decision_fn_val = 0.0
        model_name = "zscore_threshold_fallback"

        if n_history >= MIN_ML_HISTORY_POINTS:
            try:
                # Build feature matrix for historical sliding windows
                X_train = []
                for i in range(12, n_history):
                    w_curr = clean_history[i]
                    w_hist = clean_history[:i]
                    feats = ml_pipeline.extract_single_observation_features(
                        current_val=w_curr,
                        recent_values=w_hist,
                        timestamp=now,
                        baseline=base_val,
                    )
                    X_train.append([feats[c] for c in self.FEATURE_COLUMNS])

                if len(X_train) >= 12:
                    X_train_arr = np.array(X_train)
                    # Train unsupervised Isolation Forest
                    clf = IsolationForest(
                        n_estimators=100,
                        contamination=DEFAULT_CONTAMINATION,
                        random_state=42,
                    )
                    clf.fit(X_train_arr)

                    # Extract feature vector for target observation
                    target_feats = ml_pipeline.extract_single_observation_features(
                        current_val=current_value,
                        recent_values=clean_history,
                        timestamp=now,
                        baseline=base_val,
                    )
                    X_target = np.array([[target_feats[c] for c in self.FEATURE_COLUMNS]])

                    pred = clf.predict(X_target)[0]  # -1 = anomaly, 1 = normal
                    decision_fn_val = float(clf.decision_function(X_target)[0])
                    # Map decision function to normalized [0, 1] anomaly score
                    # Lower decision function means more anomalous
                    ml_anomaly_score = round(float(np.clip(0.5 - decision_fn_val, 0.0, 1.0)), 4)
                    is_ml_anomaly = (pred == -1)
                    ml_evaluated = True
                    model_name = "isolation_forest"
            except Exception as ml_err:
                logger.warning("IsolationForest evaluation encountered error: %s. Safely falling back.", ml_err)

        # -------------------------------------------------------------------
        # 4. Decision Fusion Policy
        # -------------------------------------------------------------------
        severity = "NORMAL"
        detection_method = "NORMAL"
        reasons = []

        if is_rule_critical:
            severity = "CRITICAL"
            detection_method = "ISOLATION_FOREST_AND_RULE_CRITICAL" if is_ml_anomaly else "RULE_CRITICAL"
            reasons.append(
                f"Anomaly: Reading {current_value:.2f}{unit_str} breaches expected baseline range and is {direction} critical threshold "
                f"(±{crit_pct:.1f}%). Baseline: {base_val:.2f}{unit_str}, Deviation: {dev_pct:.1f}%."
            )
            if is_ml_anomaly:
                reasons.append(f"Confirmed by multivariate Isolation Forest (anomaly score: {ml_anomaly_score:.3f}).")
        elif is_rule_warning:
            severity = "HIGH"
            detection_method = "ISOLATION_FOREST_AND_RULE_WARNING" if is_ml_anomaly else "RULE_WARNING"
            reasons.append(
                f"Anomaly: Reading {current_value:.2f}{unit_str} breaches expected baseline range and is {direction} warning threshold "
                f"(±{warn_pct:.1f}%). Baseline: {base_val:.2f}{unit_str}, Deviation: {dev_pct:.1f}%."
            )
            if is_ml_anomaly:
                reasons.append(f"Confirmed by multivariate Isolation Forest (anomaly score: {ml_anomaly_score:.3f}).")
        elif z_score >= 3.0:
            severity = "CRITICAL"
            detection_method = "STATISTICAL_CRITICAL"
            reasons.append(
                f"Anomaly: Reading {current_value:.2f}{unit_str} breaches expected baseline range and severely deviates from historical mean "
                f"{mean_val:.2f}{unit_str} (Z-score: {z_score:.2f})."
            )
        elif z_score >= 2.5:
            severity = "HIGH"
            detection_method = "STATISTICAL_HIGH"
            reasons.append(
                f"Anomaly: Reading {current_value:.2f}{unit_str} breaches expected baseline range and deviates significantly from expected range "
                f"({expected_min:.2f}–{expected_max:.2f}{unit_str}, Z-score: {z_score:.2f})."
            )
        elif is_ml_anomaly:
            severity = "HIGH" if z_score >= 1.5 else "MEDIUM"
            detection_method = "ML_ISOLATION_FOREST"
            reasons.append(
                f"Anomaly: Multivariate Isolation Forest detected an abnormal multidimensional pattern "
                f"(anomaly score: {ml_anomaly_score:.3f}, Z-score: {z_score:.2f})."
            )
        elif z_score >= 2.0:
            severity = "MEDIUM"
            detection_method = "STATISTICAL_MEDIUM"
            reasons.append(
                f"Anomaly: Reading {current_value:.2f}{unit_str} exhibits noticeable statistical deviation (Z-score: {z_score:.2f})."
            )
        elif z_score >= 1.5:
            severity = "LOW"
            detection_method = "STATISTICAL_LOW"
            reasons.append(
                f"Anomaly: Reading {current_value:.2f}{unit_str} exhibits slight statistical deviation (Z-score: {z_score:.2f})."
            )
        elif is_ml_anomaly:
            # Subtle ML anomaly without high univariate z-score
            severity = "LOW"
            detection_method = "ML_ISOLATION_FOREST_SUBTLE"
            reasons.append(
                f"Anomaly: Isolation Forest identified atypical behavioral pattern relative to learned diurnal baseline "
                f"(ML score: {ml_anomaly_score:.2f})."
            )
        else:
            severity = "NORMAL"
            detection_method = "NORMAL"
            reasons.append(
                f"Reading {current_value:.2f}{unit_str} is within normal operational range."
            )

        is_anomaly = (severity != "NORMAL")
        combined_score = round(
            float(np.clip(max(z_score / 4.0, ml_anomaly_score if ml_evaluated else 0.0, dev_pct / 100.0), 0.0, 1.0)),
            4,
        )

        return {
            "is_anomaly": is_anomaly,
            "severity": severity,
            "detection_method": detection_method,
            "anomaly_score": combined_score,
            "z_score": round(z_score, 2),
            "ml_anomaly_score": ml_anomaly_score,
            "ml_evaluated": ml_evaluated,
            "model_name": model_name,
            "expected_min": expected_min,
            "expected_max": expected_max,
            "baseline": round(base_val, 2),
            "deviation_pct": round(dev_pct, 1),
            "reason": " ".join(reasons),
            "history_points_count": n_history,
            "features_analyzed": self.FEATURE_COLUMNS if ml_evaluated else ["value", "z_score"],
        }


anomaly_ml_service = AnomalyMLService()
