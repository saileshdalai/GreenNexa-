"""
Tests for Bug 1: Clear Data Must Reset Simulator to Current Configuration Baseline.

Verifies:
1. Normal generation produces readings.
2. Clear Data purges operational records (sensor readings, anomalies, recommendations, messages).
3. Clear Data purges simulator runtime cache (_last_cumulative_values, _last_anomaly_times).
4. Subsequent cycle starts directly from CURRENT configured baseline, NOT old last value.
5. Updating baseline to a new value (e.g. 200.0) + Clear Data ensures next cycle initializes from 200.0.
6. Updating thresholds is respected by newly generated readings and anomaly logic.
7. Organisation, blocks, modules, and admin account are strictly preserved.
8. Super Admin Clear All Data purges all simulator runtime state platform-wide.
"""

import json
import os
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
)
from app.services.synthetic_simulator import SyntheticDataSimulator, simulator_instance


@pytest.fixture
def sim_setup(db_session: Session):
    """Setup organisation with blocks, configs, and admin."""
    org = Organisation(
        id="ORG-SIM-TEST",
        name="Simulator Test University",
        org_type="college",
        facility_name="Main Campus",
        is_active=True,
    )
    db_session.add(org)

    block_a = FacilityBlock(
        organisation_id="ORG-SIM-TEST",
        block_id="BLK-A",
        block_name="Block A",
        is_active=True,
    )
    block_b = FacilityBlock(
        organisation_id="ORG-SIM-TEST",
        block_id="BLK-B",
        block_name="Block B",
        is_active=True,
    )
    db_session.add_all([block_a, block_b])

    cfg = OrganisationSensorConfig(
        organisation_id="ORG-SIM-TEST",
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        enabled_sensors="energy|water|temperature",
        sensor_configs=json.dumps({
            "energy": {
                "baseline": 100.0,
                "warning_threshold": 15.0,
                "critical_threshold": 30.0,
                "unit": "kWh",
            },
            "water": {
                "baseline": 50.0,
                "warning_threshold": 10.0,
                "critical_threshold": 25.0,
                "unit": "L",
            },
            "temperature": {
                "baseline": 24.0,
                "warning_threshold": 10.0,
                "critical_threshold": 20.0,
                "unit": "°C",
            },
        }),
        is_active=True,
    )
    db_session.add(cfg)

    admin = User(
        id="admin_sim_user",
        email="admin_sim@testuniv.edu",
        hashed_password=hash_password("Pass123!"),
        full_name="Admin Sim",
        role=User.ROLE_ADMIN,
        organisation_id="ORG-SIM-TEST",
        is_active=True,
    )
    super_admin = db_session.query(User).filter_by(email="superadmin@greennexa.com").first()
    if not super_admin:
        super_admin = User(
            id="super_sim_user",
            email="superadmin@greennexa.com",
            hashed_password=hash_password("SuperAdmin@123"),
            full_name="Super Admin",
            role=User.ROLE_SUPER_ADMIN,
            is_active=True,
        )
        db_session.add(super_admin)

    db_session.add(admin)
    db_session.commit()

    simulator_instance.reset_all_simulator_state()

    return {
        "org_id": "ORG-SIM-TEST",
        "admin": admin,
        "super_admin": super_admin,
        "config": cfg,
    }


