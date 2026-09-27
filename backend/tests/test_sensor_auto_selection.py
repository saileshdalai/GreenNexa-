"""
GreenNexa — Unit tests for Sensor Auto-Selection, Editable Control, and Simulator Integration.
"""

import pytest
from fastapi.testclient import TestClient
from app.db.models import Organisation, OrganisationSensorConfig, SensorReading
from app.core.sensor_catalog import (
    MASTER_SENSOR_CATALOG,
    RECOMMENDED_SENSORS_BY_TYPE,
    get_recommended_sensors_for_type,
    get_default_configs_for_sensors,
)
from app.services.synthetic_simulator import SyntheticDataSimulator


def get_token(client: TestClient, email: str, password: str, organisation_type: str = None) -> str:
    body = {"email": email, "password": password}
    if organisation_type:
        body["organisation_type"] = organisation_type
    res = client.post("/api/v1/auth/login", json=body)
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_get_master_sensor_catalog(client: TestClient):
    sa_token = get_token(client, "superadmin@greennexa.com", "SuperAdmin123!")

    # 1. Non-auth or regular user -> 401/403
    unauth_res = client.get("/api/v1/super-admin/sensor-catalog")
    assert unauth_res.status_code in (401, 403)

    # 2. Super Admin -> 200
    res = client.get(
        "/api/v1/super-admin/sensor-catalog",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "catalog" in data
    assert "categories" in data
    assert "recommendations" in data

    # Check categories
    cats = data["categories"]
    assert "CORE" in cats
    assert "MUNICIPALITY / OUTDOOR" in cats
    assert "ASSET / UTILISATION" in cats
    assert "INDUSTRIAL" in cats

    # Check catalog items
    catalog_ids = [s["id"] for s in data["catalog"]]
    assert "energy" in catalog_ids
    assert "water" in catalog_ids
    assert "water_flow" in catalog_ids
    assert "water_level" in catalog_ids
    assert "sewage_level" in catalog_ids
    assert "rainfall" in catalog_ids
    assert "pressure" in catalog_ids
    assert "vibration" in catalog_ids
    assert "flow" in catalog_ids
    assert "rpm" in catalog_ids
    assert "fire_smoke" in catalog_ids


def test_get_sensor_catalog_defaults_for_all_types(client: TestClient):
    sa_token = get_token(client, "superadmin@greennexa.com", "SuperAdmin123!")

    types_to_check = [
        ("Hospital", ["energy", "water", "waste", "air_quality", "temperature", "humidity", "equipment_asset", "occupancy", "safety"]),
        ("School", ["energy", "water", "waste", "air_quality", "temperature", "humidity", "occupancy", "safety"]),
        ("College / University", ["energy", "water", "waste", "air_quality", "temperature", "humidity", "equipment_asset", "occupancy", "parking", "safety"]),
        ("Water Pump Station", ["energy", "water", "water_flow", "water_level", "sewage_level", "equipment_asset", "pressure", "flow", "vibration", "machine_temperature", "safety"]),
        ("Municipality", ["energy", "water", "waste", "air_quality", "temperature", "humidity", "water_flow", "water_level", "sewage_level", "rainfall", "traffic", "parking", "safety"]),
        ("Industrial Organisation", ["energy", "water", "waste", "air_quality", "vibration", "pressure", "flow", "current_voltage", "rpm", "machine_temperature", "runtime_hours", "acoustic_sound", "gas", "dust_pm", "fire_smoke", "safety"]),
        ("Park", ["energy", "water", "water_flow", "air_quality", "rainfall", "temperature", "humidity", "safety"]),
    ]

    for type_name, expected_sensors in types_to_check:
        res = client.get(
            f"/api/v1/super-admin/sensor-catalog/defaults?type={type_name}",
            headers={"Authorization": f"Bearer {sa_token}"},
        )
        assert res.status_code == 200, f"Failed for {type_name}: {res.text}"
        data = res.json()
        assert "recommended_sensors" in data
        assert "default_configs" in data
        for s in expected_sensors:
            assert s in data["recommended_sensors"], f"{s} expected in defaults for {type_name}"
            assert s in data["default_configs"], f"{s} expected in default_configs for {type_name}"


def test_create_organisation_auto_selects_recommended_sensors(client: TestClient, db_session):
    sa_token = get_token(client, "superadmin@greennexa.com", "SuperAdmin123!")

    # Create a new Water Pump Station without passing explicit sensor_configs
    payload = {
        "name": "Kalinga Water Intake Station",
        "ownership_type": "GOVERNMENT",
        "facility_type": "Water Pump Station",
        "facility_name": "Intake Pump House",
        "state": "Odisha",
        "district": "Khurda",
        "city": "Bhubaneswar",
        "address": "Mahanadi Intake Canal, Sector 9",
        "org_code": "PMP-AUTO-01",
        "admin_name": "Pump Station Admin",
        "admin_user_id": "PUMP_AUTO_ADMIN",
        "admin_email": "pump_auto@greennexa.local",
        "admin_password": "PumpPassword123!",
        # enabled_modules intentionally omitted -> should auto-populate recommended defaults
    }

    res = client.post(
        "/api/v1/super-admin/organisations/create-full",
        json=payload,
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res.status_code == 201, res.text
    created = res.json()
    org_id = created["organisation_id"]

    # Verify sensor config in DB
    config = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=org_id).first()
    assert config is not None
    enabled = config.enabled_sensors_list

    # Water Pump Station recommendations must be auto-selected
    expected = ["energy", "water", "water_flow", "water_level", "pressure", "flow", "vibration", "machine_temperature"]
    for s in expected:
        assert s in enabled, f"Expected {s} to be auto-selected for Water Pump Station"

    # Verify default baselines are set in sensor_configs_dict
    sensor_cfgs = config.sensor_configs_dict
    assert sensor_cfgs["water_flow"]["baseline"] == 120.0
    assert sensor_cfgs["pressure"]["baseline"] == 6.0
    assert sensor_cfgs["vibration"]["baseline"] == 2.5
    assert sensor_cfgs["machine_temperature"]["baseline"] == 65.0


def test_super_admin_toggle_sensors_and_reset_recommended(client: TestClient, db_session):
    sa_token = get_token(client, "superadmin@greennexa.com", "SuperAdmin123!")

    # 1. Create Hospital
    payload = {
        "name": "Apollo Care Center",
        "ownership_type": "PRIVATE",
        "facility_type": "Hospital",
        "facility_name": "Care Block",
        "state": "Odisha",
        "district": "Khurda",
        "city": "Bhubaneswar",
        "address": "Health Avenue 10",
        "admin_name": "Apollo Admin",
        "admin_user_id": "APOLLO_CARE_ADMIN",
        "admin_email": "apollo_care@greennexa.local",
        "admin_password": "HospitalPassword123!",
        "enabled_modules": ["energy", "water", "waste", "air_quality"],
    }
    res = client.post(
        "/api/v1/super-admin/organisations/create-full",
        json=payload,
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res.status_code == 201
    org_id = res.json()["organisation_id"]

    # 2. Super Admin toggles OFF a recommended sensor (e.g. occupancy) and toggles ON an additional sensor (e.g. vibration)
    # Fetch current sensor config
    get_res = client.get(
        f"/api/v1/super-admin/sensors/{org_id}",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert get_res.status_code == 200
    current_cfg = get_res.json()

    # Modify enabled_sensors
    updated_sensors = [s for s in current_cfg["enabled_modules"] if s != "occupancy"]
    updated_sensors.append("vibration")

    update_payload = {
        "enabled_sensors": updated_sensors,
        "sensor_configs": {
            "vibration": {
                "baseline": 3.2,
                "warning_threshold": 12.0,
                "critical_threshold": 25.0,
                "unit": "mm/s",
            }
        },
    }
    put_res = client.put(
        f"/api/v1/super-admin/sensors/{org_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert put_res.status_code == 200
    saved_cfg = put_res.json()
    assert "occupancy" not in saved_cfg["enabled_modules"]
    assert "vibration" in saved_cfg["enabled_modules"]
    assert saved_cfg["sensor_configs"]["vibration"]["baseline"] == 3.2

    # 3. Super Admin clicks [ Reset to Recommended ]
    reset_res = client.post(
        f"/api/v1/super-admin/sensors/{org_id}/reset-recommended",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert "occupancy" in reset_data["enabled_modules"], "Reset should restore occupancy for Hospital"
    assert "vibration" not in reset_data["enabled_modules"], "Reset should remove vibration for Hospital"


def test_zero_silent_overwrite(client: TestClient, db_session):
    sa_token = get_token(client, "superadmin@greennexa.com", "SuperAdmin123!")

    # 1. Existing org with custom sensor setup
    payload = {
        "name": "Custom Engineering Labs",
        "ownership_type": "PRIVATE",
        "facility_type": "Industrial Organisation",
        "facility_name": "Main Plant",
        "state": "Odisha",
        "district": "Khurda",
        "city": "Bhubaneswar",
        "address": "Industrial Corridor 5",
        "admin_name": "Custom Admin",
        "admin_user_id": "CUSTOM_LABS_ADMIN",
        "admin_email": "custom_labs@greennexa.local",
        "admin_password": "LabPassword123!",
        "enabled_modules": ["energy", "water", "assets"],
        "sensor_configs": {
            "energy": {"baseline": 850, "warning_threshold": 12, "critical_threshold": 24, "unit": "kWh"},
            "pressure": {"baseline": 4.5, "warning_threshold": 10, "critical_threshold": 20, "unit": "bar"},
        },
    }
    res = client.post(
        "/api/v1/super-admin/organisations/create-full",
        json=payload,
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res.status_code == 201
    custom_org_id = res.json()["organisation_id"]

    # Verify custom org has exactly its configured sensors
    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=custom_org_id).first()
    assert cfg.enabled_sensors == "energy|pressure"
    assert cfg.sensor_configs_dict["energy"]["baseline"] == 850
    assert cfg.sensor_configs_dict["pressure"]["baseline"] == 4.5

    # 2. Creating another new organisation should NOT alter custom_org's config
    another_payload = {
        "name": "Another School Facility",
        "ownership_type": "GOVERNMENT",
        "facility_type": "School",
        "facility_name": "School Wing",
        "state": "Odisha",
        "district": "Khurda",
        "city": "Bhubaneswar",
        "address": "School Road 1",
        "admin_name": "School Admin 2",
        "admin_user_id": "SCHOOL_ADMIN_02",
        "admin_email": "school_admin02@greennexa.local",
        "admin_password": "SchoolPassword123!",
        "enabled_modules": ["energy", "water"],
    }
    client.post(
        "/api/v1/super-admin/organisations/create-full",
        json=another_payload,
        headers={"Authorization": f"Bearer {sa_token}"},
    )

    # Re-check custom org: preserved completely
    db_session.expire_all()
    preserved_cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=custom_org_id).first()
    assert preserved_cfg.enabled_sensors == "energy|pressure"
    assert preserved_cfg.sensor_configs_dict["energy"]["baseline"] == 850
    assert preserved_cfg.sensor_configs_dict["pressure"]["baseline"] == 4.5


def test_synthetic_simulator_respects_active_sensors(db_session):
    # Setup test organisation with only 2 enabled sensors: energy and water
    org = Organisation(
        id="ORG-SIM-TEST-01",
        name="Simulator Test Facility",
        org_type="Hospital",
        is_active=True,
    )
    db_session.add(org)
    db_session.commit()

    config = OrganisationSensorConfig(
        organisation_id=org.id,
        enabled_sensors="energy|water",
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        is_active=True,
    )
    config.set_sensor_configs({
        "energy": {"baseline": 500.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "kWh"},
        "water": {"baseline": 200.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "L"},
        "vibration": {"baseline": 2.5, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "mm/s"},
        "pressure": {"baseline": 5.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "bar"},
    })
    db_session.add(config)
    db_session.commit()

    sim = SyntheticDataSimulator()
    all_readings = sim.run_cycle(db_session)
    telemetry_records = [r for r in all_readings if r.organisation_id == org.id]

    # Check generated records
    generated_sensor_types = {r.sensor_type for r in telemetry_records}

    # Enabled sensors must be present
    assert "energy" in generated_sensor_types
    assert "water" in generated_sensor_types

    # Disabled sensors must NOT be generated
    assert "vibration" not in generated_sensor_types
    assert "pressure" not in generated_sensor_types
    assert "waste" not in generated_sensor_types
    assert "air_quality" not in generated_sensor_types

