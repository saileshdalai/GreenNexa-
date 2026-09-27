"""
GreenNexa — AI Recommendation Engine Unit & Integration Tests.

Tests:
  1. NORMAL severity -> No recommendation generated.
  2. MEDIUM energy anomaly -> Hedged recommendation with "Consider checking...", "Possible cause...".
  3. HIGH energy anomaly -> Comprehensive hedged actions including HVAC, lighting, electrical loads.
  4. Insufficient data -> `data_sufficient=False`, explicit notification, NO fake recommendation invented.
  5. Language hedging validation -> Asserts NO unverified definitive cause statements (e.g. "The cause is...").
  6. Persistent storage -> Recommendation saved to DB with anomaly_id relation.
  7. Preview generation (generate_without_saving).
  8. Organisation isolation -> Recommendations scoped strictly to organisation_id.
"""

import pytest
from app.ai.anomaly_detector import detect_and_save
from app.ai.recommender import (
    CONFIDENCE_NOTE,
    generate_and_save,
    generate_without_saving,
)
from app.db.models import AIRecommendation, AnomalyRecord, SensorReading
from tests.test_anomaly_detector import _seed_readings


def test_normal_anomaly_no_recommendation(db_session, seed_orgs):
    """NORMAL severity anomaly should return None (no recommendation generated)."""
    org_a = seed_orgs["org_a"]
    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        facility_id="FAC-01",
        metric="energy",
        value=100.0,
        expected_min=90.0,
        expected_max=110.0,
        anomaly_score=0.0,
        severity=AnomalyRecord.SEVERITY_NORMAL,
        reason="Normal reading",
    )
    db_session.add(anomaly)
    db_session.commit()

    rec = generate_and_save(db_session, anomaly)
    assert rec is None


def test_medium_energy_recommendation(db_session, seed_orgs):
    """MEDIUM energy anomaly should generate hedged causes and actions."""
    org_a = seed_orgs["org_a"]
    _seed_readings(db_session, org_a.id, "energy", [100.0, 102.0, 98.0, 101.0, 99.0], facility_id="FAC-MAIN")

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        facility_id="FAC-MAIN",
        metric="energy",
        sensor_type="energy",
        value=135.0,
        expected_min=95.0,
        expected_max=105.0,
        anomaly_score=0.6,
        severity=AnomalyRecord.SEVERITY_MEDIUM,
        reason="Medium energy spike",
    )
    db_session.add(anomaly)
    db_session.commit()

    rec = generate_and_save(db_session, anomaly)

    assert rec is not None
    assert isinstance(rec, AIRecommendation)
    assert rec.organisation_id == org_a.id
    assert rec.facility_id == "FAC-MAIN"
    assert rec.anomaly_id == anomaly.id
    assert rec.metric == "energy"
    assert rec.severity == AnomalyRecord.SEVERITY_MEDIUM
    assert rec.data_sufficient is True

    # Check hedged language
    causes = rec.possible_causes_list
    actions = rec.recommended_actions_list

    assert len(causes) > 0
    assert len(actions) > 0

    for cause in causes:
        assert cause.startswith("Possible")

    for action in actions:
        assert action.startswith("Consider") or action.startswith("Recommended action")

    # Check disclaimer included
    assert CONFIDENCE_NOTE in rec.summary
    assert rec.confidence_note == CONFIDENCE_NOTE


def test_high_energy_recommendation(db_session, seed_orgs):
    """
    HIGH energy anomaly scenario:
    "Consider checking HVAC operation, lighting schedules and major electrical loads."
    """
    org_a = seed_orgs["org_a"]
    _seed_readings(db_session, org_a.id, "energy", [100.0, 101.0, 99.0, 100.5, 99.5])

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        facility_id="FAC-01",
        metric="energy",
        sensor_type="energy",
        value=190.0,
        expected_min=95.0,
        expected_max=105.0,
        anomaly_score=0.9,
        severity=AnomalyRecord.SEVERITY_HIGH,
        reason="High energy anomaly detected",
    )
    db_session.add(anomaly)
    db_session.commit()

    rec = generate_and_save(db_session, anomaly)

    assert rec is not None
    assert rec.severity == AnomalyRecord.SEVERITY_HIGH

    actions_text = " ".join(rec.recommended_actions_list)
    # Validate actions address HVAC, lighting, and electrical loads as required by prompt
    assert "HVAC" in actions_text
    assert "lighting" in actions_text.lower()
    assert "electrical load" in actions_text.lower() or "electrical" in actions_text.lower()


