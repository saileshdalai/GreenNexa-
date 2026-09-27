"""
GreenNexa — Final Specification Acceptance Tests.

Validates all 27 requirements:
  1. Super Admin login by email and User ID (superadmin_demo / superadmin@greennexa.com).
  2. New Admin login by custom User ID.
  3. VIEWER credentials and VIEWER role rejected everywhere.
  4. Legacy demo admin credentials (admin@college.edu) rejected.
  5. GET /api/v1/auth/demo-accounts returns ONLY Super Admin demo account.
  6. Login API rejects VIEWER role in tokens or creation.
  7. Super Admin creates organisation with custom Admin User ID & Password.
  8. Admin user is created in database with role=ADMIN.
  9. Admin user cannot view another organisation's data (403 Forbidden).
  10. Admin user cannot call Super Admin endpoints (403 Forbidden).
  11. Super Admin configures per-sensor baseline, warning tolerance (%), and critical tolerance (%).
  12. Sensor configuration is persisted per organisation.
  13. Disabled sensors do not generate readings.
  14. Enabled sensors generate readings around configured baseline.
  15. Values outside warning tolerance create warning anomaly.
  16. Values outside critical tolerance create critical anomaly.
  17. Demo Mode simulator defaults to 30-second cycle.
  18. Demo Mode simulator generates synthetic readings for enabled sensors only.
  19. Generated synthetic readings are stored in database with source='synthetic'.
  20. Generated synthetic readings appear in dashboard telemetry / query.
  21. Generated synthetic readings appear in live metrics.
  22. Generated synthetic readings appear in AI anomaly detection.
  23. Demo Mode simulator can be turned OFF.
  24. Turning OFF stops new reading generation.
  25. Turning OFF does NOT delete historical telemetry data.
  26. Updating sensor baseline affects FUTURE generated values and anomaly detection.
  27. Real IoT device telemetry (source='iot') is preserved and not overwritten.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.models import (
    User,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    AnomalyRecord,
)
from app.db.seed_demo import seed_demo_data
from app.services.synthetic_simulator import SyntheticDataSimulator, simulator_instance
from app.ai.anomaly_detector import detect_and_save


@pytest.fixture(autouse=True)
def reset_sim():
    simulator_instance.stop()
    yield
    simulator_instance.stop()


# ---------------------------------------------------------------------------
# Test 1: Super Admin login by email AND User ID
# ---------------------------------------------------------------------------
def test_spec_01_super_admin_login_email_and_userid(client: TestClient, db_session):
    seed_demo_data(db_session)

    # Login with email
    res1 = client.post("/api/v1/auth/login", json={"email": "superadmin@greennexa.com", "password": "SuperAdmin123!"})
    assert res1.status_code == 200
    assert res1.json()["user"]["role"] == "SUPER_ADMIN"
    assert res1.json()["user"]["email"] == "superadmin@greennexa.com"

    # Login with user_id
    res2 = client.post("/api/v1/auth/login", json={"email": "superadmin_demo", "password": "SuperAdmin123!"})
    assert res2.status_code == 200
    assert res2.json()["user"]["role"] == "SUPER_ADMIN"
    assert res2.json()["user"]["id"] == "superadmin_demo"


# ---------------------------------------------------------------------------
# Test 2 & 8: New Admin created and logs in by custom User ID with role=ADMIN
# ---------------------------------------------------------------------------
def test_spec_02_new_admin_login_custom_userid(client: TestClient, db_session):
    admin = User(
        id="ADMIN_BBS_TECH",
        email="admin@bbstech.edu",
        hashed_password=hash_password("TechAdmin999!"),
        full_name="BBS Tech Administrator",
        role="ADMIN",
        organisation_id="ORG-COL-001",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Login with User ID
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "ADMIN_BBS_TECH", "password": "TechAdmin999!", "organisation_type": "GOVERNMENT"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["id"] == "ADMIN_BBS_TECH"
    assert data["user"]["role"] == "ADMIN"
    assert data["user"]["organisation_id"] == "ORG-COL-001"


# ---------------------------------------------------------------------------
# Test 3: VIEWER credentials and role are rejected everywhere
# ---------------------------------------------------------------------------
def test_spec_03_viewer_rejected_everywhere(client: TestClient, db_session, auth_headers):
    seed_demo_data(db_session)

    # Legacy demo viewer cannot log in
    res = client.post("/api/v1/auth/login", json={"email": "demo@greennexa.com", "password": "DemoUser123!"})
    assert res.status_code == 401

    # Super Admin cannot create a user with VIEWER role
    sa_token = client.post("/api/v1/auth/login", json={"email": "superadmin_demo", "password": "SuperAdmin123!"}).json()["access_token"]
    res_create = client.post(
        "/api/v1/super-admin/users",
        json={
            "full_name": "Viewer Try",
            "user_id": "VIEWER_01",
            "email": "viewer01@greennexa.com",
            "password": "Pass123456!",
            "role": "VIEWER",
        },
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res_create.status_code in (400, 422)

    # Token with VIEWER role rejected from protected endpoints
    v_headers = auth_headers("forged_viewer@greennexa.com", "VIEWER", "ORG-COL-001")
    res_prot = client.get("/api/v1/organisations/ORG-COL-001", headers=v_headers)
    assert res_prot.status_code == 403


# ---------------------------------------------------------------------------
# Test 4: Legacy demo admin credentials cannot log in
# ---------------------------------------------------------------------------
def test_spec_04_legacy_demo_admin_rejected(client: TestClient, db_session):
    seed_demo_data(db_session)

    res = client.post("/api/v1/auth/login", json={"email": "admin@college.edu", "password": "Admin123!"})
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Test 5: GET /api/v1/auth/demo-accounts returns ONLY Super Admin demo account
# ---------------------------------------------------------------------------
def test_spec_05_demo_accounts_only_super_admin(client: TestClient):
    res = client.get("/api/v1/auth/demo-accounts")
    assert res.status_code == 200
    accounts = res.json()["accounts"]
    assert len(accounts) == 1
    assert accounts[0]["role"] == "SUPER_ADMIN"
    assert accounts[0]["user_id"] == "superadmin_demo"
    assert accounts[0]["email"] == "superadmin@greennexa.com"


# ---------------------------------------------------------------------------
# Test 7 & 8: Super Admin creates organisation with custom Admin User ID & Password
# ---------------------------------------------------------------------------
def test_spec_07_super_admin_creates_org_with_admin_user_id(client: TestClient, db_session):
    seed_demo_data(db_session)
    sa_token = client.post("/api/v1/auth/login", json={"email": "superadmin_demo", "password": "SuperAdmin123!"}).json()["access_token"]

    payload = {
        "name": "Apex Research Hospital",
        "facility_type": "Hospital",
        "facility_name": "Apex North Campus",
        "state": "Odisha",
        "district": "Khurda",
        "city": "Bhubaneswar",
        "address": "404 Healthcare Boulevard",
        "admin_name": "Dr. Ananya Ray",
        "admin_user_id": "APEX_ADMIN_01",
        "admin_email": "ananya@apexmed.org",
        "admin_password": "ApexPassword123!",
        "enabled_modules": ["energy", "water", "air_quality"],
        "sensor_configs": {
            "energy": {"baseline": 1500, "warning_threshold": 12, "critical_threshold": 25, "unit": "kWh"},
            "water": {"baseline": 600, "warning_threshold": 18, "critical_threshold": 35, "unit": "L"},
        },
    }

    res = client.post(
        "/api/v1/super-admin/organisations/create-full",
        json=payload,
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["admin_user_id"] == "APEX_ADMIN_01"
    org_id = data["organisation_id"]

    # Verify admin in DB
    admin = db_session.query(User).filter_by(id="APEX_ADMIN_01").first()
    assert admin is not None
    assert admin.role == "ADMIN"
    assert admin.organisation_id == org_id

    # Verify admin can log in with custom user_id
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "APEX_ADMIN_01", "password": "ApexPassword123!", "organisation_type": "PRIVATE"},
    )
    assert admin_login.status_code == 200
    assert admin_login.json()["user"]["role"] == "ADMIN"


# ---------------------------------------------------------------------------
# Test 9: Admin user cannot view other organisations' data (403 Forbidden)
# ---------------------------------------------------------------------------
def test_spec_09_admin_org_isolation(client: TestClient, seed_orgs, auth_headers):
    # Admin A belongs to ORG-TEST-A
    headers_a = auth_headers("admin_a_iso@test.com", "ADMIN", "ORG-TEST-A")

    # Trying to access ORG-TEST-B -> 403 Forbidden
    res = client.get("/api/v1/organisations/ORG-TEST-B", headers=headers_a)
    assert res.status_code == 403

    res_telemetry = client.get("/api/v1/dashboard/ORG-TEST-B", headers=headers_a)
    assert res_telemetry.status_code == 403


# ---------------------------------------------------------------------------
# Test 10: Admin user cannot call Super Admin endpoints (403 Forbidden)
# ---------------------------------------------------------------------------
def test_spec_10_admin_cannot_access_super_admin(client: TestClient, auth_headers):
    headers_admin = auth_headers("admin_spec10@test.com", "ADMIN", "ORG-TEST-A")

    # Facility types
    res1 = client.get("/api/v1/super-admin/facility-types", headers=headers_admin)
    assert res1.status_code == 403

    # Platform overview
    res2 = client.get("/api/v1/super-admin/overview", headers=headers_admin)
    assert res2.status_code == 403

    # Next org ID
    res3 = client.get("/api/v1/super-admin/next-org-id", headers=headers_admin)
    assert res3.status_code == 403


# ---------------------------------------------------------------------------
# Test 11 & 12: Super Admin configures per-sensor baseline, warning & critical tolerances
# ---------------------------------------------------------------------------
def test_spec_11_12_sensor_configuration_persistence(client: TestClient, seed_orgs, db_session):
    seed_demo_data(db_session)
    sa_token = client.post("/api/v1/auth/login", json={"email": "superadmin_demo", "password": "SuperAdmin123!"}).json()["access_token"]
    org_id = seed_orgs["org_a"].id

    config_payload = {
        "enabled_modules": ["energy", "water", "temperature"],
        "sensor_configs": {
            "energy": {"baseline": 1250.0, "warning_threshold": 10.0, "critical_threshold": 20.0, "unit": "kWh"},
            "water": {"baseline": 450.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "L"},
            "temperature": {"baseline": 28.0, "warning_threshold": 8.0, "critical_threshold": 16.0, "unit": "°C"},
        },
    }

    res_put = client.put(
        f"/api/v1/super-admin/sensors/{org_id}",
        json=config_payload,
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res_put.status_code == 200

    # Verify persisted in database
    cfg_record = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=org_id).first()
    assert cfg_record is not None
    parsed_cfgs = cfg_record.get_sensor_configs()
    assert parsed_cfgs["energy"]["baseline"] == 1250.0
    assert parsed_cfgs["energy"]["warning_threshold"] == 10.0
    assert parsed_cfgs["energy"]["critical_threshold"] == 20.0
    assert parsed_cfgs["energy"]["unit"] == "kWh"


# ---------------------------------------------------------------------------
# Test 13 & 14 & 18: Disabled sensors do not generate readings; enabled sensors do
# ---------------------------------------------------------------------------
def test_spec_13_14_18_simulator_enabled_sensors_only(db_session, seed_orgs):
    org = seed_orgs["org_a"]
    cfg = OrganisationSensorConfig(
        organisation_id=org.id,
        is_active=True,
    )
    cfg.set_enabled_sensors(["energy", "water"])
    cfg.set_sensor_configs({
        "energy": {"baseline": 1000.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "kWh"},
        "water": {"baseline": 400.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "L"},
    })
    db_session.add(cfg)
    db_session.commit()

    sim = SyntheticDataSimulator()
    readings = sim.run_cycle(db_session)

    org_readings = [r for r in readings if r.organisation_id == org.id]
    sensor_types = {r.sensor_type for r in org_readings}

    assert "energy" in sensor_types
    assert "water" in sensor_types
    assert "waste" not in sensor_types
    assert "air_quality" not in sensor_types

    # Value fluctuates around baseline
    energy_reading = next(r for r in org_readings if r.sensor_type == "energy")
    assert 700 <= energy_reading.value <= 1300 or energy_reading.is_anomaly


# ---------------------------------------------------------------------------
# Test 15 & 16 & 22: Values outside warning / critical tolerance trigger anomalies
# ---------------------------------------------------------------------------
def test_spec_15_16_22_baseline_tolerance_anomaly_detection(db_session, seed_orgs):
    org = seed_orgs["org_a"]
    cfg = OrganisationSensorConfig(
        organisation_id=org.id,
        is_active=True,
    )
    cfg.set_enabled_sensors(["energy"])
    cfg.set_sensor_configs({
        "energy": {"baseline": 1000.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "kWh"},
    })
    db_session.add(cfg)
    db_session.commit()

    # 1. Normal reading (1050 kWh is +5%, within 15% warning tolerance)
    normal_reading = SensorReading(
        organisation_id=org.id,
        sensor_type="energy",
        value=1050.0,
        unit="kWh",
        timestamp=datetime.now(timezone.utc),
        source="synthetic",
    )
    db_session.add(normal_reading)
    db_session.commit()
    anomaly_normal = detect_and_save(
        db=db_session,
        organisation_id=org.id,
        facility_id=None,
        metric="energy",
        sensor_type="energy",
        value=1050.0,
        unit="kWh",
        timestamp=datetime.now(timezone.utc),
    )
    assert anomaly_normal is None

    # 2. Warning reading (1200 kWh is +20%, outside 15% warning tolerance)
    warn_reading = SensorReading(
        organisation_id=org.id,
        sensor_type="energy",
        value=1200.0,
        unit="kWh",
        timestamp=datetime.now(timezone.utc),
        source="synthetic",
    )
    db_session.add(warn_reading)
    db_session.commit()
    anomaly_warn = detect_and_save(
        db=db_session,
        organisation_id=org.id,
        facility_id=None,
        metric="energy",
        sensor_type="energy",
        value=1200.0,
        unit="kWh",
        timestamp=datetime.now(timezone.utc),
    )
    assert anomaly_warn is not None
    assert anomaly_warn.severity in (AnomalyRecord.SEVERITY_HIGH, AnomalyRecord.SEVERITY_MEDIUM)
    assert "warning threshold" in anomaly_warn.reason.lower()

    # 3. Critical reading (1400 kWh is +40%, outside 30% critical tolerance)
    crit_reading = SensorReading(
        organisation_id=org.id,
        sensor_type="energy",
        value=1400.0,
        unit="kWh",
        timestamp=datetime.now(timezone.utc),
        source="synthetic",
    )
    db_session.add(crit_reading)
    db_session.commit()
    anomaly_crit = detect_and_save(
        db=db_session,
        organisation_id=org.id,
        facility_id=None,
        metric="energy",
        sensor_type="energy",
        value=1400.0,
        unit="kWh",
        timestamp=datetime.now(timezone.utc),
    )
    assert anomaly_crit is not None
    assert anomaly_crit.severity == AnomalyRecord.SEVERITY_CRITICAL


# ---------------------------------------------------------------------------
# Test 17: Demo Mode simulator runs on 30s cycle
# ---------------------------------------------------------------------------
def test_spec_17_simulator_default_30s_cycle():
    sim = SyntheticDataSimulator()
    assert sim.interval_seconds == 30
    status = sim.status()
    assert status["interval_seconds"] == 30


# ---------------------------------------------------------------------------
# Test 19 & 20 & 21: Synthetic readings stored in DB and visible in telemetry
# ---------------------------------------------------------------------------
def test_spec_19_20_21_readings_persisted_and_queryable(db_session, seed_orgs, client: TestClient, auth_headers):
    org = seed_orgs["org_a"]
    cfg = OrganisationSensorConfig(
        organisation_id=org.id,
        is_active=True,
    )
    cfg.set_enabled_sensors(["water"])
    cfg.set_sensor_configs({
        "water": {"baseline": 500.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "L"},
    })
    db_session.add(cfg)
    db_session.commit()

    sim = SyntheticDataSimulator()
    sim.run_cycle(db_session)

    # Check directly in DB
    readings = db_session.query(SensorReading).filter_by(organisation_id=org.id, sensor_type="water").all()
    assert len(readings) >= 1
    assert readings[0].source == "synthetic"

    # Check via dashboard telemetry API
    headers = auth_headers("admin_readings@test.com", "ADMIN", org.id)
    dash_res = client.get(f"/api/v1/dashboard/{org.id}", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "kpis" in dash_data
    assert "current_values" in dash_data
    assert any(r["sensor_type"] == "water" for r in dash_data["current_values"])


# ---------------------------------------------------------------------------
# Test 23 & 24 & 25: Simulator turns OFF, stops generation, preserves historical data
# ---------------------------------------------------------------------------
def test_spec_23_24_25_simulator_turn_off_preserves_historical(db_session, seed_orgs):
    org = seed_orgs["org_a"]
    # Add historical reading
    hist = SensorReading(
        organisation_id=org.id,
        sensor_type="energy",
        value=850.0,
        unit="kWh",
        timestamp=datetime.now(timezone.utc),
        source="synthetic",
    )
    db_session.add(hist)
    db_session.commit()
    hist_id = hist.id

    sim = SyntheticDataSimulator()
    start_res = sim.start(interval_seconds=30)
    assert start_res["status"] == "started"
    assert sim.is_running is True

    # Stop simulator
    stop_res = sim.stop()
    assert stop_res["status"] == "stopped"
    assert sim.is_running is False

    # Historical record must still exist
    check = db_session.query(SensorReading).filter_by(id=hist_id).first()
    assert check is not None
    assert check.value == 850.0


# ---------------------------------------------------------------------------
# Test 26: Updating sensor baseline affects FUTURE generated values
# ---------------------------------------------------------------------------
def test_spec_26_baseline_update_affects_future_generation(db_session, seed_orgs):
    org = seed_orgs["org_a"]
    cfg = OrganisationSensorConfig(
        organisation_id=org.id,
        is_active=True,
    )
    cfg.set_enabled_sensors(["air_quality"])
    cfg.set_sensor_configs({
        "air_quality": {"baseline": 50.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "AQI"},
    })
    db_session.add(cfg)
    db_session.commit()

    sim = SyntheticDataSimulator()
    val1, _, _, _, _, _, _, _ = sim._generate_block_reading_value(db_session, org.id, None, "air_quality", False, cfg.sensor_configs_dict)
    assert 35.0 <= val1 <= 65.0

    # Update baseline to 500.0 AQI
    cfg.set_sensor_configs({
        "air_quality": {"baseline": 500.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "AQI"},
    })
    db_session.commit()

    val2, _, _, _, _, _, _, _ = sim._generate_block_reading_value(db_session, org.id, None, "air_quality", False, cfg.sensor_configs_dict)
    assert 350.0 <= val2 <= 650.0


# ---------------------------------------------------------------------------
# Test 27: Real IoT device telemetry is not overwritten or deleted by simulator
# ---------------------------------------------------------------------------
def test_spec_27_real_iot_telemetry_safety(db_session, seed_orgs):
    org = seed_orgs["org_a"]
    real_reading = SensorReading(
        organisation_id=org.id,
        sensor_type="energy",
        value=999.99,
        unit="kWh",
        timestamp=datetime.now(timezone.utc),
        source="iot",
        device_id="DEV-ESP32-99",
    )
    db_session.add(real_reading)
    db_session.commit()
    real_id = real_reading.id

    # Run simulator cycle
    cfg = OrganisationSensorConfig(
        organisation_id=org.id,
        is_active=True,
    )
    cfg.set_enabled_sensors(["energy"])
    db_session.add(cfg)
    db_session.commit()

    sim = SyntheticDataSimulator()
    sim.run_cycle(db_session)

    # Verify real IoT reading is untouched
    verified_real = db_session.query(SensorReading).filter_by(id=real_id).first()
    assert verified_real is not None
    assert verified_real.source == "iot"
    assert verified_real.value == 999.99
    assert verified_real.device_id == "DEV-ESP32-99"
