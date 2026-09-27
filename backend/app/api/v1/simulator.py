
"""
GreenNexa — Synthetic Data Simulator API Router.

Routes:
  POST /api/v1/simulator/synthetic/start  — Start background simulator loop
  POST /api/v1/simulator/synthetic/stop   — Stop background simulator loop
  GET  /api/v1/simulator/synthetic/status — Get simulator running status
"""

from __future__ import annotations

from datetime import date, timedelta
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.db.models import Organisation, PlatformState, User, _utcnow
from app.schemas.simulator import (
    ChangeSimulatedDayRequest,
    SetSimulatedDateRequest,
    SimulatorStartRequest,
    SimulatorStatusResponse,
)
from app.services.synthetic_simulator import simulator_instance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulator/synthetic", tags=["Synthetic Data Simulator"])


# Helper: Validate role permissions (Only SUPER_ADMIN and ADMIN allowed)
def _verify_simulator_access(current_user: User, organisation_id: Optional[str] = None) -> None:
    if current_user.role not in (User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Insufficient role permissions for simulator control.",
        )
    if current_user.role == User.ROLE_ADMIN and organisation_id:
        if current_user.organisation_id != organisation_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only control simulator for your own organisation.",
            )


@router.post(
    "/start",
    response_model=SimulatorStatusResponse,
    summary="Start synthetic data simulator",
    description="Starts background synthetic sensor data generation (default interval: 30s).",
)
def start_simulator(
    body: Optional[SimulatorStartRequest] = None,
    organisation_id: Optional[str] = Query(None, description="Optional target organisation ID filter for ADMIN validation"),
    module: Optional[str] = Query(None, description="Optional target module to scope demo mode to"),
    current_user: User = Depends(get_current_user),
):
    _verify_simulator_access(current_user, organisation_id)

    interval = body.interval_seconds if body and body.interval_seconds else 30
    demo_mode = bool(getattr(body, "demo_mode", False)) if body else False
    target_module = (body.module if body and body.module else None) or module
    target_org_id = organisation_id or current_user.organisation_id
    simulator_instance.start(interval_seconds=interval, demo_mode=demo_mode, organisation_id=target_org_id, module=target_module)

    logger.info("Simulator start requested by user=%s role=%s (interval=%ds demo_mode=%s org=%s module=%s)", current_user.email, current_user.role, interval, demo_mode, target_org_id, target_module)
    return simulator_instance.status(organisation_id=target_org_id, module=target_module)


@router.post(
    "/stop",
    response_model=SimulatorStatusResponse,
    summary="Stop synthetic data simulator",
    description="Stops background synthetic sensor data generation.",
)
def stop_simulator(
    organisation_id: Optional[str] = Query(None, description="Optional target organisation ID filter for ADMIN validation"),
    module: Optional[str] = Query(None, description="Optional target module to stop demo mode for"),
    current_user: User = Depends(get_current_user),
):
    _verify_simulator_access(current_user, organisation_id)

    target_org_id = organisation_id or current_user.organisation_id
    simulator_instance.stop(organisation_id=target_org_id, module=module)

    logger.info("Simulator stop requested by user=%s role=%s org=%s module=%s", current_user.email, current_user.role, target_org_id, module)
    return simulator_instance.status(organisation_id=target_org_id, module=module)


@router.get(
    "/status",
    response_model=SimulatorStatusResponse,
    summary="Get simulator status",
    description="Returns operational status and execution metrics of synthetic data simulator.",
)
def get_simulator_status(
    organisation_id: Optional[str] = Query(None, description="Optional target organisation ID filter for ADMIN validation"),
    module: Optional[str] = Query(None, description="Optional target module"),
    current_user: User = Depends(get_current_user),
):
    _verify_simulator_access(current_user, organisation_id)
    return simulator_instance.status(organisation_id=organisation_id or current_user.organisation_id, module=module)


