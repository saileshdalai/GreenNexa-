"""
GreenNexa — Regression Tests for the Final Implementation Pass.

Covers:
  * Municipality ward-level scoping for natural-location modules.
  * Non-municipality natural-location modules falling back to org level.
  * ward_id propagation onto AnomalyRecord for ward-scoped anomalies.
  * Demo Mode scenario scheduling cadence (first ~30-40s, then 60-120s).
  * Single-anomaly-per-cycle invariant under Demo Mode.
  * demo_mode status flag on start/stop.
  * run_cycle_for_org producing ward-level readings.
"""

import random
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.sensor_catalog import SENSOR_CATALOG_MAP
from app.db.models import (
    AnomalyRecord,
    FacilityBlock,
    MunicipalityWard,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
)
from app.services.synthetic_simulator import SyntheticDataSimulator

NATURAL_SENSORS = {"traffic", "parking", "street_lighting"}
BLOCK_SENSORS = {"energy", "water", "waste"}
WHOLE_ORG_SENSORS = {"air_quality"}


@pytest.fixture(autouse=True)
def reset_simulator_state():
    """Ensure the global simulator instance is stopped and reset around each test."""
    from app.services.synthetic_simulator import simulator_instance

    simulator_instance.stop()
    simulator_instance._last_anomaly_times.clear()
    yield
    simulator_instance.stop()
    simulator_instance._last_anomaly_times.clear()


@pytest.fixture
def municipality_org_setup(db_session: Session):
    """Municipality with 2 blocks and 2 active civic wards."""
    org_id = "ORG-MUNI-REG-01"
    db_session.query(MunicipalityWard).filter(MunicipalityWard.municipality_id == org_id).delete()
    db_session.query(FacilityBlock).filter(FacilityBlock.organisation_id == org_id).delete()
    db_session.query(OrganisationSensorConfig).filter(OrganisationSensorConfig.organisation_id == org_id).delete()
    db_session.query(Organisation).filter(Organisation.id == org_id).delete()
    db_session.commit()

    org = Organisation(
        id=org_id,
        name="Regression Municipality",
        org_type="Municipality",
        city="Bhubaneswar",
        state="Odisha",
        is_active=True,
    )
    db_session.add(org)
    db_session.add_all([
        FacilityBlock(block_id="BLK-001", organisation_id=org_id, block_name="Office A", is_active=True),
        FacilityBlock(block_id="BLK-002", organisation_id=org_id, block_name="Office B", is_active=True),
        MunicipalityWard(municipality_id=org_id, ward_number="11", ward_name="Ward 11", is_active=True),
        MunicipalityWard(municipality_id=org_id, ward_number="12", ward_name="Ward 12", is_active=True),
    ])
    cfg = OrganisationSensorConfig(
        organisation_id=org_id,
        data_source="synthetic",
        is_active=True,
    )
    cfg.set_enabled_sensors(["energy", "water", "waste", "traffic", "parking", "street_lighting", "air_quality"])
    db_session.add(cfg)
    db_session.commit()
    return {"org_id": org_id, "blocks": ["BLK-001", "BLK-002"], "wards": ["11", "12"]}


@pytest.fixture
def hospital_block_org_setup(db_session: Session):
    """Non-municipality org with blocks (natural modules must stay org-level)."""
    org_id = "ORG-HOSP-REG-01"
    db_session.query(FacilityBlock).filter(FacilityBlock.organisation_id == org_id).delete()
    db_session.query(OrganisationSensorConfig).filter(OrganisationSensorConfig.organisation_id == org_id).delete()
    db_session.query(Organisation).filter(Organisation.id == org_id).delete()
    db_session.commit()

    org = Organisation(id=org_id, name="Regression Hospital", org_type="Hospital", is_active=True)
    db_session.add(org)
    db_session.add_all([
        FacilityBlock(block_id="BLK-001", organisation_id=org_id, block_name="Block A", is_active=True),
        FacilityBlock(block_id="BLK-002", organisation_id=org_id, block_name="Block B", is_active=True),
    ])
    cfg = OrganisationSensorConfig(organisation_id=org_id, data_source="synthetic", is_active=True)
    cfg.set_enabled_sensors(["energy", "water", "traffic", "air_quality"])
    db_session.add(cfg)
    db_session.commit()
    return {"org_id": org_id, "blocks": ["BLK-001", "BLK-002"]}


def _zero_anomaly_probabilities(sim: SyntheticDataSimulator) -> None:
    """Disable the natural probability path (including the 0.03 fallback)."""
    sim.DEFAULT_ANOMALY_PROBABILITIES = {k: 0.0 for k in SENSOR_CATALOG_MAP.keys()}


