"""
Comprehensive Targeted Test Suite for GreenNexa Bugs 1, 2, and 3:
- BUG 1: Priority Engine Logic (>= 3 activation, single top item, "No high-priority anomaly detected.", explainable scoring)
- BUG 2: Simulated Date Persistence & Manual Date Edit (DB source of truth, calendar advancement, leap years, baseline start)
- BUG 3: Optimal Score Dynamic Percentage (100% baseline, -20/-10/-5/-2 penalties, non-clamped negative scores, immediate restoration)
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
from app.services.anomaly_detection import (
    calculate_optimal_score,
    SEVERITY_PENALTIES,
)


@pytest.fixture
def seed_bug_test_data(db_session, seed_orgs):
    """Seed test organisation and sensor config."""
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
        cfg.is_active = True
    db_session.commit()
    return {"org_id": "ORG-TEST-A"}


# ===========================================================================
# BUG 1 — PRIORITY ENGINE LOGIC TESTS
# ===========================================================================

def test_pe_01_inactive_when_zero_anomalies(db_session, seed_bug_test_data):
    """0 active anomalies -> inactive."""
    org_id = seed_bug_test_data["org_id"]
    res = priority_engine_service.evaluate_organisation_priority(db_session, org_id)
    assert res.is_active is False
    assert res.active_count == 0
    assert len(res.items) == 0
    assert res.top_priority is None


def test_pe_02_inactive_when_one_anomaly(db_session, seed_bug_test_data):
    """1 active anomaly -> inactive."""
    org_id = seed_bug_test_data["org_id"]
    ano = AnomalyRecord(
        organisation_id=org_id,
        metric="energy",
        value=150.0,
        severity="CRITICAL",
        status="OPEN",
    )
    db_session.add(ano)
    db_session.commit()

    res = priority_engine_service.evaluate_organisation_priority(db_session, org_id)
    assert res.is_active is False
    assert res.active_count == 1
    assert len(res.items) == 0


def test_pe_03_inactive_when_two_anomalies(db_session, seed_bug_test_data):
    """2 active anomalies -> inactive."""
    org_id = seed_bug_test_data["org_id"]
    for i in range(2):
        db_session.add(AnomalyRecord(
            organisation_id=org_id,
            metric="energy",
            value=145.0 + i,
            severity="CRITICAL",
            status="OPEN",
        ))
    db_session.commit()

    res = priority_engine_service.evaluate_organisation_priority(db_session, org_id)
    assert res.is_active is False
    assert res.active_count == 2
    assert len(res.items) == 0


def test_pe_04_active_when_three_anomalies(db_session, seed_bug_test_data):
    """3 active anomalies -> ACTIVE."""
    org_id = seed_bug_test_data["org_id"]
    for i in range(3):
        db_session.add(AnomalyRecord(
            organisation_id=org_id,
            metric="energy",
            value=145.0 + i,
            severity="CRITICAL",
            status="OPEN",
        ))
    db_session.commit()

    res = priority_engine_service.evaluate_organisation_priority(db_session, org_id)
    assert res.is_active is True
    assert res.active_count == 3


def test_pe_05_active_when_four_or_more_anomalies(db_session, seed_bug_test_data):
    """4+ active anomalies -> ACTIVE."""
    org_id = seed_bug_test_data["org_id"]
    for i in range(5):
        db_session.add(AnomalyRecord(
            organisation_id=org_id,
            metric="energy",
            value=145.0 + i,
            severity="HIGH",
            status="OPEN",
        ))
    db_session.commit()

    res = priority_engine_service.evaluate_organisation_priority(db_session, org_id)
    assert res.is_active is True
    assert res.active_count == 5


def test_pe_06_displays_only_single_most_important_anomaly(db_session, seed_bug_test_data):
    """When 3+ active exist and high-priority exists, display ONLY the single highest priority."""
    org_id = seed_bug_test_data["org_id"]
    # Add 3 high/critical anomalies
    a1 = AnomalyRecord(
        organisation_id=org_id,
        metric="energy",
        value=125.0,
        severity="HIGH",
        status="OPEN",
        block_id="block_a",
    )
    a2 = AnomalyRecord(
        organisation_id=org_id,
        metric="energy",
        value=165.0,  # Critical breach > 140
        severity="CRITICAL",
        status="OPEN",
        block_id="block_b",
    )
    a3 = AnomalyRecord(
        organisation_id=org_id,
        metric="water",
        value=65.0,
        severity="HIGH",
        status="OPEN",
        block_id="block_c",
    )
    db_session.add_all([a1, a2, a3])
    db_session.commit()

    res = priority_engine_service.evaluate_organisation_priority(db_session, org_id)
    assert res.is_active is True
    assert res.active_count == 3
    # MUST contain exactly 1 item (the single most important anomaly)
    assert len(res.items) == 1
    assert res.items[0].id == a2.id
    assert res.items[0].current_value == 165.0
    assert res.top_priority is not None
    assert res.top_priority.id == a2.id


def test_pe_07_no_high_priority_detected_when_none_qualify(db_session, seed_bug_test_data):
    """When 3+ active anomalies exist but none qualify as high priority, display exact message."""
    org_id = seed_bug_test_data["org_id"]
    # Add 3 low anomalies with minimal baseline deviation (<15% deviation, no breach)
    for i in range(3):
        db_session.add(AnomalyRecord(
            organisation_id=org_id,
            metric="energy",
            value=105.0 + i,  # Baseline is 100, warn is 120
            severity="LOW",
            status="OPEN",
            block_id=f"block_{i}",
        ))
    db_session.commit()

    res = priority_engine_service.evaluate_organisation_priority(db_session, org_id)
    assert res.is_active is True
    assert res.active_count == 3
    assert len(res.items) == 0
    assert res.top_priority is None
    assert res.message == "No high-priority anomaly detected."
    assert res.status_message == "No high-priority anomaly detected."


def test_pe_08_resolved_and_dismissed_are_excluded(db_session, seed_bug_test_data):
    """Resolved and dismissed anomalies do not count toward active count or ranking."""
    org_id = seed_bug_test_data["org_id"]
    # 2 Open, 1 Resolved, 1 Dismissed
    db_session.add(AnomalyRecord(organisation_id=org_id, metric="energy", value=150.0, severity="CRITICAL", status="OPEN"))
    db_session.add(AnomalyRecord(organisation_id=org_id, metric="energy", value=150.0, severity="CRITICAL", status="OPEN"))
    db_session.add(AnomalyRecord(organisation_id=org_id, metric="energy", value=180.0, severity="CRITICAL", status="RESOLVED"))
    db_session.add(AnomalyRecord(organisation_id=org_id, metric="energy", value=190.0, severity="CRITICAL", status="DISMISSED"))
    db_session.commit()

    res = priority_engine_service.evaluate_organisation_priority(db_session, org_id)
    # Active count is 2 (2 OPEN)
    assert res.active_count == 2
    assert res.is_active is False
    assert len(res.items) == 0


def test_pe_09_complete_details_in_top_item(db_session, seed_bug_test_data):
    """Top item contains complete details: module, block, value, thresholds, unit, why_priority, recommendation."""
    org_id = seed_bug_test_data["org_id"]
    now = datetime.now(timezone.utc)
    for i in range(2):
        db_session.add(AnomalyRecord(
            organisation_id=org_id,
            metric="water",
            value=62.0,
            severity="HIGH",
            status="OPEN",
            block_id=f"block_w{i}",
            created_at=now - timedelta(minutes=10),
        ))

    crit_ano = AnomalyRecord(
        organisation_id=org_id,
        metric="energy",
        value=175.5,
        severity="CRITICAL",
        status="OPEN",
        block_id="Production-A",
        facility_id="Building-1",
        created_at=now,
    )
    db_session.add(crit_ano)
    db_session.flush()

    rec = AIRecommendation(
        organisation_id=org_id,
        anomaly_id=crit_ano.id,
        metric="energy",
        current_value=175.5,
        severity="CRITICAL",
        summary="Isolate high-amperage sub-panel and verify HVAC compressor load.",
        status="ACTIVE",
    )
    db_session.add(rec)
    db_session.commit()

    res = priority_engine_service.evaluate_organisation_priority(db_session, org_id)
    assert res.is_active is True
    assert len(res.items) == 1
    item = res.items[0]

    assert item.organisation_id == org_id
    assert item.module == "Energy"
    assert item.block_name == "Building-1"
    assert item.current_value == 175.5
    assert item.unit == "kWh"
    assert item.baseline == 100.0
    assert item.warning_threshold == 120.0
    assert item.critical_threshold == 140.0
    assert "critical" in item.why_priority.lower() or "threshold" in item.why_priority.lower()
    assert item.recommended_action == rec.summary
    assert item.recommendation_status == "ACTIVE"


# ===========================================================================
# BUG 2 — SIMULATED DATE PERSISTENCE & MANUAL EDIT TESTS
# ===========================================================================

def test_sim_01_persisted_in_db(db_session, seed_bug_test_data):
    """Simulated date is persisted in OrganisationSensorConfig."""
    org_id = seed_bug_test_data["org_id"]
    day_info = simulator_instance.get_simulated_day(db_session, org_id)
    assert day_info["simulated_date"] == "2026-09-20"
    assert day_info["day_of_week"] == "SUN"


def test_sim_02_manual_set_date_and_weekday_calculation(db_session, seed_bug_test_data):
    """Setting date via set_simulated_date updates DB and calculates correct weekday."""
    org_id = seed_bug_test_data["org_id"]

    res = simulator_instance.set_simulated_date(db_session, org_id, date(2026, 9, 21))
    assert res["simulated_date"] == "2026-09-21"
    assert res["day_of_week"] == "MON"

    # Tuesday
    res_tue = simulator_instance.set_simulated_date(db_session, org_id, date(2026, 9, 22))
    assert res_tue["simulated_date"] == "2026-09-22"
    assert res_tue["day_of_week"] == "TUE"


def test_sim_03_change_day_advances_from_saved_date(db_session, seed_bug_test_data):
    """Change Day advances sequentially from current saved date."""
    org_id = seed_bug_test_data["org_id"]
    simulator_instance.set_simulated_date(db_session, org_id, date(2026, 9, 25))

    adv1 = simulator_instance.change_simulated_day(db_session, org_id, days=1)
    assert adv1["simulated_date"] == "2026-09-26"
    assert adv1["day_of_week"] == "SAT"

    adv2 = simulator_instance.change_simulated_day(db_session, org_id, days=1)
    assert adv2["simulated_date"] == "2026-09-27"
    assert adv2["day_of_week"] == "SUN"


def test_sim_04_calendar_month_and_year_rollover(db_session, seed_bug_test_data):
    """Month and year boundaries rollover accurately."""
    org_id = seed_bug_test_data["org_id"]

    # Month end rollover: 2026-09-30 -> 2026-10-01
    simulator_instance.set_simulated_date(db_session, org_id, date(2026, 9, 30))
    adv_m = simulator_instance.change_simulated_day(db_session, org_id, days=1)
    assert adv_m["simulated_date"] == "2026-10-01"
    assert adv_m["day_of_week"] == "THU"

    # Year end rollover: 2026-12-31 -> 2027-01-01
    simulator_instance.set_simulated_date(db_session, org_id, date(2026, 12, 31))
    adv_y = simulator_instance.change_simulated_day(db_session, org_id, days=1)
    assert adv_y["simulated_date"] == "2027-01-01"
    assert adv_y["day_of_week"] == "FRI"

    # Leap year: 2028-02-28 -> 2028-02-29 -> 2028-03-01
    simulator_instance.set_simulated_date(db_session, org_id, date(2028, 2, 28))
    adv_leap1 = simulator_instance.change_simulated_day(db_session, org_id, days=1)
    assert adv_leap1["simulated_date"] == "2028-02-29"
    adv_leap2 = simulator_instance.change_simulated_day(db_session, org_id, days=1)
    assert adv_leap2["simulated_date"] == "2028-03-01"


def test_sim_05_new_day_starts_from_configuration_baseline(db_session, seed_bug_test_data):
    """New day simulation initializes from current config baseline without reusing yesterday's cumulative last value."""
    org_id = seed_bug_test_data["org_id"]

    # Add high reading on Day 1 (2026-09-20)
    db_session.add(SensorReading(
        organisation_id=org_id,
        sensor_type="energy",
        value=138.0,
        unit="kWh",
        source="synthetic",
        timestamp=datetime(2026, 9, 20, 23, 50, tzinfo=timezone.utc),
    ))
    db_session.commit()

    # Move to Day 2 (2026-09-21)
    simulator_instance.change_simulated_day(db_session, org_id, days=1)

    # Run cycle
    readings = simulator_instance.run_cycle_for_org(db_session, org_id)
    assert len(readings) > 0

    # First energy reading of new day should be around baseline (100.0), not 138+
    energy_readings = [r for r in readings if r.sensor_type == "energy"]
    assert len(energy_readings) > 0
    assert abs(energy_readings[0].value - 100.0) < 15.0


