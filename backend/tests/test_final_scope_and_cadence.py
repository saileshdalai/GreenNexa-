"""
GreenNexa — Final Scope, Cadence and Location-Isolation Regression Tests.

Covers the root causes fixed in the final pass:
  * 30s Demo cadence is start-to-start (no interval + processing drift, no
    catch-up burst when a cycle runs long).
  * A SCOPED stop (one organisation leaving demo mode) never tears down the
    shared simulator worker or another organisation's demo state.
  * Cumulative metrics (energy/water) progress per PHYSICAL LOCATION: a ward
    never inherits another ward's accumulator just because both carry
    block_id = None.
  * Anomaly ML history is scoped to the exact ward, not every ward.
  * A normal reading never auto-resolves an open anomaly.
"""

import time as _time_mod
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    MunicipalityWard,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
)
from app.services.synthetic_simulator import SyntheticDataSimulator

T0 = datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def reset_simulator_state():
    """Keep the module-level singleton stopped and stateless around each test."""
    from app.services.synthetic_simulator import simulator_instance

    simulator_instance.stop()
    simulator_instance._last_anomaly_times.clear()
    simulator_instance._last_cumulative_values.clear()
    yield
    simulator_instance.stop()
    simulator_instance._last_anomaly_times.clear()
    simulator_instance._last_cumulative_values.clear()


def _municipality(db_session: Session, org_id: str, sensors, wards=("1", "2"), blocks=("BLK-OWN",)) -> Organisation:
    db_session.add(Organisation(id=org_id, name="Scope Muni", org_type="Municipality", is_active=True))
    for b in blocks:
        db_session.add(FacilityBlock(block_id=b, organisation_id=org_id, block_name=b, is_active=True))
    for w in wards:
        db_session.add(
            MunicipalityWard(municipality_id=org_id, ward_number=w, ward_name=f"Ward {w}", is_active=True)
        )
    cfg = OrganisationSensorConfig(
        organisation_id=org_id,
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        is_active=True,
    )
    cfg.set_enabled_sensors(list(sensors))
    db_session.add(cfg)
    db_session.commit()
    return db_session.query(Organisation).filter(Organisation.id == org_id).first()


# ---------------------------------------------------------------------------
# 1. 30s cadence is start-to-start, not interval + processing time
# ---------------------------------------------------------------------------
class _FakeStopEvent:
    def __init__(self):
        self._set = False

    def is_set(self) -> bool:
        return self._set

    def set(self) -> None:
        self._set = True

    def clear(self) -> None:
        self._set = False

    def wait(self, timeout: float) -> bool:
        # Advance the fake clock instead of really sleeping, then report "not set"
        # so the loop keeps going until the test stops it.
        _FAKE.clock[0] += max(0.0, float(timeout))
        return False


class _FakeClock:
    def __init__(self):
        self.clock = [0.0]

    def monotonic(self) -> float:
        return self.clock[0]

    def tick(self, seconds: float) -> None:
        self.clock[0] += seconds


_FAKE = _FakeClock()


@pytest.mark.parametrize(
    "processing_seconds, exact_step",
    [
        (0.0, 30.0),   # instant cycle -> exactly 30s apart
        (5.0, 30.0),   # cycle faster than the interval -> still exactly 30s apart
    ],
)
def test_worker_loop_cadence_is_start_to_start(monkeypatch, processing_seconds, exact_step):
    """A 30s interval means cycle starts 30s apart, regardless of processing time."""
    sim = SyntheticDataSimulator(interval_seconds=30)
    _FAKE.clock = [0.0]
    monkeypatch.setattr(_time_mod, "monotonic", lambda: _FAKE.clock[0])
    monkeypatch.setattr(sim, "_stop_event", _FakeStopEvent())

    starts: list[float] = []

    def _fake_cycle() -> list:
        starts.append(_FAKE.clock[0])
        if len(starts) >= 6:
            sim._stop_event.set()
        _FAKE.tick(processing_seconds)
        return []

    monkeypatch.setattr(sim, "run_cycle_with_session", _fake_cycle)

    sim._worker_loop()

    assert len(starts) == 6
    steps = [b - a for a, b in zip(starts, starts[1:])]
    assert steps == [exact_step] * 5, f"cadence drifted: {steps}"