# ---------------------------------------------------------------------------
# Ward / location scoping
# ---------------------------------------------------------------------------
def test_municipality_ward_scoping_on_cycle(db_session: Session, municipality_org_setup):
    """Natural-location modules are generated per ward; block-wise per block; whole-org once."""
    org_id = municipality_org_setup["org_id"]
    sim = SyntheticDataSimulator()
    readings = sim.run_cycle(db_session, current_time=datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc))

    natural = [r for r in readings if r.sensor_type in NATURAL_SENSORS]
    blockwise = [r for r in readings if r.sensor_type in BLOCK_SENSORS]
    whole = [r for r in readings if r.sensor_type in WHOLE_ORG_SENSORS]

    # 2 wards x 3 natural sensors
    assert len(natural) == 6
    assert {r.ward_id for r in natural} == {"11", "12"}
    assert all(r.block_id is None for r in natural)

    # 2 blocks x 3 block sensors
    assert len(blockwise) == 6
    assert {r.block_id for r in blockwise} == {"BLK-001", "BLK-002"}
    assert all(r.ward_id is None for r in blockwise)

    # single whole-org reading
    assert len(whole) == 1
    assert whole[0].ward_id is None and whole[0].block_id is None


def test_non_municipality_natural_location_is_org_scoped(db_session: Session, hospital_block_org_setup):
    """Without wards, natural-location modules fall back to org-level (never blocks)."""
    sim = SyntheticDataSimulator()
    readings = sim.run_cycle(db_session, current_time=datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc))

    natural = [r for r in readings if r.sensor_type in {"traffic"}]
    assert len(natural) == 1
    assert natural[0].ward_id is None
    assert natural[0].block_id is None


def test_ward_scoped_anomaly_copies_ward_id_to_record(db_session: Session, municipality_org_setup):
    """A forced ward-scoped anomaly sets ward_id on the reading and its AnomalyRecord."""
    org_id = municipality_org_setup["org_id"]
    sim = SyntheticDataSimulator()
    readings = sim.run_cycle(
        db_session,
        current_time=datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc),
        forced_anomaly_sensor="traffic",
    )

    anomaly_readings = [r for r in readings if r.sensor_type == "traffic" and r.is_anomaly]
    assert len(anomaly_readings) == 1
    anom_reading = anomaly_readings[0]
    assert anom_reading.ward_id in {"11", "12"}
    assert anom_reading.block_id is None

    records = db_session.query(AnomalyRecord).filter(
        AnomalyRecord.organisation_id == org_id,
        AnomalyRecord.metric == "traffic",
    ).all()
    assert len(records) == 1
    assert records[0].ward_id == anom_reading.ward_id
    assert records[0].block_id is None


# ---------------------------------------------------------------------------
# Demo Mode scenario scheduling
# ---------------------------------------------------------------------------
def test_demo_scheduler_cadence_and_single_anomaly(db_session: Session, municipality_org_setup):
    """Demo anomalies: one per completed 30s cycle — exactly one, never mid-cycle, ward-scoped."""
    org_id = municipality_org_setup["org_id"]
    sim = SyntheticDataSimulator(interval_seconds=30)
    _zero_anomaly_probabilities(sim)

    t0 = datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc)
    # Prime a normal cycle so the demo schedule is created on the next demo cycle.
    sim.run_cycle(db_session, current_time=t0)

    sim._demo_orgs.add(org_id)
    random.seed(7)

    fires = []  # (step_index, sensor_type, location)
    step_seconds = 5
    for i in range(140):
        t = t0 + timedelta(seconds=40 + i * step_seconds)
        readings = sim.run_cycle(db_session, current_time=t)
        anomalies = [r for r in readings if r.is_anomaly]
        for r in anomalies:
            fires.append((i, r.sensor_type, r.ward_id or r.block_id or "org"))

    assert len(fires) >= 2, "expected multiple demo anomalies within the observation window"

    # The demo schedule is primed by its first completed cycle (no anomaly),
    # then ONE scenario anomaly fires on every subsequent 30s boundary.
    gaps = [fires[i][0] - fires[i - 1][0] for i in range(1, len(fires))]
    assert gaps and all(g == 6 for g in gaps), f"demo cadence must be exactly 30s (6 steps of 5s): gaps {gaps}"

    # At most one major anomaly per cycle.
    from collections import Counter
    per_cycle = Counter(f[0] for f in fires)
    assert max(per_cycle.values()) == 1

    # Municipality demo scenarios must include at least one ward-targeted anomaly.
    assert any(f[2] in {"11", "12"} for f in fires), "expected a ward-scoped demo anomaly"


def test_demo_mode_status_flag():
    """start(demo_mode=True) exposes demo_mode via status; stop clears it."""
    sim = SyntheticDataSimulator()
    sim.start(interval_seconds=99999, demo_mode=True)
    try:
        assert sim.status()["demo_mode"] is True
    finally:
        sim.stop()
    assert sim.status()["demo_mode"] is False


# ---------------------------------------------------------------------------
# run_cycle_for_org
# ---------------------------------------------------------------------------
def test_run_cycle_for_org_generates_ward_readings(db_session: Session, municipality_org_setup):
    """run_cycle_for_org honours ward scoping for a single municipality."""
    org_id = municipality_org_setup["org_id"]
    sim = SyntheticDataSimulator()
    readings = sim.run_cycle_for_org(db_session, org_id, ignore_gap=True)

    natural = [r for r in readings if r.sensor_type in NATURAL_SENSORS]
    assert natural, "expected natural-location readings"
    assert {r.ward_id for r in natural} == {"11", "12"}
    assert all(r.block_id is None for r in natural)
