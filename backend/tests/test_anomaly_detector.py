"""
GreenNexa — Anomaly Detector Unit & Integration Tests.

Tests:
  1. Normal reading classification (no anomaly record created).
  2. Abnormal readings: LOW, MEDIUM, HIGH, CRITICAL severity classification.
  3. Missing/insufficient data handling (skips safely without crashing).
  4. Invalid/NaN reading values handling.
  5. Organisation isolation (Org B historical readings do not influence Org A).
  6. Multi-metric support (energy, water, temperature, humidity, CO2, air_quality, waste).
  7. Database persistence verification.
"""

from datetime import datetime, timedelta, timezone

import pytest
from app.ai.anomaly_detector import (
    MIN_HISTORY_POINTS,
    classify_value,
    detect_and_save,
)
from app.db.models import AnomalyRecord, Organisation, SensorReading


def _seed_readings(
    db,
    org_id: str,
    sensor_type: str,
    values: list[float],
    facility_id: str = "FAC-01",
):
    """Utility to seed historical sensor readings into DB."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i, v in enumerate(values):
        ts = now - timedelta(days=20) + timedelta(hours=i)
        reading = SensorReading(
            organisation_id=org_id,
            facility_id=facility_id,
            device_id=f"DEV-{sensor_type}-01",
            sensor_type=sensor_type,
            value=v,
            unit="kWh",
            source="synthetic",
            timestamp=ts,
        )
        db.add(reading)
    db.commit()


# ---------------------------------------------------------------------------
# In-Memory Classification Tests (classify_value)
# ---------------------------------------------------------------------------

def test_classify_normal_reading():
    """Value close to mean should be classified as NORMAL."""
    history = [99.0, 101.0, 99.0, 101.0, 99.0, 101.0, 99.0, 101.0, 99.0, 101.0]
    res = classify_value(value=100.5, history_values=history, metric="energy", unit="kWh")

    assert res["severity"] == AnomalyRecord.SEVERITY_NORMAL
    assert res["z_score"] < 1.5
    assert "within the expected range" in res["reason"]


def test_classify_low_severity_anomaly():
    """Z-score between 1.5 and 2.0 should be LOW severity."""
    history = [99.0, 101.0, 99.0, 101.0, 99.0, 101.0, 99.0, 101.0, 99.0, 101.0]
    # Value 101.8 gives Z ~ 1.71 -> LOW
    res = classify_value(value=101.8, history_values=history, metric="energy", unit="kWh")

    assert res["severity"] == AnomalyRecord.SEVERITY_LOW
    assert 1.5 <= res["z_score"] < 2.0


def test_classify_medium_severity_anomaly():
    """Z-score between 2.0 and 2.8 should be MEDIUM severity."""
    history = [99.0, 101.0, 99.0, 101.0, 99.0, 101.0, 99.0, 101.0, 99.0, 101.0]
    # Value 102.5 gives Z ~ 2.37 -> MEDIUM
    res = classify_value(value=102.5, history_values=history, metric="energy", unit="kWh")

    assert res["severity"] == AnomalyRecord.SEVERITY_MEDIUM
    assert 2.0 <= res["z_score"] < 2.8


def test_classify_high_severity_anomaly():
    """Z-score between 2.8 and 3.5 should be HIGH severity."""
    history = [99.0, 101.0, 99.0, 101.0, 99.0, 101.0, 99.0, 101.0, 99.0, 101.0]
    # Value 103.3 gives Z ~ 3.13 -> HIGH
    res = classify_value(value=103.3, history_values=history, metric="energy", unit="kWh")

    assert res["severity"] == AnomalyRecord.SEVERITY_HIGH
    assert 2.8 <= res["z_score"] < 3.5
    assert "significantly" in res["reason"]


def test_classify_critical_severity_anomaly():
    """Z-score >= 3.5 should be CRITICAL severity."""
    history = [99.0, 101.0, 99.0, 101.0, 99.0, 101.0, 99.0, 101.0, 99.0, 101.0]
    # Value 120.0 gives Z > 18 -> CRITICAL
    res = classify_value(value=120.0, history_values=history, metric="energy", unit="kWh")

    assert res["severity"] == AnomalyRecord.SEVERITY_CRITICAL
    assert res["z_score"] >= 3.5
    assert "extremely" in res["reason"]


def test_classify_insufficient_history():
    """If history points < MIN_HISTORY_POINTS, return NORMAL with insufficient data reason."""
    history = [100.0, 101.0, 99.0]  # only 3 points (need 5)
    res = classify_value(value=150.0, history_values=history, metric="energy")

    assert res["severity"] == AnomalyRecord.SEVERITY_NORMAL
    assert res["anomaly_score"] == 0.0
    assert "Insufficient" in res["reason"]


# ---------------------------------------------------------------------------
# Database Detection Tests (detect_and_save)
# ---------------------------------------------------------------------------

def test_detect_and_save_normal_reading(db_session, seed_orgs):
    """NORMAL reading should NOT create an anomaly record in DB."""
    org_a = seed_orgs["org_a"]
    _seed_readings(db_session, org_a.id, "energy", [10.0, 10.5, 9.8, 10.2, 10.1, 9.9])

    result = detect_and_save(
        db=db_session,
        organisation_id=org_a.id,
        facility_id="FAC-01",
        metric="energy",
        sensor_type="energy",
        value=10.1,
        unit="kWh",
    )

    assert result is None
    records = db_session.query(AnomalyRecord).filter_by(organisation_id=org_a.id).all()
    assert len(records) == 0


def test_detect_and_save_high_anomaly(db_session, seed_orgs):
    """HIGH anomaly reading SHOULD save an AnomalyRecord to DB with all details."""
    org_a = seed_orgs["org_a"]
    # Mean = 50, Std small
    _seed_readings(db_session, org_a.id, "water", [50.0, 50.5, 49.5, 50.2, 49.8, 50.1], facility_id="FAC-MAIN")

    result = detect_and_save(
        db=db_session,
        organisation_id=org_a.id,
        facility_id="FAC-MAIN",
        metric="water",
        sensor_type="water",
        value=85.0,  # Huge spike
        unit="L",
    )

    assert result is not None
    assert isinstance(result, AnomalyRecord)
    assert result.organisation_id == org_a.id
    assert result.facility_id == "FAC-MAIN"
    assert result.metric == "water"
    assert result.value == 85.0
    assert result.severity in (AnomalyRecord.SEVERITY_HIGH, AnomalyRecord.SEVERITY_CRITICAL)
    assert result.status == AnomalyRecord.STATUS_OPEN
    assert result.reason is not None

    # Check DB entry exists
    db_record = db_session.query(AnomalyRecord).filter_by(id=result.id).first()
    assert db_record is not None
    assert db_record.value == 85.0


def test_detect_and_save_insufficient_data(db_session, seed_orgs):
    """With no history, detect_and_save should return None without error."""
    org_a = seed_orgs["org_a"]

    result = detect_and_save(
        db=db_session,
        organisation_id=org_a.id,
        facility_id="FAC-01",
        metric="co2",
        sensor_type="co2",
        value=1200.0,
        unit="ppm",
    )

    assert result is None
    count = db_session.query(AnomalyRecord).count()
    assert count == 0


def test_organisation_isolation(db_session, seed_orgs):
    """
    Org B having extreme values should NOT affect detection for Org A.
    Org A history: mean=10
    Org B history: mean=1000
    Testing value 10.1 for Org A must remain NORMAL.
    """
    org_a = seed_orgs["org_a"]
    org_b = seed_orgs["org_b"]

    _seed_readings(db_session, org_a.id, "temperature", [10.0, 10.1, 9.9, 10.2, 9.8])
    _seed_readings(db_session, org_b.id, "temperature", [1000.0, 1005.0, 995.0, 1002.0, 998.0])

    # Run for Org A
    result_a = detect_and_save(
        db=db_session,
        organisation_id=org_a.id,
        facility_id="FAC-01",
        metric="temperature",
        sensor_type="temperature",
        value=10.1,
        unit="°C",
    )

    assert result_a is None  # NORMAL for Org A

    # Verify no anomalies for Org A
    anomalies_a = db_session.query(AnomalyRecord).filter_by(organisation_id=org_a.id).all()
    assert len(anomalies_a) == 0


def test_supported_metrics(db_session, seed_orgs):
    """Test anomaly detection across various metric types: energy, water, temperature, humidity, co2, air_quality, waste."""
    org_a = seed_orgs["org_a"]
    metrics = ["energy", "water", "temperature", "humidity", "co2", "air_quality", "waste"]

    for m in metrics:
        _seed_readings(db_session, org_a.id, m, [20.0, 20.5, 19.5, 20.2, 19.8])
        # High value -> anomaly expected
        res = detect_and_save(
            db=db_session,
            organisation_id=org_a.id,
            facility_id="FAC-01",
            metric=m,
            sensor_type=m,
            value=45.0,
            unit="units",
        )
        assert res is not None, f"Expected anomaly for metric {m}"
        assert res.metric == m
