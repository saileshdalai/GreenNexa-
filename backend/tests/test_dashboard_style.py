"""
GreenNexa — Dashboard Style System: backend tests.

Covers (backend scope of the 20 required checks):
   1. default dashboard style loads successfully
   2-5. user can select EXECUTIVE / OPERATIONS / ANALYTICS / COMMAND_CENTER
   6.  selection persists (survives a fresh read / re-login)
   7.  invalid values are rejected by the backend
   9.  Organisation A style does not affect Organisation B
  10.  Municipality style does not affect Government Organisation style
  11-14. style change does not change sensor data / anomalies / forecast / simulator
  17/19. RBAC: ADMIN can only set its own organisation, municipality-only scope intact
  20.  all 4 styles are accepted for a Municipality organisation
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.db.models import (
    AnomalyRecord,
    MunicipalityWard,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
)
from app.schemas.dashboard_style import DASHBOARD_STYLE_VALUES
from app.services.forecasting import forecasting_service

ALL_STYLES = ["EXECUTIVE", "OPERATIONS", "ANALYTICS", "COMMAND_CENTER"]


def _headers(db_session: Session, user_id: str, email: str, role: str, org_id: str | None) -> dict:
    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id=user_id,
            email=email,
            hashed_password=security.hash_password("Password123!"),
            full_name=email.split("@")[0],
            role=role,
            organisation_id=org_id,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
    token = security.create_access_token({"sub": user.id, "role": user.role, "organisation_id": user.organisation_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def style_world(db_session: Session):
    """Two normal organisations + a Municipality + a Government organisation."""
    forecasting_service.clear_cache()

    org_a = Organisation(id="ORG-STYLE-A", name="Style College A", org_type="college", is_active=True)
    org_b = Organisation(id="ORG-STYLE-B", name="Style Hospital B", org_type="hospital", is_active=True)
    muni = Organisation(id="ORG-STYLE-MUNI", name="Style Municipality", org_type="Municipality", is_active=True)
    gov = Organisation(
        id="ORG-STYLE-GOV",
        name="Style Govt Authority",
        org_type="Public Sector Facility",
        ownership_type=Organisation.OWNERSHIP_GOVERNMENT,
        is_active=True,
    )
    db_session.add_all([org_a, org_b, muni, gov])

    for org_id in (org_a.id, org_b.id, muni.id, gov.id):
        db_session.add(
            OrganisationSensorConfig(
                organisation_id=org_id,
                data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
                enabled_sensors="energy|water",
                is_active=True,
            )
        )

    ward = MunicipalityWard(
        id="WARD-STYLE-1",
        municipality_id=muni.id,
        ward_number="1",
        ward_name="Ward One",
        is_active=True,
    )
    db_session.add(ward)

    now = datetime.now(timezone.utc)
    for i in range(48, 0, -1):
        ts = now - timedelta(hours=i)
        for org_id, base in ((org_a.id, 100.0), (muni.id, 200.0), (gov.id, 150.0)):
            db_session.add(
                SensorReading(
                    organisation_id=org_id,
                    sensor_type="energy",
                    value=base + (i % 5) * 2.0,
                    unit="kWh",
                    source="synthetic",
                    timestamp=ts,
                    is_anomaly=False,
                )
            )
        db_session.add(
            SensorReading(
                organisation_id=org_b.id,
                sensor_type="energy",
                value=90.0 + (i % 4) * 1.5,
                unit="kWh",
                source="synthetic",
                timestamp=ts,
                is_anomaly=False,
            )
        )

    anomaly = AnomalyRecord(
        id="ANOM-STYLE-1",
        organisation_id=org_a.id,
        metric="energy",
        value=420.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        reason="Above baseline",
        timestamp=now,
    )
    db_session.add(anomaly)
    db_session.commit()

    return {
        "org_a": org_a,
        "org_b": org_b,
        "municipality": muni,
        "gov": gov,
    }


# ---------------------------------------------------------------------------
# 1. Default style loads successfully
# ---------------------------------------------------------------------------
def test_default_dashboard_style_loads_successfully(db_session: Session, client: TestClient, style_world):
    headers = _headers(db_session, "U-ADMIN-A", "admin.a@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-A")

    res = client.get("/api/v1/dashboard/ORG-STYLE-A/style", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["organisation_id"] == "ORG-STYLE-A"
    assert body["dashboard_style"] == "EXECUTIVE"
    assert body["is_default"] is True
    assert body["available_styles"] == DASHBOARD_STYLE_VALUES

    # The dashboard summary also carries the resolved style.
    summary = client.get("/api/v1/dashboard/ORG-STYLE-A", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["dashboard_style"] == "EXECUTIVE"


# ---------------------------------------------------------------------------
# 2-5. Selecting each of the four styles
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("style", ALL_STYLES)
def test_user_can_select_each_style(db_session: Session, client: TestClient, style_world, style: str):
    headers = _headers(db_session, "U-ADMIN-A", "admin.a@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-A")

    res = client.put("/api/v1/dashboard/ORG-STYLE-A/style", json={"dashboard_style": style}, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["dashboard_style"] == style

    # 6. selection persists in the database
    db_session.expire_all()
    stored = db_session.query(Organisation).filter_by(id="ORG-STYLE-A").one()
    assert stored.dashboard_style == style

    # 6/7. persists across a fresh read (equivalent to a refresh / re-login)
    again = client.get("/api/v1/dashboard/ORG-STYLE-A/style", headers=headers)
    assert again.json()["dashboard_style"] == style


def test_style_selection_is_case_and_format_tolerant_but_never_arbitrary(db_session: Session, client: TestClient, style_world):
    headers = _headers(db_session, "U-ADMIN-A", "admin.a@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-A")

    ok = client.put(
        "/api/v1/dashboard/ORG-STYLE-A/style",
        json={"dashboard_style": "command center"},
        headers=headers,
    )
    assert ok.status_code == 200
    assert ok.json()["dashboard_style"] == "COMMAND_CENTER"

    for bad in ["FANCY", "", "DARK_MODE", "COMMAND-CENTRE", "executive_2"]:
        res = client.put(
            "/api/v1/dashboard/ORG-STYLE-A/style",
            json={"dashboard_style": bad},
            headers=headers,
        )
        assert res.status_code == 422, f"{bad!r} should be rejected, got {res.status_code}"

    # Rejected values never changed the stored style.
    assert client.get("/api/v1/dashboard/ORG-STYLE-A/style", headers=headers).json()["dashboard_style"] == "COMMAND_CENTER"


# ---------------------------------------------------------------------------
# 9. Organisation A style does not affect Organisation B
# ---------------------------------------------------------------------------
def test_organisation_a_style_does_not_affect_organisation_b(db_session: Session, client: TestClient, style_world):
    admin_a = _headers(db_session, "U-ADMIN-A", "admin.a@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-A")
    admin_b = _headers(db_session, "U-ADMIN-B", "admin.b@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-B")

    assert client.put("/api/v1/dashboard/ORG-STYLE-A/style", json={"dashboard_style": "EXECUTIVE"}, headers=admin_a).status_code == 200
    assert client.put("/api/v1/dashboard/ORG-STYLE-B/style", json={"dashboard_style": "ANALYTICS"}, headers=admin_b).status_code == 200

    assert client.get("/api/v1/dashboard/ORG-STYLE-A/style", headers=admin_a).json()["dashboard_style"] == "EXECUTIVE"
    assert client.get("/api/v1/dashboard/ORG-STYLE-B/style", headers=admin_b).json()["dashboard_style"] == "ANALYTICS"

    # Admin A cannot even attempt to change Org B.
    forbidden = client.put("/api/v1/dashboard/ORG-STYLE-B/style", json={"dashboard_style": "OPERATIONS"}, headers=admin_a)
    assert forbidden.status_code == 403
    assert client.get("/api/v1/dashboard/ORG-STYLE-B/style", headers=admin_b).json()["dashboard_style"] == "ANALYTICS"


# ---------------------------------------------------------------------------
# 10. Municipality style does not affect Government Organisation style
# ---------------------------------------------------------------------------
def test_municipality_style_does_not_affect_government_org(db_session: Session, client: TestClient, style_world):
    admin_muni = _headers(db_session, "U-ADMIN-MUNI", "admin.muni@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-MUNI")
    admin_gov = _headers(db_session, "U-ADMIN-GOV", "admin.gov@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-GOV")

    assert client.put("/api/v1/dashboard/ORG-STYLE-MUNI/style", json={"dashboard_style": "COMMAND_CENTER"}, headers=admin_muni).status_code == 200
    assert client.put("/api/v1/dashboard/ORG-STYLE-GOV/style", json={"dashboard_style": "OPERATIONS"}, headers=admin_gov).status_code == 200

    assert client.get("/api/v1/dashboard/ORG-STYLE-MUNI/style", headers=admin_muni).json()["dashboard_style"] == "COMMAND_CENTER"
    assert client.get("/api/v1/dashboard/ORG-STYLE-GOV/style", headers=admin_gov).json()["dashboard_style"] == "OPERATIONS"

    # Municipality admin cannot write the government organisation's style.
    assert client.put("/api/v1/dashboard/ORG-STYLE-GOV/style", json={"dashboard_style": "ANALYTICS"}, headers=admin_muni).status_code == 403


# ---------------------------------------------------------------------------
# 20. All four styles work for a Municipality (no duplicate dashboard engine)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("style", ALL_STYLES)
def test_municipality_supports_all_four_styles(db_session: Session, client: TestClient, style_world, style: str):
    admin_muni = _headers(db_session, "U-ADMIN-MUNI", "admin.muni@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-MUNI")

    res = client.put("/api/v1/dashboard/ORG-STYLE-MUNI/style", json={"dashboard_style": style}, headers=admin_muni)
    assert res.status_code == 200
    assert res.json()["dashboard_style"] == style

    summary = client.get("/api/v1/dashboard/ORG-STYLE-MUNI", headers=admin_muni)
    assert summary.status_code == 200
    s = summary.json()
    assert s["dashboard_style"] == style
    # Municipality data is identical regardless of style
    assert s["total_wards"] == 1
    assert s["wards"][0]["ward_name"] == "Ward One"
    assert "energy" in s["kpis"]


# ---------------------------------------------------------------------------
# 11-14. Style change must not touch data, anomalies, forecast or simulator
# ---------------------------------------------------------------------------
def test_changing_style_does_not_change_data_anomalies_forecast_or_simulator(db_session: Session, client: TestClient, style_world):
    admin_a = _headers(db_session, "U-ADMIN-A", "admin.a@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-A")

    def snapshot():
        kpi = client.get("/api/v1/dashboard/ORG-STYLE-A", headers=admin_a).json()
        anom = client.get("/api/v1/anomalies", params={"organisation_id": "ORG-STYLE-A"}, headers=admin_a)
        anom_items = anom.json()["items"] if isinstance(anom.json(), dict) else anom.json()
        fc = client.get(
            "/api/v1/forecast/ORG-STYLE-A",
            params={"sensor_type": "energy", "horizon": "24h", "mode": "last"},
            headers=admin_a,
        )
        cfg = client.get("/api/v1/organisations/ORG-STYLE-A/sensor-config", headers=admin_a).json()
        recent = client.get("/api/v1/dashboard/ORG-STYLE-A/recent", params={"limit": 10}, headers=admin_a).json()
        return {
            "kpis": kpi["kpis"],
            "anomalies": [
                {k: a.get(k) for k in ("id", "metric", "value", "severity", "status", "is_seen")}
                for a in anom_items
            ],
            "forecast": fc.json(),
            "sensor_config": cfg,
            "recent": recent["readings"],
        }

    before = snapshot()
    assert before["anomalies"], "fixture must contain at least one anomaly"

    for style in ("OPERATIONS", "ANALYTICS", "COMMAND_CENTER", "EXECUTIVE"):
        assert client.put(
            "/api/v1/dashboard/ORG-STYLE-A/style", json={"dashboard_style": style}, headers=admin_a
        ).status_code == 200
        after = snapshot()
        assert after["kpis"] == before["kpis"], "sensor data changed when the style changed"
        assert after["anomalies"] == before["anomalies"], "anomaly records/state changed when the style changed"
        assert after["forecast"] == before["forecast"], "forecast changed when the style changed"
        assert after["sensor_config"] == before["sensor_config"], "enabled modules / data source changed"
        assert after["recent"] == before["recent"], "recent sensor readings changed"


def test_changing_style_does_not_restart_simulator(db_session: Session, client: TestClient, style_world):
    from app.services.synthetic_simulator import simulator_instance

    admin_a = _headers(db_session, "U-ADMIN-A", "admin.a@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-A")

    client.post(
        "/api/v1/simulator/synthetic/start",
        json={"interval_seconds": 30, "demo_mode": True},
        params={"organisation_id": "ORG-STYLE-A"},
        headers=admin_a,
    )
    try:
        running_before = simulator_instance.status(organisation_id="ORG-STYLE-A")["running"]
        assert running_before is True

        client.put("/api/v1/dashboard/ORG-STYLE-A/style", json={"dashboard_style": "COMMAND_CENTER"}, headers=admin_a)

        running_after = simulator_instance.status(organisation_id="ORG-STYLE-A")["running"]
        assert running_after is True, "selecting a style must not stop the simulator"
    finally:
        client.post("/api/v1/simulator/synthetic/stop", params={"organisation_id": "ORG-STYLE-A"}, headers=admin_a)


# ---------------------------------------------------------------------------
# Role / scope safety
# ---------------------------------------------------------------------------
def test_super_admin_can_manage_style_of_any_organisation(db_session: Session, client: TestClient, style_world):
    sa = _headers(db_session, "U-SA-STYLE", "sa.style@greennexa.io", User.ROLE_SUPER_ADMIN, None)

    res = client.put("/api/v1/dashboard/ORG-STYLE-B/style", json={"dashboard_style": "ANALYTICS"}, headers=sa)
    assert res.status_code == 200
    assert client.get("/api/v1/dashboard/ORG-STYLE-B/style", headers=sa).json()["dashboard_style"] == "ANALYTICS"


def test_unauthenticated_cannot_read_or_write_style(client: TestClient, style_world):
    assert client.get("/api/v1/dashboard/ORG-STYLE-A/style").status_code == 401
    assert client.put("/api/v1/dashboard/ORG-STYLE-A/style", json={"dashboard_style": "EXECUTIVE"}).status_code == 401


def test_organisation_response_exposes_style_and_available_values(db_session: Session, client: TestClient, style_world):
    admin_a = _headers(db_session, "U-ADMIN-A", "admin.a@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-A")
    client.put("/api/v1/dashboard/ORG-STYLE-A/style", json={"dashboard_style": "OPERATIONS"}, headers=admin_a)

    res = client.get("/api/v1/organisations/ORG-STYLE-A", headers=admin_a)
    assert res.status_code == 200
    body = res.json()
    assert body["dashboard_style"] == "OPERATIONS"
    assert body["available_dashboard_styles"] == DASHBOARD_STYLE_VALUES


def test_oversight_browsing_does_not_leak_other_organisation_style(db_session: Session, client: TestClient, style_world):
    """A Municipality admin may READ associated gov telemetry, but never its style preference."""
    # Associate the government org with the municipality
    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id="ORG-STYLE-MUNI").one()
    cfg.sensor_configs = '{"associated_gov_org_ids": ["ORG-STYLE-GOV"]}'
    db_session.commit()

    admin_gov = _headers(db_session, "U-ADMIN-GOV", "admin.gov@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-GOV")
    client.put("/api/v1/dashboard/ORG-STYLE-GOV/style", json={"dashboard_style": "COMMAND_CENTER"}, headers=admin_gov)

    admin_muni = _headers(db_session, "U-ADMIN-MUNI", "admin.muni@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-MUNI")

    # Oversight read of telemetry is allowed…
    oversight = client.get("/api/v1/dashboard/ORG-STYLE-GOV", headers=admin_muni)
    assert oversight.status_code == 200
    # …but the style of the observed organisation is not exposed.
    assert oversight.json()["dashboard_style"] is None

    # Direct style read is not allowed for a different organisation.
    assert client.get("/api/v1/dashboard/ORG-STYLE-GOV/style", headers=admin_muni).status_code == 403


def test_legacy_row_without_style_resolves_to_default(db_session: Session, client: TestClient, style_world):
    org = db_session.query(Organisation).filter_by(id="ORG-STYLE-A").one()
    org.dashboard_style = None
    db_session.commit()

    admin_a = _headers(db_session, "U-ADMIN-A", "admin.a@greennexa.io", User.ROLE_ADMIN, "ORG-STYLE-A")
    res = client.get("/api/v1/dashboard/ORG-STYLE-A/style", headers=admin_a)
    assert res.status_code == 200
    assert res.json()["dashboard_style"] == "EXECUTIVE"

    org_res = client.get("/api/v1/organisations/ORG-STYLE-A", headers=admin_a)
    assert org_res.json()["dashboard_style"] == "EXECUTIVE"
