"""
Tests for SUPER_ADMIN Edit Existing Organisation configuration API.
"""

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import (
    Organisation,
    User,
    FacilityBlock,
    SensorReading,
    AnomalyRecord,
    AIRecommendation,
    OrganisationSensorConfig,
)


def _seed_complete_org(db: Session, org_id: str = "ORG-EDIT-TEST") -> Organisation:
    """Helper to seed an organisation with admin, blocks, and sensor configs."""
    org = Organisation(
        id=org_id,
        name="Apex Research Institute",
        org_type="research",
        facility_name="Apex Research Main Campus",
        state="Karnataka",
        district="Bengaluru Urban",
        city="Bengaluru",
        address="100 Innovation Way",
        location="100 Innovation Way, Bengaluru, Bengaluru Urban, Karnataka",
        contact_phone="+91 9876543210",
        org_code="APEX-RES",
    )
    db.add(org)
    db.flush()

    # Seed Admin user
    admin = User(
        email=f"admin_{org_id.lower()}@greennexa.ai",
        hashed_password=hash_password("Password123!"),
        full_name="Dr. Jane Doe",
        phone="+91 9876543210",
        role=User.ROLE_ADMIN,
        organisation_id=org_id,
    )
    db.add(admin)

    # Add blocks
    b1 = FacilityBlock(
        organisation_id=org_id,
        block_id="BLK-001",
        block_name="Block A - Labs",
        is_active=True,
    )
    b2 = FacilityBlock(
        organisation_id=org_id,
        block_id="BLK-002",
        block_name="Block B - Admin",
        is_active=True,
    )
    db.add_all([b1, b2])

    # Sensor config
    sensor_configs = {
        "energy": {
            "baseline": 450.0,
            "warning_threshold": 15.0,
            "critical_threshold": 30.0,
            "unit": "kWh",
        },
        "water": {
            "baseline": 12000.0,
            "warning_threshold": 20.0,
            "critical_threshold": 40.0,
            "unit": "L",
        },
    }
    cfg = OrganisationSensorConfig(
        organisation_id=org_id,
        data_source="synthetic",
        enabled_sensors="energy|water|waste",
        sensor_configs=json.dumps(sensor_configs),
        is_active=True,
    )
    db.add(cfg)
    db.commit()
    return org


def test_01_get_full_config_super_admin(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-1")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    resp = client.get(f"/api/v1/super-admin/organisations/{org.id}/full-config", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["organisation_id"] == org.id
    assert data["organisation_name"] == "Apex Research Institute"
    assert data["facility_type"] == "research"
    assert data["facility_name"] == "Apex Research Main Campus"
    assert data["state"] == "Karnataka"
    assert data["district"] == "Bengaluru Urban"
    assert data["city"] == "Bengaluru"
    assert data["address"] == "100 Innovation Way"
    assert "energy" in data["enabled_modules"]
    assert len(data["blocks"]) == 2
    assert "energy" in data["sensor_configs"]
    assert data["sensor_configs"]["energy"]["baseline"] == 450.0


def test_02_update_organisation_details_preserves_untouched(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-2")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    update_payload = {
        "name": "Apex Research Campus Renamed",
        "address": "200 New Discovery Blvd",
        # Keep facility_type, state, district, city as is
        "facility_type": "research",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bengaluru",
        "enabled_modules": ["energy", "water", "waste"],
    }

    resp = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json=update_payload, headers=headers)
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["organisation_name"] == "Apex Research Campus Renamed"
    assert updated["address"] == "200 New Discovery Blvd"
    assert updated["facility_type"] == "research"

    # Verify db directly
    refreshed = db_session.query(Organisation).filter_by(id=org.id).first()
    assert refreshed.name == "Apex Research Campus Renamed"
    assert refreshed.address == "200 New Discovery Blvd"
    assert refreshed.city == "Bengaluru"


