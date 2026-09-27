"""
Targeted Root-Cause Regression Suite for GreenNexa Bugs:
1. Current Waste vs Anomaly Trigger Value Semantics (Case A)
2. Ward Scope and Isolation
3. Notification Unread Lifecycle (Read != Resolve, Explicit Resolve clears)
4. Organization Isolation
5. 30-Second Simulator Cadence Contract Preservation
6. Core Intelligence Pipeline (Anomaly -> Priority -> Recommendation -> Forecast)
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.db.models import (
    Organisation,
    OrganisationSensorConfig,
    MunicipalityWard,
    SensorReading,
    AnomalyRecord,
    AIRecommendation,
    User,
    _utcnow,
)


@pytest.fixture
def muni_setup(db_session: Session, auth_headers):
    # Create municipality
    muni = db_session.query(Organisation).filter(Organisation.id == "ORG-MUNI-TEST").first()
    if not muni:
        muni = Organisation(
            id="ORG-MUNI-TEST",
            name="Test City Corporation",
            org_type="municipality",
            location="Metropolis",
            is_active=True,
        )
        db_session.add(muni)

    cfg = db_session.query(OrganisationSensorConfig).filter(OrganisationSensorConfig.organisation_id == "ORG-MUNI-TEST").first()
    if not cfg:
        cfg = OrganisationSensorConfig(
            organisation_id="ORG-MUNI-TEST",
            enabled_sensors="waste|energy|water|street_lighting",
            data_source="synthetic",
        )
        db_session.add(cfg)

    ward = db_session.query(MunicipalityWard).filter(MunicipalityWard.id == "WRD-TEST-01").first()
    if not ward:
        ward = MunicipalityWard(
            id="WRD-TEST-01",
            municipality_id="ORG-MUNI-TEST",
            ward_number="101",
            ward_name="Central Ward",
            zone="Zone A",
            is_active=True,
        )
        db_session.add(ward)

    db_session.commit()
    headers = auth_headers("muniadmin@test.com", "ADMIN", "ORG-MUNI-TEST")
    return {"headers": headers, "muni_id": "ORG-MUNI-TEST", "ward_id": "WRD-TEST-01"}


def test_ward_waste_current_vs_trigger_semantics(client: TestClient, db_session: Session, muni_setup):
    """
    BUG 1 VERIFICATION:
    Latest Reading is 45.3% (Current Value).
    Anomaly Event record triggered historically at 100.0% (Anomaly Trigger Value).
    Both values must be returned by the API accurately without forcing equality.
    """
    headers = muni_setup["headers"]
    muni_id = muni_setup["muni_id"]
    ward_id = muni_setup["ward_id"]

    now = _utcnow()

    # 1. Clean previous readings/anomalies for ward
    db_session.query(SensorReading).filter(SensorReading.ward_id == ward_id).delete()
    db_session.query(AnomalyRecord).filter(AnomalyRecord.ward_id == ward_id).delete()
    db_session.commit()

    # 2. Add historical anomaly triggered at 100.0%
    anomaly = AnomalyRecord(
        id="ANOM-WASTE-TEST-01",
        organisation_id=muni_id,
        ward_id=ward_id,
        sensor_type="waste",
        metric="waste",
        value=100.0,  # historical trigger value
        expected_min=20.0,
        expected_max=80.0,
        anomaly_score=3.5,
        severity="CRITICAL",
        status="OPEN",
        timestamp=now - timedelta(minutes=15),
        reason="Severe waste bin overflow detected at 100.00%",
        is_seen=False,
    )
    db_session.add(anomaly)

    # 3. Add latest reading at 45.3%
    reading = SensorReading(
        organisation_id=muni_id,
        ward_id=ward_id,
        sensor_type="waste",
        value=45.3,  # current reading
        unit="%",
        timestamp=now,
        is_anomaly=False,
    )
    db_session.add(reading)
    db_session.commit()

    # Query ward detail endpoint
    res = client.get(f"/api/v1/organisations/{muni_id}/wards/{ward_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Current telemetry value must be 45.3
    waste_metric = data["metrics"]["waste"]
    assert waste_metric["latest_value"] == pytest.approx(45.3, 0.1)

    # Anomaly trigger value must be 100.0
    anomalies = data["anomalies"]
    assert len(anomalies) >= 1
    waste_anom = next(a for a in anomalies if a["id"] == "ANOM-WASTE-TEST-01")
    assert waste_anom["trigger_value"] == pytest.approx(100.0, 0.1)
    assert waste_anom["expected_min"] == 20.0
    assert waste_anom["expected_max"] == 80.0
    assert waste_anom["unit"] == "%"
    assert waste_anom["severity"] == "CRITICAL"


def test_ward_scope_and_isolation(client: TestClient, muni_setup):
    """
    BUG 1 & MUNICIPALITY SCOPE VERIFICATION:
    Ward detail only returns data for the requested ward and requested organisation.
    """
    headers = muni_setup["headers"]
    muni_id = muni_setup["muni_id"]
    ward_id = muni_setup["ward_id"]

    res = client.get(f"/api/v1/organisations/{muni_id}/wards/{ward_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["ward"]["id"] == ward_id
    assert data["ward"]["municipality_id"] == muni_id

    res_404 = client.get(f"/api/v1/organisations/{muni_id}/wards/WRD-NONEXISTENT", headers=headers)
    assert res_404.status_code == 404


def test_red_dot_unread_persistence_and_read_vs_resolve(client: TestClient, db_session: Session, muni_setup):
    """
    BUG 4 VERIFICATION:
    1. Unread anomaly produces unread=True.
    2. Marking as read marks is_seen=True, but status remains OPEN (Read != Resolve).
    3. Explicit resolution (PATCH status=RESOLVED) resolves the anomaly and clears active state.
    """
    headers = muni_setup["headers"]
    muni_id = muni_setup["muni_id"]
    ward_id = muni_setup["ward_id"]

    db_session.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == muni_id).delete()
    db_session.commit()

    now = _utcnow()
    anomaly = AnomalyRecord(
        id="ANOM-LIFECYCLE-01",
        organisation_id=muni_id,
        ward_id=ward_id,
        sensor_type="waste",
        metric="waste",
        value=98.5,
        expected_min=10.0,
        expected_max=75.0,
        anomaly_score=3.2,
        severity="HIGH",
        status="OPEN",
        timestamp=now,
        reason="High waste level",
        is_seen=False,
    )
    db_session.add(anomaly)
    db_session.commit()

    # 1. Check unread notifications endpoint
    res = client.get(f"/api/v1/notifications/unread?organisation_id={muni_id}", headers=headers)
    assert res.status_code == 200
    notif = res.json()
    assert notif["has_unread"] is True
    assert notif["modules"]["waste"] is True
    assert "ANOM-LIFECYCLE-01" in notif["unseen_anomaly_ids"]

    # Unrelated modules MUST NOT receive red dot
    assert notif["modules"].get("energy", False) is False
    assert notif["modules"].get("water", False) is False
    assert notif["modules"].get("traffic", False) is False

    # 2. Mark as read (Read action)
    mark_res = client.post(
        "/api/v1/notifications/mark-read",
        json={"anomaly_ids": ["ANOM-LIFECYCLE-01"], "organisation_id": muni_id},
        headers=headers,
    )
    assert mark_res.status_code == 200

    # Verify: is_seen is True, but status is STILL OPEN! Read != Resolve
    db_session.refresh(anomaly)
    assert anomaly.is_seen is True
    assert anomaly.status == "OPEN"

    # 3. Now explicitly resolve anomaly
    resolve_res = client.patch(
        "/api/v1/anomalies/ANOM-LIFECYCLE-01",
        json={"status": "RESOLVED"},
        headers=headers,
    )
    assert resolve_res.status_code == 200
    db_session.refresh(anomaly)
    assert anomaly.status == "RESOLVED"

    # Check unread notifications endpoint: should now have no unread
    res_after = client.get(f"/api/v1/notifications/unread?organisation_id={muni_id}", headers=headers)
    assert res_after.status_code == 200
    notif_after = res_after.json()
    assert notif_after["has_unread"] is False
    assert notif_after["modules"].get("waste", False) is False


def test_organisation_isolation(client: TestClient, db_session: Session, muni_setup):
    """
    ORGANISATION ISOLATION VERIFICATION:
    Anomalies and notifications in Org A do not leak into Org B.
    """
    headers = muni_setup["headers"]
    muni_id = muni_setup["muni_id"]

    org_b = db_session.query(Organisation).filter(Organisation.id == "ORG-ISOLATION-B").first()
    if not org_b:
        org_b = Organisation(
            id="ORG-ISOLATION-B",
            name="Isolated Org B",
            org_type="college",
            location="Campus B",
            is_active=True,
        )
        db_session.add(org_b)
        db_session.commit()

    db_session.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == "ORG-ISOLATION-B").delete()
    now = _utcnow()
    anom_b = AnomalyRecord(
        id="ANOM-ORG-B-01",
        organisation_id="ORG-ISOLATION-B",
        sensor_type="energy",
        metric="energy",
        value=350.0,
        expected_min=50.0,
        expected_max=200.0,
        anomaly_score=4.0,
        severity="CRITICAL",
        status="OPEN",
        timestamp=now,
        reason="Overconsumption in Org B",
        is_seen=False,
    )
    db_session.add(anom_b)
    db_session.commit()

    res_muni = client.get(f"/api/v1/notifications/unread?organisation_id={muni_id}", headers=headers)
    assert res_muni.status_code == 200
    data_muni = res_muni.json()
    assert "ANOM-ORG-B-01" not in data_muni["unseen_anomaly_ids"]
    assert data_muni["modules"].get("energy", False) is False


def test_core_intelligence_pipeline(client: TestClient, db_session: Session, muni_setup):
    """
    CORE INTELLIGENCE ENGINE VERIFICATION:
    Anomaly -> Priority -> Recommendation pipeline remains active and functional.
    """
    headers = muni_setup["headers"]
    muni_id = muni_setup["muni_id"]
    ward_id = muni_setup["ward_id"]

    db_session.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == muni_id).delete()
    now = _utcnow()
    for idx in range(1, 4):
        anomaly = AnomalyRecord(
            id=f"ANOM-INTELLIGENCE-0{idx}",
            organisation_id=muni_id,
            ward_id=ward_id,
            sensor_type="waste",
            metric="waste",
            value=90.0 + idx * 2.0,
            expected_min=20.0,
            expected_max=80.0,
            anomaly_score=3.5,
            severity="CRITICAL",
            status="OPEN",
            timestamp=now,
            reason=f"Waste bin fill level is at critical {90.0 + idx * 2.0}%",
        )
        db_session.add(anomaly)

    rec = AIRecommendation(
        id="REC-INTELLIGENCE-01",
        anomaly_id="ANOM-INTELLIGENCE-01",
        organisation_id=muni_id,
        ward_id=ward_id,
        metric="waste",
        current_value=92.0,
        expected_range_min=20.0,
        expected_range_max=80.0,
        severity="CRITICAL",
        priority="CRITICAL",
        summary="Immediate Waste Compaction & Collection Route Dispatch: Waste bin fill level is at critical 92.0% exceeding baseline.",
        recommended_actions="Dispatch secondary collection vehicle to Ward 101.|Alert municipal sanitation dispatch.",
        status="ACTIVE",
    )
    db_session.add(rec)
    db_session.commit()

    p_res = client.get(f"/api/v1/anomalies/{muni_id}/priority", headers=headers)
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert p_data["is_active"] is True
    assert len(p_data["items"]) >= 1

    r_res = client.get(f"/api/v1/recommendations?organisation_id={muni_id}&status=OPEN", headers=headers)
    assert r_res.status_code == 200
    r_data = r_res.json()
    items = r_data if isinstance(r_data, list) else r_data.get("items", [])
    assert len(items) >= 1
    assert any(item.get("sensor_type") == "waste" or item.get("metric") == "waste" for item in items)


def test_30_second_demo_contract():
    """
    30-SECOND DEMO CONTRACT:
    The simulation cadence in synthetic_simulator is 30 seconds, maximum 1 anomaly per cycle.
    """
    from app.services.synthetic_simulator import simulator_instance, SyntheticDataSimulator
    sim = SyntheticDataSimulator()
    assert sim.interval_seconds == 30, "Simulation interval MUST remain exactly 30 seconds"
    assert simulator_instance.interval_seconds == 30, "Shared simulator instance MUST have interval of 30 seconds"
