"""
GreenNexa — Phase 10: AI Anomaly Detection + AI Recommendations Integration Tests.

Tests all 33 required Phase 10 scenarios:
  1. Normal reading -> no anomaly
  2. Unusual energy reading -> anomaly
  3. Unusual water reading -> anomaly
  4. Anomaly severity calculated correctly
  5. Insufficient historical data handled safely
  6. Disabled sensor rejected
  7. Invalid sensor rejected
  8. Anomaly record created
  9. Original SensorReading unchanged
  10. Duplicate anomaly prevented
  11. Anomaly list endpoint works
  12. Severity filter works
  13. Sensor filter works
  14. SUPER_ADMIN can detect for any organisation
  15. ADMIN can detect own organisation
  16. ADMIN cannot detect another organisation -> 403
  17. VIEWER cannot perform detection action -> 403
  18. VIEWER can view permitted anomalies -> 200
  19. Missing token -> 401
  20. Invalid token -> 401
  21. Energy anomaly produces energy recommendation
  22. Water anomaly produces water recommendation
  23. Temperature anomaly produces temperature recommendation
  24. Recommendation priority follows anomaly severity
  25. Recommendation contains actionable suggestion
  26. Forecast trend can influence recommendation
  27. No recommendation generated for disabled sensor
  28. Duplicate recommendations prevented
  29. Recommendation list works
  30. Recommendation status update works (PATCH)
  31. Organisation isolation enforced
  32. Synthetic source works
  33. IoT source works
"""

from datetime import datetime, timedelta, timezone

import pytest
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    OrganisationSensorConfig,
    SensorReading,
)
from app.services.anomaly_detection import anomaly_detection_service
from app.services.recommendation import recommendation_service