def test_insufficient_data_recommendation(db_session, seed_orgs):
    """
    If historical data points < 5, engine must set data_sufficient=False
    and return an explicit notification instead of inventing recommendations.
    """
    org_a = seed_orgs["org_a"]
    # Only 2 historical readings
    _seed_readings(db_session, org_a.id, "water", [50.0, 52.0])

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        facility_id="FAC-01",
        metric="water",
        sensor_type="water",
        value=200.0,
        expected_min=45.0,
        expected_max=55.0,
        anomaly_score=0.95,
        severity=AnomalyRecord.SEVERITY_HIGH,
        reason="High water reading",
    )
    db_session.add(anomaly)
    db_session.commit()

    rec = generate_and_save(db_session, anomaly)

    assert rec is not None
    assert rec.data_sufficient is False
    assert rec.historical_trend == "insufficient_data"
    assert "insufficient historical data is available" in rec.summary.lower()
    assert len(rec.possible_causes_list) == 0  # Does NOT invent fake causes


def test_no_unverified_fact_claims(db_session, seed_orgs):
    """Verify that recommendations NEVER use definitive unverified statements."""
    org_a = seed_orgs["org_a"]
    _seed_readings(db_session, org_a.id, "temperature", [22.0, 22.5, 21.8, 22.1, 21.9])

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        facility_id="FAC-01",
        metric="temperature",
        sensor_type="temperature",
        value=35.0,
        expected_min=20.0,
        expected_max=24.0,
        anomaly_score=0.85,
        severity=AnomalyRecord.SEVERITY_HIGH,
        reason="Temperature spike",
    )
    db_session.add(anomaly)
    db_session.commit()

    rec = generate_and_save(db_session, anomaly)

    forbidden_phrases = [
        "the cause is",
        "due to the fact that",
        "this is caused by",
        "definitely",
        "without a doubt",
    ]
    summary_lower = rec.summary.lower()
    for phrase in forbidden_phrases:
        assert phrase not in summary_lower, f"Forbidden phrase '{phrase}' found in summary!"


def test_generate_without_saving_preview():
    """Test preview recommendation generation without DB dependency."""
    history = [10.0, 10.2, 9.8, 10.1, 9.9, 10.0]
    preview = generate_without_saving(
        anomaly_severity="HIGH",
        metric="water",
        current_value=45.0,
        expected_min=9.0,
        expected_max=11.0,
        history_values=history,
        unit="L",
    )

    assert preview["generated"] is True
    assert preview["data_sufficient"] is True
    assert preview["metric"] == "water"
    assert preview["severity"] == "HIGH"
    assert len(preview["possible_causes"]) > 0
    assert len(preview["recommended_actions"]) > 0
    assert CONFIDENCE_NOTE in preview["summary"]


def test_recommender_org_isolation(db_session, seed_orgs):
    """Ensure AI recommendations are strictly bound to their organisation_id."""
    org_a = seed_orgs["org_a"]
    org_b = seed_orgs["org_b"]

    _seed_readings(db_session, org_a.id, "co2", [400.0, 410.0, 390.0, 405.0, 395.0])
    _seed_readings(db_session, org_b.id, "co2", [1000.0, 1010.0, 990.0, 1005.0, 995.0])

    anomaly_a = AnomalyRecord(
        organisation_id=org_a.id,
        facility_id="FAC-A",
        metric="co2",
        sensor_type="co2",
        value=1500.0,
        expected_min=380.0,
        expected_max=420.0,
        anomaly_score=0.9,
        severity=AnomalyRecord.SEVERITY_HIGH,
        reason="CO2 spike in Org A",
    )
    db_session.add(anomaly_a)
    db_session.commit()

    rec_a = generate_and_save(db_session, anomaly_a)

    assert rec_a.organisation_id == org_a.id

    # Verify query by org_b returns nothing
    recs_b = db_session.query(AIRecommendation).filter_by(organisation_id=org_b.id).all()
    assert len(recs_b) == 0

    recs_a = db_session.query(AIRecommendation).filter_by(organisation_id=org_a.id).all()
    assert len(recs_a) == 1
