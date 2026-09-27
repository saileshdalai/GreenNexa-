"""
Tests for Admin Organisation Sensor Configuration Flow & Module Access Enforcement.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Organisation, OrganisationSensorConfig, User
from app.core import security
from app.main import app


def test_admin_sensor_config_flow(db_session: Session, client: TestClient):
    # 1. Create Super Admin
    super_admin = User(
        id="SA-CONFIG-TEST",
        email="superadmin_cfg@greennexa.io",
        hashed_password=security.hash_password("supersecret123"),
        full_name="Super Admin Config",
        role=User.ROLE_SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(super_admin)
    db_session.commit()

    sa_token = security.create_access_token({"sub": super_admin.id, "role": super_admin.role})
    sa_headers = {"Authorization": f"Bearer {sa_token}"}

    # 2. Super Admin creates Organisation with Energy, Water, Waste (Parking/Traffic OFF)
    payload = {
        "name": "Dynamic Config Tech Park",
        "facility_type": "industrial_estate",
        "facility_name": "Dynamic Park",
        "state": "Maharashtra",
        "district": "Pune",
        "city": "Pune",
        "address": "Tech Zone 1",
        "org_code": "ORG-CFG-99",
        "admin_name": "Park Admin",
        "admin_email": "admin@dynamicpark.com",
        "admin_password": "AdminPassword123!",
        "enabled_modules": ["energy", "water", "waste"],
    }

    res_create = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res_create.status_code == 201
    created_data = res_create.json()
    org_id = created_data["organisation_id"]
    admin_email = created_data["admin_email"]

    # 3. Admin logs in
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPassword123!", "organisation_type": "PRIVATE"},
    )
    assert res_login.status_code == 200
    admin_token = res_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Fetch GET /api/v1/organisation/sensor-config as Admin
    res_cfg = client.get("/api/v1/organisation/sensor-config", headers=admin_headers)
    assert res_cfg.status_code == 200
    cfg_json = res_cfg.json()
    assert cfg_json["organisation_id"] == org_id
    assert "energy" in cfg_json["enabled_modules"]
    assert "water" in cfg_json["enabled_modules"]
    assert "waste" in cfg_json["enabled_modules"]
    assert "parking" not in cfg_json["enabled_modules"]
    assert "traffic" not in cfg_json["enabled_modules"]

    # 5. Fetch Dashboard summary as Admin
    res_dash = client.get(f"/api/v1/dashboard/{org_id}", headers=admin_headers)
    assert res_dash.status_code == 200
    dash_json = res_dash.json()
    kpis = dash_json["kpis"]
    assert "energy" in kpis
    assert "water" in kpis
    assert "waste" in kpis
    assert "parking" not in kpis
    assert "traffic" not in kpis

    # 6. Route protection check: Request timeseries for disabled sensor "parking"
    res_ts_disabled = client.get(
        f"/api/v1/dashboard/{org_id}/timeseries",
        params={"sensor_type": "parking", "period": "24h"},
        headers=admin_headers,
    )
    assert res_ts_disabled.status_code in [403, 422]

    # 7. Super Admin updates sensor configuration to enable "parking"
    res_update_cfg = client.put(
        f"/api/v1/super-admin/sensors/{org_id}",
        json=["energy", "water", "waste", "parking"],
        headers=sa_headers,
    )
    assert res_update_cfg.status_code == 200

    # 8. Admin fetches sensor config again after update
    res_cfg_updated = client.get("/api/v1/organisation/sensor-config", headers=admin_headers)
    assert res_cfg_updated.status_code == 200
    cfg_updated_json = res_cfg_updated.json()
    assert "parking" in cfg_updated_json["enabled_modules"]

    # 9. Admin Dashboard now includes parking
    res_dash_updated = client.get(f"/api/v1/dashboard/{org_id}", headers=admin_headers)
    assert res_dash_updated.status_code == 200
    assert "parking" in res_dash_updated.json()["kpis"]


def test_admin_sidebar_and_body_synchronization(db_session: Session, client: TestClient):
    """
    Test exact enable -> disable -> re-enable flow for Energy, Water, Waste, Air Quality, Assets, Safety, Temperature.
    """
    # 1. Create Super Admin
    super_admin = User(
        id="SA-SYNC-TEST",
        email="superadmin_sync@greennexa.io",
        hashed_password=security.hash_password("supersecret123"),
        full_name="Super Admin Sync",
        role=User.ROLE_SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(super_admin)
    db_session.commit()

    sa_token = security.create_access_token({"sub": super_admin.id, "role": super_admin.role})
    sa_headers = {"Authorization": f"Bearer {sa_token}"}

    # 2. Super Admin creates Organisation with 7 modules enabled
    full_modules = ["energy", "water", "waste", "air_quality", "assets", "safety", "temperature"]
    payload = {
        "name": "Sync Verification Campus",
        "facility_type": "college_university",
        "facility_name": "Main Campus",
        "state": "Karnataka",
        "district": "Bengaluru",
        "city": "Bengaluru",
        "address": "Campus Road 42",
        "org_code": "ORG-SYNC-01",
        "admin_name": "Sync Admin",
        "admin_email": "admin@sync-campus.edu",
        "admin_password": "SyncAdminPassword123!",
        "enabled_modules": full_modules,
    }

    res_create = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res_create.status_code == 201
    created_data = res_create.json()
    org_id = created_data["organisation_id"]
    admin_email = created_data["admin_email"]

    # 3. Admin logs in
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "SyncAdminPassword123!", "organisation_type": "PRIVATE"},
    )
    assert res_login.status_code == 200
    admin_token = res_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Verify initial 7 modules on config & dashboard body
    res_cfg1 = client.get("/api/v1/organisation/sensor-config", headers=admin_headers)
    assert res_cfg1.status_code == 200
    cfg1 = res_cfg1.json()["enabled_modules"]
    for m in full_modules:
        assert m in cfg1

    res_dash1 = client.get(f"/api/v1/dashboard/{org_id}", headers=admin_headers)
    assert res_dash1.status_code == 200
    kpis1 = res_dash1.json()["kpis"]
    for m in full_modules:
        assert m in kpis1

    # 5. Disable Waste, Safety, Assets
    reduced_modules = ["energy", "water", "air_quality", "temperature"]
    res_disable = client.put(
        f"/api/v1/super-admin/sensors/{org_id}",
        json=reduced_modules,
        headers=sa_headers,
    )
    assert res_disable.status_code == 200

    # 6. Verify config & dashboard body after disabling
    res_cfg2 = client.get("/api/v1/organisation/sensor-config", headers=admin_headers)
    assert res_cfg2.status_code == 200
    cfg2 = res_cfg2.json()["enabled_modules"]
    assert sorted(cfg2) == sorted(reduced_modules)
    assert "waste" not in cfg2
    assert "safety" not in cfg2
    assert "assets" not in cfg2

    res_dash2 = client.get(f"/api/v1/dashboard/{org_id}", headers=admin_headers)
    assert res_dash2.status_code == 200
    kpis2 = res_dash2.json()["kpis"]
    assert "waste" not in kpis2
    assert "safety" not in kpis2
    assert "assets" not in kpis2
    for m in reduced_modules:
        assert m in kpis2

    # 7. Re-enable Waste, Safety, Assets
    res_reenable = client.put(
        f"/api/v1/super-admin/sensors/{org_id}",
        json=full_modules,
        headers=sa_headers,
    )
    assert res_reenable.status_code == 200

    # 8. Verify config & dashboard body after re-enabling
    res_cfg3 = client.get("/api/v1/organisation/sensor-config", headers=admin_headers)
    assert res_cfg3.status_code == 200
    cfg3 = res_cfg3.json()["enabled_modules"]
    for m in full_modules:
        assert m in cfg3

    res_dash3 = client.get(f"/api/v1/dashboard/{org_id}", headers=admin_headers)
    assert res_dash3.status_code == 200
    kpis3 = res_dash3.json()["kpis"]
    for m in full_modules:
        assert m in kpis3