def test_sim_06_endpoints_super_admin_no_org_id(client, auth_headers, seed_bug_test_data):
    """Super admin calling /current-day and /set-date without explicit org query param succeeds."""
    headers = auth_headers("admin@greennexa.com", "SUPER_ADMIN", None)

    # GET /current-day
    res = client.get("/api/v1/simulator/current-day", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "simulated_date" in data
    assert "day_of_week" in data

    # POST /set-date
    res_set = client.post(
        "/api/v1/simulator/set-date",
        json={"date": "2026-09-24"},
        headers=headers,
    )
    assert res_set.status_code == 200
    assert res_set.json()["simulated_date"] == "2026-09-24"
    assert res_set.json()["day_of_week"] == "THU"

    # POST /change-day
    res_chg = client.post(
        "/api/v1/simulator/change-day",
        json={"days": 1},
        headers=headers,
    )
    assert res_chg.status_code == 200
    assert res_chg.json()["simulated_date"] == "2026-09-25"
    assert res_chg.json()["day_of_week"] == "FRI"


# ===========================================================================
# BUG 3 — OPTIMAL SCORE DYNAMIC PERCENTAGE TESTS
# ===========================================================================

def test_score_01_baseline_100_percent():
    """No active anomalies -> 100% score."""
    score = calculate_optimal_score([])
    assert score == 100


def test_score_02_critical_anomaly_penalty_20():
    """1 Critical anomaly -> 80% (100 - 20)."""
    score = calculate_optimal_score([{"severity": "CRITICAL", "status": "OPEN"}])
    assert score == 80


def test_score_03_high_anomaly_penalty_10():
    """1 High anomaly -> 90% (100 - 10)."""
    score = calculate_optimal_score([{"severity": "HIGH", "status": "OPEN"}])
    assert score == 90


def test_score_04_medium_anomaly_penalty_5():
    """1 Medium anomaly -> 95% (100 - 5)."""
    score = calculate_optimal_score([{"severity": "MEDIUM", "status": "OPEN"}])
    assert score == 95


def test_score_05_low_anomaly_penalty_2():
    """1 Low anomaly -> 98% (100 - 2)."""
    score = calculate_optimal_score([{"severity": "LOW", "status": "OPEN"}])
    assert score == 98


def test_score_06_mixed_penalties():
    """1 Critical (-20), 1 High (-10), 1 Medium (-5), 1 Low (-2) -> 63%."""
    anomalies = [
        {"severity": "CRITICAL", "status": "OPEN"},
        {"severity": "HIGH", "status": "OPEN"},
        {"severity": "MEDIUM", "status": "OPEN"},
        {"severity": "LOW", "status": "OPEN"},
    ]
    score = calculate_optimal_score(anomalies)
    assert score == 63


def test_score_07_acknowledged_status_included():
    """ACKNOWLEDGED status is active and penalised."""
    anomalies = [
        {"severity": "CRITICAL", "status": "ACKNOWLEDGED"},
        {"severity": "HIGH", "status": "ACKNOWLEDGED"},
    ]
    score = calculate_optimal_score(anomalies)
    assert score == 70  # 100 - 20 - 10


def test_score_08_resolved_and_dismissed_excluded():
    """RESOLVED and DISMISSED anomalies have 0 penalty."""
    anomalies = [
        {"severity": "CRITICAL", "status": "RESOLVED"},
        {"severity": "CRITICAL", "status": "DISMISSED"},
        {"severity": "HIGH", "status": "RESOLVED"},
    ]
    score = calculate_optimal_score(anomalies)
    assert score == 100


def test_score_09_not_clamped_to_zero_can_go_negative():
    """6 Critical anomalies -> 100 - (6 * 20) = -20% (intentional, NOT clamped to 0)."""
    anomalies = [{"severity": "CRITICAL", "status": "OPEN"} for _ in range(6)]
    score = calculate_optimal_score(anomalies)
    assert score == -20


def test_score_10_resolving_immediately_restores_score(db_session, seed_bug_test_data):
    """Resolving an anomaly immediately restores its penalty in DB query."""
    org_id = seed_bug_test_data["org_id"]
    a1 = AnomalyRecord(organisation_id=org_id, metric="energy", value=150.0, severity="CRITICAL", status="OPEN")
    a2 = AnomalyRecord(organisation_id=org_id, metric="energy", value=130.0, severity="HIGH", status="OPEN")
    db_session.add_all([a1, a2])
    db_session.commit()

    active = db_session.query(AnomalyRecord).filter(
        AnomalyRecord.organisation_id == org_id,
        AnomalyRecord.status.in_(["OPEN", "ACKNOWLEDGED"]),
    ).all()
    score_initial = calculate_optimal_score(active)
    assert score_initial == 70  # 100 - 20 - 10

    # Resolve a1
    a1.status = "RESOLVED"
    db_session.commit()

    active_after = db_session.query(AnomalyRecord).filter(
        AnomalyRecord.organisation_id == org_id,
        AnomalyRecord.status.in_(["OPEN", "ACKNOWLEDGED"]),
    ).all()
    score_after = calculate_optimal_score(active_after)
    assert score_after == 90  # 100 - 10


def test_score_11_dashboard_summary_returns_optimal_score(client, auth_headers, seed_bug_test_data):
    """GET /dashboard/{org_id} includes dynamic optimal_score and active_anomaly_count."""
    headers = auth_headers("admina@test.com", "ADMIN", "ORG-TEST-A")
    res = client.get("/api/v1/dashboard/ORG-TEST-A", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "optimal_score" in data
    assert "active_anomaly_count" in data
    assert isinstance(data["optimal_score"], int)