@router.post(
    "/generate-reading",
    summary="Generate single sensor reading cycle",
    description="Immediately generates one cycle of synthetic sensor readings for the user's organisation.",
)
def generate_single_reading(
    organisation_id: Optional[str] = Query(None, description="Optional target organisation ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_org_id = organisation_id or current_user.organisation_id
    if not target_org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No organisation ID provided or associated with user.")

    _verify_simulator_access(current_user, target_org_id)
    readings = simulator_instance.run_cycle_for_org(db, target_org_id)
    return {
        "status": "success",
        "organisation_id": target_org_id,
        "readings_generated": len(readings),
        "anomalies_generated": sum(1 for r in readings if r.is_anomaly),
    }


@router.post(
    "/generate-anomaly",
    summary="Trigger controlled demo anomaly",
    description="Immediately triggers a high-severity anomaly reading for demonstration purposes.",
)
def generate_demo_anomaly(
    sensor_type: str = Query("energy", description="Sensor metric to trigger anomaly on"),
    organisation_id: Optional[str] = Query(None, description="Optional target organisation ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_org_id = organisation_id or current_user.organisation_id
    if not target_org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No organisation ID provided or associated with user.")

    _verify_simulator_access(current_user, target_org_id)
    readings = simulator_instance.run_cycle_for_org(db, target_org_id, forced_anomaly_sensor=sensor_type, ignore_gap=True)

    anomalous = [r for r in readings if r.is_anomaly]
    return {
        "status": "success",
        "organisation_id": target_org_id,
        "sensor_type": sensor_type,
        "anomalies_generated": len(anomalous),
        "details": [
            {
                "sensor_type": r.sensor_type,
                "value": r.value,
                "unit": r.unit,
                "severity": r.anomaly_severity,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in anomalous
        ],
    }


@router.post(
    "/reset-demo",
    summary="Reset demo synthetic data",
    description="Safely clears synthetic readings and anomalies for demonstration reset.",
)
def reset_demo_data(
    organisation_id: Optional[str] = Query(None, description="Optional target organisation ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_org_id = organisation_id or current_user.organisation_id
    if not target_org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No organisation ID provided or associated with user.")

    _verify_simulator_access(current_user, target_org_id)
    result = simulator_instance.reset_demo_data(db, target_org_id)
    return {
        "status": "success",
        "organisation_id": target_org_id,
        "readings_deleted": result["readings_deleted"],
        "anomalies_deleted": result["anomalies_deleted"],
    }


STATE_KEY_SIMULATED_DATE = "platform_simulated_date"


def _get_platform_date(db: Session) -> date:
    try:
        state = db.query(PlatformState).filter_by(key=STATE_KEY_SIMULATED_DATE).first()
        if state and state.value:
            return date.fromisoformat(state.value.strip())
    except Exception:
        pass
    return date(2026, 9, 20)


def _set_platform_date(db: Session, new_date: date) -> date:
    try:
        state = db.query(PlatformState).filter_by(key=STATE_KEY_SIMULATED_DATE).first()
        if not state:
            state = PlatformState(key=STATE_KEY_SIMULATED_DATE, value=new_date.isoformat())
            db.add(state)
        else:
            state.value = new_date.isoformat()
            state.updated_at = _utcnow()
        db.commit()
    except Exception as e:
        logger.warning("Could not persist platform simulated date: %s", e)
    return new_date


def _resolve_target_org(db: Session, current_user: User, organisation_id: Optional[str]) -> Optional[str]:
    candidate_id = organisation_id or current_user.organisation_id
    if candidate_id:
        org = db.query(Organisation).filter(Organisation.id == candidate_id).first()
        if org:
            return org.id

    if current_user.role == User.ROLE_SUPER_ADMIN:
        first_org = db.query(Organisation.id).filter(Organisation.is_active == True).first()
        if first_org:
            return first_org[0]
        return None

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No organisation ID provided or associated with user.",
    )


@router.get(
    "/current-day",
    summary="Get current simulated date and day name",
    description="Returns the organisation's current simulated date, day name, and display text.",
)
def get_current_simulated_day(
    organisation_id: Optional[str] = Query(None, description="Optional target organisation ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_org_id = _resolve_target_org(db, current_user, organisation_id)
    _verify_simulator_access(current_user, target_org_id)
    if not target_org_id:
        sim_date = _get_platform_date(db)
        day_name = sim_date.strftime("%a").upper()
        return {
            "organisation_id": None,
            "simulated_date": sim_date.isoformat(),
            "day_name": day_name,
            "day_of_week": day_name,
            "date_display": f"{sim_date.strftime('%d %b %Y')} / {day_name}",
        }
    return simulator_instance.get_simulated_day(db, target_org_id)


@router.post(
    "/change-day",
    summary="Advance to next simulated calendar day",
    description="Moves simulation to the next calendar day while preserving all previous day operational history.",
)
def advance_simulated_day(
    body: Optional[ChangeSimulatedDayRequest] = None,
    organisation_id: Optional[str] = Query(None, description="Optional target organisation ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req_org = (body.organisation_id if body else None) or organisation_id
    target_org_id = _resolve_target_org(db, current_user, req_org)
    _verify_simulator_access(current_user, target_org_id)

    if body and body.date:
        try:
            target_date = date.fromisoformat(body.date.strip())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date format '{body.date}'. Expected YYYY-MM-DD.",
            )
        _set_platform_date(db, target_date)
        if not target_org_id:
            day_name = target_date.strftime("%a").upper()
            return {
                "organisation_id": None,
                "previous_date": target_date.isoformat(),
                "simulated_date": target_date.isoformat(),
                "day_name": day_name,
                "day_of_week": day_name,
                "date_display": f"{target_date.strftime('%d %b %Y')} / {day_name}",
                "message": f"Simulated date set to {target_date.isoformat()} ({day_name}).",
            }
        return simulator_instance.set_simulated_date(db, target_org_id, target_date)

    days = body.days if (body and body.days is not None) else 1
    if not target_org_id:
        prev_date = _get_platform_date(db)
        new_date = prev_date + timedelta(days=days)
        _set_platform_date(db, new_date)
        day_name = new_date.strftime("%a").upper()
        return {
            "organisation_id": None,
            "previous_date": prev_date.isoformat(),
            "simulated_date": new_date.isoformat(),
            "day_name": day_name,
            "day_of_week": day_name,
            "date_display": f"{new_date.strftime('%d %b %Y')} / {day_name}",
            "message": f"Simulated day advanced to {new_date.isoformat()} ({day_name}).",
        }

    res = simulator_instance.change_simulated_day(db, target_org_id, days=days)
    if isinstance(res, dict) and "simulated_date" in res:
        try:
            _set_platform_date(db, date.fromisoformat(res["simulated_date"]))
        except Exception:
            pass
    return res


@router.post(
    "/set-date",
    summary="Manually set simulated calendar date",
    description="Manually sets the organisation's simulated calendar date while preserving history and resetting baseline.",
)
def set_simulated_date_endpoint(
    body: SetSimulatedDateRequest,
    organisation_id: Optional[str] = Query(None, description="Optional target organisation ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_org_id = _resolve_target_org(db, current_user, body.organisation_id or organisation_id)
    _verify_simulator_access(current_user, target_org_id)
    try:
        target_date = date.fromisoformat(body.date.strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid date format '{body.date}'. Expected YYYY-MM-DD.",
        )
    _set_platform_date(db, target_date)
    if not target_org_id:
        day_name = target_date.strftime("%a").upper()
        return {
            "organisation_id": None,
            "previous_date": target_date.isoformat(),
            "simulated_date": target_date.isoformat(),
            "day_name": day_name,
            "day_of_week": day_name,
            "date_display": f"{target_date.strftime('%d %b %Y')} / {day_name}",
            "message": f"Simulated date set to {target_date.isoformat()} ({day_name}).",
        }
    return simulator_instance.set_simulated_date(db, target_org_id, target_date)


direct_router = APIRouter(prefix="/simulator", tags=["Synthetic Data Simulator"])
direct_router.add_api_route("/current-day", get_current_simulated_day, methods=["GET"])
direct_router.add_api_route("/change-day", advance_simulated_day, methods=["POST"])
direct_router.add_api_route("/set-date", set_simulated_date_endpoint, methods=["POST"])



