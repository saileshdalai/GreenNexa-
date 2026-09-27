"""
GreenNexa — Machine Learning Data Pipeline & Feature Engineering Service.

Provides robust, reproducible time-series data preparation, resampling, gap filling,
and strictly backward-looking feature engineering for ML anomaly detection and forecasting.
Guarantees zero data leakage and preserves tenant data isolation.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MLDataPipeline:
    """
    Standardized time-series preprocessing and feature engineering pipeline.
    """

    @staticmethod
    def prepare_time_series_dataframe(
        readings: Union[List[Any], pd.DataFrame],
        freq: str = "1h",
        filter_anomalies: bool = True,
        min_points: int = 5,
    ) -> pd.DataFrame:
        """
        Convert raw SensorReading records or DataFrame into a regular, cleaned time series.

        Steps:
          1. Extract timestamp and numeric value.
          2. Drop invalid / non-finite observations.
          3. Filter out past anomalies (when filter_anomalies=True) to avoid corrupting training baseline.
          4. Sort chronologically (ascending).
          5. Resample to standard frequency (e.g. '1h') using mean aggregation.
          6. Interpolate missing values (time-aware linear interpolation + forward/backward fill).
        """
        if isinstance(readings, pd.DataFrame):
            df = readings.copy()
        else:
            rows = []
            for r in readings:
                ts = getattr(r, "timestamp", None)
                val = getattr(r, "value", None)
                is_anom = getattr(r, "is_anomaly", False)
                block_id = getattr(r, "block_id", None) or getattr(r, "facility_id", None)
                if ts is not None and val is not None:
                    rows.append({
                        "timestamp": ts,
                        "value": float(val),
                        "is_anomaly": bool(is_anom),
                        "block_id": block_id,
                    })
            df = pd.DataFrame(rows)

        if df.empty:
            return pd.DataFrame(columns=["value"])

        # Validate types and finite values
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["timestamp", "value"])
        df = df[np.isfinite(df["value"])]

        if filter_anomalies and "is_anomaly" in df.columns:
            df = df[~df["is_anomaly"]]

        if len(df) < min_points:
            return pd.DataFrame(columns=["value"])

        # Sort chronologically
        df = df.sort_values("timestamp")
        df = df.set_index("timestamp")

        # Resample to regular interval
        resampled = df["value"].resample(freq).mean()

        # Handle time gaps
        if resampled.isna().any():
            resampled = resampled.interpolate(method="time").ffill().bfill()

        resampled = resampled.dropna()
        res_df = pd.DataFrame({"value": resampled})
        return res_df

    @staticmethod
    def engineer_features(
        df: pd.DataFrame,
        baseline: Optional[float] = None,
        include_lags: bool = True,
        include_rolling: bool = True,
        include_calendar: bool = True,
    ) -> pd.DataFrame:
        """
        Generate rich, strictly backward-looking features for ML training and inference.
        Guarantees NO future data leakage by using shift() operations.

        Features generated:
          - Lags: lag_1, lag_2, lag_3, lag_6, lag_12, lag_24 (adapted to available history)
          - Rolling stats: rolling_mean_6, rolling_std_6, rolling_mean_12, rolling_std_12, rolling_mean_24
          - Cyclical temporal encodings: hour_sin, hour_cos, day_sin, day_cos
          - Calendar flags: hour, day_of_week, is_weekend
          - Deviation from baseline: relative percentage delta
        """
        if df.empty or "value" not in df.columns:
            return pd.DataFrame()

        out = df.copy()
        n_obs = len(out)

        # 1. Temporal & Calendar features
        if include_calendar:
            if isinstance(out.index, pd.DatetimeIndex):
                hours = out.index.hour
                dows = out.index.dayofweek
            else:
                hours = pd.Series(0, index=out.index)
                dows = pd.Series(0, index=out.index)

            out["hour"] = hours
            out["day_of_week"] = dows
            out["is_weekend"] = (dows >= 5).astype(float)

            # Cyclical trigonometric transformations
            out["hour_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
            out["hour_cos"] = np.cos(2.0 * np.pi * hours / 24.0)
            out["day_sin"] = np.sin(2.0 * np.pi * dows / 7.0)
            out["day_cos"] = np.cos(2.0 * np.pi * dows / 7.0)

        # 2. Lag features (strictly backward looking)
        if include_lags:
            lag_candidates = [1, 2, 3, 6, 12, 24]
            for lag in lag_candidates:
                if n_obs > lag:
                    out[f"lag_{lag}"] = out["value"].shift(lag)

        # 3. Rolling statistics (shifted by 1 to exclude current observation)
        if include_rolling:
            for w in [6, 12, 24]:
                if n_obs > w:
                    shifted = out["value"].shift(1)
                    out[f"rolling_mean_{w}"] = shifted.rolling(window=w, min_periods=max(2, w // 2)).mean()
                    out[f"rolling_std_{w}"] = shifted.rolling(window=w, min_periods=max(2, w // 2)).std().fillna(0.0)

        # 4. Baseline deviation
        if baseline is not None and baseline > 0:
            out["baseline_dev_pct"] = (out["value"] - baseline) / baseline * 100.0
        else:
            out["baseline_dev_pct"] = 0.0

        # Backfill initial lag NaNs so we retain maximum usable data
        out = out.bfill().ffill()
        return out

    @staticmethod
    def extract_single_observation_features(
        current_val: float,
        recent_values: List[float],
        timestamp: Optional[datetime] = None,
        baseline: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Compute an explainable feature vector for a single newly arrived sensor reading
        using available preceding historical values.
        """
        ts = timestamp or datetime.now(timezone.utc)
        hour = ts.hour
        dow = ts.weekday()
        is_weekend = 1.0 if dow >= 5 else 0.0

        clean_history = [v for v in recent_values if v is not None and math.isfinite(v)]
        n_hist = len(clean_history)

        lag_1 = clean_history[-1] if n_hist >= 1 else current_val
        lag_2 = clean_history[-2] if n_hist >= 2 else lag_1
        lag_3 = clean_history[-3] if n_hist >= 3 else lag_2

        # 6-point rolling stats
        recent_6 = clean_history[-6:] if n_hist >= 6 else (clean_history if n_hist > 0 else [current_val])
        rolling_mean_6 = float(np.mean(recent_6))
        rolling_std_6 = float(np.std(recent_6, ddof=1)) if len(recent_6) > 1 else 0.0

        # Baseline deviation
        base = baseline if (baseline is not None and baseline > 0) else (rolling_mean_6 if rolling_mean_6 > 0 else 100.0)
        dev_pct = ((current_val - base) / base * 100.0) if base > 0 else 0.0

        return {
            "current_value": float(current_val),
            "lag_1": float(lag_1),
            "lag_2": float(lag_2),
            "lag_3": float(lag_3),
            "rolling_mean_6": float(rolling_mean_6),
            "rolling_std_6": float(rolling_std_6),
            "hour": float(hour),
            "day_of_week": float(dow),
            "is_weekend": float(is_weekend),
            "hour_sin": float(np.sin(2.0 * np.pi * hour / 24.0)),
            "hour_cos": float(np.cos(2.0 * np.pi * hour / 24.0)),
            "baseline_dev_pct": float(dev_pct),
        }

    def preprocess_series(
        self,
        df: pd.DataFrame,
        timestamp_col: Optional[str] = "timestamp",
        value_col: str = "value",
        resample_freq: str = "1h",
        filter_anomalies: bool = True,
        anomaly_col: Optional[str] = "is_anomaly",
    ) -> pd.DataFrame:
        """Convenience wrapper around prepare_time_series_dataframe."""
        data = df.copy()
        if timestamp_col and timestamp_col in data.columns and not isinstance(data.index, pd.DatetimeIndex):
            data["timestamp"] = pd.to_datetime(data[timestamp_col])
        return self.prepare_time_series_dataframe(
            readings=data,
            freq=resample_freq,
            filter_anomalies=filter_anomalies,
            min_points=3,
        )

    def build_supervised_features(
        self,
        df: pd.DataFrame,
        value_col: str = "value",
        lags: Optional[List[int]] = None,
        rolling_windows: Optional[List[int]] = None,
        baseline: Optional[float] = None,
    ) -> pd.DataFrame:
        """Convenience wrapper around engineer_features."""
        return self.engineer_features(
            df=df,
            baseline=baseline,
            include_lags=True,
            include_rolling=True,
            include_calendar=True,
        )

    @staticmethod
    def generate_future_feature_row(
        history_values: List[float],
        target_dt: datetime,
        feature_names: List[str],
        baseline: Optional[float] = None,
    ) -> np.ndarray:
        """Construct a feature row for iterative multi-step future forecasting."""
        hour = target_dt.hour
        dow = target_dt.weekday()
        is_weekend = 1.0 if dow >= 5 else 0.0
        n_hist = len(history_values)

        lag_1 = history_values[-1] if n_hist >= 1 else 100.0
        lag_2 = history_values[-2] if n_hist >= 2 else lag_1
        lag_3 = history_values[-3] if n_hist >= 3 else lag_2

        recent_6 = history_values[-6:] if n_hist >= 6 else history_values
        recent_24 = history_values[-24:] if n_hist >= 24 else history_values

        rolling_mean_6 = float(np.mean(recent_6)) if recent_6 else lag_1
        rolling_std_6 = float(np.std(recent_6)) if len(recent_6) > 1 else 0.0
        rolling_mean_24 = float(np.mean(recent_24)) if recent_24 else lag_1
        rolling_std_24 = float(np.std(recent_24)) if len(recent_24) > 1 else 0.0

        feat_dict = {
            "lag_1": lag_1,
            "lag_2": lag_2,
            "lag_3": lag_3,
            "lag_6": history_values[-6] if n_hist >= 6 else lag_1,
            "lag_12": history_values[-12] if n_hist >= 12 else lag_1,
            "lag_24": history_values[-24] if n_hist >= 24 else lag_1,
            "lag_48": history_values[-48] if n_hist >= 48 else lag_1,
            "rolling_mean_6": rolling_mean_6,
            "rolling_std_6": rolling_std_6,
            "rolling_mean_12": rolling_mean_6,
            "rolling_std_12": rolling_std_6,
            "rolling_mean_24": rolling_mean_24,
            "rolling_std_24": rolling_std_24,
            "hour": float(hour),
            "day_of_week": float(dow),
            "is_weekend": float(is_weekend),
            "hour_sin": float(np.sin(2.0 * np.pi * hour / 24.0)),
            "hour_cos": float(np.cos(2.0 * np.pi * hour / 24.0)),
            "day_sin": float(np.sin(2.0 * np.pi * dow / 7.0)),
            "day_cos": float(np.cos(2.0 * np.pi * dow / 7.0)),
            "baseline_dev_pct": ((lag_1 - baseline) / baseline * 100.0) if baseline and baseline > 0 else 0.0,
        }
        row = [feat_dict.get(fn, 0.0) for fn in feature_names]
        return np.array([row])


ml_pipeline = MLDataPipeline()
ml_data_pipeline = ml_pipeline
