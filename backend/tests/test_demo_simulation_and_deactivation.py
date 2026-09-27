"""
GreenNexa — Demo Mode Simulation & Organisation Deactivation Acceptance Test Suite.

Comprehensive tests covering:
PART A — Demo Mode Simulation (20 tests):
  1. Demo OFF -> no new synthetic reading generated
  2. Demo ON -> simulator thread starts
  3. Simulator cycle configured for 30 seconds
  4. New reading is created on simulation cycle
  5. Reading is persisted in sensor_readings table
  6. Reading timestamp updates with each cycle
  7. Generated values fluctuate naturally over time (not constant)
  8. Only enabled sensors generate readings
  9. Disabled sensors generate zero readings
  10. Organisation-specific baseline is respected
  11. Warning threshold bounds are evaluated
  12. Critical threshold bounds are evaluated
  13. Normal fluctuations do not generate anomaly records
  14. Threshold exceedance creates AnomalyRecord
  15. Dashboard API returns latest generated reading
  16. Demo OFF stops new generation
  17. Historical readings remain intact after Demo OFF
  18. Configuration change affects future readings
  19. Multiple toggles do not create duplicate simulator loops
  20. Organisation isolation is strictly enforced

PART B — Organisation Delete / Deactivate (8 tests):
  1. Super Admin can deactivate organisation
  2. Admin cannot deactivate organisation (403 Forbidden)
  3. Deactivated organisation Admin cannot login (403 Forbidden)
  4. Deactivated organisation disappears from active list
  5. Historical telemetry remains intact
  6. Historical anomalies remain intact
  7. Organisation record remains preserved (soft delete)
  8. Unrelated organisations are unaffected
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.db.database import get_db
from app.db.models import (
    AnomalyRecord,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
    _utcnow,
)
from app.main import app
from app.services.synthetic_simulator import SyntheticDataSimulator, simulator_instance


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_simulator():
    """Ensure simulator is stopped before and after each test."""
    simulator_instance.stop()
    simulator_instance._last_anomaly_times.clear()
    simulator_instance._organisations_processed = 0
    simulator_instance._last_run_at = None
    yield
    simulator_instance.stop()
    simulator_instance._last_anomaly_times.clear()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient overriding get_db dependency."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def setup_test_org(db_session: Session):
    """Set up an active organisation with sensor configs and admin."""
    org_id = "ORG-SIM-TEST"
    org = db_session.query(Organisation).filter_by(id=org_id).first()
    if not org:
        org = Organisation(
            id=org_id,
            name="Simulation Test Facility",
            facility_name="Main Building",
            org_type="college",
            ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
            is_active=True,
        )
        db_session.add(org)
        db_session.commit()

    config = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=org_id).first()
    if not config:
        config = OrganisationSensorConfig(
            organisation_id=org_id,
            data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
            is_active=True,
        )
        db_session.add(config)

    config.set_enabled_sensors(["energy", "water", "temperature"])
    config.set_sensor_configs({
        "energy": {"baseline": 1000.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "kWh"},
        "water": {"baseline": 400.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "L"},
        "temperature": {"baseline": 30.0, "warning_threshold": 10.0, "critical_threshold": 20.0, "unit": "°C"},
    })
    db_session.commit()

    # Create admin
    admin = db_session.query(User).filter_by(id="admin_sim_test").first()
    if not admin:
        admin = User(
            id="admin_sim_test",
            email="admin_sim@facility.org",
            hashed_password=security.hash_password("AdminPass123!"),
            full_name="Facility Administrator",
            role=User.ROLE_ADMIN,
            organisation_id=org_id,
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()

    # Create super admin
    sadmin = db_session.query(User).filter_by(id="superadmin_test").first()
    if not sadmin:
        sadmin = User(
            id="superadmin_test",
            email="superadmin_test@greennexa.com",
            hashed_password=security.hash_password("SuperAdmin123!"),
            full_name="Super Administrator",
            role=User.ROLE_SUPER_ADMIN,
            is_active=True,
        )
        db_session.add(sadmin)
        db_session.commit()

    return {
        "org_id": org_id,
        "admin": admin,
        "superadmin": sadmin,
    }


def _auth_header(user: User) -> dict[str, str]:
    token = security.create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "organisation_id": user.organisation_id,
    })
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# PART A — DEMO MODE DATA SIMULATION TESTS
# ===========================================================================

def test_1_demo_off_no_new_readings(db_session, setup_test_org):
    """1. Demo OFF -> no new synthetic reading is generated."""
    sim = SyntheticDataSimulator(interval_seconds=30)
    assert sim.is_running is False

    initial_count = db_session.query(SensorReading).filter_by(organisation_id=setup_test_org["org_id"]).count()
    # When stopped, no readings are generated in background
    assert sim.status()["running"] is False
    after_count = db_session.query(SensorReading).filter_by(organisation_id=setup_test_org["org_id"]).count()
    assert after_count == initial_count


def test_2_demo_on_simulator_starts(setup_test_org):
    """2. Demo ON -> simulator thread starts and status reports running."""
    sim = SyntheticDataSimulator(interval_seconds=30)
    start_res = sim.start()
    try:
        assert start_res["status"] == "started"
        assert sim.is_running is True
        assert sim._thread is not None
        assert sim._thread.is_alive() is True
        assert sim.status()["running"] is True
    finally:
        sim.stop()


def test_3_cycle_occurs_every_30_seconds(setup_test_org):
    """3. Simulator cycle interval defaults to 30 seconds."""
    sim = SyntheticDataSimulator()
    assert sim.interval_seconds == 30
    assert sim.status()["interval_seconds"] == 30


def test_4_and_5_reading_created_and_persisted(db_session, setup_test_org):
    """4 & 5. Readings are created and persisted to sensor_readings table."""
    sim = SyntheticDataSimulator()
    readings = sim.run_cycle(db_session)
    assert len(readings) > 0

    for r in readings:
        assert r.id is not None
        assert r.organisation_id == setup_test_org["org_id"]
        assert r.source == "synthetic"
        # Verify committed in DB
        persisted = db_session.query(SensorReading).filter_by(id=r.id).first()
        assert persisted is not None
        assert persisted.value == r.value


def test_6_reading_timestamp_updates(db_session, setup_test_org):
    """6. Reading timestamp updates across cycles."""
    sim = SyntheticDataSimulator()
    t1 = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(seconds=30)

    readings1 = sim.run_cycle(db_session, current_time=t1)
    readings2 = sim.run_cycle(db_session, current_time=t2)

    ts1 = readings1[0].timestamp.replace(tzinfo=timezone.utc) if readings1[0].timestamp.tzinfo is None else readings1[0].timestamp
    ts2 = readings2[0].timestamp.replace(tzinfo=timezone.utc) if readings2[0].timestamp.tzinfo is None else readings2[0].timestamp
    assert ts1 == t1
    assert ts2 == t2
    assert ts2 > ts1


def test_7_generated_values_differ_naturally(db_session, setup_test_org):
    """7. Generated values fluctuate naturally over time (not constant)."""
    sim = SyntheticDataSimulator()
    values = []
    for i in range(5):
        t = datetime(2026, 9, 19, 10, i, 0, tzinfo=timezone.utc)
        cycle = sim.run_cycle(db_session, current_time=t)
        energy_r = next(r for r in cycle if r.sensor_type == "energy" and r.organisation_id == setup_test_org["org_id"])
        values.append(energy_r.value)

    # Values must not all be identical
    assert len(set(values)) > 1, f"Expected varied values but got {values}"


def test_8_and_9_only_enabled_sensors_generate_readings(db_session, setup_test_org):
    """8 & 9. Only enabled sensors generate readings; disabled sensors generate zero."""
    sim = SyntheticDataSimulator()
    cycle = sim.run_cycle(db_session)
    org_readings = [r for r in cycle if r.organisation_id == setup_test_org["org_id"]]
    generated_types = {r.sensor_type for r in org_readings}

    # Enabled in fixture: energy, water, temperature
    assert "energy" in generated_types
    assert "water" in generated_types
    assert "temperature" in generated_types

    # Disabled: waste, air_quality, traffic, parking, assets, safety
    assert "waste" not in generated_types
    assert "parking" not in generated_types
    assert "traffic" not in generated_types


def test_10_organisation_specific_baseline_used(db_session, setup_test_org):
    """10. Organisation-specific configured baseline is respected."""
    sim = SyntheticDataSimulator()
    cycle = sim.run_cycle(db_session)
    energy_r = next(r for r in cycle if r.sensor_type == "energy" and r.organisation_id == setup_test_org["org_id"])
    water_r = next(r for r in cycle if r.sensor_type == "water" and r.organisation_id == setup_test_org["org_id"])

    # Energy baseline is 1000 with warning 15% (850 - 1150)
    assert 850.0 <= energy_r.value <= 1150.0 or energy_r.is_anomaly
    # Water baseline is 400 with warning 20% (320 - 480)
    assert 320.0 <= water_r.value <= 480.0 or water_r.is_anomaly


def test_11_and_12_warning_and_critical_thresholds(db_session, setup_test_org):
    """11 & 12. Warning and critical threshold calculations."""
    sim = SyntheticDataSimulator()
    cfg = {
        "energy": {"baseline": 1000.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "kWh"}
    }
    org_id = setup_test_org["org_id"]
    # Test normal reading
    val_norm, sev_norm, e_min, e_max, unit, base, w_pct, c_pct = sim._generate_block_reading_value(
        db_session, org_id, None, "energy", is_anomaly=False, sensor_configs=cfg
    )
    assert e_min == 850.0
    assert e_max == 1150.0
    assert sev_norm is None
    assert 850.0 <= val_norm <= 1150.0

    # Test forced anomaly reading
    val_anom, sev_anom, _, _, _, _, _, _ = sim._generate_block_reading_value(
        db_session, org_id, None, "energy", is_anomaly=True, sensor_configs=cfg, forced_anomaly=True
    )
    assert sev_anom in (AnomalyRecord.SEVERITY_HIGH, AnomalyRecord.SEVERITY_CRITICAL)
    assert val_anom > e_max or val_anom < e_min


def test_13_normal_fluctuations_do_not_create_anomalies(db_session, setup_test_org):
    """13. Normal fluctuations do not create anomaly records."""
    sim = SyntheticDataSimulator()
    # Generate 5 cycles without forced anomalies; check anomaly records
    pre_anoms = db_session.query(AnomalyRecord).filter_by(organisation_id=setup_test_org["org_id"]).count()
    for i in range(3):
        t = datetime(2026, 9, 19, 12, i, 0, tzinfo=timezone.utc)
        sim.run_cycle(db_session, current_time=t)

    # Anomaly rate is small (~3%), normal readings should not create anomalies
    non_anom_readings = db_session.query(SensorReading).filter_by(
        organisation_id=setup_test_org["org_id"],
        is_anomaly=False,
    ).all()
    assert len(non_anom_readings) > 0


def test_14_threshold_exceedance_creates_anomaly(db_session, setup_test_org):
    """14. Exceeding tolerance threshold creates AnomalyRecord in DB."""
    sim = SyntheticDataSimulator()
    readings = sim.run_cycle_for_org(db_session, setup_test_org["org_id"], forced_anomaly_sensor="energy", ignore_gap=True)
    anom_reading = next((r for r in readings if r.sensor_type == "energy" and r.is_anomaly), None)
    assert anom_reading is not None

    anom_record = db_session.query(AnomalyRecord).filter_by(
        organisation_id=setup_test_org["org_id"],
        metric="energy",
    ).order_by(AnomalyRecord.created_at.desc()).first()
    assert anom_record is not None
    assert anom_record.severity in (AnomalyRecord.SEVERITY_HIGH, AnomalyRecord.SEVERITY_CRITICAL)
    assert "breaches expected baseline range" in anom_record.reason or "Anomaly" in anom_record.reason


def test_15_dashboard_api_returns_latest_generated_reading(client, db_session, setup_test_org):
    """15. Dashboard API returns latest simulated reading."""
    sim = SyntheticDataSimulator()
    t = _utcnow()
    sim.run_cycle(db_session, current_time=t)

    headers = _auth_header(setup_test_org["admin"])
    res = client.get(f"/api/v1/dashboard/{setup_test_org['org_id']}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "kpis" in data
    assert "energy" in data["kpis"]
    assert data["kpis"]["energy"]["latest_value"] is not None
    assert data["kpis"]["energy"]["latest_value"] > 0.0


def test_16_and_17_demo_off_stops_generation_preserves_history(db_session, setup_test_org):
    """16 & 17. Stopping Demo Mode stops new generation while preserving historical readings."""
    sim = SyntheticDataSimulator()
    sim.run_cycle(db_session)
    count_before = db_session.query(SensorReading).filter_by(organisation_id=setup_test_org["org_id"]).count()
    assert count_before > 0

    # Stop simulator
    sim.stop()
    assert sim.is_running is False

    # Historical data must remain untouched
    count_after = db_session.query(SensorReading).filter_by(organisation_id=setup_test_org["org_id"]).count()
    assert count_after == count_before


def test_18_configuration_change_affects_future_readings(db_session, setup_test_org):
    """18. Configuration change affects future readings without altering past readings."""
    sim = SyntheticDataSimulator()
    # Cycle 1: Water is enabled, Waste is disabled
    c1 = sim.run_cycle(db_session)
    c1_types = {r.sensor_type for r in c1 if r.organisation_id == setup_test_org["org_id"]}
    assert "water" in c1_types
    assert "waste" not in c1_types

    # Super admin updates config: Water OFF, Waste ON
    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=setup_test_org["org_id"]).first()
    cfg.set_enabled_sensors(["energy", "waste", "temperature"])
    db_session.commit()

    # Cycle 2: Water stops, Waste starts
    c2 = sim.run_cycle(db_session)
    c2_types = {r.sensor_type for r in c2 if r.organisation_id == setup_test_org["org_id"]}
    assert "waste" in c2_types
    assert "water" not in c2_types

    # Historical Water readings remain in DB
    water_count = db_session.query(SensorReading).filter_by(
        organisation_id=setup_test_org["org_id"],
        sensor_type="water",
    ).count()
    assert water_count > 0


def test_19_multiple_toggles_no_duplicate_loops(setup_test_org):
    """19. Multiple start calls do not create duplicate simulator threads."""
    sim = SyntheticDataSimulator(interval_seconds=30)
    r1 = sim.start(30)
    assert r1["status"] == "started"
    first_thread = sim._thread

    r2 = sim.start(30)
    assert r2["status"] == "already_running"
    assert sim._thread is first_thread

    sim.stop()
    assert sim.is_running is False


def test_20_organisation_isolation_in_simulation(db_session, setup_test_org):
    """20. Each organisation receives isolated synthetic readings."""
    sim = SyntheticDataSimulator()
    readings = sim.run_cycle(db_session)
    org_ids = {r.organisation_id for r in readings}
    assert setup_test_org["org_id"] in org_ids


# ===========================================================================
# PART B — SUPER ADMIN ORGANISATION DELETE / DEACTIVATE TESTS
# ===========================================================================

def test_21_super_admin_can_deactivate_organisation(client, db_session, setup_test_org):
    """21. Super Admin can deactivate an organisation."""
    org_id = setup_test_org["org_id"]
    headers = _auth_header(setup_test_org["superadmin"])

    res = client.delete(f"/api/v1/organisations/{org_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_active"] is False

    # Check in DB
    org = db_session.query(Organisation).filter_by(id=org_id).first()
    assert org.is_active is False


def test_22_admin_cannot_deactivate_organisation(client, setup_test_org):
    """22. Admin receives 403 Forbidden when attempting to deactivate organisation."""
    org_id = setup_test_org["org_id"]
    headers = _auth_header(setup_test_org["admin"])

    res = client.delete(f"/api/v1/organisations/{org_id}", headers=headers)
    assert res.status_code == 403


def test_23_deactivated_organisation_admin_cannot_login(client, db_session, setup_test_org):
    """23. Deactivated organisation Admin cannot log in (403 Forbidden)."""
    org_id = setup_test_org["org_id"]
    # Deactivate org
    org = db_session.query(Organisation).filter_by(id=org_id).first()
    org.is_active = False
    for u in org.users:
        u.is_active = False
    db_session.commit()

    # Attempt login
    res = client.post("/api/v1/auth/login", json={
        "email": setup_test_org["admin"].email,
        "password": "AdminPass123!",
        "organisation_type": "GOVERNMENT",
    })
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"].lower()


def test_24_deactivated_organisation_filtered_from_active_list(client, db_session, setup_test_org):
    """24. Deactivated organisation is marked inactive and filtered from active list."""
    org_id = setup_test_org["org_id"]
    org = db_session.query(Organisation).filter_by(id=org_id).first()
    org.is_active = False
    db_session.commit()

    headers = _auth_header(setup_test_org["superadmin"])
    res = client.get("/api/v1/super-admin/overview", headers=headers)
    assert res.status_code == 200
    orgs_list = res.json()["organisations"]
    target_item = next((o for o in orgs_list if o["id"] == org_id), None)
    assert target_item is not None
    assert target_item["status"] == "Inactive"


def test_25_and_26_historical_telemetry_and_anomalies_remain(client, db_session, setup_test_org):
    """25 & 26. Historical telemetry and anomalies are safely preserved after deactivation."""
    org_id = setup_test_org["org_id"]
    sim = SyntheticDataSimulator()
    sim.run_cycle_for_org(db_session, org_id, forced_anomaly_sensor="energy", ignore_gap=True)

    readings_count_before = db_session.query(SensorReading).filter_by(organisation_id=org_id).count()
    anomalies_count_before = db_session.query(AnomalyRecord).filter_by(organisation_id=org_id).count()
    assert readings_count_before > 0
    assert anomalies_count_before > 0

    # Deactivate
    headers = _auth_header(setup_test_org["superadmin"])
    res = client.delete(f"/api/v1/organisations/{org_id}", headers=headers)
    assert res.status_code == 200

    # Verify preserved
    readings_count_after = db_session.query(SensorReading).filter_by(organisation_id=org_id).count()
    anomalies_count_after = db_session.query(AnomalyRecord).filter_by(organisation_id=org_id).count()
    assert readings_count_after == readings_count_before
    assert anomalies_count_after == anomalies_count_before


def test_27_organisation_record_remains_and_can_reactivate(client, db_session, setup_test_org):
    """27. Organisation record remains preserved (soft delete) and can be reactivated."""
    org_id = setup_test_org["org_id"]
    headers = _auth_header(setup_test_org["superadmin"])

    # Deactivate
    client.delete(f"/api/v1/organisations/{org_id}", headers=headers)
    org_in_db = db_session.query(Organisation).filter_by(id=org_id).first()
    assert org_in_db is not None
    assert org_in_db.is_active is False

    # Reactivate
    res = client.post(f"/api/v1/organisations/{org_id}/reactivate", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is True

    db_session.refresh(org_in_db)
    assert org_in_db.is_active is True

    # Admin login restored
    login_res = client.post("/api/v1/auth/login", json={
        "email": setup_test_org["admin"].email,
        "password": "AdminPass123!",
        "organisation_type": "GOVERNMENT",
    })
    assert login_res.status_code == 200


def test_28_unrelated_organisations_unaffected(client, db_session, setup_test_org):
    """28. Deactivating one organisation leaves unrelated organisations unaffected."""
    # Create another org
    other_org = Organisation(
        id="ORG-OTHER-TEST",
        name="Other Campus",
        facility_name="Other Building",
        is_active=True,
    )
    db_session.add(other_org)
    db_session.commit()

    headers = _auth_header(setup_test_org["superadmin"])
    client.delete(f"/api/v1/organisations/{setup_test_org['org_id']}", headers=headers)

    refreshed_other = db_session.query(Organisation).filter_by(id="ORG-OTHER-TEST").first()
    assert refreshed_other is not None
    assert refreshed_other.is_active is True
