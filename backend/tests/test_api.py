"""
GreenNexa — API Integration Tests.

Tests FastAPI endpoints:
  - GET  /health
  - POST /api/v1/anomalies/detect
  - POST /api/v1/anomalies/classify
  - GET  /api/v1/anomalies
  - POST /api/v1/recommendations/generate
  - POST /api/v1/recommendations/preview
  - GET  /api/v1/recommendations
"""

import pytest
from app.db.models import AnomalyRecord
from tests.test_anomaly_detector import _seed_readings


def test_health_check(client):
    """Health check endpoint should return 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_api_detect_anomaly_endpoint(client, db_session, seed_orgs, auth_headers):
    """POST /api/v1/anomalies/detect should process reading and return anomaly result for ADMIN."""
    org_a = seed_orgs["org_a"]
    headers = auth_headers("admin_detect@test.com", "ADMIN", org_a.id)
    _seed_readings(db_session, org_a.id, "energy", [50.0, 51.0, 49.0, 50.5, 49.5])

    payload = {
        "organisation_id": org_a.id,
        "facility_id": "FAC-01",
        "metric": "energy",
        "sensor_type": "energy",
        "value": 150.0,  # High spike
        "unit": "kWh",
    }

    response = client.post("/api/v1/anomalies/detect", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data is not None
    assert data["id"] is not None
    assert data["organisation_id"] == org_a.id
    assert data["facility_id"] == "FAC-01"
    assert data["metric"] == "energy"
    assert data["value"] == 150.0
    assert data["severity"] in ("HIGH", "CRITICAL")


def test_api_classify_preview_endpoint(client, auth_headers):
    """POST /api/v1/anomalies/classify should classify without saving to DB."""
    headers = auth_headers("admin_preview@test.com", "ADMIN", "ORG-TEST-A")
    payload = {
        "metric": "temperature",
        "value": 38.0,
        "unit": "°C",
        "history_values": [22.0, 22.5, 21.8, 22.1, 21.9, 22.0],
    }

    response = client.post("/api/v1/anomalies/classify", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["severity"] in ("HIGH", "CRITICAL")
    assert data["z_score"] > 3.0
    assert "reason" in data


def test_api_list_anomalies_org_isolated(client, db_session, seed_orgs, auth_headers):
    """GET /api/v1/anomalies should list anomalies filtered by user organisation_id."""
    org_a = seed_orgs["org_a"]
    org_b = seed_orgs["org_b"]

    headers_a = auth_headers("admin_a_list@test.com", "ADMIN", org_a.id)
    headers_b = auth_headers("admin_b_list@test.com", "ADMIN", org_b.id)

    anom_a = AnomalyRecord(
        organisation_id=org_a.id,
        facility_id="FAC-A",
        metric="water",
        value=500.0,
        severity="HIGH",
        reason="Water leak",
    )
    anom_b = AnomalyRecord(
        organisation_id=org_b.id,
        facility_id="FAC-B",
        metric="energy",
        value=900.0,
        severity="CRITICAL",
        reason="Power spike",
    )
    db_session.add_all([anom_a, anom_b])
    db_session.commit()

    # Admin A accessing Org A
    res_a = client.get(f"/api/v1/anomalies?organisation_id={org_a.id}", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert len(data_a["items"]) == 1
    assert data_a["items"][0]["organisation_id"] == org_a.id
    assert data_a["items"][0]["metric"] == "water"

    # Admin B accessing Org B
    res_b = client.get(f"/api/v1/anomalies?organisation_id={org_b.id}", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert len(data_b["items"]) == 1
    assert data_b["items"][0]["organisation_id"] == org_b.id
    assert data_b["items"][0]["metric"] == "energy"

    # Admin A trying to access Org B -> 403 Forbidden
    res_forbidden = client.get(f"/api/v1/anomalies?organisation_id={org_b.id}", headers=headers_a)
    assert res_forbidden.status_code == 403
    assert "Access denied" in res_forbidden.json()["detail"]


def test_api_recommendation_preview_endpoint(client, auth_headers):
    """POST /api/v1/recommendations/preview should preview recommendation."""
    headers = auth_headers("admin_rec_prev@test.com", "ADMIN", "ORG-TEST-A")
    payload = {
        "organisation_id": "ORG-TEST-A",
        "metric": "energy",
        "current_value": 250.0,
        "expected_range_min": 90.0,
        "expected_range_max": 110.0,
        "severity": "HIGH",
        "history_values": [100.0, 102.0, 98.0, 101.0, 99.0, 100.5],
        "unit": "kWh",
    }

    response = client.post("/api/v1/recommendations/preview", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["generated"] is True
    assert data["severity"] == "HIGH"
    assert len(data["possible_causes"]) > 0
    assert len(data["recommended_actions"]) > 0


def test_api_generate_recommendation_endpoint(client, db_session, seed_orgs, auth_headers):
    """POST /api/v1/recommendations/generate should generate and persist rec for anomaly."""
    org_a = seed_orgs["org_a"]
    headers = auth_headers("admin_gen_rec@test.com", "ADMIN", org_a.id)
    _seed_readings(db_session, org_a.id, "co2", [400.0, 410.0, 390.0, 405.0, 395.0])

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        facility_id="FAC-01",
        metric="co2",
        sensor_type="co2",
        value=1400.0,
        expected_min=380.0,
        expected_max=420.0,
        anomaly_score=0.95,
        severity="HIGH",
        reason="High CO2 concentration",
    )
    db_session.add(anomaly)
    db_session.commit()

    payload = {"anomaly_id": anomaly.id}

    response = client.post("/api/v1/recommendations/generate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["anomaly_id"] == anomaly.id
    assert data["metric"] == "co2"
    assert data["severity"] == "HIGH"
    assert data["data_sufficient"] is True
    assert "ventilation" in data["summary"].lower()


def test_rbac_viewer_denied_write_operations(client, db_session, seed_orgs, auth_headers):
    """VIEWER role must be denied (403) across endpoints."""
    org_a = seed_orgs["org_a"]
    viewer_headers = auth_headers("viewer_readonly@college.edu", "VIEWER", org_a.id)

    # Detect write
    detect_res = client.post(
        "/api/v1/anomalies/detect",
        json={
            "organisation_id": org_a.id,
            "metric": "energy",
            "value": 200.0,
        },
        headers=viewer_headers,
    )
    assert detect_res.status_code == 403

    # Seed write
    seed_res = client.post("/api/v1/auth/seed", headers=viewer_headers)
    assert seed_res.status_code == 403


def test_rbac_super_admin_cross_organisation_access(client, db_session, seed_orgs, auth_headers):
    """SUPER_ADMIN role should be permitted to access any organisation data."""
    org_b = seed_orgs["org_b"]
    super_headers = auth_headers("superadmin@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")

    anom_b = AnomalyRecord(
        organisation_id=org_b.id,
        facility_id="FAC-B",
        metric="energy",
        value=950.0,
        severity="CRITICAL",
        reason="Critical Power Overload",
    )
    db_session.add(anom_b)
    db_session.commit()

    # Super Admin querying Org B explicitly
    response = client.get(f"/api/v1/anomalies?organisation_id={org_b.id}", headers=super_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["organisation_id"] == org_b.id

