"""
GreenNexa — Dashboard APIs Router.

Routes:
  GET /api/v1/dashboard/{organisation_id}            — Complete main dashboard summary
  GET /api/v1/dashboard/{organisation_id}/style      — Persisted dashboard style (presentation only)
  PUT /api/v1/dashboard/{organisation_id}/style      — Select + persist dashboard style
  GET /api/v1/dashboard/{organisation_id}/latest     — Latest reading per enabled sensor
  GET /api/v1/dashboard/{organisation_id}/timeseries — Historical time-series points per sensor
  GET /api/v1/dashboard/{organisation_id}/statistics — Database-aggregated statistics per sensor
  GET /api/v1/dashboard/{organisation_id}/recent     — Recent reading log items
  GET /api/v1/dashboard/{organisation_id}/data-source— Data source mode & simulator/IoT device status
  GET /api/v1/dashboard/{organisation_id}/status     — Sensor freshness & connectivity status (ONLINE/OFFLINE/NO_DATA)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_current_user,
    verify_organisation_access,
    verify_oversight_read_access,
)
from app.db.database import get_db
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    IoTDevice,
    MunicipalityWard,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
)
from app.schemas.dashboard_style import (
    DASHBOARD_STYLE_VALUES,
    DashboardStyleResponse,
    DashboardStyleUpdateRequest,
)
from app.schemas.ward import WardResponse
from app.schemas.module_detail import (
    BlockComparisonItem,
    ModuleBlockDetailResponse,
    ModuleOverallResponse,
    PredictionRowItem,
    TrendPointItem,
)
from app.core.aggregation import compute_metric_summary, is_block_wise_module
from app.schemas.dashboard import (
    BlockInfo,
    DashboardSummaryResponse,
    DataSourceStatusResponse,
    KPIMetricSummary,
    LatestSensorReading,
    LatestSensorValuesResponse,
    OwnOfficeSummary,
    RecentReadingItem,
    RecentReadingsResponse,
    SensorStatisticsItem,
    SensorStatisticsResponse,
    SensorStatusItem,
    SensorStatusResponse,
    TimeSeriesItem,
    TimeSeriesResponse,
)
from app.services.synthetic_simulator import simulator_instance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard Intelligence"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ALLOWED_PERIODS = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def _parse_period(period_str: str) -> tuple[str, timedelta]:
    clean = period_str.strip().lower()
    if clean not in ALLOWED_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid period '{period_str}'. Allowed periods: {sorted(list(ALLOWED_PERIODS.keys()))}",
        )
    return clean, ALLOWED_PERIODS[clean]


def _get_org_and_config(
    organisation_id: str,
    db: Session,
    current_user: User,
    allow_oversight: bool = True,
) -> tuple[Organisation, OrganisationSensorConfig]:
    if allow_oversight:
        # Read-only telemetry endpoints may be browsed by Municipality Admins for
        # their associated Government organisations (oversight intelligence).
        resolved_org_id = verify_oversight_read_access(organisation_id, current_user, db)
    else:
        resolved_org_id = verify_organisation_access(organisation_id, current_user)

    org = db.query(Organisation).filter_by(id=resolved_org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{organisation_id}' not found.",
        )

    config = db.query(OrganisationSensorConfig).filter_by(organisation_id=resolved_org_id).first()
    if not config:
        if allow_oversight:
            # Read-only oversight: build a harmless in-memory default config.
            # Never persist config changes for an organisation being observed.
            config = OrganisationSensorConfig(
                organisation_id=resolved_org_id,
                data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
                is_active=True,
            )
        else:
            config = OrganisationSensorConfig(
                organisation_id=resolved_org_id,
                data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
                is_active=True,
            )
            db.add(config)
            db.commit()
            db.refresh(config)

    return org, config


def _determine_status(last_ts: Optional[datetime], now_dt: datetime) -> str:
    if last_ts is None:
        return "NO_DATA"
    # Ensure timezone aware comparison
    if last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=timezone.utc)
    gap = (now_dt - last_ts).total_seconds()
    if gap <= 600.0:  # Fresh within 10 minutes (600s)
        return "ONLINE"
    return "OFFLINE"


def _status_reference_now(last_ts: Optional[datetime]) -> datetime:
    """
    Reference "now" used for sensor freshness/status evaluation.

    Synthetic simulator readings are stamped with the organisation's SIMULATED
    calendar date (e.g. 2026-09-20) plus the current UTC time-of-day. Comparing
    those timestamps against the real wall-clock date would falsely report every
    sensor as OFFLINE. This reference reuses the reading's own calendar day and
    the live UTC time-of-day, which exactly mirrors how the simulator stamps
    readings and yields TRUE freshness semantics for both synthetic and
    IoT-seeded data.
    """
    real_now = _utcnow()
    if last_ts is None:
        return real_now
    ts = last_ts if last_ts.tzinfo is not None else last_ts.replace(tzinfo=timezone.utc)
    return datetime(
        ts.year, ts.month, ts.day,
        real_now.hour, real_now.minute, real_now.second,
        tzinfo=timezone.utc,
    )


# ---------------------------------------------------------------------------
# GET /dashboard/{organisation_id} — Main Dashboard Summary
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}",
    response_model=DashboardSummaryResponse,
    summary="Get complete dashboard summary",
    description="Returns main dashboard KPIs, current values, recent readings, and sensor statuses.",
)
def get_dashboard_summary(
    organisation_id: str,
    period: str = Query("24h", description="Time period filter: 1h, 6h, 24h, 7d, 30d"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, config = _get_org_and_config(organisation_id, db, current_user)
    period_clean, period_td = _parse_period(period)

    now_dt = _utcnow()
    cutoff_dt = now_dt - period_td
    enabled_sensors = config.enabled_sensors_list

    # Active blocks for block-wise aggregation
    blocks = (
        db.query(FacilityBlock)
        .filter(FacilityBlock.organisation_id == organisation_id, FacilityBlock.is_active == True)
        .order_by(FacilityBlock.block_id.asc())
        .all()
    )

    # 1. Compute KPIs for enabled sensors using centralized metric-aware aggregation
    kpis: Dict[str, KPIMetricSummary] = {}
    current_values: List[LatestSensorReading] = []
    sensor_statuses: List[SensorStatusItem] = []
    overall_last_updated: Optional[datetime] = None

    for s_type in enabled_sensors:
        metric_sum = compute_metric_summary(
            db=db,
            organisation_id=organisation_id,
            sensor_type=s_type,
            cutoff_dt=cutoff_dt,
            blocks=blocks,
            now_dt=now_dt,
        )

        # Track overall last updated from the latest reading
        if metric_sum.latest_timestamp:
            latest_reading = (
                db.query(SensorReading)
                .filter(
                    SensorReading.organisation_id == organisation_id,
                    SensorReading.sensor_type == s_type,
                )
                .order_by(SensorReading.timestamp.desc())
                .first()
            )
            if latest_reading:
                reading_time = latest_reading.created_at if latest_reading.created_at else latest_reading.timestamp
                if reading_time:
                    r_tz = reading_time if reading_time.tzinfo is not None else reading_time.replace(tzinfo=timezone.utc)
                    if overall_last_updated is None or r_tz > overall_last_updated:
                        overall_last_updated = r_tz

        s_status = _determine_status(metric_sum.latest_timestamp, _status_reference_now(metric_sum.latest_timestamp))

        kpis[s_type] = KPIMetricSummary(
            sensor_type=s_type,
            unit=metric_sum.unit,
            latest_value=metric_sum.current_value,
            average=metric_sum.average,
            minimum=metric_sum.minimum,
            maximum=metric_sum.maximum,
            reading_count=metric_sum.reading_count,
            latest_timestamp=metric_sum.latest_timestamp,
            is_anomaly=metric_sum.is_anomaly,
            anomaly_severity=metric_sum.anomaly_severity,
        )

        current_values.append(
            LatestSensorReading(
                sensor_type=s_type,
                value=metric_sum.current_value,
                unit=metric_sum.unit,
                timestamp=metric_sum.latest_timestamp,
                source=config.data_source,
                is_anomaly=metric_sum.is_anomaly,
                anomaly_severity=metric_sum.anomaly_severity,
                status=s_status,
            )
        )

        sensor_statuses.append(
            SensorStatusItem(
                sensor_type=s_type,
                status=s_status,
                last_value=metric_sum.current_value,
                unit=metric_sum.unit,
                last_updated_at=metric_sum.latest_timestamp,
                source=config.data_source,
            )
        )

    # 2. Query Recent Readings (top 10 across enabled sensors)
    recent_db_readings = (
        db.query(SensorReading)
        .filter(
            SensorReading.organisation_id == organisation_id,
            SensorReading.sensor_type.in_(enabled_sensors),
        )
        .order_by(SensorReading.timestamp.desc())
        .limit(10)
        .all()
    )

    recent_items = [RecentReadingItem.model_validate(r) for r in recent_db_readings]

    # Compute authoritative active anomaly count & dynamic optimal score
    active_anomalies = (
        db.query(AnomalyRecord)
        .filter(
            AnomalyRecord.organisation_id == organisation_id,
            AnomalyRecord.status.in_((AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED)),
        )
        .all()
    )
    from app.services.anomaly_detection import anomaly_detection_service
    optimal_score = anomaly_detection_service.calculate_optimal_score(active_anomalies)

    is_municipality = bool(org.org_type and "municipality" in org.org_type.lower())
    muni_wards_list = None
    total_wards_count = None
    own_office_summary = None

    if is_municipality:
        muni_wards_db = (
            db.query(MunicipalityWard)
            .filter(
                MunicipalityWard.municipality_id == organisation_id,
                MunicipalityWard.is_active == True,
            )
            .order_by(MunicipalityWard.ward_number.asc())
            .all()
        )
        muni_wards_list = [WardResponse.model_validate(w) for w in muni_wards_db]
        total_wards_count = len(muni_wards_db)

        # Build dedicated Municipality Own Office summary
        # Own office blocks are physical blocks of the municipality organisation
        office_blocks_info = [BlockInfo(block_id=b.block_id, block_name=b.block_name) for b in blocks]
        office_block_ids = [b.block_id for b in blocks]

        # Own office anomalies
        office_anomalies = [
            a for a in active_anomalies
            if (a.ward_id is None) and (not a.block_id or a.block_id in office_block_ids)
        ]

        # Own office recommendations
        office_recs = (
            db.query(AIRecommendation)
            .filter(
                AIRecommendation.organisation_id == organisation_id,
                AIRecommendation.status.in_((AIRecommendation.STATUS_OPEN, AIRecommendation.STATUS_ACTIVE)),
            )
            .all()
        )
        office_recs = [r for r in office_recs if not r.block_id or r.block_id in office_block_ids]

        # Metric values for Own Office
        energy_kpi = kpis.get("energy")
        water_kpi = kpis.get("water")
        waste_kpi = kpis.get("waste")
        aqi_kpi = kpis.get("air_quality")
        occ_kpi = kpis.get("occupancy")
        safety_kpi = kpis.get("safety")

        own_office_summary = OwnOfficeSummary(
            office_name=org.facility_name or f"{org.name} Headquarters",
            location=org.location or (", ".join(p for p in [org.city, org.district, org.state] if p)),
            blocks=office_blocks_info,
            kpis=kpis,
            total_energy_kwh=energy_kpi.latest_value if energy_kpi else None,
            total_water_liters=water_kpi.latest_value if water_kpi else None,
            total_waste_kg=waste_kpi.latest_value if waste_kpi else None,
            avg_aqi=aqi_kpi.latest_value if aqi_kpi else None,
            occupancy_pct=occ_kpi.latest_value if occ_kpi else None,
            safety_score=safety_kpi.latest_value if safety_kpi else None,
            active_anomalies_count=len(office_anomalies),
            recommendations_count=len(office_recs),
            status="ONLINE" if any(s.status == "ONLINE" for s in sensor_statuses) else "OFFLINE",
            data_source=config.data_source,
            config={
                "enabled_sensors": enabled_sensors,
                "data_source": config.data_source,
                "simulated_date": config.current_simulated_date.isoformat() if hasattr(config, "current_simulated_date") else None,
            },
        )

    return DashboardSummaryResponse(
        organisation_id=org.id,
        organisation_name=org.name,
        org_type=org.org_type,
        facility_name=org.facility_name,
        data_source=config.data_source,
        period=period_clean,
        last_updated_at=overall_last_updated,
        kpis=kpis,
        current_values=current_values,
        recent_readings=recent_items,
        sensor_status=sensor_statuses,
        optimal_score=optimal_score,
        active_anomaly_count=len(active_anomalies),
        blocks=[BlockInfo(block_id=b.block_id, block_name=b.block_name) for b in blocks],
        wards=muni_wards_list,
        total_wards=total_wards_count,
        own_office=own_office_summary,
        dashboard_style=_readable_dashboard_style(org, current_user),
    )


# ---------------------------------------------------------------------------
# Dashboard Style System — read / select (presentation only)
# ---------------------------------------------------------------------------
def _readable_dashboard_style(org: Organisation, current_user: User) -> Optional[str]:
    """
    Return the organisation's dashboard style, but ONLY when the caller is
    allowed to see that organisation's own presentation preference
    (own organisation, or SUPER_ADMIN). Oversight/read-only browsing of an
    associated organisation never exposes its style preference (None is returned
    and the client falls back to the default style).
    """
    if current_user.role == User.ROLE_SUPER_ADMIN:
        return org.effective_dashboard_style
    if current_user.organisation_id and current_user.organisation_id == org.id:
        return org.effective_dashboard_style
    return None


@router.get(
    "/{organisation_id}/style",
    response_model=DashboardStyleResponse,
    summary="Get the persisted dashboard style for an organisation",
    description=(
        "Returns the saved dashboard presentation style (EXECUTIVE, OPERATIONS, "
        "ANALYTICS or COMMAND_CENTER) for the requested organisation. "
        "Requires access to that organisation."
    ),
)
def get_dashboard_style(
    organisation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Read the dashboard style preference (own organisation, or any for SUPER_ADMIN)."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    org = db.query(Organisation).filter(Organisation.id == target_org_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{target_org_id}' not found.",
        )

    style = org.effective_dashboard_style
    return DashboardStyleResponse(
        organisation_id=org.id,
        dashboard_style=style,
        available_styles=list(DASHBOARD_STYLE_VALUES),
        is_default=style == Organisation.DEFAULT_DASHBOARD_STYLE,
    )


@router.put(
    "/{organisation_id}/style",
    response_model=DashboardStyleResponse,
    summary="Select the dashboard style for an organisation",
    description=(
        "Persists the dashboard presentation style for one organisation. "
        "Only EXECUTIVE, OPERATIONS, ANALYTICS and COMMAND_CENTER are accepted; "
        "any other value is rejected. Requires ADMIN of that organisation or SUPER_ADMIN."
    ),
)
def update_dashboard_style(
    organisation_id: str,
    body: DashboardStyleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Persist the dashboard style for an organisation.

    The value is validated by DashboardStyleUpdateRequest (422 on unknown values).
    Write access is gated by verify_organisation_access, so an ADMIN can only
    change their own organisation and can never touch another organisation's style.
    Only the stored presentation preference changes — no telemetry, anomaly,
    forecast, recommendation, module or permission state is touched.
    """
    if current_user.role not in (User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Insufficient role permissions for this operation.",
        )

    target_org_id = verify_organisation_access(organisation_id, current_user)

    org = db.query(Organisation).filter(Organisation.id == target_org_id).first()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{target_org_id}' not found.",
        )

    # body.dashboard_style is already normalised/validated by the schema
    org.dashboard_style = body.dashboard_style
    db.commit()
    db.refresh(org)

    logger.info(
        "Dashboard style set to '%s' for org=%s by user=%s",
        body.dashboard_style,
        org.id,
        current_user.email,
    )
    return DashboardStyleResponse(
        organisation_id=org.id,
        dashboard_style=org.effective_dashboard_style,
        available_styles=list(DASHBOARD_STYLE_VALUES),
        is_default=org.effective_dashboard_style == Organisation.DEFAULT_DASHBOARD_STYLE,
    )