def test_worker_loop_never_bursts_when_cycle_overruns_interval(monkeypatch):
    """A cycle slower than the interval must not trigger catch-up bursts.

    When a cycle overruns its slot the loop keeps feeding data (it cannot run
    faster than the work itself), but it must never fire back-to-back cycles to
    "make up" missed boundaries — that would break exactly-one-anomaly-per-cycle.
    """
    sim = SyntheticDataSimulator(interval_seconds=30)
    _FAKE.clock = [0.0]
    monkeypatch.setattr(_time_mod, "monotonic", lambda: _FAKE.clock[0])
    monkeypatch.setattr(sim, "_stop_event", _FakeStopEvent())

    starts: list[float] = []

    def _fake_cycle() -> list:
        starts.append(_FAKE.clock[0])
        if len(starts) >= 6:
            sim._stop_event.set()
        _FAKE.tick(70.0)  # each cycle takes longer than the 30s interval
        return []

    monkeypatch.setattr(sim, "run_cycle_with_session", _fake_cycle)

    sim._worker_loop()

    steps = [b - a for a, b in zip(starts, starts[1:])]
    assert len(starts) == 6
    assert all(s >= 30.0 for s in steps), f"catch-up burst detected: {steps}"
    # 6 cycles x 70s of work can never fit into fewer than 350s of wall clock.
    assert starts[-1] - starts[0] >= 350.0


# ---------------------------------------------------------------------------
# 2. Scoped stop never tears down the shared worker
# ---------------------------------------------------------------------------
def test_scoped_stop_keeps_worker_and_other_orgs_alive():
    sim = SyntheticDataSimulator(interval_seconds=30)
    assert sim.start(demo_mode=True, organisation_id="ORG-A")["status"] == "started"
    assert sim.start(demo_mode=True, organisation_id="ORG-B")["status"] == "already_running"
    assert sim._demo_active_for("ORG-A") is True
    assert sim._demo_active_for("ORG-B") is True

    sim._demo_schedules["ORG-A"] = {"next_trigger_at": T0, "scenario_index": 0}
    sim._demo_schedules["ORG-B"] = {"next_trigger_at": T0, "scenario_index": 0}

    # ORG-A leaves the demo scope.
    result = sim.stop(organisation_id="ORG-A")
    assert result["status"] == "scoped_stopped"
    assert sim.is_running is True, "shared worker must survive a scoped stop"
    assert sim._demo_active_for("ORG-A") is False
    assert sim._demo_active_for("ORG-B") is True, "ORG-B demo scope must be untouched"
    assert "ORG-A" not in sim._demo_schedules
    assert "ORG-B" in sim._demo_schedules

    # Status stays honest for both scopes.
    assert sim.status(organisation_id="ORG-A")["demo_mode"] is False
    assert sim.status(organisation_id="ORG-B")["demo_mode"] is True

    # Last org leaving the demo scope also must not kill the worker.
    sim.stop(organisation_id="ORG-B")
    assert sim.is_running is True, "worker must not die when demo scope empties"

    # Only a full stop tears the worker down.
    assert sim.stop()["status"] == "stopped"
    assert sim.is_running is False


# ---------------------------------------------------------------------------
# 3. Cumulative metrics are tracked per physical location
# ---------------------------------------------------------------------------
def _energy_baseline() -> float:
    from app.core.sensor_catalog import SENSOR_CATALOG_MAP

    return float(SENSOR_CATALOG_MAP["energy"]["default_baseline"])


def test_cumulative_energy_is_isolated_per_ward(db_session: Session):
    """Every ward starts from the baseline instead of inheriting the previous ward."""
    org = _municipality(db_session, "ORG-CUM-1", ["energy"], wards=("1", "2"), blocks=())
    baseline = _energy_baseline()
    sim = SyntheticDataSimulator()
    sim._demo_orgs.add(org.id)  # demo active -> energy is generated per ward

    sim.run_cycle(db_session, current_time=T0)

    first = {
        r.ward_id: r.value
        for r in db_session.query(SensorReading).filter(
            SensorReading.organisation_id == org.id,
            SensorReading.sensor_type == "energy",
            SensorReading.timestamp == T0,
        )
        if r.ward_id in ("1", "2")
    }
    assert set(first) == {"1", "2"}
    # Both wards start at the configured baseline on their first reading.
    assert first["1"] == first["2"] == baseline, f"wards share a counter: {first}"

    # The second cycle advances each ward independently.
    sim.run_cycle(db_session, current_time=T0 + timedelta(seconds=30))
    second = {
        r.ward_id: r.value
        for r in db_session.query(SensorReading).filter(
            SensorReading.organisation_id == org.id,
            SensorReading.sensor_type == "energy",
            SensorReading.timestamp == T0 + timedelta(seconds=30),
        )
        if r.ward_id in ("1", "2")
    }
    assert second["1"] > baseline
    assert second["2"] > baseline

    # Each ward keeps its own accumulator key.
    keys = set(sim._last_cumulative_values)
    assert (org.id, None, "1", "energy") in keys
    assert (org.id, None, "2", "energy") in keys


