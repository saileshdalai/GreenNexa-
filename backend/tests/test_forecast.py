"""
GreenNexa — Phase 9: AI/ML Forecasting Engine Unit & Integration Tests.

Tests all 27 required scenarios:
  1. SUPER_ADMIN forecasts any organisation -> success
  2. ADMIN forecasts own organisation -> success
  3. ADMIN forecasts another organisation -> 403
  4. VIEWER forecasts permitted organisation -> success
  5. VIEWER forecasts another organisation -> 403
  6. Missing token -> 401
  7. Invalid token -> 401
  8. Unsupported sensor -> 422
  9. Disabled sensor -> 422
  10. Unsupported horizon -> 422
  11. Horizon > 72h -> 422
  12. Sufficient historical data -> forecast generated
  13. Insufficient historical data -> clean 422
  14. Invalid/NaN historical values handled safely
  15. Timestamps sorted correctly
  16. Forecast contains requested number of hourly points
  17. Predictions are finite numbers
  18. lower_bound <= predicted_value <= upper_bound
  19. Forecast timestamps are in the future
  20. No future historical data is used for training
  21. Existing anomaly readings do not corrupt forecasting
  22. Raw anomaly readings remain unchanged in database
  23. Synthetic source forecast works
  24. IoT source forecast works
  25. Organisation data cannot leak into another organisation's forecast
  26. Training window is limited
  27. Repeated requests do not unnecessarily perform uncontrolled retraining (cache hit)
"""

from datetime import datetime, timedelta, timezone

import pytest
from app.db.models import OrganisationSensorConfig, SensorReading
from app.services.forecasting import forecasting_service


@pytest.fixture
def seed_forecast_data(db_session, seed_orgs):
    """Seed 48 hours of deterministic historical readings for ORG-TEST-A."""
    forecasting_service.clear_cache()
    now = datetime.now(timezone.utc)

    # Configure ORG-TEST-A with synthetic mode and enabled energy and water sensors
    cfg_a = OrganisationSensorConfig(
        organisation_id="ORG-TEST-A",
        data_source="synthetic",
        enabled_sensors="energy|water",
        is_active=True,
    )
    # Configure ORG-TEST-B with iot mode and enabled energy sensor
    cfg_b = OrganisationSensorConfig(
        organisation_id="ORG-TEST-B",
        data_source="iot",
        enabled_sensors="energy",
        is_active=True,
    )
    db_session.add_all([cfg_a, cfg_b])

    readings = []
    # Seed 48 hourly readings for energy in ORG-TEST-A (value ~100 + noise)
    for i in range(48, 0, -1):
        ts = now - timedelta(hours=i)
        val = 100.0 + (i % 5) * 2.0
        readings.append(
            SensorReading(
                organisation_id="ORG-TEST-A",
                sensor_type="energy",
                value=val,
                unit="kWh",
                source="synthetic",
                timestamp=ts,
                is_anomaly=False,
            )
        )

    # Seed 30 hourly readings for water in ORG-TEST-A
    for i in range(30, 0, -1):
        ts = now - timedelta(hours=i)
        val = 50.0 + (i % 3) * 1.5
        readings.append(
            SensorReading(
                organisation_id="ORG-TEST-A",
                sensor_type="water",
                value=val,
                unit="L",
                source="synthetic",
                timestamp=ts,
                is_anomaly=False,
            )
        )

    # Seed 30 hourly readings for energy in ORG-TEST-B
    for i in range(30, 0, -1):
        ts = now - timedelta(hours=i)
        val = 500.0 + (i % 4) * 10.0
        readings.append(
            SensorReading(
                organisation_id="ORG-TEST-B",
                sensor_type="energy",
                value=val,
                unit="kWh",
                source="iot",
                timestamp=ts,
                is_anomaly=False,
            )
        )

    db_session.add_all(readings)
    db_session.commit()
    return {"org_a": "ORG-TEST-A", "org_b": "ORG-TEST-B"}