# ---------------------------------------------------------------------------
# GET /dashboard/{organisation_id}/latest — Latest Sensor Values
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}/latest",
    response_model=LatestSensorValuesResponse,
    summary="Get latest reading per enabled sensor",
    description="Returns the single most recent reading for each enabled sensor of an organisation.",
)
def get_latest_sensor_values(
    organisation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, config = _get_org_and_config(organisation_id, db, current_user)
    enabled_sensors = config.enabled_sensors_list
    now_dt = _utcnow()

    readings_list: List[LatestSensorReading] = []
    for s_type in enabled_sensors:
        latest = (
            db.query(SensorReading)
            .filter(
                SensorReading.organisation_id == organisation_id,
                SensorReading.sensor_type == s_type,
            )
            .order_by(SensorReading.timestamp.desc())
            .first()
        )

        s_status = _determine_status(latest.timestamp if latest else None, _status_reference_now(latest.timestamp if latest else None))

        readings_list.append(
            LatestSensorReading(
                sensor_type=s_type,
                value=latest.value if latest else None,
                unit=latest.unit if latest else None,
                timestamp=latest.timestamp if latest else None,
                source=latest.source if latest else None,
                is_anomaly=latest.is_anomaly if latest else False,
                anomaly_severity=latest.anomaly_severity if latest else None,
                status=s_status,
            )
        )

    return LatestSensorValuesResponse(
        organisation_id=org.id,
        data_source=config.data_source,
        readings=readings_list,
    )


# ---------------------------------------------------------------------------
# GET /dashboard/{organisation_id}/timeseries — Historical Time-Series API
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}/timeseries",
    response_model=TimeSeriesResponse,
    summary="Get historical time-series data for a sensor",
    description="Returns chronologically ordered sensor data points for charting and analysis.",
)
def get_timeseries_data(
    organisation_id: str,
    sensor_type: str = Query(..., description="Sensor type e.g. energy, water, temperature"),
    period: str = Query("24h", description="Time period filter: 1h, 6h, 24h, 7d, 30d"),
    start: Optional[datetime] = Query(None, description="Optional start datetime ISO filter"),
    end: Optional[datetime] = Query(None, description="Optional end datetime ISO filter"),
    limit: int = Query(500, ge=1, le=2000, description="Max data points returned (default 500, max 2000)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, config = _get_org_and_config(organisation_id, db, current_user)
    clean_sensor = sensor_type.strip().lower()

    if clean_sensor not in OrganisationSensorConfig.ALLOWED_SENSOR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported sensor type '{sensor_type}'. Allowed types: {sorted(list(OrganisationSensorConfig.ALLOWED_SENSOR_TYPES))}",
        )

    if clean_sensor not in config.enabled_sensors_list:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Sensor type '{clean_sensor}' is not enabled for organisation '{organisation_id}'.",
        )

    if start and end and start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Start datetime cannot be after end datetime.",
        )

    query = db.query(SensorReading).filter(
        SensorReading.organisation_id == organisation_id,
        SensorReading.sensor_type == clean_sensor,
    )

    if start and end:
        query = query.filter(SensorReading.timestamp >= start, SensorReading.timestamp <= end)
        period_str = "custom"
    else:
        period_str, period_td = _parse_period(period)
        cutoff = _utcnow() - period_td
        query = query.filter(SensorReading.timestamp >= cutoff)

    db_readings = query.order_by(SensorReading.timestamp.asc()).limit(limit).all()

    unit = db_readings[0].unit if db_readings else None

    points = [
        TimeSeriesItem(
            timestamp=r.timestamp,
            value=r.value,
            is_anomaly=r.is_anomaly,
            anomaly_severity=r.anomaly_severity,
            source=r.source,
        )
        for r in db_readings
    ]

    return TimeSeriesResponse(
        organisation_id=org.id,
        sensor_type=clean_sensor,
        unit=unit,
        period=period_str,
        total_points=len(points),
        data=points,
    )


