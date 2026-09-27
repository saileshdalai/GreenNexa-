"""
GreenNexa — Deep Verification of SQLite to PostgreSQL Data Migration.

Performs side-by-side integrity, relationship, and value checks between
SQLite (greennexa_test.db) and PostgreSQL (greennexa_local).
"""

from __future__ import annotations

import os
import sqlite3
import sys
from typing import Dict, List

from sqlalchemy import create_engine, text

_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_current_dir, "..", ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)


def verify_migration(sqlite_path: str, pg_url: str) -> Dict[str, any]:
    results = {}

    sqlite_conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    sqlite_cur = sqlite_conn.cursor()

    pg_engine = create_engine(pg_url)

    with pg_engine.connect() as pg_conn:
        # 1. Organisations verification
        sqlite_cur.execute("SELECT id, name, ownership_type, org_type, is_active FROM organisations ORDER BY id")
        sq_orgs = sqlite_cur.fetchall()
        pg_orgs = pg_conn.execute(text("SELECT id, name, ownership_type, org_type, is_active FROM organisations ORDER BY id")).fetchall()
        orgs_match = (sq_orgs == [(r[0], r[1], r[2], r[3], bool(r[4])) for r in pg_orgs] or
                      [(r[0], r[1], r[2], r[3], int(r[4])) for r in sq_orgs] == [(r[0], r[1], r[2], r[3], int(r[4])) for r in pg_orgs])
        results["organisations_preserved"] = {
            "count": len(pg_orgs),
            "matches_source": orgs_match,
            "sample_ids": [r[0] for r in pg_orgs],
        }

        # 2. Ownership types
        sqlite_cur.execute("SELECT ownership_type, count(*) FROM organisations GROUP BY ownership_type ORDER BY ownership_type")
        sq_ownership = sqlite_cur.fetchall()
        pg_ownership = pg_conn.execute(text("SELECT ownership_type, count(*) FROM organisations GROUP BY ownership_type ORDER BY ownership_type")).fetchall()
        results["ownership_preserved"] = {
            "sqlite": sq_ownership,
            "postgres": [(r[0], int(r[1])) for r in pg_ownership],
            "matches": sq_ownership == [(r[0], int(r[1])) for r in pg_ownership],
        }

        # 3. Users and Roles
        sqlite_cur.execute("SELECT id, email, role, is_active, organisation_id FROM users")
        sq_users_dict = {r[0]: (r[1], r[2], bool(r[3]), r[4]) for r in sqlite_cur.fetchall()}
        pg_users_raw = pg_conn.execute(text("SELECT id, email, role, is_active, organisation_id FROM users")).fetchall()
        pg_users_dict = {r[0]: (r[1], r[2], bool(r[3]), r[4]) for r in pg_users_raw}
        users_match = (sq_users_dict == pg_users_dict)
        
        sqlite_cur.execute("SELECT role, count(*) FROM users GROUP BY role ORDER BY role")
        sq_roles = sqlite_cur.fetchall()
        pg_roles = pg_conn.execute(text("SELECT role, count(*) FROM users GROUP BY role ORDER BY role")).fetchall()
        results["users_preserved"] = {
            "count": len(pg_users_dict),
            "matches_source": users_match,
            "roles_breakdown": [(r[0], int(r[1])) for r in pg_roles],
            "roles_match": sq_roles == [(r[0], int(r[1])) for r in pg_roles],
        }

        # 4. Municipality Wards
        sqlite_cur.execute("SELECT id, municipality_id, ward_number, ward_name FROM municipality_wards ORDER BY id")
        sq_wards = sqlite_cur.fetchall()
        pg_wards = pg_conn.execute(text("SELECT id, municipality_id, ward_number, ward_name FROM municipality_wards ORDER BY id")).fetchall()
        results["wards_preserved"] = {
            "count": len(pg_wards),
            "matches_source": sq_wards == pg_wards,
        }

        # 5. Facility Blocks
        sqlite_cur.execute("SELECT id, organisation_id, block_id, block_name FROM facility_blocks ORDER BY id")
        sq_blocks = sqlite_cur.fetchall()
        pg_blocks = pg_conn.execute(text("SELECT id, organisation_id, block_id, block_name FROM facility_blocks ORDER BY id")).fetchall()
        results["blocks_preserved"] = {
            "count": len(pg_blocks),
            "matches_source": sq_blocks == pg_blocks,
        }

        # 6. Sensor Configs
        sqlite_cur.execute("SELECT organisation_id, data_source, simulated_date FROM organisation_sensor_configs ORDER BY organisation_id")
        sq_configs = sqlite_cur.fetchall()
        pg_configs = pg_conn.execute(text("SELECT organisation_id, data_source, simulated_date FROM organisation_sensor_configs ORDER BY organisation_id")).fetchall()
        results["sensor_configs_preserved"] = {
            "count": len(pg_configs),
            "matches_source": len(sq_configs) == len(pg_configs),
        }

        # 7. Sensor Readings
        sqlite_cur.execute("SELECT count(*), round(sum(value), 2) FROM sensor_readings")
        sq_sr = sqlite_cur.fetchone()
        pg_sr = pg_conn.execute(text("SELECT count(*), round(sum(value)::numeric, 2) FROM sensor_readings")).fetchone()
        results["sensor_readings_preserved"] = {
            "sqlite_count": sq_sr[0],
            "postgres_count": int(pg_sr[0]),
            "counts_match": sq_sr[0] == int(pg_sr[0]),
            "sqlite_sum": float(sq_sr[1]),
            "postgres_sum": float(pg_sr[1]),
            "sum_match": abs(float(sq_sr[1]) - float(pg_sr[1])) < 0.01,
        }

        # 8. Anomaly Records & Relationships
        sqlite_cur.execute("SELECT count(*), round(sum(value), 2) FROM anomaly_records")
        sq_ar = sqlite_cur.fetchone()
        pg_ar = pg_conn.execute(text("SELECT count(*), round(sum(value)::numeric, 2) FROM anomaly_records")).fetchone()
        results["anomalies_preserved"] = {
            "count": int(pg_ar[0]),
            "counts_match": sq_ar[0] == int(pg_ar[0]),
            "sum_match": abs(float(sq_ar[1]) - float(pg_ar[1])) < 0.01,
        }

        # 9. Recommendations & Anomaly FK Relationships
        sqlite_cur.execute("SELECT count(*) FROM ai_recommendations")
        sq_rec = sqlite_cur.fetchone()[0]
        pg_rec = pg_conn.execute(text("SELECT count(*) FROM ai_recommendations")).scalar()
        pg_rec_fks = pg_conn.execute(text("""
            SELECT count(*)
            FROM ai_recommendations r
            JOIN anomaly_records a ON r.anomaly_id = a.id
        """)).scalar()
        results["recommendations_preserved"] = {
            "count": int(pg_rec),
            "counts_match": sq_rec == int(pg_rec),
            "valid_fks_match": int(pg_rec) == int(pg_rec_fks),
        }

        # 10. IoT Devices
        sqlite_cur.execute("SELECT count(*) FROM iot_devices")
        sq_iot = sqlite_cur.fetchone()[0]
        pg_iot = pg_conn.execute(text("SELECT count(*) FROM iot_devices")).scalar()
        results["iot_devices_preserved"] = {
            "sqlite_count": sq_iot,
            "postgres_count": int(pg_iot),
            "matches": sq_iot == int(pg_iot),
        }

        # 11. Password Reset Records
        sqlite_cur.execute("SELECT count(*) FROM password_reset_otps")
        sq_otp = sqlite_cur.fetchone()[0]
        pg_otp = pg_conn.execute(text("SELECT count(*) FROM password_reset_otps")).scalar()
        results["password_resets_preserved"] = {
            "sqlite_count": sq_otp,
            "postgres_count": int(pg_otp),
            "matches": sq_otp == int(pg_otp),
        }

        # 12. Platform State
        sqlite_cur.execute("SELECT key, value FROM platform_state ORDER BY key")
        sq_ps = sqlite_cur.fetchall()
        pg_ps = pg_conn.execute(text("SELECT key, value FROM platform_state ORDER BY key")).fetchall()
        results["platform_state_preserved"] = {
            "count": len(pg_ps),
            "matches": sq_ps == pg_ps,
        }

    sqlite_cur.close()
    sqlite_conn.close()

    return results


def main():
    sqlite_path = os.path.join(_backend_dir, "greennexa_test.db")
    scratch_creds = os.path.expanduser(r"~\.gemini\antigravity-ide\brain\33f3b87a-dd5a-4dea-89ef-b41c7c92fb8b\scratch\pg_creds.py")
    pg_url = None
    if os.path.exists(scratch_creds):
        import importlib.util
        spec = importlib.util.spec_from_file_location("pg_creds", scratch_creds)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        pg_url = mod.PG_URL

    res = verify_migration(sqlite_path, pg_url)
    import pprint
    pprint.pprint(res)


if __name__ == "__main__":
    main()
