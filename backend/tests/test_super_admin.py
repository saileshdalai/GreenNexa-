"""
GreenNexa — Unit tests for Super Admin Platform Management APIs.
"""

import os
import pytest
from fastapi.testclient import TestClient
from app.db.models import User, Organisation, OrganisationSensorConfig


def get_token(client: TestClient, email: str, password: str, organisation_type: str = None) -> str:
    body = {"email": email, "password": password}
    if organisation_type:
        body["organisation_type"] = organisation_type
    res = client.post("/api/v1/auth/login", json=body)
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_super_admin_facility_types_role_enforcement(client: TestClient, db_session, auth_headers):
    # 1. Anonymous -> 401
    res = client.get("/api/v1/super-admin/facility-types")
    assert res.status_code in (401, 403)

    # 2. Admin -> 403
    admin_headers = auth_headers("test_admin@college.edu", "ADMIN", "ORG-COL-001")
    res = client.get(
        "/api/v1/super-admin/facility-types",
        headers=admin_headers,
    )
    assert res.status_code == 403

    # 3. Super Admin -> 200 with 7 facility types
    sa_token = get_token(client, "superadmin@greennexa.com", "SuperAdmin123!")
    res = client.get(
        "/api/v1/super-admin/facility-types",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res.status_code == 200
    types = res.json()
    assert len(types) == 7
    names = [t["name"] for t in types]
    assert "School" in names
    assert "Hospital" in names


def test_super_admin_overview_kpis(client: TestClient):
    sa_token = get_token(client, "superadmin@greennexa.com", "SuperAdmin123!")
    res = client.get(
        "/api/v1/super-admin/overview",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "total_organisations" in data
    assert "active_organisations" in data
    assert "total_admins" in data
    assert "active_iot_devices" in data
    assert "organisations" in data
    assert isinstance(data["organisations"], list)


def test_super_admin_create_full_organisation_and_admin(client: TestClient):
    sa_token = get_token(client, "superadmin@greennexa.com", "SuperAdmin123!")

    payload = {
        "name": "St. Jude High School",
        "ownership_type": "PRIVATE",
        "facility_type": "School",
        "facility_name": "Main Campus",
        "state": "Odisha",
        "district": "Khurda",
        "city": "Bhubaneswar",
        "address": "123 Education Lane",
        "org_code": "STJ-001",
        "admin_name": "Jude Admin",
        "admin_user_id": "ST_JUDE_ADMIN",
        "admin_email": "admin@stjude.edu",
        "admin_phone": "+91-9876543210",
        "admin_password": "SchoolPassword123!",
        "enabled_modules": ["energy", "water", "waste", "air_quality"],
    }

    res = client.post(
        "/api/v1/super-admin/organisations/create-full",
        json=payload,
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["organisation_name"] == "St. Jude High School"
    assert data["admin_user_id"] == "ST_JUDE_ADMIN"

    # Now verify new Admin can log in with Private ownership type!
    new_admin_token = get_token(client, "admin@stjude.edu", "SchoolPassword123!", "PRIVATE")
    assert new_admin_token is not None

    # Verify parking module is disabled in sensor config
    cfg_res = client.get(
        f"/api/v1/organisations/{data['organisation_id']}/sensor-config",
        headers={"Authorization": f"Bearer {new_admin_token}"},
    )
    assert cfg_res.status_code == 200
    cfg = cfg_res.json()
    assert "parking" not in cfg["enabled_sensors"]
    assert "energy" in cfg["enabled_sensors"]


def test_super_admin_reset_user_password(client: TestClient):
    sa_token = get_token(client, "superadmin@greennexa.com", "SuperAdmin123!")

    # 1. Create a user to reset password for
    create_payload = {
        "full_name": "Reset Test User",
        "user_id": "USER_RESET_01",
        "email": "reset_test@greennexa.com",
        "password": "InitialPassword123!",
        "organisation_id": "ORG-COL-001",
        "role": "ADMIN",
    }
    create_res = client.post(
        "/api/v1/super-admin/users",
        json=create_payload,
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert create_res.status_code == 201

    # 2. Reset password
    res = client.post(
        "/api/v1/super-admin/users/USER_RESET_01/reset-password",
        json={"confirmation_password": os.getenv("GREENNEXA_DESTRUCTIVE_ACTION_PASSWORD", "test_destructive_action_password"), "new_password": "NewSecretPassword123!"},
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert res.status_code == 200

    # 3. Old password fails
    fail_res = client.post(
        "/api/v1/auth/login",
        json={"email": "reset_test@greennexa.com", "password": "InitialPassword123!", "organisation_type": "GOVERNMENT"},
    )
    assert fail_res.status_code == 401

    # 4. New password succeeds
    succ_token = get_token(client, "reset_test@greennexa.com", "NewSecretPassword123!", "GOVERNMENT")
    assert succ_token is not None