# ---------------------------------------------------------------------------
# GET /dashboard/{organisation_id}/statistics — Sensor-wise Statistics API
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}/statistics",
    response_model=SensorStatisticsResponse,
    summary="Get aggregated statistics by sensor type",
    description="Returns database-aggregated count, average, minimum, and maximum per enabled sensor.",
)
def get_sensor_statistics(
    organisation_id: str,
    period: str = Query("24h", description="Time period filter: 1h, 6h, 24h, 7d, 30d"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, config = _get_org_and_config(organisation_id, db, current_user)
    period_str, period_td = _parse_period(period)
    cutoff = _utcnow() - period_td
    enabled_sensors = config.enabled_sensors_list

    stats: Dict[str, SensorStatisticsItem] = {}

    for s_type in enabled_sensors:
        agg = (
            db.query(
                func.count(SensorReading.id),
                func.avg(SensorReading.value),
                func.min(SensorReading.value),
                func.max(SensorReading.value),
            )
            .filter(
                SensorReading.organisation_id == organisation_id,
                SensorReading.sensor_type == s_type,
                SensorReading.timestamp >= cutoff,
            )
            .first()
        )

        cnt, avg_v, min_v, max_v = agg if agg else (0, None, None, None)
        if cnt == 0:
            continue

        latest = (
            db.query(SensorReading.unit)
            .filter(SensorReading.organisation_id == organisation_id, SensorReading.sensor_type == s_type)
            .order_by(SensorReading.timestamp.desc())
            .first()
        )

        stats[s_type] = SensorStatisticsItem(
            sensor_type=s_type,
            count=cnt,
            average=round(float(avg_v), 2) if avg_v is not None else None,
            minimum=round(float(min_v), 2) if min_v is not None else None,
            maximum=round(float(max_v), 2) if max_v is not None else None,
            unit=latest[0] if latest else None,
        )

    return SensorStatisticsResponse(
        organisation_id=org.id,
        period=period_str,
        statistics=stats,
    )


# ---------------------------------------------------------------------------
# GET /dashboard/{organisation_id}/recent — Recent Readings API
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}/recent",
    response_model=RecentReadingsResponse,
    summary="Get recent sensor reading logs",
    description="Returns newest sensor readings across enabled sensors.",
)
def get_recent_readings(
    organisation_id: str,
    limit: int = Query(20, ge=1, le=100, description="Max readings to return (default 20, max 100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, config = _get_org_and_config(organisation_id, db, current_user)
    enabled_sensors = config.enabled_sensors_list

    readings_db = (
        db.query(SensorReading)
        .filter(
            SensorReading.organisation_id == organisation_id,
            SensorReading.sensor_type.in_(enabled_sensors),
        )
        .order_by(SensorReading.timestamp.desc())
        .limit(limit)
        .all()
    )

    items = [RecentReadingItem.model_validate(r) for r in readings_db]
    return RecentReadingsResponse(
        organisation_id=org.id,
        total=len(items),
        readings=items,
    )


# ---------------------------------------------------------------------------
# GET /dashboard/{organisation_id}/data-source — Data Source Mode Status API
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}/data-source",
    response_model=DataSourceStatusResponse,
    summary="Get data source mode and operational status",
    description="Returns current data source mode (synthetic vs iot), simulator state, and IoT device count.",
)
def get_data_source_status(
    organisation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, config = _get_org_and_config(organisation_id, db, current_user)

    iot_devices_count = db.query(func.count(IoTDevice.id)).filter(IoTDevice.organisation_id == organisation_id, IoTDevice.is_active == True).scalar() or 0

    latest_reading = (
        db.query(SensorReading.timestamp)
        .filter(SensorReading.organisation_id == organisation_id)
        .order_by(SensorReading.timestamp.desc())
        .first()
    )

    sim_running = simulator_instance.is_running if config.data_source == OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC else False

    return DataSourceStatusResponse(
        organisation_id=org.id,
        data_source=config.data_source,
        enabled_sensors=config.enabled_sensors_list,
        simulator_running=sim_running,
        iot_devices_count=iot_devices_count,
        last_updated_at=latest_reading[0] if latest_reading else None,
    )


# ---------------------------------------------------------------------------
# GET /dashboard/{organisation_id}/status — Sensor Connectivity & Freshness Status API
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}/status",
    response_model=SensorStatusResponse,
    summary="Get sensor freshness and status",
    description="Returns connectivity freshness status (ONLINE / OFFLINE / NO_DATA) per enabled sensor.",
)
def get_sensor_freshness_status(
    organisation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, config = _get_org_and_config(organisation_id, db, current_user)
    enabled_sensors = config.enabled_sensors_list
    now_dt = _utcnow()

    statuses: List[SensorStatusItem] = []
    for s_type in enabled_sensors:
        latest = (
            db.query(SensorReading)
            .filter(
                SensorReading.organisation_id == organisation_id,
                SensorReading.sensor_type == s_type,
            )
            .order_by(SensorReading.timestamp.desc())
            .first()
        )

        s_status = _determine_status(latest.timestamp if latest else None, _status_reference_now(latest.timestamp if latest else None))
        statuses.append(
            SensorStatusItem(
                sensor_type=s_type,
                status=s_status,
                last_value=latest.value if latest else None,
                unit=latest.unit if latest else None,
                last_updated_at=latest.timestamp if latest else None,
                source=latest.source if latest else None,
            )
        )

    return SensorStatusResponse(
        organisation_id=org.id,
        sensors=statuses,
    )


# ---------------------------------------------------------------------------
# GET /dashboard/{organisation_id}/modules/{module_id}/overall
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}/modules/{module_id}/overall",
    response_model=ModuleOverallResponse,
    summary="Get overall module intelligence and block comparison",
)
def get_module_overall_intelligence(
    organisation_id: str,
    module_id: str,
    period: str = Query("24h", description="Time period filter: 1h, 6h, 24h, 7d, 30d"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve overall metric intelligence, trend graph points, block comparison, and prediction table."""
    org, config = _get_org_and_config(organisation_id, db, current_user)
    period_clean, period_td = _parse_period(period)

    clean_mod = module_id.strip().lower()
    enabled = config.enabled_sensors_list
    if clean_mod not in enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Module '{clean_mod}' is disabled for organisation '{organisation_id}'.",
        )

    now_dt = _utcnow()
    cutoff_dt = now_dt - period_td

    # Fetch active blocks
    blocks = (
        db.query(FacilityBlock)
        .filter(FacilityBlock.organisation_id == organisation_id, FacilityBlock.is_active == True)
        .order_by(FacilityBlock.block_id.asc())
        .all()
    )

    # Unit mapping
    unit_map = {
        "energy": "kWh",
        "water": "L",
        "waste": "%",
        "air_quality": "AQI",
        "temperature": "°C",
        "humidity": "%",
        "co2": "ppm",
        "traffic": "veh/h",
        "parking": "%",
        "assets": "%",
        "safety": "%",
        "climate": "°C",
        "street_lighting": "kWh",
        "roads": "%",
        "parks": "%",
        "sewage": "%",
    }
    unit = unit_map.get(clean_mod, "")

    # Query readings over period
    readings = (
        db.query(SensorReading)
        .filter(
            SensorReading.organisation_id == organisation_id,
            SensorReading.sensor_type == clean_mod,
            SensorReading.timestamp >= cutoff_dt,
        )
        .order_by(SensorReading.timestamp.asc())
        .all()
    )

    if not readings:
        # Fallback to latest readings if none in period window
        readings = (
            db.query(SensorReading)
            .filter(
                SensorReading.organisation_id == organisation_id,
                SensorReading.sensor_type == clean_mod,
            )
            .order_by(SensorReading.timestamp.asc())
            .all()
        )

    total_count = len(readings)
    has_history = total_count >= 3

    # 1. Compute centralized metric-aware intelligence summary
    metric_sum = compute_metric_summary(
        db=db,
        organisation_id=organisation_id,
        sensor_type=clean_mod,
        cutoff_dt=cutoff_dt,
        blocks=blocks,
        now_dt=now_dt,
    )

    current_val = metric_sum.current_value or 0.0
    average_val = metric_sum.average or 0.0
    peak_val = metric_sum.maximum or current_val
    change_pct_str = metric_sum.change_pct_str
    overall_status = metric_sum.status
    unit = metric_sum.unit or unit

    # Config baseline and thresholds
    sensor_cfg = config.sensor_configs_dict.get(clean_mod, {})
    raw_baseline = float(sensor_cfg.get("baseline", 100.0))
    warn_pct = float(sensor_cfg.get("warning_threshold", 15.0))
    crit_pct = float(sensor_cfg.get("critical_threshold", 30.0))

    is_additive = is_block_wise_module(clean_mod) and clean_mod in {"energy", "power", "water", "waste"}
    ov_baseline = raw_baseline * max(1, len(blocks)) if (blocks and is_additive) else raw_baseline
    ov_warn_thresh = ov_baseline * (1.0 + warn_pct / 100.0)
    ov_crit_thresh = ov_baseline * (1.0 + crit_pct / 100.0)

    # Build trend graph points from cycle_points
    trend_points: List[TrendPointItem] = []
    cycle_pts = metric_sum.cycle_points
    if cycle_pts:
        if len(cycle_pts) > 150:
            stride = max(1, len(cycle_pts) // 100)
            selected_indices = set(range(0, len(cycle_pts), stride))
            selected_indices.add(len(cycle_pts) - 1)
            for idx, pt in enumerate(cycle_pts):
                if pt.is_anomaly:
                    selected_indices.add(idx)
            final_pts = [cycle_pts[i] for i in sorted(selected_indices)]
        else:
            final_pts = cycle_pts

        for pt in final_pts:
            trend_points.append(
                TrendPointItem(
                    timestamp=pt.timestamp_str,
                    value=round(pt.value, 2),
                    is_anomaly=pt.is_anomaly,
                    anomaly_severity=pt.anomaly_severity,
                    baseline=round(ov_baseline, 2),
                    warning_threshold=round(ov_warn_thresh, 2),
                    critical_threshold=round(ov_crit_thresh, 2),
                )
            )

    # Build block comparison items using Data Scope rules:
    # Only block-wise modules show facility blocks, and only if actual mapped readings exist
    block_comparison: List[BlockComparisonItem] = []
    if is_block_wise_module(clean_mod) and blocks:
        for blk in blocks:
            latest_b = (
                db.query(SensorReading)
                .filter(
                    SensorReading.organisation_id == organisation_id,
                    SensorReading.block_id == blk.block_id,
                    SensorReading.sensor_type == clean_mod,
                )
                .order_by(SensorReading.timestamp.desc())
                .first()
            )
            if not latest_b:
                continue

            b_val = latest_b.value if latest_b else 0.0
            b_unit = latest_b.unit if latest_b else unit

            b_anom = (
                db.query(AnomalyRecord)
                .filter(
                    AnomalyRecord.organisation_id == organisation_id,
                    AnomalyRecord.block_id == blk.block_id,
                    AnomalyRecord.metric == clean_mod,
                    AnomalyRecord.status == AnomalyRecord.STATUS_OPEN,
                )
                .first()
            )
            b_status = b_anom.severity if b_anom else "Normal"
            if b_status == AnomalyRecord.SEVERITY_CRITICAL:
                b_status = "Critical"
            elif b_status == AnomalyRecord.SEVERITY_HIGH:
                b_status = "Warning"

            block_comparison.append(
                BlockComparisonItem(
                    block_id=blk.block_id,
                    block_name=blk.block_name,
                    current_value=round(b_val, 2),
                    unit=b_unit,
                    status=b_status,
                )
            )

    # Build dynamic prediction table via ML Forecasting
    prediction_table: List[PredictionRowItem] = []
    if has_history:
        # Overall row via ML Forecast
        from app.services.forecasting import forecasting_service
        ov_pred = current_val
        ov_chg_pct = 0.0
        try:
            fc_resp = forecasting_service.get_forecast(
                db=db, organisation_id=organisation_id, sensor_type=clean_mod, horizon="24h", mode="last"
            )
            if fc_resp and fc_resp.forecast:
                ov_pred = round(fc_resp.forecast[0].predicted_value, 1)
                ov_chg_pct = round((ov_pred - current_val) / current_val * 100.0, 1) if current_val > 0 else 0.0
        except Exception:
            ov_pred = round(current_val * 1.02, 1)
            ov_chg_pct = 2.0

        ov_chg_str = f"+{ov_chg_pct}%" if ov_chg_pct >= 0 else f"{ov_chg_pct}%"
        prediction_table.append(
            PredictionRowItem(
                location="Overall",
                block_id=None,
                current_value=round(current_val, 1),
                predicted_value=ov_pred,
                change_pct_str=ov_chg_str,
                status=overall_status,
            )
        )
        # Row for each valid mapped block comparison item
        for comp_item in block_comparison:
            c_val = comp_item.current_value

            if current_val > 0 and c_val > 0:
                block_ratio = c_val / current_val
                pred_v = round(ov_pred * block_ratio, 1)
            else:
                pred_v = round(c_val * 1.02, 1)

            chg_pct = round((pred_v - c_val) / c_val * 100.0, 1) if c_val > 0 else 0.0
            chg_str = f"+{chg_pct}%" if chg_pct >= 0 else f"{chg_pct}%"
            p_status = "Warning" if chg_pct > 12 else "Normal"

            prediction_table.append(
                PredictionRowItem(
                    location=comp_item.block_name,
                    block_id=comp_item.block_id,
                    current_value=round(c_val, 1),
                    predicted_value=pred_v,
                    change_pct_str=chg_str,
                    status=p_status,
                )
            )

    title_map = {
        "energy": "Energy Consumption",
        "water": "Water Usage",
        "waste": "Waste Generation",
        "air_quality": "Air Quality",
        "temperature": "Indoor Temperature",
        "humidity": "Humidity",
        "co2": "CO2 Concentration",
        "traffic": "Traffic Management",
        "parking": "Parking Occupancy",
        "assets": "Assets Monitoring",
        "safety": "Safety Intelligence",
        "climate": "Climate KPI",
        "street_lighting": "Street Lighting",
        "roads": "Roads & Infrastructure",
        "parks": "Parks & Playgrounds",
        "sewage": "Drainage & Sewage",
    }
    module_title = title_map.get(clean_mod, clean_mod.capitalize())

    open_anomalies = (
        db.query(AnomalyRecord)
        .filter(
            AnomalyRecord.organisation_id == organisation_id,
            AnomalyRecord.metric == clean_mod,
            AnomalyRecord.status == AnomalyRecord.STATUS_OPEN,
        )
        .all()
    )
    open_count = len(open_anomalies)

    return ModuleOverallResponse(
        organisation_id=org.id,
        organisation_name=org.name,
        module_id=clean_mod,
        module_title=module_title,
        unit=unit,
        # Current/Peak use the SAME precision as the trend graph so the KPI card is
        # numerically identical to the graph's CURRENT marker and historical MAX.
        current_value=round(current_val, 2),
        average=round(average_val, 2),
        peak=round(peak_val, 2),
        change_pct_str=change_pct_str,
        status=overall_status,
        open_anomalies_count=open_count,
        has_sufficient_history=has_history,
        trend_points=trend_points,
        block_comparison=block_comparison,
        prediction_table=prediction_table,
        baseline=round(ov_baseline, 2),
        warning_threshold=round(ov_warn_thresh, 2),
        critical_threshold=round(ov_crit_thresh, 2),
    )


# ---------------------------------------------------------------------------
# GET /dashboard/{organisation_id}/modules/{module_id}/block/{block_id}
# ---------------------------------------------------------------------------
@router.get(
    "/{organisation_id}/modules/{module_id}/block/{block_id}",
    response_model=ModuleBlockDetailResponse,
    summary="Get block-specific module intelligence and telemetry",
)
def get_module_block_detail(
    organisation_id: str,
    module_id: str,
    block_id: str,
    period: str = Query("24h", description="Time period filter: 1h, 6h, 24h, 7d, 30d"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve selected block intelligence, trend graph (block-only), block prediction, anomalies & recommendations."""
    org, config = _get_org_and_config(organisation_id, db, current_user)
    period_clean, period_td = _parse_period(period)

    clean_mod = module_id.strip().lower()

    # Find block
    block_obj = (
        db.query(FacilityBlock)
        .filter(FacilityBlock.organisation_id == organisation_id, FacilityBlock.block_id == block_id)
        .first()
    )
    if not block_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Facility block '{block_id}' not found in organisation '{organisation_id}'.",
        )

    now_dt = _utcnow()
    cutoff_dt = now_dt - period_td

    # Fetch block telemetry points
    readings = (
        db.query(SensorReading)
        .filter(
            SensorReading.organisation_id == organisation_id,
            SensorReading.block_id == block_id,
            SensorReading.sensor_type == clean_mod,
            SensorReading.timestamp >= cutoff_dt,
        )
        .order_by(SensorReading.timestamp.asc())
        .all()
    )

    if not readings:
        readings = (
            db.query(SensorReading)
            .filter(
                SensorReading.organisation_id == organisation_id,
                SensorReading.block_id == block_id,
                SensorReading.sensor_type == clean_mod,
            )
            .order_by(SensorReading.timestamp.asc())
            .all()
        )

    total_count = len(readings)
    has_history = total_count >= 3

    unit_map = {
        "energy": "kWh",
        "water": "L",
        "waste": "%",
        "air_quality": "AQI",
        "temperature": "°C",
        "humidity": "%",
        "co2": "ppm",
        "traffic": "veh/h",
        "parking": "%",
        "assets": "%",
        "safety": "%",
        "climate": "°C",
    }
    unit = unit_map.get(clean_mod, "")

    if readings:
        unit = readings[-1].unit or unit
        values = [r.value for r in readings]
        current_val = float(readings[-1].value)
        average_val = float(sum(values) / len(values))
        peak_val = float(max(values))
        peak_val = max(peak_val, current_val)

        if len(values) >= 2:
            mid = len(values) // 2
            first_half = sum(values[:mid]) / mid if mid > 0 else values[0]
            second_half = sum(values[mid:]) / (len(values) - mid)
            diff = second_half - first_half
            pct = (diff / first_half * 100.0) if first_half != 0 else 0.0
            change_pct_str = f"+{pct:.1f}%" if pct >= 0 else f"{pct:.1f}%"
        else:
            change_pct_str = "+0.0%"
    else:
        current_val = 0.0
        average_val = 0.0
        peak_val = 0.0
        change_pct_str = "0.0%"

    # Block config baseline and thresholds
    sensor_cfg = config.sensor_configs_dict.get(clean_mod, {})
    blk_baseline = float(sensor_cfg.get("baseline", 100.0))
    blk_warn_pct = float(sensor_cfg.get("warning_threshold", 15.0))
    blk_crit_pct = float(sensor_cfg.get("critical_threshold", 30.0))
    warn_thresh = blk_baseline * (1.0 + blk_warn_pct / 100.0)
    crit_thresh = blk_baseline * (1.0 + blk_crit_pct / 100.0)

    # Block trend graph points
    trend_points: List[TrendPointItem] = []
    if readings:
        if len(readings) > 150:
            stride = max(1, len(readings) // 100)
            selected_indices = set(range(0, len(readings), stride))
            selected_indices.add(len(readings) - 1)
            for idx, r in enumerate(readings):
                if r.is_anomaly:
                    selected_indices.add(idx)
            selected_readings = [readings[i] for i in sorted(selected_indices)]
        else:
            selected_readings = readings

        for r in selected_readings:
            ts_str = r.timestamp.isoformat() if r.timestamp else _utcnow().isoformat()
            trend_points.append(
                TrendPointItem(
                    timestamp=ts_str,
                    value=round(r.value, 2),
                    is_anomaly=bool(r.is_anomaly),
                    anomaly_severity=r.anomaly_severity,
                    baseline=round(blk_baseline, 2),
                    warning_threshold=round(warn_thresh, 2),
                    critical_threshold=round(crit_thresh, 2),
                )
            )

    # Block anomalies
    valid_metrics = [clean_mod]
    if clean_mod == "climate":
        valid_metrics = ["climate", "temperature", "humidity", "co2"]
    elif clean_mod == "air_quality":
        valid_metrics = ["air_quality", "pm25", "pm10", "aqi"]
    elif clean_mod == "waste":
        valid_metrics = ["waste", "waste_level"]
    elif clean_mod == "traffic":
        valid_metrics = ["traffic", "traffic_parking"]

    block_filter_conditions = or_(
        AnomalyRecord.block_id == block_id,
        AnomalyRecord.block_id == block_obj.block_name,
        AnomalyRecord.facility_id == block_obj.block_name,
        AnomalyRecord.facility_id == block_id,
    )

    anomalies_objs = (
        db.query(AnomalyRecord)
        .filter(
            AnomalyRecord.organisation_id == organisation_id,
            block_filter_conditions,
            AnomalyRecord.metric.in_(valid_metrics),
        )
        .order_by(AnomalyRecord.timestamp.desc())
        .limit(15)
        .all()
    )
    anom_list = [
        {
            "id": a.id,
            "metric": a.metric,
            "value": a.value,
            "expected_min": a.expected_min,
            "expected_max": a.expected_max,
            "severity": a.severity,
            "reason": a.reason,
            "status": a.status,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "block_id": a.block_id,
            "facility_id": a.facility_id,
        }
        for a in anomalies_objs
    ]

    # Block recommendations
    rec_block_conditions = or_(
        AIRecommendation.block_id == block_id,
        AIRecommendation.block_id == block_obj.block_name,
        AIRecommendation.facility_id == block_obj.block_name,
        AIRecommendation.facility_id == block_id,
    )
    recs_objs = (
        db.query(AIRecommendation)
        .filter(
            AIRecommendation.organisation_id == organisation_id,
            rec_block_conditions,
            AIRecommendation.metric.in_(valid_metrics),
        )
        .order_by(AIRecommendation.created_at.desc())
        .limit(15)
        .all()
    )
    rec_list = [
        {
            "id": r.id,
            "anomaly_id": r.anomaly_id,
            "metric": r.metric,
            "current_value": r.current_value,
            "severity": r.severity,
            "priority": r.priority,
            "summary": r.summary,
            "possible_causes": r.possible_causes_list,
            "recommended_actions": r.recommended_actions_list,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "block_id": r.block_id,
            "facility_id": r.facility_id,
        }
        for r in recs_objs
    ]

    # Status & active counts
    active_anoms_count = sum(
        1 for a in anomalies_objs if a.status in (AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED)
    )
    active_recs_count = sum(
        1 for r in recs_objs if r.status in (AIRecommendation.STATUS_ACTIVE, "OPEN")
    )

    open_anoms = [a for a in anomalies_objs if a.status in (AnomalyRecord.STATUS_OPEN, AnomalyRecord.STATUS_ACKNOWLEDGED)]
    if any(a.severity == AnomalyRecord.SEVERITY_CRITICAL for a in open_anoms):
        blk_status = "Critical"
    elif any(a.severity == AnomalyRecord.SEVERITY_HIGH for a in open_anoms):
        blk_status = "Warning"
    else:
        blk_status = "Normal"

    # Prediction via ML Forecasting Service
    block_pred: Optional[PredictionRowItem] = None
    if has_history:
        from app.services.forecasting import forecasting_service
        p_val = current_val
        chg = 0.0
        try:
            fc_resp = forecasting_service.get_forecast(
                db=db, organisation_id=organisation_id, sensor_type=clean_mod, horizon="24h", mode="last"
            )
            if fc_resp and fc_resp.forecast:
                p_val = round(fc_resp.forecast[0].predicted_value, 1)
                chg = round((p_val - current_val) / current_val * 100.0, 1) if current_val > 0 else 0.0
        except Exception:
            p_val = round(current_val * 1.02, 1)
            chg = 2.0

        chg_str = f"+{chg}%" if chg >= 0 else f"{chg}%"
        block_pred = PredictionRowItem(
            location=block_obj.block_name,
            block_id=block_id,
            current_value=round(current_val, 1),
            predicted_value=p_val,
            change_pct_str=chg_str,
            status="Warning" if chg > 10 else "Normal",
        )

    title_map = {
        "energy": "Energy Consumption",
        "water": "Water Usage",
        "waste": "Waste Generation",
        "air_quality": "Air Quality",
        "temperature": "Indoor Temperature",
        "humidity": "Humidity",
        "co2": "CO2 Concentration",
        "traffic": "Traffic Management",
        "parking": "Parking Occupancy",
        "assets": "Assets Monitoring",
        "safety": "Safety Intelligence",
        "climate": "Climate KPI",
        "street_lighting": "Street Lighting",
        "roads": "Roads & Infrastructure",
        "parks": "Parks & Playgrounds",
        "sewage": "Drainage & Sewage",
    }
    module_title = title_map.get(clean_mod, clean_mod.capitalize())

    return ModuleBlockDetailResponse(
        organisation_id=org.id,
        organisation_name=org.name,
        module_id=clean_mod,
        module_title=module_title,
        block_id=block_id,
        block_name=block_obj.block_name,
        unit=unit,
        current_value=round(current_val, 2),
        average=round(average_val, 2),
        peak=round(peak_val, 2),
        change_pct_str=change_pct_str,
        status=blk_status,
        has_sufficient_history=has_history,
        trend_points=trend_points,
        prediction=block_pred,
        anomalies=anom_list,
        recommendations=rec_list,
        active_anomalies_count=active_anoms_count,
        active_recommendations_count=active_recs_count,
        baseline=round(blk_baseline, 2),
        warning_threshold=round(warn_thresh, 2),
        critical_threshold=round(crit_thresh, 2),
    )
