"""
GreenNexa — AI/ML Time-Series Forecasting API Router.

Routes:
  GET /api/v1/forecast/{organisation_id} — Short-term AI time-series forecast for energy & water metrics.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, verify_organisation_access
from app.db.database import get_db
from app.db.models import Organisation, OrganisationSensorConfig, User
from app.schemas.forecast import ForecastResponse
from app.services.forecasting import forecasting_service

from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forecast", tags=["AI/ML Forecasting"])


@router.get(
    "/{organisation_id}",
    response_model=ForecastResponse,
    summary="Generate time-series forecast",
    description=(
        "Returns a short-term AI time-series forecast with 95% confidence bounds "
        "for the requested sensor metric (energy or water)."
    ),
)
def get_organisation_forecast(
    organisation_id: str,
    sensor_type: str = Query(..., description="Sensor metric to forecast (e.g. energy, water)"),
    horizon: str = Query("24h", description="Forecast horizon (6h, 12h, 24h, 48h, 72h)"),
    mode: Optional[str] = Query(None, description="Forecast mode: default, last, 7d, 15d, 30d"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ForecastResponse:
    """
    Generate time-series forecast for an organisation.
    """
    # 1. Enforce RBAC & organisation access
    verify_organisation_access(organisation_id, current_user)

    # 2. Check organisation existence
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{organisation_id}' not found.",
        )

    # 3. Check sensor configuration & enablement
    clean_sensor = sensor_type.lower().strip()
    config = (
        db.query(OrganisationSensorConfig)
        .filter(OrganisationSensorConfig.organisation_id == organisation_id)
        .first()
    )

    if config and clean_sensor not in config.enabled_sensors_list:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Sensor '{sensor_type}' is disabled for organisation '{organisation_id}'.",
        )

    # 4. Generate forecast
    try:
        forecast_res = forecasting_service.get_forecast(
            db=db,
            organisation_id=organisation_id,
            sensor_type=clean_sensor,
            horizon=horizon,
            mode=mode,
        )
        return forecast_res
    except ValueError as e:
        logger.info(f"Forecast validation exception for {organisation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected forecasting error for {organisation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the forecast.",
        )
