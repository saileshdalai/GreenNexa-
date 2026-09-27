"""
GreenNexa — Regression Tests for Clear All Data Repopulation Bug.

Verifies:
1. Fresh database startup seeding behaviour (default demo organisations seeded).
2. Clear All Data deletes all organisations and organisation-level data.
3. Clear All Data leaves only the fixed SUPER_ADMIN account.
4. Restart after Clear All Data does NOT recreate organisations (no resurrection of ORG-COL-001 or ORG-HOSP-002).
5. Manual organisation creation after reset persists normally across backend restart.
6. Existing Clear All Data confirmation phrase validation remains unchanged.
7. Existing organisation creation endpoints remain fully functional.
8. Existing auth and RBAC permissions remain strictly enforced.
"""

from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

CONFIRMATION_PWD = os.getenv("GREENNEXA_DESTRUCTIVE_ACTION_PASSWORD", "test_destructive_action_password")

from app.core.security import create_access_token, hash_password
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    EventReadState,
    FacilityBlock,
    IoTDevice,
    Message,
    Organisation,
    OrganisationSensorConfig,
    PlatformState,
    SensorReading,
    User,
)
from app.db.seed_demo import is_platform_data_cleared, seed_demo_data, set_platform_data_cleared


@pytest.fixture
def superadmin_token(db_session: Session) -> str:
    """Ensure fixed Super Admin demo account exists and return Bearer token."""
    sa = db_session.query(User).filter_by(email="superadmin@greennexa.com").first()
    if not sa:
        sa = User(
            id="superadmin_demo",
            email="superadmin@greennexa.com",
            hashed_password=hash_password("SuperAdmin123!"),
            full_name="Global Super Admin",
            role=User.ROLE_SUPER_ADMIN,
            organisation_id=None,
            is_active=True,
        )
        db_session.add(sa)
        db_session.commit()
    return create_access_token({"sub": sa.id, "email": sa.email, "role": sa.role})


@pytest.fixture
def populated_platform(db_session: Session) -> dict:
    """Setup platform with demo organisations, users, and operational data."""
    # Seed base demo organisations & superadmin
    seed_demo_data(db_session)

    # Add extra organisation with full operational data
    org = Organisation(
        id="ORG-TEST-REG",
        name="Regression Test University",
        org_type="college",
        location="Campus R",
        is_active=True,
    )
    db_session.add(org)

    cfg = OrganisationSensorConfig(
        organisation_id="ORG-TEST-REG",
        data_source="synthetic",
        enabled_sensors="energy|water|temperature",
        is_active=True,
    )
    db_session.add(cfg)

    blk = FacilityBlock(
        organisation_id="ORG-TEST-REG",
        block_id="BLK-R1",
        block_name="Block R1",
        is_active=True,
    )
    db_session.add(blk)

    admin = User(
        id="usr_admin_reg",
        email="admin@reg.org",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Regression Admin",
        role=User.ROLE_ADMIN,
        organisation_id="ORG-TEST-REG",
        is_active=True,
    )
    db_session.add(admin)

    reading = SensorReading(
        organisation_id="ORG-TEST-REG",
        sensor_type="energy",
        value=150.0,
        block_id="BLK-R1",
    )
    db_session.add(reading)
    db_session.flush()

    anomaly = AnomalyRecord(
        organisation_id="ORG-TEST-REG",
        metric="energy",
        value=150.0,
        severity="HIGH",
        status="OPEN",
        block_id="BLK-R1",
    )
    db_session.add(anomaly)
    db_session.flush()

    rec = AIRecommendation(
        organisation_id="ORG-TEST-REG",
        anomaly_id=anomaly.id,
        metric="energy",
        current_value=150.0,
        severity="HIGH",
        priority="HIGH",
        summary="Test anomaly rec",
        status="ACTIVE",
    )
    db_session.add(rec)

    dev = IoTDevice(
        organisation_id="ORG-TEST-REG",
        device_id="DEV-REG-01",
        device_name="Reg Sensor 1",
        api_key_hash="hash_reg_123",
        is_active=True,
    )
    db_session.add(dev)

    sa = db_session.query(User).filter_by(email="superadmin@greennexa.com").first()
    msg = Message(
        organisation_id="ORG-TEST-REG",
        sender_id=admin.id,
        recipient_id=sa.id,
        subject="Alert",
        body="Reg message body",
    )
    db_session.add(msg)

    read_state = EventReadState(
        user_id=admin.id,
        organisation_id="ORG-TEST-REG",
        event_type="anomaly",
        event_id=anomaly.id,
        metric="energy",
    )
    db_session.add(read_state)

    db_session.commit()
    return {"org_id": "ORG-TEST-REG", "admin": admin, "superadmin": sa}