def test_03_preserve_existing_blocks(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-3")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    update_payload = {
        "name": org.name,
        "blocks": [
            {"block_id": "BLK-001", "block_name": "Block A - Labs"},
            {"block_id": "BLK-002", "block_name": "Block B - Admin"},
        ],
    }

    resp = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json=update_payload, headers=headers)
    assert resp.status_code == 200, resp.text
    blocks = resp.json()["blocks"]
    assert len(blocks) == 2
    b_ids = [b["block_id"] for b in blocks]
    assert "BLK-001" in b_ids
    assert "BLK-002" in b_ids


def test_04_rename_existing_block(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-4")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    update_payload = {
        "name": org.name,
        "blocks": [
            {"block_id": "BLK-001", "block_name": "Block A - Advanced Nanotech Lab"},
            {"block_id": "BLK-002", "block_name": "Block B - Admin"},
        ],
    }

    resp = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json=update_payload, headers=headers)
    assert resp.status_code == 200
    blocks = resp.json()["blocks"]
    b1 = next(b for b in blocks if b["block_id"] == "BLK-001")
    assert b1["block_name"] == "Block A - Advanced Nanotech Lab"


def test_05_remove_block_without_history_deletes_cleanly(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-5")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    # Only include BLK-001; omit BLK-002 (BLK-002 has no readings or anomalies)
    update_payload = {
        "name": org.name,
        "blocks": [
            {"block_id": "BLK-001", "block_name": "Block A - Labs"},
        ],
    }

    resp = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json=update_payload, headers=headers)
    assert resp.status_code == 200
    blocks = resp.json()["blocks"]
    assert len(blocks) == 1
    assert blocks[0]["block_id"] == "BLK-001"

    # Verify BLK-002 is deleted cleanly from database
    b2 = db_session.query(FacilityBlock).filter_by(organisation_id=org.id, block_id="BLK-002").first()
    assert b2 is None


def test_06_remove_block_with_history_safe_deactivates(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-6")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    # Add historical sensor reading referencing BLK-002
    reading = SensorReading(
        organisation_id=org.id,
        sensor_type="energy",
        value=520.0,
        unit="kWh",
        block_id="BLK-002",
    )
    db_session.add(reading)
    db_session.commit()

    # Now edit org and omit BLK-002 from payload
    update_payload = {
        "name": org.name,
        "blocks": [
            {"block_id": "BLK-001", "block_name": "Block A - Labs"},
        ],
    }

    resp = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json=update_payload, headers=headers)
    assert resp.status_code == 200

    # BLK-002 should NOT be deleted, but soft-deactivated (is_active=False)
    b2 = db_session.query(FacilityBlock).filter_by(organisation_id=org.id, block_id="BLK-002").first()
    assert b2 is not None
    assert b2.is_active is False

    # Historical reading must still exist!
    r = db_session.query(SensorReading).filter_by(organisation_id=org.id, block_id="BLK-002").first()
    assert r is not None
    assert r.value == 520.0


def test_07_threshold_validation_warning_exceeds_critical(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-7")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    # Invalid payload: warning_threshold (35%) > critical_threshold (20%)
    invalid_payload = {
        "name": org.name,
        "sensor_configs": {
            "energy": {
                "baseline": 500.0,
                "warning_threshold": 35.0,
                "critical_threshold": 20.0,  # Invalid: warning > critical
                "unit": "kWh",
            }
        },
    }

    resp = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json=invalid_payload, headers=headers)
    assert resp.status_code == 400
    assert "cannot exceed critical threshold" in resp.json()["detail"]


def test_08_baseline_value_update(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-8")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    update_payload = {
        "name": org.name,
        "sensor_configs": {
            "energy": {"baseline": 520.0, "warning_threshold": 12.0, "critical_threshold": 25.0, "unit": "kWh"},
            "water": {"baseline": 15000.0, "warning_threshold": 18.0, "critical_threshold": 35.0, "unit": "L"},
        },
    }

    resp = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json=update_payload, headers=headers)
    assert resp.status_code == 200
    configs = resp.json()["sensor_configs"]
    assert configs["energy"]["baseline"] == 520.0
    assert configs["water"]["baseline"] == 15000.0


