"""
GreenNexa — Machine Learning Priority & Escalation Risk Service.

Predicts anomaly escalation risk probability (0.0 to 1.0) using Scikit-Learn
LogisticRegression when sufficient historical outcome data exists (>= 30 records),
or an explainable calibrated risk model when data is sparse.
Complements and preserves the deterministic Priority Engine.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.linear_model import LogisticRegression
from sqlalchemy.orm import Session

from app.db.models import AnomalyRecord
from app.services.model_registry import model_registry

logger = logging.getLogger(__name__)


class PriorityMLService:
    """
    ML service for predicting anomaly escalation and criticality risk.
    """

    MIN_SAMPLES_FOR_ML = 30

    def __init__(self) -> None:
        self._model: Optional[LogisticRegression] = None

    def evaluate_escalation_risk(
        self,
        db: Session,
        organisation_id: str,
        anomaly: AnomalyRecord,
        baseline: float = 100.0,
        warning_thresh: float = 120.0,
        critical_thresh: float = 140.0,
    ) -> Dict[str, Any]:
        """
        Computes escalation probability (0.0 to 1.0) and risk factors for an anomaly.
        """
        val = float(anomaly.value) if anomaly.value is not None else baseline
        sev = str(anomaly.severity or "medium").lower()
        dev_pct = abs((val - baseline) / baseline * 100.0) if baseline > 0 else 0.0

        ts = anomaly.timestamp or datetime.now(timezone.utc)
        hour = float(ts.hour if hasattr(ts, "hour") else 12)
        dow = float(ts.weekday() if hasattr(ts, "weekday") else 0)
        is_weekend = 1.0 if dow >= 5 else 0.0

        # Feature vector
        feature_vector = np.array([
            dev_pct,
            val,
            float(anomaly.anomaly_score or 0.5),
            1.0 if sev == "critical" else (0.6 if sev == "high" else 0.3),
            hour,
            is_weekend,
        ]).reshape(1, -1)

        # 1. Attempt loading trained model from registry or train if >= 30 records exist
        model, meta = model_registry.load_model(f"priority_{organisation_id}")
        if model is None:
            model = self._train_model_if_sufficient(db, organisation_id)

        if model is not None:
            try:
                prob = float(model.predict_proba(feature_vector)[0][1])
                return {
                    "ml_risk_probability": round(prob, 3),
                    "model_used": "logistic_regression",
                    "data_sufficient": True,
                    "risk_factors": {
                        "deviation_pct": round(dev_pct, 1),
                        "severity_weight": 1.0 if sev == "critical" else (0.6 if sev == "high" else 0.3),
                        "anomaly_score": round(float(anomaly.anomaly_score or 0.5), 2),
                        "off_hours_factor": 1.2 if (hour < 8 or hour > 18 or is_weekend) else 1.0,
                    },
                }
            except Exception as e:
                logger.warning("Priority ML inference failed: %s", e)

        # 2. Transparent rule-weighted calibrated fallback
        sev_score = 0.85 if sev == "critical" else (0.60 if sev == "high" else 0.30)
        dev_score = min(1.0, dev_pct / 50.0) if dev_pct > 0 else 0.2
        time_mult = 1.15 if (hour < 8 or hour > 18 or is_weekend) else 1.0

        calibrated_prob = min(0.99, (sev_score * 0.5 + dev_score * 0.5) * time_mult)
        calibrated_prob = round(max(0.05, calibrated_prob), 3)

        return {
            "ml_risk_probability": calibrated_prob,
            "model_used": "calibrated_rule_weighted",
            "data_sufficient": False,
            "risk_factors": {
                "deviation_pct": round(dev_pct, 1),
                "severity_weight": sev_score,
                "off_hours_factor": time_mult,
            },
        }

    def _train_model_if_sufficient(
        self,
        db: Session,
        organisation_id: str,
    ) -> Optional[LogisticRegression]:
        """
        Trains a LogisticRegression model if at least 30 historical anomalies exist.
        """
        try:
            records = (
                db.query(AnomalyRecord)
                .filter(AnomalyRecord.organisation_id == organisation_id)
                .limit(200)
                .all()
            )
            if len(records) < self.MIN_SAMPLES_FOR_ML:
                return None

            X = []
            y = []
            for r in records:
                v = float(r.value or 0.0)
                s = str(r.severity or "medium").lower()
                is_crit = 1 if (s == "critical" or r.status == AnomalyRecord.STATUS_OPEN) else 0
                t = r.timestamp or datetime.now(timezone.utc)
                h = float(t.hour if hasattr(t, "hour") else 12)
                w = 1.0 if (hasattr(t, "weekday") and t.weekday() >= 5) else 0.0
                dev = abs(v - float(r.expected_max or v)) / max(float(r.expected_max or 1.0), 1.0) * 100.0

                X.append([dev, v, float(r.anomaly_score or 0.5), 1.0 if s == "critical" else 0.5, h, w])
                y.append(is_crit)

            if len(set(y)) < 2:
                return None

            clf = LogisticRegression(class_weight="balanced", random_state=42, max_iter=200)
            clf.fit(np.array(X), np.array(y))

            model_id = f"priority_{organisation_id}"
            model_registry.save_model(
                model=clf,
                model_id=model_id,
                metadata={
                    "model_type": "priority_risk",
                    "algorithm": "LogisticRegression",
                    "organisation_id": organisation_id,
                    "samples": len(X),
                },
            )
            return clf
        except Exception as e:
            logger.warning("Could not train Priority ML model: %s", e)
            return None


priority_ml_service = PriorityMLService()