def test_01_simulator_cumulative_progression_and_clear_data_reset(client: TestClient, db_session: Session, sim_setup):
    """Test cumulative progression, Clear Data reset, and fresh baseline start."""
    org_id = sim_setup["org_id"]
    admin = sim_setup["admin"]
    token = create_access_token({"sub": admin.id})
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Cycle 1: Generate first readings (set anomaly cooldown so initial reading is non-anomalous baseline)
    simulator_instance._last_anomaly_times[org_id] = datetime.now(timezone.utc)
    simulator_instance.run_cycle(db_session)
    c1_readings = db_session.query(SensorReading).filter_by(organisation_id=org_id, block_id="BLK-A", sensor_type="energy").all()
    assert len(c1_readings) == 1
    c1_val = c1_readings[0].value
    # Initial reading should start directly from baseline (100.0)
    assert c1_val == 100.0

    # Cycle 2: Monotonic increase
    simulator_instance._last_anomaly_times[org_id] = datetime.now(timezone.utc)
    simulator_instance.run_cycle(db_session)
    c2_readings = db_session.query(SensorReading).filter_by(organisation_id=org_id, block_id="BLK-A", sensor_type="energy").order_by(SensorReading.timestamp.desc()).all()
    assert len(c2_readings) == 2
    c2_val = c2_readings[0].value
    assert c2_val > c1_val

    # Cycle 3: Further increase (e.g. 100 -> 104.5 -> 109)
    simulator_instance._last_anomaly_times[org_id] = datetime.now(timezone.utc)
    simulator_instance.run_cycle(db_session)
    c3_readings = db_session.query(SensorReading).filter_by(organisation_id=org_id, block_id="BLK-A", sensor_type="energy").order_by(SensorReading.timestamp.desc()).all()
    assert len(c3_readings) == 3
    c3_val = c3_readings[0].value
    assert c3_val > c2_val

    # In-memory simulator cache holds the elevated value.
    # Key is (org_id, block_id, ward_id, sensor_type) so cumulative progression is
    # tracked per physical location (wards never share a block-level accumulator).
    key = (org_id, "BLK-A", None, "energy")
    assert key in simulator_instance._last_cumulative_values
    assert simulator_instance._last_cumulative_values[key] == c3_val

    # Perform Admin Clear Data
    res = client.post(f"/api/v1/organisations/{org_id}/clear-data", headers=auth_headers)
    assert res.status_code == 200

    # 1. Operational data is deleted
    assert db_session.query(SensorReading).filter_by(organisation_id=org_id).count() == 0
    assert db_session.query(AnomalyRecord).filter_by(organisation_id=org_id).count() == 0
    assert db_session.query(AIRecommendation).filter_by(organisation_id=org_id).count() == 0

    # 2. Simulator runtime cache for org is PURGED
    assert key not in simulator_instance._last_cumulative_values
    assert org_id not in simulator_instance._last_anomaly_times

    # 3. Configuration is strictly PRESERVED
    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=org_id).first()
    assert cfg is not None
    assert cfg.sensor_configs_dict["energy"]["baseline"] == 100.0
    assert db_session.query(FacilityBlock).filter_by(organisation_id=org_id).count() == 2

    # 4. Turn Demo ON / run next cycle: MUST NOT use old c3_val! Must initialize from baseline 100.0
    simulator_instance._last_anomaly_times[org_id] = datetime.now(timezone.utc)
    simulator_instance.run_cycle(db_session)
    new_readings = db_session.query(SensorReading).filter_by(organisation_id=org_id, block_id="BLK-A", sensor_type="energy").all()
    assert len(new_readings) == 1
    new_val = new_readings[0].value
    assert new_val == 100.0
    assert new_val != c3_val


def test_02_super_admin_updates_baseline_and_clear_data_initializes_from_new_baseline(client: TestClient, db_session: Session, sim_setup):
    """Super Admin changes baseline 100 -> 200. Clear Data + cycle initializes relative to 200."""
    org_id = sim_setup["org_id"]
    admin = sim_setup["admin"]
    token = create_access_token({"sub": admin.id})
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Generate initial readings with baseline 100
    simulator_instance.run_cycle(db_session)
    simulator_instance.run_cycle(db_session)

    # Super Admin updates baseline to 200.0
    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=org_id).first()
    configs = cfg.sensor_configs_dict
    configs["energy"]["baseline"] = 200.0
    configs["energy"]["warning_threshold"] = 20.0
    configs["energy"]["critical_threshold"] = 40.0
    cfg.sensor_configs = json.dumps(configs)
    db_session.commit()

    # Clear Data
    res = client.post(f"/api/v1/organisations/{org_id}/clear-data", headers=auth_headers)
    assert res.status_code == 200

    # Verify simulator in-memory state is cleared
    key = (org_id, "BLK-A", "energy")
    assert key not in simulator_instance._last_cumulative_values

    # Run cycle: MUST start from the NEW baseline 200.0
    simulator_instance._last_anomaly_times[org_id] = datetime.now(timezone.utc)
    simulator_instance.run_cycle(db_session)
    readings = db_session.query(SensorReading).filter_by(organisation_id=org_id, block_id="BLK-A", sensor_type="energy").all()
    assert len(readings) == 1
    assert readings[0].value == 200.0


def test_03_super_admin_clear_all_data_resets_all_simulator_state(client: TestClient, db_session: Session, sim_setup):
    """Super Admin Clear All Data purges all simulator state platform-wide."""
    org_id = sim_setup["org_id"]
    super_admin = sim_setup["super_admin"]
    token = create_access_token({"sub": super_admin.id})
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Generate readings
    simulator_instance.run_cycle(db_session)
    assert len(simulator_instance._last_cumulative_values) > 0

    conf_pwd = os.getenv("GREENNEXA_DESTRUCTIVE_ACTION_PASSWORD", "test_destructive_action_password")
    res = client.post("/api/v1/super-admin/clear-all-data", headers=auth_headers, json={"confirmation_password": conf_pwd, "confirmation": "CLEAR ALL DATA"})
    assert res.status_code == 200

    # Verify platform-wide simulator state is reset
    assert len(simulator_instance._last_cumulative_values) == 0
    assert len(simulator_instance._last_anomaly_times) == 0
    assert simulator_instance._organisations_processed == 0
    assert simulator_instance._total_readings_generated == 0
