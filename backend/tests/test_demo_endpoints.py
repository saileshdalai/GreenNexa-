"""
GreenNexa — Phase 14: Demo Endpoints Unit & Integration Tests.

Tests:
  1. POST /api/v1/simulator/synthetic/generate-reading generates single cycle
  2. POST /api/v1/simulator/synthetic/generate-anomaly triggers controlled anomaly
  3. POST /api/v1/simulator/synthetic/reset-demo clears synthetic readings & anomalies
  4. Role restrictions: ADMIN can trigger for own org, VIEWER is denied (403)
"""

import pytest
from app.db.models import AnomalyRecord, SensorReading


def test_generate_single_reading_endpoint(client, seed_orgs, auth_headers):
    """ADMIN can trigger an immediate single synthetic reading cycle."""
    headers = auth_headers("admin_a@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.post("/api/v1/simulator/synthetic/generate-reading?organisation_id=ORG-TEST-A", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["organisation_id"] == "ORG-TEST-A"
    assert data["readings_generated"] > 0


def test_generate_demo_anomaly_endpoint(client, seed_orgs, auth_headers, db_session):
    """ADMIN can trigger a controlled demo anomaly on energy metric."""
    headers = auth_headers("admin_a@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.post("/api/v1/simulator/synthetic/generate-anomaly?sensor_type=energy&organisation_id=ORG-TEST-A", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["organisation_id"] == "ORG-TEST-A"
    assert data["anomalies_generated"] == 1
    assert data["details"][0]["sensor_type"] == "energy"

    # Verify DB anomaly record was created
    anom = db_session.query(AnomalyRecord).filter_by(organisation_id="ORG-TEST-A", metric="energy").order_by(AnomalyRecord.timestamp.desc()).first()
    assert anom is not None
    assert anom.severity == "HIGH"


def test_reset_demo_data_endpoint(client, seed_orgs, auth_headers, db_session):
    """ADMIN can safely reset synthetic demo readings & anomalies for their organisation."""
    headers = auth_headers("admin_a@greennexa.com", "ADMIN", "ORG-TEST-A")

    # Generate some readings & anomaly first
    client.post("/api/v1/simulator/synthetic/generate-anomaly?sensor_type=energy&organisation_id=ORG-TEST-A", headers=headers)

    res = client.post("/api/v1/simulator/synthetic/reset-demo?organisation_id=ORG-TEST-A", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["readings_deleted"] > 0
    assert data["anomalies_deleted"] > 0

    # Verify DB is clean for synthetic readings
    readings = db_session.query(SensorReading).filter_by(organisation_id="ORG-TEST-A", source="synthetic").all()
    assert len(readings) == 0


def test_demo_endpoints_rbac_restrictions(client, seed_orgs, auth_headers):
    """VIEWER role cannot trigger demo endpoints (403 Forbidden)."""
    headers = auth_headers("viewer_a@greennexa.com", "VIEWER", "ORG-TEST-A")

    res1 = client.post("/api/v1/simulator/synthetic/generate-reading", headers=headers)
    assert res1.status_code == 403

    res2 = client.post("/api/v1/simulator/synthetic/generate-anomaly", headers=headers)
    assert res2.status_code == 403

    res3 = client.post("/api/v1/simulator/synthetic/reset-demo", headers=headers)
    assert res3.status_code == 403
