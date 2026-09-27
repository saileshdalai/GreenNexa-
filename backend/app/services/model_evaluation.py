"""
GreenNexa — Machine Learning Model Evaluation Service.

Computes genuine chronological holdout backtesting metrics (MAE, RMSE, R², MAPE)
with zero future data leakage. Enforces strict sample guards to prevent fake metrics.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)


class ModelEvaluationService:
    """
    Evaluates ML models using strict chronological holdout splits and computes
    transparent statistical and machine learning accuracy metrics.
    """

    MIN_HOLDOUT_SAMPLES = 5

    def chronological_train_test_split(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_ratio: float = 0.2,
        min_test_samples: int = 5,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Chronological split for time-series: trains on earlier timestamps, tests on later timestamps.
        Never shuffles or leaks future information.
        """
        n_samples = len(X)
        if n_samples < (min_test_samples + 5):
            return X, np.empty((0, X.shape[1] if X.ndim > 1 else 0)), y, np.empty((0,))

        n_test = max(min_test_samples, int(n_samples * test_ratio))
        n_train = n_samples - n_test

        X_train, X_test = X[:n_train], X[n_train:]
        y_train, y_test = y[:n_train], y[n_train:]

        return X_train, X_test, y_train, y_test

    def evaluate_regression(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str = "ML Regression Model",
    ) -> Dict[str, Any]:
        """
        Calculates MAE, RMSE, R2, and MAPE on genuine holdout data.
        Returns explicit insufficient data indicators when sample size is too small.
        """
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)

        valid_mask = np.isfinite(y_true) & np.isfinite(y_pred)
        y_true = y_true[valid_mask]
        y_pred = y_pred[valid_mask]

        sample_count = len(y_true)

        if sample_count < self.MIN_HOLDOUT_SAMPLES:
            return {
                "model_name": model_name,
                "evaluation_method": "chronological_holdout",
                "sample_count": sample_count,
                "is_evaluated": False,
                "status": "insufficient_holdout_samples",
                "mae": None,
                "rmse": None,
                "r2": None,
                "mape": None,
                "accuracy_percentage": None,
            }

        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))

        # R2 score can be negative if model performs worse than mean baseline
        try:
            r2 = float(r2_score(y_true, y_pred))
            if not math.isfinite(r2):
                r2 = 0.0
        except Exception:
            r2 = 0.0

        # MAPE with zero protection
        non_zero = y_true != 0
        if np.any(non_zero):
            mape = float(np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100.0)
            mape = round(min(mape, 100.0), 2)
            accuracy_pct = round(max(0.0, 100.0 - mape), 2)
        else:
            mape = None
            accuracy_pct = None

        return {
            "model_name": model_name,
            "evaluation_method": "chronological_holdout",
            "sample_count": sample_count,
            "is_evaluated": True,
            "status": "evaluated_successfully",
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "r2": round(r2, 4),
            "mape": mape,
            "accuracy_percentage": accuracy_pct,
        }

    def evaluate_anomaly_scores(
        self,
        y_true: List[bool],
        y_pred: List[bool],
    ) -> Dict[str, Any]:
        """
        Evaluate classification metrics (Precision, Recall, F1) for anomaly detection
        when ground-truth or simulated anomaly labels exist.
        """
        y_true_arr = np.array(y_true, dtype=bool)
        y_pred_arr = np.array(y_pred, dtype=bool)

        tp = int(np.sum(y_true_arr & y_pred_arr))
        fp = int(np.sum(~y_true_arr & y_pred_arr))
        fn = int(np.sum(y_true_arr & ~y_pred_arr))
        tn = int(np.sum(~y_true_arr & ~y_pred_arr))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        return {
            "evaluation_method": "classification_matrix",
            "sample_count": len(y_true),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }


model_evaluation_service = ModelEvaluationService()
