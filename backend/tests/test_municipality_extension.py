"""
Tests for Municipality Extension and Government Organisation Associations.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.db.models import FacilityBlock, Organisation, OrganisationSensorConfig, User


def test_municipality_full_extension_flow(db_session: Session, client: TestClient):
    # 1. Setup Super Admin
    super_admin = User(
        id="SA-MUNI-TEST",
        email="superadmin_muni@greennexa.io",
        hashed_password=security.hash_password("supersecret123"),
        full_name="Super Admin Muni",
        role=User.ROLE_SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(super_admin)
    db_session.commit()

    sa_token = security.create_access_token({"sub": super_admin.id, "role": super_admin.role})
    sa_headers = {"Authorization": f"Bearer {sa_token}"}

    # 2. Create a GOVERNMENT organisation
    gov_org = Organisation(
        id="ORG-GOV-001",
        name="State Water Authority",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Public Sector Facility",
        facility_name="HQ Office",
        state="Odisha",
        district="Khurda",
        city="Bhubaneswar",
        address="Secretariat Rd",
        location="Bhubaneswar, Odisha",
        is_active=True,
    )
    db_session.add(gov_org)

    # Create a PRIVATE organisation
    pvt_org = Organisation(
        id="ORG-PVT-001",
        name="Private Tech Center",
        ownership_type=Organisation.OWNERSHIP_PRIVATE,
        org_type="College / University",
        location="Bhubaneswar, Odisha",
        is_active=True,
    )
    db_session.add(pvt_org)

    # Create a Municipality Organisation
    muni_org = Organisation(
        id="ORG-MUNI-001",
        name="Bhubaneswar Municipal Corporation",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Municipality / Municipal Campus",
        location="Bhubaneswar, Odisha",
        is_active=True,
    )
    db_session.add(muni_org)

    # Create Municipality Admin
    muni_admin = User(
        id="ADMIN-MUNI-001",
        organisation_id=muni_org.id,
        email="admin@bmc.gov.in",
        hashed_password=security.hash_password("muniAdminPass123"),
        full_name="BMC Admin",
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    db_session.add(muni_admin)
    db_session.commit()

    muni_admin_token = security.create_access_token({"sub": muni_admin.id, "role": muni_admin.role})
    muni_headers = {"Authorization": f"Bearer {muni_admin_token}"}

    # 3. Test GET /super-admin/organisations/government
    res_gov = client.get("/api/v1/super-admin/organisations/government", headers=sa_headers)
    assert res_gov.status_code == 200
    gov_list = res_gov.json()
    gov_ids = [o["id"] for o in gov_list]
    assert "ORG-GOV-001" in gov_ids
    assert "ORG-PVT-001" not in gov_ids

    # 4. Test PUT /super-admin/organisations/{org_id}/municipality-associations
    assoc_payload = {"associated_gov_org_ids": ["ORG-GOV-001"]}
    res_put_assoc = client.put(
        f"/api/v1/super-admin/organisations/{muni_org.id}/municipality-associations",
        json=assoc_payload,
        headers=sa_headers,
    )
    assert res_put_assoc.status_code == 200
    assert res_put_assoc.json()["associated_gov_org_ids"] == ["ORG-GOV-001"]

    # Test invalid org rejected if PRIVATE org attempted
    bad_assoc = client.put(
        f"/api/v1/super-admin/organisations/{muni_org.id}/municipality-associations",
        json={"associated_gov_org_ids": ["ORG-PVT-001"]},
        headers=sa_headers,
    )
    assert bad_assoc.status_code == 400

    # 5. Test GET /super-admin/organisations/{org_id}/municipality-associations
    res_get_assoc = client.get(
        f"/api/v1/super-admin/organisations/{muni_org.id}/municipality-associations",
        headers=sa_headers,
    )
    assert res_get_assoc.status_code == 200
    assert res_get_assoc.json()["associated_gov_org_ids"] == ["ORG-GOV-001"]

    # 6. Test GET /organisations/{org_id}/associated-government-orgs by Municipality Admin
    res_admin_view = client.get(
        f"/api/v1/organisations/{muni_org.id}/associated-government-orgs",
        headers=muni_headers,
    )
    assert res_admin_view.status_code == 200
    data = res_admin_view.json()
    assert data["municipality_id"] == muni_org.id
    assert len(data["associated_government_orgs"]) == 1
    assert data["associated_government_orgs"][0]["id"] == "ORG-GOV-001"
    assert data["associated_government_orgs"][0]["name"] == "State Water Authority"

    # 7. Test Ward Creation (FacilityBlock) by Municipality Admin
    res_add_ward = client.post(
        f"/api/v1/organisations/{muni_org.id}/blocks",
        json={"block_name": "Ward 1 – North Zone"},
        headers=muni_headers,
    )
    assert res_add_ward.status_code == 201
    created_ward = res_add_ward.json()
    assert created_ward["block_name"] == "Ward 1 – North Zone"
    ward_id = created_ward["block_id"]

    # List wards
    res_list_wards = client.get(
        f"/api/v1/organisations/{muni_org.id}/blocks",
        headers=muni_headers,
    )
    assert res_list_wards.status_code == 200
    items = res_list_wards.json().get("items", [])
    assert any(w["block_id"] == ward_id for w in items)

    # 8. Test Non-Municipality cannot access associated-government-orgs
    pvt_admin = User(
        id="ADMIN-PVT-001",
        organisation_id=pvt_org.id,
        email="admin@pvt.io",
        hashed_password=security.hash_password("pvtpass123"),
        full_name="Pvt Admin",
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    db_session.add(pvt_admin)
    db_session.commit()

    pvt_admin_token = security.create_access_token({"sub": pvt_admin.id, "role": pvt_admin.role})
    pvt_headers = {"Authorization": f"Bearer {pvt_admin_token}"}

    res_pvt_forbidden = client.get(
        f"/api/v1/organisations/{pvt_org.id}/associated-government-orgs",
        headers=pvt_headers,
    )
    assert res_pvt_forbidden.status_code == 403


def test_municipality_add_government_org_association_flow(db_session: Session, client: TestClient):
    # Setup Municipality
    muni_org = Organisation(
        id="ORG-MUNI-TEST2",
        name="Cuttack Municipal Corporation",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Municipality / Municipal Campus",
        location="Cuttack, Odisha",
        is_active=True,
    )
    db_session.add(muni_org)

    # Setup Gov Org
    gov_org_2 = Organisation(
        id="ORG-GOV-HOSP-01",
        name="SCB Medical College & Hospital",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Hospital / Healthcare Facility",
        location="Cuttack, Odisha",
        is_active=True,
    )
    db_session.add(gov_org_2)

    # Setup Private Org
    pvt_org_2 = Organisation(
        id="ORG-PVT-CORP-01",
        name="Private Diagnostics Lab",
        ownership_type=Organisation.OWNERSHIP_PRIVATE,
        org_type="Hospital / Healthcare Facility",
        location="Cuttack, Odisha",
        is_active=True,
    )
    db_session.add(pvt_org_2)

    # Muni Admin
    muni_admin = User(
        id="ADMIN-MUNI-002",
        organisation_id=muni_org.id,
        email="admin@cmc.gov.in",
        hashed_password=security.hash_password("adminpass123"),
        full_name="CMC Admin",
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    db_session.add(muni_admin)
    db_session.commit()

    token = security.create_access_token({"sub": muni_admin.id, "role": muni_admin.role})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test GET /api/v1/organisations/government
    res_gov_list = client.get("/api/v1/organisations/government", headers=headers)
    assert res_gov_list.status_code == 200
    returned_govs = res_gov_list.json()
    gov_ids = [g["id"] for g in returned_govs]
    assert "ORG-GOV-HOSP-01" in gov_ids
    assert "ORG-PVT-CORP-01" not in gov_ids

    # 2. Count existing orgs in DB before association
    count_before = db_session.query(Organisation).count()

    # 3. Associate government org
    res_assoc = client.post(
        f"/api/v1/organisations/{muni_org.id}/associated-government-orgs",
        json={"target_org_id": "ORG-GOV-HOSP-01"},
        headers=headers,
    )
    assert res_assoc.status_code == 200
    assert "ORG-GOV-HOSP-01" in res_assoc.json().get("associated_gov_org_ids", [])

    # Verify NO new organisation record was created in the database (association only)
    count_after = db_session.query(Organisation).count()
    assert count_after == count_before

    # 4. Duplicate association prevention
    res_dup = client.post(
        f"/api/v1/organisations/{muni_org.id}/associated-government-orgs",
        json={"target_org_id": "ORG-GOV-HOSP-01"},
        headers=headers,
    )
    assert res_dup.status_code == 400
    assert "already associated" in res_dup.json()["detail"].lower()

    # 5. Reject private org association
    res_pvt = client.post(
        f"/api/v1/organisations/{muni_org.id}/associated-government-orgs",
        json={"target_org_id": "ORG-PVT-CORP-01"},
        headers=headers,
    )
    assert res_pvt.status_code == 400
    assert "government" in res_pvt.json()["detail"].lower()

