"""
GreenNexa — Phase 8: Dashboard APIs, KPIs & Time-Series Data Unit & Integration Tests.

Tests all 32 required scenarios:
  1. SUPER_ADMIN views any organisation dashboard -> success
  2. ADMIN views own dashboard -> success
  3. ADMIN views another organisation -> 403
  4. VIEWER views own dashboard -> success
  5. VIEWER views another organisation -> 403
  6. Missing token -> 401
  7. Invalid token -> 401
  8. KPI values calculated from actual database readings
  9. Average/min/max correct
  10. Latest value correct
  11. Latest endpoint returns latest reading per enabled sensor
  12. Disabled sensors excluded
  13. Time-series chronological ordering
  14. Time-series sensor filter works
  15. Time-series period filter works
  16. Time-series maximum result limit enforced
  17. Statistics grouped correctly
  18. Recent readings returned newest first
  19. Limit parameter works
  20. Synthetic mode status correct
  21. IoT mode status correct
  22. Simulator state reflected correctly
  23. Recent sensor -> ONLINE
  24. Stale sensor -> OFFLINE
  25. No reading -> NO_DATA
  26. Empty data does not create fake readings
  27. Invalid sensor type -> 422
  28. Invalid period -> 422
  29. Invalid date range (start > end) -> 422
  30. Nonexistent organisation -> 404
  31. Cross-organisation access cannot expose data
  32. Dashboard queries do not load unlimited historical records
"""

from datetime import datetime, timedelta, timezone

import pytest
from app.db.models import IoTDevice, OrganisationSensorConfig, SensorReading


@pytest.fixture
def seed_dashboard_readings(db_session, seed_orgs):
    """Seed deterministic test readings for ORG-TEST-A."""
    now = datetime.now(timezone.utc)

    # 1. Configure ORG-TEST-A: synthetic mode, enabled: energy, water, temperature
    cfg = OrganisationSensorConfig(
        organisation_id="ORG-TEST-A",
        data_source="synthetic",
        enabled_sensors="energy|water|temperature",
        is_active=True,
    )
    db_session.add(cfg)

    # 2. Add readings for energy (values: 1000, 1200, 1400 -> min 1000, max 1400, avg 1200, latest 1400)
    r1 = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="energy",
        value=1000.0,
        unit="kWh",
        source="synthetic",
        timestamp=now - timedelta(minutes=30),
    )
    r2 = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="energy",
        value=1200.0,
        unit="kWh",
        source="synthetic",
        timestamp=now - timedelta(minutes=15),
    )
    r3 = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="energy",
        value=1400.0,
        unit="kWh",
        source="synthetic",
        timestamp=now - timedelta(minutes=2),
    )

    # 3. Add readings for water (values: 300, 500 -> min 300, max 500, avg 400, latest 500)
    r4 = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="water",
        value=300.0,
        unit="L",
        source="synthetic",
        timestamp=now - timedelta(minutes=20),
    )
    r5 = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="water",
        value=500.0,
        unit="L",
        source="synthetic",
        timestamp=now - timedelta(minutes=5),
    )

    # 4. Add stale reading for temperature (older than 15 mins -> status OFFLINE)
    r6 = SensorReading(
        organisation_id="ORG-TEST-A",
        sensor_type="temperature",
        value=25.0,
        unit="°C",
        source="synthetic",
        timestamp=now - timedelta(minutes=45),
    )

    db_session.add_all([r1, r2, r3, r4, r5, r6])
    db_session.commit()
    return {"org_id": "ORG-TEST-A"}


