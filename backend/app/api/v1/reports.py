"""
GreenNexa — Reporting & File Export API Router.

Routes:
  GET /api/v1/reports/dashboard       — Download Dashboard summary report (CSV/PDF)
  GET /api/v1/reports/energy          — Download Energy report (CSV/PDF)
  GET /api/v1/reports/water           — Download Water report (CSV/PDF)
  GET /api/v1/reports/waste           — Download Waste report (CSV/PDF)
  GET /api/v1/reports/environmental   — Download Environmental/Sensors report (CSV/PDF)
  GET /api/v1/reports/anomalies       — Download Anomaly report (CSV/PDF)
  GET /api/v1/reports/recommendations — Download AI Recommendations report (CSV/PDF)
  GET /api/v1/reports/forecast      — Download Forecast report (CSV/PDF)
  GET /api/v1/reports/iot           — Download IoT Sensor Data report (CSV/PDF)
  GET /api/v1/reports/{report_type}   — Unified report export endpoint (CSV/PDF)
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, verify_organisation_access
from app.db.database import get_db
from app.db.models import User
from app.services.reporting import reporting_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reporting & Download System"])


def _generate_report_response(
    db: Session,
    current_user: User,
    organisation_id: Optional[str],
    report_type: str,
    format: str,
    start_date: Optional[date],
    end_date: Optional[date],
    sensor_type: Optional[str] = None,
    source: Optional[str] = None,
    severity: Optional[str] = None,
    status_param: Optional[str] = None,
    horizon: str = "24h",
) -> Response:
    """Helper function to execute report generation and format HTTP attachment response."""
    target_org_id = verify_organisation_access(organisation_id, current_user)

    try:
        file_bytes, media_type, filename = reporting_service.generate_report(
            db=db,
            organisation_id=target_org_id,
            report_type=report_type,
            export_format=format,
            start_date=start_date,
            end_date=end_date,
            sensor_type=sensor_type,
            source=source,
            severity=severity,
            status=status_param,
            horizon=horizon,
        )
        return Response(
            content=file_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        detail_str = str(e)
        if "not found" in detail_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail_str,
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail_str,
        )
    except Exception as e:
        logger.exception("Unexpected error generating %s report: %s", report_type, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate {report_type} report.",
        )


@router.get(
    "/dashboard",
    summary="Download Dashboard summary report",
    description="Export dashboard KPIs and summary in CSV or PDF format.",
)
def get_dashboard_report(
    organisation_id: Optional[str] = Query(None, description="Organisation ID (defaults to user's org)"),
    format: str = Query("csv", description="Export format: csv | pdf"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(db, current_user, organisation_id, "dashboard", format, None, None)


@router.get(
    "/energy",
    summary="Download Energy report",
    description="Export energy sensor readings, statistics, and anomalies in CSV or PDF format.",
)
def get_energy_report(
    organisation_id: Optional[str] = Query(None),
    format: str = Query("csv", description="csv | pdf"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    source: Optional[str] = Query(None, description="synthetic | iot"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(db, current_user, organisation_id, "energy", format, start_date, end_date, sensor_type="energy", source=source)


@router.get(
    "/water",
    summary="Download Water report",
    description="Export water sensor readings and summary in CSV or PDF format.",
)
def get_water_report(
    organisation_id: Optional[str] = Query(None),
    format: str = Query("csv", description="csv | pdf"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    source: Optional[str] = Query(None, description="synthetic | iot"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(db, current_user, organisation_id, "water", format, start_date, end_date, sensor_type="water", source=source)


@router.get(
    "/waste",
    summary="Download Waste report",
    description="Export waste sensor readings and summary in CSV or PDF format.",
)
def get_waste_report(
    organisation_id: Optional[str] = Query(None),
    format: str = Query("csv", description="csv | pdf"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    source: Optional[str] = Query(None, description="synthetic | iot"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(db, current_user, organisation_id, "waste", format, start_date, end_date, sensor_type="waste", source=source)


@router.get(
    "/environmental",
    summary="Download Environmental report",
    description="Export temperature, humidity, and CO2 sensor readings in CSV or PDF format.",
)
def get_environmental_report(
    organisation_id: Optional[str] = Query(None),
    format: str = Query("csv", description="csv | pdf"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    sensor_type: Optional[str] = Query(None, description="temperature | humidity | co2"),
    source: Optional[str] = Query(None, description="synthetic | iot"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(db, current_user, organisation_id, "environmental", format, start_date, end_date, sensor_type=sensor_type, source=source)


@router.get(
    "/anomalies",
    summary="Download Anomaly report",
    description="Export statistical anomaly log records in CSV or PDF format.",
)
def get_anomalies_report(
    organisation_id: Optional[str] = Query(None),
    format: str = Query("csv", description="csv | pdf"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    sensor_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH | CRITICAL"),
    status: Optional[str] = Query(None, description="OPEN | ACKNOWLEDGED | RESOLVED"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(db, current_user, organisation_id, "anomalies", format, start_date, end_date, sensor_type=sensor_type, severity=severity, status_param=status)


@router.get(
    "/recommendations",
    summary="Download AI Recommendation report",
    description="Export AI sustainability recommendation records in CSV or PDF format.",
)
def get_recommendations_report(
    organisation_id: Optional[str] = Query(None),
    format: str = Query("csv", description="csv | pdf"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    sensor_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH | CRITICAL"),
    status: Optional[str] = Query(None, description="ACTIVE | ACTIONED | DISMISSED"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(db, current_user, organisation_id, "recommendations", format, start_date, end_date, sensor_type=sensor_type, severity=severity, status_param=status)


@router.get(
    "/forecast",
    summary="Download Forecast report",
    description="Export Phase 9 AI time-series forecast predictions in CSV or PDF format.",
)
def get_forecast_report(
    organisation_id: Optional[str] = Query(None),
    format: str = Query("csv", description="csv | pdf"),
    sensor_type: str = Query("energy", description="energy | water"),
    horizon: str = Query("24h", description="6h | 12h | 24h | 48h | 72h"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(db, current_user, organisation_id, "forecast", format, None, None, sensor_type=sensor_type, horizon=horizon)


@router.get(
    "/iot",
    summary="Download IoT Sensor Data report",
    description="Export IoT ingested sensor readings in CSV or PDF format.",
)
def get_iot_report(
    organisation_id: Optional[str] = Query(None),
    format: str = Query("csv", description="csv | pdf"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    sensor_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(db, current_user, organisation_id, "iot", format, start_date, end_date, sensor_type=sensor_type)


@router.get(
    "/daily",
    summary="Download Date-wise Comprehensive Report (CSV/PDF)",
    description="Export strict date-wise data matching the selected simulated date (exact CSV schema or Power BI-style PDF).",
)
def get_daily_report(
    organisation_id: Optional[str] = Query(None),
    date: Optional[date] = Query(None, description="Simulated date to export (e.g. 2026-09-20)"),
    format: str = Query("csv", description="csv | pdf"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(
        db=db,
        current_user=current_user,
        organisation_id=organisation_id,
        report_type="daily",
        format=format,
        start_date=date,
        end_date=date,
    )


@router.get(
    "/date-wise",
    summary="Download Date-wise Comprehensive Report (CSV/PDF)",
    description="Alias for /daily date-wise report download.",
)
def get_date_wise_report(
    organisation_id: Optional[str] = Query(None),
    date: Optional[date] = Query(None, description="Simulated date to export (e.g. 2026-09-20)"),
    format: str = Query("csv", description="csv | pdf"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(
        db=db,
        current_user=current_user,
        organisation_id=organisation_id,
        report_type="daily",
        format=format,
        start_date=date,
        end_date=date,
    )


@router.get(
    "/{report_type}",
    summary="Unified report download endpoint",
    description="Unified report endpoint for dashboard, energy, water, waste, environmental, anomalies, recommendations, forecast, and iot reports.",
)
def get_unified_report(
    report_type: str,
    organisation_id: Optional[str] = Query(None),
    format: str = Query("csv", description="csv | pdf"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    sensor_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    horizon: str = Query("24h"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _generate_report_response(
        db=db,
        current_user=current_user,
        organisation_id=organisation_id,
        report_type=report_type,
        format=format,
        start_date=start_date,
        end_date=end_date,
        sensor_type=sensor_type,
        source=source,
        severity=severity,
        status_param=status,
        horizon=horizon,
    )
