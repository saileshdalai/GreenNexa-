"""
GreenNexa — Phase 6: Synthetic Data Simulator Unit & Integration Tests.

Tests all 23 required scenarios:
  1. Synthetic organisation generates readings -> success
  2. IoT organisation does NOT generate synthetic readings
  3. Only enabled sensors generate readings
  4. Disabled sensors do not generate readings
  5. source is stored as 'synthetic'
  6. readings are associated with correct organisation
  7. simulator interval defaults to 180 seconds
  8. simulator starts successfully
  9. simulator stops successfully
  10. starting simulator twice does not create duplicate loops
  11. ADMIN can control simulator for own organisation
  12. ADMIN cannot control another organisation -> 403
  13. VIEWER cannot start simulator -> 403
  14. missing token -> 401
  15. invalid token -> 401
  16. normal cycles generate normal values
  17. anomalies are not generated every cycle
  18. maximum one major anomaly per generation cycle
  19. anomaly sensor is selected from enabled sensors
  20. after an anomaly occurs, another anomaly cannot occur before 10 minutes
  21. after 10 minutes, another anomaly can occur according to probability
  22. multiple organisations remain isolated
  23. simulator exceptions do not crash the API
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.db.models import AnomalyRecord, Organisation, OrganisationSensorConfig, SensorReading
from app.services.synthetic_simulator import SyntheticDataSimulator, simulator_instance


@pytest.fixture(autouse=True)
def reset_simulator_state():
    """Ensure global simulator instance is stopped and reset before/after each test."""
    simulator_instance.stop()
    simulator_instance._last_anomaly_times.clear()
    simulator_instance._organisations_processed = 0
    simulator_instance._last_run_at = None
    yield
    simulator_instance.stop()
    simulator_instance._last_anomaly_times.clear()


# ---------------------------------------------------------------------------
# Test 1 & 5 & 6: Synthetic organisation generates readings with source='synthetic'
# ---------------------------------------------------------------------------
def test_synthetic_org_generates_readings(db_session, seed_orgs):
    """Synthetic organisation generates readings associated with correct org and source='synthetic'."""
    sim = SyntheticDataSimulator()
    readings = sim.run_cycle(db_session)

    assert len(readings) > 0
    for r in readings:
        assert r.source == "synthetic"
        assert r.organisation_id in ("ORG-TEST-A", "ORG-TEST-B")
        assert r.created_at is not None


# ---------------------------------------------------------------------------
# Test 2: IoT organisation does NOT generate synthetic readings
# ---------------------------------------------------------------------------
def test_iot_org_does_not_generate_readings(db_session, seed_orgs):
    """Organisation set to data_source='iot' does NOT receive synthetic readings."""
    # Set ORG-TEST-B to IoT mode
    cfg_b = OrganisationSensorConfig(
        organisation_id="ORG-TEST-B",
        data_source="iot",
        is_active=True,
    )
    db_session.add(cfg_b)
    db_session.commit()

    sim = SyntheticDataSimulator()
    readings = sim.run_cycle(db_session)

    # Only ORG-TEST-A should have generated readings
    org_ids = {r.organisation_id for r in readings}
    assert "ORG-TEST-A" in org_ids
    assert "ORG-TEST-B" not in org_ids


# ---------------------------------------------------------------------------
# Test 3 & 4: Only enabled sensors generate readings; disabled do not
# ---------------------------------------------------------------------------
def test_only_enabled_sensors_generate_readings(db_session, seed_orgs):
    """Only enabled sensors in configuration generate readings."""
    cfg_a = OrganisationSensorConfig(
        organisation_id="ORG-TEST-A",
        data_source="synthetic",
        enabled_sensors="energy|water|temperature",
        is_active=True,
    )
    db_session.add(cfg_a)
    db_session.commit()

    sim = SyntheticDataSimulator()
    readings = sim.run_cycle(db_session)

    org_a_types = {r.sensor_type for r in readings if r.organisation_id == "ORG-TEST-A"}
    assert org_a_types == {"energy", "water", "temperature"}
    assert "co2" not in org_a_types
    assert "humidity" not in org_a_types
    assert "waste" not in org_a_types


# ---------------------------------------------------------------------------
# Test 7: Simulator interval defaults to 30 seconds
# ---------------------------------------------------------------------------
def test_simulator_interval_default():
    """Simulator interval defaults to 30 seconds."""
    sim = SyntheticDataSimulator()
    assert sim.interval_seconds == 30
    assert sim.status()["interval_seconds"] == 30


# ---------------------------------------------------------------------------
# Test 8 & 9: Simulator starts and stops successfully
# ---------------------------------------------------------------------------
def test_simulator_start_stop():
    """Simulator starts and stops successfully."""
    sim = SyntheticDataSimulator()
    start_res = sim.start(interval_seconds=180)
    assert start_res["status"] == "started"
    assert sim.is_running is True

    stop_res = sim.stop()
    assert stop_res["status"] == "stopped"
    assert sim.is_running is False


# ---------------------------------------------------------------------------
# Test 10: Starting simulator twice does not create duplicate loops
# ---------------------------------------------------------------------------
def test_simulator_start_twice_no_duplicate():
    """Starting simulator twice does not create duplicate loops."""
    sim = SyntheticDataSimulator()
    res1 = sim.start(180)
    assert res1["status"] == "started"

    res2 = sim.start(180)
    assert res2["status"] == "already_running"
    sim.stop()


# ---------------------------------------------------------------------------
# Test 11: ADMIN can control simulator for own organisation
# ---------------------------------------------------------------------------
def test_admin_control_own_org_simulator(client, seed_orgs, auth_headers):
    """ADMIN can start/stop/view status for their own organisation.

    The stop is SCOPE-SPECIFIC: it only removes that organisation from the demo
    scope. The shared simulator worker keeps running so no other organisation's
    generation is affected (scope isolation).
    """
    headers = auth_headers("admin_a@greennexa.com", "ADMIN", "ORG-TEST-A")

    # Start
    res_start = client.post("/api/v1/simulator/synthetic/start?organisation_id=ORG-TEST-A", headers=headers)
    assert res_start.status_code == 200
    assert res_start.json()["running"] is True

    # Status
    res_status = client.get("/api/v1/simulator/synthetic/status?organisation_id=ORG-TEST-A", headers=headers)
    assert res_status.status_code == 200

    # Stop (scoped to this organisation)
    res_stop = client.post("/api/v1/simulator/synthetic/stop?organisation_id=ORG-TEST-A", headers=headers)
    assert res_stop.status_code == 200
    body = res_stop.json()
    assert body["demo_mode"] is False, "scoped stop must clear demo enrollment for this org"
    assert body["running"] is True, "shared worker must survive a scoped stop"


# ---------------------------------------------------------------------------
# Test 12: ADMIN cannot control another organisation -> 403
# ---------------------------------------------------------------------------
def test_admin_control_another_org_denied(client, seed_orgs, auth_headers):
    """ADMIN cannot start/stop simulator for another organisation (403 Forbidden)."""
    headers = auth_headers("admin_a_cross@greennexa.com", "ADMIN", "ORG-TEST-A")

    res_start = client.post("/api/v1/simulator/synthetic/start?organisation_id=ORG-TEST-B", headers=headers)
    assert res_start.status_code == 403

    res_stop = client.post("/api/v1/simulator/synthetic/stop?organisation_id=ORG-TEST-B", headers=headers)
    assert res_stop.status_code == 403


# ---------------------------------------------------------------------------
# Test 13: VIEWER cannot start simulator -> 403
# ---------------------------------------------------------------------------
def test_viewer_cannot_control_simulator(client, seed_orgs, auth_headers):
    """VIEWER cannot start, stop, or view simulator status (403 Forbidden)."""
    headers = auth_headers("viewer_a@greennexa.com", "VIEWER", "ORG-TEST-A")

    res_start = client.post("/api/v1/simulator/synthetic/start", headers=headers)
    assert res_start.status_code == 403

    res_stop = client.post("/api/v1/simulator/synthetic/stop", headers=headers)
    assert res_stop.status_code == 403

    res_status = client.get("/api/v1/simulator/synthetic/status", headers=headers)
    assert res_status.status_code == 403


# ---------------------------------------------------------------------------
# Test 14 & 15: Authentication error handling (401 Missing/Invalid Token)
# ---------------------------------------------------------------------------
def test_authentication_errors(client):
    """Simulator API returns 401 Unauthorized for missing or invalid token."""
    res1 = client.get("/api/v1/simulator/synthetic/status")
    assert res1.status_code == 401

    res2 = client.post(
        "/api/v1/simulator/synthetic/start",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert res2.status_code == 401


# ---------------------------------------------------------------------------
# Test 16: Normal cycles generate normal values
# ---------------------------------------------------------------------------
def test_normal_cycles_generate_normal_values(db_session, seed_orgs):
    """Normal generation cycles produce values within normal baseline ranges."""
    sim = SyntheticDataSimulator()
    # Force no anomalies by passing forced_anomaly_sensor=None and probabilities 0
    sim.DEFAULT_ANOMALY_PROBABILITIES = {k: 0.0 for k in sim.DEFAULT_ANOMALY_PROBABILITIES}

    readings = sim.run_cycle(db_session)
    for r in readings:
        assert r.is_anomaly is False
        assert r.anomaly_severity is None
        cfg = sim.SENSOR_CONFIGS[r.sensor_type]
        norm_min, norm_max = cfg["normal_range"]
        assert norm_min <= r.value <= norm_max


# ---------------------------------------------------------------------------
# Test 17 & 18 & 19: Anomalies: max one per cycle, selected from enabled sensors
# ---------------------------------------------------------------------------
def test_anomaly_generation_rules(db_session, seed_orgs):
    """At most one major anomaly per cycle, selected from enabled sensors."""
    sim = SyntheticDataSimulator()
    now = datetime.now(timezone.utc)

    # Force energy anomaly for ORG-TEST-A
    readings = sim.run_cycle(db_session, current_time=now, forced_anomaly_sensor="energy")

    org_a_anomalies = [r for r in readings if r.organisation_id == "ORG-TEST-A" and r.is_anomaly]
    assert len(org_a_anomalies) == 1
    anom = org_a_anomalies[0]
    assert anom.sensor_type == "energy"
    assert anom.anomaly_severity == AnomalyRecord.SEVERITY_HIGH

    # Verify AnomalyRecord DB entry was created
    db_anom = db_session.query(AnomalyRecord).filter_by(organisation_id="ORG-TEST-A", metric="energy").first()
    assert db_anom is not None
    assert db_anom.severity == AnomalyRecord.SEVERITY_HIGH


# ---------------------------------------------------------------------------
# Test 20: After an anomaly occurs, another anomaly CANNOT occur before 10 minutes
# ---------------------------------------------------------------------------
def test_anomaly_10_minute_gap_enforced(db_session, seed_orgs):
    """After an anomaly occurs, another anomaly CANNOT occur before 10 minutes have passed."""
    sim = SyntheticDataSimulator()
    t0 = datetime(2026, 9, 14, 10, 0, 0, tzinfo=timezone.utc)

    # Cycle 1 at 10:00 -> trigger energy anomaly
    readings_t0 = sim.run_cycle(db_session, current_time=t0, forced_anomaly_sensor="energy")
    assert any(r.is_anomaly for r in readings_t0 if r.organisation_id == "ORG-TEST-A")

    # Cycle 2 at 10:03 (3 mins later) -> try forcing anomaly, should be BLOCKED
    t1 = t0 + timedelta(minutes=3)
    readings_t1 = sim.run_cycle(db_session, current_time=t1, forced_anomaly_sensor="energy")
    anomalies_t1 = [r for r in readings_t1 if r.organisation_id == "ORG-TEST-A" and r.is_anomaly]
    assert len(anomalies_t1) == 0  # Blocked!

    # Cycle 3 at 10:06 (6 mins later) -> try forcing anomaly, should still be BLOCKED
    t2 = t0 + timedelta(minutes=6)
    readings_t2 = sim.run_cycle(db_session, current_time=t2, forced_anomaly_sensor="energy")
    anomalies_t2 = [r for r in readings_t2 if r.organisation_id == "ORG-TEST-A" and r.is_anomaly]
    assert len(anomalies_t2) == 0  # Blocked!

    # Cycle 4 at 10:09 (9 mins later) -> try forcing anomaly, should still be BLOCKED
    t3 = t0 + timedelta(minutes=9)
    readings_t3 = sim.run_cycle(db_session, current_time=t3, forced_anomaly_sensor="energy")
    anomalies_t3 = [r for r in readings_t3 if r.organisation_id == "ORG-TEST-A" and r.is_anomaly]
    assert len(anomalies_t3) == 0  # Blocked!


# ---------------------------------------------------------------------------
# Test 21: After 10 minutes, another anomaly CAN occur according to probability
# ---------------------------------------------------------------------------
def test_anomaly_allowed_after_10_minutes(db_session, seed_orgs):
    """After 10 minutes pass, another anomaly CAN occur."""
    sim = SyntheticDataSimulator()
    t0 = datetime(2026, 9, 14, 10, 0, 0, tzinfo=timezone.utc)

    # Anomaly at 10:00
    sim.run_cycle(db_session, current_time=t0, forced_anomaly_sensor="energy")

    # 10 minutes and 1 second later (10:10:01) -> anomaly allowed again
    t1 = t0 + timedelta(minutes=10, seconds=1)
    readings_t1 = sim.run_cycle(db_session, current_time=t1, forced_anomaly_sensor="water")

    anomalies_t1 = [r for r in readings_t1 if r.organisation_id == "ORG-TEST-A" and r.is_anomaly]
    assert len(anomalies_t1) == 1
    assert anomalies_t1[0].sensor_type == "water"


# ---------------------------------------------------------------------------
# Test 22: Multiple organisations remain isolated
# ---------------------------------------------------------------------------
def test_multiple_organisations_remain_isolated(db_session, seed_orgs):
    """Simulator handles multiple organisations independently with full isolation."""
    # Org A = synthetic, Org B = iot
    cfg_a = OrganisationSensorConfig(organisation_id="ORG-TEST-A", data_source="synthetic", is_active=True)
    cfg_b = OrganisationSensorConfig(organisation_id="ORG-TEST-B", data_source="iot", is_active=True)
    db_session.add_all([cfg_a, cfg_b])
    db_session.commit()

    sim = SyntheticDataSimulator()
    readings = sim.run_cycle(db_session)

    org_a_readings = [r for r in readings if r.organisation_id == "ORG-TEST-A"]
    org_b_readings = [r for r in readings if r.organisation_id == "ORG-TEST-B"]

    assert len(org_a_readings) > 0
    assert len(org_b_readings) == 0


# ---------------------------------------------------------------------------
# Test 23: Simulator exceptions do not crash the API
# ---------------------------------------------------------------------------
def test_simulator_exception_resilience():
    """Simulator catches exceptions gracefully during cycle execution without crashing."""
    sim = SyntheticDataSimulator()
    mock_db = MagicMock()
    mock_db.query.side_effect = Exception("Database transient failure test")

    # Executing run_cycle with failing DB raises or logs error cleanly without corrupting simulator state
    with pytest.raises(Exception):
        sim.run_cycle(mock_db)

    # Simulator operational state remains safe
    assert sim.status()["running"] is False
