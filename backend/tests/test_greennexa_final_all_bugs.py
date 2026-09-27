"""
GreenNexa — FINAL ALL-BUG Mandatory Regression Suite (45 numbered scenarios).

Maps the 45 mandatory regression scenarios from the FINAL ALL-BUG ROOT-CAUSE
FIX pass to explicit tests:

  1-3    Real-time: 30s cycle persists fresh readings, dashboard "Last Updated",
         recent readings show the newest cycle.
  4-8    Demo scope isolation: only the enrolled organisation changes (TEST A/B).
  9-15   Municipality demo: ward civic data (Energy/Water/Waste/Air Quality),
         correct ward_id, ward detail has_data, ward-scoped anomaly copy.
  16-21  Demo anomaly cadence (EXACTLY ONE per completed 30s cycle, primed on
         first cycle, no mid-cycle duplicates), real pipeline records,
         sewage canonical red-dot, force_new persistence.
  22-23  Priority Engine ranks Critical first; priority inactive below threshold.
  24-26  Ward forecast scoped strictly to ward history; honest empty state.
  27-33  Ward counts never include blocks; add ward creates no block; natural
         modules never use blocks; AQ never uses blocks.
  34-35  Super-admin oversight for any org; municipality own office live data.
  36-37  Aggregation: overall is NOT the highest block, current == latest cycle
         point, peak == historical max >= current.
  38     Ward detail freshness uses the reading's simulated calendar day +
         live time-of-day (sim-clock) so simulated-day data is ONLINE and
         genuinely stale data is OFFLINE.
  39     Civic demo anomalies (street lighting / drainage / pump / rainfall)
         produce ward-scoped AI recommendations.
  40-41  Ward-level unread red dots: /unread exposes wards, mark-read by ward_id
         clears only that ward.
  42     Demo reset clears schedules + round-robin offsets (per-org & all).
  43     Demo ward targets rotate round-robin across cycles.
  44     force_new bypasses anomaly + recommendation dedup; dedup stays intact
         for the natural (non-demo) path.
  45     Demo cadence fires inside the natural 600s anomaly gap; natural
         anomalies are suspended for demo orgs (single anomaly per cycle).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

import pytest
from sqlalchemy.orm import Session

from app.core.aggregation import compute_metric_summary
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    MunicipalityWard,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
    _utcnow,
)
from app.services.anomaly_detection import anomaly_detection_service as anomaly_service
from app.services.synthetic_simulator import (
    SyntheticDataSimulator as SyntheticSimulator,
    simulator_instance,
)

SENSOR_BASELINES = {
    "energy": (1000.0, "kWh"),
    "water": (400.0, "L"),
    "waste": (50.0, "kg"),
    "traffic": (500.0, "veh/h"),
    "parking": (80.0, "%"),
    "street_lighting": (100.0, "%"),
    "air_quality": (55.0, "AQI"),
    "sewage_level": (60.0, "%"),
    "sewage": (60.0, "%"),
    "water_flow": (300.0, "L/s"),
    "water_level": (70.0, "%"),
    "rainfall": (10.0, "mm"),
    "climate": (24.0, "C"),
    "temperature": (24.0, "C"),
    "humidity": (55.0, "%"),
    "roads": (85.0, "score"),
    "parks": (75.0, "score"),
    "safety": (80.0, "score"),
}


@pytest.fixture(autouse=True)
def _deterministic_and_clean():
    """Zero natural anomaly probabilities and isolate steady state per test."""
    saved = dict(SyntheticSimulator.DEFAULT_ANOMALY_PROBABILITIES)
    SyntheticSimulator.DEFAULT_ANOMALY_PROBABILITIES = {k: 0.0 for k in saved}
    simulator_instance.reset_all_simulator_state()
    yield
    simulator_instance.reset_all_simulator_state()
    SyntheticSimulator.DEFAULT_ANOMALY_PROBABILITIES = saved


def _configure_sensors(db: Session, org_id: str, sensors: List[str]) -> OrganisationSensorConfig:
    cfg = (
        db.query(OrganisationSensorConfig)
        .filter(OrganisationSensorConfig.organisation_id == org_id)
        .first()
    )
    if cfg is None:
        cfg = OrganisationSensorConfig(
            organisation_id=org_id,
            data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
            is_active=True,
        )
        db.add(cfg)
    cfg.set_enabled_sensors(list(sensors))
    configs = {}
    for s in sensors:
        base, unit = SENSOR_BASELINES.get(s, (100.0, "units"))
        configs[s] = {
            "baseline": base,
            "warning_threshold": 15.0,
            "critical_threshold": 30.0,
            "unit": unit,
        }
    cfg.set_sensor_configs(configs)
    db.commit()
    return cfg


def _seed_org(
    db: Session,
    org_id: str,
    name: str,
    org_type: str,
    sensors: List[str],
    blocks: tuple = (),
    wards: tuple = (),
) -> Organisation:
    org = Organisation(
        id=org_id,
        name=name,
        org_type=org_type,
        facility_name=f"{name} HQ",
        location="Test City",
        is_active=True,
    )
    db.add(org)
    for b in blocks:
        db.add(
            FacilityBlock(
                block_id=b,
                organisation_id=org_id,
                block_name=b.replace("BLK-", "Block "),
                is_active=True,
            )
        )
    for w in wards:
        db.add(
            MunicipalityWard(
                municipality_id=org_id,
                ward_number=w,
                ward_name=f"Ward {w}",
                is_active=True,
            )
        )
    db.commit()
    _configure_sensors(db, org_id, sensors)
    return org


def _add_reading(
    db: Session,
    org_id: str,
    sensor_type: str,
    value: float,
    ts: datetime,
    block_id: Optional[str] = None,
    ward_id: Optional[str] = None,
    unit: Optional[str] = None,
    is_anomaly: bool = False,
) -> SensorReading:
    r = SensorReading(
        organisation_id=org_id,
        sensor_type=sensor_type,
        value=value,
        unit=unit,
        timestamp=ts,
        block_id=block_id,
        ward_id=ward_id,
        source="synthetic",
        is_anomaly=is_anomaly,
    )
    db.add(r)
    db.commit()
    return r


def _mk_sim() -> SyntheticSimulator:
    return SyntheticSimulator(interval_seconds=30)


def _cycles(sim: SyntheticSimulator, db: Session, ts: datetime, n: int = 2, step_s: int = 30):
    for i in range(n):
        sim.run_cycle(db=db, current_time=ts + timedelta(seconds=i * step_s))


def _count(db: Session, org_id: str, sensor_type: str) -> int:
    return (
        db.query(SensorReading)
        .filter(SensorReading.organisation_id == org_id, SensorReading.sensor_type == sensor_type)
        .count()
    )


def _super_header(auth_headers, organisation_id: str = "ORG-TEST-A") -> dict:
    return auth_headers("finalbugs.super@greennexa.io", User.ROLE_SUPER_ADMIN, organisation_id)


DT0 = datetime(2026, 9, 24, 9, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# 1-3. REAL-TIME 30s CADENCE + DASHBOARD LAST UPDATED + RECENT READINGS
# ---------------------------------------------------------------------------
class TestRealTimeCadence:
    def test_1_30s_cycle_persists_fresh_readings(self, db_session):
        org = _seed_org(db_session, "ORG-RT-1", "RT College", "college", ["energy", "water"], blocks=("BLK-A", "BLK-B"))
        sim = _mk_sim()
        _cycles(sim, db_session, DT0, n=1)
        assert _count(db_session, org.id, "energy") == 2
        _cycles(sim, db_session, DT0 + timedelta(seconds=30), n=1)
        assert _count(db_session, org.id, "energy") == 4
        latest = (
            db_session.query(SensorReading)
            .filter(SensorReading.organisation_id == org.id, SensorReading.sensor_type == "energy")
            .order_by(SensorReading.timestamp.desc())
            .first()
        )
        assert latest.timestamp.replace(tzinfo=timezone.utc) == DT0 + timedelta(seconds=30)

    def test_2_dashboard_last_updated_follows_latest_reading(self, db_session, auth_headers, client):
        org = _seed_org(db_session, "ORG-RT-2", "RT College B", "college", ["energy", "water"], blocks=("BLK-A",))
        sim = _mk_sim()
        _cycles(sim, db_session, DT0, n=1)
        _cycles(sim, db_session, DT0 + timedelta(seconds=30), n=1)
        h = _super_header(auth_headers)
        resp = client.get(f"/api/v1/dashboard/{org.id}", headers=h)
        assert resp.status_code == 200
        body = resp.json()
        assert body["organisation_id"] == org.id
        assert body["kpis"]["energy"]["latest_timestamp"] is not None
        kpi_ts = datetime.fromisoformat(body["kpis"]["energy"]["latest_timestamp"])
        if kpi_ts.tzinfo is None:
            kpi_ts = kpi_ts.replace(tzinfo=timezone.utc)
        assert kpi_ts == DT0 + timedelta(seconds=30)
        assert body["last_updated_at"] is not None

    def test_3_recent_readings_show_newest_cycle(self, db_session, auth_headers, client):
        org = _seed_org(db_session, "ORG-RT-3", "RT College C", "college", ["energy", "water"], blocks=("BLK-A",))
        sim = _mk_sim()
        _cycles(sim, db_session, DT0, n=2)
        h = _super_header(auth_headers)
        resp = client.get(f"/api/v1/dashboard/{org.id}/recent", headers=h)
        assert resp.status_code == 200
        items = resp.json()["readings"]
        assert items
        newest = max(datetime.fromisoformat(i["timestamp"]) for i in items)
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=timezone.utc)
        assert newest == DT0 + timedelta(seconds=30)


# ---------------------------------------------------------------------------
# 4-8. DEMO SCOPE ISOLATION (TEST A/B)
# ---------------------------------------------------------------------------
class TestDemoScopeIsolation:
    def test_4_demo_org_a_changes_only_org_a(self, db_session):
        sim = _mk_sim()
        a = _seed_org(db_session, "ORG-SC-A", "College A", "college", ["energy", "water"], blocks=("BLK-A", "BLK-B"))
        b = _seed_org(db_session, "ORG-SC-B", "Hospital B", "hospital", ["energy", "water", "traffic"], blocks=("BLK-C",))
        m = _seed_org(db_session, "ORG-SC-M", "Muni M", "Municipality", ["energy", "traffic"], wards=("1", "2"))
        sim._demo_orgs.add(a.id)
        _cycles(sim, db_session, DT0, n=2)
        assert _count(db_session, a.id, "energy") == 4  # 2 blocks x 2 cycles
        assert _count(db_session, b.id, "energy") == 0  # frozen (TEST A)
        assert _count(db_session, b.id, "traffic") == 0
        assert _count(db_session, m.id, "energy") == 0  # frozen (TEST B)
        assert _count(db_session, m.id, "traffic") == 0

    def test_5_government_and_private_orgs_frozen(self, db_session):
        sim = _mk_sim()
        gov = _seed_org(db_session, "ORG-SC-G", "Gov Office", "government", ["energy"], blocks=("BLK-G",))
        priv = _seed_org(db_session, "ORG-SC-P", "Private Co", "company", ["energy"], blocks=("BLK-P",))
        sim._demo_orgs.add("ORG-SC-G")
        _cycles(sim, db_session, DT0, n=2)
        assert _count(db_session, gov.id, "energy") == 2
        assert _count(db_session, priv.id, "energy") == 0

    def test_6_municipality_demo_changes_only_municipality_scope(self, db_session):
        sim = _mk_sim()
        college = _seed_org(db_session, "ORG-SC-C", "College", "college", ["energy"], blocks=("BLK-A",))
        muni = _seed_org(db_session, "ORG-SC-M2", "Muni", "Municipality", ["energy", "traffic"], wards=("1", "2"))
        sim._demo_orgs.add(muni.id)
        _cycles(sim, db_session, DT0, n=2)
        assert _count(db_session, muni.id, "energy") == 6  # 2 wards + org-level fallback (no own office block) x 2 cycles
        assert _count(db_session, muni.id, "traffic") == 4
        assert _count(db_session, college.id, "energy") == 0

    def test_7_enrollment_follows_owner_and_demo_generation_active(self, db_session):
        o = _seed_org(db_session, "ORG-SC-O", "Owned Org", "college", ["energy"], blocks=("BLK-O",))
        sim = _mk_sim()
        sim._demo_orgs.add(o.id)
        assert sim._demo_active_for(o.id) is True
        assert sim._demo_active_for("ORG-OTHER") is False
        assert sim.status(organisation_id=o.id)["demo_mode"] is True

    def test_8_stop_org_relinquishes_scope_without_stopping_others(self, db_session):
        sim = _mk_sim()
        a = _seed_org(db_session, "ORG-SS-A", "College A", "college", ["energy"], blocks=("BLK-A",))
        b = _seed_org(db_session, "ORG-SS-B", "Hospital B", "hospital", ["energy"], blocks=("BLK-B",))
        sim._demo_orgs.update({a.id, b.id})
        _cycles(sim, db_session, DT0, n=1)
        assert _count(db_session, a.id, "energy") == 1
        assert _count(db_session, b.id, "energy") == 1
        result = sim.stop(organisation_id=b.id)
        assert result["status"] == "scoped_stopped"
        assert sim._demo_active_for(b.id) is False
        _cycles(sim, db_session, DT0 + timedelta(seconds=30), n=1)
        assert _count(db_session, a.id, "energy") == 2
        assert _count(db_session, b.id, "energy") == 1  # stopped generating


# ---------------------------------------------------------------------------
# 9-15. MUNICIPALITY DEMO WARD CIVIC DATA (BUG-05/BUG-06)
# ---------------------------------------------------------------------------
class TestMunicipalityWardDemoData:
    MUNI_SENSORS = ["energy", "water", "waste", "traffic", "parking", "street_lighting", "air_quality", "sewage_level"]

    @pytest.fixture
    def sim_muni(self, db_session):
        muni = _seed_org(
            db_session,
            "ORG-WD-1",
            "Ward Muni",
            "Municipality",
            self.MUNI_SENSORS,
            blocks=("BLK-OWN",),
            wards=("1", "2"),
        )
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        _cycles(sim, db_session, DT0, n=2)
        return sim, muni

    def test_9_demo_changes_ward_readings(self, db_session, auth_headers, client, sim_muni):
        sim, muni = sim_muni
        h = _super_header(auth_headers)
        resp = client.get(f"/api/v1/dashboard/{muni.id}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["total_wards"] == 2
        wards = resp.json()["wards"]
        assert wards[0]["ward_number"] == "1"
        assert wards[1]["ward_number"] == "2"
        w2 = client.get(f"/api/v1/organisations/{muni.id}/wards/2", headers=h)
        assert w2.status_code == 200
        assert w2.json()["ward"]["ward_number"] == "2"

    def test_10_ward_readings_have_correct_ward_id_no_block(self, db_session, sim_muni):
        sim, muni = sim_muni
        rows = (
            db_session.query(SensorReading)
            .filter(SensorReading.organisation_id == muni.id, SensorReading.sensor_type == "energy")
            .all()
        )
        ward_rows = [r for r in rows if r.ward_id is not None]
        block_rows = [r for r in rows if r.block_id is not None]
        assert len(ward_rows) == 4  # 2 wards x 2 cycles
        assert len(block_rows) == 2  # own office x 2 cycles
        assert {r.ward_id for r in ward_rows} == {"1", "2"}
        assert all(r.block_id is None for r in ward_rows)

    def test_11_ward_detail_energy_water_waste_aq_has_data(self, db_session, auth_headers, client, sim_muni):
        sim, muni = sim_muni
        h = _super_header(auth_headers)
        resp = client.get(f"/api/v1/organisations/{muni.id}/wards/1", headers=h)
        assert resp.status_code == 200
        metrics = resp.json()["metrics"]
        for s in ("energy", "water", "waste", "air_quality"):
            assert metrics[s]["has_data"] is True, f"{s} should have ward data during demo (BUG-05)"
            assert metrics[s]["latest_value"] is not None

    def test_12_street_lighting_per_ward_changes(self, db_session, sim_muni):
        sim, muni = sim_muni
        rows = (
            db_session.query(SensorReading)
            .filter(SensorReading.organisation_id == muni.id, SensorReading.sensor_type == "street_lighting")
            .order_by(SensorReading.timestamp.asc())
            .all()
        )
        assert len(rows) == 4  # 2 wards x 2 cycles
        assert {r.ward_id for r in rows} == {"1", "2"}
        assert all(r.block_id is None for r in rows)
        vals = sorted({round(r.value, 2) for r in rows if r.ward_id == "1"})
        assert len(vals) >= 2 and vals[0] != vals[-1]

    def test_13_ward_scoped_civic_anomaly_attaches_ward_id(self, db_session):
        muni = _seed_org(
            db_session,
            "ORG-WD-AN",
            "Ward Muni Anom",
            "Municipality",
            ["water", "waste", "energy", "traffic"],
            blocks=("BLK-OWN",),
            wards=("1", "2"),
        )
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 1}  # Waste Overflow (block->ward)
        fired = sim.run_cycle(db=db_session, current_time=DT0)
        anom_readings = [r for r in fired if r.is_anomaly]
        assert len(anom_readings) == 1, "exactly one demo anomaly per cycle"
        assert anom_readings[0].ward_id in {"1", "2"}
        assert anom_readings[0].block_id is None
        rec = (
            db_session.query(AnomalyRecord)
            .filter(AnomalyRecord.organisation_id == muni.id, AnomalyRecord.metric == "waste")
            .first()
        )
        assert rec is not None
        assert rec.ward_id == anom_readings[0].ward_id
        assert rec.status == AnomalyRecord.STATUS_OPEN

    def test_14_first_demo_anomaly_scoped_to_ward_energy(self, db_session):
        muni = _seed_org(
            db_session,
            "ORG-WD-EN",
            "Ward Muni Energy",
            "Municipality",
            ["energy", "water"],
            blocks=("BLK-OWN",),
            wards=("1", "2"),
        )
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 8}  # Energy Overload block->ward
        fired = sim.run_cycle(db=db_session, current_time=DT0)
        anom = [r for r in fired if r.is_anomaly]
        assert len(anom) == 1 and anom[0].sensor_type == "energy"
        assert anom[0].ward_id in {"1", "2"}

    def test_15_ward_detail_never_shows_block_data(self, db_session, auth_headers, client, sim_muni):
        sim, muni = sim_muni
        h = _super_header(auth_headers)
        body = client.get(f"/api/v1/organisations/{muni.id}/wards/1", headers=h).json()
        metrics = body["metrics"]
        for s, m in metrics.items():
            if m["has_data"]:
                latest = (
                    db_session.query(SensorReading)
                    .filter(
                        SensorReading.organisation_id == muni.id,
                        SensorReading.sensor_type == s,
                        SensorReading.ward_id == "1",
                    )
                    .order_by(SensorReading.timestamp.desc())
                    .first()
                )
                assert latest is not None
                assert latest.block_id is None, f"{s} leaked a block into ward detail"


# ---------------------------------------------------------------------------
# 16-21. DEMO ANOMALY CADENCE (ONE PER COMPLETED 30s CYCLE) + PIPELINE + RED DOTS
# ---------------------------------------------------------------------------
class TestDemoAnomalyCadence:
    def test_16_schedule_primed_then_fires_once_every_30s(self, db_session):
        org = _seed_org(db_session, "ORG-CD-1", "Cadence College", "college", ["water", "traffic", "energy"], blocks=("BLK-A", "BLK-B"))
        sim = _mk_sim()
        sim._demo_orgs.add(org.id)
        sim._demo_schedules[org.id] = {"next_trigger_at": DT0, "scenario_index": 0}
        # First completed cycle boundary fires exactly ONE demo anomaly.
        fired = sim.run_cycle(db=db_session, current_time=DT0)
        assert sum(1 for r in fired if r.is_anomaly) == 1
        # Mid-cycle polling must never fire or persist duplicates.
        for sec in (5, 10, 25):
            fired = sim.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=sec))
            assert sum(1 for r in fired if r.is_anomaly) == 0
        # Next completed cycle boundary fires again — inside the 600s natural gap.
        fired = sim.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=30))
        assert sum(1 for r in fired if r.is_anomaly) == 1
        recs = (
            db_session.query(AnomalyRecord)
            .filter(AnomalyRecord.organisation_id == org.id)
            .order_by(AnomalyRecord.timestamp.asc())
            .all()
        )
        assert len(recs) == 2
        assert len({r.id for r in recs}) == 2
        gap = (recs[1].timestamp - recs[0].timestamp).total_seconds()
        assert gap == 30.0, f"demo fires on every completed 30s cycle, got {gap}s"
        assert gap < SyntheticSimulator.ANOMALY_MIN_GAP_SECONDS  # inside natural gap

    def test_17_demo_scenario_rotation_honours_sensor_sequence(self, db_session):
        org = _seed_org(db_session, "ORG-CD-2", "Cadence College B", "college", ["water", "traffic", "energy"], blocks=("BLK-A",))
        sim = _mk_sim()
        sim._demo_orgs.add(org.id)
        sim._demo_schedules[org.id] = {"next_trigger_at": DT0, "scenario_index": 0}
        for step in range(5):
            fired = sim.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=step * 30))
            assert sum(1 for r in fired if r.is_anomaly) == 1, f"cycle {step} must fire exactly one anomaly"
        recs = (
            db_session.query(AnomalyRecord)
            .filter(AnomalyRecord.organisation_id == org.id)
            .order_by(AnomalyRecord.timestamp.asc(), AnomalyRecord.id.asc())
            .all()
        )
        metrics = [r.metric for r in recs]
        # sequence indices 0 (water, block), 4 (traffic), 8 (energy), 0 (water), 4 (traffic)
        assert metrics == ["water", "traffic", "energy", "water", "traffic"], f"rotation order wrong: {metrics}"

    def test_18_demo_anomaly_flows_through_real_pipeline(self, db_session):
        muni = _seed_org(
            db_session,
            "ORG-PL-1",
            "Pipeline Muni",
            "Municipality",
            ["sewage_level", "water", "energy", "traffic"],
            blocks=("BLK-OWN",),
            wards=("1", "2"),
        )
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 3}  # Drainage Backup
        sim.run_cycle(db=db_session, current_time=DT0)
        rec = (
            db_session.query(AnomalyRecord)
            .filter(AnomalyRecord.organisation_id == muni.id, AnomalyRecord.metric == "sewage_level")
            .first()
        )
        assert rec is not None
        assert rec.ward_id in {"1", "2"}
        assert rec.status == AnomalyRecord.STATUS_OPEN
        assert rec.severity in {"HIGH", "MEDIUM", "CRITICAL"}
        assert rec.value is not None

    def test_19_wards_valid_and_records_attached_after_anomaly(self, db_session):
        muni = _seed_org(
            db_session,
            "ORG-PL-2",
            "Pipe Muni B",
            "Municipality",
            ["sewage_level", "water"],
            wards=("1", "2"),
        )
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 3}
        sim.run_cycle(db=db_session, current_time=DT0)
        db_session.commit()
        recs = db_session.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == muni.id).all()
        assert len(recs) == 1
        rows = (
            db_session.query(SensorReading)
            .filter(SensorReading.organisation_id == muni.id, SensorReading.is_anomaly == True)
            .all()
        )
        assert rows and rows[0].ward_id == recs[0].ward_id

    def test_20_sewage_level_canonical_red_dot(self, db_session, auth_headers, client):
        muni = _seed_org(
            db_session,
            "ORG-NOT-1",
            "Notify Muni",
            "Municipality",
            ["sewage_level", "water", "energy", "traffic"],
            blocks=("BLK-OWN",),
            wards=("1", "2"),
        )
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 3}
        sim.run_cycle(db=db_session, current_time=DT0)
        h = _super_header(auth_headers, muni.id)
        resp = client.get("/api/v1/notifications/unread", headers=h)
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_unread"] is True
        assert body["modules"]["sewage"] is True, "sewage_level anomaly must surface as sewage red dot (BUG-09)"
        assert body["total_unread"] >= 1

    def test_21_no_mid_cycle_duplicates_force_new_persistence(self, db_session):
        org = _seed_org(db_session, "ORG-ND-1", "NoDup College", "college", ["water", "traffic", "energy"], blocks=("BLK-A",))
        sim = _mk_sim()
        sim._demo_orgs.add(org.id)
        sim._demo_schedules[org.id] = {"next_trigger_at": DT0, "scenario_index": 0}
        sim.run_cycle(db=db_session, current_time=DT0)
        assert sum(1 for r in db_session.query(SensorReading).filter(SensorReading.organisation_id == org.id, SensorReading.is_anomaly == True)) == 1
        # Mid-cycle polling must not create duplicates (returns existing records).
        for sec in (5, 10, 25):
            sim.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=sec))
        assert sum(1 for r in db_session.query(SensorReading).filter(SensorReading.organisation_id == org.id, SensorReading.is_anomaly == True)) == 1
        assert db_session.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == org.id).count() == 1
        # Every completed 30s boundary persists a brand-new anomaly (force_new).
        for step in range(30, 130, 30):
            sim.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=step))
        anomaly_readings = db_session.query(SensorReading).filter(SensorReading.organisation_id == org.id, SensorReading.is_anomaly == True).all()
        assert len(anomaly_readings) == 5  # DT0 + 4 boundaries
        recs = db_session.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == org.id).all()
        assert len(recs) == 5
        assert len({r.id for r in recs}) == 5  # all distinct, none deduped


# ---------------------------------------------------------------------------
# 22-23. PRIORITY ENGINE
# ---------------------------------------------------------------------------
class TestPriorityEngine:
    def _seed_anomalies(self, db_session, org_id, severities):
        for sev in severities:
            db_session.add(
                AnomalyRecord(
                    organisation_id=org_id,
                    metric="energy",
                    sensor_type="energy",
                    value=1420.0,
                    severity=sev,
                    status=AnomalyRecord.STATUS_OPEN,
                    reason=f"{sev} energy breach on Block-A",
                    facility_id="Block A",
                )
            )
        db_session.commit()

    def test_22_priority_ranks_critical_first(self, db_session, auth_headers, client):
        org = _seed_org(db_session, "ORG-PR-1", "Priority College", "college", ["energy"], blocks=("BLK-A", "BLK-B"))
        self._seed_anomalies(db_session, org.id, ["MEDIUM", "HIGH", "CRITICAL"])
        h = _super_header(auth_headers)
        resp = client.get(f"/api/v1/anomalies/{org.id}/priority", headers=h)
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_active"] is True
        assert body["active_anomaly_count"] == 3
        assert body["top_priority"]["priority_level"] == "CRITICAL"
        assert body["items"][0]["priority_level"] == "CRITICAL"

    def test_23_priority_inactive_below_threshold(self, db_session, auth_headers, client):
        org = _seed_org(db_session, "ORG-PR-2", "Priority College B", "college", ["energy"], blocks=("BLK-A",))
        self._seed_anomalies(db_session, org.id, ["HIGH"])
        h = _super_header(auth_headers)
        body = client.get(f"/api/v1/anomalies/{org.id}/priority", headers=h).json()
        assert body["is_active"] is False
        assert "inactive" in body["message"].lower()


# ---------------------------------------------------------------------------
# 24-26. WARD-FORECAST SCOPING (honest history, no fabrication)
# ---------------------------------------------------------------------------
class TestForecastScoping:
    def test_24_energy_ward_forecast_uses_only_ward_history(self, db_session, auth_headers, client):
        muni = _seed_org(db_session, "ORG-FC-1", "Forecast Muni", "Municipality", ["energy"], wards=("1", "2"))
        t = DT0
        for i, v in enumerate((100.0, 110.0, 115.0)):
            _add_reading(db_session, muni.id, "energy", v, t + timedelta(seconds=30 * i), ward_id="1", unit="kWh")
        _add_reading(db_session, muni.id, "energy", 9999.0, t, ward_id="2", unit="kWh")  # must NOT leak into ward 1
        h = _super_header(auth_headers)
        body = client.get(f"/api/v1/organisations/{muni.id}/wards/1", headers=h).json()
        fc = body["forecasts"]
        assert fc  # items exist
        energy_fc = next((f for f in fc if f["sensor_type"] == "energy"), None)
        assert energy_fc is not None
        assert energy_fc["is_available"] is True
        assert len(energy_fc["points"]) == 3  # 6h / 12h / 24h horizons
        assert energy_fc["current_value"] == 115.0
        assert energy_fc["current_value"] != 9999.0  # ward-2 reading excluded

    def test_25_org_level_aggregation_not_contaminated_by_wards(self, db_session):
        muni = _seed_org(db_session, "ORG-FC-2", "Agg Muni", "Municipality", ["energy"], blocks=("BLK-OWN",), wards=("1", "2"))
        t = DT0
        _add_reading(db_session, muni.id, "energy", 100.0, t, block_id="BLK-OWN", unit="kWh")
        _add_reading(db_session, muni.id, "energy", 100.0, t + timedelta(seconds=30), block_id="BLK-OWN", unit="kWh")
        _add_reading(db_session, muni.id, "energy", 500.0, t, ward_id="1", unit="kWh")
        _add_reading(db_session, muni.id, "energy", 500.0, t + timedelta(seconds=30), ward_id="1", unit="kWh")
        summary = compute_metric_summary(
            db=db_session,
            organisation_id=muni.id,
            sensor_type="energy",
            blocks=[b for b in db_session.query(FacilityBlock).filter(FacilityBlock.organisation_id == muni.id)],
            now_dt=t + timedelta(seconds=30),
        )
        assert summary.current_value == 100.0  # only block readings contribute (wards excluded)
        assert [p.value for p in summary.cycle_points] == [100.0, 100.0]

    def test_26_ward_forecast_honest_when_insufficient_history(self, db_session, auth_headers, client):
        muni = _seed_org(db_session, "ORG-FC-3", "Honest Muni", "Municipality", ["energy"], wards=("1", "2"))
        _add_reading(db_session, muni.id, "energy", 100.0, DT0, ward_id="1", unit="kWh")
        h = _super_header(auth_headers)
        body = client.get(f"/api/v1/organisations/{muni.id}/wards/1", headers=h).json()
        energy_fc = next((f for f in body["forecasts"] if f["sensor_type"] == "energy"), None)
        assert energy_fc is not None
        assert energy_fc["is_available"] is False
        assert "Insufficient" in energy_fc["message"]


# ---------------------------------------------------------------------------
# 27-33. SCOPE RULES: WARDS-NEVER-BLOCKS, CIVIC MODULES
# ---------------------------------------------------------------------------
class TestScopeRules:
    def test_27_ward_count_excludes_facility_blocks(self, db_session, auth_headers, client):
        muni = _seed_org(
            db_session, "ORG-WL-1", "Ward List Muni", "Municipality",
            ["energy", "traffic"], blocks=("BLK-OWN", "BLK-OWN-2"), wards=("1", "2", "3"),
        )
        h = _super_header(auth_headers)
        body = client.get(f"/api/v1/organisations/{muni.id}/wards", headers=h).json()
        assert body["total"] == 3
        assert all("ward_number" in i for i in body["items"])

    def test_28_add_ward_creates_no_block(self, db_session, auth_headers, client):
        muni = _seed_org(db_session, "ORG-AD-1", "Add Ward Muni", "Municipality", ["energy"], blocks=("BLK-OWN",), wards=("1",))
        blocks_before = db_session.query(FacilityBlock).filter(FacilityBlock.organisation_id == muni.id).count()
        h = _super_header(auth_headers)
        resp = client.post(
            f"/api/v1/organisations/{muni.id}/wards",
            json={"ward_name": "Ward 4"},
            headers=h,
        )
        assert resp.status_code == 201
        assert db_session.query(MunicipalityWard).filter(MunicipalityWard.municipality_id == muni.id).count() == 2
        assert db_session.query(FacilityBlock).filter(FacilityBlock.organisation_id == muni.id).count() == blocks_before

    def test_29_street_lighting_never_block_generated(self, db_session):
        muni = _seed_org(db_session, "ORG-SL-1", "Street L Muni", "Municipality", ["street_lighting", "energy"], blocks=("BLK-OWN",), wards=("1", "2"))
        sim = _mk_sim()
        _cycles(sim, db_session, DT0, n=2)
        rows = db_session.query(SensorReading).filter(SensorReading.organisation_id == muni.id, SensorReading.sensor_type == "street_lighting").all()
        assert rows
        assert all(r.block_id is None for r in rows)
        assert all(r.ward_id in {"1", "2"} for r in rows)

    def test_30_parking_traffic_water_flow_never_block(self, db_session):
        muni = _seed_org(
            db_session, "ORG-PT-1", "Parking Muni", "Municipality",
            ["parking", "traffic", "water_flow", "energy"], blocks=("BLK-OWN",), wards=("1", "2"),
        )
        sim = _mk_sim()
        _cycles(sim, db_session, DT0, n=2)
        for s in ("parking", "traffic", "water_flow"):
            rows = db_session.query(SensorReading).filter(SensorReading.organisation_id == muni.id, SensorReading.sensor_type == s).all()
            assert all(r.block_id is None for r in rows)
            assert all(r.ward_id in {"1", "2"} for r in rows)

    def test_31_water_flow_scoped_to_ward_for_municipality(self, db_session):
        muni = _seed_org(db_session, "ORG-WF-1", "Flow Muni", "Municipality", ["water_flow", "water_level"], wards=("1", "2"))
        sim = _mk_sim()
        _cycles(sim, db_session, DT0, n=1)
        rows = db_session.query(SensorReading).filter(SensorReading.organisation_id == muni.id, SensorReading.sensor_type == "water_flow").all()
        assert len(rows) == 2
        assert {r.ward_id for r in rows} == {"1", "2"}

    def test_32_air_quality_never_uses_blocks(self, db_session):
        muni = _seed_org(db_session, "ORG-AQ-1", "AQ Muni", "Municipality", ["air_quality", "energy"], blocks=("BLK-OWN",), wards=("1", "2"))
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        _cycles(sim, db_session, DT0, n=1)
        rows = db_session.query(SensorReading).filter(SensorReading.organisation_id == muni.id, SensorReading.sensor_type == "air_quality").all()
        assert all(r.block_id is None for r in rows)
        assert {r.ward_id for r in rows} == {"1", "2"}

    def test_33_energy_stays_block_scoped_for_own_office(self, db_session):
        muni = _seed_org(db_session, "ORG-EO-1", "Energy Own Muni", "Municipality", ["energy"], blocks=("BLK-OWN",), wards=("1", "2"))
        sim = _mk_sim()
        _cycles(sim, db_session, DT0, n=2)
        sim2 = _mk_sim()
        sim2._demo_orgs.add(muni.id)
        sim2.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=60))
        rows = db_session.query(SensorReading).filter(SensorReading.organisation_id == muni.id, SensorReading.sensor_type == "energy").all()
        block_rows = [r for r in rows if r.block_id == "BLK-OWN"]
        ward_rows = [r for r in rows if r.ward_id is not None]
        assert len(block_rows) >= 1
        assert len(ward_rows) >= 1


# ---------------------------------------------------------------------------
# 34-35. OVERSIGHT + OWN OFFICE LIVE DATA
# ---------------------------------------------------------------------------
class TestOversightAndOwnOffice:
    def test_34_super_admin_oversight_works_for_any_org(self, db_session, auth_headers, client):
        b = _seed_org(db_session, "ORG-OV-1", "Oversight Hospital", "hospital", ["energy", "water"], blocks=("BLK-H",))
        sim = _mk_sim()
        _cycles(sim, db_session, DT0, n=1)
        h = _super_header(auth_headers)
        resp = client.get(f"/api/v1/dashboard/{b.id}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["organisation_name"] == b.name

    def test_35_municipality_own_office_live_data_during_demo(self, db_session):
        muni = _seed_org(
            db_session, "ORG-OO-1", "Own Office Muni", "Municipality",
            ["energy", "water", "waste"], blocks=("BLK-OWN",), wards=("1", "2"),
        )
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        _cycles(sim, db_session, DT0, n=2)
        own_energy = db_session.query(SensorReading).filter(
            SensorReading.organisation_id == muni.id,
            SensorReading.sensor_type == "energy",
            SensorReading.block_id == "BLK-OWN",
        ).count()
        ward_energy = db_session.query(SensorReading).filter(
            SensorReading.organisation_id == muni.id,
            SensorReading.sensor_type == "energy",
            SensorReading.ward_id.isnot(None),
        ).count()
        assert own_energy == 2
        assert ward_energy == 4


# ---------------------------------------------------------------------------
# 36-37. AGGREGATION RULES
# ---------------------------------------------------------------------------
class TestAggregationRules:
    def test_36_overall_is_not_highest_block_and_current_peak(self, db_session):
        org = _seed_org(db_session, "ORG-AG-1", "Agg College", "college", ["energy"], blocks=("BLK-A", "BLK-B"))
        t = DT0
        for cycle_i, (a_val, b_val) in enumerate(((100.0, 200.0), (150.0, 250.0), (120.0, 180.0))):
            ts = t + timedelta(seconds=30 * cycle_i)
            _add_reading(db_session, org.id, "energy", a_val, ts, block_id="BLK-A", unit="kWh")
            _add_reading(db_session, org.id, "energy", b_val, ts, block_id="BLK-B", unit="kWh")
        blocks = [b for b in db_session.query(FacilityBlock).filter(FacilityBlock.organisation_id == org.id)]
        summary = compute_metric_summary(db=db_session, organisation_id=org.id, sensor_type="energy", blocks=blocks, now_dt=t + timedelta(seconds=60))
        # scenario 36: overall is the SUM, never the highest single block
        highest_block = 250.0
        assert summary.current_value == 300.0  # 120 + 180, sum across blocks
        assert summary.current_value > highest_block
        # scenario 37a: current == latest cycle point
        assert summary.cycle_points[-1].value == 300.0
        assert summary.current_value == summary.cycle_points[-1].value
        # peak == historical maximum >= current
        peak = max(p.value for p in summary.cycle_points)
        assert summary.maximum == peak == 400.0
        assert summary.maximum >= summary.current_value
        assert summary.reading_count == 6

    def test_37_current_value_recomputed_from_latest_cycle(self, db_session):
        org = _seed_org(db_session, "ORG-AG-2", "Agg College B", "college", ["water"], blocks=("BLK-A", "BLK-B"))
        t = DT0
        _add_reading(db_session, org.id, "water", 40.0, t, block_id="BLK-A", unit="L")
        _add_reading(db_session, org.id, "water", 60.0, t, block_id="BLK-B", unit="L")
        _add_reading(db_session, org.id, "water", 55.0, t + timedelta(seconds=30), block_id="BLK-A", unit="L")
        _add_reading(db_session, org.id, "water", 45.0, t + timedelta(seconds=30), block_id="BLK-B", unit="L")
        blocks = [b for b in db_session.query(FacilityBlock).filter(FacilityBlock.organisation_id == org.id)]
        summary = compute_metric_summary(db=db_session, organisation_id=org.id, sensor_type="water", blocks=blocks, now_dt=t + timedelta(seconds=30))
        assert summary.current_value == 100.0  # 55 + 45
        assert summary.cycle_points[1].value == 100.0


# ---------------------------------------------------------------------------
# 38. SIM-CLOCK STATUS SEMANTICS (ward detail freshness)
# ---------------------------------------------------------------------------
class TestSimClockStatus:
    def test_38_ward_detail_status_uses_simulated_day_freshness(self, db_session, auth_headers, client):
        muni = _seed_org(db_session, "ORG-ST-1", "Status Muni", "Municipality", ["water"], wards=("1", "2"))
        cfg = db_session.query(OrganisationSensorConfig).filter(OrganisationSensorConfig.organisation_id == muni.id).first()
        sim_date = cfg.current_simulated_date or OrganisationSensorConfig.DEFAULT_SIMULATED_DATE
        now_wall = _utcnow()
        base = datetime(
            sim_date.year, sim_date.month, sim_date.day,
            now_wall.hour, now_wall.minute, now_wall.second,
            tzinfo=timezone.utc,
        )
        # Reading stamped on the simulated calendar day at the live time-of-day => ONLINE.
        _add_reading(db_session, muni.id, "water", 500.0, base, ward_id="1", unit="L")
        # Reading stamped on the same simulated day but 15 minutes behind the live
        # time-of-day => genuinely stale (the sim-clock reference reuses the
        # reading's own calendar day + live time-of-day, so a 900s gap is OFFLINE).
        _add_reading(db_session, muni.id, "water", 500.0, base - timedelta(minutes=15), ward_id="2", unit="L")
        h = _super_header(auth_headers)
        w1 = client.get(f"/api/v1/organisations/{muni.id}/wards/1", headers=h).json()
        w2 = client.get(f"/api/v1/organisations/{muni.id}/wards/2", headers=h).json()
        assert w1["metrics"]["water"]["has_data"] is True
        assert w1["metrics"]["water"]["status"] == "ONLINE", "simulated-day ward data must read ONLINE (sim-clock)"
        assert w2["metrics"]["water"]["status"] == "OFFLINE", "reading 15min behind live time-of-day must read OFFLINE (sim-clock)"


# ---------------------------------------------------------------------------
# 39. CIVIC DEMO ANOMALIES -> WARD-SCOPED RECOMMENDATIONS
# ---------------------------------------------------------------------------
class TestCivicRecommendations:
    def test_39_civic_demo_anomalies_produce_recommendations(self, db_session):
        muni = _seed_org(
            db_session,
            "ORG-CR-1",
            "Civic Rec Muni",
            "Municipality",
            ["street_lighting", "sewage_level", "water_flow", "rainfall", "energy", "traffic"],
            blocks=("BLK-O",),
            wards=("1", "2"),
        )
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        # Street Light Outage (idx 6, ward scope)
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 6}
        sim.run_cycle(db=db_session, current_time=DT0)
        # Drainage Backup (idx 3, ward scope)
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 3}
        sim.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=30))
        # Pump Pressure Loss (idx 5, ward scope)
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 5}
        sim.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=60))
        # Heavy Rainfall (idx 2, ward scope)
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 2}
        sim.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=90))
        recs = (
            db_session.query(AIRecommendation)
            .filter(AIRecommendation.organisation_id == muni.id)
            .all()
        )
        assert recs, "civic demo anomalies must produce AI recommendations"
        metrics = {r.metric for r in recs}
        assert "street_lighting" in metrics, f"missing street_lighting rec: {metrics}"
        assert "sewage_level" in metrics, f"missing sewage_level rec: {metrics}"
        assert "water_flow" in metrics, f"missing water_flow rec: {metrics}"
        assert "rainfall" in metrics, f"missing rainfall rec: {metrics}"
        for r in recs:
            if r.metric in {"street_lighting", "sewage_level", "water_flow", "rainfall"}:
                assert r.ward_id in {"1", "2"}, f"{r.metric} recommendation must be ward-scoped"
                assert r.status in {
                    AIRecommendation.STATUS_ACTIVE,
                    AIRecommendation.STATUS_OPEN,
                }, f"{r.metric} recommendation must be open/active, got {r.status!r}"


# ---------------------------------------------------------------------------
# 40-41. WARD-LEVEL UNREAD RED DOTS + MARK-READ BY WARD
# ---------------------------------------------------------------------------
class TestWardRedDots:
    def _muni(self, db_session) -> Organisation:
        return _seed_org(
            db_session,
            "ORG-WR-1",
            "Ward Red Dot Muni",
            "Municipality",
            ["street_lighting", "sewage_level", "water"],
            blocks=("BLK-O",),
            wards=("1", "2"),
        )

    def test_40_unread_response_exposes_ward_red_dots(self, db_session, auth_headers, client):
        muni = self._muni(db_session)
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 6}  # street_lighting ward
        sim.run_cycle(db=db_session, current_time=DT0)
        h = _super_header(auth_headers, muni.id)
        body = client.get("/api/v1/notifications/unread", headers=h).json()
        assert body["has_unread"] is True
        # Round-robin first ward target is ward "1" (wards ordered ascending).
        assert body["wards"] == {"1": True}, f"wards mapping wrong: {body['wards']}"
        assert body["modules"]["street_lighting"] is True

    def test_41_mark_read_by_ward_id_clears_only_that_ward(self, db_session, auth_headers, client):
        muni = self._muni(db_session)
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        # Fire street_lighting on ward 1 (offset 0), then ward 2 (offset 1).
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 6}
        sim.run_cycle(db=db_session, current_time=DT0)
        sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 6}
        sim.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=30))
        h = _super_header(auth_headers, muni.id)
        body = client.get("/api/v1/notifications/unread", headers=h).json()
        assert body["wards"] == {"1": True, "2": True}, f"wards mapping wrong: {body['wards']}"
        resp = client.post("/api/v1/notifications/mark-read", json={"ward_id": "1"}, headers=h)
        assert resp.status_code == 200
        assert resp.json()["marked_count"] == 1
        body2 = client.get("/api/v1/notifications/unread", headers=h).json()
        assert body2["wards"] == {"2": True}, f"ward 1 must be cleared, ward 2 stays: {body2['wards']}"


# ---------------------------------------------------------------------------
# 42. DEMO RESET CLEARS SCHEDULES + ROUND-ROBIN OFFSETS
# ---------------------------------------------------------------------------
class TestDemoReset:
    def test_42_reset_clears_demo_state_per_org_and_all(self, db_session):
        sim = _mk_sim()
        a = _seed_org(db_session, "ORG-RS-A", "Reset College A", "college", ["energy"], blocks=("BLK-A",))
        b = _seed_org(db_session, "ORG-RS-B", "Reset College B", "college", ["energy"], blocks=("BLK-B",))
        sim._demo_orgs.update({a.id, b.id})
        sim._demo_schedules.update({
            a.id: {"next_trigger_at": DT0, "scenario_index": 0},
            b.id: {"next_trigger_at": DT0, "scenario_index": 1},
        })
        sim._demo_target_offsets[a.id] = {"ward": 2, "block": 1}
        sim._demo_target_offsets[b.id] = {"ward": 0}
        # Per-org reset removes only that org's schedule + offsets.
        sim.reset_simulator_state(a.id)
        assert a.id not in sim._demo_schedules
        assert a.id not in sim._demo_target_offsets
        assert b.id in sim._demo_schedules
        assert b.id in sim._demo_target_offsets
        # All reset clears every org, the schedules, offsets and enrollment.
        sim.reset_all_simulator_state()
        assert sim._demo_orgs == set()
        assert sim._demo_schedules == {}
        assert sim._demo_target_offsets == {}
        assert sim._demo_active_for(a.id) is False
        assert sim._demo_active_for(b.id) is False


# ---------------------------------------------------------------------------
# 43. DEMO WARD TARGETS ROTATE ROUND-ROBIN
# ---------------------------------------------------------------------------
class TestDemoTargetRotation:
    def test_43_demo_ward_targets_rotate_round_robin(self, db_session):
        muni = _seed_org(
            db_session,
            "ORG-RT-ROT",
            "Rotate Muni",
            "Municipality",
            ["street_lighting", "water"],
            blocks=("BLK-O",),
            wards=("1", "2"),
        )
        sim = _mk_sim()
        sim._demo_orgs.add(muni.id)
        fired_wards = []
        for i in range(4):
            sim._demo_schedules[muni.id] = {"next_trigger_at": DT0, "scenario_index": 6}
            fired = sim.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=i * 30))
            anom = [r for r in fired if r.is_anomaly]
            assert len(anom) == 1
            assert anom[0].sensor_type == "street_lighting"
            fired_wards.append(anom[0].ward_id)
        assert fired_wards == ["1", "2", "1", "2"], f"round-robin rotation wrong: {fired_wards}"


# ---------------------------------------------------------------------------
# 44. force_new BYPASSES DEDUP; DEDUP INTACT FOR THE NATURAL PATH
# ---------------------------------------------------------------------------
class TestForceNewDedup:
    def test_44_force_new_bypasses_dedup_but_dedup_intact_outside_demo(self, db_session):
        org = _seed_org(db_session, "ORG-DD-1", "Dedup College", "college", ["energy"], blocks=("BLK-A",))
        cfg = _configure_sensors(db_session, org.id, ["energy"])

        def _mk_reading(ts: datetime) -> SensorReading:
            return SensorReading(
                organisation_id=org.id,
                sensor_type="energy",
                value=1500.0,
                unit="kWh",
                block_id="BLK-A",
                source="synthetic",
                timestamp=ts,
                is_anomaly=True,
            )

        r1 = _mk_reading(DT0)
        db_session.add(r1)
        db_session.commit()
        rec1 = anomaly_service.process_single_reading(db_session, r1, cfg, force_new=False)
        assert rec1 is not None

        # Same metric + same block within 5 minutes, natural path: dedup returns the SAME record.
        r2 = _mk_reading(DT0 + timedelta(seconds=10))
        db_session.add(r2)
        db_session.commit()
        rec2 = anomaly_service.process_single_reading(db_session, r2, cfg, force_new=False)
        assert rec2 is not None and rec2.id == rec1.id
        assert db_session.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == org.id).count() == 1
        assert db_session.query(AIRecommendation).filter(AIRecommendation.organisation_id == org.id).count() == 1

        # Follow-up demo-style reading with force_new: new record + new recommendation-pair persisted.
        r3 = _mk_reading(DT0 + timedelta(seconds=20))
        db_session.add(r3)
        db_session.commit()
        rec3 = anomaly_service.process_single_reading(db_session, r3, cfg, force_new=True)
        assert rec3 is not None and rec3.id != rec1.id
        assert db_session.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == org.id).count() == 2
        energy_recs = db_session.query(AIRecommendation).filter(
            AIRecommendation.organisation_id == org.id,
            AIRecommendation.metric == "energy",
        ).all()
        assert len(energy_recs) == 2, "skip_recent_dedup must bypass the 1h recommendation dedup for demo"


# ---------------------------------------------------------------------------
# 45. DEMO CADENCE INSIDE NATURAL GAP + NATURAL ANOMALIES SUSPENDED FOR DEMO
# ---------------------------------------------------------------------------
class TestNaturalSuspension:
    def test_45_demo_fires_inside_natural_gap_and_natural_anomalies_suspended(self, db_session):
        org = _seed_org(db_session, "ORG-NS-1", "Suspended College", "college", ["energy", "water", "traffic"], blocks=("BLK-A",))
        # Arm a 100% natural probability for traffic: IF the natural path were NOT
        # suspended inside the active demo scope, this cycle would fire it.
        SyntheticSimulator.DEFAULT_ANOMALY_PROBABILITIES["traffic"] = 1.0
        sim = _mk_sim()
        sim._demo_orgs.add(org.id)
        # The demo scenario path is gated to completed 30s boundaries — a schedule
        # that is not yet due cannot fire. So with natural anomalies suspended,
        # this cycle yields NO anomaly at all.
        sim._demo_schedules[org.id] = {"next_trigger_at": DT0 + timedelta(seconds=30), "scenario_index": 0}
        sim.run_cycle(db=db_session, current_time=DT0)
        assert (
            db_session.query(SensorReading)
            .filter(SensorReading.organisation_id == org.id, SensorReading.is_anomaly == True)
            .count()
        ) == 0
        assert db_session.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == org.id).count() == 0

        # Reach a completed 30s boundary while a natural anomaly was recorded 30s
        # ago — inside the natural 600s ANOMALY_MIN_GAP the natural path is
        # impossible, yet the demo scenario fires anyway. EXACTLY ONE anomaly
        # appears: the demo scenario clocking through the natural gap.
        sim._last_anomaly_times[org.id] = DT0
        sim._demo_schedules[org.id] = {"next_trigger_at": DT0 + timedelta(seconds=30), "scenario_index": 0}
        sim.run_cycle(db=db_session, current_time=DT0 + timedelta(seconds=30))
        recs = db_session.query(AnomalyRecord).filter(AnomalyRecord.organisation_id == org.id).all()
        assert len(recs) == 1
        assert recs[0].metric == "water"  # DEMO_SCENARIO_SEQUENCE[0] Water Supply Leak
        db_session.refresh(org)