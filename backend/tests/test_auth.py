"""
GreenNexa — Authentication Unit & Integration Tests.

Tests:
  1. Demo user seeding (`seed_demo_data`).
  2. Super Admin login (`superadmin@greennexa.com`).
  3. Admin login (`admin@college.edu`).
  4. Demo Viewer user login (`demo@greennexa.com`).
  5. Invalid password handling (401 Unauthorized).
  6. Nonexistent email handling (401 Unauthorized).
  7. Token verification and `GET /api/v1/auth/me`.
  8. Demo accounts listing endpoint (`GET /api/v1/auth/demo-accounts`).
"""

import pytest
from app.core.security import hash_password, verify_password
from app.db.models import Organisation, User
from app.db.seed_demo import seed_demo_data


def test_password_hashing():
    """Verify PBKDF2 password hashing and verification."""
    password = "MySecurePassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_seed_demo_users(db_session):
    """Verify seed_demo_data creates Super Admin and removes legacy demo users."""
    res = seed_demo_data(db_session)
    assert res["status"] == "ok"

    users = db_session.query(User).all()
    emails = {u.email for u in users}

    assert "superadmin@greennexa.com" in emails
    assert "admin@college.edu" not in emails
    assert "demo@greennexa.com" not in emails

    # Test idempotency — running again should create 0 new users
    res2 = seed_demo_data(db_session)
    assert res2["created_users"] == 0


def test_login_super_admin(client, db_session):
    """POST /api/v1/auth/login with Super Admin credentials (email and user_id)."""
    seed_demo_data(db_session)

    # 1. Login with email
    payload = {
        "email": "superadmin@greennexa.com",
        "password": "SuperAdmin123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["access_token"] is not None
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "superadmin@greennexa.com"
    assert data["user"]["role"] == "SUPER_ADMIN"

    # 2. Login with user_id
    payload_uid = {
        "email": "superadmin_demo",
        "password": "SuperAdmin123!",
    }
    response_uid = client.post("/api/v1/auth/login", json=payload_uid)
    assert response_uid.status_code == 200
    assert response_uid.json()["user"]["id"] == "superadmin_demo"


def test_login_admin(client, db_session):
    """Verify legacy admin@college.edu is rejected and active admin can log in."""
    seed_demo_data(db_session)

    # 1. Legacy admin must be rejected
    payload_legacy = {
        "email": "admin@college.edu",
        "password": "Admin123!",
    }
    response_legacy = client.post("/api/v1/auth/login", json=payload_legacy)
    assert response_legacy.status_code == 401

    # 2. Create an organisation and admin user, verify login
    org = Organisation(
        id="ORG-TEST-001",
        name="Test Organisation",
        ownership_type="GOVERNMENT",
        is_active=True,
    )
    db_session.add(org)

    admin_user = User(
        id="ADMIN_TEST_ORG",
        email="admin@testorg.edu",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Test Org Admin",
        role="ADMIN",
        organisation_id="ORG-TEST-001",
        is_active=True,
    )
    db_session.add(admin_user)
    db_session.commit()

    # Login with email
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@testorg.edu", "password": "AdminPass123!", "organisation_type": "GOVERNMENT"},
    )
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "ADMIN"

    # Login with user_id
    res_uid = client.post(
        "/api/v1/auth/login",
        json={"email": "ADMIN_TEST_ORG", "password": "AdminPass123!", "organisation_type": "GOVERNMENT"},
    )
    assert res_uid.status_code == 200
    assert res_uid.json()["user"]["id"] == "ADMIN_TEST_ORG"


def test_login_demo_viewer(client, db_session):
    """POST /api/v1/auth/login with Demo Viewer credentials must return 401."""
    seed_demo_data(db_session)

    payload = {
        "email": "demo@greennexa.com",
        "password": "DemoUser123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401


def test_login_invalid_password(client, db_session):
    """Wrong password should return 401 Unauthorized."""
    seed_demo_data(db_session)

    payload = {
        "email": "superadmin@greennexa.com",
        "password": "WrongPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


def test_login_nonexistent_user(client):
    """Unknown email should return 401 Unauthorized."""
    payload = {
        "email": "nobody@nowhere.com",
        "password": "SomePassword123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401


def test_get_current_user_me(client, db_session):
    """GET /api/v1/auth/me should return authenticated user profile."""
    seed_demo_data(db_session)

    # 1. Login with Super Admin
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@greennexa.com", "password": "SuperAdmin123!"},
    )
    token = login_res.json()["access_token"]

    # 2. Get /me with Bearer token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "superadmin@greennexa.com"
    assert me_data["role"] == "SUPER_ADMIN"


def test_get_current_user_me_missing_token(client):
    """GET /api/v1/auth/me without token should return 401 Unauthorized."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "Missing or malformed Authorization header" in response.json()["detail"]


def test_get_current_user_me_malformed_token(client):
    """GET /api/v1/auth/me with non-Bearer auth scheme should return 401 Unauthorized."""
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert response.status_code == 401
    assert "Missing or malformed Authorization header" in response.json()["detail"]


def test_get_current_user_me_invalid_token(client):
    """GET /api/v1/auth/me with invalid JWT should return 401 Unauthorized."""
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.jwt.string"})
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


def test_get_demo_accounts_endpoint(client):
    """GET /api/v1/auth/demo-accounts should return ONLY Super Admin demo account."""
    response = client.get("/api/v1/auth/demo-accounts")
    assert response.status_code == 200
    data = response.json()

    assert len(data["accounts"]) == 1
    assert data["accounts"][0]["role"] == "SUPER_ADMIN"
    assert data["accounts"][0]["user_id"] == "superadmin_demo"
    assert data["accounts"][0]["email"] == "superadmin@greennexa.com"


def test_seed_endpoint_rbac_permissions(client, db_session, auth_headers):
    """POST /api/v1/auth/seed should enforce RBAC role permissions."""
    # 1. Unauthenticated -> 401
    unauth_res = client.post("/api/v1/auth/seed")
    assert unauth_res.status_code == 401

    # 2. VIEWER role token -> 403 Forbidden
    viewer_headers = auth_headers("viewer_seed@test.com", "VIEWER", "ORG-COL-001")
    viewer_res = client.post("/api/v1/auth/seed", headers=viewer_headers)
    assert viewer_res.status_code == 403

    # 3. ADMIN -> 200 OK
    admin_headers = auth_headers("admin_seed@test.com", "ADMIN", "ORG-COL-001")
    admin_res = client.post("/api/v1/auth/seed", headers=admin_headers)
    assert admin_res.status_code == 200

    # 4. SUPER_ADMIN -> 200 OK
    super_headers = auth_headers("super_seed@test.com", "SUPER_ADMIN", "ORG-MAIN")
    super_res = client.post("/api/v1/auth/seed", headers=super_headers)
    assert super_res.status_code == 200
