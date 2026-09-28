"""
GreenNexa — Database connection and session management.

Uses SQLAlchemy 2.0 with support for:
- PostgreSQL (production)
- SQLite (testing / local dev without PostgreSQL)
"""

import os
import re
import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Priority: .env file / environment variable → SQLite fallback for tests
# Absolute backend directory used to resolve relative SQLite DB paths.
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Try loading from backend/.env if python-dotenv is available
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(_backend_dir, ".env")
    if os.path.exists(_env_path):
        load_dotenv(dotenv_path=_env_path, override=True)
except ImportError:
    pass

_raw_url = os.environ.get("DATABASE_URL", "").strip()
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)

# Fall back to SQLite for local development/testing
if not _raw_url:
    _default_db_path = os.path.join(_backend_dir, "greennexa_test.db").replace("\\", "/")
    DATABASE_URL: str = f"sqlite:///{_default_db_path}"
else:
    DATABASE_URL: str = _raw_url


def _normalize_sqlite_url(url: str, base_dir: str) -> str:
    """
    Resolve relative SQLite file URLs against the backend directory so the
    DB file location never depends on the current working directory.
    Prevents accidental shadow databases (e.g. a 0-byte greennexa_test.db in
    the repo root) when DATABASE_URL=sqlite:///./greennexa_test.db is used.
    """
    if not url.startswith("sqlite:///"):
        return url
    remainder = url[len("sqlite:///"):]
    if remainder == ":memory:" or remainder.startswith(":memory:"):
        return url
    if remainder.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", remainder):
        return url
    abs_path = os.path.abspath(os.path.join(base_dir, remainder)).replace("\\", "/")
    return f"sqlite:///{abs_path}"


DATABASE_URL = _normalize_sqlite_url(DATABASE_URL, _backend_dir)
try:
    from sqlalchemy.engine import make_url
    _masked_url = make_url(DATABASE_URL).render_as_string(hide_password=True)
except Exception:
    _masked_url = DATABASE_URL
logger.info("GreenNexa active persistent database URL: %s", _masked_url)

# ---------------------------------------------------------------------------
# Engine setup
# ---------------------------------------------------------------------------
_is_sqlite = DATABASE_URL.startswith("sqlite")

_connect_args: dict = {}
if _is_sqlite:
    # SQLite requires check_same_thread=False for FastAPI's thread model
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    # For PostgreSQL: use a connection pool
    # For SQLite: pool_pre_ping is harmless
    pool_pre_ping=True,
)

