"""
GreenNexa — Facility Block & Block-Wise Module Drill-Down Tests

Tests:
1. Super Admin create organisation with facility blocks & validation (duplicate/empty names).
2. Organisation Block CRUD APIs (list, create, update, delete).
3. Synthetic Simulator block-wise telemetry generation:
   - Monotonic cumulative values (Energy/Water) per block.
   - Live metric fluctuations.
   - Waste 100% capacity anomaly creation & auto-resolution on decrease.
4. Module Drill-down APIs:
   - Overall View (/dashboard/{org_id}/modules/{module_id}/overall).
   - Block View (/dashboard/{org_id}/modules/{module_id}/block/{block_id}).
5. Multi-tenant isolation for blocks and module drill-down endpoints.
"""

import pytest
from app.db.models import FacilityBlock, Organisation, SensorReading, AnomalyRecord, AIRecommendation
from app.services.anomaly_detection import anomaly_detection_service
from app.services.synthetic_simulator import SyntheticDataSimulator


def test_create_org_with_facility_blocks(client, auth_headers):
    sa_headers = auth_headers("superadmin@greennexa.com", "SUPER_ADMIN", organisation_id="SYSTEM")

    payload = {
        "name": "Block Test University",
        "facility_type": "college_university",
        "facility_name": "Main Campus",
        "state": "State",
        "district": "District",
        "city": "City",
        "address": "123 Campus Way",
        "admin_name": "Block Admin",
        "admin_email": "blockadmin@university.edu",
        "admin_password": "Password123!",
        "enabled_modules": ["energy", "waste", "water"],
        "blocks": [
            {"block_name": "Main Academic Block"},
            {"block_name": "Science Block"},
            {"block_name": "Hostel Block A"},
        ],
    }

    res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res.status_code == 201
    data = res.json()
    org_id = data["organisation_id"]

    # Verify blocks created
    res_blocks = client.get(f"/api/v1/organisations/{org_id}/blocks", headers=sa_headers)
    assert res_blocks.status_code == 200
    blocks_data = res_blocks.json()["items"]  # list of blocks in items
    assert len(blocks_data) == 3
    block_names = [b["block_name"] for b in blocks_data]
    assert "Main Academic Block" in block_names
    assert "Science Block" in block_names
    assert "Hostel Block A" in block_names


def test_create_org_duplicate_block_name_validation(client, auth_headers):
    sa_headers = auth_headers("superadmin@greennexa.com", "SUPER_ADMIN", organisation_id="SYSTEM")

    payload = {
        "name": "Dup Block Org",
        "facility_type": "college_university",
        "facility_name": "Dup Campus",
        "state": "State",
        "district": "District",
        "city": "City",
        "address": "123 Dup Way",
        "admin_name": "Dup Admin",
        "admin_email": "dupadmin@corp.com",
        "admin_password": "Password123!",
        "enabled_modules": ["energy"],
        "blocks": [
            {"block_name": "Tower A"},
            {"block_name": "tower a"},  # Case insensitive duplicate
        ],
    }

    res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res.status_code == 400
    assert "Duplicate block name" in res.json()["detail"]


def test_create_org_empty_block_name_validation(client, auth_headers):
    sa_headers = auth_headers("superadmin@greennexa.com", "SUPER_ADMIN", organisation_id="SYSTEM")

    payload = {
        "name": "Empty Block Org",
        "facility_type": "college_university",
        "facility_name": "Empty Campus",
        "state": "State",
        "district": "District",
        "city": "City",
        "address": "123 Empty Way",
        "admin_name": "Empty Admin",
        "admin_email": "emptyadmin@corp.com",
        "admin_password": "Password123!",
        "enabled_modules": ["energy"],
        "blocks": [
            {"block_name": "   "},
        ],
    }

    res = client.post("/api/v1/super-admin/organisations/create-full", json=payload, headers=sa_headers)
    assert res.status_code == 422
    assert "Block name cannot be empty" in str(res.json()["detail"])