def test_09_enabled_modules_update(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-9")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    update_payload = {
        "name": org.name,
        "enabled_modules": ["energy", "water", "waste", "traffic", "safety"],
    }

    resp = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json=update_payload, headers=headers)
    assert resp.status_code == 200
    modules = resp.json()["enabled_modules"]
    assert "traffic" in modules
    assert "safety" in modules
    assert len(modules) == 5


def test_10_nonexistent_org_returns_404(client: TestClient, db_session: Session, auth_headers):
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")
    resp = client.get("/api/v1/super-admin/organisations/NONEXISTENT-ORG/full-config", headers=headers)
    assert resp.status_code == 404

    resp2 = client.put("/api/v1/super-admin/organisations/NONEXISTENT-ORG/edit-full", json={"name": "X"}, headers=headers)
    assert resp2.status_code == 404


def test_11_rbac_admin_forbidden(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-11")
    admin_headers = auth_headers("admin@greennexa.ai", "ADMIN", organisation_id=org.id)

    resp_get = client.get(f"/api/v1/super-admin/organisations/{org.id}/full-config", headers=admin_headers)
    assert resp_get.status_code == 403

    resp_put = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json={"name": "Hacked"}, headers=admin_headers)
    assert resp_put.status_code == 403


def test_12_historical_data_preserved_after_edit(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-12")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    # Add historical anomaly and recommendation
    anomaly = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.95,
        status="OPEN",
        value=890.0,
        expected_min=300.0,
        expected_max=500.0,
        reason="Grid surge detected",
        block_id="BLK-001",
    )
    db_session.add(anomaly)
    db_session.flush()

    rec = AIRecommendation(
        organisation_id=org.id,
        metric="energy",
        current_value=890.0,
        severity="CRITICAL",
        summary="Check capacitor banks",
        priority="CRITICAL",
        anomaly_id=anomaly.id,
    )
    db_session.add(rec)
    db_session.commit()

    # Perform full configuration edit
    update_payload = {
        "name": "Updated Org Name",
        "state": "Tamil Nadu",
        "city": "Chennai",
    }
    resp = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json=update_payload, headers=headers)
    assert resp.status_code == 200

    # Ensure anomaly and recommendation still exist completely intact
    persisted_anomaly = db_session.query(AnomalyRecord).filter_by(organisation_id=org.id).first()
    assert persisted_anomaly is not None
    assert persisted_anomaly.value == 890.0
    assert persisted_anomaly.reason == "Grid surge detected"

    persisted_rec = db_session.query(AIRecommendation).filter_by(organisation_id=org.id).first()
    assert persisted_rec is not None
    assert persisted_rec.summary == "Check capacitor banks"


def test_13_sensor_config_update(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-13")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    update_payload = {
        "name": org.name,
        "sensor_configs": {
            "energy": {
                "baseline": 600.0,
                "warning_threshold": 10.0,
                "critical_threshold": 25.0,
                "unit": "kWh",
            },
            "water": {
                "baseline": 8000.0,
                "warning_threshold": 15.0,
                "critical_threshold": 30.0,
                "unit": "L",
            },
        },
    }

    resp = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json=update_payload, headers=headers)
    assert resp.status_code == 200
    configs = resp.json()["sensor_configs"]
    assert configs["energy"]["baseline"] == 600.0
    assert configs["energy"]["warning_threshold"] == 10.0


def test_14_add_new_blocks_in_edit(client: TestClient, db_session: Session, auth_headers):
    org = _seed_complete_org(db_session, "ORG-CFG-14")
    headers = auth_headers("super@greennexa.ai", "SUPER_ADMIN")

    update_payload = {
        "name": org.name,
        "blocks": [
            {"block_id": "BLK-001", "block_name": "Block A - Labs"},
            {"block_id": "BLK-002", "block_name": "Block B - Admin"},
            {"block_id": "BLK-003", "block_name": "Block C - Auditorium"},
        ],
    }

    resp = client.put(f"/api/v1/super-admin/organisations/{org.id}/edit-full", json=update_payload, headers=headers)
    assert resp.status_code == 200
    blocks = resp.json()["blocks"]
    assert len(blocks) == 3
    b3 = next(b for b in blocks if b["block_id"] == "BLK-003")
    assert b3["block_name"] == "Block C - Auditorium"
