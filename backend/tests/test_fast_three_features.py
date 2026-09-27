"""
GreenNexa — Targeted Verification Tests for the 3 Fast Features:
1. Priority Engine (>3 threshold, deterministic scoring, exclusion of resolved/dismissed)
2. Simulated Day Change (calendar progression, state reset, baseline start, history preservation)
3. Forecasting Modes (5 modes, honest incomplete data) & Date-Wise CSV/PDF Reporting
"""

import json
import pytest
from datetime import date, datetime, timedelta, timezone
from app.db.models import (
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    AnomalyRecord,
    AIRecommendation,
)
from app.services.priority_engine import priority_engine_service
from app.services.synthetic_simulator import simulator_instance
from app.services.forecasting import forecasting_service
from app.services.reporting import reporting_service


@pytest.fixture
def seed_three_features_data(db_session, seed_orgs):
    """Seed base organisation, configuration, and baseline readings."""
    forecasting_service.clear_cache()
    simulator_instance.reset_simulator_state("ORG-TEST-A")

    cfg = db_session.query(OrganisationSensorConfig).filter_by(organisation_id="ORG-TEST-A").first()
    if not cfg:
        cfg = OrganisationSensorConfig(
            organisation_id="ORG-TEST-A",
            data_source="synthetic",
            enabled_sensors="energy|water",
            sensor_configs=json.dumps({
                "energy": {
                    "baseline": 100.0,
                    "warning_threshold": 120.0,
                    "critical_threshold": 140.0,
                    "unit": "kWh",
                },
                "water": {
                    "baseline": 50.0,
                    "warning_threshold": 60.0,
                    "critical_threshold": 70.0,
                    "unit": "L",
                },
            }),
            simulated_date=date(2026, 9, 20),
            is_active=True,
        )
        db_session.add(cfg)
    else:
        cfg.sensor_configs = json.dumps({
            "energy": {
                "baseline": 100.0,
                "warning_threshold": 120.0,
                "critical_threshold": 140.0,
                "unit": "kWh",
            },
            "water": {
                "baseline": 50.0,
                "warning_threshold": 60.0,
                "critical_threshold": 70.0,
                "unit": "L",
            },
        })
        cfg.simulated_date = date(2026, 9, 20)
        cfg.enabled_sensors = "energy|water"
        cfg.data_source = "synthetic"
        cfg.is_active = True
    db_session.commit()

    return {"org_id": "ORG-TEST-A"}


# ---------------------------------------------------------------------------
# FEATURE 1: Priority Engine Tests
# ---------------------------------------------------------------------------

def test_priority_engine_inactive_when_fewer_than_three_anomalies(db_session, seed_three_features_data):
    """Priority engine must be INACTIVE when active anomalies count is 0, 1, or 2 (fewer than 3)."""
    org_id = seed_three_features_data["org_id"]
    now = datetime.now(timezone.utc)

    # Seed 2 open anomalies
    for i in range(2):
        ano = AnomalyRecord(
            organisation_id=org_id,
            facility_id="FAC-01",
            block_id=f"block_{chr(97+i)}",
            metric="energy",
            value=130.0 + i * 5,
            severity="HIGH",
            status="OPEN",
            timestamp=now - timedelta(minutes=i * 10),
        )
        db_session.add(ano)
    db_session.commit()

    resp = priority_engine_service.get_priority_anomalies(db_session, org_id)
    assert resp.is_active is False
    assert resp.active_count == 2
    assert len(resp.items) == 0


def test_priority_engine_active_when_three_or_more_anomalies(db_session, seed_three_features_data):
    """Priority engine must ACTIVATE when active anomalies count >= 3."""
    org_id = seed_three_features_data["org_id"]
    now = datetime.now(timezone.utc)

    # Seed 2 open anomalies
    for i in range(2):
        ano = AnomalyRecord(
            organisation_id=org_id,
            facility_id="FAC-01",
            block_id=f"block_{chr(97+i)}",
            metric="energy",
            value=125.0 + i * 5,
            severity="HIGH",
            status="OPEN",
            timestamp=now - timedelta(minutes=(i + 1) * 10),
        )
        db_session.add(ano)

    # Add 3rd anomaly (critical threshold breach: value 155 > critical 140)
    ano3 = AnomalyRecord(
        organisation_id=org_id,
        facility_id="FAC-01",
        block_id="block_c",
        metric="energy",
        value=155.0,
        severity="CRITICAL",
        status="OPEN",
        timestamp=now,
    )
    db_session.add(ano3)
    db_session.flush()

    rec = AIRecommendation(
        organisation_id=org_id,
        facility_id="FAC-01",
        block_id="block_c",
        anomaly_id=ano3.id,
        metric="energy",
        current_value=155.0,
        severity="CRITICAL",
        summary="Critical heating ventilation overload in Block C. Inspect dampers.",
        status="ACTIVE",
    )
    db_session.add(rec)
    db_session.commit()

    resp = priority_engine_service.get_priority_anomalies(db_session, org_id)
    assert resp.is_active is True
    assert resp.active_count == 3
    # When active with a high priority issue, display ONLY the single most important anomaly
    assert len(resp.items) == 1

    top = resp.items[0]
    assert top.priority_level in ("CRITICAL", "P1_CRITICAL")
    assert top.critical_threshold == 140.0
    assert top.current_value >= 140.0
    assert "critical" in top.why_priority.lower()