def test_block_crud_apis(client, auth_headers, seed_orgs):
    org_id = seed_orgs["org_a"].id
    admin_headers = auth_headers("admin_a@test.com", "ADMIN", organisation_id=org_id)

    # 1. Create Block
    res_create = client.post(
        f"/api/v1/organisations/{org_id}/blocks",
        json={"block_name": "Engineering Block"},
        headers=admin_headers,
    )
    assert res_create.status_code == 201
    created_block = res_create.json()
    assert created_block["block_name"] == "Engineering Block"
    block_id = created_block["block_id"]

    # 2. List Blocks
    res_list = client.get(f"/api/v1/organisations/{org_id}/blocks", headers=admin_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()["items"]) >= 1

    # 3. Update Block Name
    res_update = client.put(
        f"/api/v1/organisations/{org_id}/blocks/{block_id}",
        json={"block_name": "School of Engineering"},
        headers=admin_headers,
    )
    assert res_update.status_code == 200
    assert res_update.json()["block_name"] == "School of Engineering"

    # 4. Duplicate name update check
    res_create2 = client.post(
        f"/api/v1/organisations/{org_id}/blocks",
        json={"block_name": "Medical Wing"},
        headers=admin_headers,
    )
    assert res_create2.status_code == 201

    res_dup_update = client.put(
        f"/api/v1/organisations/{org_id}/blocks/{block_id}",
        json={"block_name": "Medical Wing"},
        headers=admin_headers,
    )
    assert res_dup_update.status_code == 400
    assert "already exists" in res_dup_update.json()["detail"]

    # 5. Soft Delete Block
    res_delete = client.delete(
        f"/api/v1/organisations/{org_id}/blocks/{block_id}",
        headers=admin_headers,
    )
    assert res_delete.status_code == 200

    # Verify block marked inactive
    res_list2 = client.get(f"/api/v1/organisations/{org_id}/blocks", headers=admin_headers)
    active_ids = [b["block_id"] for b in res_list2.json()["items"]]
    assert block_id not in active_ids


def test_synthetic_simulator_block_readings_and_cumulative(db_session, seed_orgs):
    org_id = seed_orgs["org_a"].id
    # Create 2 blocks
    b1 = FacilityBlock(organisation_id=org_id, block_id="block_a", block_name="Block A")
    b2 = FacilityBlock(organisation_id=org_id, block_id="block_b", block_name="Block B")
    db_session.add_all([b1, b2])
    db_session.commit()

    simulator = SyntheticDataSimulator()
    # Turn demo mode on
    seed_orgs["org_a"].is_demo_mode = True
    db_session.commit()

    # Cycle 1
    simulator.run_cycle(db_session)

    # Fetch readings for cycle 1
    readings_c1 = db_session.query(SensorReading).filter(SensorReading.organisation_id == org_id).all()
    assert len(readings_c1) > 0
    blocks_in_c1 = {r.block_id for r in readings_c1 if r.block_id}
    assert "block_a" in blocks_in_c1
    assert "block_b" in blocks_in_c1

    # Extract cumulative energy values for block_a
    c1_energy = next((r.value for r in readings_c1 if r.block_id == "block_a" and r.sensor_type == "energy"), None)
    assert c1_energy is not None

    # Cycle 2
    simulator.run_cycle(db_session)
    readings_c2 = db_session.query(SensorReading).filter(SensorReading.organisation_id == org_id).all()
    c2_energy = next((r.value for r in sorted(readings_c2, key=lambda x: x.timestamp, reverse=True) if r.block_id == "block_a" and r.sensor_type == "energy"), None)
    assert c2_energy is not None

    # Cumulative energy MUST strictly increase (c2_energy >= c1_energy)
    assert c2_energy >= c1_energy


def test_waste_capacity_anomaly_does_not_auto_resolve(db_session, seed_orgs):
    """FINAL SPEC: a normal reading must NEVER silently resolve an open anomaly.

    Anomalies persist and stay active until a user explicitly RESOLVES or DISMISSES
    them. The previous auto-resolution logic resolved the open waste anomaly on the
    next sub-100% reading without any user action, which erased history and
    un-actioned recommendations.
    """
    org_id = seed_orgs["org_a"].id
    seed_orgs["org_a"].is_demo_mode = True

    # Ensure waste module is enabled in sensor config
    from app.db.models import OrganisationSensorConfig
    config = db_session.query(OrganisationSensorConfig).filter_by(organisation_id=org_id).first()
    if not config:
        config = OrganisationSensorConfig(organisation_id=org_id, data_source="synthetic", is_active=True)
        db_session.add(config)
    config.set_enabled_sensors(["energy", "water", "waste"])
    db_session.commit()

    b1 = FacilityBlock(organisation_id=org_id, block_id="hostel_block", block_name="Hostel Block")
    db_session.add(b1)
    db_session.commit()

    simulator = SyntheticDataSimulator()

    # Create reading, anomaly, and recommendation
    reading = SensorReading(
        organisation_id=org_id,
        block_id="hostel_block",
        sensor_type="waste",
        value=100.0,
        unit="%",
        source="synthetic",
    )
    anom = AnomalyRecord(
        organisation_id=org_id,
        block_id="hostel_block",
        metric="waste",
        sensor_type="waste",
        value=100.0,
        severity="CRITICAL",
        reason="Critical Waste Capacity Alert: Hostel Block has reached 100% capacity.",
        status="OPEN",
    )
    rec = AIRecommendation(
        organisation_id=org_id,
        block_id="hostel_block",
        metric="waste",
        current_value=100.0,
        severity="CRITICAL",
        summary="Hostel Block waste container is at 100% capacity.",
        status="PENDING",
        anomaly=anom,
    )
    db_session.add_all([reading, anom, rec])
    db_session.commit()

    # Verify active anomaly exists
    open_anom = db_session.query(AnomalyRecord).filter(
        AnomalyRecord.organisation_id == org_id,
        AnomalyRecord.block_id == "hostel_block",
        AnomalyRecord.metric == "waste",
        AnomalyRecord.status == "OPEN",
    ).first()
    assert open_anom is not None

    # Now simulate another cycle where waste fill level < 100%
    # Force anomaly on energy so waste stays in normal 20-85% range
    simulator.run_cycle(db_session, forced_anomaly_sensor="energy")

    # The waste anomaly must STILL be OPEN: a normal reading is not a resolution.
    db_session.refresh(open_anom)
    assert open_anom.status == AnomalyRecord.STATUS_OPEN, (
        "anomalies must remain active until an explicit RESOLVE/DISMISS"
    )
    assert open_anom.resolved_at is None

    # Only an explicit lifecycle action resolves it (and syncs the recommendation).
    anomaly_detection_service.update_anomaly_status(
        db_session, open_anom.id, AnomalyRecord.STATUS_RESOLVED
    )
    db_session.refresh(open_anom)
    db_session.refresh(rec)
    assert open_anom.status == AnomalyRecord.STATUS_RESOLVED
    assert open_anom.resolved_at is not None
    assert rec.status == AIRecommendation.STATUS_RESOLVED


