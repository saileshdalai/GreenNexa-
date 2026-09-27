"""
GreenNexa — Unit & Regression Tests for Final Root-Cause Fixes (Bugs 1-14).
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import (
    Organisation,
    OrganisationSensorConfig,
    FacilityBlock,
    SensorReading,
    AnomalyRecord,
    User,
)
from app.core.security import hash_password
from app.core.aggregation import (
    compute_metric_summary,
    is_block_wise_module,
    is_metric_additive,
)


@pytest.fixture
def multi_block_org_setup(db_session: Session):
    """Setup an organisation with 3 facility blocks and distinct readings."""
    now = datetime.now(timezone.utc)
    org_id = "ORG-MULTIBLK-01"

    # Clean existing if any
    db_session.query(SensorReading).filter(SensorReading.organisation_id == org_id).delete()
    db_session.query(FacilityBlock).filter(FacilityBlock.organisation_id == org_id).delete()
    db_session.query(OrganisationSensorConfig).filter(OrganisationSensorConfig.organisation_id == org_id).delete()
    db_session.query(User).filter(User.organisation_id == org_id).delete()
    db_session.query(Organisation).filter(Organisation.id == org_id).delete()
    db_session.commit()

    org = Organisation(
        id=org_id,
        name="Multi-Block Test Campus",
        org_type="Commercial",
        city="Bhubaneswar",
        state="Odisha",
        is_active=True,
    )
    db_session.add(org)

    b1 = FacilityBlock(block_id="block_a", organisation_id=org_id, block_name="Block A", is_active=True)
    b2 = FacilityBlock(block_id="block_b", organisation_id=org_id, block_name="Block B", is_active=True)
    b3 = FacilityBlock(block_id="block_c", organisation_id=org_id, block_name="Block C", is_active=True)
    db_session.add_all([b1, b2, b3])

    cfg = OrganisationSensorConfig(
        organisation_id=org_id,
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        enabled_sensors="energy|water|temperature|parking|air_quality",
        sensor_configs=json.dumps({
            "energy": {"baseline": 1500.0, "warning_threshold": 15.0, "critical_threshold": 30.0},
            "water": {"baseline": 600.0, "warning_threshold": 20.0, "critical_threshold": 40.0},
            "temperature": {"baseline": 24.0, "warning_threshold": 10.0, "critical_threshold": 20.0},
            "parking": {"baseline": 70.0, "warning_threshold": 15.0, "critical_threshold": 30.0},
            "air_quality": {"baseline": 50.0, "warning_threshold": 20.0, "critical_threshold": 40.0},
        }),
    )
    db_session.add(cfg)

    # Add historical and latest readings
    # Energy: Block A = 500, Block B = 800, Block C = 650. Total = 1950.
    t0 = now - timedelta(minutes=5)
    t1 = now
    readings = [
        # Older cycle (peak): Block A = 600, Block B = 900, Block C = 700. Total = 2200.
        SensorReading(organisation_id=org_id, block_id="block_a", sensor_type="energy", value=600.0, unit="kWh", timestamp=t0),
        SensorReading(organisation_id=org_id, block_id="block_b", sensor_type="energy", value=900.0, unit="kWh", timestamp=t0),
        SensorReading(organisation_id=org_id, block_id="block_c", sensor_type="energy", value=700.0, unit="kWh", timestamp=t0),
        # Latest cycle: Block A = 500, Block B = 800, Block C = 650. Total = 1950.
        SensorReading(organisation_id=org_id, block_id="block_a", sensor_type="energy", value=500.0, unit="kWh", timestamp=t1),
        SensorReading(organisation_id=org_id, block_id="block_b", sensor_type="energy", value=800.0, unit="kWh", timestamp=t1),
        SensorReading(organisation_id=org_id, block_id="block_c", sensor_type="energy", value=650.0, unit="kWh", timestamp=t1),
        # Temperature: Block A = 22, Block B = 26, Block C = 24. Mean = 24.0.
        SensorReading(organisation_id=org_id, block_id="block_a", sensor_type="temperature", value=22.0, unit="°C", timestamp=t1),
        SensorReading(organisation_id=org_id, block_id="block_b", sensor_type="temperature", value=26.0, unit="°C", timestamp=t1),
        SensorReading(organisation_id=org_id, block_id="block_c", sensor_type="temperature", value=24.0, unit="°C", timestamp=t1),
        # Parking (natural location module — should NOT map to facility blocks): 68.0%
        SensorReading(organisation_id=org_id, sensor_type="parking", value=68.0, unit="%", timestamp=t1),
        # Air Quality (whole-organisation default): 45.0 AQI
        SensorReading(organisation_id=org_id, sensor_type="air_quality", value=45.0, unit="AQI", timestamp=t1),
    ]
    db_session.add_all(readings)

    # Admin user
    admin = User(
        id="usr-multiblk-admin",
        email="multiblk-admin@example.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="MultiBlk Admin",
        role="ADMIN",
        organisation_id=org_id,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    return {"org_id": org_id, "admin": admin, "blocks": [b1, b2, b3]}


def test_bug1_energy_overall_is_sum_not_highest_block(db_session: Session, multi_block_org_setup):
    """Bug 1: Energy Overall must be SUM of blocks (1950), NOT highest block (800)."""
    org_id = multi_block_org_setup["org_id"]
    blocks = multi_block_org_setup["blocks"]

    summary = compute_metric_summary(
        db=db_session,
        organisation_id=org_id,
        sensor_type="energy",
        blocks=blocks,
    )

    # Current value must be 500 + 800 + 650 = 1950.0
    assert summary.current_value == 1950.0, f"Expected 1950.0, got {summary.current_value}"
    assert summary.current_value != 800.0, "Overall must NOT be highest block value!"

    # Historical Peak must be 600 + 900 + 700 = 2200.0
    assert summary.maximum == 2200.0, f"Expected peak 2200.0, got {summary.maximum}"
    assert summary.current_value <= summary.maximum, "Current value must be <= Peak Telemetry"


def test_bug1_temperature_overall_is_mean_not_highest_block(db_session: Session, multi_block_org_setup):
    """Bug 1: Temperature Overall must be representative MEAN (24.0), NOT highest block (26.0)."""
    org_id = multi_block_org_setup["org_id"]
    blocks = multi_block_org_setup["blocks"]

    summary = compute_metric_summary(
        db=db_session,
        organisation_id=org_id,
        sensor_type="temperature",
        blocks=blocks,
    )

    # Mean of (22, 26, 24) = 24.0
    assert summary.current_value == 24.0, f"Expected 24.0, got {summary.current_value}"
    assert summary.current_value != 26.0, "Overall temperature must NOT be highest block!"


def test_bug2_current_matches_graph_current_and_peak(client: TestClient, multi_block_org_setup, auth_headers):
    """Bug 2: Module page overall API returns consistent current_value and peak."""
    org_id = multi_block_org_setup["org_id"]

    # Login as admin to get token
    login_resp = client.post("/api/v1/auth/login", json={"email": "multiblk-admin@example.com", "password": "AdminPass123!"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Query module intelligence for energy
    resp = client.get(f"/api/v1/dashboard/{org_id}/modules/energy/overall?period=24h", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Current value must be 1950.0
    assert data["current_value"] == 1950.0
    # Peak must be 2200.0
    assert data["peak"] == 2200.0
    # Current <= Peak
    assert data["current_value"] <= data["peak"]

    # Block comparison must contain all 3 blocks with their individual latest readings
    assert len(data["block_comparison"]) == 3
    b_vals = {b["block_id"]: b["current_value"] for b in data["block_comparison"]}
    assert b_vals["block_a"] == 500.0
    assert b_vals["block_b"] == 800.0
    assert b_vals["block_c"] == 650.0


def test_bug3_natural_location_modules_do_not_use_facility_blocks(client: TestClient, multi_block_org_setup):
    """Bug 3 & Bug 12: Parking and Air Quality must NOT display facility blocks."""
    org_id = multi_block_org_setup["org_id"]

    login_resp = client.post("/api/v1/auth/login", json={"email": "multiblk-admin@example.com", "password": "AdminPass123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Parking
    resp_parking = client.get(f"/api/v1/dashboard/{org_id}/modules/parking/overall?period=24h", headers=headers)
    assert resp_parking.status_code == 200
    data_parking = resp_parking.json()
    assert data_parking["block_comparison"] == [], "Parking must NOT display Facility Blocks!"

    # Air Quality
    resp_aq = client.get(f"/api/v1/dashboard/{org_id}/modules/air_quality/overall?period=24h", headers=headers)
    assert resp_aq.status_code == 200
    data_aq = resp_aq.json()
    assert data_aq["block_comparison"] == [], "Air Quality must NOT display Facility Blocks!"


def test_bug4_and_bug5_dashboard_returns_blocks_and_kpis(client: TestClient, multi_block_org_setup):
    """Bug 4 & 5: Dashboard returns blocks/wards and centralized KPIs."""
    org_id = multi_block_org_setup["org_id"]

    login_resp = client.post("/api/v1/auth/login", json={"email": "multiblk-admin@example.com", "password": "AdminPass123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(f"/api/v1/dashboard/{org_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Blocks list present for administrative ward/block operations
    assert "blocks" in data
    assert len(data["blocks"]) == 3

    # Energy KPI must match centralized aggregate (1950.0)
    assert data["kpis"]["energy"]["latest_value"] == 1950.0
    # Temperature KPI must match centralized mean (24.0)
    assert data["kpis"]["temperature"]["latest_value"] == 24.0