# Enable foreign keys for SQLite (not enforced by default)
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ---------------------------------------------------------------------------
# Declarative base (shared by all models)
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency — yields a DB session and closes it after the request
# ---------------------------------------------------------------------------
def get_db():
    """Yield a SQLAlchemy session. Closes on completion or error."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def safe_vacuum_sqlite(eng=None) -> bool:
    """
    Safely execute VACUUM on SQLite or PostgreSQL database to compact free pages and release
    filesystem space after destructive deletion operations.
    Runs with autocommit to prevent active transaction conflicts.
    """
    target_engine = eng or engine
    db_url = str(target_engine.url)
    if db_url.startswith("sqlite") and ":memory:" not in db_url:
        try:
            with target_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                from sqlalchemy import text
                conn.execute(text("VACUUM"))
            logger.info("SQLite VACUUM compaction completed successfully.")
            return True
        except Exception as e:
            logger.warning("SQLite VACUUM warning: %s", e)
            return False
    elif not db_url.startswith("sqlite"):
        try:
            with target_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                from sqlalchemy import text
                conn.execute(text("VACUUM"))
            logger.info("PostgreSQL VACUUM completed successfully.")
            return True
        except Exception as e:
            logger.warning("PostgreSQL VACUUM warning: %s", e)
            return False
    return False


def get_active_db_path(eng=None):
    """Return the absolute filesystem path to the active SQLite database, or None if not SQLite."""
    target_engine = eng or engine
    db_url = str(target_engine.url)
    if db_url.startswith("sqlite:///"):
        path = db_url[len("sqlite:///"):]
        if path != ":memory:" and not path.startswith(":memory:"):
            return os.path.abspath(path)
    return None


def get_db_physical_size_bytes(eng=None) -> int:
    """Return actual measured physical database size in bytes."""
    target_engine = eng or engine
    db_path = get_active_db_path(target_engine)
    if db_path and os.path.exists(db_path):
        return os.path.getsize(db_path)
    if not str(target_engine.url).startswith("sqlite"):
        try:
            with target_engine.connect() as conn:
                from sqlalchemy import text
                res = conn.execute(text("SELECT pg_database_size(current_database())")).scalar()
                if res:
                    return int(res)
        except Exception:
            pass
    return 0


# ---------------------------------------------------------------------------
# Convenience: create all tables (used in tests and local startup)
# ---------------------------------------------------------------------------
def create_all_tables():
    """Create all tables defined in models. Safe to call on existing DBs."""
    from app.db import models  # noqa: F401 — import triggers model registration
    Base.metadata.create_all(bind=engine)

    # For SQLite dev databases: ensure newly added columns exist
    if _is_sqlite:
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                # organisations migrations
                result = conn.execute(text("PRAGMA table_info(organisations)"))
                cols = [row[1] for row in result.fetchall()]
                if "contact_email" not in cols:
                    conn.execute(text("ALTER TABLE organisations ADD COLUMN contact_email VARCHAR(255)"))
                if "contact_phone" not in cols:
                    conn.execute(text("ALTER TABLE organisations ADD COLUMN contact_phone VARCHAR(50)"))
                if "facility_name" not in cols:
                    conn.execute(text("ALTER TABLE organisations ADD COLUMN facility_name VARCHAR(200)"))
                if "state" not in cols:
                    conn.execute(text("ALTER TABLE organisations ADD COLUMN state VARCHAR(100)"))
                if "district" not in cols:
                    conn.execute(text("ALTER TABLE organisations ADD COLUMN district VARCHAR(100)"))
                if "city" not in cols:
                    conn.execute(text("ALTER TABLE organisations ADD COLUMN city VARCHAR(100)"))
                if "address" not in cols:
                    conn.execute(text("ALTER TABLE organisations ADD COLUMN address VARCHAR(300)"))
                if "org_code" not in cols:
                    conn.execute(text("ALTER TABLE organisations ADD COLUMN org_code VARCHAR(50)"))
                if "ownership_type" not in cols:
                    conn.execute(text("ALTER TABLE organisations ADD COLUMN ownership_type VARCHAR(50)"))
                if "dashboard_style" not in cols:
                    conn.execute(text("ALTER TABLE organisations ADD COLUMN dashboard_style VARCHAR(30)"))

                # users migrations
                res_u = conn.execute(text("PRAGMA table_info(users)"))
                cols_u = [row[1] for row in res_u.fetchall()]
                if "phone" not in cols_u:
                    conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50)"))
                if "last_login_at" not in cols_u:
                    conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))

                # sensor_readings migrations
                res_sr = conn.execute(text("PRAGMA table_info(sensor_readings)"))
                cols_sr = [row[1] for row in res_sr.fetchall()]
                if "block_id" not in cols_sr:
                    conn.execute(text("ALTER TABLE sensor_readings ADD COLUMN block_id VARCHAR(50)"))
                if "ward_id" not in cols_sr:
                    conn.execute(text("ALTER TABLE sensor_readings ADD COLUMN ward_id VARCHAR(50)"))
                if "created_at" not in cols_sr:
                    conn.execute(text("ALTER TABLE sensor_readings ADD COLUMN created_at DATETIME"))
                if "is_anomaly" not in cols_sr:
                    conn.execute(text("ALTER TABLE sensor_readings ADD COLUMN is_anomaly BOOLEAN DEFAULT 0"))
                if "anomaly_severity" not in cols_sr:
                    conn.execute(text("ALTER TABLE sensor_readings ADD COLUMN anomaly_severity VARCHAR(20)"))

                # anomaly_records migrations
                res_ar = conn.execute(text("PRAGMA table_info(anomaly_records)"))
                cols_ar = [row[1] for row in res_ar.fetchall()]
                if "block_id" not in cols_ar:
                    conn.execute(text("ALTER TABLE anomaly_records ADD COLUMN block_id VARCHAR(50)"))
                if "ward_id" not in cols_ar:
                    conn.execute(text("ALTER TABLE anomaly_records ADD COLUMN ward_id VARCHAR(50)"))
                if "is_seen" not in cols_ar:
                    conn.execute(text("ALTER TABLE anomaly_records ADD COLUMN is_seen BOOLEAN DEFAULT 0"))
                if "seen_at" not in cols_ar:
                    conn.execute(text("ALTER TABLE anomaly_records ADD COLUMN seen_at DATETIME"))
                if "seen_by" not in cols_ar:
                    conn.execute(text("ALTER TABLE anomaly_records ADD COLUMN seen_by VARCHAR(36)"))

                # ai_recommendations migrations
                res_rec = conn.execute(text("PRAGMA table_info(ai_recommendations)"))
                cols_rec = [row[1] for row in res_rec.fetchall()]
                if "block_id" not in cols_rec:
                    conn.execute(text("ALTER TABLE ai_recommendations ADD COLUMN block_id VARCHAR(50)"))
                if "ward_id" not in cols_rec:
                    conn.execute(text("ALTER TABLE ai_recommendations ADD COLUMN ward_id VARCHAR(50)"))

                # organisation_sensor_configs migrations
                res_osc = conn.execute(text("PRAGMA table_info(organisation_sensor_configs)"))
                cols_osc = [row[1] for row in res_osc.fetchall()]
                if "sensor_configs" not in cols_osc:
                    conn.execute(text("ALTER TABLE organisation_sensor_configs ADD COLUMN sensor_configs TEXT"))

                conn.commit()

                # Safe targeted migration: Move actual ward records mistakenly inserted into facility_blocks
                # to municipality_wards, while preserving legitimate office blocks
                try:
                    res_muni_check = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='municipality_wards'")).fetchone()
                    if res_muni_check:
                        res_fb = conn.execute(text("""
                            SELECT fb.id, fb.organisation_id, fb.block_id, fb.block_name, fb.is_active, fb.created_at
                            FROM facility_blocks fb
                            JOIN organisations o ON fb.organisation_id = o.id
                            WHERE LOWER(o.org_type) LIKE '%municipality%'
                        """))
                        for row in res_fb.fetchall():
                            fb_id, m_org_id, b_id, b_name, is_act, cr_at = row
                            is_ward = (
                                b_id == "11"
                                or b_id.startswith("WRD-")
                                or b_id.isdigit()
                                or "sahi" in b_name.lower()
                                or "ward" in b_name.lower()
                            )
                            is_office = any(term in b_name.lower() for term in ["secretariat", "revenue", "public works", "engineering", "sanitation", "headquarters"]) or (b_id.startswith("BLK-") and not any(w in b_name.lower() for w in ["ward", "sahi"]))
                            if is_ward and not is_office:
                                exists = conn.execute(
                                    text("SELECT id FROM municipality_wards WHERE municipality_id = :org_id AND (ward_number = :w_num OR ward_name = :w_name)"),
                                    {"org_id": m_org_id, "w_num": b_id, "w_name": b_name}
                                ).fetchone()
                                if not exists:
                                    import uuid as _uuid
                                    conn.execute(
                                        text("""
                                            INSERT INTO municipality_wards (id, municipality_id, ward_number, ward_name, is_active, created_at, updated_at)
                                            VALUES (:id, :m_id, :w_num, :w_name, :is_act, :cr_at, :cr_at)
                                        """),
                                        {
                                            "id": str(_uuid.uuid4()),
                                            "m_id": m_org_id,
                                            "w_num": b_id,
                                            "w_name": b_name,
                                            "is_act": 1 if is_act is None else int(is_act),
                                            "cr_at": cr_at or datetime.now(timezone.utc).isoformat(),
                                        }
                                    )
                                conn.execute(text("DELETE FROM facility_blocks WHERE id = :fb_id"), {"fb_id": fb_id})
                        conn.commit()
                except Exception as mig_err:
                    logger.warning("Municipality ward data migration warning: %s", mig_err)

                # Idempotent migration: ensure municipalities expose the civic function
                # sensors (street lighting, roads, parks, sewage). This is config-only and
                # never deletes or rewrites existing readings/blocks/wards data.
                try:
                    _CIVIC_SENSORS = ["street_lighting", "roads", "parks", "sewage"]
                    _muni_rows = conn.execute(text("""
                        SELECT oc.organisation_id, oc.enabled_sensors
                        FROM organisation_sensor_configs oc
                        JOIN organisations o ON oc.organisation_id = o.id
                        WHERE LOWER(o.org_type) LIKE '%municipality%'
                    """)).fetchall()
                    for _c_org, _en_str in _muni_rows:
                        if not _en_str:
                            continue
                        _parts = [p.strip() for p in _en_str.split("|") if p.strip()]
                        _missing = [s for s in _CIVIC_SENSORS if s not in _parts]
                        if _missing:
                            conn.execute(
                                text("""
                                    UPDATE organisation_sensor_configs
                                    SET enabled_sensors = :enabled, updated_at = :upd
                                    WHERE organisation_id = :oid
                                """),
                                {
                                    "enabled": "|".join(_parts + _missing),
                                    "upd": datetime.now(timezone.utc).isoformat(),
                                    "oid": _c_org,
                                },
                            )
                    conn.commit()
                except Exception as mig_err:
                    logger.warning("Municipality civic sensor config migration warning: %s", mig_err)
        except Exception as e:
            logger.warning("Database column migration warning: %s", e)
    else:
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("ALTER TABLE organisations ADD COLUMN IF NOT EXISTS ownership_type VARCHAR(50)"))
                conn.execute(text("ALTER TABLE organisations ADD COLUMN IF NOT EXISTS dashboard_style VARCHAR(30)"))
                conn.commit()
        except Exception as e:
            logger.warning("Database column migration warning: %s", e)
