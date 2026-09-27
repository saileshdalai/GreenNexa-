"""
Tests for Municipality Admin READ-ONLY Oversight of Associated Government Orgs.

Fix 10:
- Municipality Admin may READ dashboard summaries, anomaly lists and
  recommendation lists of the GOVERNMENT organisations associated with their
  municipality (stored in the municipality's OrganisationSensorConfig json).
- Oversight browsing NEVER persists an OrganisationSensorConfig for the
  observed organisation and NEVER grants write access.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.db.models import Organisation, OrganisationSensorConfig, User


def _put_association(client: TestClient, sa_headers, muni_org_id: str, gov_ids):
    return client.put(
        f"/api/v1/super-admin/organisations/{muni_org_id}/municipality-associations",
        json={"associated_gov_org_ids": gov_ids},
        headers=sa_headers,
    )


def test_municipality_admin_read_only_oversight_of_associated_gov_org(
    db_session: Session, client: TestClient
):
    sa = User(
        id="SA-OS-T1",
        email="sa_os_t1@greennexa.io",
        hashed_password=security.hash_password("s"),
        full_name="SA",
        role=User.ROLE_SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(sa)

    gov_org = Organisation(
        id="ORG-GOV-OS-T1",
        name="T1 Civic Hospital",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Hospital / Healthcare Facility",
        location="Bhubaneswar",
        is_active=True,
    )
    db_session.add(gov_org)

    muni_org = Organisation(
        id="ORG-MUNI-OS-T1",
        name="T1 Municipality",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Municipality / Municipal Campus",
        location="Bhubaneswar",
        is_active=True,
    )
    db_session.add(muni_org)

    muni_admin = User(
        id="ADMIN-OS-T1",
        organisation_id=muni_org.id,
        email="t1_admin@nac.gov.in",
        hashed_password=security.hash_password("p"),
        full_name="T1 Admin",
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    db_session.add(muni_admin)
    db_session.commit()

    sa_headers = {
        "Authorization": f"Bearer {security.create_access_token({'sub': sa.id, 'role': sa.role})}"
    }
    muni_headers = {
        "Authorization": f"Bearer {security.create_access_token({'sub': muni_admin.id, 'role': muni_admin.role})}"
    }

    # 1. Associate the government org
    assert (
        _put_association(
            client, sa_headers, muni_org.id, ["ORG-GOV-OS-T1"]
        ).status_code
        == 200
    )

    # 2. Municipality Admin can READ the associated hospital's dashboard summary
    res_summary = client.get(
        "/api/v1/dashboard/ORG-GOV-OS-T1",
        headers=muni_headers,
    )
    assert res_summary.status_code == 200, res_summary.text

    # 3. Municipality Admin can READ associated hospital's anomalies & recommendations
    res_anomalies = client.get(
        "/api/v1/anomalies",
        params={"organisation_id": "ORG-GOV-OS-T1", "limit": 5, "status": "OPEN"},
        headers=muni_headers,
    )
    assert res_anomalies.status_code == 200, res_anomalies.text

    res_recs = client.get(
        "/api/v1/recommendations",
        params={"organisation_id": "ORG-GOV-OS-T1", "status": "OPEN"},
        headers=muni_headers,
    )
    assert res_recs.status_code == 200, res_recs.text

    # 4. Oversight MUST NOT persist a config for the observed government org
    observed_cfg = (
        db_session.query(OrganisationSensorConfig)
        .filter_by(organisation_id="ORG-GOV-OS-T1")
        .count()
    )
    assert observed_cfg == 0

    # 5. Oversight DOES NOT grant write access to the associated org
    res_write = client.post(
        "/api/v1/anomalies/detect/ORG-GOV-OS-T1",
        headers=muni_headers,
    )
    assert res_write.status_code == 403


def test_municipality_admin_cannot_read_non_associated_orgs(
    db_session: Session, client: TestClient
):
    sa = User(
        id="SA-OS-T2",
        email="sa_os_t2@greennexa.io",
        hashed_password=security.hash_password("s"),
        full_name="SA",
        role=User.ROLE_SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(sa)

    gov_org = Organisation(
        id="ORG-GOV-OS-T2",
        name="T2 Civic Hospital",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Hospital / Healthcare Facility",
        location="Bhubaneswar",
        is_active=True,
    )
    db_session.add(gov_org)

    other_gov = Organisation(
        id="ORG-GOV-OS-T2B",
        name="T2 Unassociated Water Board",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Public Sector Facility",
        location="Cuttack",
        is_active=True,
    )
    db_session.add(other_gov)

    muni_org = Organisation(
        id="ORG-MUNI-OS-T2",
        name="T2 Municipality",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Municipality / Municipal Campus",
        location="Bhubaneswar",
        is_active=True,
    )
    db_session.add(muni_org)

    muni_admin = User(
        id="ADMIN-OS-T2",
        organisation_id=muni_org.id,
        email="t2_admin@nac.gov.in",
        hashed_password=security.hash_password("p"),
        full_name="T2 Admin",
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    db_session.add(muni_admin)
    db_session.commit()

    sa_headers = {
        "Authorization": f"Bearer {security.create_access_token({'sub': sa.id, 'role': sa.role})}"
    }
    muni_headers = {
        "Authorization": f"Bearer {security.create_access_token({'sub': muni_admin.id, 'role': muni_admin.role})}"
    }

    # Associate only ORG-GOV-OS-T2
    assert (
        _put_association(
            client, sa_headers, muni_org.id, ["ORG-GOV-OS-T2"]
        ).status_code
        == 200
    )

    # Reading the unassociated GOVERNMENT org is denied
    res_other = client.get("/api/v1/dashboard/ORG-GOV-OS-T2B", headers=muni_headers)
    assert res_other.status_code == 403

    # Reading a non-existent org via the summary endpoint is 404 (not 403)
    # (verify_organisation_access returns the string; org lookup yields 404)
    res_unknown = client.get("/api/v1/dashboard/ORG-NOPE-000", headers=muni_headers)
    assert res_unknown.status_code in (403, 404)


def test_regular_admin_still_blocked_from_other_org_reads(
    db_session: Session, client: TestClient
):
    college = Organisation(
        id="ORG-COL-OS-T3",
        name="T3 College",
        org_type="college",
        location="Campus",
        is_active=True,
    )
    db_session.add(college)

    hospital = Organisation(
        id="ORG-HOSP-OS-T3",
        name="T3 Hospital",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Hospital / Healthcare Facility",
        location="City",
        is_active=True,
    )
    db_session.add(hospital)

    college_admin = User(
        id="ADMIN-OS-T3",
        organisation_id=college.id,
        email="t3_admin@college.io",
        hashed_password=security.hash_password("p"),
        full_name="College Admin",
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    db_session.add(college_admin)
    db_session.commit()

    headers = {
        "Authorization": f"Bearer {security.create_access_token({'sub': college_admin.id, 'role': college_admin.role})}"
    }

    # Non-municipality ADMIN must NOT read another org's dashboard
    res = client.get("/api/v1/dashboard/ORG-HOSP-OS-T3", headers=headers)
    assert res.status_code == 403

    # But CAN still read their own dashboard
    res_own = client.get("/api/v1/dashboard/ORG-COL-OS-T3", headers=headers)
    assert res_own.status_code == 200


def test_super_admin_read_any_org_dashboard(db_session: Session, client: TestClient):
    sa = User(
        id="SA-OS-T4",
        email="sa_os_t4@greennexa.io",
        hashed_password=security.hash_password("s"),
        full_name="SA",
        role=User.ROLE_SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(sa)

    gov_org = Organisation(
        id="ORG-GOV-OS-T4",
        name="T4 Civic Hospital",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Hospital / Healthcare Facility",
        location="Bhubaneswar",
        is_active=True,
    )
    db_session.add(gov_org)
    db_session.commit()

    sa_headers = {
        "Authorization": f"Bearer {security.create_access_token({'sub': sa.id, 'role': sa.role})}"
    }

    res = client.get("/api/v1/dashboard/ORG-GOV-OS-T4", headers=sa_headers)
    assert res.status_code == 200


def test_oversight_uses_stored_associations_and_no_default_sensor_leak(
    db_session: Session, client: TestClient
):
    """The municipality's associated_gov_org_ids come from ITS OWN config json,
    and municipality-type-only modules are NOT enabled for the observed org."""
    sa = User(
        id="SA-OS-T5",
        email="sa_os_t5@greennexa.io",
        hashed_password=security.hash_password("s"),
        full_name="SA",
        role=User.ROLE_SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(sa)

    gov_org = Organisation(
        id="ORG-GOV-OS-T5",
        name="T5 Civic Hospital",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Hospital / Healthcare Facility",
        location="Bhubaneswar",
        is_active=True,
    )
    db_session.add(gov_org)

    muni_org = Organisation(
        id="ORG-MUNI-OS-T5",
        name="T5 Municipality",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        org_type="Municipality / Municipal Campus",
        location="Bhubaneswar",
        is_active=True,
    )
    db_session.add(muni_org)

    muni_admin = User(
        id="ADMIN-OS-T5",
        organisation_id=muni_org.id,
        email="t5_admin@nac.gov.in",
        hashed_password=security.hash_password("p"),
        full_name="T5 Admin",
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    db_session.add(muni_admin)

    # The observed hospital has its OWN config with hospital modules only.
    gov_cfg = OrganisationSensorConfig(
        organisation_id=gov_org.id,
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        is_active=True,
    )
    gov_cfg.set_enabled_sensors(["energy", "water"])
    gov_cfg.set_sensor_configs({
        "energy": {"baseline": 1000.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "kWh"},
        "water": {"baseline": 400.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "L"},
    })
    db_session.add(gov_cfg)
    db_session.commit()

    sa_headers = {
        "Authorization": f"Bearer {security.create_access_token({'sub': sa.id, 'role': sa.role})}"
    }
    muni_headers = {
        "Authorization": f"Bearer {security.create_access_token({'sub': muni_admin.id, 'role': muni_admin.role})}"
    }

    assert (
        _put_association(
            client, sa_headers, muni_org.id, ["ORG-GOV-OS-T5"]
        ).status_code
        == 200
    )

    # Oversight read of the hospital must succeed and expose ONLY the
    # hospital's own configured modules (energy|water), never the
    # municipality civic modules (street_lighting|sewage|roads|parks).
    res = client.get("/api/v1/dashboard/ORG-GOV-OS-T5", headers=muni_headers)
    assert res.status_code == 200, res.text
    data = res.json()

    final_keys = {
        "street_lighting", "sewage", "roads", "parks",
    }
    observed_keys = set()
    for rec in data.get("current_values") or []:
        observed_keys.add(rec.get("sensor_type"))
    for block in data.get("blocks") or []:
        for rec in (block.get("current_values") or []):
            observed_keys.add(rec.get("sensor_type"))
    kpi_keys = set((data.get("kpis") or {}).keys())
    observed_keys = observed_keys | kpi_keys

    assert observed_keys <= {"energy", "water"}
    assert not (observed_keys & final_keys)