# ---------------------------------------------------------------------------
# Test 1: Fresh database startup seeding behaviour
# ---------------------------------------------------------------------------
def test_fresh_database_startup_seeding_behaviour(db_session: Session):
    """
    On a fresh brand-new database:
    1. is_platform_data_cleared is False.
    2. seed_demo_data creates default organisations ORG-COL-001 and ORG-HOSP-002.
    3. Associated sensor configs and super admin are created.
    """
    assert db_session.query(Organisation).count() == 0
    assert db_session.query(User).count() == 0
    assert not is_platform_data_cleared(db_session)

    res = seed_demo_data(db_session)
    assert res["status"] == "ok"
    assert res.get("organisations_seeded") is True

    # Default organisations created
    org1 = db_session.query(Organisation).filter_by(id="ORG-COL-001").first()
    org2 = db_session.query(Organisation).filter_by(id="ORG-HOSP-002").first()
    assert org1 is not None
    assert org1.name == "Green Valley University"
    assert org2 is not None
    assert org2.name == "City Central Hospital"

    # Sensor configs created
    cfg1 = db_session.query(OrganisationSensorConfig).filter_by(organisation_id="ORG-COL-001").first()
    cfg2 = db_session.query(OrganisationSensorConfig).filter_by(organisation_id="ORG-HOSP-002").first()
    assert cfg1 is not None
    assert cfg2 is not None

    # Super Admin created
    sa = db_session.query(User).filter_by(email="superadmin@greennexa.com").first()
    assert sa is not None
    assert sa.role == User.ROLE_SUPER_ADMIN


# ---------------------------------------------------------------------------
# Test 2: Clear All Data deletes all organisations and operational data
# ---------------------------------------------------------------------------
def test_clear_all_data_deletes_all_organisations_and_operational_data(
    client: TestClient, db_session: Session, populated_platform, superadmin_token
):
    """
    Super Admin Clear All Data wipes all organisations and organisation-level records:
    readings, anomalies, recommendations, devices, blocks, sensor configs, messages, read states.
    """
    res = client.post(
        "/api/v1/super-admin/clear-all-data",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"confirmation": "CLEAR ALL DATA", "confirmation_password": CONFIRMATION_PWD},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["preserved_user"] == "superadmin@greennexa.com"
    assert data["deleted"]["organisations"] >= 3

    # Verify all organisation-level tables are empty
    assert db_session.query(Organisation).count() == 0
    assert db_session.query(OrganisationSensorConfig).count() == 0
    assert db_session.query(FacilityBlock).count() == 0
    assert db_session.query(SensorReading).count() == 0
    assert db_session.query(AnomalyRecord).count() == 0
    assert db_session.query(AIRecommendation).count() == 0
    assert db_session.query(IoTDevice).count() == 0
    assert db_session.query(Message).count() == 0
    assert db_session.query(EventReadState).count() == 0

    # Persistent platform state is recorded
    assert is_platform_data_cleared(db_session) is True


# ---------------------------------------------------------------------------
# Test 3: Clear All Data leaves ONLY SUPER_ADMIN
# ---------------------------------------------------------------------------
def test_clear_all_data_leaves_only_super_admin(
    client: TestClient, db_session: Session, populated_platform, superadmin_token
):
    """
    Super Admin Clear All Data preserves ONLY the fixed Super Admin demo account.
    All tenant admin users are wiped.
    """
    res = client.post(
        "/api/v1/super-admin/clear-all-data",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"confirmation": "CLEAR ALL DATA", "confirmation_password": CONFIRMATION_PWD},
    )
    assert res.status_code == 200

    remaining_users = db_session.query(User).all()
    assert len(remaining_users) == 1
    assert remaining_users[0].email == "superadmin@greennexa.com"
    assert remaining_users[0].role == User.ROLE_SUPER_ADMIN
    assert remaining_users[0].id == "superadmin_demo"

    # Tenant admins are completely gone
    assert db_session.query(User).filter_by(role=User.ROLE_ADMIN).count() == 0


