"""
GreenNexa — Organisation Ownership Type & Admin Login Verification Suite.

Tests 20 requirements:
 1. Government organisation creation.
 2. Private organisation creation.
 3. Organisation ownership value is persisted.
 4. Organisation edit changes ownership type.
 5. Existing organisation data remains intact.
 6. Government ADMIN + Government selection -> login success.
 7. Private ADMIN + Private selection -> login success.
 8. Government ADMIN + Private selection -> login rejected (401).
 9. Private ADMIN + Government selection -> login rejected (401).
10. Wrong password still rejected (401).
11. Missing organisation type rejected for ADMIN login (400).
12. Invalid ownership type rejected (400).
13. Inactive organisation still blocked (403).
14. Suspended admin still blocked (403).
15. SUPER_ADMIN login remains unchanged (bypasses ownership check).
16. ADMIN cannot access another organisation (tenant isolation).
17. Organisation dashboard routing still uses authenticated organisation.
18. Startup does not overwrite existing ownership type.
19. New organisation creation works after backend restart.
20. Existing organisations persist after backend restart.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models import (
    Organisation,
    OrganisationSensorConfig,
    User,
)
from app.db.seed_demo import seed_demo_data


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
def sa_headers(superadmin_token: str) -> dict:
    return {"Authorization": f"Bearer {superadmin_token}"}


def make_org_payload(
    name: str = "Test Org",
    ownership_type: str = "GOVERNMENT",
    admin_name: str = "Admin",
    admin_email: str = "admin@test.org",
    admin_password: str = "Password123!",
    **kwargs,
) -> dict:
    base = {
        "name": name,
        "ownership_type": ownership_type,
        "facility_type": "College",
        "facility_name": f"{name} Facility",
        "state": "Maharashtra",
        "district": "Pune",
        "city": "Pune",
        "address": "123 Green Way",
        "admin_name": admin_name,
        "admin_email": admin_email,
        "admin_password": admin_password,
        "enabled_modules": ["energy"],
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# 1. Government organisation creation
# ---------------------------------------------------------------------------
def test_01_government_organisation_creation(client: TestClient, sa_headers: dict):
    payload = make_org_payload(
        name="Gov Polytechnic Institute",
        ownership_type="GOVERNMENT",
        admin_email="admin@govpoly.edu",
    )
    res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["ownership_type"] == "GOVERNMENT"
    assert data["organisation_name"] == "Gov Polytechnic Institute"


# ---------------------------------------------------------------------------
# 2. Private organisation creation
# ---------------------------------------------------------------------------
def test_02_private_organisation_creation(client: TestClient, sa_headers: dict):
    payload = make_org_payload(
        name="Private Cyber Health",
        ownership_type="PRIVATE",
        facility_type="Hospital",
        admin_email="admin@pvthealth.org",
    )
    res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["ownership_type"] == "PRIVATE"
    assert data["organisation_name"] == "Private Cyber Health"


# ---------------------------------------------------------------------------
# 3. Organisation ownership value is persisted
# ---------------------------------------------------------------------------
def test_03_organisation_ownership_value_is_persisted(client: TestClient, sa_headers: dict, db_session: Session):
    payload = make_org_payload(
        name="Persisted Gov Campus",
        ownership_type="GOVERNMENT",
        admin_email="admin@persistgov.edu",
    )
    res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res.status_code == 201
    org_id = res.json()["organisation_id"]

    # 1. Verify directly in database
    db_org = db_session.query(Organisation).filter_by(id=org_id).first()
    assert db_org is not None
    assert db_org.ownership_type == "GOVERNMENT"

    # 2. Verify via Super Admin full-config API
    cfg_res = client.get(f"/api/v1/super-admin/organisations/{org_id}/full-config", headers=sa_headers)
    assert cfg_res.status_code == 200
    assert cfg_res.json()["ownership_type"] == "GOVERNMENT"

    # 3. Verify via Organisation API
    org_res = client.get(f"/api/v1/organisations/{org_id}", headers=sa_headers)
    assert org_res.status_code == 200
    assert org_res.json()["ownership_type"] == "GOVERNMENT"


# ---------------------------------------------------------------------------
# 4. Organisation edit changes ownership type
# ---------------------------------------------------------------------------
def test_04_organisation_edit_changes_ownership_type(client: TestClient, sa_headers: dict, db_session: Session):
    payload = make_org_payload(
        name="Editable Org",
        ownership_type="GOVERNMENT",
        admin_email="admin@editablerec.edu",
    )
    create_res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert create_res.status_code == 201
    org_id = create_res.json()["organisation_id"]

    # Edit ownership_type to PRIVATE via edit-full
    edit_res = client.put(
        f"/api/v1/super-admin/organisations/{org_id}/edit-full",
        json={"ownership_type": "PRIVATE"},
        headers=sa_headers,
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["ownership_type"] == "PRIVATE"

    # Check database persistence
    db_session.expire_all()
    org_db = db_session.query(Organisation).filter_by(id=org_id).first()
    assert org_db.ownership_type == "PRIVATE"


# ---------------------------------------------------------------------------
# 5. Existing organisation data remains intact after ownership edit
# ---------------------------------------------------------------------------
def test_05_existing_organisation_data_remains_intact(client: TestClient, sa_headers: dict, db_session: Session):
    payload = make_org_payload(
        name="Intact Check Org",
        ownership_type="GOVERNMENT",
        facility_type="University",
        facility_name="North Campus",
        state="Delhi",
        district="New Delhi",
        city="Delhi",
        address="123 Academic Way",
        admin_email="admin@intact.edu",
        enabled_modules=["energy", "water", "waste"],
        blocks=[
            {"block_id": "BLK-A", "block_name": "Science Block", "floor_count": 4},
            {"block_id": "BLK-B", "block_name": "Arts Block", "floor_count": 3},
        ],
    )
    create_res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert create_res.status_code == 201
    org_id = create_res.json()["organisation_id"]

    # Edit only the ownership type
    edit_res = client.put(
        f"/api/v1/super-admin/organisations/{org_id}/edit-full",
        json={"ownership_type": "PRIVATE"},
        headers=sa_headers,
    )
    assert edit_res.status_code == 200
    edited = edit_res.json()

    # Verify other fields remain intact
    assert edited["organisation_name"] == "Intact Check Org"
    assert edited["facility_name"] == "North Campus"
    assert edited["facility_type"] == "University"
    assert edited["state"] == "Delhi"
    assert edited["city"] == "Delhi"
    assert edited["admin_email"] == "admin@intact.edu"
    assert "energy" in edited["enabled_modules"]
    assert "water" in edited["enabled_modules"]
    assert "waste" in edited["enabled_modules"]
    block_ids = [b["block_id"] for b in edited["blocks"]]
    assert "BLK-A" in block_ids
    assert "BLK-B" in block_ids


# ---------------------------------------------------------------------------
# 6. Government ADMIN + Government selection -> login success
# ---------------------------------------------------------------------------
def test_06_government_admin_government_selection_login_success(client: TestClient, sa_headers: dict):
    payload = make_org_payload(
        name="Gov Success University",
        ownership_type="GOVERNMENT",
        admin_email="gov_success@university.edu",
        admin_password="GovPassword123!",
    )
    client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)

    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "gov_success@university.edu",
            "password": "GovPassword123!",
            "organisation_type": "GOVERNMENT",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# ---------------------------------------------------------------------------
# 7. Private ADMIN + Private selection -> login success
# ---------------------------------------------------------------------------
def test_07_private_admin_private_selection_login_success(client: TestClient, sa_headers: dict):
    payload = make_org_payload(
        name="Pvt Success Hospital",
        ownership_type="PRIVATE",
        facility_type="Hospital",
        admin_email="pvt_success@medcenter.org",
        admin_password="PvtPassword123!",
    )
    client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)

    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "pvt_success@medcenter.org",
            "password": "PvtPassword123!",
            "organisation_type": "PRIVATE",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# ---------------------------------------------------------------------------
# 8. Government ADMIN + Private selection -> login rejected (401)
# ---------------------------------------------------------------------------
def test_08_government_admin_private_selection_login_rejected(client: TestClient, sa_headers: dict):
    payload = make_org_payload(
        name="Gov College Beta",
        ownership_type="GOVERNMENT",
        admin_email="gov_beta@college.edu",
        admin_password="BetaPassword123!",
    )
    client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)

    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "gov_beta@college.edu",
            "password": "BetaPassword123!",
            "organisation_type": "PRIVATE",  # Mismatch!
        },
    )
    assert res.status_code == 401
    assert "Selected organisation type does not match these credentials." in res.json()["detail"]


# ---------------------------------------------------------------------------
# 9. Private ADMIN + Government selection -> login rejected (401)
# ---------------------------------------------------------------------------
def test_09_private_admin_government_selection_login_rejected(client: TestClient, sa_headers: dict):
    payload = make_org_payload(
        name="Private Enterprise Tech",
        ownership_type="PRIVATE",
        admin_email="admin@privatetech.com",
        admin_password="PvtPassword123!",
    )
    client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)

    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@privatetech.com",
            "password": "PvtPassword123!",
            "organisation_type": "GOVERNMENT",  # Mismatch!
        },
    )
    assert res.status_code == 401
    assert "Selected organisation type does not match these credentials." in res.json()["detail"]


# ---------------------------------------------------------------------------
# 10. Wrong password still rejected (401)
# ---------------------------------------------------------------------------
def test_10_wrong_password_still_rejected(client: TestClient, sa_headers: dict):
    payload = make_org_payload(
        name="Wrong Pass Org",
        ownership_type="GOVERNMENT",
        admin_email="admin@wrongpass.edu",
        admin_password="CorrectPassword123!",
    )
    client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)

    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@wrongpass.edu",
            "password": "IncorrectPassword999!",
            "organisation_type": "GOVERNMENT",
        },
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]


# ---------------------------------------------------------------------------
# 11. Missing organisation type rejected for ADMIN login (400)
# ---------------------------------------------------------------------------
def test_11_missing_organisation_type_rejected_for_admin_login(client: TestClient, sa_headers: dict):
    payload = make_org_payload(
        name="Missing Type Org",
        ownership_type="PRIVATE",
        admin_email="admin@missingtype.edu",
        admin_password="Password123!",
    )
    client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)

    # 1. organisation_type omitted
    res1 = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@missingtype.edu",
            "password": "Password123!",
        },
    )
    assert res1.status_code == 400
    assert "Organisation type is required" in res1.json()["detail"]

    # 2. organisation_type empty string
    res2 = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@missingtype.edu",
            "password": "Password123!",
            "organisation_type": "",
        },
    )
    assert res2.status_code == 400
    assert "Organisation type is required" in res2.json()["detail"]


# ---------------------------------------------------------------------------
# 12. Invalid ownership type rejected (400)
# ---------------------------------------------------------------------------
def test_12_invalid_ownership_type_rejected(client: TestClient, sa_headers: dict):
    payload_valid = make_org_payload(
        name="Valid Org For Invalid Login",
        ownership_type="GOVERNMENT",
        admin_email="admin@validforinv.edu",
        admin_password="Password123!",
    )
    client.post("/api/v1/super-admin/organisations/create-full", json=payload_valid, headers=sa_headers)

    # 1. Invalid organisation_type in login with valid admin credentials
    res_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@validforinv.edu",
            "password": "Password123!",
            "organisation_type": "SEMI_GOVERNMENT",
        },
    )
    assert res_login.status_code == 400
    assert "Invalid organisation type" in res_login.json()["detail"]

    # 2. Invalid ownership_type in create-full
    payload = make_org_payload(
        name="Bad Type Org",
        ownership_type="INVALID_TYPE",
        admin_email="bad@type.edu",
    )
    res_create = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res_create.status_code == 400
    assert "Invalid organisation ownership type" in res_create.json()["detail"]


# ---------------------------------------------------------------------------
# 13. Inactive organisation still blocked (403)
# ---------------------------------------------------------------------------
def test_13_inactive_organisation_still_blocked(client: TestClient, sa_headers: dict, db_session: Session):
    payload = make_org_payload(
        name="Inactive Org",
        ownership_type="GOVERNMENT",
        admin_email="admin@inactiveorg.edu",
    )
    create_res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert create_res.status_code == 201
    org_id = create_res.json()["organisation_id"]

    # Deactivate the organisation in database
    org = db_session.query(Organisation).filter_by(id=org_id).first()
    org.is_active = False
    db_session.commit()

    # Attempt login with matching organisation type
    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@inactiveorg.edu",
            "password": "Password123!",
            "organisation_type": "GOVERNMENT",
        },
    )
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 14. Suspended admin still blocked (403)
# ---------------------------------------------------------------------------
def test_14_suspended_admin_still_blocked(client: TestClient, sa_headers: dict, db_session: Session):
    payload = make_org_payload(
        name="Active Org Suspended Admin",
        ownership_type="PRIVATE",
        facility_type="Hospital",
        admin_email="admin@suspendedadmin.org",
    )
    create_res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert create_res.status_code == 201

    # Suspend user while organisation is active
    admin_user = db_session.query(User).filter_by(email="admin@suspendedadmin.org").first()
    admin_user.is_active = False
    db_session.commit()

    res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@suspendedadmin.org",
            "password": "Password123!",
            "organisation_type": "PRIVATE",
        },
    )
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 15. SUPER_ADMIN login remains unchanged
# ---------------------------------------------------------------------------
def test_15_super_admin_login_remains_unchanged(client: TestClient, db_session: Session):
    sa = db_session.query(User).filter_by(email="superadmin@greennexa.com").first()
    if not sa:
        sa = User(
            id="superadmin_demo",
            email="superadmin@greennexa.com",
            hashed_password=hash_password("SuperAdmin123!"),
            full_name="Global Super Admin",
            role=User.ROLE_SUPER_ADMIN,
            is_active=True,
        )
        db_session.add(sa)
        db_session.commit()

    # 1. Super Admin logs in without organisation_type
    res1 = client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@greennexa.com", "password": "SuperAdmin123!"},
    )
    assert res1.status_code == 200
    assert "access_token" in res1.json()

    # 2. Super Admin logs in with organisation_type supplied (must not be blocked)
    res2 = client.post(
        "/api/v1/auth/login",
        json={
            "email": "superadmin@greennexa.com",
            "password": "SuperAdmin123!",
            "organisation_type": "GOVERNMENT",
        },
    )
    assert res2.status_code == 200
    assert "access_token" in res2.json()


# ---------------------------------------------------------------------------
# 16. ADMIN cannot access another organisation (tenant isolation)
# ---------------------------------------------------------------------------
def test_16_admin_cannot_access_another_organisation(client: TestClient, sa_headers: dict):
    # Org A (Government)
    payload_a = make_org_payload(
        name="Tenant A Org",
        ownership_type="GOVERNMENT",
        admin_name="Admin A",
        admin_email="admin_a@tenant.edu",
        admin_password="PasswordA123!",
    )
    res_a = client.post("/api/v1/super-admin/organisations/create-full", json=payload_a, headers=sa_headers)
    assert res_a.status_code == 201

    # Org B (Private)
    payload_b = make_org_payload(
        name="Tenant B Org",
        ownership_type="PRIVATE",
        admin_name="Admin B",
        admin_email="admin_b@tenant.edu",
        admin_password="PasswordB123!",
    )
    res_b = client.post("/api/v1/super-admin/organisations/create-full", json=payload_b, headers=sa_headers)
    assert res_b.status_code == 201
    org_b_id = res_b.json()["organisation_id"]

    # Login as Admin A
    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_a@tenant.edu", "password": "PasswordA123!", "organisation_type": "GOVERNMENT"},
    )
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Admin A attempts to access Org B's details
    res_forbidden = client.get(f"/api/v1/organisations/{org_b_id}", headers=headers_a)
    assert res_forbidden.status_code == 403


# ---------------------------------------------------------------------------
# 17. Organisation dashboard routing still uses authenticated organisation
# ---------------------------------------------------------------------------
def test_17_organisation_dashboard_routing_uses_authenticated_organisation(client: TestClient, sa_headers: dict):
    payload = make_org_payload(
        name="Routing Org",
        ownership_type="GOVERNMENT",
        admin_name="Routing Admin",
        admin_email="admin@routing.edu",
        admin_password="Password123!",
    )
    res_org = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res_org.status_code == 201
    org_id = res_org.json()["organisation_id"]

    # Login as Admin
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@routing.edu", "password": "Password123!", "organisation_type": "GOVERNMENT"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Sensor config route scoped to authenticated user's organisation
    cfg_res = client.get("/api/v1/organisation/sensor-config", headers=headers)
    assert cfg_res.status_code == 200
    assert cfg_res.json()["organisation_id"] == org_id

    # Auth me route
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["organisation_id"] == org_id


# ---------------------------------------------------------------------------
# 18. Startup does not overwrite existing ownership type
# ---------------------------------------------------------------------------
def test_18_startup_does_not_overwrite_existing_ownership_type(db_session: Session):
    # Seed platform
    seed_demo_data(db_session)

    # Modify ORG-COL-001 from GOVERNMENT to PRIVATE
    org_col = db_session.query(Organisation).filter_by(id="ORG-COL-001").first()
    assert org_col is not None
    org_col.ownership_type = "PRIVATE"
    db_session.commit()

    # Re-run startup seeding (simulating backend restart)
    seed_demo_data(db_session)

    # Verify ownership_type was NOT reverted back to GOVERNMENT
    db_session.expire_all()
    reloaded_col = db_session.query(Organisation).filter_by(id="ORG-COL-001").first()
    assert reloaded_col.ownership_type == "PRIVATE"


# ---------------------------------------------------------------------------
# 19. New organisation creation works after backend restart
# ---------------------------------------------------------------------------
def test_19_new_organisation_creation_works_after_backend_restart(client: TestClient, sa_headers: dict, db_session: Session):
    # Simulate restart by running startup seeder
    seed_demo_data(db_session)

    # Super Admin creates a new organisation post-restart
    payload = make_org_payload(
        name="Post Restart Org",
        ownership_type="GOVERNMENT",
        admin_name="PR Admin",
        admin_email="admin@postrestart.edu",
        admin_password="Password123!",
    )
    res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["ownership_type"] == "GOVERNMENT"

    # Confirm admin can log in
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@postrestart.edu",
            "password": "Password123!",
            "organisation_type": "GOVERNMENT",
        },
    )
    assert login_res.status_code == 200


# ---------------------------------------------------------------------------
# 20. Existing organisations persist after backend restart
# ---------------------------------------------------------------------------
def test_20_existing_organisations_persist_after_backend_restart(client: TestClient, sa_headers: dict, db_session: Session):
    # Create custom organisation
    payload = make_org_payload(
        name="Persistent Test Campus",
        ownership_type="PRIVATE",
        admin_name="Persist Admin 2",
        admin_email="admin@persist2.org",
        admin_password="Password123!",
    )
    res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res.status_code == 201
    org_id = res.json()["organisation_id"]

    # Simulate backend restart with seed_demo_data
    seed_demo_data(db_session)

    # Verify organisation and its ownership type still exist
    org = db_session.query(Organisation).filter_by(id=org_id).first()
    assert org is not None
    assert org.ownership_type == "PRIVATE"

    # Verify admin can still log in
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@persist2.org",
            "password": "Password123!",
            "organisation_type": "PRIVATE",
        },
    )
    assert login_res.status_code == 200