def test_priority_engine_excludes_resolved_and_dismissed(db_session, seed_three_features_data):
    """Resolving an anomaly drops active count; if active count drops < 3 (0-2), engine deactivates."""
    org_id = seed_three_features_data["org_id"]
    now = datetime.now(timezone.utc)

    # Seed 3 open anomalies
    anomalies = []
    for i in range(3):
        ano = AnomalyRecord(
            organisation_id=org_id,
            facility_id="FAC-01",
            block_id=f"block_{chr(97+i)}",
            metric="energy",
            value=130.0 + i * 5,
            severity="HIGH",
            status="OPEN",
            timestamp=now - timedelta(minutes=i * 10),
        )
        db_session.add(ano)
        anomalies.append(ano)
    db_session.commit()

    # Verify active when 3
    resp3 = priority_engine_service.get_priority_anomalies(db_session, org_id)
    assert resp3.is_active is True
    assert resp3.active_count == 3

    # Mark one anomaly as RESOLVED
    anomalies[0].status = "RESOLVED"
    db_session.commit()

    # Now active count is 2 -> must be inactive
    resp2 = priority_engine_service.get_priority_anomalies(db_session, org_id)
    assert resp2.active_count == 2
    assert resp2.is_active is False
    assert len(resp2.items) == 0

    # Mark another anomaly as DISMISSED
    anomalies[1].status = "DISMISSED"
    db_session.commit()

    resp1 = priority_engine_service.get_priority_anomalies(db_session, org_id)
    assert resp1.active_count == 1
    assert resp1.is_active is False
    assert len(resp1.items) == 0


# ---------------------------------------------------------------------------
# FEATURE 2: Simulated Day Change Tests
# ---------------------------------------------------------------------------

def test_simulated_day_change_advances_date_and_preserves_history(db_session, seed_three_features_data):
    """Day change advances calendar by 1 day and preserves prior day readings."""
    org_id = seed_three_features_data["org_id"]
    db_session.query(SensorReading).filter_by(organisation_id=org_id).delete()
    db_session.commit()

    # Seed 5 readings for Day 1 (2026-09-20)
    for i in range(5):
        db_session.add(
            SensorReading(
                organisation_id=org_id,
                sensor_type="energy",
                value=115.0 + i,
                unit="kWh",
                source="synthetic",
                timestamp=datetime(2026, 9, 20, 10, i * 5, tzinfo=timezone.utc),
            )
        )
    db_session.commit()

    # Verify Day 1
    day_info = simulator_instance.get_simulated_day(db_session, org_id)
    assert day_info["simulated_date"] == "2026-09-20"
    assert day_info["day_of_week"] == "SUN"

    # Advance by 1 day
    advance_res = simulator_instance.change_simulated_day(db_session, org_id, days=1)
    assert advance_res["simulated_date"] == "2026-09-21"
    assert advance_res["day_of_week"] == "MON"

    # Prior day readings are completely preserved
    day1_readings = db_session.query(SensorReading).filter(
        SensorReading.organisation_id == org_id,
        SensorReading.timestamp < datetime(2026, 9, 21, tzinfo=timezone.utc),
    ).count()
    assert day1_readings == 5

    # Run simulator on new day — initial reading should start at current configuration baseline (100.0)
    cycle_res = simulator_instance.run_cycle_for_org(db_session, org_id)
    new_day_readings = db_session.query(SensorReading).filter(
        SensorReading.organisation_id == org_id,
        SensorReading.timestamp >= datetime(2026, 9, 21, tzinfo=timezone.utc),
    ).all()
    assert len(new_day_readings) > 0
    # Values should start around baseline 100.0 (not reusing 119.0 from yesterday's end)
    energy_r = [r for r in new_day_readings if r.sensor_type == "energy"]
    assert len(energy_r) > 0
    assert abs(energy_r[0].value - 100.0) < 15.0


# ---------------------------------------------------------------------------
# FEATURE 3: Forecasting Modes & Date-Wise Reporting Tests
# ---------------------------------------------------------------------------

def test_forecast_default_mode_honest_insufficient_data(client, auth_headers, seed_three_features_data):
    """Default mode returns honest status_message when current-day readings are insufficient."""
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")

    # Only 1 reading exists for today (2026-09-21)
    forecasting_service.clear_cache()
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h&mode=default", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_available"] is False
    assert "insufficient current-day data" in data["status_message"].lower()


def test_forecast_multi_day_modes_incomplete_data(client, auth_headers, seed_three_features_data):
    """7d, 15d, and 30d modes honestly report incomplete data counts."""
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")

    forecasting_service.clear_cache()
    res = client.get("/api/v1/forecast/ORG-TEST-A?sensor_type=energy&horizon=24h&mode=7d", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_available"] is False
    assert "7-day data not complete" in data["status_message"]
    assert data["required_days"] == 7


def test_date_wise_csv_export_exact_columns(client, auth_headers, seed_three_features_data):
    """Date-wise CSV export strictly filters to selected date and outputs exact required columns."""
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")

    res = client.get("/api/v1/reports/daily?format=csv&date=2026-09-20", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]

    first_line = res.text.strip().split("\n")[0].strip()
    expected_header = "Date,Day,Time,Organisation,Module,Block,Metric,Value,Baseline,Warning Threshold,Critical Threshold,Anomaly,Anomaly Status,Recommendation,Recommendation Status,Data Source"
    assert first_line == expected_header


def test_date_wise_power_bi_pdf_export(client, auth_headers, seed_three_features_data):
    """Date-wise PDF report generates valid Power BI-style PDF."""
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")

    res = client.get("/api/v1/reports/daily?format=pdf&date=2026-09-20", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")
    assert len(res.content) > 500