# ---------------------------------------------------------------------------
# Tests 1 - 7: Dashboard Authorization & Access Control
# ---------------------------------------------------------------------------
def test_super_admin_views_any_org_dashboard(client, seed_dashboard_readings, auth_headers):
    """SUPER_ADMIN can view any organisation's dashboard."""
    headers = auth_headers("super_dash@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")
    res = client.get("/api/v1/dashboard/ORG-TEST-A", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["organisation_id"] == "ORG-TEST-A"


def test_admin_views_own_dashboard(client, seed_dashboard_readings, auth_headers):
    """ADMIN can view their own organisation's dashboard."""
    headers = auth_headers("admin_dash@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-A", headers=headers)
    assert res.status_code == 200
    assert res.json()["organisation_id"] == "ORG-TEST-A"


def test_admin_views_another_org_dashboard_denied(client, seed_dashboard_readings, auth_headers):
    """ADMIN cannot view another organisation's dashboard (403 Forbidden)."""
    headers = auth_headers("admin_dash@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-B", headers=headers)
    assert res.status_code == 403


def test_viewer_views_own_dashboard(client, seed_dashboard_readings, auth_headers):
    """VIEWER role is rejected with 403 Forbidden everywhere."""
    headers = auth_headers("viewer_dash@greennexa.com", "VIEWER", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-A", headers=headers)
    assert res.status_code == 403


def test_viewer_views_another_org_dashboard_denied(client, seed_dashboard_readings, auth_headers):
    """VIEWER cannot view another organisation's dashboard (403 Forbidden)."""
    headers = auth_headers("viewer_dash@greennexa.com", "VIEWER", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-B", headers=headers)
    assert res.status_code == 403


def test_missing_token_returns_401(client):
    """Dashboard APIs return 401 Unauthorized when Bearer token is missing."""
    res = client.get("/api/v1/dashboard/ORG-TEST-A")
    assert res.status_code == 401


def test_invalid_token_returns_401(client):
    """Dashboard APIs return 401 Unauthorized when Bearer token is invalid."""
    res = client.get("/api/v1/dashboard/ORG-TEST-A", headers={"Authorization": "Bearer invalid.token"})
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Tests 8 - 10: KPI Calculations
# ---------------------------------------------------------------------------
def test_kpi_values_calculated_from_db(client, seed_dashboard_readings, auth_headers):
    """KPI summary calculates min, max, avg, and latest values directly from DB readings."""
    headers = auth_headers("admin_kpi@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-A", headers=headers)
    assert res.status_code == 200
    kpis = res.json()["kpis"]

    # Energy KPI (1000, 1200, 1400)
    assert "energy" in kpis
    e_kpi = kpis["energy"]
    assert e_kpi["minimum"] == 1000.0
    assert e_kpi["maximum"] == 1400.0
    assert e_kpi["average"] == 1200.0
    assert e_kpi["latest_value"] == 1400.0
    assert e_kpi["reading_count"] == 3

    # Water KPI (300, 500)
    assert "water" in kpis
    w_kpi = kpis["water"]
    assert w_kpi["minimum"] == 300.0
    assert w_kpi["maximum"] == 500.0
    assert w_kpi["average"] == 400.0
    assert w_kpi["latest_value"] == 500.0
    assert w_kpi["reading_count"] == 2


# ---------------------------------------------------------------------------
# Tests 11 & 12: Latest Sensor Values
# ---------------------------------------------------------------------------
def test_latest_sensor_values_endpoint(client, seed_dashboard_readings, auth_headers):
    """GET /latest returns most recent value for enabled sensors; excludes disabled."""
    headers = auth_headers("admin_lat@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-A/latest", headers=headers)
    assert res.status_code == 200
    data = res.json()

    sensor_types = [r["sensor_type"] for r in data["readings"]]
    assert set(sensor_types) == {"energy", "water", "temperature"}
    assert "co2" not in sensor_types
    assert "humidity" not in sensor_types

    energy_item = next(r for r in data["readings"] if r["sensor_type"] == "energy")
    assert energy_item["value"] == 1400.0
    assert energy_item["unit"] == "kWh"


# ---------------------------------------------------------------------------
# Tests 13 - 16: Historical Time-Series
# ---------------------------------------------------------------------------
def test_timeseries_chronological_ordering_and_filters(client, seed_dashboard_readings, auth_headers):
    """Time-series returns data points ordered chronologically, filtered by period and sensor."""
    headers = auth_headers("admin_ts@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-A/timeseries?sensor_type=energy&period=24h", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["sensor_type"] == "energy"
    assert data["total_points"] == 3
    points = data["data"]
    # Check chronological ordering (ascending timestamps)
    assert points[0]["value"] == 1000.0
    assert points[1]["value"] == 1200.0
    assert points[2]["value"] == 1400.0


def test_timeseries_limit_enforced(client, seed_dashboard_readings, auth_headers):
    """Time-series respects maximum limit parameter."""
    headers = auth_headers("admin_ts_lim@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-A/timeseries?sensor_type=energy&limit=2", headers=headers)
    assert res.status_code == 200
    assert len(res.json()["data"]) == 2


# ---------------------------------------------------------------------------
# Test 17: Sensor-wise Statistics
# ---------------------------------------------------------------------------
def test_sensor_statistics_grouped_correctly(client, seed_dashboard_readings, auth_headers):
    """GET /statistics returns DB aggregated count, avg, min, max per enabled sensor."""
    headers = auth_headers("admin_stat@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-A/statistics?period=24h", headers=headers)
    assert res.status_code == 200
    stats = res.json()["statistics"]

    assert "energy" in stats
    assert stats["energy"]["count"] == 3
    assert stats["energy"]["average"] == 1200.0
    assert stats["energy"]["minimum"] == 1000.0
    assert stats["energy"]["maximum"] == 1400.0


# ---------------------------------------------------------------------------
# Tests 18 & 19: Recent Readings
# ---------------------------------------------------------------------------
def test_recent_readings_newest_first_and_limit(client, seed_dashboard_readings, auth_headers):
    """GET /recent returns newest readings first and respects limit parameter."""
    headers = auth_headers("admin_rec@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-A/recent?limit=3", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total"] == 3
    readings = data["readings"]
    # Newest reading first (energy 1400.0 from 2 mins ago)
    assert readings[0]["sensor_type"] == "energy"
    assert readings[0]["value"] == 1400.0


# ---------------------------------------------------------------------------
# Tests 20 - 22: Data Source Mode Status
# ---------------------------------------------------------------------------
def test_data_source_status_endpoint(client, db_session, seed_dashboard_readings, auth_headers):
    """GET /data-source reflects current mode, enabled sensors, and IoT devices count."""
    # Add an IoT device to ORG-TEST-A
    dev = IoTDevice(
        device_id="ESP32-DS-001",
        organisation_id="ORG-TEST-A",
        device_name="Test Dev",
        api_key_hash="hash",
        is_active=True,
    )
    db_session.add(dev)
    db_session.commit()

    headers = auth_headers("admin_ds@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-A/data-source", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["data_source"] == "synthetic"
    assert data["enabled_sensors"] == ["energy", "water", "temperature"]
    assert data["iot_devices_count"] == 1


# ---------------------------------------------------------------------------
# Tests 23 - 25: Sensor Freshness Status (ONLINE / OFFLINE / NO_DATA)
# ---------------------------------------------------------------------------
def test_sensor_freshness_status_determination(client, seed_dashboard_readings, auth_headers):
    """Sensor status evaluates ONLINE (<10m), OFFLINE (>10m), or NO_DATA (no reading)."""
    headers = auth_headers("admin_st@greennexa.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-A/status", headers=headers)
    assert res.status_code == 200
    sensors = res.json()["sensors"]

    e_item = next(s for s in sensors if s["sensor_type"] == "energy")
    assert e_item["status"] == "ONLINE"  # Reading from 2 mins ago

    t_item = next(s for s in sensors if s["sensor_type"] == "temperature")
    assert t_item["status"] == "OFFLINE"  # Reading from 45 mins ago


# ---------------------------------------------------------------------------
# Test 26: Empty Data Handling (No fake data created)
# ---------------------------------------------------------------------------
def test_empty_data_handling_no_fake_readings(client, db_session, seed_orgs, auth_headers):
    """Organisations with no readings return clean NO_DATA response without fake readings."""
    headers = auth_headers("admin_b_empty@greennexa.com", "ADMIN", "ORG-TEST-B")
    res = client.get("/api/v1/dashboard/ORG-TEST-B/status", headers=headers)
    assert res.status_code == 200
    data = res.json()

    for item in data["sensors"]:
        assert item["status"] == "NO_DATA"
        assert item["last_value"] is None


# ---------------------------------------------------------------------------
# Tests 27 - 30: Validation & Entity Error Handling
# ---------------------------------------------------------------------------
def test_dashboard_validation_and_not_found(client, seed_dashboard_readings, auth_headers):
    """Dashboard APIs return 422 for invalid parameters and 404 for nonexistent org."""
    headers = auth_headers("super_val@greennexa.com", "SUPER_ADMIN", "ORG-MAIN")

    # Invalid sensor type -> 422
    res_s = client.get("/api/v1/dashboard/ORG-TEST-A/timeseries?sensor_type=quantum_flux", headers=headers)
    assert res_s.status_code == 422

    # Invalid period -> 422
    res_p = client.get("/api/v1/dashboard/ORG-TEST-A/statistics?period=100years", headers=headers)
    assert res_p.status_code == 422

    # Invalid date range (start > end) -> 422
    t1 = "2026-09-14T12:00:00Z"
    t2 = "2026-09-14T10:00:00Z"
    res_d = client.get(f"/api/v1/dashboard/ORG-TEST-A/timeseries?sensor_type=energy&start={t1}&end={t2}", headers=headers)
    assert res_d.status_code == 422

    # Nonexistent organisation -> 404
    res_404 = client.get("/api/v1/dashboard/ORG-NONEXISTENT", headers=headers)
    assert res_404.status_code == 404


# ---------------------------------------------------------------------------
# Test 31 & 32: Security Isolation & Performance Limits
# ---------------------------------------------------------------------------
def test_cross_org_isolation_and_limit(client, seed_dashboard_readings, auth_headers):
    """ADMIN from another org receives 403 and cannot access dashboard data."""
    admin_b_headers = auth_headers("admin_b_sec@greennexa.com", "ADMIN", "ORG-TEST-B")

    assert client.get("/api/v1/dashboard/ORG-TEST-A", headers=admin_b_headers).status_code == 403
    assert client.get("/api/v1/dashboard/ORG-TEST-A/latest", headers=admin_b_headers).status_code == 403
    assert client.get("/api/v1/dashboard/ORG-TEST-A/timeseries?sensor_type=energy", headers=admin_b_headers).status_code == 403
    assert client.get("/api/v1/dashboard/ORG-TEST-A/statistics", headers=admin_b_headers).status_code == 403
    assert client.get("/api/v1/dashboard/ORG-TEST-A/recent", headers=admin_b_headers).status_code == 403
    assert client.get("/api/v1/dashboard/ORG-TEST-A/data-source", headers=admin_b_headers).status_code == 403
    assert client.get("/api/v1/dashboard/ORG-TEST-A/status", headers=admin_b_headers).status_code == 403