def test_module_overall_and_block_detail_apis(client, auth_headers, db_session, seed_orgs):
    org_id = seed_orgs["org_a"].id
    seed_orgs["org_a"].is_demo_mode = True
    b1 = FacilityBlock(organisation_id=org_id, block_id="b_acad", block_name="Academic Block")
    b2 = FacilityBlock(organisation_id=org_id, block_id="b_sci", block_name="Science Block")
    db_session.add_all([b1, b2])
    db_session.commit()

    # Generate some simulation data (3 cycles for history)
    simulator = SyntheticDataSimulator()
    simulator.run_cycle(db_session)
    simulator.run_cycle(db_session)
    simulator.run_cycle(db_session)

    admin_headers = auth_headers("admin_a@test.com", "ADMIN", organisation_id=org_id)

    # 1. Overall View API
    res_overall = client.get(f"/api/v1/dashboard/{org_id}/modules/energy/overall", headers=admin_headers)
    assert res_overall.status_code == 200
    ov_data = res_overall.json()
    assert ov_data["module_id"] == "energy"
    assert "current_value" in ov_data
    assert "average" in ov_data
    assert "peak" in ov_data
    assert len(ov_data["trend_points"]) > 0
    assert len(ov_data["block_comparison"]) >= 2
    assert len(ov_data["prediction_table"]) >= 3  # Overall + 2 blocks

    # Verify prediction table contains Overall and block rows
    pred_block_ids = [p["block_id"] for p in ov_data["prediction_table"]]
    assert None in pred_block_ids  # Overall row has block_id = None
    assert "b_acad" in pred_block_ids
    assert "b_sci" in pred_block_ids

    # 2. Block Detail API
    res_block = client.get(f"/api/v1/dashboard/{org_id}/modules/energy/block/b_acad", headers=admin_headers)
    assert res_block.status_code == 200
    b_data = res_block.json()
    assert b_data["block_id"] == "b_acad"
    assert b_data["block_name"] == "Academic Block"
    assert "current_value" in b_data
    assert "average" in b_data
    assert b_data["prediction"]["block_id"] == "b_acad"


def test_multi_tenant_block_access_isolation(client, auth_headers, seed_orgs):
    org_a_id = seed_orgs["org_a"].id
    org_b_id = seed_orgs["org_b"].id

    admin_a_headers = auth_headers("admin_a@test.com", "ADMIN", organisation_id=org_a_id)

    # Admin A attempts to access Org B's block endpoints -> 403 Forbidden
    res_get = client.get(f"/api/v1/organisations/{org_b_id}/blocks", headers=admin_a_headers)
    assert res_get.status_code == 403

    res_post = client.post(
        f"/api/v1/organisations/{org_b_id}/blocks",
        json={"block_name": "Hacker Block"},
        headers=admin_a_headers,
    )
    assert res_post.status_code == 403

    res_module = client.get(f"/api/v1/dashboard/{org_b_id}/modules/energy/overall", headers=admin_a_headers)
    assert res_module.status_code == 403
