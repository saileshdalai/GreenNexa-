"""
GreenNexa — Final Root-Cause Regression Suite.

Covers:
  1. Demo Mode propagation: start API with demo_mode -> status.demo_mode True.
  2. Demo-mode scenario anomalies fire on their own cadence even when the
     natural 600s anomaly gap is still active.
  3. Municipality demo exposes ward-scoped readings (ward_id) -> ward-scoped
     AnomalyRecord -> ward-scoped AIRecommendation (ward_id) -> ward detail
     endpoint returns recommendations + forecasts.
  4. Ward forecast estimates are derived strictly from the ward's own readings.
"""

import pytest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    MunicipalityWard,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
)
from app.services.synthetic_simulator import SyntheticDataSimulator, simulator_instance


def _fresh_sim(enroll_org: str | None = None) -> SyntheticDataSimulator:
    sim = SyntheticDataSimulator(interval_seconds=30)
    if enroll_org:
        sim._demo_orgs.add(enroll_org)
    # Zero natural probability path so demo cadence is fully deterministic.
    sim.DEFAULT_ANOMALY_PROBABILITIES = {k: 0.0 for k in SyntheticDataSimulator.DEFAULT_ANOMALY_PROBABILITIES}
    return sim


def _municipality_org(db: Session, org_id: str = "ORG-MUNI-1") -> Organisation:
    org = Organisation(
        id=org_id,
        name="Municipal Corporation Test",
        org_type="municipality",
        facility_name="Municipal Corporation HQ",
        is_active=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _municipality_config(db: Session, org_id: str) -> OrganisationSensorConfig:
    config = OrganisationSensorConfig(
        organisation_id=org_id,
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        enabled_sensors="traffic|water|waste|air_quality",
        is_active=True,
    )
    config.set_sensor_configs({
        "traffic": {"baseline": 500.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "veh/h"},
        "water": {"baseline": 400.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "L"},
        "waste": {"baseline": 50.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "%"},
        "air_quality": {"baseline": 50.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "AQI"},
    })
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@pytest.fixture(autouse=True)
def _reset_simulator_state():
    yield
    simulator_instance.stop()
    simulator_instance.reset_all_simulator_state()


def test_demo_mode_propagation_through_api(db_session: Session, client: TestClient, auth_headers):
    headers = auth_headers("super_admin_demo@greennexa.io", User.ROLE_SUPER_ADMIN)
    try:
        res = client.post(
            "/api/v1/simulator/synthetic/start",
            json={"interval_seconds": 30, "demo_mode": True},
            headers=headers,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["running"] is True
        assert body["demo_mode"] is True
        assert body["interval_seconds"] == 30

        # Status endpoint retains demo_mode
        res_status = client.get("/api/v1/simulator/synthetic/status", headers=headers)
        assert res_status.status_code == 200
        assert res_status.json()["demo_mode"] is True
    finally:
        client.post("/api/v1/simulator/synthetic/stop", headers=headers)

    res_stop = client.get("/api/v1/simulator/synthetic/status", headers=headers)
    assert res_stop.status_code == 200
    assert res_stop.json()["demo_mode"] is False


def test_demo_cadence_fires_within_natural_anomaly_gap(db_session: Session):
    org = Organisation(id="ORG-DEMO-GAP", name="Gap Org", org_type="college", is_active=True)
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    config = OrganisationSensorConfig(
        organisation_id=org.id,
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        enabled_sensors="energy|water|traffic",
        is_active=True,
    )
    config.set_sensor_configs({
        "energy": {"baseline": 1000.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "kWh"},
        "water": {"baseline": 400.0, "warning_threshold": 20.0, "critical_threshold": 40.0, "unit": "L"},
        "traffic": {"baseline": 500.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": "veh/h"},
    })
    db_session.add(config)
    db_session.commit()

    sim = _fresh_sim(org.id)
    t0 = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)

    # Fire scenario 0 (Water Supply Leak) immediately.
    sim._demo_schedules[org.id] = {"next_trigger_at": t0, "scenario_index": 0}
    r1 = sim.run_cycle(db_session, current_time=t0)
    assert any(r.is_anomaly for r in r1), "expected an anomaly in the first demo cycle"
    assert sim._last_anomaly_times.get(org.id) == t0

    # 30 seconds later — well inside the 600s natural gap — scenario 4
    # (Traffic Congestion) must still fire on the demo cadence.
    t1 = t0 + timedelta(seconds=30)
    sim._demo_schedules[org.id] = {"next_trigger_at": t1, "scenario_index": 4}
    r2 = sim.run_cycle(db_session, current_time=t1)
    traffic_anom = [r for r in r2 if r.sensor_type == "traffic" and r.is_anomaly]
    assert traffic_anom, "demo anomaly must fire within the 600s natural gap"
    assert sim._last_anomaly_times.get(org.id) == t1


def test_ward_scoped_demo_produces_ward_anomaly_recommendation_and_detail(
    db_session: Session, client: TestClient, auth_headers
):
    org = _municipality_org(db_session, "ORG-MUNI-1")
    _municipality_config(db_session, org.id)

    ward = MunicipalityWard(
        id="WRD-1",
        municipality_id=org.id,
        ward_number="1",
        ward_name="Nagar Ward 1",
        zone="North Zone",
        is_active=True,
    )
    db_session.add(ward)
    db_session.commit()
    db_session.refresh(ward)

    sim = _fresh_sim(org.id)
    t0 = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)

    # Scenario 4 = Traffic Congestion on ward scope.
    sim._demo_schedules[org.id] = {"next_trigger_at": t0, "scenario_index": 4}
    r1 = sim.run_cycle(db_session, current_time=t0)

    ward_anom_readings = [
        r for r in r1
        if r.sensor_type == "traffic" and r.ward_id in (ward.ward_number, ward.id) and r.is_anomaly
    ]
    assert ward_anom_readings, "expected a ward-scoped traffic anomaly reading"
    assert ward_anom_readings[0].is_anomaly is True

    anom = (
        db_session.query(AnomalyRecord)
        .filter(
            AnomalyRecord.organisation_id == org.id,
            AnomalyRecord.metric == "traffic",
            AnomalyRecord.ward_id.in_([ward.ward_number, ward.id]),
            AnomalyRecord.status == AnomalyRecord.STATUS_OPEN,
        )
        .first()
    )
    assert anom is not None, "ward anomaly record must be persisted with ward_id"
    assert anom.ward_id == ward.ward_number

    rec = (
        db_session.query(AIRecommendation)
        .filter(
            AIRecommendation.organisation_id == org.id,
            AIRecommendation.ward_id.in_([ward.ward_number, ward.id]),
        )
        .first()
    )
    assert rec is not None, "recommendation must carry ward_id"
    assert rec.anomaly_id == anom.id
    assert rec.facility_id == ward.ward_name

    # Two more cycles accumulate ward-scoped traffic history (3 readings total),
    # enabling a genuinely-derived ward forecast estimate.
    sim.run_cycle_for_org(db_session, org.id, current_time=t0 + timedelta(seconds=30))
    sim.run_cycle_for_org(db_session, org.id, current_time=t0 + timedelta(seconds=60))

    ward_traffic_count = (
        db_session.query(SensorReading)
        .filter(
            SensorReading.organisation_id == org.id,
            SensorReading.sensor_type == "traffic",
            SensorReading.ward_id.in_([ward.ward_number, ward.id]),
        )
        .count()
    )
    assert ward_traffic_count >= 3

    headers = auth_headers("super_admin_ward@greennexa.io", User.ROLE_SUPER_ADMIN)
    res = client.get(f"/api/v1/organisations/{org.id}/wards/{ward.ward_number}", headers=headers)
    assert res.status_code == 200
    payload = res.json()

    assert payload["has_data"] is True
    assert payload["metrics"]["traffic"]["has_data"] is True

    # The ward anomaly surfaces in the anomalies list (the latest traffic reading
    # itself is normal after the two non-anomaly accumulation cycles).
    assert any(a["metric"] == "traffic" for a in payload["anomalies"])

    # Recommendations surfaced on ward detail
    assert payload["recommendations"], "ward detail must return recommendations"
    assert any(r["metric"] == "traffic" for r in payload["recommendations"])

    # Forecasts surfaced on ward detail — derived from the ward's own readings only
    assert payload["forecasts"]
    traffic_forecast = next((f for f in payload["forecasts"] if f["sensor_type"] == "traffic"), None)
    assert traffic_forecast is not None
    assert traffic_forecast["is_available"] is True
    assert len(traffic_forecast["points"]) == 3
    for p in traffic_forecast["points"]:
        assert p["predicted_value"] >= 0
        assert p["lower_bound"] <= p["predicted_value"] <= p["upper_bound"]


def test_ward_detail_honest_empty_forecast_when_history_insufficient(
    db_session: Session, client: TestClient, auth_headers
):
    org = _municipality_org(db_session, "ORG-MUNI-2")
    _municipality_config(db_session, org.id)
    ward = MunicipalityWard(
        id="WRD-11",
        municipality_id=org.id,
        ward_number="11",
        ward_name="Sparse Ward",
        is_active=True,
    )
    db_session.add(ward)
    db_session.commit()

    sim = _fresh_sim()
    sim.run_cycle_for_org(db_session, org.id, current_time=datetime(2026, 9, 20, 11, 0, 0, tzinfo=timezone.utc))

    headers = auth_headers("super_admin_sparse@greennexa.io", User.ROLE_SUPER_ADMIN)
    res = client.get(f"/api/v1/organisations/{org.id}/wards/{ward.ward_number}", headers=headers)
    assert res.status_code == 200
    payload = res.json()

    assert payload["metrics"]["traffic"]["has_data"] is True
    # Only 1-2 readings exist for this ward -> forecast must be honestly unavailable
    traffic_forecast = next((f for f in payload["forecasts"] if f["sensor_type"] == "traffic"), None)
    assert traffic_forecast is not None
    assert traffic_forecast["is_available"] is False
    assert traffic_forecast["points"] == []
    assert traffic_forecast["message"]