def test_ward_cumulative_history_does_not_leak_from_other_wards(db_session: Session):
    """A ward's first reading must not resume from another ward's last value."""
    org = _municipality(db_session, "ORG-CUM-2", ["energy"], wards=("1", "2"), blocks=())
    baseline = _energy_baseline()
    sim = SyntheticDataSimulator()
    sim._demo_orgs.add(org.id)

    # Pre-seed a long history on ward 1 only.
    t = T0 - timedelta(hours=2)
    for i in range(10):
        db_session.add(
            SensorReading(
                organisation_id=org.id,
                ward_id="1",
                sensor_type="energy",
                value=500.0 + i,
                unit="kWh",
                source="synthetic",
                timestamp=t + timedelta(minutes=10 * i),
            )
        )
    db_session.commit()
    sim._last_cumulative_values.clear()

    sim.run_cycle(db_session, current_time=T0)
    rows = {
        r.ward_id: r.value
        for r in db_session.query(SensorReading).filter(
            SensorReading.organisation_id == org.id,
            SensorReading.sensor_type == "energy",
            SensorReading.timestamp == T0,
        )
        if r.ward_id in ("1", "2")
    }
    assert rows["1"] > 500.0, "ward 1 must resume from its own history"
    assert rows["2"] == baseline, f"ward 2 must start from baseline, not ward 1's history: {rows}"


# ---------------------------------------------------------------------------
# 4. Anomaly ML history is scoped to the exact ward
# ---------------------------------------------------------------------------
def test_anomaly_history_is_scoped_to_the_exact_ward(db_session: Session, monkeypatch):
    from app.services.anomaly_ml_service import anomaly_ml_service
    from app.services.anomaly_detection import anomaly_detection_service

    muni = _municipality(db_session, "ORG-HIST-1", ["energy"], wards=("1", "2"), blocks=())
    t = T0 - timedelta(hours=1)
    for i in range(5):
        db_session.add(
            SensorReading(
                organisation_id=muni.id, ward_id="1", sensor_type="energy",
                value=100.0, unit="kWh", source="synthetic",
                timestamp=t + timedelta(minutes=10 * i),
            )
        )
        db_session.add(
            SensorReading(
                organisation_id=muni.id, ward_id="2", sensor_type="energy",
                value=9000.0, unit="kWh", source="synthetic",
                timestamp=t + timedelta(minutes=10 * i),
            )
        )
    db_session.commit()

    captured: dict = {}
    real_evaluate = anomaly_ml_service.evaluate_reading

    def _spy(**kwargs):
        captured.setdefault("history", []).append(list(kwargs.get("history_values") or []))
        return real_evaluate(**kwargs)

    monkeypatch.setattr(anomaly_ml_service, "evaluate_reading", _spy)

    reading = SensorReading(
        organisation_id=muni.id, ward_id="1", sensor_type="energy",
        value=150.0, unit="kWh", source="synthetic", timestamp=T0, is_anomaly=True,
    )
    db_session.add(reading)
    db_session.commit()

    anomaly_detection_service.process_single_reading(db_session, reading)

    assert captured["history"], "ML evaluation never ran"
    for history in captured["history"]:
        assert 9000.0 not in history, f"ward 2 history leaked into ward 1: {history}"


# ---------------------------------------------------------------------------
# 5. Open anomalies are never auto-resolved by a later normal reading
# ---------------------------------------------------------------------------
def test_normal_reading_does_not_auto_resolve_open_anomaly(db_session: Session):
    org = _municipality(db_session, "ORG-AUTORES-1", ["energy", "waste"], wards=("1",), blocks=("BLK-OWN",))
    sim = SyntheticDataSimulator()
    sim._demo_orgs.add(org.id)
    sim._demo_schedules[org.id] = {"next_trigger_at": T0, "scenario_index": 1}  # Waste Overflow

    sim.run_cycle(db_session, current_time=T0)
    opened = (
        db_session.query(AnomalyRecord)
        .filter(AnomalyRecord.organisation_id == org.id, AnomalyRecord.metric == "waste")
        .all()
    )
    assert opened, "waste scenario anomaly must persist"
    assert all(a.status == AnomalyRecord.STATUS_OPEN for a in opened)

    # Several more cycles produce normal (<100%) waste readings.
    for step in range(2, 6):
        sim.run_cycle(db_session, current_time=T0 + timedelta(seconds=30 * step))

    still_open = (
        db_session.query(AnomalyRecord)
        .filter(AnomalyRecord.organisation_id == org.id, AnomalyRecord.metric == "waste")
        .all()
    )
    assert still_open, "anomalies must never be deleted by later cycles"
    assert all(a.status == AnomalyRecord.STATUS_OPEN for a in still_open), (
        "open anomalies must stay OPEN until an explicit RESOLVE/DISMISS"
    )
    assert all(a.resolved_at is None for a in still_open)
    linked = (
        db_session.query(AIRecommendation)
        .filter(AIRecommendation.organisation_id == org.id)
        .count()
    )
    assert linked >= 1, "linked recommendation must survive a normal reading"