# ---------------------------------------------------------------------------
# Test 4: Restart after Clear All Data does NOT recreate organisations
# ---------------------------------------------------------------------------
def test_restart_after_clear_all_data_does_not_recreate_organisations(
    client: TestClient, db_session: Session, populated_platform, superadmin_token
):
    """
    CRITICAL BUG REGRESSION TEST:
    After Clear All Data, simulating backend startup/lifespan (calling seed_demo_data)
    MUST NOT recreate the deleted default organisations ORG-COL-001 and ORG-HOSP-002.
    """
    # 1. Execute Clear All Data
    res = client.post(
        "/api/v1/super-admin/clear-all-data",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"confirmation": "CLEAR ALL DATA", "confirmation_password": CONFIRMATION_PWD},
    )
    assert res.status_code == 200
    assert db_session.query(Organisation).count() == 0

    # 2. Simulate backend restart: on_startup calls seed_demo_data(db)
    seed_res = seed_demo_data(db_session)
    assert seed_res["status"] == "ok"
    assert seed_res.get("organisations_seeded") is False

    # 3. Verify organisations are STILL 0 and NO default organisations were resurrected
    assert db_session.query(Organisation).count() == 0
    assert db_session.query(Organisation).filter_by(id="ORG-COL-001").first() is None
    assert db_session.query(Organisation).filter_by(id="ORG-HOSP-002").first() is None
    assert db_session.query(OrganisationSensorConfig).count() == 0
    assert db_session.query(FacilityBlock).count() == 0

    # 4. Only Super Admin demo account remains
    remaining_users = db_session.query(User).all()
    assert len(remaining_users) == 1
    assert remaining_users[0].email == "superadmin@greennexa.com"


# ---------------------------------------------------------------------------
# Test 5: Manual organisation creation after reset persists across restart
# ---------------------------------------------------------------------------
def test_manual_organisation_creation_after_reset_persists_across_restart(
    client: TestClient, db_session: Session, populated_platform, superadmin_token
):
    """
    After Clear All Data:
    1. Super Admin manually creates a new organisation.
    2. The new organisation is stored with blocks, admin, and sensor configs.
    3. On backend restart (seed_demo_data), the newly created organisation persists.
    4. The deleted default organisations (ORG-COL-001, ORG-HOSP-002) are NOT resurrected.
    """
    # 1. Clear All Data
    res_clear = client.post(
        "/api/v1/super-admin/clear-all-data",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={"confirmation": "CLEAR ALL DATA", "confirmation_password": CONFIRMATION_PWD},
    )
    assert res_clear.status_code == 200
    assert db_session.query(Organisation).count() == 0

    # 2. Super Admin manually creates a new organisation
    create_payload = {
        "name": "Nova Technological Institute",
        "facility_type": "college_university",
        "facility_name": "Nova Tech Main Campus",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bengaluru",
        "address": "100 Innovation Expressway",
        "admin_name": "Nova SuperAdmin Contact",
        "admin_email": "dean@novatech.edu",
        "admin_password": "NovaPassword123!",
        "admin_phone": "+91 98765 43210",
        "enabled_modules": ["energy", "water", "air_quality"],
        "blocks": [
            {"block_id": "BLK-ENG", "block_name": "Engineering Block"},
            {"block_id": "BLK-SCI", "block_name": "Science Complex"},
        ],
    }
    res_create = client.post(
        "/api/v1/super-admin/organisations/create-full",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json=create_payload,
    )
    assert res_create.status_code == 201
    created_org_id = res_create.json()["organisation_id"]

    # Verify exactly 1 organisation exists
    assert db_session.query(Organisation).count() == 1
    new_org = db_session.query(Organisation).filter_by(id=created_org_id).first()
    assert new_org is not None
    assert new_org.name == "Nova Technological Institute"

    # 3. Simulate backend restart
    seed_res = seed_demo_data(db_session)
    assert seed_res["status"] == "ok"
    assert seed_res.get("organisations_seeded") is False

    # 4. Verify after restart:
    # - New organisation still exists
    # - Old default organisations were NOT resurrected
    # - Total organisations is strictly 1
    assert db_session.query(Organisation).count() == 1
    persisted_org = db_session.query(Organisation).filter_by(id=created_org_id).first()
    assert persisted_org is not None
    assert persisted_org.name == "Nova Technological Institute"

    assert db_session.query(Organisation).filter_by(id="ORG-COL-001").first() is None
    assert db_session.query(Organisation).filter_by(id="ORG-HOSP-002").first() is None

    # Verify blocks and config for the new organisation persisted
    blocks = db_session.query(FacilityBlock).filter_by(organisation_id=created_org_id).all()
    assert len(blocks) == 2
    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=created_org_id).first()
    assert cfg is not None
    assert cfg.enabled_sensors_list == ["energy", "water", "air_quality"]


