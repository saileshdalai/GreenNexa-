"""
Tests for Bug 2: Resolve/Dismiss Must Immediately Update Block-Wise Anomaly + Recommendation Sections.

Verifies:
1. Anomaly created for Block A with linked recommendation shows up in block detail endpoint.
2. Active anomaly count is 1, active recommendation count is 1.
3. Resolving the anomaly updates AnomalyRecord status to RESOLVED and AIRecommendation status to RESOLVED.
4. Calling block detail endpoint for Block A returns active_anomalies_count = 0 and active_recommendations_count = 0.
5. Resolved anomaly remains in block anomalies list with status='RESOLVED' for historical views.
6. Resolved recommendation remains in block recommendations list with status='RESOLVED'.
7. Block B active anomaly is untouched when Block A is resolved (strict block isolation).
8. Dismissing an anomaly updates both anomaly and recommendation to DISMISSED and resets active counts.
"""

import json
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    Organisation,
    OrganisationSensorConfig,
    User,
)


@pytest.fixture
def block_sync_setup(db_session: Session):
    """Setup organisation with 2 blocks and admin user."""
    org = Organisation(
        id="ORG-SYNC-TEST",
        name="Block Sync Academy",
        org_type="college",
        facility_name="Sync Campus",
        is_active=True,
    )
    db_session.add(org)

    b_a = FacilityBlock(
        organisation_id="ORG-SYNC-TEST",
        block_id="BLK-A",
        block_name="Academic Block",
        is_active=True,
    )
    b_b = FacilityBlock(
        organisation_id="ORG-SYNC-TEST",
        block_id="BLK-B",
        block_name="Library Block",
        is_active=True,
    )
    db_session.add_all([b_a, b_b])

    cfg = OrganisationSensorConfig(
        organisation_id="ORG-SYNC-TEST",
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        enabled_sensors="energy|water",
        sensor_configs=json.dumps({
            "energy": {"baseline": 100.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "kWh"},
            "water": {"baseline": 50.0, "warning_threshold": 10.0, "critical_threshold": 25.0, "unit": "L"},
        }),
        is_active=True,
    )
    db_session.add(cfg)

    admin = User(
        id="admin_sync_user",
        email="admin_sync@syncacademy.edu",
        hashed_password=hash_password("Pass123!"),
        full_name="Admin Sync",
        role=User.ROLE_ADMIN,
        organisation_id="ORG-SYNC-TEST",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    return {
        "org_id": "ORG-SYNC-TEST",
        "admin": admin,
        "block_a": b_a,
        "block_b": b_b,
    }


def test_01_resolve_anomaly_immediately_updates_block_detail(client: TestClient, db_session: Session, block_sync_setup):
    """Resolve anomaly updates backend lifecycle and immediately zeroes active counts on block detail."""
    org_id = block_sync_setup["org_id"]
    admin = block_sync_setup["admin"]
    token = create_access_token({"sub": admin.id})
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Active Anomaly and Linked Active Recommendation for Block A
    now = datetime.now(timezone.utc)
    anom_a = AnomalyRecord(
        id="anom-blk-a-1",
        organisation_id=org_id,
        block_id="BLK-A",
        facility_id="Academic Block",
        metric="energy",
        sensor_type="energy",
        value=145.0,
        expected_min=85.0,
        expected_max=115.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        reason="Energy surge detected in Academic Block",
        timestamp=now,
        created_at=now,
    )
    db_session.add(anom_a)
    db_session.flush()

    rec_a = AIRecommendation(
        id="rec-blk-a-1",
        organisation_id=org_id,
        block_id="BLK-A",
        facility_id="Academic Block",
        anomaly_id=anom_a.id,
        metric="energy",
        current_value=145.0,
        severity="HIGH",
        priority="HIGH",
        summary="Reduce Academic Block HVAC during non-operational hours",
        recommended_actions="1. Check HVAC thermostat; 2. Inspect lighting controls",
        status=AIRecommendation.STATUS_ACTIVE,
        created_at=now,
    )
    db_session.add(rec_a)

    # Also create an active anomaly in Block B to verify isolation
    anom_b = AnomalyRecord(
        id="anom-blk-b-1",
        organisation_id=org_id,
        block_id="BLK-B",
        facility_id="Library Block",
        metric="energy",
        sensor_type="energy",
        value=140.0,
        expected_min=85.0,
        expected_max=115.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        reason="Energy surge in Library Block",
        timestamp=now,
        created_at=now,
    )
    rec_b = AIRecommendation(
        id="rec-blk-b-1",
        organisation_id=org_id,
        block_id="BLK-B",
        facility_id="Library Block",
        anomaly_id=anom_b.id,
        metric="energy",
        current_value=140.0,
        severity="HIGH",
        priority="HIGH",
        summary="Inspect Library Block circulation pumps",
        status=AIRecommendation.STATUS_ACTIVE,
        created_at=now,
    )
    db_session.add_all([anom_b, rec_b])
    db_session.commit()

    # 2. Before Resolve: Check Block A detail endpoint
    res_before = client.get(f"/api/v1/dashboard/{org_id}/modules/energy/block/BLK-A", headers=auth_headers)
    assert res_before.status_code == 200
    data_before = res_before.json()
    assert data_before["active_anomalies_count"] == 1
    assert data_before["active_recommendations_count"] == 1
    assert len(data_before["anomalies"]) == 1
    assert data_before["anomalies"][0]["status"] == "OPEN"
    assert len(data_before["recommendations"]) == 1
    assert data_before["recommendations"][0]["status"] == "ACTIVE"

    # 3. Resolve Anomaly A
    res_resolve = client.post(f"/api/v1/anomalies/{anom_a.id}/resolve", headers=auth_headers)
    assert res_resolve.status_code == 200

    # Verify DB status
    db_session.expire_all()
    anom_a_db = db_session.query(AnomalyRecord).filter_by(id=anom_a.id).first()
    assert anom_a_db.status == AnomalyRecord.STATUS_RESOLVED
    rec_a_db = db_session.query(AIRecommendation).filter_by(id=rec_a.id).first()
    assert rec_a_db.status == AIRecommendation.STATUS_RESOLVED

    # 4. After Resolve: Check Block A detail endpoint
    res_after = client.get(f"/api/v1/dashboard/{org_id}/modules/energy/block/BLK-A", headers=auth_headers)
    assert res_after.status_code == 200
    data_after = res_after.json()
    # Active counts MUST BE 0!
    assert data_after["active_anomalies_count"] == 0
    assert data_after["active_recommendations_count"] == 0
    # Historical records are PRESERVED with status RESOLVED
    assert len(data_after["anomalies"]) == 1
    assert data_after["anomalies"][0]["status"] == "RESOLVED"
    assert len(data_after["recommendations"]) == 1
    assert data_after["recommendations"][0]["status"] == "RESOLVED"

    # 5. Check Block B: MUST REMAIN UNTOUCHED (Strict Block Isolation)
    res_b = client.get(f"/api/v1/dashboard/{org_id}/modules/energy/block/BLK-B", headers=auth_headers)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["active_anomalies_count"] == 1
    assert data_b["active_recommendations_count"] == 1
    assert data_b["anomalies"][0]["status"] == "OPEN"
    assert data_b["recommendations"][0]["status"] == "ACTIVE"


def test_02_dismiss_anomaly_updates_block_detail_similarly(client: TestClient, db_session: Session, block_sync_setup):
    """Dismiss anomaly updates status to DISMISSED and zeroes active counts on block detail."""
    org_id = block_sync_setup["org_id"]
    admin = block_sync_setup["admin"]
    token = create_access_token({"sub": admin.id})
    auth_headers = {"Authorization": f"Bearer {token}"}

    now = datetime.now(timezone.utc)
    anom = AnomalyRecord(
        id="anom-blk-a-dismiss",
        organisation_id=org_id,
        block_id="BLK-A",
        facility_id="Academic Block",
        metric="energy",
        sensor_type="energy",
        value=142.0,
        expected_min=85.0,
        expected_max=115.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        reason="Spike test",
        timestamp=now,
        created_at=now,
    )
    db_session.add(anom)
    db_session.flush()

    rec = AIRecommendation(
        id="rec-blk-a-dismiss",
        organisation_id=org_id,
        block_id="BLK-A",
        facility_id="Academic Block",
        anomaly_id=anom.id,
        metric="energy",
        current_value=142.0,
        severity="HIGH",
        priority="HIGH",
        summary="Test dismiss recommendation",
        status=AIRecommendation.STATUS_ACTIVE,
        created_at=now,
    )
    db_session.add(rec)
    db_session.commit()

    # Dismiss anomaly
    res_dismiss = client.post(f"/api/v1/anomalies/{anom.id}/dismiss", headers=auth_headers)
    assert res_dismiss.status_code == 200

    # Check Block A detail endpoint
    res = client.get(f"/api/v1/dashboard/{org_id}/modules/energy/block/BLK-A", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["active_anomalies_count"] == 0
    assert data["active_recommendations_count"] == 0
    # Historical record has status DISMISSED
    matched_anom = next((a for a in data["anomalies"] if a["id"] == anom.id), None)
    assert matched_anom is not None
    assert matched_anom["status"] == "DISMISSED"
    matched_rec = next((r for r in data["recommendations"] if r["id"] == rec.id), None)
    assert matched_rec is not None
    assert matched_rec["status"] == "DISMISSED"
