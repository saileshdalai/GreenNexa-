"""
Tests for GreenNexa Time-Series Waveform API & Module Trend Points.
Verifies time-series structure, anomaly flags, baseline & threshold levels,
block switching isolation, and multi-tenant security.
"""

import pytest
from app.db.models import FacilityBlock, SensorReading, OrganisationSensorConfig, AnomalyRecord
from app.services.synthetic_simulator import SyntheticDataSimulator


def test_module_overall_trend_points_structure(client, auth_headers, seed_orgs, db_session):
    org_id = seed_orgs["org_a"].id
    simulator = SyntheticDataSimulator()

    # Run cycles to generate data
    simulator.run_cycle(db_session)
    simulator.run_cycle(db_session)

    admin_headers = auth_headers("admin_a@test.com", "ADMIN", organisation_id=org_id)

    res = client.get(f"/api/v1/dashboard/{org_id}/modules/energy/overall", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["module_id"] == "energy"
    assert "trend_points" in data
    assert len(data["trend_points"]) > 0

    # Top-level baseline and thresholds
    assert "baseline" in data
    assert "warning_threshold" in data
    assert "critical_threshold" in data
    assert data["baseline"] is not None
    assert data["warning_threshold"] is not None
    assert data["critical_threshold"] is not None

    # Verify trend point schema
    pt = data["trend_points"][0]
    assert "timestamp" in pt
    assert "value" in pt
    assert "is_anomaly" in pt
    assert isinstance(pt["is_anomaly"], bool)
    assert "anomaly_severity" in pt
    assert "baseline" in pt
    assert "warning_threshold" in pt
    assert "critical_threshold" in pt


def test_module_block_detail_trend_points_structure(client, auth_headers, seed_orgs, db_session):
    org_id = seed_orgs["org_a"].id
    # Ensure block exists
    block = FacilityBlock(organisation_id=org_id, block_id="b_acad", block_name="Academic Block")
    db_session.add(block)
    db_session.commit()

    simulator = SyntheticDataSimulator()
    simulator.run_cycle(db_session)
    simulator.run_cycle(db_session)

    admin_headers = auth_headers("admin_a@test.com", "ADMIN", organisation_id=org_id)

    res = client.get(f"/api/v1/dashboard/{org_id}/modules/energy/block/b_acad", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["block_id"] == "b_acad"
    assert data["block_name"] == "Academic Block"
    assert len(data["trend_points"]) > 0

    assert data["baseline"] is not None
    assert data["warning_threshold"] is not None
    assert data["critical_threshold"] is not None

    pt = data["trend_points"][0]
    assert "timestamp" in pt
    assert "value" in pt
    assert isinstance(pt["is_anomaly"], bool)


def test_energy_cumulative_monotonic_trend(client, auth_headers, seed_orgs, db_session):
    org_id = seed_orgs["org_a"].id
    # Ensure block exists
    block = FacilityBlock(organisation_id=org_id, block_id="b_acad", block_name="Academic Block")
    db_session.add(block)
    db_session.commit()

    simulator = SyntheticDataSimulator()
    for _ in range(4):
        simulator.run_cycle(db_session)

    admin_headers = auth_headers("admin_a@test.com", "ADMIN", organisation_id=org_id)

    # Check block b_acad
    res = client.get(f"/api/v1/dashboard/{org_id}/modules/energy/block/b_acad", headers=admin_headers)
    assert res.status_code == 200
    pts = res.json()["trend_points"]
    assert len(pts) >= 4

    # Verify cumulative non-decreasing for energy
    for i in range(1, len(pts)):
        assert pts[i]["value"] >= pts[i - 1]["value"]


def test_variable_sensor_temperature_trend(client, auth_headers, seed_orgs, db_session):
    org_id = seed_orgs["org_a"].id
    simulator = SyntheticDataSimulator()

    for _ in range(3):
        simulator.run_cycle(db_session)

    admin_headers = auth_headers("admin_a@test.com", "ADMIN", organisation_id=org_id)

    res = client.get(f"/api/v1/dashboard/{org_id}/modules/temperature/overall", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["unit"] == "°C"
    assert len(data["trend_points"]) > 0


def test_waste_fill_percentage_trend(client, auth_headers, seed_orgs, db_session):
    org_id = seed_orgs["org_a"].id
    # Enable waste module for org_a
    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=org_id).first()
    if not cfg:
        cfg = OrganisationSensorConfig(organisation_id=org_id, enabled_sensors="energy|water|temperature|humidity|waste")
        db_session.add(cfg)
    else:
        cfg.enabled_sensors = "energy|water|temperature|humidity|waste"
    db_session.commit()

    simulator = SyntheticDataSimulator()
    for _ in range(3):
        simulator.run_cycle(db_session)

    admin_headers = auth_headers("admin_a@test.com", "ADMIN", organisation_id=org_id)

    res = client.get(f"/api/v1/dashboard/{org_id}/modules/waste/overall", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["unit"] == "%"
    pts = data["trend_points"]
    for p in pts:
        assert 0.0 <= p["value"] <= 100.0


def test_zero_telemetry_clean_empty_trend(client, auth_headers, db_session):
    from app.db.models import Organisation, User

    # Create fresh empty org with no readings
    empty_org = Organisation(
        id="ORG-EMPTY-TEST",
        name="Empty Facility",
        is_active=True,
    )
    db_session.add(empty_org)
    db_session.flush()

    cfg = OrganisationSensorConfig(
        organisation_id=empty_org.id,
        enabled_sensors="energy|water|temperature|waste",
    )
    db_session.add(cfg)
    db_session.commit()

    admin_headers = auth_headers("admin_empty@test.com", "ADMIN", organisation_id=empty_org.id)

    res = client.get(f"/api/v1/dashboard/{empty_org.id}/modules/energy/overall", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["trend_points"] == []
    assert data["current_value"] == 0.0
    assert data["has_sufficient_history"] is False


def test_multi_tenant_isolation_on_modules(client, auth_headers, seed_orgs):
    org_a_id = seed_orgs["org_a"].id
    org_b_id = seed_orgs["org_b"].id

    admin_a_headers = auth_headers("admin_a@test.com", "ADMIN", organisation_id=org_a_id)

    # Admin A attempts to query Org B's module intelligence -> 403 Forbidden
    res_ov = client.get(f"/api/v1/dashboard/{org_b_id}/modules/energy/overall", headers=admin_a_headers)
    assert res_ov.status_code == 403

    res_blk = client.get(f"/api/v1/dashboard/{org_b_id}/modules/energy/block/b_acad", headers=admin_a_headers)
    assert res_blk.status_code == 403