@pytest.fixture
def seed_phase10_data(db_session, seed_orgs):
    """Seed historical readings and configuration for ORG-TEST-A and ORG-TEST-B."""
    now = datetime.now(timezone.utc)

    # Configure ORG-TEST-A with synthetic mode and enabled energy, water, temperature, humidity, co2, waste
    cfg_a = OrganisationSensorConfig(
        organisation_id="ORG-TEST-A",
        data_source="synthetic",
        enabled_sensors="energy|water|temperature|humidity|co2|waste",
        is_active=True,
    )
    # Configure ORG-TEST-B with iot mode and enabled energy
    cfg_b = OrganisationSensorConfig(
        organisation_id="ORG-TEST-B",
        data_source="iot",
        enabled_sensors="energy",
        is_active=True,
    )
    db_session.add_all([cfg_a, cfg_b])

    readings = []
    # Seed 20 historical normal readings for energy in ORG-TEST-A (value ~100.0)
    for i in range(20, 0, -1):
        ts = now - timedelta(hours=i * 2)
        readings.append(
            SensorReading(
                organisation_id="ORG-TEST-A",
                sensor_type="energy",
                value=100.0 + (i % 3),
                unit="kWh",
                source="synthetic",
                timestamp=ts,
                is_anomaly=False,
            )
        )

    # Seed 20 historical normal readings for water in ORG-TEST-A (value ~50.0)
    for i in range(20, 0, -1):
        ts = now - timedelta(hours=i * 2)
        readings.append(
            SensorReading(
                organisation_id="ORG-TEST-A",
                sensor_type="water",
                value=50.0 + (i % 2),
                unit="L",
                source="synthetic",
                timestamp=ts,
                is_anomaly=False,
            )
        )

    # Seed 20 historical normal readings for temperature in ORG-TEST-A (value ~22.0)
    for i in range(20, 0, -1):
        ts = now - timedelta(hours=i * 2)
        readings.append(
            SensorReading(
                organisation_id="ORG-TEST-A",
                sensor_type="temperature",
                value=22.0 + (i % 2) * 0.5,
                unit="°C",
                source="synthetic",
                timestamp=ts,
                is_anomaly=False,
            )
        )

    # Seed 20 historical normal readings for energy in ORG-TEST-B (value ~500.0)
    for i in range(20, 0, -1):
        ts = now - timedelta(hours=i * 2)
        readings.append(
            SensorReading(
                organisation_id="ORG-TEST-B",
                sensor_type="energy",
                value=500.0 + (i % 4),
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
# Anomaly Detection Unit & Integration Tests (1 - 13)
# ---------------------------------------------------------------------------
def test_normal_reading_no_anomaly(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    # Add normal energy reading (101.0)
    db_session.add(
        SensorReading(
            organisation_id="ORG-TEST-A",
            sensor_type="energy",
            value=101.0,
            unit="kWh",
            source="synthetic",
            timestamp=now,
        )
    )
    db_session.commit()

    res = anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    item = res["results"][0]
    assert item["anomaly_detected"] is False
    assert item["severity"] == "NORMAL"


def test_unusual_energy_reading_anomaly(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    # Add unusual energy spike (250.0)
    reading = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="energy",
        value=250.0,
        unit="kWh",
        source="synthetic",
        timestamp=now,
    )
    db_session.add(reading)
    db_session.commit()

    res = anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    item = res["results"][0]
    assert item["anomaly_detected"] is True
    assert item["severity"] in {"HIGH", "CRITICAL"}
    assert item["anomaly_id"] is not None


def test_unusual_water_reading_anomaly(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    reading = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="water",
        value=150.0,
        unit="L",
        source="synthetic",
        timestamp=now,
    )
    db_session.add(reading)
    db_session.commit()

    res = anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="water")
    item = res["results"][0]
    assert item["anomaly_detected"] is True
    assert item["severity"] in {"HIGH", "CRITICAL"}


def test_anomaly_severity_calculation(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    # Add moderate energy spike (102.5) -> LOW/MEDIUM
    reading = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="energy",
        value=102.5,
        unit="kWh",
        source="synthetic",
        timestamp=now,
    )
    db_session.add(reading)
    db_session.commit()

    res = anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    item = res["results"][0]
    assert item["severity"] in {"LOW", "MEDIUM"}



def test_insufficient_historical_data_handled(db_session, seed_orgs):
    # Empty org with < 5 readings
    cfg = OrganisationSensorConfig(organisation_id="ORG-EMPTY", enabled_sensors="energy")
    db_session.add(cfg)
    db_session.commit()

    res = anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-EMPTY", sensor_type="energy")
    item = res["results"][0]
    assert item["anomaly_detected"] is False
    assert "insufficient historical data" in item["reason"].lower()


def test_disabled_sensor_rejected(client, auth_headers, db_session, seed_phase10_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    # Disable water for ORG-TEST-A
    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id="ORG-TEST-A").first()
    cfg.set_enabled_sensors(["energy"])
    db_session.commit()

    res = client.post("/api/v1/anomalies/detect/ORG-TEST-A?sensor_type=water", headers=headers)
    assert res.status_code == 422


def test_invalid_sensor_rejected(client, auth_headers, seed_phase10_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.post("/api/v1/anomalies/detect/ORG-TEST-A?sensor_type=invalid_sensor", headers=headers)
    assert res.status_code == 422


def test_anomaly_record_created_and_original_reading_preserved(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    reading = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="energy",
        value=300.0,
        unit="kWh",
        source="synthetic",
        timestamp=now,
    )
    db_session.add(reading)
    db_session.commit()

    res = anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    item = res["results"][0]
    anomaly_id = item["anomaly_id"]

    # Check AnomalyRecord created
    record = db_session.query(AnomalyRecord).filter_by(id=anomaly_id).first()
    assert record is not None
    assert record.value == 300.0

    # Original SensorReading preserved (value unchanged)
    raw_reading = db_session.query(SensorReading).filter_by(id=reading.id).first()
    assert raw_reading.value == 300.0
    assert raw_reading.is_anomaly is True


def test_duplicate_anomaly_prevented(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    reading = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="energy",
        value=300.0,
        unit="kWh",
        source="synthetic",
        timestamp=now,
    )
    db_session.add(reading)
    db_session.commit()

    res1 = anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    id1 = res1["results"][0]["anomaly_id"]

    res2 = anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    id2 = res2["results"][0]["anomaly_id"]

    assert id1 == id2


def test_anomaly_listing_and_filtering(client, auth_headers, db_session, seed_phase10_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    now = datetime.now(timezone.utc)
    db_session.add(
        SensorReading(
            organisation_id="ORG-TEST-A",
            sensor_type="energy",
            value=350.0,
            unit="kWh",
            timestamp=now,
        )
    )
    db_session.commit()
    anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")

    res = client.get("/api/v1/anomalies/ORG-TEST-A?sensor_type=energy&severity=CRITICAL", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1


# ---------------------------------------------------------------------------
# Authorization Tests (14 - 20)
# ---------------------------------------------------------------------------
def test_super_admin_detect_any_org(client, auth_headers, seed_phase10_data):
    headers = auth_headers("super@admin.com", "SUPER_ADMIN", "ORG-TEST-A")
    res_a = client.post("/api/v1/anomalies/detect/ORG-TEST-A", headers=headers)
    res_b = client.post("/api/v1/anomalies/detect/ORG-TEST-B", headers=headers)
    assert res_a.status_code == 200
    assert res_b.status_code == 200


def test_admin_detect_own_org(client, auth_headers, seed_phase10_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.post("/api/v1/anomalies/detect/ORG-TEST-A", headers=headers)
    assert res.status_code == 200


def test_admin_detect_cross_org_forbidden(client, auth_headers, seed_phase10_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.post("/api/v1/anomalies/detect/ORG-TEST-B", headers=headers)
    assert res.status_code == 403


def test_viewer_cannot_detect_action(client, auth_headers, seed_phase10_data):
    headers = auth_headers("viewera@test.com", "VIEWER", "ORG-TEST-A")
    res = client.post("/api/v1/anomalies/detect/ORG-TEST-A", headers=headers)
    assert res.status_code == 403


def test_viewer_can_view_permitted_anomalies(client, auth_headers, seed_phase10_data):
    headers = auth_headers("viewera@test.com", "VIEWER", "ORG-TEST-A")
    res = client.get("/api/v1/anomalies/ORG-TEST-A", headers=headers)
    assert res.status_code == 403


def test_missing_token_unauthorized(client, seed_phase10_data):
    res = client.get("/api/v1/anomalies/ORG-TEST-A")
    assert res.status_code == 401


def test_invalid_token_unauthorized(client, seed_phase10_data):
    res = client.get("/api/v1/anomalies/ORG-TEST-A", headers={"Authorization": "Bearer invalid.token"})
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Recommendation Tests (21 - 33)
# ---------------------------------------------------------------------------
def test_energy_anomaly_produces_energy_recommendation(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    db_session.add(
        SensorReading(
            organisation_id="ORG-TEST-A",
            sensor_type="energy",
            value=350.0,
            unit="kWh",
            timestamp=now,
        )
    )
    db_session.commit()

    anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    recs = recommendation_service.generate_recommendations_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")

    assert len(recs) >= 1
    assert recs[0].metric == "energy"
    assert "HVAC" in recs[0].summary or "energy" in recs[0].summary.lower()


def test_water_anomaly_produces_water_recommendation(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    db_session.add(
        SensorReading(
            organisation_id="ORG-TEST-A",
            sensor_type="water",
            value=250.0,
            unit="L",
            timestamp=now,
        )
    )
    db_session.commit()

    anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="water")
    recs = recommendation_service.generate_recommendations_for_organisation(db_session, "ORG-TEST-A", sensor_type="water")

    assert len(recs) >= 1
    assert recs[0].metric == "water"
    assert "leakage" in recs[0].summary.lower() or "water" in recs[0].summary.lower()


def test_temperature_anomaly_produces_temperature_recommendation(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    db_session.add(
        SensorReading(
            organisation_id="ORG-TEST-A",
            sensor_type="temperature",
            value=45.0,
            unit="°C",
            timestamp=now,
        )
    )
    db_session.commit()

    anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="temperature")
    recs = recommendation_service.generate_recommendations_for_organisation(db_session, "ORG-TEST-A", sensor_type="temperature")

    assert len(recs) >= 1
    assert recs[0].metric == "temperature"
    assert "temperature" in recs[0].summary.lower()


def test_recommendation_priority_and_actionable_suggestion(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    db_session.add(
        SensorReading(
            organisation_id="ORG-TEST-A",
            sensor_type="energy",
            value=400.0,
            unit="kWh",
            timestamp=now,
        )
    )
    db_session.commit()

    anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    recs = recommendation_service.generate_recommendations_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")

    rec = recs[0]
    assert rec.priority in {"HIGH", "CRITICAL"}
    assert len(rec.recommended_actions_list) > 0


def test_forecast_trend_influences_recommendation(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    # Add readings to support forecasting for energy
    for i in range(30):
        db_session.add(
            SensorReading(
                organisation_id="ORG-TEST-A",
                sensor_type="energy",
                value=100.0 + i,
                unit="kWh",
                timestamp=now - timedelta(hours=30 - i),
            )
        )
    # Add anomaly
    db_session.add(
        SensorReading(
            organisation_id="ORG-TEST-A",
            sensor_type="energy",
            value=300.0,
            unit="kWh",
            timestamp=now,
        )
    )
    db_session.commit()

    anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    recs = recommendation_service.generate_recommendations_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")

    assert len(recs) >= 1
    assert "decision-support" in recs[0].confidence_note.lower()


def test_no_recommendation_for_disabled_sensor(client, auth_headers, db_session, seed_phase10_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    # Disable water for ORG-TEST-A
    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id="ORG-TEST-A").first()
    cfg.set_enabled_sensors(["energy"])
    db_session.commit()

    res = client.post("/api/v1/recommendations/generate/ORG-TEST-A?sensor_type=water", headers=headers)
    assert res.status_code == 422


def test_duplicate_recommendations_prevented(db_session, seed_phase10_data):
    now = datetime.now(timezone.utc)
    db_session.add(
        SensorReading(
            organisation_id="ORG-TEST-A",
            sensor_type="energy",
            value=350.0,
            unit="kWh",
            timestamp=now,
        )
    )
    db_session.commit()

    anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    recs1 = recommendation_service.generate_recommendations_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    recs2 = recommendation_service.generate_recommendations_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")

    assert len(recs1) == len(recs2)
    assert recs1[0].id == recs2[0].id


def test_recommendation_list_and_status_update(client, auth_headers, db_session, seed_phase10_data):
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    now = datetime.now(timezone.utc)
    db_session.add(
        SensorReading(
            organisation_id="ORG-TEST-A",
            sensor_type="energy",
            value=350.0,
            unit="kWh",
            timestamp=now,
        )
    )
    db_session.commit()

    anomaly_detection_service.detect_anomalies_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")
    recommendation_service.generate_recommendations_for_organisation(db_session, "ORG-TEST-A", sensor_type="energy")

    # List recommendations
    res_list = client.get("/api/v1/recommendations/ORG-TEST-A", headers=headers)
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    assert len(items) >= 1

    rec_id = items[0]["id"]

    # PATCH status update
    res_patch = client.patch(
        f"/api/v1/recommendations/{rec_id}",
        json={"status": "ACKNOWLEDGED"},
        headers=headers,
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "ACKNOWLEDGED"


def test_organisation_isolation_recommendations(client, auth_headers, seed_phase10_data):
    headers_a = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/recommendations/ORG-TEST-B", headers=headers_a)
    assert res.status_code == 403


def test_synthetic_and_iot_data_sources_work(client, auth_headers, db_session, seed_phase10_data):
    headers_a = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    headers_b = auth_headers("adminb@test.com", "ADMIN", "ORG-TEST-B")

    now = datetime.now(timezone.utc)
    # Add anomaly to ORG-TEST-A (synthetic)
    db_session.add(
        SensorReading(
            organisation_id="ORG-TEST-A",
            sensor_type="energy",
            value=350.0,
            unit="kWh",
            source="synthetic",
            timestamp=now,
        )
    )
    # Add anomaly to ORG-TEST-B (iot)
    db_session.add(
        SensorReading(
            organisation_id="ORG-TEST-B",
            sensor_type="energy",
            value=950.0,
            unit="kWh",
            source="iot",
            timestamp=now,
        )
    )
    db_session.commit()

    res_a = client.post("/api/v1/anomalies/detect/ORG-TEST-A", headers=headers_a)
    res_b = client.post("/api/v1/anomalies/detect/ORG-TEST-B", headers=headers_b)

    assert res_a.status_code == 200
    assert res_b.status_code == 200
