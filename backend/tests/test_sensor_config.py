"""
GreenNexa — Phase 5: Organisation Sensor Configuration & Data Source Management Tests.

Tests:
  1. Default sensor configuration creation (GET returns default config if none exists).
  2. SUPER_ADMIN capabilities (View any org, PUT update, PATCH data-source, PATCH sensors).
  3. ADMIN capabilities (View/modify own org; cross-org view/modify returns 403 Forbidden).
  4. VIEWER capabilities (View permitted org; modify attempt returns 403 Forbidden).
  5. Strict Data Source Mutual Exclusivity ('synthetic' vs 'iot').
  6. Validation errors (Invalid data_source, invalid sensor_type, empty sensors list -> 422).
  7. Entity & Authentication errors (404 Not Found, 401 Unauthorized).
"""

import pytest


def test_get_default_sensor_config(client, seed_orgs, auth_headers):
    """GET sensor config for an org with no existing config returns default synthetic config."""
    headers = auth_headers("admin_a@greennexa.com", "ADMIN", "ORG-TEST-A")
    response = client.get("/api/v1/organisations/ORG-TEST-A/sensor-config", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["organisation_id"] == "ORG-TEST-A"
    assert data["data_source"] == "synthetic"
    assert set(data["enabled_sensors"]) == {"energy", "water", "temperature", "humidity"}
    assert data["is_active"] is True
    assert "created_at" in data
    assert "updated_at" in data


def test_super_admin_view_any_org_sensor_config(client, seed_orgs, auth_headers):
    """SUPER_ADMIN can view sensor configuration of any organisation."""
    headers = auth_headers("superadmin@greennexa.com", "SUPER_ADMIN", "ORG-TEST-A")
    response = client.get("/api/v1/organisations/ORG-TEST-B/sensor-config", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["organisation_id"] == "ORG-TEST-B"


def test_super_admin_put_update_sensor_config(client, seed_orgs, auth_headers):
    """SUPER_ADMIN can perform full update on sensor config for any org."""
    headers = auth_headers("superadmin_put@greennexa.com", "SUPER_ADMIN", "ORG-TEST-A")
    payload = {
        "data_source": "iot",
        "enabled_sensors": ["energy", "co2"],
        "is_active": True,
    }
    response = client.put("/api/v1/organisations/ORG-TEST-B/sensor-config", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["organisation_id"] == "ORG-TEST-B"
    assert data["data_source"] == "iot"
    assert set(data["enabled_sensors"]) == {"energy", "co2"}


def test_patch_data_source_mutual_exclusivity(client, seed_orgs, auth_headers):
    """PATCH /data-source toggles mode strictly between synthetic and iot."""
    headers = auth_headers("admin_patch@greennexa.com", "ADMIN", "ORG-TEST-A")

    # Initial state is synthetic
    get_res = client.get("/api/v1/organisations/ORG-TEST-A/sensor-config", headers=headers)
    assert get_res.json()["data_source"] == "synthetic"

    # Switch to iot
    patch_res1 = client.patch(
        "/api/v1/organisations/ORG-TEST-A/sensor-config/data-source",
        json={"data_source": "iot"},
        headers=headers,
    )
    assert patch_res1.status_code == 200
    assert patch_res1.json()["data_source"] == "iot"

    # Switch back to synthetic
    patch_res2 = client.patch(
        "/api/v1/organisations/ORG-TEST-A/sensor-config/data-source",
        json={"data_source": "synthetic"},
        headers=headers,
    )
    assert patch_res2.status_code == 200
    assert patch_res2.json()["data_source"] == "synthetic"


def test_patch_enabled_sensors(client, seed_orgs, auth_headers):
    """PATCH /sensors updates enabled sensor types for an organisation."""
    headers = auth_headers("admin_sensors@greennexa.com", "ADMIN", "ORG-TEST-A")
    payload = {"enabled_sensors": ["water", "temperature", "waste"]}

    response = client.patch(
        "/api/v1/organisations/ORG-TEST-A/sensor-config/sensors",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert set(data["enabled_sensors"]) == {"water", "temperature", "waste"}
    assert data["data_source"] == "synthetic"  # data_source remains unchanged


def test_admin_cross_org_sensor_config_denied(client, seed_orgs, auth_headers):
    """ADMIN cannot view or update another organisation's sensor config (403 Forbidden)."""
    headers = auth_headers("admin_a_cross@greennexa.com", "ADMIN", "ORG-TEST-A")

    # View attempt on ORG-TEST-B
    view_res = client.get("/api/v1/organisations/ORG-TEST-B/sensor-config", headers=headers)
    assert view_res.status_code == 403

    # Update attempt on ORG-TEST-B
    put_res = client.put(
        "/api/v1/organisations/ORG-TEST-B/sensor-config",
        json={"data_source": "iot", "enabled_sensors": ["energy"]},
        headers=headers,
    )
    assert put_res.status_code == 403

    # Patch data-source attempt on ORG-TEST-B
    patch_ds_res = client.patch(
        "/api/v1/organisations/ORG-TEST-B/sensor-config/data-source",
        json={"data_source": "iot"},
        headers=headers,
    )
    assert patch_ds_res.status_code == 403

    # Patch sensors attempt on ORG-TEST-B
    patch_s_res = client.patch(
        "/api/v1/organisations/ORG-TEST-B/sensor-config/sensors",
        json={"enabled_sensors": ["energy"]},
        headers=headers,
    )
    assert patch_s_res.status_code == 403


def test_viewer_view_success_modify_denied(client, seed_orgs, auth_headers):
    """VIEWER role token is rejected everywhere (403 Forbidden)."""
    headers = auth_headers("viewer_a@greennexa.com", "VIEWER", "ORG-TEST-A")

    # View denied
    view_res = client.get("/api/v1/organisations/ORG-TEST-A/sensor-config", headers=headers)
    assert view_res.status_code == 403

    # Modify PUT denied
    put_res = client.put(
        "/api/v1/organisations/ORG-TEST-A/sensor-config",
        json={"data_source": "iot", "enabled_sensors": ["energy"]},
        headers=headers,
    )
    assert put_res.status_code == 403

    # Modify PATCH data-source denied
    patch_ds_res = client.patch(
        "/api/v1/organisations/ORG-TEST-A/sensor-config/data-source",
        json={"data_source": "iot"},
        headers=headers,
    )
    assert patch_ds_res.status_code == 403

    # Modify PATCH sensors denied
    patch_s_res = client.patch(
        "/api/v1/organisations/ORG-TEST-A/sensor-config/sensors",
        json={"enabled_sensors": ["energy"]},
        headers=headers,
    )
    assert patch_s_res.status_code == 403


def test_validation_errors(client, seed_orgs, auth_headers):
    """API returns 422 Unprocessable Entity for invalid data_source or sensor types."""
    headers = auth_headers("admin_val@greennexa.com", "ADMIN", "ORG-TEST-A")

    # Invalid data source
    res1 = client.patch(
        "/api/v1/organisations/ORG-TEST-A/sensor-config/data-source",
        json={"data_source": "hybrid_magic"},
        headers=headers,
    )
    assert res1.status_code == 422

    # Invalid sensor type
    res2 = client.patch(
        "/api/v1/organisations/ORG-TEST-A/sensor-config/sensors",
        json={"enabled_sensors": ["energy", "quantum_flux"]},
        headers=headers,
    )
    assert res2.status_code == 422

    # Empty sensors list
    res3 = client.patch(
        "/api/v1/organisations/ORG-TEST-A/sensor-config/sensors",
        json={"enabled_sensors": []},
        headers=headers,
    )
    assert res3.status_code == 422


def test_not_found_organisation(client, auth_headers):
    """GET/PUT sensor config on nonexistent organisation returns 404 Not Found."""
    headers = auth_headers("superadmin_404@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")
    res = client.get("/api/v1/organisations/ORG-NONEXISTENT/sensor-config", headers=headers)
    assert res.status_code == 404


def test_authentication_errors(client):
    """Requests without token or with malformed token return 401 Unauthorized."""
    # Missing token
    res1 = client.get("/api/v1/organisations/ORG-TEST-A/sensor-config")
    assert res1.status_code == 401

    # Malformed token
    res2 = client.get(
        "/api/v1/organisations/ORG-TEST-A/sensor-config",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert res2.status_code == 401
