"""
Unit & Integration Tests for Admin Clear Data & Super Admin Clear All Data.
"""

from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    IoTDevice,
    Message,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
)


@pytest.fixture
def clear_data_setup(db_session: Session):
    """Setup test data across 2 organisations for clear-data testing."""
    # Org 1
    org1 = Organisation(id="ORG-CLR-1", name="Clear Test Org 1", org_type="college", location="Loc 1")
    db_session.add(org1)
    cfg1 = OrganisationSensorConfig(organisation_id="ORG-CLR-1", data_source="synthetic", is_active=True)
    db_session.add(cfg1)
    blk1 = FacilityBlock(organisation_id="ORG-CLR-1", block_id="BLK-CLR-1", block_name="Block C1", is_active=True)
    db_session.add(blk1)
    dev1 = IoTDevice(organisation_id="ORG-CLR-1", device_id="DEV-001", device_name="Test Sensor 1", api_key_hash="hash123", is_active=True)
    db_session.add(dev1)

    admin1 = User(
        id="usr_admin_clr1",
        email="admin@clr1.org",
        hashed_password=hash_password("Pass123!"),
        full_name="Admin Clr 1",
        role=User.ROLE_ADMIN,
        organisation_id="ORG-CLR-1",
        is_active=True,
    )
    db_session.add(admin1)

    r1 = SensorReading(organisation_id="ORG-CLR-1", sensor_type="energy", value=120.0, block_id="BLK-CLR-1")
    db_session.add(r1)
    a1 = AnomalyRecord(
        organisation_id="ORG-CLR-1",
        metric="energy",
        facility_id="Block C1",
        block_id="BLK-CLR-1",
        value=120.0,
        severity="HIGH",
        status="OPEN",
    )
    db_session.add(a1)
    db_session.flush()

    rec1 = AIRecommendation(
        organisation_id="ORG-CLR-1",
        anomaly_id=a1.id,
        metric="energy",
        current_value=120.0,
        severity="HIGH",
        facility_id="Block C1",
        block_id="BLK-CLR-1",
        priority="HIGH",
        summary="Test Recommendation",
        status="ACTIVE",
    )
    db_session.add(rec1)
    # Super Admin User
    superadmin = db_session.query(User).filter_by(email="superadmin@greennexa.com").first()
    if not superadmin:
        superadmin = User(
            id="superadmin_demo",
            email="superadmin@greennexa.com",
            hashed_password=hash_password("SuperAdmin123!"),
            full_name="Global Super Admin",
            role=User.ROLE_SUPER_ADMIN,
            organisation_id=None,
            is_active=True,
        )
        db_session.add(superadmin)
    db_session.flush()

    msg1 = Message(organisation_id="ORG-CLR-1", sender_id=admin1.id, recipient_id=superadmin.id, subject="Test Msg", body="Test message content")
    db_session.add(msg1)

    db_session.commit()

    return {
        "admin1": admin1,
        "superadmin": superadmin,
        "org1_id": "ORG-CLR-1",
    }


def test_admin_clear_data_deletes_operational_data_only(client: TestClient, db_session: Session, clear_data_setup):
    """Admin Clear Data wipes readings, anomalies, recommendations, and messages while preserving org, admin, blocks, configs, devices."""
    admin1 = clear_data_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        f"/api/v1/organisations/{clear_data_setup['org1_id']}/clear-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["deleted"]["sensor_readings"] >= 1
    assert data["deleted"]["anomaly_records"] >= 1
    assert data["deleted"]["recommendations"] >= 1

    # Verify operational tables cleared for ORG-CLR-1
    assert db_session.query(SensorReading).filter_by(organisation_id="ORG-CLR-1").count() == 0
    assert db_session.query(AnomalyRecord).filter_by(organisation_id="ORG-CLR-1").count() == 0
    assert db_session.query(AIRecommendation).filter_by(organisation_id="ORG-CLR-1").count() == 0
    assert db_session.query(Message).filter_by(organisation_id="ORG-CLR-1").count() == 0

    # Verify structural elements PRESERVED
    assert db_session.query(Organisation).filter_by(id="ORG-CLR-1").first() is not None
    assert db_session.query(User).filter_by(id=admin1.id).first() is not None
    assert db_session.query(FacilityBlock).filter_by(organisation_id="ORG-CLR-1").count() >= 1
    assert db_session.query(OrganisationSensorConfig).filter_by(organisation_id="ORG-CLR-1").first() is not None
    assert db_session.query(IoTDevice).filter_by(organisation_id="ORG-CLR-1").count() >= 1


def test_admin_cannot_clear_other_org_data(client: TestClient, clear_data_setup):
    """Admin of Org 1 is forbidden from calling clear-data on Org 2."""
    admin1 = clear_data_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/organisations/ORG-COL-001/clear-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_super_admin_clear_all_requires_confirmation_phrase(client: TestClient, clear_data_setup):
    """Super Admin Clear All Data requires confirmation phrase 'CLEAR ALL DATA'."""
    superadmin = clear_data_setup["superadmin"]
    token = create_access_token({"sub": superadmin.id})

    conf_pwd = os.getenv("GREENNEXA_DESTRUCTIVE_ACTION_PASSWORD", "test_destructive_action_password")
    res = client.post(
        "/api/v1/super-admin/clear-all-data",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_password": conf_pwd, "confirmation": "INVALID PHRASE"},
    )
    assert res.status_code == 400
    assert "CLEAR ALL DATA" in res.json()["detail"]


def test_super_admin_clear_all_deletes_all_orgs_and_preserves_superadmin(client: TestClient, db_session: Session, clear_data_setup):
    """Super Admin Clear All Data wipes all tenant orgs and accounts, keeping ONLY superadmin@greennexa.com."""
    superadmin = clear_data_setup["superadmin"]
    token = create_access_token({"sub": superadmin.id})
    conf_pwd = os.getenv("GREENNEXA_DESTRUCTIVE_ACTION_PASSWORD", "test_destructive_action_password")

    res = client.post(
        "/api/v1/super-admin/clear-all-data",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_password": conf_pwd, "confirmation": "CLEAR ALL DATA"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["preserved_user"] == "superadmin@greennexa.com"

    # All organisations wiped
    assert db_session.query(Organisation).count() == 0

    # Only super admin user preserved
    remaining_users = db_session.query(User).all()
    assert len(remaining_users) == 1
    assert remaining_users[0].email == "superadmin@greennexa.com"
