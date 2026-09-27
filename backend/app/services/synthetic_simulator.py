"""
GreenNexa — Synthetic Data Simulator Service.

Generates realistic sustainable-facility sensor data for organisations configured
with data_source = 'synthetic'. Enforces strict mutual exclusivity, enabled sensor
filtering, at most 1 anomaly per cycle, and a minimum 10-minute gap between anomalies.
"""

from __future__ import annotations

import asyncio
import logging
import random
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.aggregation import (
    BLOCK_WISE_MODULES,
    NATURAL_LOCATION_MODULES,
    WHOLE_ORG_DEFAULT_MODULES,
)
from app.core.sensor_catalog import MASTER_SENSOR_CATALOG, SENSOR_CATALOG_MAP
from app.db.database import SessionLocal
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    MunicipalityWard,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SyntheticDataSimulator:
    """
    Background simulator for generating realistic synthetic facility sensor readings.
    """

    # Baseline normal ranges and units per sensor type (from Master Sensor Catalog)
    SENSOR_CONFIGS: Dict[str, Dict[str, Any]] = {
        s["id"]: {
            "unit": s["unit"],
            "normal_range": s["normal_range"],
            "anomaly_range": s["anomaly_range"],
            "baseline": s["default_baseline"],
            "warning_threshold": s["default_warn"],
            "critical_threshold": s["default_crit"],
        }
        for s in MASTER_SENSOR_CATALOG
    }

    # Anomaly probabilities per cycle (configurable)
    DEFAULT_ANOMALY_PROBABILITIES: Dict[str, float] = {
        "energy": 0.04,
        "water": 0.03,
        "temperature": 0.05,
        "humidity": 0.03,
        "co2": 0.04,
        "waste": 0.03,
        "air_quality": 0.04,
        "traffic": 0.04,
        "parking": 0.04,
        "water_flow": 0.03,
        "water_level": 0.03,
        "sewage_level": 0.03,
        "rainfall": 0.03,
        "equipment_asset": 0.03,
        "occupancy": 0.03,
        "vibration": 0.03,
        "pressure": 0.03,
        "flow": 0.03,
        "current_voltage": 0.03,
        "rpm": 0.03,
        "machine_temperature": 0.03,
        "runtime_hours": 0.02,
        "acoustic_sound": 0.03,
        "gas": 0.03,
        "dust_pm": 0.03,
        "fire_smoke": 0.02,
        "oil_fluid_level": 0.03,
        "assets": 0.03,
        "safety": 0.02,
        "climate": 0.03,
    }

    # Module-to-Sensor mappings for module-scoped Demo Mode
    MODULE_SENSOR_MAP: Dict[str, set[str]] = {
        "energy": {"energy", "power"},
        "water": {"water", "water_flow", "water_level"},
        "waste": {"waste"},
        "air_quality": {"air_quality", "co2", "dust_pm", "gas"},
        "environment": {"air_quality", "climate", "temperature", "humidity", "co2"},
        "temperature": {"temperature", "humidity", "climate"},
        "humidity": {"humidity", "climate", "temperature"},
        "co2": {"co2", "air_quality"},
        "traffic": {"traffic", "parking"},
        "parking": {"parking"},
        "street_lighting": {"street_lighting"},
        "roads": {"roads"},
        "parks": {"parks"},
        "sewage": {"sewage", "sewage_level"},
        "safety": {"safety", "fire_smoke", "acoustic_sound"},
        "assets": {"assets", "equipment_asset", "vibration", "pressure", "rpm", "runtime_hours"},
        "climate": {"climate", "rainfall", "temperature", "humidity", "co2"},
    }

    @classmethod
    def _sensors_for_module(cls, module_name: str) -> set[str]:
        clean = (module_name or "").lower().strip()
        mapped = cls.MODULE_SENSOR_MAP.get(clean, set())
        return mapped | {clean} if clean else set()

    # Minimum gap required between anomalies per organisation (10 minutes)
    # Applies to naturally-triggered anomalies. Demo-mode scenario anomalies
    # follow their own cadence (see DEMO_SCENARIO_SEQUENCE) and are gated to a
    # maximum of one anomaly per organisation per cycle.
    ANOMALY_MIN_GAP_SECONDS: float = 600.0

    # Demo Mode scenario rotation. Each scenario maps to the sensors it can
    # trigger and the location scope the anomaly is applied to:
    #   block  -> a randomly selected active FacilityBlock (block-wise modules)
    #   ward   -> a randomly selected active MunicipalityWard (natural location modules)
    #   org    -> whole-organisation (whole-org default modules)
    DEMO_SCENARIO_SEQUENCE: List[Dict[str, Any]] = [
        {"name": "Water Supply Leak", "sensors": ["water"], "scope": "block"},
        {"name": "Waste Overflow", "sensors": ["waste"], "scope": "block"},
        {"name": "Heavy Rainfall", "sensors": ["rainfall"], "scope": "ward"},
        {"name": "Drainage Backup", "sensors": ["sewage_level", "sewage"], "scope": "ward"},
        {"name": "Traffic Congestion", "sensors": ["traffic"], "scope": "ward"},
        {"name": "Pump Pressure Loss", "sensors": ["water_flow", "water_level"], "scope": "ward"},
        {"name": "Street Light Outage", "sensors": ["street_lighting"], "scope": "ward"},
        {"name": "Air Quality Spike", "sensors": ["air_quality"], "scope": "org"},
        {"name": "Energy Overload", "sensors": ["energy"], "scope": "block"},
    ]

    # Demo Mode anomaly cadence (FINAL SPEC): exactly ONE Demo scenario anomaly
    # fires on EVERY completed 30s cycle per demo-enrolled organisation. The
    # schedule is primed on the first cycle after enrollment (returns None), then
    # fires on every subsequent cycle boundary, rotating through
    # DEMO_SCENARIO_SEQUENCE and round-robin location targets. Natural
    # probability anomalies are suspended while an org is inside the active demo
    # scope so the demo cadence is deterministic and provable.
    #
    # The attributes below are retained for backward compatibility with older
    # callers but are NOT used by the demo scheduler anymore (every cycle fires).
    DEMO_FIRST_DELAY_SECONDS: Tuple[float, float] = (10.0, 25.0)
    DEMO_NEXT_DELAY_SECONDS: Tuple[float, float] = (60.0, 120.0)

    def __init__(self, interval_seconds: int = 30) -> None:
        self.interval_seconds = interval_seconds
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._task: Optional[asyncio.Task] = None
        self._last_run_at: Optional[datetime] = None
        self._organisations_processed: int = 0
        self._total_readings_generated: int = 0
        self._total_anomalies_generated: int = 0
        
        # Thread safety lock for state operations
        self._lock: threading.RLock = threading.RLock()

        # State tracking: org_id -> last_anomaly_timestamp
        self._last_anomaly_times: Dict[str, datetime] = {}
        # Cumulative metric tracking: (org_id, block_id, ward_id, sensor_type) -> last_value
        self._last_cumulative_values: Dict[Tuple[str, Optional[str], Optional[str], str], float] = {}

        # Demo Mode state — PER-ORGANISATION enrollment, never a global boolean.
        # Contains organisation_ids currently enrolled in demo mode. A sentinel
        # "*" means the demo scope is global (all active synthetic orgs). When
        # this set is non-empty, ONLY enrolled orgs generate data (strict scope
        # isolation); when empty, all active orgs generate on the normal cadence.
        # org_id -> {next_trigger_at: datetime, scenario_index: int}
        self._demo_orgs: set[str] = set()
        # Active demo modules per organisation: org_id -> set of active module names (e.g. {"energy"})
        self._demo_modules: Dict[str, set[str]] = {}
        self._demo_schedules: Dict[str, Dict[str, Any]] = {}
        # Demo round-robin rotation state: org_id -> {scope: next_target_index}
        self._demo_target_offsets: Dict[str, Dict[str, int]] = {}

    @property
    def is_running(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return True
        return self._running

    def _enroll_demo(self, organisation_id: Optional[str], module: Optional[str] = None) -> None:
        """Enroll an organisation into demo mode (None => global demo scope).
        If module is provided, demo mode data generation is restricted to that module.
        """
        with self._lock:
            key = organisation_id if organisation_id else "*"
            self._demo_orgs.add(key)
            if module:
                clean_mod = module.lower().strip()
                self._demo_modules.setdefault(key, set()).add(clean_mod)

    def _demo_active_for(self, organisation_id: str, module: Optional[str] = None) -> bool:
        """True when the organisation (and optional module) lies inside the active demo scope."""
        is_org_active = bool(self._demo_orgs) and (
            "*" in self._demo_orgs or organisation_id in self._demo_orgs
        )
        if not is_org_active:
            return False
        if module:
            clean_mod = module.lower().strip()
            active_mods = self._demo_modules.get(organisation_id) or self._demo_modules.get("*")
            if active_mods is not None and len(active_mods) > 0:
                return clean_mod in active_mods
        return True

    def start(
        self,
        interval_seconds: Optional[int] = None,
        demo_mode: bool = False,
        organisation_id: Optional[str] = None,
        module: Optional[str] = None,
    ) -> Dict[str, str | bool | int]:
        """
        Start background simulator worker thread.
        If already running, updates interval without spawning duplicate thread.
        demo_mode=True scopes fast-cadence scenario anomalies to the target
        organisation (organisation_id) and optional module (module).
        """
        if interval_seconds is not None:
            self.interval_seconds = interval_seconds

        if self._running and self._thread is not None and self._thread.is_alive():
            logger.info("Simulator already running. Updated interval to %ds.", self.interval_seconds)
            if demo_mode:
                self._enroll_demo(organisation_id, module=module)
            else:
                with self._lock:
                    if organisation_id:
                        self._demo_orgs.discard(organisation_id)
                        self._demo_modules.pop(organisation_id, None)
                        self._demo_schedules.pop(organisation_id, None)
                    else:
                        self._demo_orgs.clear()
                        self._demo_modules.clear()
                        self._demo_schedules.clear()
            return {"status": "already_running", "interval_seconds": self.interval_seconds}

        if demo_mode:
            self._enroll_demo(organisation_id, module=module)
        else:
            with self._lock:
                if organisation_id:
                    self._demo_orgs.discard(organisation_id)
                    self._demo_modules.pop(organisation_id, None)
                    self._demo_schedules.pop(organisation_id, None)
                else:
                    self._demo_orgs.clear()
                    self._demo_modules.clear()
                    self._demo_schedules.clear()

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="greennexa-synthetic-simulator",
        )
        self._thread.start()

        logger.info("SyntheticDataSimulator started with interval=%ds.", self.interval_seconds)
        return {"status": "started", "interval_seconds": self.interval_seconds}

    def stop(self, organisation_id: Optional[str] = None, module: Optional[str] = None) -> Dict[str, str | bool]:
        """Stop background simulator worker thread or unenroll an organisation/module.

        When organisation_id is provided, demo mode is turned OFF for that single
        organisation ONLY (or for the specified module if module is given).
        """
        if organisation_id:
            with self._lock:
                if module:
                    clean_mod = module.lower().strip()
                    if organisation_id in self._demo_modules:
                        self._demo_modules[organisation_id].discard(clean_mod)
                        if not self._demo_modules[organisation_id]:
                            self._demo_modules.pop(organisation_id, None)
                            self._demo_orgs.discard(organisation_id)
                            self._demo_schedules.pop(organisation_id, None)
                            self._demo_target_offsets.pop(organisation_id, None)
                            self._last_anomaly_times.pop(organisation_id, None)
                    elif "*" in self._demo_modules:
                        self._demo_modules["*"].discard(clean_mod)
                else:
                    self._demo_orgs.discard(organisation_id)
                    self._demo_modules.pop(organisation_id, None)
                    self._demo_schedules.pop(organisation_id, None)
                    self._demo_target_offsets.pop(organisation_id, None)
                    self._last_anomaly_times.pop(organisation_id, None)
                remaining = sorted(self._demo_orgs)
            if self._running and self._thread is not None and self._thread.is_alive():
                logger.info(
                    "Demo mode disabled for org=%s module=%s; worker stays alive (remaining demo scope: %s).",
                    organisation_id, module or "all", remaining or "none",
                )
                return {"status": "scoped_stopped"}
            return {"status": "scoped_stopped"}

        if not self._running and (self._thread is None or not self._thread.is_alive()):
            with self._lock:
                self._demo_orgs.clear()
                self._demo_modules.clear()
            self._demo_schedules.clear()
            return {"status": "already_stopped"}

        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

        with self._lock:
            self._demo_orgs.clear()
            self._demo_modules.clear()
        self._demo_schedules.clear()

        logger.info("SyntheticDataSimulator stopped.")
        return {"status": "stopped"}

    def status(self, organisation_id: Optional[str] = None, module: Optional[str] = None) -> Dict[str, Any]:
        """Return simulator operational state and metrics.

        demo_mode reflects the per-organisation (and optional module) demo enrollment.
        """
        now = _utcnow()
        running = self.is_running
        next_run = None
        if running and self._last_run_at:
            next_run_dt = self._last_run_at + timedelta(seconds=self.interval_seconds)
            next_run = next_run_dt.isoformat()
        elif running:
            next_run = now.isoformat()

        if organisation_id:
            demo_scope = self._demo_active_for(organisation_id, module=module)
            active_mods = list(self._demo_modules.get(organisation_id) or self._demo_modules.get("*") or [])
        else:
            demo_scope = bool(self._demo_orgs)
            active_mods = list(self._demo_modules.get("*") or [])
        generating = bool(running) and (not self._demo_orgs or demo_scope)

        return {
            "running": running,
            "interval_seconds": self.interval_seconds,
            "organisations_processed": self._organisations_processed,
            "last_run_at": self._last_run_at.isoformat() if self._last_run_at else None,
            "next_run_at": next_run,
            "total_readings_generated": self._total_readings_generated,
            "total_anomalies_generated": self._total_anomalies_generated,
            "demo_mode": demo_scope,
            "active_modules": sorted(active_mods),
            "generation_active": generating,
        }

    def _worker_loop(self) -> None:
        """Internal background thread loop.

        The cycle boundary is scheduled start-to-start (monotonic), so the wall
        clock gap between the start of cycle N and cycle N+1 is exactly
        `interval_seconds` even when a cycle takes time to process. Waiting a flat
        `interval_seconds` AFTER processing (the previous behaviour) stretched the
        real cadence to interval + processing time and drifted continuously.
        """
        import time as _time

        logger.info("Simulator background worker thread started (interval=%ds).", self.interval_seconds)
        # Anchor the grid BEFORE the first cycle so the cadence is measured from the
        # start of cycle 1, not from its completion.
        next_deadline = _time.monotonic() + self.interval_seconds
        try:
            self.run_cycle_with_session()
        except Exception as e:
            logger.error("Error in initial simulator cycle: %s", e, exc_info=True)

        while not self._stop_event.is_set():
            remaining = next_deadline - _time.monotonic()
            if remaining > 0 and self._stop_event.wait(timeout=remaining):
                break
            try:
                self.run_cycle_with_session()
            except Exception as e:
                logger.error("Error during synthetic data simulator cycle: %s", e, exc_info=True)
            # Never accumulate backlog: skip missed deadlines instead of firing a
            # burst of catch-up cycles that would break the exactly-one-per-cycle rule.
            next_deadline += self.interval_seconds
            now_mono = _time.monotonic()
            if next_deadline < now_mono:
                missed = int((now_mono - next_deadline) // self.interval_seconds) + 1
                next_deadline += missed * self.interval_seconds
        logger.info("Simulator background worker thread stopped.")

    async def _loop(self) -> None:
        """Asyncio loop compatibility alias."""
        while self._running:
            try:
                self.run_cycle_with_session()
            except Exception as e:
                logger.error("Error during synthetic data simulator cycle: %s", e, exc_info=True)

            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    def run_cycle_with_session(self) -> List[SensorReading]:
        """Convenience method to execute a cycle with a fresh DB session."""
        db = SessionLocal()
        try:
            return self.run_cycle(db)
        finally:
            db.close()

    def run_cycle(
        self,
        db: Session,
        current_time: Optional[datetime] = None,
        forced_anomaly_sensor: Optional[str] = None,
    ) -> List[SensorReading]:
        """
        Execute one generation cycle across all eligible organisations.
        Support block-wise generation for configured facility blocks.
        """
        now = current_time or _utcnow()
        active_orgs = db.query(Organisation).filter(Organisation.is_active == True).all()

        generated_readings: List[SensorReading] = []
        processed_count = 0

        for org in active_orgs:
            config = db.query(OrganisationSensorConfig).filter_by(organisation_id=org.id).first()
            if not config:
                config = OrganisationSensorConfig(
                    organisation_id=org.id,
                    data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
                    is_active=True,
                )
                db.add(config)
                db.commit()
                db.refresh(config)

            if not config.is_active or config.data_source == OrganisationSensorConfig.DATA_SOURCE_IOT:
                logger.info("Skipped synthetic generation for org=%s because data_source='%s'", org.id, config.data_source)
                continue

            enabled_sensors = config.enabled_sensors_list
            if not enabled_sensors:
                logger.info("Skipped synthetic generation for org=%s: no enabled sensors.", org.id)
                continue

            sim_date = config.current_simulated_date
            if not current_time:
                utc_now = _utcnow()
                org_now = datetime(
                    sim_date.year, sim_date.month, sim_date.day,
                    utc_now.hour, utc_now.minute, utc_now.second,
                    tzinfo=timezone.utc,
                )
            else:
                org_now = current_time

            processed_count += 1

            # Demo-scope isolation: while any organisation is enrolled in demo
            # mode, ONLY the enrolled organisations generate data. Every other
            # organisation stays frozen with zero new readings so the demo scope
            # is provably isolated (TEST A/B).
            if self._demo_orgs and not self._demo_active_for(org.id):
                logger.info("Skipped org=%s: outside active demo scope.", org.id)
                continue

            # Module-scope isolation: when demo mode is active for this organisation
            # with specific active module(s), restrict enabled_sensors to ONLY the
            # sensors corresponding to the active demo module(s).
            if self._demo_active_for(org.id):
                active_mods = self._demo_modules.get(org.id) or self._demo_modules.get("*")
                if active_mods:
                    allowed_sensors = set()
                    for m in active_mods:
                        allowed_sensors.update(self._sensors_for_module(m))
                    enabled_sensors = [s for s in enabled_sensors if s in allowed_sensors]
                    if not enabled_sensors:
                        logger.info("Skipped synthetic generation for org=%s: no enabled sensors in active demo modules (%s).", org.id, active_mods)
                        continue

            blocks = (
                db.query(FacilityBlock)
                .filter(FacilityBlock.organisation_id == org.id, FacilityBlock.is_active == True)
                .order_by(FacilityBlock.block_id.asc())
                .all()
            )

            # For municipalities, readings for natural-location modules are scoped
            # to active civic wards (ward_id), never to FacilityBlocks.
            wards: List[MunicipalityWard] = []
            if "municipality" in (org.org_type or "").lower():
                wards = (
                    db.query(MunicipalityWard)
                    .filter(MunicipalityWard.municipality_id == org.id, MunicipalityWard.is_active == True)
                    .order_by(MunicipalityWard.ward_number.asc())
                    .all()
                )

            # Anomaly evaluation (natural probability path + demo scenario path)
            anomaly_sensor_selected: Optional[str] = None
            anomaly_scope: Optional[str] = None
            anomaly_target: Optional[Any] = None

            is_forced = forced_anomaly_sensor is not None and forced_anomaly_sensor in enabled_sensors
            last_anomaly_dt = self._last_anomaly_times.get(org.id)

            can_generate_anomaly = True
            if last_anomaly_dt is not None:
                gap = (now - last_anomaly_dt).total_seconds()
                if gap < self.ANOMALY_MIN_GAP_SECONDS:
                    can_generate_anomaly = False

            if can_generate_anomaly:
                if is_forced:
                    anomaly_sensor_selected = forced_anomaly_sensor
                elif not self._demo_active_for(org.id):
                    # Natural probability anomalies apply ONLY outside the active
                    # demo scope. Inside demo scope the scenario path below is the
                    # sole anomaly source, guaranteeing EXACTLY ONE anomaly per
                    # completed 30s cycle (deterministic demo cadence).
                    candidates = []
                    for s_type in enabled_sensors:
                        prob = self.DEFAULT_ANOMALY_PROBABILITIES.get(s_type, 0.03)
                        if random.random() < prob:
                            candidates.append(s_type)
                    if candidates:
                        anomaly_sensor_selected = random.choice(candidates)

            # Demo Mode scenario anomalies fire exactly once per completed 30s
            # cycle (see _consume_demo_anomaly) and only when a forced anomaly did
            # not short-circuit this cycle, preserving the single-anomaly invariant.
            demo_scenario_fired = False
            if anomaly_sensor_selected is None and self._demo_active_for(org.id) and not is_forced:
                demo_sensor, demo_scope = self._consume_demo_anomaly(
                    db=db,
                    org=org,
                    enabled_sensors=enabled_sensors,
                    now=now,
                    blocks=blocks,
                    wards=wards,
                )
                if demo_sensor:
                    anomaly_sensor_selected = demo_sensor
                    anomaly_scope = demo_scope
                    demo_scenario_fired = True
                    logger.info(
                        "Demo scenario anomaly triggered for org=%s on sensor='%s' (scope=%s)",
                        org.id, demo_sensor, demo_scope,
                    )

            if anomaly_sensor_selected:
                self._last_anomaly_times[org.id] = now
                if anomaly_scope is None:
                    anomaly_scope, anomaly_target = self._resolve_anomaly_scope(
                        org, anomaly_sensor_selected, blocks, wards
                    )
                elif demo_scenario_fired:
                    anomaly_target = self._pick_demo_scope_target(org, anomaly_scope, blocks, wards)
                else:
                    anomaly_target = self._pick_scope_target(anomaly_scope, blocks, wards)
                logger.info(
                    "Anomaly triggered for org=%s on sensor='%s' (scope=%s, target=%s)",
                    org.id,
                    anomaly_sensor_selected,
                    anomaly_scope,
                    getattr(anomaly_target, "block_id", getattr(anomaly_target, "ward_number", "org-level")),
                )

            generated_readings.extend(
                self._generate_org_readings(
                    db=db,
                    org=org,
                    config=config,
                    enabled_sensors=enabled_sensors,
                    now=org_now,
                    sim_date=sim_date,
                    anomaly_sensor=anomaly_sensor_selected,
                    anomaly_scope=anomaly_scope,
                    anomaly_target=anomaly_target,
                    forced_anomaly=is_forced,
                )
            )

        db.commit()

        self._last_run_at = now
        self._organisations_processed = processed_count
        logger.info(
            "Completed simulator cycle at %s: processed %d orgs, generated %d readings (%d anomalies).",
            now.isoformat(),
            processed_count,
            len(generated_readings),
            sum(1 for r in generated_readings if r.is_anomaly),
        )

        return generated_readings

    # ------------------------------------------------------------------
    # Location-aware generation & Demo Mode scenario scheduling helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_municipality(org: Organisation) -> bool:
        return "municipality" in (org.org_type or "").lower()

    def _resolve_anomaly_scope(
        self,
        org: Organisation,
        sensor_type: str,
        blocks: List[FacilityBlock],
        wards: List[MunicipalityWard],
    ) -> Tuple[str, Optional[Any]]:
        """Resolve the location scope + target for a naturally triggered anomaly."""
        s = (sensor_type or "").lower().strip()
        if s in WHOLE_ORG_DEFAULT_MODULES:
            return ("org", None)
        if s in NATURAL_LOCATION_MODULES:
            if wards:
                return ("ward", random.choice(wards))
            return ("org", None)
        if blocks:
            return ("block", random.choice(blocks))
        return ("org", None)

    def _pick_scope_target(self, scope: str, blocks: List[FacilityBlock], wards: List[MunicipalityWard]) -> Optional[Any]:
        if scope == "ward" and wards:
            return random.choice(wards)
        if scope == "block" and blocks:
            return random.choice(blocks)
        return None

    def _pick_demo_scope_target(self, org: Organisation, scope: str, blocks: List[FacilityBlock], wards: List[MunicipalityWard]) -> Optional[Any]:
        """
        Round-robin location selection for Demo scenario anomalies so anomalies
        hop deterministically across wards (and blocks) instead of randomly
        repeating the same target while the demo rotates through scenarios.
        """
        idx_map = self._demo_target_offsets.setdefault(org.id, {})
        idx = idx_map.get(scope, 0)
        if scope == "ward" and wards:
            target = wards[idx % len(wards)]
            idx_map[scope] = idx + 1
            return target
        if scope == "block" and blocks:
            target = blocks[idx % len(blocks)]
            idx_map[scope] = idx + 1
            return target
        return None

    def _anomaly_match_key(self, scope: str, target: Optional[Any]) -> Tuple[str, Optional[str]]:
        """Key used to decide which generated reading carries the anomaly flag."""
        if scope == "ward":
            return ("ward", getattr(target, "ward_number", None))
        if scope == "block":
            return ("block", getattr(target, "block_id", None))
        return ("org", None)

    def _consume_demo_anomaly(
        self,
        db: Session,
        org: Organisation,
        enabled_sensors: List[str],
        now: datetime,
        blocks: List[FacilityBlock],
        wards: List[MunicipalityWard],
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Evaluate whether a Demo Mode scenario anomaly is due for the organisation.
        Returns (sensor_type, scope) when fired, else (None, None).
        """
        sched = self._demo_schedules.get(org.id)
        if not sched:
            # Prime the schedule: the FIRST Demo scenario anomaly fires on the
            # completion of the NEXT 30s cycle (so the first persisted anomaly
            # arrives ~30s after the first completed demo cycle).
            self._demo_schedules[org.id] = {
                "next_trigger_at": now + timedelta(seconds=self.interval_seconds),
                "scenario_index": 0,
            }
            return (None, None)

        if now < sched["next_trigger_at"]:
            # Not yet at a completed cycle boundary: nothing fires this cycle.
            # This is what makes mid-cycle polling duplicate-free.
            return (None, None)

        seq_len = len(self.DEMO_SCENARIO_SEQUENCE)
        idx = sched["scenario_index"]
        for _ in range(seq_len):
            scenario = self.DEMO_SCENARIO_SEQUENCE[idx % seq_len]
            idx += 1
            sensor = next((s for s in scenario["sensors"] if s in enabled_sensors), None)
            if sensor is None:
                continue
            scope = scenario["scope"]
            # Municipality civic scenarios apply to civic wards, never to council
            # office blocks or the organisation as a whole. This keeps Energy /
            # Water / Waste / Air Quality flaws visible on the ward metrics page.
            if "municipality" in (org.org_type or "").lower() and wards:
                if sensor in {"water", "waste", "energy", "air_quality"} and scope in ("block", "org"):
                    scope = "ward"
            if scope == "ward" and not wards:
                scope = "org"
            elif scope == "block" and not blocks:
                scope = "org"
            sched["scenario_index"] = idx % seq_len
            # Fire exactly one Demo anomaly on this completed 30s cycle; the next
            # one becomes due on the next completed cycle.
            sched["next_trigger_at"] = now + timedelta(seconds=self.interval_seconds)
            return (sensor, scope)

        # No enabled scenario sensor this cycle; retry on the next cycle without
        # advancing the rotation so every enabled scenario is still honoured.
        sched["scenario_index"] = idx % seq_len
        sched["next_trigger_at"] = now + timedelta(seconds=self.interval_seconds)
        return (None, None)

    def _generate_org_readings(
        self,
        db: Session,
        org: Organisation,
        config: OrganisationSensorConfig,
        enabled_sensors: List[str],
        now: datetime,
        sim_date: date,
        anomaly_sensor: Optional[str],
        anomaly_scope: Optional[str],
        anomaly_target: Optional[Any],
        forced_anomaly: bool = False,
    ) -> List[SensorReading]:
        """
        Generate one cycle of readings for an organisation with location-aware scoping:

        - Block-wise modules   -> one reading per active FacilityBlock (org level if none).
        - Natural-location     -> one reading per active MunicipalityWard for municipalities
                                  (org level otherwise). ward_id is always set on ward readings.
        - Whole-org default    -> single org-level reading.
        """
        blocks = (
            db.query(FacilityBlock)
            .filter(FacilityBlock.organisation_id == org.id, FacilityBlock.is_active == True)
            .order_by(FacilityBlock.block_id.asc())
            .all()
        )
        wards: List[MunicipalityWard] = []
        if "municipality" in (org.org_type or "").lower():
            wards = (
                db.query(MunicipalityWard)
                .filter(MunicipalityWard.municipality_id == org.id, MunicipalityWard.is_active == True)
                .order_by(MunicipalityWard.ward_number.asc())
                .all()
            )

        targets: List[Tuple[str, Optional[FacilityBlock], Optional[MunicipalityWard]]] = []
        is_muni = "municipality" in (org.org_type or "").lower()
        demo_active = self._demo_active_for(org.id)
        # During a municipality demo, Energy / Water / Waste / Air Quality are ALSO
        # generated per civic ward so the Ward Metrics page shows live changing data
        # (BUG-05). Own-office blocks keep their block-scoped readings on top.
        extra_ward_civic = {"energy", "water", "waste", "air_quality"} if (is_muni and demo_active and wards) else set()
        active_mods = self._demo_modules.get(org.id) or self._demo_modules.get("*")
        if active_mods and extra_ward_civic:
            allowed_civic_sensors = set()
            for m in active_mods:
                allowed_civic_sensors.update(self._sensors_for_module(m))
            extra_ward_civic = extra_ward_civic.intersection(allowed_civic_sensors)
        for sensor_type in enabled_sensors:
            if sensor_type in NATURAL_LOCATION_MODULES:
                if wards:
                    targets.extend((sensor_type, None, w) for w in wards)
                else:
                    targets.append((sensor_type, None, None))
            elif sensor_type in WHOLE_ORG_DEFAULT_MODULES:
                if sensor_type == "air_quality" and sensor_type in extra_ward_civic:
                    targets.extend((sensor_type, None, w) for w in wards)
                else:
                    targets.append((sensor_type, None, None))
            elif sensor_type in extra_ward_civic:
                targets.extend((sensor_type, None, w) for w in wards)
                if blocks:
                    targets.extend((sensor_type, b, None) for b in blocks)
                else:
                    targets.append((sensor_type, None, None))
            else:
                if blocks:
                    targets.extend((sensor_type, b, None) for b in blocks)
                else:
                    targets.append((sensor_type, None, None))

        if anomaly_sensor and anomaly_scope:
            anomaly_key = self._anomaly_match_key(anomaly_scope, anomaly_target)
        else:
            anomaly_key = None

        sensor_configs_dict = config.sensor_configs_dict
        generated_readings: List[SensorReading] = []

        for sensor_type, target_block, target_ward in targets:
            b_id = target_block.block_id if target_block else None
            w_id = target_ward.ward_number if target_ward else None

            # The anomaly match key must use the ACTUAL resolved target location so
            # ward-targeted civic anomalies (energy/water/waste/AQ) attach to the
            # right ward readings instead of being derived from the sensor's static
            # scope mapping.
            if target_ward is not None:
                this_key = ("ward", target_ward.ward_number)
            elif target_block is not None:
                this_key = ("block", target_block.block_id)
            else:
                this_key = ("org", None)

            is_anomaly = bool(
                anomaly_sensor == sensor_type
                and anomaly_key is not None
                and anomaly_key == this_key
            )
            is_forced = is_anomaly and forced_anomaly

            if target_ward is not None:
                facility_label = target_ward.ward_name or f"Ward {target_ward.ward_number}"
            elif target_block is not None:
                facility_label = target_block.block_name
            else:
                facility_label = org.facility_name or org.name

            val, severity, expected_min, expected_max, unit, baseline, warn_pct, crit_pct = self._generate_block_reading_value(
                db=db,
                org_id=org.id,
                block_id=b_id,
                ward_id=w_id,
                sensor_type=sensor_type,
                is_anomaly=is_anomaly,
                sensor_configs=sensor_configs_dict,
                forced_anomaly=is_forced,
                sim_date=sim_date,
            )

            if is_anomaly:
                self._total_anomalies_generated += 1

            reading = SensorReading(
                organisation_id=org.id,
                block_id=b_id,
                ward_id=w_id,
                facility_id=facility_label,
                sensor_type=sensor_type,
                value=val,
                unit=unit,
                source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
                timestamp=now,
                created_at=_utcnow(),
                is_anomaly=is_anomaly,
                anomaly_severity=severity,
            )
            db.add(reading)
            generated_readings.append(reading)
            self._total_readings_generated += 1

            # Anomaly & Recommendation handling via unified Detection Pipeline
            if is_anomaly:
                try:
                    from app.services.anomaly_detection import anomaly_detection_service
                    anomaly_detection_service.process_single_reading(
                        db=db, reading=reading, config=config,
                        # Demo scenario anomalies must ALWAYS persist as a brand-new
                        # AnomalyRecord (+ linked AIRecommendation) every completed
                        # 30s cycle, bypassing the 5-minute same-location dedup so the
                        # demo cadence remains exactly-one-new-record-per-cycle.
                        force_new=(demo_active or forced_anomaly),
                    )
                except Exception as anom_err:
                    logger.warning("Simulator reading anomaly processing error: %s", anom_err)

            # NOTE: there is deliberately NO waste (or any metric) auto-resolution
            # here. Anomalies are persisted once and stay active until a user
            # explicitly RESOLVES or DISMISSES them via the anomaly lifecycle API.
            # Auto-resolving on the next normal reading silently cleared open
            # anomalies (and their recommendations) without any user action.

        return generated_readings

    def _generate_block_reading_value(
        self,
        db: Session,
        org_id: str,
        block_id: Optional[str],
        sensor_type: str,
        is_anomaly: bool,
        sensor_configs: Dict[str, Dict[str, Any]],
        forced_anomaly: bool = False,
        sim_date: Optional[date] = None,
        ward_id: Optional[str] = None,
    ) -> Tuple[float, Optional[str], float, float, str, float, float, float]:
        """
        Generate synthetic reading value respecting cumulative vs live metrics.
        Returns: (val, severity, expected_min, expected_max, unit, baseline, warning_pct, critical_pct)
        """
        s_clean = sensor_type.lower().strip()
        cfg = sensor_configs.get(
            s_clean,
            self.SENSOR_CONFIGS.get(
                s_clean,
                {"baseline": 100.0, "warning_threshold": 15.0, "critical_threshold": 30.0, "unit": ""},
            ),
        )

        baseline = float(cfg.get("baseline", 100.0))
        warning_pct = float(cfg.get("warning_threshold", 15.0))
        critical_pct = float(cfg.get("critical_threshold", 30.0))
        unit = str(cfg.get("unit", ""))

        warning_delta = baseline * (warning_pct / 100.0)
        critical_delta = baseline * (critical_pct / 100.0)

        expected_min = round(baseline - warning_delta, 2)
        expected_max = round(baseline + warning_delta, 2)

        # 1. WASTE SPECIAL MODEL — Fill level percentage (0 - 100%)
        if s_clean == "waste":
            unit = "%"
            expected_min = 0.0
            expected_max = 85.0
            if is_anomaly:
                val = 100.0
                severity = AnomalyRecord.SEVERITY_CRITICAL
            else:
                val = round(random.uniform(15.0, 85.0), 1)
                severity = None
            return (val, severity, expected_min, expected_max, unit, baseline, warning_pct, critical_pct)

        # 2. CUMULATIVE METRICS (Energy, Water) — Monotonic non-decreasing progression
        is_cumulative = s_clean in {"energy", "water"}
        if is_cumulative:
            # Cumulative progression is tracked PER PHYSICAL LOCATION. Keying only on
            # (org, block_id, sensor) merged every ward into one counter, because ward
            # readings carry block_id=None: all wards shared a single accumulator and
            # the highest ward polluted the next ward's value (and the org-level
            # reading). ward_id is now part of the key.
            key = (org_id, block_id, ward_id, s_clean)
            with self._lock:
                last_val = self._last_cumulative_values.get(key)
                is_initial = False
                if last_val is None:
                    # Query DB for the latest value at THIS exact location on THIS
                    # simulated day. The ward_id predicate is mandatory: a plain
                    # `block_id IS NULL` filter also matches every ward reading.
                    query = db.query(SensorReading).filter(
                        SensorReading.organisation_id == org_id,
                        SensorReading.sensor_type == s_clean,
                        SensorReading.block_id == block_id,
                        SensorReading.ward_id == ward_id,
                    )
                    if sim_date is not None:
                        query = query.filter(func.date(SensorReading.timestamp) == sim_date.isoformat())
                    latest_reading = query.order_by(SensorReading.timestamp.desc()).first()

                    if latest_reading:
                        last_val = latest_reading.value
                    else:
                        # Fresh initialization strictly from current configuration baseline
                        last_val = baseline
                        is_initial = True

                if is_anomaly:
                    if forced_anomaly:
                        inc = critical_delta * random.uniform(1.2, 1.8)
                        severity = AnomalyRecord.SEVERITY_HIGH
                    else:
                        inc = critical_delta * random.uniform(1.5, 2.5)
                        severity = AnomalyRecord.SEVERITY_CRITICAL
                else:
                    if is_initial:
                        # Initial cycle starts directly at current baseline
                        inc = 0.0
                    else:
                        inc = random.uniform(2.0, max(5.0, warning_delta * 0.3))
                    severity = None

                val = round(last_val + inc, 2)
                self._last_cumulative_values[key] = val
                return (val, severity, expected_min, expected_max, unit, baseline, warning_pct, critical_pct)

        # 3. LIVE / VARIABLE METRICS (Temperature, Air Quality, CO2, Humidity, Traffic, Parking, Assets, Safety, Climate)
        if not is_anomaly:
            fluctuation = random.uniform(-0.75 * warning_delta, 0.75 * warning_delta)
            val = round(baseline + fluctuation, 2)
            if baseline >= 0 and val < 0 and s_clean not in {"temperature", "climate"}:
                val = 0.0
            return (val, None, expected_min, expected_max, unit, baseline, warning_pct, critical_pct)
        else:
            if forced_anomaly:
                add_delta = warning_delta + (critical_delta - warning_delta) * 0.5
                val = round(baseline + add_delta, 2)
                severity = AnomalyRecord.SEVERITY_HIGH
            else:
                is_critical = random.random() < 0.4
                mult = random.choice([1, -1])
                if is_critical:
                    add_delta = critical_delta * random.uniform(1.1, 1.5)
                    val = round(baseline + mult * add_delta, 2)
                    severity = AnomalyRecord.SEVERITY_CRITICAL
                else:
                    add_delta = warning_delta + (critical_delta - warning_delta) * random.uniform(0.15, 0.85)
                    val = round(baseline + mult * add_delta, 2)
                    severity = AnomalyRecord.SEVERITY_HIGH

            if baseline >= 0 and val < 0 and s_clean not in {"temperature", "climate"}:
                val = 0.0
            return (val, severity, expected_min, expected_max, unit, baseline, warning_pct, critical_pct)

    def _build_recommendation_summary(self, sensor_type: str, location: str, val: float, baseline: float, dev_pct: float) -> str:
        s = sensor_type.lower()
        if s == "energy":
            return f"Inspect high-load equipment in {location}. Consider reducing non-essential HVAC/AC usage temporarily and check equipment operation."
        elif s == "water":
            return f"Inspect {location} for possible leakage or abnormal water usage."
        elif s == "waste":
            return f"Prioritize waste collection for {location}."
        elif s == "air_quality":
            return f"Inspect ventilation and check for a possible local pollution source at {location}."
        elif s in {"temperature", "climate"}:
            return f"Adjust thermostat controls and inspect HVAC cooling performance in {location}."
        elif s == "co2":
            return f"Increase fresh air ventilation in {location} to reduce CO2 concentration."
        elif s == "water_flow":
            return f"Inspect pipeline distribution network in {location} for abnormal flow surge or pipe leakage."
        elif s == "water_level":
            return f"Inspect reservoir water level in {location} due to reserve depletion or supply disruption."
        elif s == "sewage_level":
            return f"Inspect drainage sump and stormwater channels in {location} for blockage or overflow risk."
        elif s == "traffic":
            return f"Manage vehicular traffic congestion in {location} with adaptive signal timing and diversion advisory."
        elif s == "parking":
            return f"Civic parking capacity nearing 100% in {location}. Redirect inbound vehicles to auxiliary bays."
        elif s == "rainfall":
            return f"High precipitation rate at {location}. Activate stormwater retention protocols."
        elif s in {"equipment_asset", "assets"}:
            return f"Asset health score degraded at {location}. Schedule preventive electromechanical inspection."
        elif s == "vibration":
            return f"Abnormal rotational vibration detected in {location}. Inspect bearing mounts and shaft alignment."
        elif s == "pressure":
            return f"System fluid pressure threshold breach in {location}. Check pressure relief valves."
        elif s == "machine_temperature":
            return f"Elevated machine bearing temperature in {location}. Verify cooling fans and lubricant levels."
        else:
            return f"Inspect {sensor_type} indicators at {location} and adjust operational parameters."

    def _build_possible_causes(self, sensor_type: str, location: str) -> str:
        s = sensor_type.lower()
        if s == "water":
            return f"Possible plumbing leakage in {location}|Faulty fixture or tap|Abnormal water equipment draw"
        elif s == "waste":
            return f"Waste container at critical capacity in {location}|High disposal rate|Collection schedule backlog"
        elif s == "air_quality":
            return f"Elevated particulate/pollutant levels in {location}|Poor ventilation damper performance"
        elif s in {"temperature", "climate"}:
            return f"Thermostat miscalibration in {location}|HVAC cooling or heating system failure"
        elif s == "co2":
            return f"High occupancy in {location}|Insufficient fresh air ventilation"
        elif s == "humidity":
            return f"HVAC dehumidification fault in {location}|Moisture ingress"
        elif s == "energy":
            return f"High-load operation at {location}|Unscheduled electrical consumption|HVAC/AC spike"
        elif s == "water_flow":
            return f"Main distribution pipeline burst in {location}|Gate valve failure|Downstream overflow"
        elif s == "water_level":
            return f"Storage sump inlet supply disruption|High drawdown rate|Tank structural leakage in {location}"
        elif s == "sewage_level":
            return f"Drain intake grate blocked by debris in {location}|Stormwater flash surge|Sump lift pump trip"
        elif s == "traffic":
            return f"Peak commuter influx in {location}|Roadway obstruction or lane closure|Intersection bottleneck"
        elif s == "parking":
            return f"Civic event footfall surge|Commercial zone parking overflow at {location}"
        elif s == "rainfall":
            return f"Heavy localized monsoon storm front|Urban cloudburst at {location}"
        elif s in {"equipment_asset", "assets"}:
            return f"Electromechanical wear|Thermal fatigue|Pending overhaul schedule for equipment in {location}"
        elif s == "vibration":
            return f"Shaft misalignment|Bearing race pitting|Foundation bolt loosening in {location}"
        elif s == "pressure":
            return f"Pressure relief valve obstruction|Pumping head discharge excess|Downstream valve closure in {location}"
        elif s == "machine_temperature":
            return f"Motor winding thermal overload|Cooling fan clogging|Lubrication oil breakdown in {location}"
        else:
            return f"Sensor threshold breach at {location}|Abnormal operational variance"

    def _build_recommended_actions(self, sensor_type: str, location: str) -> str:
        s = sensor_type.lower()
        if s == "water":
            return f"Inspect {location} for pipe leaks or open taps|Check shut-off valves and inspect plumbing infrastructure|Verify abnormal consumption"
        elif s == "waste":
            return f"Prioritize waste collection for {location}|Deploy additional disposal capacity|Inspect full bins"
        elif s == "air_quality":
            return f"Inspect ventilation and air filters in {location}|Check for local pollution source"
        elif s in {"temperature", "climate"}:
            return f"Adjust thermostat controls in {location}|Inspect HVAC cooling performance"
        elif s == "co2":
            return f"Increase fresh air ventilation in {location}|Inspect damper controls"
        elif s == "humidity":
            return f"Inspect HVAC dehumidifier and ventilation controls in {location}"
        elif s == "energy":
            return f"Inspect high-load equipment in {location}|Check equipment operation and reduce non-essential load temporarily"
        elif s == "water_flow":
            return f"Dispatch field technician to inspect pipeline flow meters in {location}|Verify shut-off valve positions"
        elif s == "water_level":
            return f"Activate auxiliary water feed line for {location}|Verify tank level sensor calibration"
        elif s == "sewage_level":
            return f"Deploy sanitation maintenance crew to clear intake grates at {location}|Start backup lift pump"
        elif s == "traffic":
            return f"Broadcast digital traffic diversion advisory for {location}|Extend green signal phase on congested arterial"
        elif s == "parking":
            return f"Update roadside VMS parking guidance displays for {location}|Direct vehicles to overflow parking zones"
        elif s == "rainfall":
            return f"Alert civic emergency drainage operations center|Inspect low-lying retention basins in {location}"
        elif s in {"equipment_asset", "assets"}:
            return f"Schedule immediate electromechanical inspection in {location}|Review equipment operational logs"
        elif s == "vibration":
            return f"Perform laser shaft alignment check in {location}|Inspect bearing lubrication and mounts"
        elif s == "pressure":
            return f"Check pressure relief valve function in {location}|Throttle discharge booster pump"
        elif s == "machine_temperature":
            return f"Clean motor cooling ducts in {location}|Check winding thermal sensor and oil reservoir"
        else:
            return f"Inspect {sensor_type} equipment in {location}|Check calibration and operational parameters"

    def run_cycle_for_org(
        self,
        db: Session,
        organisation_id: str,
        forced_anomaly_sensor: Optional[str] = None,
        ignore_gap: bool = False,
        current_time: Optional[datetime] = None,
        allow_random_anomaly: bool = False,
        module: Optional[str] = None,
    ) -> List[SensorReading]:
        """
        Execute one generation cycle specifically for one organisation.
        """
        now = current_time or _utcnow()
        org = db.query(Organisation).filter_by(id=organisation_id, is_active=True).first()
        if not org:
            return []

        config = db.query(OrganisationSensorConfig).filter_by(organisation_id=organisation_id).first()
        if not config:
            config = OrganisationSensorConfig(
                organisation_id=organisation_id,
                data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
                is_active=True,
            )
            db.add(config)
            db.commit()
            db.refresh(config)

        if not config.is_active or config.data_source == OrganisationSensorConfig.DATA_SOURCE_IOT:
            return []

        enabled_sensors = config.enabled_sensors_list
        if not enabled_sensors:
            return []

        # Check if module restriction applies (from param or active demo modules)
        active_mods: set[str] = set()
        if module:
            active_mods.add(module.lower().strip())
        elif self._demo_active_for(org.id):
            org_mods = self._demo_modules.get(org.id) or self._demo_modules.get("*")
            if org_mods:
                active_mods = set(org_mods)

        if active_mods:
            allowed_sensors = set()
            for m in active_mods:
                allowed_sensors.update(self._sensors_for_module(m))
            enabled_sensors = [s for s in enabled_sensors if s in allowed_sensors]
            if not enabled_sensors:
                return []

        sim_date = config.current_simulated_date
        if not current_time:
            utc_now = _utcnow()
            now = datetime(
                sim_date.year, sim_date.month, sim_date.day,
                utc_now.hour, utc_now.minute, utc_now.second,
                tzinfo=timezone.utc,
            )
        else:
            now = current_time

        blocks = (
            db.query(FacilityBlock)
            .filter(FacilityBlock.organisation_id == org.id, FacilityBlock.is_active == True)
            .order_by(FacilityBlock.block_id.asc())
            .all()
        )

        wards: List[MunicipalityWard] = []
        if "municipality" in (org.org_type or "").lower():
            wards = (
                db.query(MunicipalityWard)
                .filter(MunicipalityWard.municipality_id == org.id, MunicipalityWard.is_active == True)
                .order_by(MunicipalityWard.ward_number.asc())
                .all()
            )

        anomaly_sensor_selected: Optional[str] = None
        if forced_anomaly_sensor and forced_anomaly_sensor in enabled_sensors:
            if ignore_gap:
                anomaly_sensor_selected = forced_anomaly_sensor
            else:
                last_anomaly_dt = self._last_anomaly_times.get(org.id)
                can_generate_anomaly = True
                if last_anomaly_dt is not None:
                    gap = (now - last_anomaly_dt).total_seconds()
                    if gap < self.ANOMALY_MIN_GAP_SECONDS:
                        can_generate_anomaly = False

                if can_generate_anomaly:
                    anomaly_sensor_selected = forced_anomaly_sensor
        elif allow_random_anomaly:
            last_anomaly_dt = self._last_anomaly_times.get(org.id)
            can_generate_anomaly = True
            if last_anomaly_dt is not None:
                gap = (now - last_anomaly_dt).total_seconds()
                if gap < self.ANOMALY_MIN_GAP_SECONDS:
                    can_generate_anomaly = False

            if can_generate_anomaly:
                candidates = []
                for s_type in enabled_sensors:
                    prob = self.DEFAULT_ANOMALY_PROBABILITIES.get(s_type, 0.03)
                    if random.random() < prob:
                        candidates.append(s_type)
                if candidates:
                    anomaly_sensor_selected = random.choice(candidates)

        anomaly_scope: Optional[str] = None
        anomaly_target: Optional[Any] = None

        if anomaly_sensor_selected:
            self._last_anomaly_times[org.id] = now
            anomaly_scope, anomaly_target = self._resolve_anomaly_scope(
                org, anomaly_sensor_selected, blocks, wards
            )
            logger.info(
                "Anomaly triggered for org=%s on sensor='%s' (scope=%s, target=%s)",
                org.id,
                anomaly_sensor_selected,
                anomaly_scope,
                getattr(anomaly_target, "block_id", getattr(anomaly_target, "ward_number", "org-level")),
            )

        generated_readings = self._generate_org_readings(
            db=db,
            org=org,
            config=config,
            enabled_sensors=enabled_sensors,
            now=now,
            sim_date=sim_date,
            anomaly_sensor=anomaly_sensor_selected,
            anomaly_scope=anomaly_scope,
            anomaly_target=anomaly_target,
            forced_anomaly=forced_anomaly_sensor is not None,
        )

        db.commit()
        self._last_run_at = now
        return generated_readings

    def reset_simulator_state(self, organisation_id: str) -> None:
        """
        Safely reset all simulator runtime state for a specific organisation.
        Purges in-memory cumulative tracking, anomaly timing, and cached runtime values.
        Next generation cycle will re-initialize strictly from current saved configuration.
        """
        with self._lock:
            keys_to_remove = [k for k in self._last_cumulative_values if k[0] == organisation_id]
            for k in keys_to_remove:
                self._last_cumulative_values.pop(k, None)

            self._last_anomaly_times.pop(organisation_id, None)
            self._demo_schedules.pop(organisation_id, None)
            self._demo_target_offsets.pop(organisation_id, None)
            self._demo_modules.pop(organisation_id, None)
            self._demo_orgs.discard(organisation_id)
            logger.info("Simulator runtime state reset for organisation '%s' (cleared %d cumulative keys).", organisation_id, len(keys_to_remove))

    def reset_all_simulator_state(self) -> None:
        """
        Safely reset all simulator runtime state across all organisations.
        Used by Super Admin Clear All Data.
        """
        with self._lock:
            self._last_cumulative_values.clear()
            self._last_anomaly_times.clear()
            self._demo_schedules.clear()
            self._demo_target_offsets.clear()
            self._demo_modules.clear()
            self._demo_orgs.clear()
            self._organisations_processed = 0
            self._total_readings_generated = 0
            self._total_anomalies_generated = 0
            self._last_run_at = None
            logger.info("All simulator runtime state reset platform-wide.")

    def reset_demo_data(self, db: Session, organisation_id: str) -> Dict[str, int]:
        """
        Safely resets synthetic readings and anomaly records for a target organisation.
        Leaves non-synthetic readings (if any) and org settings intact.
        """
        readings_deleted = db.query(SensorReading).filter(
            SensorReading.organisation_id == organisation_id,
            SensorReading.source == OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        ).delete(synchronize_session=False)

        anomalies_deleted = db.query(AnomalyRecord).filter(
            AnomalyRecord.organisation_id == organisation_id,
        ).delete(synchronize_session=False)

        self.reset_simulator_state(organisation_id)

        db.commit()
        logger.info("Reset demo data for org=%s: deleted %d readings, %d anomalies.", organisation_id, readings_deleted, anomalies_deleted)
        return {
            "readings_deleted": readings_deleted,
            "anomalies_deleted": anomalies_deleted,
        }

    def get_simulated_day(self, db: Session, organisation_id: str) -> Dict[str, Any]:
        """Get current simulated date and day name for an organisation."""
        config = (
            db.query(OrganisationSensorConfig)
            .filter(OrganisationSensorConfig.organisation_id == organisation_id)
            .first()
        )
        sim_date = config.current_simulated_date if config else OrganisationSensorConfig.DEFAULT_SIMULATED_DATE
        day_name = sim_date.strftime("%a").upper()
        return {
            "organisation_id": organisation_id,
            "simulated_date": sim_date.isoformat(),
            "day_name": day_name,
            "day_of_week": day_name,
            "date_display": f"{sim_date.strftime('%d %b %Y')} / {day_name}",
        }

    def change_simulated_day(self, db: Session, organisation_id: str, days: int = 1) -> Dict[str, Any]:
        """
        Advance simulated date by N calendar day(s) for the organisation.
        Preserves all historical telemetry, anomalies, recommendations, and configurations.
        Purges daily simulator runtime cache so the new day starts from the current configuration baseline.
        """
        config = (
            db.query(OrganisationSensorConfig)
            .filter(OrganisationSensorConfig.organisation_id == organisation_id)
            .first()
        )
        if not config:
            org_exists = db.query(Organisation.id).filter(Organisation.id == organisation_id).first()
            if not org_exists:
                cur_date = OrganisationSensorConfig.DEFAULT_SIMULATED_DATE + timedelta(days=days)
                day_name = cur_date.strftime("%a").upper()
                return {
                    "organisation_id": organisation_id,
                    "previous_date": OrganisationSensorConfig.DEFAULT_SIMULATED_DATE.isoformat(),
                    "simulated_date": cur_date.isoformat(),
                    "day_name": day_name,
                    "day_of_week": day_name,
                    "date_display": f"{cur_date.strftime('%d %b %Y')} / {day_name}",
                    "message": f"Simulated day advanced to {cur_date.isoformat()} ({day_name}).",
                }
            config = OrganisationSensorConfig(
                organisation_id=organisation_id,
                data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
                is_active=True,
            )
            db.add(config)
            db.flush()

        prev_date = config.current_simulated_date
        new_date = config.advance_simulated_date(days)
        db.commit()

        # Reset in-memory runtime cache for this organisation
        self.reset_simulator_state(organisation_id)

        day_name = new_date.strftime("%a").upper()
        logger.info(
            "Day change executed for org=%s: %s (%s) -> %s (%s). Simulator state reset to current baseline.",
            organisation_id,
            prev_date.isoformat(),
            prev_date.strftime("%a").upper(),
            new_date.isoformat(),
            day_name,
        )
        return {
            "organisation_id": organisation_id,
            "previous_date": prev_date.isoformat(),
            "simulated_date": new_date.isoformat(),
            "day_name": day_name,
            "day_of_week": day_name,
            "date_display": f"{new_date.strftime('%d %b %Y')} / {day_name}",
            "message": f"Simulated day advanced to {new_date.isoformat()} ({day_name}). New simulation will initialize from current configuration baseline.",
        }

    def set_simulated_date(self, db: Session, organisation_id: str, new_date: date) -> Dict[str, Any]:
        """
        Manually set simulated date for the organisation.
        Preserves all historical telemetry, anomalies, recommendations, and configurations.
        Purges daily simulator runtime cache so the new day starts from current baseline.
        """
        config = (
            db.query(OrganisationSensorConfig)
            .filter(OrganisationSensorConfig.organisation_id == organisation_id)
            .first()
        )
        if not config:
            org_exists = db.query(Organisation.id).filter(Organisation.id == organisation_id).first()
            if not org_exists:
                day_name = new_date.strftime("%a").upper()
                return {
                    "organisation_id": organisation_id,
                    "previous_date": OrganisationSensorConfig.DEFAULT_SIMULATED_DATE.isoformat(),
                    "simulated_date": new_date.isoformat(),
                    "day_name": day_name,
                    "day_of_week": day_name,
                    "date_display": f"{new_date.strftime('%d %b %Y')} / {day_name}",
                    "message": f"Simulated date set to {new_date.isoformat()} ({day_name}).",
                }
            config = OrganisationSensorConfig(
                organisation_id=organisation_id,
                data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
                is_active=True,
            )
            db.add(config)
            db.flush()

        prev_date = config.current_simulated_date
        config.set_simulated_date(new_date)
        db.commit()

        # Reset in-memory runtime cache for this organisation
        self.reset_simulator_state(organisation_id)

        day_name = new_date.strftime("%a").upper()
        logger.info(
            "Manual date set executed for org=%s: %s (%s) -> %s (%s). Simulator state reset to current baseline.",
            organisation_id,
            prev_date.isoformat(),
            prev_date.strftime("%a").upper(),
            new_date.isoformat(),
            day_name,
        )
        return {
            "organisation_id": organisation_id,
            "previous_date": prev_date.isoformat(),
            "simulated_date": new_date.isoformat(),
            "day_name": day_name,
            "day_of_week": day_name,
            "date_display": f"{new_date.strftime('%d %b %Y')} / {day_name}",
            "message": f"Simulated date set to {new_date.isoformat()} ({day_name}). New simulation will initialize from current configuration baseline.",
        }


# Global singleton instance for app-wide control
simulator_instance = SyntheticDataSimulator(interval_seconds=30)
