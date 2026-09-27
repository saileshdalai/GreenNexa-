"""
GreenNexa — Machine Learning Time-Series Forecasting Service.

Implements genuine Scikit-Learn regression forecasting (Ridge & RandomForestRegressor)
with ML feature engineering (lags, rolling statistics, calendar encodings),
chronological holdout backtesting, expanding confidence intervals,
and safe multi-level fallback cascade.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge

from app.schemas.forecast import ForecastPoint
from app.services.ml_pipeline import MLDataPipeline, ml_data_pipeline
from app.services.model_evaluation import model_evaluation_service
from app.services.model_registry import model_registry

logger = logging.getLogger(__name__)

ALL_SUPPORTED_SENSORS = {
    "energy",
    "water",
    "waste",
    "temperature",
    "indoor_temperature",
    "humidity",
    "co2",
    "air_quality",
    "traffic",
    "parking",
    "assets",
    "safety",
    "climate",
}

DEFAULT_METRIC_UNITS = {
    "energy": "kWh",
    "water": "L",
    "waste": "%",
    "temperature": "°C",
    "indoor_temperature": "°C",
    "humidity": "%",
    "co2": "ppm",
    "air_quality": "AQI",
    "traffic": "veh/h",
    "parking": "%",
    "assets": "units",
    "safety": "score",
    "climate": "score",
}


class ForecastMLService:
    """
    Production-grade Scikit-Learn forecasting service for building facilities.
    """

    MIN_ML_SAMPLES = 24
    MIN_EXP_SMOOTH_SAMPLES = 12
    MIN_MOVING_AVG_SAMPLES = 4

    def __init__(self, pipeline: Optional[MLDataPipeline] = None) -> None:
        self.pipeline = pipeline or ml_data_pipeline

    def forecast(
        self,
        historical_df: pd.DataFrame,
        horizon_hours: int = 24,
        metric: str = "energy",
        organisation_id: str = "default",
        baseline: float = 100.0,
        warning_thresh: float = 120.0,
        critical_thresh: float = 140.0,
        last_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Executes the hierarchical forecasting cascade:
        1. Scikit-Learn Regression (Ridge / RandomForest) if >= 24 historical points
        2. Statsmodels Exponential Smoothing if between 12 and 23 points
        3. Weighted Moving Average with diurnal cycle if between 4 and 11 points
        4. Safe baseline fallback if < 4 points
        """
        metric_clean = metric.lower().strip()
        unit = DEFAULT_METRIC_UNITS.get(metric_clean, "")

        # Guard: empty or invalid DataFrame
        if historical_df is None or historical_df.empty or "value" not in historical_df.columns:
            return self._build_insufficient_data_response(
                metric=metric_clean,
                unit=unit,
                horizon_hours=horizon_hours,
                baseline=baseline,
                last_timestamp=last_timestamp,
                reason="No historical data found in selected window",
            )

        # Preprocess through ML Pipeline: resample hourly, filter anomalies, forward-fill gaps
        clean_df = self.pipeline.preprocess_series(
            historical_df,
            timestamp_col="timestamp" if "timestamp" in historical_df.columns else None,
            value_col="value",
            resample_freq="1h",
            filter_anomalies=True,
            anomaly_col="is_anomaly" if "is_anomaly" in historical_df.columns else None,
        )

        n_samples = len(clean_df)
        if last_timestamp is None and not clean_df.empty:
            last_timestamp = clean_df.index[-1].to_pydatetime()
        elif last_timestamp is None:
            last_timestamp = datetime.now(timezone.utc)

        # ------------------------------------------------------------------
        # Level 1: ML Model (Ridge / Random Forest) when n_samples >= 24
        # ------------------------------------------------------------------
        if n_samples >= self.MIN_ML_SAMPLES:
            try:
                ml_res = self._forecast_with_ml(
                    clean_df=clean_df,
                    horizon_hours=horizon_hours,
                    metric=metric_clean,
                    unit=unit,
                    organisation_id=organisation_id,
                    last_timestamp=last_timestamp,
                )
                if ml_res is not None:
                    return ml_res
            except Exception as ml_err:
                logger.warning("ML Regression failed, cascading to statistical model: %s", ml_err)

        # ------------------------------------------------------------------
        # Level 2: Statsmodels Exponential Smoothing when 12 <= n_samples < 24
        # ------------------------------------------------------------------
        if n_samples >= self.MIN_EXP_SMOOTH_SAMPLES:
            try:
                exp_res = self._forecast_with_exp_smoothing(
                    clean_df=clean_df,
                    horizon_hours=horizon_hours,
                    metric=metric_clean,
                    unit=unit,
                    last_timestamp=last_timestamp,
                )
                if exp_res is not None:
                    return exp_res
            except Exception as exp_err:
                logger.warning("Exponential smoothing failed, cascading to moving average: %s", exp_err)

        # ------------------------------------------------------------------
        # Level 3: Weighted Moving Average when 4 <= n_samples < 12
        # ------------------------------------------------------------------
        if n_samples >= self.MIN_MOVING_AVG_SAMPLES:
            try:
                wma_res = self._forecast_with_moving_average(
                    clean_df=clean_df,
                    horizon_hours=horizon_hours,
                    metric=metric_clean,
                    unit=unit,
                    last_timestamp=last_timestamp,
                )
                if wma_res is not None:
                    return wma_res
            except Exception as wma_err:
                logger.warning("Moving average forecast failed, cascading to baseline: %s", wma_err)

        # ------------------------------------------------------------------
        # Level 4: Baseline fallback for insufficient data (< 4 points)
        # ------------------------------------------------------------------
        return self._build_insufficient_data_response(
            metric=metric_clean,
            unit=unit,
            horizon_hours=horizon_hours,
            baseline=baseline,
            last_timestamp=last_timestamp,
            reason=f"Insufficient clean historical samples ({n_samples} observed, minimum 4 required for statistical estimation)",
        )

    def _forecast_with_ml(
        self,
        clean_df: pd.DataFrame,
        horizon_hours: int,
        metric: str,
        unit: str,
        organisation_id: str,
        last_timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """
        Builds feature matrix, splits chronologically, trains Ridge / RandomForest,
        evaluates holdout metrics, and generates iterative future predictions.
        """
        # Create supervised features (lags, rolling stats, calendar encodings)
        feature_df = self.pipeline.build_supervised_features(
            clean_df,
            value_col="value",
            lags=[1, 2, 3, 24, 48] if len(clean_df) >= 72 else [1, 2, 3, 24] if len(clean_df) >= 30 else [1, 2, 3],
            rolling_windows=[6, 24] if len(clean_df) >= 36 else [6] if len(clean_df) >= 12 else [],
        )

        if len(feature_df) < 15:
            return None

        feature_cols = [c for c in feature_df.columns if c != "value"]
        X = feature_df[feature_cols].values
        y = feature_df["value"].values

        # Chronological holdout evaluation
        X_train, X_test, y_train, y_test = model_evaluation_service.chronological_train_test_split(
            X, y, test_ratio=0.2, min_test_samples=5
        )

        # Select model: Ridge if small dataset (< 60 samples), RandomForest if larger
        use_rf = len(X_train) >= 60
        model_name = "RandomForestRegressor" if use_rf else "RidgeRegressor"
        model = (
            RandomForestRegressor(n_estimators=60, max_depth=6, random_state=42)
            if use_rf
            else Ridge(alpha=1.0)
        )

        model.fit(X_train, y_train)

        # Evaluate on chronological holdout
        if len(y_test) >= 5:
            y_pred_test = model.predict(X_test)
            metrics = model_evaluation_service.evaluate_regression(
                y_true=y_test, y_pred=y_pred_test, model_name=model_name
            )
            residuals = y_test - y_pred_test
            residual_std = float(np.std(residuals)) if len(residuals) > 1 else 1.0
        else:
            # Whole dataset fit
            residuals = y - model.predict(X)
            residual_std = float(np.std(residuals)) if len(residuals) > 1 else 1.0
            metrics = {
                "model_name": model_name,
                "evaluation_method": "chronological_holdout",
                "sample_count": len(y_test),
                "is_evaluated": False,
                "status": "insufficient_holdout_samples",
                "mae": None,
                "rmse": None,
                "r2": None,
                "mape": None,
            }

        # Retrain on full dataset for maximum future accuracy
        full_model = (
            RandomForestRegressor(n_estimators=60, max_depth=6, random_state=42)
            if use_rf
            else Ridge(alpha=1.0)
        )
        full_model.fit(X, y)

        # Feature importances / coefficients
        feature_importance_map: Dict[str, float] = {}
        if use_rf and hasattr(full_model, "feature_importances_"):
            for f_name, imp in zip(feature_cols, full_model.feature_importances_):
                feature_importance_map[f_name] = round(float(imp), 4)
        elif hasattr(full_model, "coef_"):
            for f_name, coef in zip(feature_cols, full_model.coef_):
                feature_importance_map[f_name] = round(float(abs(coef)), 4)

        # Save to Model Registry
        model_id = f"forecast_{organisation_id}_{metric}_{horizon_hours}h"
        model_registry.save_model(
            model=full_model,
            model_id=model_id,
            metadata={
                "model_type": "forecasting",
                "algorithm": model_name,
                "metric": metric,
                "organisation_id": organisation_id,
                "horizon_hours": horizon_hours,
                "metrics": metrics,
                "feature_count": len(feature_cols),
                "trained_samples": len(X),
            },
        )

        # Generate future horizon steps
        forecast_points = []
        recent_values = list(clean_df["value"].values)
        curr_dt = last_timestamp

        for step in range(1, horizon_hours + 1):
            curr_dt = curr_dt + timedelta(hours=1)
            future_feats = self.pipeline.generate_future_feature_row(
                history_values=recent_values,
                target_dt=curr_dt,
                feature_names=feature_cols,
            )
            pred_val = float(full_model.predict(future_feats)[0])
            pred_val = self._apply_physical_bounds(pred_val, metric)

            # Expanding uncertainty bounds with horizon: 1.96 * std * sqrt(1 + step / 24)
            uncertainty_scale = math.sqrt(1.0 + (step / 24.0))
            half_width = 1.96 * max(residual_std, 0.1) * uncertainty_scale
            lower = self._apply_physical_bounds(pred_val - half_width, metric)
            upper = self._apply_physical_bounds(pred_val + half_width, metric)

            forecast_points.append(
                ForecastPoint(
                    timestamp=curr_dt,
                    predicted_value=round(pred_val, 2),
                    lower_bound=round(lower, 2),
                    upper_bound=round(upper, 2),
                )
            )
            recent_values.append(pred_val)

        return {
            "model": f"scikit_learn_{model_name.lower()}",
            "model_family": "machine_learning",
            "is_available": True,
            "status_message": f"Generated using Scikit-Learn {model_name} with ML feature engineering",
            "metrics": metrics,
            "feature_importances": feature_importance_map,
            "forecast": forecast_points,
            "basis": f"Trained on {len(X)} historical points with {len(feature_cols)} time-series features (lags, rolling averages, calendar sine/cosine)",
            "assumptions": "Assumes historical diurnal facility occupancy and seasonal patterns hold over projection horizon.",
        }

    def _forecast_with_exp_smoothing(
        self,
        clean_df: pd.DataFrame,
        horizon_hours: int,
        metric: str,
        unit: str,
        last_timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Level 2 fallback: statsmodels Holt / Exponential Smoothing."""
        from statsmodels.tsa.api import Holt, SimpleExpSmoothing

        series = clean_df["value"].values
        n = len(series)
        curr_dt = last_timestamp

        try:
            if n >= 18:
                model = Holt(series, initialization_method="estimated").fit()
            else:
                model = SimpleExpSmoothing(series, initialization_method="estimated").fit()

            preds = model.forecast(horizon_hours)
            residuals = series - model.fittedvalues
            residual_std = float(np.std(residuals)) if len(residuals) > 1 else 1.0

            forecast_points = []
            for step, p in enumerate(preds, start=1):
                curr_dt = curr_dt + timedelta(hours=1)
                val = self._apply_physical_bounds(float(p), metric)
                uncertainty_scale = math.sqrt(1.0 + (step / 24.0))
                half_width = 1.96 * max(residual_std, 0.1) * uncertainty_scale
                lower = self._apply_physical_bounds(val - half_width, metric)
                upper = self._apply_physical_bounds(val + half_width, metric)

                forecast_points.append(
                    ForecastPoint(
                        timestamp=curr_dt,
                        predicted_value=round(val, 2),
                        lower_bound=round(lower, 2),
                        upper_bound=round(upper, 2),
                    )
                )

            return {
                "model": "exponential_smoothing",
                "model_family": "statistical",
                "is_available": True,
                "status_message": "Generated using statsmodels Exponential Smoothing (statistical fallback)",
                "metrics": {
                    "evaluation_method": "in_sample_residuals",
                    "sample_count": n,
                    "mae": round(float(np.mean(np.abs(residuals))), 4),
                    "rmse": round(float(np.sqrt(np.mean(residuals**2))), 4),
                    "r2": None,
                },
                "feature_importances": {},
                "forecast": forecast_points,
                "basis": f"Exponential smoothing fit over {n} points",
                "assumptions": "Statistical trend projection without external covariates.",
            }
        except Exception as e:
            logger.warning("Exponential smoothing fit failed: %s", e)
            return None

    def _forecast_with_moving_average(
        self,
        clean_df: pd.DataFrame,
        horizon_hours: int,
        metric: str,
        unit: str,
        last_timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Level 3 fallback: weighted moving average."""
        series = clean_df["value"].values
        n = len(series)
        weights = np.linspace(0.5, 1.0, n)
        w_avg = float(np.sum(series * weights) / np.sum(weights))
        series_std = float(np.std(series)) if n > 1 else max(w_avg * 0.1, 1.0)

        forecast_points = []
        curr_dt = last_timestamp

        for step in range(1, horizon_hours + 1):
            curr_dt = curr_dt + timedelta(hours=1)
            # subtle diurnal wave if live metric
            hour = curr_dt.hour
            diurnal_factor = 1.0 + 0.08 * math.sin((hour - 8) * math.pi / 12.0)
            val = self._apply_physical_bounds(w_avg * diurnal_factor, metric)
            half_width = 1.96 * series_std * math.sqrt(1.0 + step / 24.0)
            lower = self._apply_physical_bounds(val - half_width, metric)
            upper = self._apply_physical_bounds(val + half_width, metric)

            forecast_points.append(
                ForecastPoint(
                    timestamp=curr_dt,
                    predicted_value=round(val, 2),
                    lower_bound=round(lower, 2),
                    upper_bound=round(upper, 2),
                )
            )

        return {
            "model": "weighted_moving_average",
            "model_family": "heuristic_statistical",
            "is_available": True,
            "status_message": "Generated using Weighted Moving Average (insufficient data for full ML)",
            "metrics": {
                "evaluation_method": "sample_variance",
                "sample_count": n,
                "mae": None,
                "rmse": round(series_std, 4),
                "r2": None,
            },
            "feature_importances": {},
            "forecast": forecast_points,
            "basis": f"Weighted moving average computed over {n} recent data points",
            "assumptions": "Flat trend assumption with standard diurnal scaling.",
        }

    def _build_insufficient_data_response(
        self,
        metric: str,
        unit: str,
        horizon_hours: int,
        baseline: float,
        last_timestamp: Optional[datetime],
        reason: str,
    ) -> Dict[str, Any]:
        """Safe fallback response when data is insufficient (< 4 points)."""
        curr_dt = last_timestamp or datetime.now(timezone.utc)
        forecast_points = []
        for step in range(1, horizon_hours + 1):
            curr_dt = curr_dt + timedelta(hours=1)
            forecast_points.append(
                ForecastPoint(
                    timestamp=curr_dt,
                    predicted_value=round(baseline, 2),
                    lower_bound=round(max(0.0, baseline * 0.85), 2),
                    upper_bound=round(baseline * 1.15, 2),
                )
            )

        return {
            "model": "baseline_fallback",
            "model_family": "rule_heuristic",
            "is_available": False,
            "status_message": reason,
            "metrics": None,
            "feature_importances": {},
            "forecast": forecast_points,
            "basis": "Organisation configuration baseline fallback",
            "assumptions": "Static baseline applied due to insufficient historical readings.",
        }

    def _apply_physical_bounds(self, value: float, metric: str) -> float:
        """Enforces realistic physical domain boundaries."""
        if not math.isfinite(value):
            return 0.0

        # Non-negative metrics
        if metric in {"energy", "water", "waste", "co2", "air_quality", "traffic", "parking", "assets", "safety"}:
            value = max(0.0, value)

        # Percentage metrics capped at 100%
        if metric in {"humidity", "waste", "parking"}:
            value = min(100.0, value)

        return value


forecast_ml_service = ForecastMLService()
