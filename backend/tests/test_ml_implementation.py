"""
GreenNexa — Complete Backend AI/ML Implementation Test Suite.

Comprehensive tests for:
  - Scikit-Learn IsolationForest anomaly detection
  - Scikit-Learn Ridge & RandomForest time-series forecasting
  - Chronological holdout backtesting (MAE, RMSE, R²)
  - Multi-level fallback cascade
  - Future anomaly risk estimation & time-to-breach
  - ML model registry persistence & caching
  - ML explainability & decision attribution
  - New ML API endpoints
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.db.models import AnomalyRecord, Organisation, OrganisationSensorConfig, SensorReading
from app.services.anomaly_ml_service import anomaly_ml_service
from app.services.forecasting_ml_service import forecast_ml_service
from app.services.future_anomaly_service import future_anomaly_service
from app.services.ml_explainability import ml_explainability_service
from app.services.ml_pipeline import ml_data_pipeline
from app.services.model_registry import model_registry


@pytest.fixture
def seed_ml_data(db_session: Session) -> dict:
    """Sets up a test organisation with historical telemetry for ML validation."""
    now = datetime.now(timezone.utc)
    org_id = "ORG-ML-TEST"

    org = db_session.query(Organisation).filter_by(id=org_id).first()
    if not org:
        org = Organisation(
            id=org_id,
            name="ML Test Facility",
            facility_name="ML Research Campus",
            is_active=True,
        )
        db_session.add(org)

    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=org_id).first()
    if not cfg:
        cfg = OrganisationSensorConfig(
            organisation_id=org_id,
            data_source="synthetic",
            enabled_sensors="energy|water|waste|temperature|co2|traffic",
            is_active=True,
        )
        db_session.add(cfg)
    db_session.commit()

    # Clear any old readings
    db_session.query(SensorReading).filter_by(organisation_id=org_id).delete()
    db_session.query(AnomalyRecord).filter_by(organisation_id=org_id).delete()
    db_session.commit()

    # Seed 72 hours of hourly readings with realistic diurnal pattern
    readings = []
    for h in range(72, 0, -1):
        ts = now - timedelta(hours=h)
        hour = ts.hour
        # Diurnal pattern
        diurnal = 1000.0 + 300.0 * math.sin((hour - 8) * math.pi / 12.0)
        noise = float((h % 7) * 5.0)
        val = round(diurnal + noise, 2)
        readings.append(
            SensorReading(
                organisation_id=org_id,
                sensor_type="energy",
                value=val,
                unit="kWh",
                source="synthetic",
                timestamp=ts,
                is_anomaly=False,
            )
        )
    db_session.add_all(readings)
    db_session.commit()

    return {"org_id": org_id, "reading_count": len(readings)}


# ===========================================================================
# 1. ML Data Pipeline Tests
# ===========================================================================
def test_ml_pipeline_preprocessing():
    """Verify resampling, chronological sorting, and anomaly filtering."""
    now = datetime.now(timezone.utc)
    raw_data = [
        {"timestamp": now - timedelta(hours=3), "value": 100.0, "is_anomaly": False},
        {"timestamp": now - timedelta(hours=2), "value": 999.0, "is_anomaly": True},
        {"timestamp": now - timedelta(hours=1), "value": 110.0, "is_anomaly": False},
        {"timestamp": now, "value": 120.0, "is_anomaly": False},
    ]
    df = pd.DataFrame(raw_data)
    clean = ml_data_pipeline.preprocess_series(df, filter_anomalies=True)
    assert not clean.empty
    assert clean["value"].max() < 500.0


def test_ml_pipeline_feature_engineering_no_future_leakage():
    """Verify lag features strictly use past values with zero future leakage."""
    dates = pd.date_range("2026-01-01", periods=30, freq="1h")
    values = np.linspace(100.0, 200.0, 30)
    df = pd.DataFrame({"value": values}, index=dates)

    feats = ml_data_pipeline.engineer_features(df, baseline=150.0)
    assert "lag_1" in feats.columns
    assert "rolling_mean_6" in feats.columns
    assert "hour_sin" in feats.columns
    assert "hour_cos" in feats.columns

    assert math.isclose(feats["lag_1"].iloc[5], df["value"].iloc[4], rel_tol=1e-3)


# ===========================================================================
# 2. Isolation Forest Anomaly Detection Tests
# ===========================================================================
def test_isolation_forest_detects_genuine_multivariate_outlier():
    """Verify Scikit-Learn IsolationForest detects abnormal deviations when history >= 24."""
    history = [1000.0 + (i % 6) * 10.0 for i in range(48)]

    # Normal reading ~1020
    norm_res = anomaly_ml_service.evaluate_reading(
        current_value=1020.0,
        history_values=history,
        metric="energy",
        baseline=1000.0,
        warning_threshold_pct=15.0,
        critical_threshold_pct=30.0,
    )
    assert not norm_res["is_anomaly"]
    assert norm_res["ml_evaluated"] is True
    assert norm_res["anomaly_score"] < 0.60

    # Severe spike 2200 kWh (+120%)
    spike_res = anomaly_ml_service.evaluate_reading(
        current_value=2200.0,
        history_values=history,
        metric="energy",
        baseline=1000.0,
        warning_threshold_pct=15.0,
        critical_threshold_pct=30.0,
    )
    assert spike_res["is_anomaly"] is True
    assert spike_res["ml_evaluated"] is True
    assert spike_res["anomaly_score"] >= 0.65
    assert spike_res["severity"].lower() in ("critical", "high")
    assert "isolation_forest" in spike_res["detection_method"].lower()


def test_isolation_forest_minimum_sample_guard():
    """Verify graceful fallback when history < 24 points."""
    sparse_history = [100.0, 105.0, 102.0]
    res = anomaly_ml_service.evaluate_reading(
        current_value=250.0,
        history_values=sparse_history,
        metric="water",
        baseline=100.0,
        warning_threshold_pct=15.0,
        critical_threshold_pct=30.0,
    )
    assert res["is_anomaly"] is True
    assert res["ml_evaluated"] is False
    assert "rule" in res["detection_method"].lower()


# ===========================================================================
# 3. ML Forecasting & Chronological Evaluation Tests
# ===========================================================================
def test_ml_forecasting_produces_valid_predictions_and_metrics(db_session: Session, seed_ml_data: dict):
    """Verify Scikit-Learn regression generates 24h predictions with holdout metrics."""
    org_id = seed_ml_data["org_id"]
    from app.services.forecasting import forecasting_service
    forecasting_service.clear_cache()

    fc_resp = forecasting_service.get_forecast(
        db=db_session,
        organisation_id=org_id,
        sensor_type="energy",
        horizon="24h",
        mode="last",
    )

    assert fc_resp.is_available is True
    assert len(fc_resp.forecast) == 24
    assert fc_resp.model_family in ("machine_learning", "statistical")

    for pt in fc_resp.forecast:
        assert math.isfinite(pt.predicted_value)
        assert pt.lower_bound <= pt.predicted_value <= pt.upper_bound
        assert pt.predicted_value >= 0.0

    if fc_resp.metrics and fc_resp.metrics.get("is_evaluated"):
        assert fc_resp.metrics["evaluation_method"] == "chronological_holdout"
        assert fc_resp.metrics["mae"] is not None
        assert fc_resp.metrics["rmse"] is not None


def test_ml_forecasting_multi_module_support(db_session: Session, seed_ml_data: dict):
    """Verify forecasting works across multiple modules (temperature, water, etc.)."""
    org_id = seed_ml_data["org_id"]
    now = datetime.now(timezone.utc)

    readings = [
        SensorReading(
            organisation_id=org_id,
            sensor_type="temperature",
            value=24.0 + (i % 4) * 0.5,
            unit="°C",
            source="synthetic",
            timestamp=now - timedelta(hours=30 - i),
            is_anomaly=False,
        )
        for i in range(30)
    ]
    db_session.add_all(readings)
    db_session.commit()

    from app.services.forecasting import forecasting_service
    forecasting_service.clear_cache()

    fc_resp = forecasting_service.get_forecast(
        db=db_session,
        organisation_id=org_id,
        sensor_type="temperature",
        horizon="12h",
        mode="last",
    )
    assert fc_resp.is_available is True
    assert len(fc_resp.forecast) == 12
    assert fc_resp.unit == "°C"


# ===========================================================================
# 4. Future Anomaly Risk Prediction Tests
# ===========================================================================
def test_future_anomaly_risk_projection(db_session: Session, seed_ml_data: dict):
    """Verify 24h future anomaly risk estimation and driver breakdown."""
    org_id = seed_ml_data["org_id"]
    risk = future_anomaly_service.evaluate_future_risk(
        db=db_session,
        organisation_id=org_id,
        metric="energy",
        horizon="24h",
    )

    assert "risk_score" in risk
    assert 0.0 <= risk["risk_score"] <= 1.0
    assert risk["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert "explanation" in risk
    assert "peak_projected_value" in risk


# ===========================================================================
# 5. ML Model Registry Persistence Tests
# ===========================================================================
def test_model_registry_persistence():
    """Verify saving and loading models via joblib with sidecar metadata."""
    from sklearn.linear_model import LinearRegression
    dummy_model = LinearRegression()
    dummy_model.fit(np.array([[1.0], [2.0], [3.0]]), np.array([2.0, 4.0, 6.0]))

    model_id = "test_unit_model"
    saved = model_registry.save_model(
        model=dummy_model,
        model_id=model_id,
        metadata={"algorithm": "LinearRegression", "model_type": "unit_test"},
    )
    assert saved is True

    loaded_model, loaded_meta = model_registry.load_model(model_id)
    assert loaded_model is not None
    assert loaded_meta["algorithm"] == "LinearRegression"

    pred = loaded_model.predict([[4.0]])
    assert math.isclose(float(pred[0]), 8.0, abs_tol=1e-3)

    model_registry.delete_model(model_id)


# ===========================================================================
# 6. ML Explainability Service Tests
# ===========================================================================
def test_ml_explainability_service(db_session: Session, seed_ml_data: dict):
    """Verify transparent decision attribution for an anomaly record."""
    org_id = seed_ml_data["org_id"]
    anom = AnomalyRecord(
        organisation_id=org_id,
        sensor_type="energy",
        metric="energy",
        value=2400.0,
        expected_min=800.0,
        expected_max=1200.0,
        anomaly_score=0.88,
        severity="critical",
        reason="Critical Energy Anomaly detected",
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(anom)
    db_session.commit()
    db_session.refresh(anom)

    explanation = ml_explainability_service.explain_anomaly(db_session, anom.id)
    assert explanation["anomaly_id"] == anom.id
    assert "decision_factors" in explanation
    assert len(explanation["decision_factors"]) >= 2
    assert "model_attribution" in explanation


# ===========================================================================
# 7. Dedicated ML API Endpoints Tests
# ===========================================================================
def test_ml_api_endpoints(client, auth_headers, db_session: Session, seed_ml_data: dict):
    """Verify GET /api/v1/ml/models, GET /api/v1/ml/risk, and GET /api/v1/ml/insights."""
    org_id = seed_ml_data["org_id"]
    admin_headers = auth_headers("admin@mltest.com", "ADMIN", org_id)

    # List models
    res_models = client.get("/api/v1/ml/models", headers=admin_headers)
    assert res_models.status_code == 200
    assert "models" in res_models.json()

    # Risk evaluation
    res_risk = client.get(f"/api/v1/ml/risk/{org_id}?metric=energy", headers=admin_headers)
    assert res_risk.status_code == 200
    risk_data = res_risk.json()
    assert risk_data["metric"] == "energy"
    assert "risk_level" in risk_data

    # Insights briefing
    res_insights = client.get(f"/api/v1/ml/insights/{org_id}", headers=admin_headers)
    assert res_insights.status_code == 200
    insights = res_insights.json()
    assert "executive_summary" in insights
    assert "predictive_risks" in insights