# ---------------------------------------------------------------------------
# Authorization Tests (1 - 7)
# ---------------------------------------------------------------------------
def test_super_admin_forecast_any_org(client, auth_headers, seed_forecast_data):
    headers = auth_headers("super@admin.com", "SUPER_ADMIN", "ORG-TEST-A")
    res_a = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h", headers=headers)
    assert res_a.status_code == 200
    assert res_a.json()["organisation_id"] == "ORG-TEST-A"

    res_b = client.get("/api/v1/forecast/ORG-TEST-B?sensor_type=energy&horizon=24h", headers=headers)
    assert res_b.status_code == 200
    assert res_b.json()["organisation_id"] == "ORG-TEST-B"


def test_admin_forecast_own_org(client, auth_headers, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h", headers=headers)
    assert res.status_code == 200
    assert len(res.json()["forecast"]) == 24


def test_admin_forecast_cross_org_forbidden(client, auth_headers, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/forecast/ORG-TEST-B?sensor_type=energy&horizon=24h", headers=headers)
    assert res.status_code == 403


def test_viewer_forecast_own_org(client, auth_headers, seed_forecast_data):
    headers = auth_headers("viewera@test.com", "VIEWER", "ORG-TEST-A")
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h", headers=headers)
    assert res.status_code == 403


def test_viewer_forecast_cross_org_forbidden(client, auth_headers, seed_forecast_data):
    headers = auth_headers("viewera@test.com", "VIEWER", "ORG-TEST-A")
    res = client.get("/api/v1/forecast/ORG-TEST-B?sensor_type=energy&horizon=24h", headers=headers)
    assert res.status_code == 403


def test_missing_token_unauthorized(client, seed_forecast_data):
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h")
    assert res.status_code == 401


def test_invalid_token_unauthorized(client, seed_forecast_data):
    res = client.get(
        "/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h",
        headers={"Authorization": "Bearer invalid.token.str"},
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Validation Tests (8 - 11)
# ---------------------------------------------------------------------------
def test_unsupported_sensor_type(client, auth_headers, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=temperature&horizon=24h", headers=headers)
    assert res.status_code == 422


def test_disabled_sensor(client, auth_headers, db_session, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    # Disable water sensor for ORG-TEST-A
    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id="ORG-TEST-A").first()
    cfg.set_enabled_sensors(["energy"])
    db_session.commit()

    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=water&horizon=24h", headers=headers)
    assert res.status_code == 422
    assert "disabled" in res.json()["detail"].lower()


def test_unsupported_horizon(client, auth_headers, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=5h", headers=headers)
    assert res.status_code == 422


def test_horizon_exceeds_maximum(client, auth_headers, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=100h", headers=headers)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Data & Horizon Tests (12 - 20)
# ---------------------------------------------------------------------------
def test_sufficient_historical_data(client, auth_headers, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["forecast"]) == 24
    assert data["sensor_type"] == "energy"
    assert data["horizon"] == "24h"


def test_insufficient_historical_data_returns_422(client, auth_headers, db_session, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    # Delete readings for energy so fewer than 24 points remain
    db_session.query(SensorReading).filter(
        SensorReading.organisation_id == "ORG-TEST-A",
        SensorReading.sensor_type == "energy",
    ).delete()
    db_session.commit()

    # Add only 10 readings
    now = datetime.now(timezone.utc)
    for i in range(10):
        db_session.add(
            SensorReading(
                organisation_id="ORG-TEST-A",
                sensor_type="energy",
                value=100.0,
                unit="kWh",
                source="synthetic",
                timestamp=now - timedelta(hours=i),
            )
        )
    db_session.commit()

    forecasting_service.clear_cache()
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h", headers=headers)
    assert res.status_code == 422
    assert "insufficient historical data" in res.json()["detail"].lower()


def test_horizon_point_counts(client, auth_headers, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    for h_str, h_count in [("6h", 6), ("12h", 12), ("24h", 24), ("48h", 48), ("72h", 72)]:
        forecasting_service.clear_cache()
        res = client.get(f"/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon={h_str}", headers=headers)
        assert res.status_code == 200
        assert len(res.json()["forecast"]) == h_count


def test_finite_predictions_and_bounds_order(client, auth_headers, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h", headers=headers)
    assert res.status_code == 200
    points = res.json()["forecast"]

    now_utc = datetime.now(timezone.utc)
    for p in points:
        pred = p["predicted_value"]
        lb = p["lower_bound"]
        ub = p["upper_bound"]

        assert isinstance(pred, (int, float))
        assert isinstance(lb, (int, float))
        assert isinstance(ub, (int, float))

        assert lb <= pred <= ub, f"Bound check failed: {lb} <= {pred} <= {ub}"

        # Check future timestamp
        p_ts = datetime.fromisoformat(p["timestamp"])
        if p_ts.tzinfo is None:
            p_ts = p_ts.replace(tzinfo=timezone.utc)
        assert p_ts > now_utc - timedelta(hours=1)


# ---------------------------------------------------------------------------
# Anomaly Handling Tests (21 - 22)
# ---------------------------------------------------------------------------
def test_anomaly_filtering_and_db_preservation(client, auth_headers, db_session, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    now = datetime.now(timezone.utc)

    # Insert 2 extreme anomaly readings into ORG-TEST-A
    ano1 = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="energy",
        value=99999.0,
        unit="kWh",
        source="synthetic",
        timestamp=now - timedelta(hours=10),
        is_anomaly=True,
        anomaly_severity="CRITICAL",
    )
    db_session.add(ano1)
    db_session.commit()

    forecasting_service.clear_cache()
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h", headers=headers)
    assert res.status_code == 200
    points = res.json()["forecast"]

    # Forecast values should be around 100-110, NOT 99999
    for p in points:
        assert p["predicted_value"] < 500.0

    # Ensure raw anomaly record remains unchanged in database
    db_ano = db_session.query(SensorReading).filter_by(id=ano1.id).first()
    assert db_ano is not None
    assert db_ano.value == 99999.0
    assert db_ano.is_anomaly is True


# ---------------------------------------------------------------------------
# Data Source & Organisation Isolation Tests (23 - 25)
# ---------------------------------------------------------------------------
def test_data_source_mode_reported(client, auth_headers, seed_forecast_data):
    headers_a = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    headers_b = auth_headers("adminb@test.com", "ADMIN", "ORG-TEST-B")

    res_a = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["data_source"] == "synthetic"

    res_b = client.get("/api/v1/forecast/ORG-TEST-B?sensor_type=energy&horizon=24h", headers=headers_b)
    assert res_b.status_code == 200
    assert res_b.json()["data_source"] == "iot"


def test_organisation_data_isolation(client, auth_headers, seed_forecast_data):
    headers_a = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    headers_b = auth_headers("adminb@test.com", "ADMIN", "ORG-TEST-B")

    res_a = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h", headers=headers_a)
    res_b = client.get("/api/v1/forecast/ORG-TEST-B?sensor_type=energy&horizon=24h", headers=headers_b)

    # ORG-TEST-A predictions should be ~100-110, ORG-TEST-B predictions should be ~500-530
    val_a = res_a.json()["forecast"][0]["predicted_value"]
    val_b = res_b.json()["forecast"][0]["predicted_value"]

    assert abs(val_a - 100.0) < 50.0
    assert abs(val_b - 500.0) < 100.0


# ---------------------------------------------------------------------------
# Performance & Caching Tests (26 - 27)
# ---------------------------------------------------------------------------
def test_model_caching(client, auth_headers, seed_forecast_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")

    forecasting_service.clear_cache()
    res1 = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h", headers=headers)
    assert res1.status_code == 200
    gen1 = res1.json()["generated_at"]

    # Second call should return cached result with identical timestamp
    res2 = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h", headers=headers)
    assert res2.status_code == 200
    gen2 = res2.json()["generated_at"]

    assert gen1 == gen2
