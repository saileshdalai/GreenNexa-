"""
GreenNexa — Regression Suite: Municipality Wards, Civic Sensors & Correct Scoping.

Covers Fix 2 (wards never FacilityBlocks), Fix 3/5 (ward list/detail never
leak facility blocks), Fix 6/7 (civic sensor catalog), Fix 8/9/16/19
(aggregation scoping for new civic modules), Fix 13 (create-full setup modes).
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.core.sensor_catalog import get_recommended_sensors_for_type
from app.db.models import (
    Organisation,
    OrganisationSensorConfig,
    FacilityBlock,
    MunicipalityWard,
    SensorReading,
    AnomalyRecord,
    User,
)


def _seed_municipality(db_session: Session):
    """Seed a municipality org + admin + config, return ids and headers."""
    muni = Organisation(
        id="ORG-CIVIC-MUNI",
        name="Civic NAC",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Municipality / Municipal Campus",
        location="Bhubaneswar",
        is_active=True,
    )
    db_session.add(muni)
    admin = User(
        id="ADMIN-CIVIC-01",
        organisation_id=muni.id,
        email="civic_admin@nac.gov.in",
        hashed_password=security.hash_password("civicPass123"),
        full_name="NAC Admin",
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    cfg = OrganisationSensorConfig(
        organisation_id=muni.id,
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        enabled_sensors="energy|street_lighting|sewage|roads|parks|water",
        is_active=True,
    )
    db_session.add(cfg)
    db_session.commit()
    headers = {"Authorization": f"Bearer {security.create_access_token(data={'sub': admin.id, 'role': admin.role, 'organisation_id': muni.id})}"}
    return muni, admin, headers


# ---------------------------------------------------------------------------
# Fix 2 / 3 / 5 — Wards are MunicipalityWard records, NEVER FacilityBlocks
# ---------------------------------------------------------------------------

def test_ward_create_never_creates_facility_block(db_session: Session, client: TestClient):
    _, _, headers = _seed_municipality(db_session)

    res = client.post("/api/v1/organisations/ORG-CIVIC-MUNI/wards", json={"ward_name": "Ward 11 – Old Town"}, headers=headers)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["ward_name"] == "Ward 11 – Old Town"
    assert body["ward_number"]

    # MunicipalityWard created, but NO FacilityBlock
    assert db_session.query(MunicipalityWard).filter(
        MunicipalityWard.municipality_id == "ORG-CIVIC-MUNI"
    ).count() == 1
    assert db_session.query(FacilityBlock).filter(
        FacilityBlock.organisation_id == "ORG-CIVIC-MUNI"
    ).count() == 0


def test_ward_duplicate_name_rejected(db_session: Session, client: TestClient):
    _, _, headers = _seed_municipality(db_session)
    client.post("/api/v1/organisations/ORG-CIVIC-MUNI/wards", json={"ward_name": "Ward 5"}, headers=headers)
    res_dup = client.post("/api/v1/organisations/ORG-CIVIC-MUNI/wards", json={"ward_name": "Ward 5"}, headers=headers)
    assert res_dup.status_code == 400


def test_ward_list_never_returns_facility_blocks(db_session: Session, client: TestClient):
    _, admin, headers = _seed_municipality(db_session)
    # Give the municipality a FacilityBlock (own office wing) AND a ward
    db_session.add(FacilityBlock(organisation_id="ORG-CIVIC-MUNI", block_id="BLK-001", block_name="Mayor Wing", is_active=True))
    db_session.add(MunicipalityWard(municipality_id="ORG-CIVIC-MUNI", ward_number="3", ward_name="Ward 3 – Bazaar", is_active=True))
    db_session.commit()

    res = client.get("/api/v1/organisations/ORG-CIVIC-MUNI/wards?active_only=false", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["ward_number"] == "3"
    assert all("block_id" not in i for i in items)
    assert all("block_name" not in i for i in items)


def test_ward_soft_deactivate(db_session: Session, client: TestClient):
    _, _, headers = _seed_municipality(db_session)
    created = client.post("/api/v1/organisations/ORG-CIVIC-MUNI/wards", json={"ward_name": "Ward 9"}, headers=headers).json()

    res_active = client.get("/api/v1/organisations/ORG-CIVIC-MUNI/wards", headers=headers)
    assert res_active.json()["total"] == 1

    res_del = client.delete(f"/api/v1/organisations/ORG-CIVIC-MUNI/wards/{created['id']}", headers=headers)
    assert res_del.status_code == 200
    assert res_del.json()["is_active"] is False

    res_all = client.get("/api/v1/organisations/ORG-CIVIC-MUNI/wards?active_only=false", headers=headers)
    assert res_all.json()["total"] == 1
    assert res_all.json()["items"][0]["is_active"] is False
    # Active-only list is now empty
    assert client.get("/api/v1/organisations/ORG-CIVIC-MUNI/wards", headers=headers).json()["total"] == 0


# ---------------------------------------------------------------------------
# Fix 8 — Ward detail never fabricates data, never shows facility blocks
# ---------------------------------------------------------------------------

def test_ward_detail_empty_state_has_no_fabricated_data(db_session: Session, client: TestClient):
    _, _, headers = _seed_municipality(db_session)
    ward = client.post("/api/v1/organisations/ORG-CIVIC-MUNI/wards", json={"ward_name": "Ward 2 – Empty"}, headers=headers).json()

    res = client.get(f"/api/v1/organisations/ORG-CIVIC-MUNI/wards/{ward['id']}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_data"] is False
    assert data["message"]
    # NO facility block data leaked into metrics
    assert all(not (m.get("metric") == "block") for m in data.get("metrics", {}).values())
    assert data["anomalies"] == []


def test_ward_detail_shows_only_ward_scoped_telemetry(db_session: Session, client: TestClient):
    _, _, headers = _seed_municipality(db_session)
    ward = client.post("/api/v1/organisations/ORG-CIVIC-MUNI/wards", json={"ward_name": "Ward 1", "ward_number": "1"}, headers=headers).json()

    now = datetime.now(timezone.utc)
    # Reading mapped TO ward 1
    db_session.add(SensorReading(
        organisation_id="ORG-CIVIC-MUNI", ward_id="1", sensor_type="water",
        value=333.0, unit="L", timestamp=now - timedelta(minutes=2),
    ))
    # Reading with block_id (facility block) must NOT leak into ward detail
    db_session.add(SensorReading(
        organisation_id="ORG-CIVIC-MUNI", block_id="BLK-OWN", sensor_type="energy",
        value=9999.0, unit="kWh", timestamp=now - timedelta(minutes=1),
    ))
    db_session.commit()

    res = client.get(f"/api/v1/organisations/ORG-CIVIC-MUNI/wards/{ward['id']}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_data"] is True
    assert data["metrics"]["water"]["latest_value"] == 333.0
    assert data["metrics"]["water"]["status"] == "ONLINE"
    # Energy metric belongs to ward scope only — no block reading leaked
    assert data["metrics"]["energy"]["has_data"] is False
    assert data["metrics"]["energy"]["latest_value"] is None


def test_ward_detail_404_for_other_municipality(db_session: Session, client: TestClient):
    _, _, headers = _seed_municipality(db_session)
    other = Organisation(
        id="ORG-CIVIC-MUNI-2", name="Another NAC",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Municipality / Municipal Campus", is_active=True,
    )
    db_session.add(other)
    ward = MunicipalityWard(municipality_id="ORG-CIVIC-MUNI-2", ward_number="77", ward_name="Ward 77", is_active=True)
    db_session.add(ward)
    db_session.commit()

    res = client.get(f"/api/v1/organisations/ORG-CIVIC-MUNI/wards/{ward.id}", headers=headers)
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Fix 13 — create-full municipality setup modes
# ---------------------------------------------------------------------------

def _sa_headers(db_session: Session) -> dict:
    sa = User(
        id="SA-CIVIC-01", email="civic_sa@greennexa.io",
        hashed_password=security.hash_password("x"), full_name="SA",
        role=User.ROLE_SUPER_ADMIN, is_active=True,
    )
    db_session.add(sa)
    db_session.commit()
    return {"Authorization": f"Bearer {security.create_access_token(data={'sub': sa.id, 'role': sa.role})}"}


def test_create_full_normal_municipality_creates_wards_not_blocks(db_session: Session, client: TestClient):
    sa_headers = _sa_headers(db_session)
    payload = {
        "name": "New NAC Normal",
        "ownership_type": "GOVERNMENT",
        "facility_type": "Municipality / Municipal Campus",
        "facility_name": "New NAC Normal",
        "state": "Odisha",
        "district": "Khurda",
        "city": "Bhubaneswar",
        "address": "Main Rd",
        "admin_name": "NAC Admin",
        "admin_user_id": "nacadmin1",
        "admin_password": "pass1234",
        "municipality_setup_type": "NORMAL_MUNICIPALITY",
        "wards": [{"ward_name": "Ward 1"}, {"ward_name": "Ward 2"}],
        "enabled_modules": ["energy", "street_lighting"],
    }
    res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res.status_code == 201, res.text
    org_id = res.json()["organisation_id"]
    assert db_session.query(MunicipalityWard).filter(MunicipalityWard.municipality_id == org_id).count() == 2
    assert db_session.query(FacilityBlock).filter(FacilityBlock.organisation_id == org_id).count() == 0


def test_create_full_own_office_municipality_creates_blocks_not_wards(db_session: Session, client: TestClient):
    sa_headers = _sa_headers(db_session)
    payload = {
        "name": "New NAC Own Office",
        "ownership_type": "GOVERNMENT",
        "facility_type": "Municipality / Municipal Campus",
        "facility_name": "NAC Own Office",
        "state": "Odisha",
        "district": "Khurda",
        "city": "Bhubaneswar",
        "address": "Main Rd",
        "admin_name": "NAC Admin",
        "admin_user_id": "nacadmin2",
        "admin_password": "pass1234",
        "municipality_setup_type": "OWN_OFFICE",
        "blocks": [{"block_id": "BLK-001", "block_name": "Mayor & Commissioner"}, {"block_id": "BLK-002", "block_name": "Revenue Wing"}],
        "enabled_modules": ["energy", "water"],
    }
    res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res.status_code == 201, res.text
    org_id = res.json()["organisation_id"]
    assert db_session.query(FacilityBlock).filter(FacilityBlock.organisation_id == org_id).count() == 2
    assert db_session.query(MunicipalityWard).filter(MunicipalityWard.municipality_id == org_id).count() == 0


# ---------------------------------------------------------------------------
# Fix 6/7 — Civic sensor catalog
# ---------------------------------------------------------------------------

def test_civic_sensors_recommended_for_municipality():
    rec = get_recommended_sensors_for_type("Municipality / Municipal Campus")
    for mod in ("street_lighting", "roads", "parks", "sewage"):
        assert mod in rec


def test_civic_sensor_in_enabled_config(db_session: Session):
    for mod in ("street_lighting", "roads", "parks", "sewage"):
        assert mod in OrganisationSensorConfig.ALLOWED_SENSOR_TYPES


# ---------------------------------------------------------------------------
# Fix 8/9/16/19 — Civic (natural-location) modules not block-scoped
# ---------------------------------------------------------------------------

def test_street_lighting_not_block_wise_scoped(client: TestClient, db_session: Session):
    _, _, headers = _seed_municipality(db_session)
    # Municipality has a FacilityBlock (own office) — street_lighting is civic
    db_session.add(FacilityBlock(organisation_id="ORG-CIVIC-MUNI", block_id="BLK-OWN", block_name="Own Office", is_active=True))
    now = datetime.now(timezone.utc)
    db_session.add(SensorReading(organisation_id="ORG-CIVIC-MUNI", block_id="BLK-OWN", sensor_type="energy", value=500.0, unit="kWh", timestamp=now))
    # street_lighting reading with NO block — pure civic, not tied to office wings
    db_session.add(SensorReading(organisation_id="ORG-CIVIC-MUNI", sensor_type="street_lighting", value=412.0, unit="kWh", timestamp=now))
    db_session.commit()

    res = client.get("/api/v1/dashboard/ORG-CIVIC-MUNI/modules/street_lighting/overall?period=24h", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["current_value"] == 412.0
    assert data["block_comparison"] == [], "street_lighting must NOT display own-office Facility Blocks"
    assert data["peak"] == 412.0

    # energy stays block-scoped to own office
    res_e = client.get("/api/v1/dashboard/ORG-CIVIC-MUNI/modules/energy/overall?period=24h", headers=headers)
    assert res_e.status_code == 200
    assert res_e.json()["current_value"] == 500.0


def test_module_overall_sewage_parks_roads_supported(client: TestClient, db_session: Session):
    _, admin, headers = _seed_municipality(db_session)
    now = datetime.now(timezone.utc)
    for st, val in (("sewage", 30.0), ("roads", 88.0), ("parks", 65.0)):
        db_session.add(SensorReading(organisation_id="ORG-CIVIC-MUNI", sensor_type=st, value=val, unit="%", timestamp=now))
    db_session.commit()

    for st in ("sewage", "roads", "parks"):
        res = client.get(f"/api/v1/dashboard/ORG-CIVIC-MUNI/modules/{st}/overall?period=24h", headers=headers)
        assert res.status_code == 200, f"{st}: {res.text}"
        assert res.json()["block_comparison"] == []


def test_municipality_dashboard_includes_civic_current_values(client: TestClient, db_session: Session):
    _, _, headers = _seed_municipality(db_session)
    now = datetime.now(timezone.utc)
    db_session.add(SensorReading(organisation_id="ORG-CIVIC-MUNI", sensor_type="street_lighting", value=444.0, unit="kWh", timestamp=now))
    db_session.commit()

    res = client.get("/api/v1/dashboard/ORG-CIVIC-MUNI", headers=headers)
    assert res.status_code == 200
    data = res.json()
    sensor_types = {r["sensor_type"] for r in data["current_values"]}
    assert "street_lighting" in sensor_types


def test_ward_anomalies_scoped_to_ward(db_session: Session, client: TestClient):
    _, _, headers = _seed_municipality(db_session)
    ward = client.post("/api/v1/organisations/ORG-CIVIC-MUNI/wards", json={"ward_name": "Ward 8", "ward_number": "8"}, headers=headers).json()

    now = datetime.now(timezone.utc)
    db_session.add(AnomalyRecord(
        organisation_id="ORG-CIVIC-MUNI", ward_id="8", sensor_type="water",
        metric="water", value=2.0, severity=AnomalyRecord.SEVERITY_HIGH,
        reason="Pressure drop in ward 8", status=AnomalyRecord.STATUS_OPEN,
        timestamp=now - timedelta(minutes=3),
    ))
    db_session.add(AnomalyRecord(
        organisation_id="ORG-CIVIC-MUNI", ward_id="9", sensor_type="energy",
        metric="energy", value=30.0, severity=AnomalyRecord.SEVERITY_MEDIUM,
        reason="Other ward anomaly", status=AnomalyRecord.STATUS_OPEN,
        timestamp=now - timedelta(minutes=3),
    ))
    db_session.commit()

    res = client.get(f"/api/v1/organisations/ORG-CIVIC-MUNI/wards/{ward['id']}", headers=headers)
    assert res.status_code == 200
    anomalies = res.json()["anomalies"]
    assert len(anomalies) == 1
    assert anomalies[0]["metric"] == "water"
    assert anomalies[0]["severity"] == "HIGH"