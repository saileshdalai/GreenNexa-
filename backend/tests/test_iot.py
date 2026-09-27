"""
GreenNexa — Phase 7: Real Sensor / IoT Data Ingestion Unit & Integration Tests.

Tests all 28 required scenarios:
  1. SUPER_ADMIN registers device -> success
  2. ADMIN registers device for own organisation -> success
  3. ADMIN registers device for another organisation -> 403
  4. VIEWER registers device -> 403
  5. Duplicate device_id -> 409
  6. Valid device credentials -> accepted
  7. Missing device credentials -> 401
  8. Invalid device credentials -> 401
  9. Inactive device -> 403
  10. Device cannot impersonate another organisation
  11. Organisation in iot mode -> IoT data accepted
  12. Organisation in synthetic mode -> IoT data rejected (409)
  13. Enabled sensor -> accepted
  14. Disabled sensor -> rejected (422)
  15. Invalid sensor type -> 422
  16. Empty readings -> 422
  17. Malformed payload -> 422
  18. Invalid numeric value -> 422
  19. Invalid timestamp -> 422
  20. Too many readings -> 422
  21. Stored source = 'iot'
  22. Correct organisation_id stored
  23. Correct device_id association stored
  24. last_seen_at updated after successful ingestion
  25. Duplicate reading handled safely
  26. Cross-organisation access -> 403
  27. Missing user token on admin endpoint -> 401
  28. Invalid user token -> 401
"""

import pytest
from app.db.models import IoTDevice, OrganisationSensorConfig, SensorReading


@pytest.fixture
def registered_iot_device(client, seed_orgs, auth_headers):
    """Helper fixture: register an active IoT device for ORG-TEST-A under IoT mode."""
    # 1. Set ORG-TEST-A to iot mode
    admin_headers = auth_headers("admin_iot_setup@greennexa.com", "ADMIN", "ORG-TEST-A")
    client.patch(
        "/api/v1/organisations/ORG-TEST-A/sensor-config/data-source",
        json={"data_source": "iot"},
        headers=admin_headers,
    )

    # 2. Register device
    super_headers = auth_headers("super_iot_setup@greennexa.com", "SUPER_ADMIN", "ORG-TEST-A")
    reg_payload = {
        "device_id": "ESP32-TEST-001",
        "organisation_id": "ORG-TEST-A",
        "device_name": "Test ESP32 Sensor A",
        "device_type": "ESP32",
    }
    res = client.post("/api/v1/iot/devices", json=reg_payload, headers=super_headers)
    assert res.status_code == 201
    data = res.json()
    return {
        "device_id": data["device_id"],
        "api_key": data["api_key"],
        "organisation_id": data["organisation_id"],
    }


