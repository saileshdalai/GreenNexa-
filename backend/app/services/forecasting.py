"""
GreenNexa — AI/ML Time-Series Forecasting Service.

Provides short-term time-series forecasting for sustainable facility metrics
(energy, water) using statsmodels Exponential Smoothing / Holt-Winters algorithms.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session
from statsmodels.tsa.api import ExponentialSmoothing, Holt, SimpleExpSmoothing

from app.db.models import OrganisationSensorConfig, SensorReading
from app.schemas.forecast import ForecastPoint, ForecastResponse

logger = logging.getLogger(__name__)

# Supported forecast targets & horizons
SUPPORTED_SENSORS = {
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

HORIZON_MAP = {
    "6h": 6,
    "12h": 12,
    "24h": 24,
    "48h": 48,
    "72h": 72,
}

DEFAULT_UNITS = {
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


class ForecastingService:
    """
    Singleton service handling historical data extraction, preprocessing,
    time-series model fitting, confidence interval generation, and caching.
    """

    def __init__(self):
        # Cache structure: key -> (cached_at_datetime, ForecastResponse)
        self._cache: Dict[str, Tuple[datetime, ForecastResponse]] = {}
        self._cache_ttl_seconds = 300  # 5 minutes cache TTL

    def clear_cache(self) -> None:
        """Clear all cached forecast entries."""
        self._cache.clear()

    def _get_cache_key(
        self,
        organisation_id: str,
        sensor_type: str,
        horizon: str,
        mode: Optional[str],
        last_ts: Optional[datetime],
        count: int,
    ) -> str:
        ts_str = last_ts.isoformat() if last_ts else "none"
        mode_str = mode or "none"
        return f"{organisation_id}:{sensor_type}:{horizon}:{mode_str}:{ts_str}:{count}"

    def get_forecast(
        self,
        db: Session,
        organisation_id: str,
        sensor_type: str,
        horizon: str = "24h",
        window_days: int = 30,
        mode: Optional[str] = None,
    ) -> ForecastResponse:
        """
        Generate short-term time-series forecast for an organisation and sensor type.
        Supports 5 modes: default, last, 7d, 15d, 30d.
        """
        # 1. Validate metric support
        sensor_type_clean = sensor_type.lower().strip()
        if sensor_type_clean not in SUPPORTED_SENSORS:
            raise ValueError(
                f"Unsupported sensor type '{sensor_type}' for forecasting. "
                f"Currently supported: {', '.join(sorted(SUPPORTED_SENSORS))}."
            )

        # 2. Validate horizon
        horizon_clean = horizon.lower().strip()
        if horizon_clean not in HORIZON_MAP:
            raise ValueError(
                f"Unsupported horizon '{horizon}'. "
                f"Supported values: {', '.join(sorted(HORIZON_MAP.keys()))}."
            )
        horizon_hours = HORIZON_MAP[horizon_clean]

        # 3. Retrieve config for baselines & thresholds
        config = (
            db.query(OrganisationSensorConfig)
            .filter(OrganisationSensorConfig.organisation_id == organisation_id)
            .first()
        )
        data_source = config.data_source if config else "synthetic"
        from datetime import date
        current_sim_date = config.current_simulated_date if config and config.simulated_date else date(2026, 9, 20)
        
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
        cfg_dict = config.sensor_configs_dict.get(sensor_type_clean, {}) if config else {}
        if sensor_type_clean == "energy":
            baseline = config.energy_baseline if config else 100.0
            warning_thresh = config.energy_warning_threshold if config else 120.0
            critical_thresh = config.energy_critical_threshold if config else 140.0
        elif sensor_type_clean == "water":
            baseline = config.water_baseline if config else 50.0
            warning_thresh = config.water_warning_threshold if config else 60.0
            critical_thresh = config.water_critical_threshold if config else 70.0
        else:
            baseline = float(cfg_dict.get("baseline", DEFAULT_BASELINES.get(sensor_type_clean, 100.0)))
            warning_thresh = float(cfg_dict.get("warning_threshold", baseline * 1.15))
            critical_thresh = float(cfg_dict.get("critical_threshold", baseline * 1.30))

        # Determine unit
        unit = cfg_dict.get("unit") or DEFAULT_UNITS.get(sensor_type_clean, "units")

        # 4. Mode normalization
        mode_clean = (mode.lower().replace(" ", "").replace("days", "d") if mode else None)
        if mode_clean and mode_clean not in {"default", "last", "7d", "15d", "30d"}:
            mode_clean = "default"

        # 5. Query distinct available calendar days
        distinct_days_query = (
            db.query(func.date(SensorReading.timestamp))
            .filter(
                SensorReading.organisation_id == organisation_id,
                SensorReading.sensor_type == sensor_type_clean,
            )
            .distinct()
            .all()
        )
        available_days = len(distinct_days_query)

        # 6. Retrieve historical non-anomaly readings
        query = (
            db.query(SensorReading.timestamp, SensorReading.value, SensorReading.unit)
            .filter(
                SensorReading.organisation_id == organisation_id,
                SensorReading.sensor_type == sensor_type_clean,
                SensorReading.is_anomaly == False,
            )
            .order_by(SensorReading.timestamp.asc())
        )
        records = query.all()
        raw_count = len(records)
        last_ts = records[-1].timestamp if records else None
        current_val = round(float(records[-1].value), 2) if records else None

        if records and records[-1].unit:
            unit = records[-1].unit

        # Check cache hit
        cache_key = self._get_cache_key(organisation_id, sensor_type_clean, horizon_clean, mode_clean, last_ts, raw_count)
        if cache_key in self._cache:
            cached_time, cached_response = self._cache[cache_key]
            if (datetime.now(timezone.utc) - cached_time).total_seconds() < self._cache_ttl_seconds:
                return cached_response

        # 7. Check mode-specific availability criteria
        # Mode: 7d, 15d, 30d
        if mode_clean in {"7d", "15d", "30d"}:
            req_days = 7 if mode_clean == "7d" else (15 if mode_clean == "15d" else 30)
            if available_days < req_days:
                if mode is None:
                    raise ValueError("Insufficient historical data for forecasting.")
                resp = ForecastResponse(
                    organisation_id=organisation_id,
                    sensor_type=sensor_type_clean,
                    horizon=horizon_clean,
                    model="none",
                    data_source=data_source,
                    unit=unit,
                    generated_at=datetime.now(timezone.utc),
                    is_available=False,
                    status_message=f"{req_days}-day data not complete ({available_days}/{req_days} days available)",
                    mode=mode_clean,
                    selected_window=f"{req_days} Days",
                    available_days=available_days,
                    required_days=req_days,
                    current_value=current_val,
                    historical_comparison=f"Config baseline: {baseline:.2f} {unit}, Warning: {warning_thresh:.2f}, Critical: {critical_thresh:.2f}",
                    basis=f"Requires {req_days} full days of telemetry. Currently {available_days} days logged.",
                    assumptions="Reliable multi-day seasonality modeling requires full multi-day data span.",
                    forecast=[],
                )
                return resp

        # Mode: default (compares previous simulated day + current simulated day)
        if mode_clean == "default":
            # Check current simulated day readings count
            current_day_readings = [
                r for r in records
                if (r.timestamp.date() if hasattr(r.timestamp, "date") else r.timestamp) == current_sim_date
            ]
            if len(current_day_readings) < 5:
                if mode is None:
                    raise ValueError("Insufficient historical data for forecasting.")
                resp = ForecastResponse(
                    organisation_id=organisation_id,
                    sensor_type=sensor_type_clean,
                    horizon=horizon_clean,
                    model="none",
                    data_source=data_source,
                    unit=unit,
                    generated_at=datetime.now(timezone.utc),
                    is_available=False,
                    status_message="Forecast unavailable — insufficient current-day data.",
                    mode="default",
                    selected_window="Previous + Current Day",
                    available_days=available_days,
                    required_days=2,
                    current_value=current_val,
                    historical_comparison=f"Config baseline: {baseline:.2f} {unit}, Warning: {warning_thresh:.2f}, Critical: {critical_thresh:.2f}",
                    basis="Requires previous day baseline and sufficient intra-day progression (minimum 5 cycles) on current simulated day.",
                    assumptions="Day Change just occurred or current day simulation has not logged enough diurnal cycles.",
                    forecast=[],
                )
                return resp

        # Mode: last (sliding window)
        if mode_clean == "last":
            if raw_count < 10:
                if mode is None:
                    raise ValueError("Insufficient historical data for forecasting.")
                resp = ForecastResponse(
                    organisation_id=organisation_id,
                    sensor_type=sensor_type_clean,
                    horizon=horizon_clean,
                    model="none",
                    data_source=data_source,
                    unit=unit,
                    generated_at=datetime.now(timezone.utc),
                    is_available=False,
                    status_message="Forecast unavailable — insufficient data in recent sliding window.",
                    mode="last",
                    selected_window="Last 24h-48h",
                    available_days=available_days,
                    required_days=1,
                    current_value=current_val,
                    historical_comparison=f"Config baseline: {baseline:.2f} {unit}, Warning: {warning_thresh:.2f}, Critical: {critical_thresh:.2f}",
                    basis="Requires at least 10 recent observations within sliding window.",
                    assumptions="Recent trajectory projection requires minimum 10 non-anomaly data points.",
                    forecast=[],
                )
                return resp

        # 8. Check base record availability
        if not records or raw_count < 10:
            if mode is None:
                raise ValueError("Insufficient historical data for forecasting.")
            resp = ForecastResponse(
                organisation_id=organisation_id,
                sensor_type=sensor_type_clean,
                horizon=horizon_clean,
                model="none",
                data_source=data_source,
                unit=unit,
                generated_at=datetime.now(timezone.utc),
                is_available=False,
                status_message="Forecast unavailable — insufficient historical data.",
                mode=mode_clean or "default",
                selected_window=mode_clean or "default",
                available_days=available_days,
                required_days=1,
                current_value=current_val,
                historical_comparison=f"Config baseline: {baseline:.2f} {unit}",
                basis="Insufficient readings.",
                assumptions="N/A",
                forecast=[],
            )
            return resp

        timestamps = [r.timestamp for r in records]
        values = [r.value for r in records]

        df = pd.DataFrame({"timestamp": pd.to_datetime(timestamps), "value": values})
        df = df[np.isfinite(df["value"])]
        if df.empty:
            raise ValueError("Insufficient historical data for forecasting.")

        df = df.set_index("timestamp")
        # Hourly resampling with mean aggregation
        hourly_series = df["value"].resample("1h").mean()
        if hourly_series.isna().any():
            hourly_series = hourly_series.interpolate(method="time").ffill().bfill()
        hourly_series = hourly_series.dropna()

        # Check minimum observation requirement for legacy calls
        if len(hourly_series) < 24 and len(records) < 24 and mode is None:
            raise ValueError("Insufficient historical data for forecasting.")

        # Fallback to direct values if hourly series is too short but we have enough raw points
        if len(hourly_series) < 5:
            series_vals = np.array(values[-24:])
        else:
            series_vals = hourly_series.values

        # 9. Model Training & Point Predictions via ML Forecasting Service
        from app.services.forecasting_ml_service import forecast_ml_service

        last_hist_ts = timestamps[-1]
        if hasattr(last_hist_ts, "to_pydatetime"):
            last_hist_ts = last_hist_ts.to_pydatetime()
        if last_hist_ts.tzinfo is None:
            last_hist_ts = last_hist_ts.replace(tzinfo=timezone.utc)

        raw_df = pd.DataFrame({"timestamp": timestamps, "value": values, "is_anomaly": [False] * len(values)})
        ml_res = forecast_ml_service.forecast(
            historical_df=raw_df,
            horizon_hours=horizon_hours,
            metric=sensor_type_clean,
            organisation_id=organisation_id,
            baseline=baseline,
            warning_thresh=warning_thresh,
            critical_thresh=critical_thresh,
            last_timestamp=last_hist_ts,
        )

        if ml_res and ml_res.get("forecast"):
            forecast_points = ml_res["forecast"]
            model_name = ml_res["model"]
            model_family = ml_res.get("model_family", "machine_learning")
            metrics = ml_res.get("metrics")
            feature_importances = ml_res.get("feature_importances")
            basis_narrative = ml_res.get("basis") or f"{model_name} projection based on {len(values)} observations."
            assumptions_narrative = ml_res.get("assumptions") or "Assumes normal facility operating conditions."
        else:
            predictions, lower_bounds, upper_bounds, model_name = self._fit_and_predict(
                series_vals, horizon_hours
            )
            model_family = "statistical"
            metrics = None
            feature_importances = None
            start_hour = last_hist_ts.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            future_timestamps = [start_hour + timedelta(hours=i) for i in range(horizon_hours)]
            forecast_points = []
            for ts, pred, lb, ub in zip(future_timestamps, predictions, lower_bounds, upper_bounds):
                p_v = max(0.0, round(float(pred) if math.isfinite(pred) else 0.0, 2))
                l_v = max(0.0, round(float(lb) if math.isfinite(lb) else 0.0, 2))
                u_v = max(p_v, round(float(ub) if math.isfinite(ub) else p_v, 2))
                if l_v > p_v:
                    l_v = p_v
                if u_v < p_v:
                    u_v = p_v
                forecast_points.append(ForecastPoint(timestamp=ts, predicted_value=p_v, lower_bound=l_v, upper_bound=u_v))
            basis_narrative = f"{model_name.replace('_', ' ').title()} projection based on {len(series_vals)} observations."
            assumptions_narrative = "Assumes continuous facility operating conditions."

        # Build comparison narrative
        diff_pct = ((current_val - baseline) / baseline * 100.0) if current_val is not None and baseline > 0 else 0.0
        hist_comp = (
            f"Current observed value is {current_val:.2f} {unit} ({diff_pct:+.1f}% vs baseline {baseline:.2f} {unit}). "
            f"Thresholds: Warning {warning_thresh:.2f} {unit}, Critical {critical_thresh:.2f} {unit}."
        )

        response = ForecastResponse(
            organisation_id=organisation_id,
            sensor_type=sensor_type_clean,
            horizon=horizon_clean,
            model=model_name,
            model_family=model_family,
            metrics=metrics,
            feature_importances=feature_importances,
            data_source=data_source,
            unit=unit,
            generated_at=datetime.now(timezone.utc),
            is_available=True,
            status_message=None,
            mode=mode_clean or "default",
            selected_window=mode_clean or "default",
            available_days=available_days,
            required_days=7 if mode_clean == "7d" else (15 if mode_clean == "15d" else (30 if mode_clean == "30d" else 2)),
            current_value=current_val,
            historical_comparison=hist_comp,
            basis=basis_narrative,
            assumptions=assumptions_narrative,
            forecast=forecast_points,
        )

        # Store in cache
        self._cache[cache_key] = (datetime.now(timezone.utc), response)
        return response

    def _fit_and_predict(
        self, series: np.ndarray, steps: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, str]:
        """
        Fit statsmodels Exponential Smoothing and compute predictions and bounds.
        """
        n_obs = len(series)
        model_name = "exponential_smoothing"

        predictions: Optional[np.ndarray] = None
        fitted_values: Optional[np.ndarray] = None

        # Strategy 1: Exponential Smoothing with 24h seasonality if >= 48 observations
        if n_obs >= 48:
            try:
                model = ExponentialSmoothing(
                    series,
                    trend="add",
                    seasonal="add",
                    seasonal_periods=24,
                    initialization_method="estimated",
                )
                fit = model.fit(optimized=True)
                predictions = fit.forecast(steps)
                fitted_values = fit.fittedvalues
                model_name = "holt_winters_additive"
            except Exception as e:
                logger.warning(f"Holt-Winters 24h seasonal fit failed: {e}. Falling back to Holt linear.")

        # Strategy 2: Holt's Linear Trend if >= 24 observations
        if predictions is None and n_obs >= 24:
            try:
                model = Holt(series, initialization_method="estimated")
                fit = model.fit(optimized=True)
                predictions = fit.forecast(steps)
                fitted_values = fit.fittedvalues
                model_name = "holt_linear"
            except Exception as e:
                logger.warning(f"Holt linear fit failed: {e}. Falling back to Simple Exponential Smoothing.")

        # Strategy 3: Simple Exponential Smoothing
        if predictions is None:
            try:
                model = SimpleExpSmoothing(series, initialization_method="estimated")
                fit = model.fit(optimized=True)
                predictions = fit.forecast(steps)
                fitted_values = fit.fittedvalues
                model_name = "simple_exponential_smoothing"
            except Exception as e:
                logger.warning(f"Simple exp smoothing failed: {e}. Falling back to mean baseline.")
                mean_val = float(np.nanmean(series))
                predictions = np.full(steps, mean_val)
                fitted_values = np.full(n_obs, mean_val)
                model_name = "mean_baseline"

        # Calculate Residual Standard Error for 95% Confidence Bounds
        if fitted_values is not None and len(fitted_values) == n_obs:
            residuals = series - fitted_values
            std_err = float(np.nanstd(residuals))
        else:
            std_err = float(np.nanstd(series)) * 0.1

        if std_err == 0 or not math.isfinite(std_err):
            std_err = float(np.nanmean(series)) * 0.05

        # Step-dependent margin of error for 95% interval (1.96 * std_err * sqrt(1 + 0.03 * h))
        margins = np.array(
            [1.96 * std_err * math.sqrt(1.0 + 0.03 * (h + 1)) for h in range(steps)]
        )

        lower_bounds = np.maximum(0.0, predictions - margins)
        upper_bounds = predictions + margins

        return predictions, lower_bounds, upper_bounds, model_name


# Singleton instance
forecasting_service = ForecastingService()
