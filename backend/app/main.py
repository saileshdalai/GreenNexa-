"""
GreenNexa — FastAPI Application Entry Point.
"""

from __future__ import annotations

import logging

import os
from dotenv import load_dotenv

# Ensure backend/.env is loaded into os.environ
_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(_env_path):
    load_dotenv(_env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.db.database as db_database
from app.api.v1.ai import router as ai_router
from app.api.v1.anomalies import router as anomaly_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.forecast import router as forecast_router
from app.api.v1.iot import router as iot_router
from app.api.v1.messages import router as messages_router
from app.api.v1.ml import router as ml_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.organisations import router as organisation_router
from app.api.v1.recommendations import router as recommendation_router
from app.api.v1.reports import router as reports_router
from app.api.v1.simulator import direct_router as simulator_direct_router, router as simulator_router
from app.api.v1.super_admin import router as super_admin_router
from app.db.seed_demo import seed_demo_data

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="GreenNexa API",
    description=(
        "AI-Powered Sustainable Facility Intelligence — Backend API.\n\n"
        "Provides anomaly detection, AI recommendations, and authentication.\n\n"
        "**Note:** AI recommendations are decision-support suggestions only. "
        "They are not verified diagnoses."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — restrict in production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://[::1]:3000",
        "http://[::1]:3001",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Create tables on startup (safe for SQLite and PostgreSQL)
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    logger.info("GreenNexa backend starting — creating database tables…")
    db_database.create_all_tables()
    # Safe column migration for SQLite/PostgreSQL
    try:
        from sqlalchemy import text
        with db_database.engine.connect() as conn:
            if not str(db_database.engine.url).startswith("sqlite"):
                conn.execute(text("ALTER TABLE organisation_sensor_configs ADD COLUMN IF NOT EXISTS simulated_date DATE"))
            else:
                conn.execute(text("ALTER TABLE organisation_sensor_configs ADD COLUMN simulated_date DATE"))
            conn.commit()
    except Exception:
        pass
    logger.info("Database tables ready. Seeding demo accounts…")
    db = db_database.SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()
    logger.info("Demo user accounts ready.")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(ai_router, prefix=API_PREFIX)
app.include_router(organisation_router, prefix=API_PREFIX)
app.include_router(super_admin_router, prefix=API_PREFIX)
app.include_router(anomaly_router, prefix=API_PREFIX)
app.include_router(recommendation_router, prefix=API_PREFIX)
app.include_router(simulator_router, prefix=API_PREFIX)
app.include_router(simulator_direct_router, prefix=API_PREFIX)
app.include_router(iot_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(forecast_router, prefix=API_PREFIX)
app.include_router(messages_router, prefix=API_PREFIX)
app.include_router(notifications_router, prefix=API_PREFIX)
app.include_router(reports_router, prefix=API_PREFIX)
app.include_router(ml_router, prefix=API_PREFIX)


from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.api.v1.organisations import get_current_user_sensor_config
from app.schemas.sensor_config import SensorConfigResponse
from app.db.models import User
from sqlalchemy.orm import Session
from fastapi import Depends

@app.get(
    "/api/v1/organisation/sensor-config",
    response_model=SensorConfigResponse,
    tags=["Organisation Management"],
    summary="Get authenticated user's organisation sensor configuration",
)
def get_singular_organisation_sensor_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_current_user_sensor_config(current_user=current_user, db=db)




# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "GreenNexa API"}


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "GreenNexa API — AI-Powered Sustainable Facility Intelligence",
        "docs": "/docs",
        "health": "/health",
    }