# ---------------------------------------------------------------------------
# Test 6: Existing Clear All Data confirmation behaviour remains unchanged
# ---------------------------------------------------------------------------
def test_clear_all_data_confirmation_behaviour_remains_unchanged(
    client: TestClient, db_session: Session, populated_platform, superadmin_token
):
    """
    Clear All Data strictly requires 'CLEAR ALL DATA' confirmation phrase.
    Any other phrase or empty string must be rejected with 400 Bad Request.
    """
    for invalid_phrase in ["CLEAR", "clear all data", "DELETE", "", "   "]:
        res = client.post(
            "/api/v1/super-admin/clear-all-data",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"confirmation": invalid_phrase, "confirmation_password": CONFIRMATION_PWD},
        )
        assert res.status_code == 400
        assert "CLEAR ALL DATA" in res.json()["detail"]

    # Verify no data was deleted
    assert db_session.query(Organisation).count() >= 3


# ---------------------------------------------------------------------------
# Test 7: Existing organisation creation remains functional
# ---------------------------------------------------------------------------
def test_existing_organisation_creation_remains_functional(
    client: TestClient, db_session: Session, superadmin_token
):
    """
    Normal organisation creation endpoints (POST /organisations and POST /super-admin/organisations/create-full)
    continue to work without issue.
    """
    # 1. Standard POST /organisations
    res1 = client.post(
        "/api/v1/organisations",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "id": "ORG-STD-001",
            "name": "Standard Test Org",
            "org_type": "office",
            "location": "City Centre",
        },
    )
    assert res1.status_code == 201
    assert res1.json()["id"] == "ORG-STD-001"

    # 2. Multi-step atomic POST /super-admin/organisations/create-full
    res2 = client.post(
        "/api/v1/super-admin/organisations/create-full",
        headers={"Authorization": f"Bearer {superadmin_token}"},
        json={
            "name": "Full Test Hospital",
            "facility_type": "hospital",
            "facility_name": "Full Test Main",
            "state": "Maharashtra",
            "district": "Mumbai City",
            "city": "Mumbai",
            "address": "12 Hospital Road",
            "admin_name": "Dr. Smith",
            "admin_email": "smith@testhosp.org",
            "admin_password": "Password123!",
            "blocks": [{"block_id": "BLK-01", "block_name": "Main Ward"}],
        },
    )
    assert res2.status_code == 201
    assert res2.json()["organisation_name"] == "Full Test Hospital"
    assert len(res2.json()["blocks"]) == 1


# ---------------------------------------------------------------------------
# Test 8: Existing auth and RBAC remains functional
# ---------------------------------------------------------------------------
def test_existing_auth_and_rbac_remains_functional(
    client: TestClient, db_session: Session, populated_platform
):
    """
    Verify RBAC enforcement on /clear-all-data:
    - Unauthenticated: 401 Unauthorized
    - Org Admin: 403 Forbidden
    - Super Admin: 200 OK
    """
    admin = populated_platform["admin"]
    admin_token = create_access_token({"sub": admin.id, "email": admin.email, "role": admin.role})

    # Unauthenticated
    res_unauth = client.post("/api/v1/super-admin/clear-all-data", json={"confirmation": "CLEAR ALL DATA"})
    assert res_unauth.status_code == 401

    # Org Admin (forbidden)
    res_admin = client.post(
        "/api/v1/super-admin/clear-all-data",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"confirmation": "CLEAR ALL DATA", "confirmation_password": CONFIRMATION_PWD},
    )
    assert res_admin.status_code == 403

    # Super Admin login with user ID
    res_login_uid = client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin_demo", "password": "SuperAdmin123!"},
    )
    assert res_login_uid.status_code == 200
    assert res_login_uid.json()["user"]["role"] == "SUPER_ADMIN"

    # Super Admin login with email
    res_login_email = client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@greennexa.com", "password": "SuperAdmin123!"},
    )
    assert res_login_email.status_code == 200
    assert res_login_email.json()["user"]["role"] == "SUPER_ADMIN"
