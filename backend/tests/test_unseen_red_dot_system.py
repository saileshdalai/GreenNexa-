"""
Tests for Admin New/Unseen Change Red-Dot Notification System.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import (
    Organisation,
    FacilityBlock,
    AnomalyRecord,
    SensorReading,
    EventReadState,
    User,
)


def _seed_org_with_blocks(db: Session, org_id: str = "ORG-NOTIF-A") -> Organisation:
    org = Organisation(
        id=org_id,
        name=f"Org {org_id}",
        org_type="factory",
        location="Zone 1",
    )
    db.add(org)
    db.flush()

    b1 = FacilityBlock(
        organisation_id=org_id,
        block_id="BLK-001",
        block_name="Block 1 - Production",
        is_active=True,
    )
    b2 = FacilityBlock(
        organisation_id=org_id,
        block_id="BLK-002",
        block_name="Block 2 - Warehouse",
        is_active=True,
    )
    db.add_all([b1, b2])
    db.commit()
    return org


def test_15_anomaly_defaults_to_unseen(db_session: Session):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-15")
    anomaly = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.9,
        status=AnomalyRecord.STATUS_OPEN,
        value=750.0,
        block_id="BLK-001",
    )
    db_session.add(anomaly)
    db_session.commit()
    db_session.refresh(anomaly)

    assert anomaly.is_seen is False
    assert anomaly.seen_at is None
    assert anomaly.seen_by is None


def test_16_unread_notifications_endpoint(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-16")
    admin_headers = auth_headers("admin16@test.com", "ADMIN", organisation_id=org.id)

    # Initially no anomalies -> unread = 0
    resp0 = client.get("/api/v1/notifications/unread", headers=admin_headers)
    assert resp0.status_code == 200
    assert resp0.json()["total_unread"] == 0
    assert resp0.json()["has_unread"] is False

    # Create unread anomaly
    anomaly = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="WARNING",
        anomaly_score=0.85,
        status=AnomalyRecord.STATUS_OPEN,
        value=610.0,
        block_id="BLK-001",
    )
    db_session.add(anomaly)
    db_session.commit()

    resp1 = client.get("/api/v1/notifications/unread", headers=admin_headers)
    assert resp1.status_code == 200
    data = resp1.json()
    assert data["total_unread"] == 1
    assert data["has_unread"] is True


def test_17_unread_modules_includes_metric(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-17")
    admin_headers = auth_headers("admin17@test.com", "ADMIN", organisation_id=org.id)

    anomaly = AnomalyRecord(
        organisation_id=org.id,
        metric="water",
        severity="CRITICAL",
        anomaly_score=0.95,
        status=AnomalyRecord.STATUS_OPEN,
        value=25000.0,
        block_id="BLK-002",
    )
    db_session.add(anomaly)
    db_session.commit()

    resp = client.get("/api/v1/notifications/unread", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["modules"]["water"] is True
    assert data["modules"].get("energy", False) is False


def test_18_unread_blocks_mapping(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-18")
    admin_headers = auth_headers("admin18@test.com", "ADMIN", organisation_id=org.id)

    anomaly = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.92,
        status=AnomalyRecord.STATUS_OPEN,
        value=800.0,
        block_id="BLK-001",
    )
    db_session.add(anomaly)
    db_session.commit()

    resp = client.get("/api/v1/notifications/unread", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["blocks"].get("BLK-001") is True
    assert data["module_blocks"]["energy"].get("BLK-001") is True


def test_19_mark_block_read(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-19")
    admin_headers = auth_headers("admin19@test.com", "ADMIN", organisation_id=org.id)

    anomaly = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.9,
        status=AnomalyRecord.STATUS_OPEN,
        value=800.0,
        block_id="BLK-001",
    )
    db_session.add(anomaly)
    db_session.commit()

    # Mark block read
    mark_resp = client.post(
        "/api/v1/notifications/mark-read",
        json={"metric": "energy", "block_id": "BLK-001"},
        headers=admin_headers,
    )
    assert mark_resp.status_code == 200
    assert mark_resp.json()["marked_count"] >= 1


def test_20_unread_blocks_cleared_after_mark_read(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-20")
    admin_headers = auth_headers("admin20@test.com", "ADMIN", organisation_id=org.id)

    anomaly = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.9,
        status=AnomalyRecord.STATUS_OPEN,
        value=800.0,
        block_id="BLK-001",
    )
    db_session.add(anomaly)
    db_session.commit()

    client.post(
        "/api/v1/notifications/mark-read",
        json={"metric": "energy", "block_id": "BLK-001"},
        headers=admin_headers,
    )

    resp = client.get("/api/v1/notifications/unread", headers=admin_headers)
    data = resp.json()
    assert data["total_unread"] == 0
    assert data["has_unread"] is False
    assert data["modules"].get("energy", False) is False


def test_21_independent_block_states(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-21")
    admin_headers = auth_headers("admin21@test.com", "ADMIN", organisation_id=org.id)

    # Anomaly in Block 1
    a1 = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="WARNING",
        anomaly_score=0.8,
        status=AnomalyRecord.STATUS_OPEN,
        value=620.0,
        block_id="BLK-001",
    )
    # Anomaly in Block 2
    a2 = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.95,
        status=AnomalyRecord.STATUS_OPEN,
        value=900.0,
        block_id="BLK-002",
    )
    db_session.add_all([a1, a2])
    db_session.commit()

    # Initial check: 2 unread, energy in modules, BLK-001 and BLK-002 both in blocks
    resp0 = client.get("/api/v1/notifications/unread", headers=admin_headers)
    data0 = resp0.json()
    assert data0["total_unread"] == 2
    assert data0["blocks"].get("BLK-001") is True
    assert data0["blocks"].get("BLK-002") is True

    # Mark only BLK-001 as read
    client.post(
        "/api/v1/notifications/mark-read",
        json={"metric": "energy", "block_id": "BLK-001"},
        headers=admin_headers,
    )

    # After BLK-001 read: BLK-001 is cleared, BLK-002 remains unread, Energy module STILL unread
    resp1 = client.get("/api/v1/notifications/unread", headers=admin_headers)
    data1 = resp1.json()
    assert data1["total_unread"] == 1
    assert data1["modules"]["energy"] is True
    assert data1["blocks"].get("BLK-001", False) is False
    assert data1["blocks"].get("BLK-002") is True


def test_22_module_cleared_when_all_blocks_read(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-22")
    admin_headers = auth_headers("admin22@test.com", "ADMIN", organisation_id=org.id)

    a1 = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="WARNING",
        anomaly_score=0.8,
        status=AnomalyRecord.STATUS_OPEN,
        value=620.0,
        block_id="BLK-001",
    )
    db_session.add(a1)
    db_session.commit()

    client.post(
        "/api/v1/notifications/mark-read",
        json={"metric": "energy", "block_id": "BLK-001"},
        headers=admin_headers,
    )

    resp = client.get("/api/v1/notifications/unread", headers=admin_headers)
    assert resp.json()["modules"].get("energy", False) is False
    assert resp.json()["has_unread"] is False


def test_23_direct_anomaly_read_endpoint(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-23")
    admin_headers = auth_headers("admin23@test.com", "ADMIN", organisation_id=org.id)

    anomaly = AnomalyRecord(
        organisation_id=org.id,
        metric="waste",
        severity="WARNING",
        anomaly_score=0.75,
        status=AnomalyRecord.STATUS_OPEN,
        value=95.0,
        block_id="BLK-001",
    )
    db_session.add(anomaly)
    db_session.commit()
    db_session.refresh(anomaly)

    resp_read = client.post(f"/api/v1/notifications/read/{anomaly.id}", headers=admin_headers)
    assert resp_read.status_code == 200

    # Verify db status on anomaly
    db_session.refresh(anomaly)
    assert anomaly.is_seen is True

    # Check unread endpoint
    resp = client.get("/api/v1/notifications/unread", headers=admin_headers)
    assert resp.json()["total_unread"] == 0


def test_24_lifecycle_operations_preserve_read_state(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-24")
    admin_headers = auth_headers("admin24@test.com", "ADMIN", organisation_id=org.id)

    anomaly = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.9,
        status=AnomalyRecord.STATUS_OPEN,
        value=850.0,
        block_id="BLK-001",
    )
    db_session.add(anomaly)
    db_session.commit()
    db_session.refresh(anomaly)

    # Mark as read first
    client.post(f"/api/v1/notifications/read/{anomaly.id}", headers=admin_headers)

    # Now transition lifecycle to RESOLVED
    resolve_resp = client.post(
        f"/api/v1/anomalies/{anomaly.id}/resolve",
        headers=admin_headers,
    )
    assert resolve_resp.status_code == 200

    # Verify anomaly still exists in database and is_seen is still True
    db_session.refresh(anomaly)
    assert anomaly.status == "RESOLVED"
    assert anomaly.is_seen is True


def test_25_multi_tenant_isolation(client: TestClient, db_session: Session, auth_headers):
    org_a = _seed_org_with_blocks(db_session, "ORG-NOTIF-25A")
    org_b = _seed_org_with_blocks(db_session, "ORG-NOTIF-25B")

    admin_a_headers = auth_headers("admin25a@test.com", "ADMIN", organisation_id=org_a.id)
    admin_b_headers = auth_headers("admin25b@test.com", "ADMIN", organisation_id=org_b.id)

    # Anomaly created only in Org A
    anomaly_a = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.9,
        status=AnomalyRecord.STATUS_OPEN,
        value=990.0,
        block_id="BLK-001",
    )
    db_session.add(anomaly_a)
    db_session.commit()

    # Admin A sees 1 unread notification
    resp_a = client.get("/api/v1/notifications/unread", headers=admin_a_headers)
    assert resp_a.json()["total_unread"] == 1
    assert resp_a.json()["has_unread"] is True

    # Admin B sees 0 unread notifications (Strict Tenant Isolation!)
    resp_b = client.get("/api/v1/notifications/unread", headers=admin_b_headers)
    assert resp_b.json()["total_unread"] == 0
    assert resp_b.json()["has_unread"] is False
    assert all(not v for v in resp_b.json()["modules"].values())


def test_26_tenant_cannot_mark_other_org_notifications(client: TestClient, db_session: Session, auth_headers):
    org_a = _seed_org_with_blocks(db_session, "ORG-NOTIF-26A")
    org_b = _seed_org_with_blocks(db_session, "ORG-NOTIF-26B")

    admin_b_headers = auth_headers("admin26b@test.com", "ADMIN", organisation_id=org_b.id)

    anomaly_a = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.9,
        status=AnomalyRecord.STATUS_OPEN,
        value=990.0,
        block_id="BLK-001",
    )
    db_session.add(anomaly_a)
    db_session.commit()
    db_session.refresh(anomaly_a)

    # Admin B attempts to mark anomaly from Org A as read
    resp = client.post(f"/api/v1/notifications/read/{anomaly_a.id}", headers=admin_b_headers)
    assert resp.status_code == 404  # Not found within Org B's scope


def test_27_new_anomaly_triggers_new_red_dot(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-27")
    admin_headers = auth_headers("admin27@test.com", "ADMIN", organisation_id=org.id)

    # 1. First anomaly
    a1 = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="WARNING",
        anomaly_score=0.8,
        status=AnomalyRecord.STATUS_OPEN,
        value=650.0,
        block_id="BLK-001",
    )
    db_session.add(a1)
    db_session.commit()

    # Mark all read
    client.post("/api/v1/notifications/mark-read", json={"all_unseen": True}, headers=admin_headers)
    assert client.get("/api/v1/notifications/unread", headers=admin_headers).json()["has_unread"] is False

    # 2. Later, a new anomaly occurs
    a2 = AnomalyRecord(
        organisation_id=org.id,
        metric="water",
        severity="CRITICAL",
        anomaly_score=0.99,
        status=AnomalyRecord.STATUS_OPEN,
        value=30000.0,
        block_id="BLK-002",
    )
    db_session.add(a2)
    db_session.commit()

    # Red dot appears again!
    resp_new = client.get("/api/v1/notifications/unread", headers=admin_headers)
    assert resp_new.json()["has_unread"] is True
    assert resp_new.json()["total_unread"] == 1
    assert resp_new.json()["modules"]["water"] is True


def test_28_org_admin_clear_data_resets_notifications(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-28")
    admin_headers = auth_headers("admin28@test.com", "ADMIN", organisation_id=org.id)

    anomaly = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.9,
        status=AnomalyRecord.STATUS_OPEN,
        value=850.0,
        block_id="BLK-001",
    )
    db_session.add(anomaly)
    db_session.commit()

    assert client.get("/api/v1/notifications/unread", headers=admin_headers).json()["has_unread"] is True

    # Clear operational data
    clear_resp = client.post(f"/api/v1/organisations/{org.id}/clear-data", headers=admin_headers)
    assert clear_resp.status_code == 200

    # Unread notifications should be 0
    resp_after = client.get("/api/v1/notifications/unread", headers=admin_headers)
    assert resp_after.json()["has_unread"] is False
    assert resp_after.json()["total_unread"] == 0


def test_29_super_admin_clear_all_data_resets_all_notifications(client: TestClient, db_session: Session, auth_headers):
    org_a = _seed_org_with_blocks(db_session, "ORG-NOTIF-29A")
    org_b = _seed_org_with_blocks(db_session, "ORG-NOTIF-29B")

    admin_a_headers = auth_headers("admin29a@test.com", "ADMIN", organisation_id=org_a.id)
    super_headers = auth_headers("superadmin@greennexa.com", "SUPER_ADMIN")

    a1 = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.9,
        status=AnomalyRecord.STATUS_OPEN,
        value=850.0,
        block_id="BLK-001",
    )
    db_session.add(a1)
    db_session.commit()

    assert client.get("/api/v1/notifications/unread", headers=admin_a_headers).json()["has_unread"] is True

    # Super Admin clear all data
    conf_pwd = os.getenv("GREENNEXA_DESTRUCTIVE_ACTION_PASSWORD", "test_destructive_action_password")
    clear_resp = client.post("/api/v1/super-admin/clear-all-data", json={"confirmation_password": conf_pwd, "confirmation": "CLEAR ALL DATA"}, headers=super_headers)
    assert clear_resp.status_code == 200

    # Unread notifications, anomalies, and read states must be completely reset
    assert db_session.query(EventReadState).count() == 0
    assert db_session.query(AnomalyRecord).count() == 0

    # Super Admin unread notifications should be 0
    resp_super = client.get("/api/v1/notifications/unread", headers=super_headers)
    assert resp_super.json()["has_unread"] is False
    assert resp_super.json()["total_unread"] == 0


def test_30_telemetry_alone_does_not_trigger_red_dot(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-30")
    admin_headers = auth_headers("admin30@test.com", "ADMIN", organisation_id=org.id)

    # Insert normal telemetry readings
    for i in range(5):
        r = SensorReading(
            organisation_id=org.id,
            sensor_type="energy",
            value=350.0 + i,
            unit="kWh",
            block_id="BLK-001",
        )
        db_session.add(r)
    db_session.commit()

    # Normal 30s telemetry updates must NOT trigger red dots
    resp = client.get("/api/v1/notifications/unread", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total_unread"] == 0
    assert resp.json()["has_unread"] is False


def test_31_mark_all_read(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-31")
    admin_headers = auth_headers("admin31@test.com", "ADMIN", organisation_id=org.id)

    a1 = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.9,
        status=AnomalyRecord.STATUS_OPEN,
        value=850.0,
        block_id="BLK-001",
    )
    a2 = AnomalyRecord(
        organisation_id=org.id,
        metric="water",
        severity="WARNING",
        anomaly_score=0.85,
        status=AnomalyRecord.STATUS_OPEN,
        value=12000.0,
        block_id="BLK-002",
    )
    db_session.add_all([a1, a2])
    db_session.commit()

    assert client.get("/api/v1/notifications/unread", headers=admin_headers).json()["total_unread"] == 2

    # Mark all read
    resp = client.post("/api/v1/notifications/mark-read", json={"all_unseen": True}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["marked_count"] >= 2

    assert client.get("/api/v1/notifications/unread", headers=admin_headers).json()["total_unread"] == 0


def test_32_mark_module_only_read(client: TestClient, db_session: Session, auth_headers):
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-32")
    admin_headers = auth_headers("admin32@test.com", "ADMIN", organisation_id=org.id)

    # 2 energy anomalies in different blocks
    a1 = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="CRITICAL",
        anomaly_score=0.9,
        status=AnomalyRecord.STATUS_OPEN,
        value=850.0,
        block_id="BLK-001",
    )
    a2 = AnomalyRecord(
        organisation_id=org.id,
        metric="energy",
        severity="WARNING",
        anomaly_score=0.8,
        status=AnomalyRecord.STATUS_OPEN,
        value=650.0,
        block_id="BLK-002",
    )
    # 1 water anomaly
    a3 = AnomalyRecord(
        organisation_id=org.id,
        metric="water",
        severity="CRITICAL",
        anomaly_score=0.9,
        status=AnomalyRecord.STATUS_OPEN,
        value=20000.0,
        block_id="BLK-002",
    )
    db_session.add_all([a1, a2, a3])
    db_session.commit()

    # Mark only "energy" module read (no block_id specified)
    resp = client.post("/api/v1/notifications/mark-read", json={"metric": "energy"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["marked_count"] == 2

    # Verify energy is cleared, water remains unread
    unread_resp = client.get("/api/v1/notifications/unread", headers=admin_headers)
    data = unread_resp.json()
    assert data["total_unread"] == 1
    assert data["modules"].get("energy", False) is False
    assert data["modules"]["water"] is True


def test_33_equipment_asset_anomaly_lights_assets_module_red_dot(client: TestClient, db_session: Session, auth_headers):
    """The catalog sensor is `equipment_asset` but the nav module id is `assets`.

    Without canonicalisation the anomaly lit a key no UI reads, so the Municipal
    Assets red dot never appeared. Marking the `assets` module read must also clear
    the `equipment_asset` anomaly (the alias has to work in both directions).
    """
    org = _seed_org_with_blocks(db_session, "ORG-NOTIF-33")
    admin_headers = auth_headers("admin33@test.com", "ADMIN", organisation_id=org.id)

    db_session.add(
        AnomalyRecord(
            organisation_id=org.id,
            metric="equipment_asset",
            sensor_type="equipment_asset",
            severity="HIGH",
            anomaly_score=0.85,
            status=AnomalyRecord.STATUS_OPEN,
            value=62.0,
        )
    )
    db_session.commit()

    data = client.get("/api/v1/notifications/unread", headers=admin_headers).json()
    assert data["modules"].get("assets") is True, "assets module red dot must light"
    assert data["modules"].get("equipment_asset") is True, "raw sensor key must also be exposed"

    # Reading the `assets` module clears the underlying equipment_asset anomaly.
    resp = client.post("/api/v1/notifications/mark-read", json={"metric": "assets"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["marked_count"] == 1

    after = client.get("/api/v1/notifications/unread", headers=admin_headers).json()
    assert after["total_unread"] == 0
    assert after["modules"].get("assets") is False
