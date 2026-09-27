"""
GreenNexa — Machine Learning Management & Explainability API Router.

Routes:
  GET  /api/v1/ml/models                — List registered ML models and evaluation metrics
  GET  /api/v1/ml/models/{model_id}     — Retrieve details of a specific model
  GET  /api/v1/ml/risk/{organisation_id} — Upcoming threshold breach risk estimation (24h)
  GET  /api/v1/ml/explain/{anomaly_id}  — Transparent decision attribution for an anomaly
  GET  /api/v1/ml/insights/{organisation_id} — Executive sustainability briefing synthesis
  POST /api/v1/ml/retrain/{organisation_id} — Trigger background model retraining
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, verify_organisation_access
from app.db.database import get_db
from app.db.models import Organisation, SensorReading, User
from app.services.future_anomaly_service import future_anomaly_service
from app.services.insight_service import insight_service
from app.services.ml_explainability import ml_explainability_service
from app.services.model_registry import model_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.get(
    "/models",
    summary="List registered ML models",
    description="Returns metadata, evaluation metrics, and algorithms of all trained models in the registry.",
)
def list_models(
    model_type: Optional[str] = Query(None, description="Filter by model type (e.g. forecasting, anomaly_detection)"),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    models = model_registry.list_models(filter_type=model_type)
    return {
        "status": "success",
        "total_models": len(models),
        "models": models,
    }


@router.get(
    "/models/{model_id}",
    summary="Get model metadata & metrics",
    description="Returns configuration, hyperparameters, and holdout backtesting metrics for a registered model.",
)
def get_model_details(
    model_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    model, meta = model_registry.load_model(model_id)
    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found in registry.",
        )
    return {
        "status": "success",
        "model_id": model_id,
        "metadata": meta,
        "loaded_in_memory": model is not None,
    }


@router.get(
    "/risk/{organisation_id}",
    summary="Evaluate future anomaly risk",
    description="Projects 24h ML forecast against thresholds to calculate upcoming breach probability.",
)
def get_future_risk(
    organisation_id: str,
    metric: str = Query("energy", description="Sensor metric to evaluate (e.g. energy, water)"),
    horizon: str = Query("24h", description="Evaluation horizon (6h, 12h, 24h, 48h, 72h)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    verify_organisation_access(organisation_id, current_user)
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{organisation_id}' not found.",
        )

    risk_res = future_anomaly_service.evaluate_future_risk(
        db=db, organisation_id=organisation_id, metric=metric, horizon=horizon
    )
    return risk_res


@router.get(
    "/explain/{anomaly_id}",
    summary="Explain anomaly detection decision",
    description="Provides transparent feature attribution and Isolation Forest scoring breakdown.",
)
def explain_anomaly(
    anomaly_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    explanation = ml_explainability_service.explain_anomaly(db, anomaly_id)
    if "error" in explanation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=explanation["error"],
        )
    # Check access to organisation
    verify_organisation_access(explanation["organisation_id"], current_user)
    return explanation


@router.get(
    "/insights/{organisation_id}",
    summary="Synthesize sustainability executive briefing",
    description="Generative briefing combining ML anomaly detection, forecasting risk, and environmental context.",
)
def get_sustainability_insights(
    organisation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    verify_organisation_access(organisation_id, current_user)
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation '{organisation_id}' not found.",
        )

    return insight_service.generate_sustainability_briefing(db, organisation_id)


@router.post(
    "/retrain/{organisation_id}",
    summary="Trigger model retraining",
    description="Forces on-demand retraining of ML models for an organisation using latest historical telemetry.",
)
def trigger_retraining(
    organisation_id: str,
    metric: str = Query("energy", description="Metric to retrain"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    verify_organisation_access(organisation_id, current_user)

    from app.services.forecasting import forecasting_service
    forecasting_service.clear_cache()

    try:
        fc = forecasting_service.get_forecast(
            db=db, organisation_id=organisation_id, sensor_type=metric, horizon="24h", mode="last"
        )
        return {
            "status": "success",
            "message": f"Successfully retrained ML model for {metric} in organisation {organisation_id}.",
            "model_used": fc.model,
            "metrics": fc.metrics,
            "sample_count": fc.available_days,
        }
    except Exception as e:
        logger.warning("Retraining encountered notice: %s", e)
        return {
            "status": "partial",
            "message": f"Retraining initiated with notice: {str(e)}",
        }
