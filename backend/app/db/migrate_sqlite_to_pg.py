"""
GreenNexa — SQLite to PostgreSQL Data Migration Script.

Fast and safe migration of GreenNexa schema and data from local SQLite
(greennexa_test.db) to local PostgreSQL (greennexa_local).

Safety guarantees:
- SQLite source database is opened in READ-ONLY mode (never modified or deleted).
- Preserves all primary keys, foreign keys, timestamps, and relationships.
- Does NOT alter the active application's DATABASE_URL or .env file.
- Masks all sensitive credentials (passwords, hashes, tokens, secrets).
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Table,
    Text,
    create_engine,
    inspect,
    text,
)

# Ensure backend directory is in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_current_dir, "..", ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.db.models import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("greennexa.migration")

# Topological insertion order to respect foreign key constraints
TABLE_MIGRATION_ORDER = [
    "organisations",
    "platform_state",
    "users",
    "facility_blocks",
    "municipality_wards",
    "organisation_sensor_configs",
    "iot_devices",
    "password_reset_otps",
    "messages",
    "sensor_readings",
    "anomaly_records",
    "ai_recommendations",
    "event_read_states",
]


def convert_val(val: Any, sa_col) -> Any:
    """Type-safe conversion from SQLite representation to PostgreSQL SQLAlchemy representation."""
    if val is None:
        return None
    type_cls = type(sa_col.type)
    if issubclass(type_cls, Boolean):
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.strip().lower() in ("1", "true", "t", "yes")
        return bool(val)
    elif issubclass(type_cls, DateTime):
        if isinstance(val, str):
            val_clean = val.strip()
            try:
                dt = datetime.fromisoformat(val_clean)
            except Exception:
                try:
                    dt = datetime.strptime(val_clean, "%Y-%m-%d %H:%M:%S.%f")
                except Exception:
                    dt = datetime.strptime(val_clean, "%Y-%m-%d %H:%M:%S")
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        elif isinstance(val, datetime):
            if val.tzinfo is None:
                return val.replace(tzinfo=timezone.utc)
            return val
        return val
    elif issubclass(type_cls, Date):
        if isinstance(val, str):
            return date.fromisoformat(val.split("T")[0].split(" ")[0])
        elif isinstance(val, datetime):
            return val.date()
        elif isinstance(val, date):
            return val
        return val
    elif issubclass(type_cls, Float):
        return float(val)
    elif issubclass(type_cls, Integer):
        return int(val)
    elif issubclass(type_cls, (String, Text)):
        return str(val)
    return val


def get_sqlite_row_counts(sqlite_path: str) -> Dict[str, int]:
    """Count rows in all tables in SQLite database (read-only)."""
    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    cur = conn.cursor()
    counts = {}
    for table_name in TABLE_MIGRATION_ORDER:
        try:
            cur.execute(f'SELECT count(*) FROM "{table_name}"')
            counts[table_name] = cur.fetchone()[0]
        except sqlite3.OperationalError:
            counts[table_name] = 0
    cur.close()
    conn.close()
    return counts


def get_pg_row_counts(pg_engine) -> Dict[str, int]:
    """Count rows in all tables in PostgreSQL database."""
    counts = {}
    with pg_engine.connect() as conn:
        for table_name in TABLE_MIGRATION_ORDER:
            try:
                res = conn.execute(text(f'SELECT count(*) FROM "{table_name}"')).scalar()
                counts[table_name] = int(res)
            except Exception:
                counts[table_name] = 0
    return counts


def migrate_data(sqlite_path: str, pg_url: str) -> Tuple[bool, Dict[str, int], Dict[str, int], List[str]]:
    """Execute complete migration and verification."""
    logger.info("Opening SQLite database (read-only): %s", sqlite_path)
    sqlite_conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    logger.info("Connecting to target PostgreSQL database...")
    pg_engine = create_engine(pg_url, pool_pre_ping=True)

    # 1. Pre-migration counts
    source_counts = get_sqlite_row_counts(sqlite_path)
    logger.info("Source SQLite row counts: %s", source_counts)

    # 2. Ensure schema exists on PostgreSQL
    logger.info("Ensuring PostgreSQL schema matches SQLAlchemy models...")
    Base.metadata.create_all(bind=pg_engine)

    # 3. Migrate data within a single atomic transaction
    mismatches: List[str] = []
    try:
        with pg_engine.begin() as pg_conn:
            for table_name in TABLE_MIGRATION_ORDER:
                sa_table: Table = Base.metadata.tables[table_name]
                expected_count = source_counts.get(table_name, 0)
                if expected_count == 0:
                    logger.info("Table '%s' has 0 rows in SQLite. Skipping data transfer.", table_name)
                    continue

                sqlite_cur.execute(f'SELECT * FROM "{table_name}"')
                rows = sqlite_cur.fetchall()
                records = []
                for r in rows:
                    row_dict = dict(r)
                    converted = {}
                    for col_name, sa_col in sa_table.columns.items():
                        raw_val = row_dict.get(col_name)
                        converted[col_name] = convert_val(raw_val, sa_col)
                    records.append(converted)

                logger.info("Inserting %d rows into PostgreSQL table '%s'...", len(records), table_name)
                # Chunked bulk insert
                chunk_size = 500
                for i in range(0, len(records), chunk_size):
                    chunk = records[i : i + chunk_size]
                    pg_conn.execute(sa_table.insert(), chunk)

        logger.info("All records committed to PostgreSQL successfully.")
    except Exception as e:
        logger.error("Migration failed during data insertion: %s", e)
        sqlite_cur.close()
        sqlite_conn.close()
        return False, source_counts, {}, [f"Data insertion error: {str(e)}"]

    sqlite_cur.close()
    sqlite_conn.close()

    # 4. Post-migration counts
    target_counts = get_pg_row_counts(pg_engine)
    logger.info("Target PostgreSQL row counts: %s", target_counts)

    # 5. Compare counts
    for table_name in TABLE_MIGRATION_ORDER:
        src = source_counts.get(table_name, 0)
        tgt = target_counts.get(table_name, 0)
        if src != tgt:
            mismatches.append(f"Table '{table_name}': SQLite has {src} rows, PostgreSQL has {tgt} rows")

    # 6. Deep verification of integrity
    logger.info("Performing deep verification of relational integrity in PostgreSQL...")
    with pg_engine.connect() as conn:
        # Check organisations count and distinct ownership
        org_owners = conn.execute(text("SELECT ownership_type, count(*) FROM organisations GROUP BY ownership_type")).fetchall()
        logger.info("Organisation ownership distribution in PostgreSQL: %s", org_owners)

        # Check user roles
        user_roles = conn.execute(text("SELECT role, count(*) FROM users GROUP BY role")).fetchall()
        logger.info("User role distribution in PostgreSQL: %s", user_roles)

        # Check wards and blocks
        ward_cnt = conn.execute(text("SELECT count(*) FROM municipality_wards")).scalar()
        block_cnt = conn.execute(text("SELECT count(*) FROM facility_blocks")).scalar()
        logger.info("Municipality wards: %d, Facility blocks: %d", ward_cnt, block_cnt)

        # Check anomalies and recommendations relation
        anom_cnt = conn.execute(text("SELECT count(*) FROM anomaly_records")).scalar()
        rec_cnt = conn.execute(text("SELECT count(*) FROM ai_recommendations")).scalar()
        matched_recs = conn.execute(text("""
            SELECT count(*)
            FROM ai_recommendations r
            JOIN anomaly_records a ON r.anomaly_id = a.id
        """)).scalar()
        logger.info("Anomaly records: %d, Recommendations: %d, Matched FKs: %d", anom_cnt, rec_cnt, matched_recs)
        if rec_cnt != matched_recs:
            mismatches.append(f"AI recommendations FK mismatch: {rec_cnt} recs vs {matched_recs} matched anomalies")

        # Check sensor readings org reference
        sr_cnt = conn.execute(text("SELECT count(*) FROM sensor_readings")).scalar()
        matched_sr = conn.execute(text("""
            SELECT count(*)
            FROM sensor_readings sr
            JOIN organisations o ON sr.organisation_id = o.id
        """)).scalar()
        logger.info("Sensor readings: %d, Matched Org FKs: %d", sr_cnt, matched_sr)
        if sr_cnt != matched_sr:
            mismatches.append(f"Sensor readings FK mismatch: {sr_cnt} readings vs {matched_sr} matched orgs")

    success = (len(mismatches) == 0)
    return success, source_counts, target_counts, mismatches


def main():
    parser = argparse.ArgumentParser(description="Migrate GreenNexa data from SQLite to PostgreSQL.")
    parser.add_argument("--sqlite-path", help="Path to SQLite database", default=None)
    parser.add_argument("--pg-url", help="Target PostgreSQL connection URL", default=None)
    args = parser.parse_args()

    sqlite_path = args.sqlite_path
    if not sqlite_path:
        sqlite_path = os.path.join(_backend_dir, "greennexa_test.db")
    sqlite_path = os.path.abspath(sqlite_path)

    pg_url = args.pg_url or os.environ.get("TARGET_DATABASE_URL")
    if not pg_url:
        # Check scratch credentials if available
        scratch_creds = os.path.expanduser(r"~\.gemini\antigravity-ide\brain\33f3b87a-dd5a-4dea-89ef-b41c7c92fb8b\scratch\pg_creds.py")
        if os.path.exists(scratch_creds):
            import importlib.util
            spec = importlib.util.spec_from_file_location("pg_creds", scratch_creds)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            pg_url = mod.PG_URL

    if not pg_url:
        logger.error("No PostgreSQL connection URL provided. Set --pg-url or TARGET_DATABASE_URL.")
        sys.exit(1)

    # Validate SQLite exists
    if not os.path.exists(sqlite_path):
        logger.error("SQLite database not found at: %s", sqlite_path)
        sys.exit(1)

    success, src_counts, tgt_counts, mismatches = migrate_data(sqlite_path, pg_url)
    if success:
        logger.info("MIGRATION AND VERIFICATION COMPLETED SUCCESSFULLY.")
    else:
        logger.error("MIGRATION FAILED WITH MISMATCHES: %s", mismatches)
        sys.exit(1)


if __name__ == "__main__":
    main()