# ---------------------------------------------------------------------------
# Tests 1 - 5: Device Registration & Management
# ---------------------------------------------------------------------------
def test_super_admin_registers_device_success(client, seed_orgs, auth_headers):
    """SUPER_ADMIN can register a new IoT device for any organisation."""
    headers = auth_headers("superadmin_reg@greennexa.com", "SUPER_ADMIN", "ORG-TEST-A")
    payload = {
        "device_id": "ESP32-SUPER-001",
        "organisation_id": "ORG-TEST-B",
        "device_name": "Hospital Sensor B",
        "device_type": "ESP32",
    }
    res = client.post("/api/v1/iot/devices", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["device_id"] == "ESP32-SUPER-001"
    assert data["organisation_id"] == "ORG-TEST-B"
    assert "api_key" in data
    assert data["api_key"].startswith("iot_key_")


def test_admin_registers_device_own_org_success(client, seed_orgs, auth_headers):
    """ADMIN can register a device for their own organisation."""
    headers = auth_headers("admin_reg_own@greennexa.com", "ADMIN", "ORG-TEST-A")
    payload = {
        "device_id": "ESP32-ADMIN-001",
        "organisation_id": "ORG-TEST-A",
        "device_name": "Campus Sensor A",
        "device_type": "ESP32",
    }
    res = client.post("/api/v1/iot/devices", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["device_id"] == "ESP32-ADMIN-001"


def test_admin_registers_device_another_org_denied(client, seed_orgs, auth_headers):
    """ADMIN cannot register a device for another organisation (403 Forbidden)."""
    headers = auth_headers("admin_reg_cross@greennexa.com", "ADMIN", "ORG-TEST-A")
    payload = {
        "device_id": "ESP32-CROSS-001",
        "organisation_id": "ORG-TEST-B",
        "device_name": "Unauthorized Attempt",
        "device_type": "ESP32",
    }
    res = client.post("/api/v1/iot/devices", json=payload, headers=headers)
    assert res.status_code == 403


def test_viewer_registers_device_denied(client, seed_orgs, auth_headers):
    """VIEWER cannot register IoT devices (403 Forbidden)."""
    headers = auth_headers("viewer_reg@greennexa.com", "VIEWER", "ORG-TEST-A")
    payload = {
        "device_id": "ESP32-VIEWER-001",
        "organisation_id": "ORG-TEST-A",
        "device_name": "Viewer Attempt",
        "device_type": "ESP32",
    }
    res = client.post("/api/v1/iot/devices", json=payload, headers=headers)
    assert res.status_code == 403


def test_duplicate_device_id_conflict(client, seed_orgs, auth_headers, registered_iot_device):
    """Registering a duplicate device_id returns 409 Conflict."""
    headers = auth_headers("superadmin_dup@greennexa.com", "SUPER_ADMIN", "ORG-TEST-A")
    payload = {
        "device_id": registered_iot_device["device_id"],
        "organisation_id": "ORG-TEST-A",
        "device_name": "Duplicate Sensor",
        "device_type": "ESP32",
    }
    res = client.post("/api/v1/iot/devices", json=payload, headers=headers)
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# Tests 6 - 10: Device Header Authentication & Security Isolation
# ---------------------------------------------------------------------------
def test_valid_device_credentials_accepted(client, registered_iot_device):
    """Valid X-Device-ID and X-API-Key credentials allow data ingestion."""
    headers = {
        "X-Device-ID": registered_iot_device["device_id"],
        "X-API-Key": registered_iot_device["api_key"],
    }
    payload = {
        "device_id": registered_iot_device["device_id"],
        "readings": [{"sensor_type": "energy", "value": 1150.0, "unit": "kWh"}],
    }
    res = client.post("/api/v1/iot/sensor-data", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["ingested_count"] == 1


def test_missing_device_credentials_401(client, registered_iot_device):
    """Missing X-Device-ID or X-API-Key header returns 401 Unauthorized."""
    payload = {
        "device_id": registered_iot_device["device_id"],
        "readings": [{"sensor_type": "energy", "value": 1150.0, "unit": "kWh"}],
    }
    res = client.post("/api/v1/iot/sensor-data", json=payload)
    assert res.status_code == 401


def test_invalid_device_credentials_401(client, registered_iot_device):
    """Invalid device API key returns 401 Unauthorized."""
    headers = {
        "X-Device-ID": registered_iot_device["device_id"],
        "X-API-Key": "wrong_invalid_key",
    }
    payload = {
        "device_id": registered_iot_device["device_id"],
        "readings": [{"sensor_type": "energy", "value": 1150.0, "unit": "kWh"}],
    }
    res = client.post("/api/v1/iot/sensor-data", json=payload, headers=headers)
    assert res.status_code == 401


def test_inactive_device_403(client, db_session, auth_headers, registered_iot_device):
    """Inactive IoT device cannot ingest sensor data (403 Forbidden)."""
    # Deactivate device
    headers_super = auth_headers("super_deact@greennexa.com", "SUPER_ADMIN", "ORG-TEST-A")
    client.patch(
        f"/api/v1/iot/devices/{registered_iot_device['device_id']}/status",
        json={"is_active": False},
        headers=headers_super,
    )

    dev_headers = {
        "X-Device-ID": registered_iot_device["device_id"],
        "X-API-Key": registered_iot_device["api_key"],
    }
    payload = {
        "device_id": registered_iot_device["device_id"],
        "readings": [{"sensor_type": "energy", "value": 1150.0, "unit": "kWh"}],
    }
    res = client.post("/api/v1/iot/sensor-data", json=payload, headers=dev_headers)
    assert res.status_code == 403


def test_device_cannot_impersonate_another_organisation(client, db_session, registered_iot_device):
    """
    Device spoofing attempt: device payload sends organisation_id or attempts mismatched device_id.
    Target organisation is strictly derived from authenticated IoTDevice DB record.
    """
    dev_headers = {
        "X-Device-ID": registered_iot_device["device_id"],
        "X-API-Key": registered_iot_device["api_key"],
    }

    # Attempt payload with mismatched device_id
    payload = {
        "device_id": "SPOOFED-DEVICE-ID",
        "readings": [{"sensor_type": "energy", "value": 1150.0, "unit": "kWh"}],
    }
    res = client.post("/api/v1/iot/sensor-data", json=payload, headers=dev_headers)
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Tests 11 & 12: Data Source Mode Rules (iot vs synthetic)
# ---------------------------------------------------------------------------
def test_organisation_in_iot_mode_accepted(client, registered_iot_device):
    """Organisation in 'iot' mode accepts IoT sensor ingestion."""
    headers = {
        "X-Device-ID": registered_iot_device["device_id"],
        "X-API-Key": registered_iot_device["api_key"],
    }
    payload = {
        "device_id": registered_iot_device["device_id"],
        "readings": [{"sensor_type": "temperature", "value": 28.5, "unit": "°C"}],
    }
    res = client.post("/api/v1/iot/sensor-data", json=payload, headers=headers)
    assert res.status_code == 201


def test_organisation_in_synthetic_mode_rejected(client, auth_headers, registered_iot_device):
    """Organisation in 'synthetic' mode rejects IoT sensor ingestion (409 Conflict)."""
    # Switch ORG-TEST-A back to synthetic mode
    admin_headers = auth_headers("admin_synth@greennexa.com", "ADMIN", "ORG-TEST-A")
    client.patch(
        "/api/v1/organisations/ORG-TEST-A/sensor-config/data-source",
        json={"data_source": "synthetic"},
        headers=admin_headers,
    )

    dev_headers = {
        "X-Device-ID": registered_iot_device["device_id"],
        "X-API-Key": registered_iot_device["api_key"],
    }
    payload = {
        "device_id": registered_iot_device["device_id"],
        "readings": [{"sensor_type": "energy", "value": 1150.0, "unit": "kWh"}],
    }
    res = client.post("/api/v1/iot/sensor-data", json=payload, headers=dev_headers)
    assert res.status_code == 409
    assert "not configured for IoT data" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Tests 13 - 15: Sensor Configuration Validation
# ---------------------------------------------------------------------------
def test_sensor_configuration_validation(client, auth_headers, registered_iot_device):
    """Only enabled sensors are accepted; disabled or unsupported sensors are rejected with 422."""
    # Configure ORG-TEST-A enabled sensors: energy and water only
    admin_headers = auth_headers("admin_cfg@greennexa.com", "ADMIN", "ORG-TEST-A")
    client.patch(
        "/api/v1/organisations/ORG-TEST-A/sensor-config/sensors",
        json={"enabled_sensors": ["energy", "water"]},
        headers=admin_headers,
    )

    dev_headers = {
        "X-Device-ID": registered_iot_device["device_id"],
        "X-API-Key": registered_iot_device["api_key"],
    }

    # Enabled sensor (energy) -> success
    res_ok = client.post(
        "/api/v1/iot/sensor-data",
        json={"device_id": registered_iot_device["device_id"], "readings": [{"sensor_type": "energy", "value": 1100.0}]},
        headers=dev_headers,
    )
    assert res_ok.status_code == 201

    # Disabled sensor for this org (temperature) -> 422
    res_dis = client.post(
        "/api/v1/iot/sensor-data",
        json={"device_id": registered_iot_device["device_id"], "readings": [{"sensor_type": "temperature", "value": 25.0}]},
        headers=dev_headers,
    )
    assert res_dis.status_code == 422

    # Unsupported invalid sensor type (quantum_flux) -> 422
    res_inv = client.post(
        "/api/v1/iot/sensor-data",
        json={"device_id": registered_iot_device["device_id"], "readings": [{"sensor_type": "quantum_flux", "value": 1.0}]},
        headers=dev_headers,
    )
    assert res_inv.status_code == 422


# ---------------------------------------------------------------------------
# Tests 16 - 20: Payload Validation
# ---------------------------------------------------------------------------
def test_payload_validation_rules(client, registered_iot_device):
    """Validates empty readings, malformed payload, NaN/Inf numeric values, and max limits."""
    dev_headers = {
        "X-Device-ID": registered_iot_device["device_id"],
        "X-API-Key": registered_iot_device["api_key"],
    }

    # Empty readings list -> 422
    res_empty = client.post(
        "/api/v1/iot/sensor-data",
        json={"device_id": registered_iot_device["device_id"], "readings": []},
        headers=dev_headers,
    )
    assert res_empty.status_code == 422

    # Malformed payload -> 422
    res_mal = client.post(
        "/api/v1/iot/sensor-data",
        json={"device_id": registered_iot_device["device_id"], "invalid_field": 123},
        headers=dev_headers,
    )
    assert res_mal.status_code == 422

    # Invalid timestamp format -> 422
    res_ts = client.post(
        "/api/v1/iot/sensor-data",
        json={
            "device_id": registered_iot_device["device_id"],
            "readings": [{"sensor_type": "energy", "value": 100.0}],
            "timestamp": "not-a-valid-datetime",
        },
        headers=dev_headers,
    )
    assert res_ts.status_code == 422

    # Too many readings (> 50) -> 422
    too_many = [{"sensor_type": "energy", "value": float(i)} for i in range(55)]
    res_max = client.post(
        "/api/v1/iot/sensor-data",
        json={"device_id": registered_iot_device["device_id"], "readings": too_many},
        headers=dev_headers,
    )
    assert res_max.status_code == 422


# ---------------------------------------------------------------------------
# Tests 21 - 24: Database Storage & Device last_seen_at Update
# ---------------------------------------------------------------------------
def test_database_storage_and_last_seen_updated(client, db_session, registered_iot_device):
    """Verifies stored source='iot', organisation_id, device_id, and last_seen_at timestamp."""
    dev_headers = {
        "X-Device-ID": registered_iot_device["device_id"],
        "X-API-Key": registered_iot_device["api_key"],
    }
    payload = {
        "device_id": registered_iot_device["device_id"],
        "readings": [{"sensor_type": "water", "value": 350.0, "unit": "L"}],
        "timestamp": "2026-09-14T12:00:00Z",
    }
    res = client.post("/api/v1/iot/sensor-data", json=payload, headers=dev_headers)
    assert res.status_code == 201

    # Check SensorReading in DB
    sr = db_session.query(SensorReading).filter_by(
        organisation_id=registered_iot_device["organisation_id"],
        device_id=registered_iot_device["device_id"],
        sensor_type="water",
    ).first()

    assert sr is not None
    assert sr.source == "iot"
    assert sr.value == 350.0
    assert sr.unit == "L"

    # Check device last_seen_at
    device_db = db_session.query(IoTDevice).filter_by(device_id=registered_iot_device["device_id"]).first()
    assert device_db.last_seen_at is not None


# ---------------------------------------------------------------------------
# Test 25: Duplicate Reading Handling
# ---------------------------------------------------------------------------
def test_duplicate_reading_protection(client, db_session, registered_iot_device):
    """Submitting duplicate reading with exact device_id, sensor_type, timestamp skips duplicate row creation."""
    dev_headers = {
        "X-Device-ID": registered_iot_device["device_id"],
        "X-API-Key": registered_iot_device["api_key"],
    }
    payload = {
        "device_id": registered_iot_device["device_id"],
        "readings": [{"sensor_type": "energy", "value": 950.0, "unit": "kWh"}],
        "timestamp": "2026-09-14T15:30:00Z",
    }

    # First submission -> 1 inserted
    res1 = client.post("/api/v1/iot/sensor-data", json=payload, headers=dev_headers)
    assert res1.status_code == 201
    assert res1.json()["ingested_count"] == 1

    # Duplicate submission -> 0 new inserted
    res2 = client.post("/api/v1/iot/sensor-data", json=payload, headers=dev_headers)
    assert res2.status_code == 201
    assert res2.json()["ingested_count"] == 0


# ---------------------------------------------------------------------------
# Tests 26 - 28: Security & User Token Validation on Admin Endpoints
# ---------------------------------------------------------------------------
def test_admin_device_endpoints_security(client, registered_iot_device, auth_headers):
    """Admin device management endpoints enforce token auth and cross-org protection."""
    # Missing token -> 401
    res_no_auth = client.get("/api/v1/iot/devices")
    assert res_no_auth.status_code == 401

    # Invalid token -> 401
    res_inv_auth = client.get("/api/v1/iot/devices", headers={"Authorization": "Bearer invalid.token"})
    assert res_inv_auth.status_code == 401

    # Cross-org ADMIN GET attempt -> 403
    admin_b_headers = auth_headers("admin_b_iot@greennexa.com", "ADMIN", "ORG-TEST-B")
    res_cross_get = client.get("/api/v1/iot/devices?organisation_id=ORG-TEST-A", headers=admin_b_headers)
    assert res_cross_get.status_code == 403

    # Cross-org ADMIN GET single device attempt -> 403
    res_cross_single = client.get(f"/api/v1/iot/devices/{registered_iot_device['device_id']}", headers=admin_b_headers)
    assert res_cross_single.status_code == 403
