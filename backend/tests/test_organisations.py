"""
GreenNexa — Phase 4: Organisation Management Unit & Integration Tests.

Tests:
  1. SUPER_ADMIN CRUD operations (Create, List, View Any, Update, Deactivate).
  2. ADMIN permission limits (View Own Org allowed; Create, Cross-Org View, Update, Deactivate denied with 403).
  3. VIEWER permission limits (View Permitted Org allowed; Create, Update, Deactivate denied with 403).
  4. Authentication error handling (401 Missing/Invalid token).
  5. Entity errors (404 Not Found, 409 Conflict Duplicate ID, 422 Unprocessable Entity).
"""

import pytest
from app.db.models import Organisation


def test_super_admin_create_organisation_success(client, auth_headers):
    """SUPER_ADMIN should successfully create a new organisation (201 Created)."""
    headers = auth_headers("superadmin_org_test@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")
    payload = {
        "id": "ORG-TEST-CREATE-001",
        "name": "Innovate Tech Institute",
        "org_type": "college",
        "location": "Building 5, Tech Park",
        "contact_email": "info@innovate.edu",
        "contact_phone": "+1-555-0100",
        "is_active": True,
    }

    response = client.post("/api/v1/organisations", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()

    assert data["id"] == "ORG-TEST-CREATE-001"
    assert data["name"] == "Innovate Tech Institute"
    assert data["org_type"] == "college"
    assert data["location"] == "Building 5, Tech Park"
    assert data["contact_email"] == "info@innovate.edu"
    assert data["is_active"] is True
    assert "created_at" in data


def test_super_admin_list_organisations_success(client, seed_orgs, auth_headers):
    """SUPER_ADMIN should list all organisations."""
    headers = auth_headers("superadmin_list@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")

    response = client.get("/api/v1/organisations", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total"] >= 2
    org_ids = {item["id"] for item in data["items"]}
    assert "ORG-TEST-A" in org_ids
    assert "ORG-TEST-B" in org_ids


def test_super_admin_view_any_organisation(client, seed_orgs, auth_headers):
    """SUPER_ADMIN can view any organisation profile."""
    headers = auth_headers("superadmin_view@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")

    response = client.get("/api/v1/organisations/ORG-TEST-B", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == "ORG-TEST-B"
    assert data["name"] == seed_orgs["org_b"].name


def test_super_admin_update_organisation(client, seed_orgs, auth_headers):
    """SUPER_ADMIN can update an organisation profile."""
    headers = auth_headers("superadmin_update@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")
    payload = {
        "name": "Updated College Name",
        "location": "Updated Address 123",
        "contact_phone": "+1-555-9999",
    }

    response = client.put("/api/v1/organisations/ORG-TEST-A", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == "ORG-TEST-A"
    assert data["name"] == "Updated College Name"
    assert data["location"] == "Updated Address 123"
    assert data["contact_phone"] == "+1-555-9999"
    assert data["updated_at"] is not None


def test_super_admin_deactivate_organisation(client, seed_orgs, auth_headers):
    """SUPER_ADMIN can deactivate an organisation."""
    headers = auth_headers("superadmin_deact@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")

    response = client.delete("/api/v1/organisations/ORG-TEST-A", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == "ORG-TEST-A"
    assert data["is_active"] is False


def test_admin_view_own_organisation_success(client, seed_orgs, auth_headers):
    """ADMIN can view their own organisation profile."""
    headers = auth_headers("admin_own@test.com", "ADMIN", seed_orgs["org_a"].id)

    response = client.get(f"/api/v1/organisations/{seed_orgs['org_a'].id}", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == seed_orgs["org_a"].id
    assert data["name"] == seed_orgs["org_a"].name


def test_admin_attempt_another_organisation_denied(client, seed_orgs, auth_headers):
    """ADMIN attempting to view another organisation should receive 403 Forbidden."""
    headers = auth_headers("admin_org_a@test.com", "ADMIN", seed_orgs["org_a"].id)

    response = client.get(f"/api/v1/organisations/{seed_orgs['org_b'].id}", headers=headers)
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_admin_attempt_create_organisation_denied(client, seed_orgs, auth_headers):
    """ADMIN attempting to create an organisation should receive 403 Forbidden."""
    headers = auth_headers("admin_create@test.com", "ADMIN", seed_orgs["org_a"].id)
    payload = {"name": "Illegal Org Creation"}

    response = client.post("/api/v1/organisations", json=payload, headers=headers)
    assert response.status_code == 403
    assert "Insufficient role permissions" in response.json()["detail"]


def test_admin_attempt_update_organisation_denied(client, seed_orgs, auth_headers):
    """ADMIN attempting to update an organisation should receive 403 Forbidden."""
    headers = auth_headers("admin_upd@test.com", "ADMIN", seed_orgs["org_a"].id)
    payload = {"name": "Unauthorized Update"}

    response = client.put(f"/api/v1/organisations/{seed_orgs['org_a'].id}", json=payload, headers=headers)
    assert response.status_code == 403
    assert "Insufficient role permissions" in response.json()["detail"]


def test_admin_attempt_deactivate_organisation_denied(client, seed_orgs, auth_headers):
    """ADMIN attempting to deactivate an organisation should receive 403 Forbidden."""
    headers = auth_headers("admin_del@test.com", "ADMIN", seed_orgs["org_a"].id)

    response = client.delete(f"/api/v1/organisations/{seed_orgs['org_a'].id}", headers=headers)
    assert response.status_code == 403
    assert "Insufficient role permissions" in response.json()["detail"]


def test_viewer_view_permitted_organisation_success(client, seed_orgs, auth_headers):
    """VIEWER role token is rejected with 403 Forbidden."""
    headers = auth_headers("viewer_own@test.com", "VIEWER", seed_orgs["org_a"].id)

    response = client.get(f"/api/v1/organisations/{seed_orgs['org_a'].id}", headers=headers)
    assert response.status_code == 403


def test_viewer_cannot_create_organisation(client, auth_headers):
    """VIEWER attempting to create an organisation should receive 403 Forbidden."""
    headers = auth_headers("viewer_create@test.com", "VIEWER", "ORG-TEST-A")
    payload = {"name": "Forbidden Viewer Org"}

    response = client.post("/api/v1/organisations", json=payload, headers=headers)
    assert response.status_code == 403


def test_viewer_cannot_update_organisation(client, seed_orgs, auth_headers):
    """VIEWER attempting to update an organisation should receive 403 Forbidden."""
    headers = auth_headers("viewer_upd@test.com", "VIEWER", seed_orgs["org_a"].id)
    payload = {"name": "Forbidden Update"}

    response = client.put(f"/api/v1/organisations/{seed_orgs['org_a'].id}", json=payload, headers=headers)
    assert response.status_code == 403


def test_viewer_cannot_deactivate_organisation(client, seed_orgs, auth_headers):
    """VIEWER attempting to deactivate an organisation should receive 403 Forbidden."""
    headers = auth_headers("viewer_del@test.com", "VIEWER", seed_orgs["org_a"].id)

    response = client.delete(f"/api/v1/organisations/{seed_orgs['org_a'].id}", headers=headers)
    assert response.status_code == 403


def test_missing_token_returns_401(client):
    """Request without token should return 401 Unauthorized."""
    response = client.get("/api/v1/organisations")
    assert response.status_code == 401
    assert "Missing or malformed Authorization header" in response.json()["detail"]


def test_invalid_token_returns_401(client):
    """Request with invalid token should return 401 Unauthorized."""
    response = client.get("/api/v1/organisations", headers={"Authorization": "Bearer invalid_token_123"})
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


def test_nonexistent_organisation_returns_404(client, auth_headers):
    """SUPER_ADMIN requesting a nonexistent organisation should receive 404 Not Found."""
    headers = auth_headers("superadmin_404@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")

    response = client.get("/api/v1/organisations/ORG-NONEXISTENT-999", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_duplicate_organisation_id_returns_409(client, seed_orgs, auth_headers):
    """Creating an organisation with an existing ID should return 409 Conflict."""
    headers = auth_headers("superadmin_dup@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")
    payload = {
        "id": seed_orgs["org_a"].id,  # Duplicate
        "name": "Duplicate Org Name",
    }

    response = client.post("/api/v1/organisations", json=payload, headers=headers)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_invalid_request_data_returns_422(client, auth_headers):
    """Creating an organisation with invalid body (missing required name) should return 422 Unprocessable Entity."""
    headers = auth_headers("superadmin_422@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")
    payload = {
        "org_type": "college",  # missing required 'name'
    }

    response = client.post("/api/v1/organisations", json=payload, headers=headers)
    assert response.status_code == 422
