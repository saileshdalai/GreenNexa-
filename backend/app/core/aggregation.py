"""
GreenNexa — Centralized Metric-Aware Aggregation Domain Service.

Single Source of Truth for aggregating telemetry readings across:
- Overview Dashboard (/api/v1/dashboard/{id})
- Module Pages (/api/v1/dashboard/{id}/modules/{id}/overall)
- Historical Time Series & Trend Points
- Current Values, Peak Telemetry, and Averages
- Anomaly contexts & Recommendations

Rules:
1. Energy / Power:
   - Use SUM of valid applicable mapped readings across relevant blocks/zones.
   - Never use MAX as Overall.
2. Water Consumption:
   - Use SUM where readings represent additive consumption.
3. Waste:
   - Use SUM for additive generation (e.g. kg/tons).
   - Use MEAN for fill percentage / capacity metrics (%).
4. Temperature & Humidity:
   - Use MEAN across active blocks/zones (representative).
   - Never automatically use highest block value as Overall.
5. Air Quality / AQI:
   - Use MEAN / representative aggregation.
   - Default to overall facility scope unless legitimate separate monitoring stations exist.
6. Peak Telemetry:
   - MAX over the aggregated cycle values in the selected valid historical window.
   - Peak >= Current Overall.
7. Current Overall:
   - Latest valid aggregate value for the metric (SUM for additive across active blocks, MEAN for representative).
8. Location Scope:
   - Block-wise modules: {"energy", "power", "water", "waste", "occupancy", "assets", "equipment_asset"}
   - Natural location modules & whole-org default modules do NOT use FacilityBlock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import AnomalyRecord, FacilityBlock, SensorReading


BLOCK_WISE_MODULES = {
    "energy",
    "power",
    "water",
    "waste",
    "occupancy",
    "assets",
    "equipment_asset",
}

NATURAL_LOCATION_MODULES = {
    "parking",
    "traffic",
    "water_flow",
    "water_level",
    "sewage_level",
    "rainfall",
    "roads",
    "street_lighting",
    "parks",
    "sewage",
    "safety",
}

WHOLE_ORG_DEFAULT_MODULES = {
    "air_quality",
    "climate",
    "temperature",
    "humidity",
    "co2",
}


def is_block_wise_module(module_name: str) -> bool:
    """Return True if this module naturally maps to campus Facility Blocks."""
    clean = (module_name or "").lower().strip()
    return clean in BLOCK_WISE_MODULES


def is_metric_additive(sensor_type: str, unit: Optional[str] = None) -> bool:
    """
    Return True if readings should be summed across blocks/zones (e.g. energy, water).
    Return False if representative aggregation (mean) should be used (e.g. temp, AQI, fill %).
    """
    clean = (sensor_type or "").lower().strip()
    if clean in {"energy", "power", "water"}:
        return True
    if clean == "waste":
        if unit == "%":
            return False
        return True
    return False


@dataclass
class CycleAggregatePoint:
    timestamp_str: str
    timestamp: datetime
    value: float
    is_anomaly: bool
    anomaly_severity: Optional[str]


@dataclass
class MetricSummaryResult:
    sensor_type: str
    unit: Optional[str]
    current_value: Optional[float]
    average: Optional[float]
    minimum: Optional[float]
    maximum: Optional[float]  # Historical peak over the window
    reading_count: int
    latest_timestamp: Optional[datetime]
    is_anomaly: bool
    anomaly_severity: Optional[str]
    status: str
    change_pct_str: str
    cycle_points: List[CycleAggregatePoint]


def compute_metric_summary(
    db: Session,
    organisation_id: str,
    sensor_type: str,
    cutoff_dt: Optional[datetime] = None,
    blocks: Optional[List[FacilityBlock]] = None,
    now_dt: Optional[datetime] = None,
) -> MetricSummaryResult:
    """
    Centralized calculation of Current Overall, Average, Peak Telemetry, and Cycle Points
    using strict metric-aware and location-aware domain logic.
    """
    clean_type = (sensor_type or "").lower().strip()
    is_block_wise = is_block_wise_module(clean_type)

    if now_dt is None:
        now_dt = datetime.now(timezone.utc)

    # 1. Fetch readings over window
    query = (
        db.query(SensorReading)
        .filter(
            SensorReading.organisation_id == organisation_id,
            SensorReading.sensor_type == clean_type,
        )
    )
    if cutoff_dt:
        query = query.filter(SensorReading.timestamp >= cutoff_dt)

    readings = query.order_by(SensorReading.timestamp.asc()).all()

    # Fallback to recent readings if period returned none
    if not readings and cutoff_dt is not None:
        readings = (
            db.query(SensorReading)
            .filter(
                SensorReading.organisation_id == organisation_id,
                SensorReading.sensor_type == clean_type,
            )
            .order_by(SensorReading.timestamp.asc())
            .all()
        )

    if not readings:
        return MetricSummaryResult(
            sensor_type=clean_type,
            unit=None,
            current_value=None,
            average=None,
            minimum=None,
            maximum=None,
            reading_count=0,
            latest_timestamp=None,
            is_anomaly=False,
            anomaly_severity=None,
            status="NO_DATA",
            change_pct_str="+0.0%",
            cycle_points=[],
        )

    unit = readings[-1].unit
    is_additive = is_metric_additive(clean_type, unit)

    # 2a. Block-scoped readings for block-wise modules.
    # When an organisation has active Facility Blocks (e.g. Municipality Own Office),
    # block-wise modules (energy/power/water/waste/occupancy/assets) MUST only aggregate
    # readings mapped to those blocks. Civic/ward-level readings (block_id NULL) or
    # readings for blocks not in the active set must never be mixed into the block-wise
    # aggregate of another scope. If no block-mapped readings exist at all, fall back to
    # org-level readings so legacy/whole-org datasets keep working.
    valid_block_ids: Optional[set] = None
    scope_readings = readings
    if is_block_wise and blocks:
        valid_block_ids = {b.block_id for b in blocks}
        block_scoped = [r for r in readings if r.block_id and r.block_id in valid_block_ids]
        if block_scoped:
            scope_readings = block_scoped

    # 2. Group readings into measurement cycles (within 10 seconds of each other)
    cycle_groups: List[List[SensorReading]] = []
    current_group: List[SensorReading] = []
    for r in scope_readings:
        if not current_group:
            current_group.append(r)
        else:
            diff = (
                abs((r.timestamp - current_group[0].timestamp).total_seconds())
                if (r.timestamp and current_group[0].timestamp)
                else 0
            )
            if diff <= 10:
                current_group.append(r)
            else:
                cycle_groups.append(current_group)
                current_group = [r]
    if current_group:
        cycle_groups.append(current_group)

    cycle_points: List[CycleAggregatePoint] = []
    for grp in cycle_groups:
        ts = grp[0].timestamp if grp[0].timestamp else now_dt
        ts_str = ts.isoformat()
        if is_block_wise:
            # Per-block duplicates within a single cycle are collapsed to the LATEST
            # reading per active block. This keeps cycle points exactly consistent with
            # the Current Overall (which is the last cycle point) and Peak (MAX cycle),
            # preventing intra-cycle repeats from inflating the aggregate.
            by_block: Dict[str, SensorReading] = {}
            for r in grp:
                key = r.block_id or "__org__"
                cur = by_block.get(key)
                if cur is None or (r.timestamp and cur.timestamp and r.timestamp > cur.timestamp):
                    by_block[key] = r
            unit_readings = list(by_block.values())
        else:
            unit_readings = grp
        if is_block_wise and is_additive:
            val = sum(r.value for r in unit_readings)
        else:
            val = sum(r.value for r in unit_readings) / max(1, len(unit_readings))
        is_anom = any(r.is_anomaly for r in grp)
        anom_sev = next((r.anomaly_severity for r in grp if r.anomaly_severity), None) if is_anom else None
        cycle_points.append(
            CycleAggregatePoint(
                timestamp_str=ts_str,
                timestamp=ts,
                value=round(val, 2),
                is_anomaly=is_anom,
                anomaly_severity=anom_sev,
            )
        )

    cycle_values = [p.value for p in cycle_points]

    # 3. Calculate Current Overall Value
    # Current == the LAST cycle point == the graph's CURRENT marker. This is the single
    # source of truth across the dashboard KPI card, module page card, and trend graph.
    current_val = float(cycle_values[-1]) if cycle_values else float(readings[-1].value)

    # 4. Calculate Peak Telemetry (MAX over the aggregated cycle series for the window)
    peak_val = float(max(cycle_values)) if cycle_values else current_val
    # Enforce Peak >= Current where metric is comparable
    peak_val = max(peak_val, current_val)

    # 5. Average and Minimum
    average_val = float(sum(cycle_values) / len(cycle_values)) if cycle_values else current_val
    minimum_val = float(min(cycle_values)) if cycle_values else current_val

    # 6. Trend / Change % calculation over the period
    if len(cycle_values) >= 2:
        mid = len(cycle_values) // 2
        first_half = sum(cycle_values[:mid]) / mid if mid > 0 else cycle_values[0]
        second_half = sum(cycle_values[mid:]) / (len(cycle_values) - mid)
        diff = second_half - first_half
        pct = (diff / first_half * 100.0) if first_half != 0 else 0.0
        change_pct_str = f"+{pct:.1f}%" if pct >= 0 else f"{pct:.1f}%"
    else:
        change_pct_str = "+0.0%"

    # 7. Anomaly state and status
    latest_grp = cycle_groups[-1] if cycle_groups else []
    is_anomaly = any(r.is_anomaly for r in latest_grp)
    anomaly_severity = next((r.anomaly_severity for r in latest_grp if r.anomaly_severity), None) if is_anomaly else None

    # Status check against open anomalies in DB
    open_anoms = (
        db.query(AnomalyRecord)
        .filter(
            AnomalyRecord.organisation_id == organisation_id,
            AnomalyRecord.metric == clean_type,
            AnomalyRecord.status == AnomalyRecord.STATUS_OPEN,
        )
        .all()
    )
    if any(a.severity == AnomalyRecord.SEVERITY_CRITICAL for a in open_anoms):
        metric_status = "Critical"
    elif any(a.severity == AnomalyRecord.SEVERITY_HIGH for a in open_anoms):
        metric_status = "Warning"
    elif is_anomaly and anomaly_severity == "CRITICAL":
        metric_status = "Critical"
    elif is_anomaly:
        metric_status = "Warning"
    else:
        metric_status = "Normal"

    return MetricSummaryResult(
        sensor_type=clean_type,
        unit=unit,
        current_value=round(current_val, 2),
        average=round(average_val, 2),
        minimum=round(minimum_val, 2),
        maximum=round(peak_val, 2),
        reading_count=len(readings),
        latest_timestamp=readings[-1].timestamp,
        is_anomaly=is_anomaly,
        anomaly_severity=anomaly_severity,
        status=metric_status,
        change_pct_str=change_pct_str,
        cycle_points=cycle_points,
    )
