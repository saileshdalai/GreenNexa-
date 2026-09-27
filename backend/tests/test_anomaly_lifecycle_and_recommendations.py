"""
GreenNexa — Anomaly Lifecycle, Health Score, Recommendation Context,
and Organisation Deactivation Enforcement Tests.

Covers all 28 targeted test requirements:
  - Anomaly status transitions: RESOLVED and DISMISSED (tests 1-8)
  - Active anomaly filtering and live Health Score recalculation (tests 9-12)
  - Recommendation context, exact block names, and module-specific advice (tests 13-18)
  - Organisation deactivation login blocking, error messaging, existing token invalidation,
    super admin bypass, and reactivation (tests 19-24)
  - Security, multi-tenant isolation, and RBAC authorization (tests 25-28)
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    Organisation,
    OrganisationSensorConfig,
    User,
)
from app.services.anomaly_detection import anomaly_service
from app.services.recommendation import recommendation_service


def _utcnow():
    return datetime.now(timezone.utc)


@pytest.fixture
def test_setup(db_session: Session, seed_orgs):
    """Seed test facility blocks and baseline sensor configurations."""
    org_a = seed_orgs["org_a"]
    org_b = seed_orgs["org_b"]

    block_a1 = FacilityBlock(
        organisation_id=org_a.id,
        block_id="block-science",
        block_name="Science Block",
        is_active=True,
    )
    block_a2 = FacilityBlock(
        organisation_id=org_a.id,
        block_id="block-eng",
        block_name="Engineering Tower B",
        is_active=True,
    )
    block_b1 = FacilityBlock(
        organisation_id=org_b.id,
        block_id="block-hospital",
        block_name="Main Wing",
        is_active=True,
    )
    db_session.add_all([block_a1, block_a2, block_b1])

    cfg_a = OrganisationSensorConfig(
        organisation_id=org_a.id,
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        enabled_sensors="energy|water|waste|temperature|humidity|co2",
        is_active=True,
    )
    cfg_b = OrganisationSensorConfig(
        organisation_id=org_b.id,
        data_source=OrganisationSensorConfig.DATA_SOURCE_SYNTHETIC,
        enabled_sensors="energy|water|waste",
        is_active=True,
    )
    db_session.add_all([cfg_a, cfg_b])
    db_session.commit()

    return {
        "org_a": org_a,
        "org_b": org_b,
        "block_science": block_a1,
        "block_eng": block_a2,
        "block_hospital": block_b1,
    }


# ===========================================================================
# PART 1: ANOMALY LIFECYCLE (TESTS 1-8)
# ===========================================================================

def test_resolve_anomaly_transitions_to_resolved(client: TestClient, db_session: Session, auth_headers, test_setup):
    """1. Test that resolving an open anomaly transitions it to RESOLVED with resolved_at."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        block_id="block-science",
        metric="energy",
        value=150.0,
        expected_min=80.0,
        expected_max=120.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()
    db_session.refresh(anomaly)

    resp = client.patch(f"/api/v1/anomalies/{anomaly.id}", json={"status": "RESOLVED"}, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "RESOLVED"
    assert data["resolved_at"] is not None

    db_session.refresh(anomaly)
    assert anomaly.status == AnomalyRecord.STATUS_RESOLVED
    assert anomaly.resolved_at is not None


def test_dismiss_anomaly_transitions_to_dismissed(client: TestClient, db_session: Session, auth_headers, test_setup):
    """2. Test that dismissing an open anomaly transitions it to DISMISSED with resolved_at."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        block_id="block-science",
        metric="water",
        value=80.0,
        expected_min=20.0,
        expected_max=50.0,
        severity=AnomalyRecord.SEVERITY_MEDIUM,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    resp = client.patch(f"/api/v1/anomalies/{anomaly.id}", json={"status": "DISMISSED"}, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "DISMISSED"
    assert data["resolved_at"] is not None

    db_session.refresh(anomaly)
    assert anomaly.status == AnomalyRecord.STATUS_DISMISSED


def test_resolve_already_resolved_returns_409(client: TestClient, db_session: Session, auth_headers, test_setup):
    """3. Test that attempting to resolve an already resolved anomaly returns HTTP 409 Conflict."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=150.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_RESOLVED,
        resolved_at=_utcnow(),
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    resp = client.patch(f"/api/v1/anomalies/{anomaly.id}", json={"status": "RESOLVED"}, headers=headers)
    assert resp.status_code == 409
    assert "already" in resp.json()["detail"].lower() or "resolved" in resp.json()["detail"].lower()


def test_dismiss_already_dismissed_returns_409(client: TestClient, db_session: Session, auth_headers, test_setup):
    """4. Test that attempting to dismiss an already dismissed anomaly returns HTTP 409 Conflict."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=150.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_DISMISSED,
        resolved_at=_utcnow(),
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    resp = client.patch(f"/api/v1/anomalies/{anomaly.id}", json={"status": "DISMISSED"}, headers=headers)
    assert resp.status_code == 409
    assert "already" in resp.json()["detail"].lower() or "dismissed" in resp.json()["detail"].lower()


def test_cannot_transition_from_resolved_to_dismissed(client: TestClient, db_session: Session, auth_headers, test_setup):
    """5. Test that transitioning from RESOLVED to DISMISSED is rejected with HTTP 409."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=150.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_RESOLVED,
        resolved_at=_utcnow(),
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    resp = client.patch(f"/api/v1/anomalies/{anomaly.id}", json={"status": "DISMISSED"}, headers=headers)
    assert resp.status_code == 409


def test_cannot_transition_from_dismissed_to_resolved(client: TestClient, db_session: Session, auth_headers, test_setup):
    """6. Test that transitioning from DISMISSED to RESOLVED is rejected with HTTP 409."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=150.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_DISMISSED,
        resolved_at=_utcnow(),
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    resp = client.patch(f"/api/v1/anomalies/{anomaly.id}", json={"status": "RESOLVED"}, headers=headers)
    assert resp.status_code == 409


def test_cannot_transition_from_resolved_to_open(client: TestClient, db_session: Session, auth_headers, test_setup):
    """7. Test that transitioning from RESOLVED back to OPEN is rejected with HTTP 409."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=150.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_RESOLVED,
        resolved_at=_utcnow(),
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    resp = client.patch(f"/api/v1/anomalies/{anomaly.id}", json={"status": "OPEN"}, headers=headers)
    assert resp.status_code == 409


def test_cannot_transition_from_dismissed_to_open(client: TestClient, db_session: Session, auth_headers, test_setup):
    """8. Test that transitioning from DISMISSED back to OPEN is rejected with HTTP 409."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=150.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_DISMISSED,
        resolved_at=_utcnow(),
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    resp = client.patch(f"/api/v1/anomalies/{anomaly.id}", json={"status": "OPEN"}, headers=headers)
    assert resp.status_code == 409


# ===========================================================================
# PART 2: ACTIVE ANOMALIES FILTERING & HEALTH SCORE RECALCULATION (TESTS 9-12)
# ===========================================================================

def test_active_anomalies_list_excludes_resolved(client: TestClient, db_session: Session, auth_headers, test_setup):
    """9. Test that querying active anomalies (status=OPEN) excludes RESOLVED records."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anom_open = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=200.0,
        severity=AnomalyRecord.SEVERITY_CRITICAL,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    anom_resolved = AnomalyRecord(
        organisation_id=org_a.id,
        metric="water",
        value=80.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_RESOLVED,
        resolved_at=_utcnow(),
        timestamp=_utcnow(),
    )
    db_session.add_all([anom_open, anom_resolved])
    db_session.commit()

    resp = client.get(f"/api/v1/anomalies?organisation_id={org_a.id}&status=OPEN", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == anom_open.id


def test_active_anomalies_list_excludes_dismissed(client: TestClient, db_session: Session, auth_headers, test_setup):
    """10. Test that querying active anomalies (status=OPEN) excludes DISMISSED records."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anom_open = AnomalyRecord(
        organisation_id=org_a.id,
        metric="waste",
        value=100.0,
        severity=AnomalyRecord.SEVERITY_CRITICAL,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    anom_dismissed = AnomalyRecord(
        organisation_id=org_a.id,
        metric="temperature",
        value=32.0,
        severity=AnomalyRecord.SEVERITY_MEDIUM,
        status=AnomalyRecord.STATUS_DISMISSED,
        resolved_at=_utcnow(),
        timestamp=_utcnow(),
    )
    db_session.add_all([anom_open, anom_dismissed])
    db_session.commit()

    resp = client.get(f"/api/v1/anomalies?organisation_id={org_a.id}&status=OPEN", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == anom_open.id


def test_resolving_anomaly_updates_health_score(db_session: Session, test_setup):
    """11. Test that resolving an active anomaly restores the calculated facility health score."""
    org_a = test_setup["org_a"]

    # 1 critical anomaly: 100 - (1 * 20) = 80
    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=300.0,
        severity=AnomalyRecord.SEVERITY_CRITICAL,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    score_before = anomaly_service.calculate_health_score(db_session, org_a.id)
    assert score_before == 80

    # Resolve anomaly
    anomaly_service.update_anomaly_status(db_session, anomaly.id, "RESOLVED", org_a.id)

    score_after = anomaly_service.calculate_health_score(db_session, org_a.id)
    assert score_after == 100


def test_dismissing_anomaly_updates_health_score(db_session: Session, test_setup):
    """12. Test that dismissing an active anomaly restores the calculated facility health score."""
    org_a = test_setup["org_a"]

    # 1 high anomaly: 100 - (1 * 10) = 90
    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        metric="water",
        value=90.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    score_before = anomaly_service.calculate_health_score(db_session, org_a.id)
    assert score_before == 90

    # Dismiss anomaly
    anomaly_service.update_anomaly_status(db_session, anomaly.id, "DISMISSED", org_a.id)

    score_after = anomaly_service.calculate_health_score(db_session, org_a.id)
    assert score_after == 100


# ===========================================================================
# PART 3: RECOMMENDATION CONTEXT & MODULE-SPECIFIC ADVICE (TESTS 13-18)
# ===========================================================================

def test_recommendation_references_correct_anomaly_and_block(db_session: Session, test_setup):
    """13. Test that generated recommendation references anomaly_id and exact block_id."""
    org_a = test_setup["org_a"]
    block = test_setup["block_science"]

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        block_id=block.block_id,
        metric="energy",
        value=220.0,
        expected_min=100.0,
        expected_max=150.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    recs = recommendation_service.generate_recommendations_for_organisation(db_session, org_a.id)
    assert len(recs) >= 1
    matching_rec = next((r for r in recs if r.anomaly_id == anomaly.id), None)
    assert matching_rec is not None
    assert matching_rec.block_id == block.block_id
    assert matching_rec.facility_id == "Science Block"


def test_water_recommendation_never_mentions_hvac_or_energy(db_session: Session, test_setup):
    """14. Test that water recommendations do NOT contain HVAC or energy keywords."""
    org_a = test_setup["org_a"]
    block = test_setup["block_science"]

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        block_id=block.block_id,
        metric="water",
        value=120.0,
        expected_min=20.0,
        expected_max=50.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    recs = recommendation_service.generate_recommendations_for_organisation(db_session, org_a.id)
    water_rec = next((r for r in recs if r.metric == "water"), None)
    assert water_rec is not None

    full_text = f"{water_rec.summary} {water_rec.possible_causes} {water_rec.recommended_actions}".lower()
    forbidden_terms = ["hvac", "air conditioning", "electrical load", "cooling unit", "kilowatt", "high-load"]
    for term in forbidden_terms:
        assert term not in full_text, f"Forbidden term '{term}' found in water recommendation: {full_text}"


def test_water_recommendation_suggests_leaks_or_pipes_or_taps(db_session: Session, test_setup):
    """15. Test that water recommendation suggests leaks, pipes, or taps."""
    org_a = test_setup["org_a"]
    block = test_setup["block_science"]

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        block_id=block.block_id,
        metric="water",
        value=110.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    recs = recommendation_service.generate_recommendations_for_organisation(db_session, org_a.id)
    water_rec = next((r for r in recs if r.metric == "water"), None)
    assert water_rec is not None

    full_text = f"{water_rec.summary} {water_rec.possible_causes} {water_rec.recommended_actions}".lower()
    water_keywords = ["leak", "pipe", "tap", "plumbing", "fixture"]
    assert any(kw in full_text for kw in water_keywords), f"No water keywords found in: {full_text}"


def test_waste_recommendation_suggests_collection_or_capacity(db_session: Session, test_setup):
    """16. Test that waste recommendation suggests waste collection or container capacity."""
    org_a = test_setup["org_a"]
    block = test_setup["block_science"]

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        block_id=block.block_id,
        metric="waste",
        value=100.0,
        severity=AnomalyRecord.SEVERITY_CRITICAL,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    recs = recommendation_service.generate_recommendations_for_organisation(db_session, org_a.id)
    waste_rec = next((r for r in recs if r.metric == "waste"), None)
    assert waste_rec is not None

    full_text = f"{waste_rec.summary} {waste_rec.possible_causes} {waste_rec.recommended_actions}".lower()
    waste_keywords = ["waste", "collection", "bin", "capacity"]
    assert any(kw in full_text for kw in waste_keywords), f"No waste keywords found in: {full_text}"


def test_energy_recommendation_suggests_load_or_hvac_or_equipment(db_session: Session, test_setup):
    """17. Test that energy recommendation suggests load, HVAC, or equipment reduction."""
    org_a = test_setup["org_a"]
    block = test_setup["block_science"]

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        block_id=block.block_id,
        metric="energy",
        value=250.0,
        severity=AnomalyRecord.SEVERITY_CRITICAL,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    recs = recommendation_service.generate_recommendations_for_organisation(db_session, org_a.id)
    energy_rec = next((r for r in recs if r.metric == "energy"), None)
    assert energy_rec is not None

    full_text = f"{energy_rec.summary} {energy_rec.possible_causes} {energy_rec.recommended_actions}".lower()
    energy_keywords = ["load", "hvac", "equipment", "electrical"]
    assert any(kw in full_text for kw in energy_keywords), f"No energy keywords found in: {full_text}"


def test_recommendation_contains_exact_block_name(db_session: Session, test_setup):
    """18. Test that recommendation incorporates the exact human-readable block name."""
    org_a = test_setup["org_a"]
    block = test_setup["block_eng"]  # "Engineering Tower B"

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        block_id=block.block_id,
        metric="energy",
        value=280.0,
        severity=AnomalyRecord.SEVERITY_CRITICAL,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    recs = recommendation_service.generate_recommendations_for_organisation(db_session, org_a.id)
    eng_rec = next((r for r in recs if r.anomaly_id == anomaly.id), None)
    assert eng_rec is not None
    assert "Engineering Tower B" in eng_rec.summary or eng_rec.facility_id == "Engineering Tower B"


# ===========================================================================
# PART 4: ORGANISATION DEACTIVATION & ACCESS ENFORCEMENT (TESTS 19-24)
# ===========================================================================

def test_deactivated_org_admin_login_blocked_with_403(client: TestClient, db_session: Session, test_setup):
    """19. Test that an admin of a deactivated organisation cannot log in (HTTP 403)."""
    org_a = test_setup["org_a"]
    admin = User(
        email="org_admin_19@test.com",
        hashed_password=hash_password("Secret123!"),
        full_name="Admin 19",
        role=User.ROLE_ADMIN,
        organisation_id=org_a.id,
        is_active=True,
    )
    db_session.add(admin)
    org_a.is_active = False
    admin.is_active = False
    db_session.commit()

    resp = client.post("/api/v1/auth/login", json={"email": "org_admin_19@test.com", "password": "Secret123!"})
    assert resp.status_code == 403


def test_deactivated_org_admin_login_error_message(client: TestClient, db_session: Session, test_setup):
    """20. Test that the login error message is specifically 'Organisation is deactivated. Access is blocked.'."""
    org_a = test_setup["org_a"]
    admin = User(
        email="org_admin_20@test.com",
        hashed_password=hash_password("Secret123!"),
        full_name="Admin 20",
        role=User.ROLE_ADMIN,
        organisation_id=org_a.id,
        is_active=True,
    )
    db_session.add(admin)
    org_a.is_active = False
    admin.is_active = False
    db_session.commit()

    resp = client.post("/api/v1/auth/login", json={"email": "org_admin_20@test.com", "password": "Secret123!"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Organisation is deactivated. Access is blocked."


def test_deactivated_org_admin_existing_token_rejected_with_403(client: TestClient, db_session: Session, auth_headers, test_setup):
    """21. Test that existing Bearer tokens of an admin whose org was deactivated are rejected with HTTP 403."""
    org_a = test_setup["org_a"]
    headers = auth_headers("active_then_deactivated@test.com", User.ROLE_ADMIN, org_a.id)

    # Deactivate the organisation
    org_a.is_active = False
    db_session.commit()

    # Now make request with previously generated token
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Organisation is deactivated. Access is blocked."


def test_super_admin_login_unaffected_by_org_deactivation(client: TestClient, db_session: Session, test_setup):
    """22. Test that Super Admin login is NOT blocked when organisations are deactivated."""
    org_a = test_setup["org_a"]
    org_a.is_active = False
    db_session.commit()

    super_admin = User(
        email="superadmin_test@test.com",
        hashed_password=hash_password("SuperSecret123!"),
        full_name="Super Admin",
        role=User.ROLE_SUPER_ADMIN,
        organisation_id=None,
        is_active=True,
    )
    db_session.add(super_admin)
    db_session.commit()

    resp = client.post("/api/v1/auth/login", json={"email": "superadmin_test@test.com", "password": "SuperSecret123!"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_super_admin_can_manage_deactivated_org(client: TestClient, db_session: Session, auth_headers, test_setup):
    """23. Test that Super Admin can access and manage a deactivated organisation."""
    org_a = test_setup["org_a"]
    org_a.is_active = False
    db_session.commit()

    super_headers = auth_headers("superadmin_manage@test.com", User.ROLE_SUPER_ADMIN, None)

    resp = client.get(f"/api/v1/organisations/{org_a.id}", headers=super_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == org_a.id
    assert resp.json()["is_active"] is False


def test_reactivated_org_admin_can_login_again(client: TestClient, db_session: Session, auth_headers, test_setup):
    """24. Test that reactivating an organisation restores admin login access."""
    org_a = test_setup["org_a"]
    admin = User(
        email="admin_reactivate@test.com",
        hashed_password=hash_password("Password123!"),
        full_name="Admin Reactivate",
        role=User.ROLE_ADMIN,
        organisation_id=org_a.id,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Super admin deactivates org
    super_headers = auth_headers("super_24@test.com", User.ROLE_SUPER_ADMIN, None)
    resp_del = client.delete(f"/api/v1/organisations/{org_a.id}", headers=super_headers)
    assert resp_del.status_code == 200

    # Admin login should be blocked
    resp_block = client.post("/api/v1/auth/login", json={"email": "admin_reactivate@test.com", "password": "Password123!"})
    assert resp_block.status_code == 403

    # Super admin reactivates org
    resp_react = client.post(f"/api/v1/organisations/{org_a.id}/reactivate", headers=super_headers)
    assert resp_react.status_code == 200

    # Admin login now succeeds
    resp_login = client.post("/api/v1/auth/login", json={"email": "admin_reactivate@test.com", "password": "Password123!"})
    assert resp_login.status_code == 200
    assert "access_token" in resp_login.json()


# ===========================================================================
# PART 5: SECURITY, RBAC & MULTI-TENANT ISOLATION (TESTS 25-28)
# ===========================================================================

def test_admin_cannot_resolve_other_org_anomaly(client: TestClient, db_session: Session, auth_headers, test_setup):
    """25. Test that an admin from Org B cannot resolve an anomaly belonging to Org A."""
    org_a = test_setup["org_a"]
    org_b = test_setup["org_b"]

    anomaly_a = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=200.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly_a)
    db_session.commit()

    headers_b = auth_headers("admin_b@test.com", User.ROLE_ADMIN, org_b.id)
    resp = client.patch(f"/api/v1/anomalies/{anomaly_a.id}", json={"status": "RESOLVED"}, headers=headers_b)
    assert resp.status_code in [403, 404]

    db_session.refresh(anomaly_a)
    assert anomaly_a.status == AnomalyRecord.STATUS_OPEN


def test_admin_cannot_dismiss_other_org_anomaly(client: TestClient, db_session: Session, auth_headers, test_setup):
    """26. Test that an admin from Org B cannot dismiss an anomaly belonging to Org A."""
    org_a = test_setup["org_a"]
    org_b = test_setup["org_b"]

    anomaly_a = AnomalyRecord(
        organisation_id=org_a.id,
        metric="water",
        value=150.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly_a)
    db_session.commit()

    headers_b = auth_headers("admin_b@test.com", User.ROLE_ADMIN, org_b.id)
    resp = client.patch(f"/api/v1/anomalies/{anomaly_a.id}", json={"status": "DISMISSED"}, headers=headers_b)
    assert resp.status_code in [403, 404]

    db_session.refresh(anomaly_a)
    assert anomaly_a.status == AnomalyRecord.STATUS_OPEN


def test_unauthenticated_cannot_resolve_or_dismiss(client: TestClient, db_session: Session, test_setup):
    """27. Test that requests without authentication are rejected with HTTP 401 Unauthorized."""
    org_a = test_setup["org_a"]
    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=150.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    resp_patch = client.patch(f"/api/v1/anomalies/{anomaly.id}", json={"status": "RESOLVED"})
    assert resp_patch.status_code == 401

    resp_resolve = client.post(f"/api/v1/anomalies/{anomaly.id}/resolve")
    assert resp_resolve.status_code == 401


def test_viewer_role_cannot_resolve_or_dismiss(client: TestClient, db_session: Session, auth_headers, test_setup):
    """28. Test that an unprivileged user (not ADMIN or SUPER_ADMIN) cannot modify anomaly status."""
    org_a = test_setup["org_a"]
    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=150.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    headers_viewer = auth_headers("viewer@test.com", "VIEWER", org_a.id)
    resp = client.patch(f"/api/v1/anomalies/{anomaly.id}", json={"status": "RESOLVED"}, headers=headers_viewer)
    assert resp.status_code == 403


# ===========================================================================
# PART 6: LINKED RECOMMENDATION LIFECYCLE TESTS (TESTS 29-33)
# ===========================================================================

def test_resolve_anomaly_resolves_linked_recommendation_and_removes_from_active_list(
    client: TestClient, db_session: Session, auth_headers, test_setup
):
    """29. Test that resolving an anomaly automatically marks linked recommendation as RESOLVED and removes it from active list."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        block_id="block-science",
        metric="energy",
        value=320.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    rec = AIRecommendation(
        organisation_id=org_a.id,
        block_id="block-science",
        facility_id="Science Block",
        anomaly_id=anomaly.id,
        metric="energy",
        current_value=320.0,
        severity="HIGH",
        priority="HIGH",
        status=AIRecommendation.STATUS_ACTIVE,
        summary="High energy usage in Science Block",
        recommended_actions="Inspect high-load equipment in Science Block",
        data_sufficient=True,
    )
    db_session.add(rec)
    db_session.commit()

    # Pre-condition: rec is returned in active/OPEN list
    resp_open_pre = client.get("/api/v1/recommendations", params={"status": "OPEN"}, headers=headers)
    assert resp_open_pre.status_code == 200
    pre_ids = [item["id"] for item in resp_open_pre.json()["items"]]
    assert rec.id in pre_ids

    # Resolve anomaly via API
    resp_resolve = client.post(f"/api/v1/anomalies/{anomaly.id}/resolve", headers=headers)
    assert resp_resolve.status_code == 200

    # Verify anomaly is resolved with timestamp
    db_session.refresh(anomaly)
    assert anomaly.status == AnomalyRecord.STATUS_RESOLVED
    assert anomaly.resolved_at is not None

    # Verify linked recommendation status in database
    db_session.refresh(rec)
    assert rec.status == AIRecommendation.STATUS_RESOLVED

    # Verify recommendation immediately disappears from active recommendations view
    resp_open_post = client.get("/api/v1/recommendations", params={"status": "OPEN"}, headers=headers)
    assert resp_open_post.status_code == 200
    post_open_ids = [item["id"] for item in resp_open_post.json()["items"]]
    assert rec.id not in post_open_ids

    # Verify recommendation IS preserved and visible in RESOLVED filter
    resp_resolved = client.get("/api/v1/recommendations", params={"status": "RESOLVED"}, headers=headers)
    assert resp_resolved.status_code == 200
    resolved_ids = [item["id"] for item in resp_resolved.json()["items"]]
    assert rec.id in resolved_ids


def test_dismiss_anomaly_dismisses_linked_recommendation_and_removes_from_active_list(
    client: TestClient, db_session: Session, auth_headers, test_setup
):
    """30. Test that dismissing an anomaly automatically marks linked recommendation as DISMISSED and removes it from active list."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    anomaly = AnomalyRecord(
        organisation_id=org_a.id,
        block_id="block-science",
        metric="water",
        value=85.0,
        severity=AnomalyRecord.SEVERITY_MEDIUM,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(anomaly)
    db_session.commit()

    rec = AIRecommendation(
        organisation_id=org_a.id,
        block_id="block-science",
        facility_id="Science Block",
        anomaly_id=anomaly.id,
        metric="water",
        current_value=85.0,
        severity="MEDIUM",
        priority="MEDIUM",
        status=AIRecommendation.STATUS_ACTIVE,
        summary="Water usage in Science Block above baseline",
        recommended_actions="Inspect pipes and taps in Science Block",
        data_sufficient=True,
    )
    db_session.add(rec)
    db_session.commit()

    # Pre-condition: rec is returned in active/OPEN list
    resp_open_pre = client.get("/api/v1/recommendations", params={"status": "OPEN"}, headers=headers)
    assert resp_open_pre.status_code == 200
    pre_ids = [item["id"] for item in resp_open_pre.json()["items"]]
    assert rec.id in pre_ids

    # Dismiss anomaly via API
    resp_dismiss = client.post(f"/api/v1/anomalies/{anomaly.id}/dismiss", headers=headers)
    assert resp_dismiss.status_code == 200

    # Verify anomaly is dismissed with timestamp
    db_session.refresh(anomaly)
    assert anomaly.status == AnomalyRecord.STATUS_DISMISSED
    assert anomaly.resolved_at is not None

    # Verify linked recommendation status in database
    db_session.refresh(rec)
    assert rec.status == AIRecommendation.STATUS_DISMISSED

    # Verify recommendation immediately disappears from active recommendations view
    resp_open_post = client.get("/api/v1/recommendations", params={"status": "OPEN"}, headers=headers)
    assert resp_open_post.status_code == 200
    post_open_ids = [item["id"] for item in resp_open_post.json()["items"]]
    assert rec.id not in post_open_ids

    # Verify recommendation IS preserved and visible in DISMISSED filter
    resp_dismissed = client.get("/api/v1/recommendations", params={"status": "DISMISSED"}, headers=headers)
    assert resp_dismissed.status_code == 200
    dismissed_ids = [item["id"] for item in resp_dismissed.json()["items"]]
    assert rec.id in dismissed_ids


def test_unrelated_recommendations_remain_active(
    client: TestClient, db_session: Session, auth_headers, test_setup
):
    """31. Test that resolving one anomaly does not affect unrelated recommendations in the same or other organisations."""
    org_a = test_setup["org_a"]
    org_b = test_setup["org_b"]
    headers_a = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)
    headers_b = auth_headers("admin_b@test.com", User.ROLE_ADMIN, org_b.id)

    # Org A: Anomaly 1 (will be resolved)
    ano_a1 = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=250.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    # Org A: Anomaly 2 (must remain open)
    ano_a2 = AnomalyRecord(
        organisation_id=org_a.id,
        metric="water",
        value=90.0,
        severity=AnomalyRecord.SEVERITY_MEDIUM,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    # Org B: Anomaly B1 (must remain open)
    ano_b1 = AnomalyRecord(
        organisation_id=org_b.id,
        metric="waste",
        value=95.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add_all([ano_a1, ano_a2, ano_b1])
    db_session.commit()

    rec_a1 = AIRecommendation(
        organisation_id=org_a.id,
        anomaly_id=ano_a1.id,
        metric="energy",
        current_value=250.0,
        severity="HIGH",
        status=AIRecommendation.STATUS_ACTIVE,
        summary="Energy anomaly 1",
        data_sufficient=True,
    )
    rec_a2 = AIRecommendation(
        organisation_id=org_a.id,
        anomaly_id=ano_a2.id,
        metric="water",
        current_value=90.0,
        severity="MEDIUM",
        status=AIRecommendation.STATUS_ACTIVE,
        summary="Water anomaly 2",
        data_sufficient=True,
    )
    rec_b1 = AIRecommendation(
        organisation_id=org_b.id,
        anomaly_id=ano_b1.id,
        metric="waste",
        current_value=95.0,
        severity="HIGH",
        status=AIRecommendation.STATUS_ACTIVE,
        summary="Waste anomaly B1",
        data_sufficient=True,
    )
    db_session.add_all([rec_a1, rec_a2, rec_b1])
    db_session.commit()

    # Resolve ano_a1
    resp_resolve = client.patch(f"/api/v1/anomalies/{ano_a1.id}", json={"status": "RESOLVED"}, headers=headers_a)
    assert resp_resolve.status_code == 200

    # Refresh DB
    db_session.refresh(rec_a1)
    db_session.refresh(rec_a2)
    db_session.refresh(rec_b1)

    # Rec A1 must be RESOLVED
    assert rec_a1.status == AIRecommendation.STATUS_RESOLVED
    # Rec A2 must remain ACTIVE
    assert rec_a2.status == AIRecommendation.STATUS_ACTIVE
    # Rec B1 must remain ACTIVE
    assert rec_b1.status == AIRecommendation.STATUS_ACTIVE

    # Org A active list has rec_a2, but not rec_a1
    resp_a_open = client.get("/api/v1/recommendations", params={"status": "OPEN"}, headers=headers_a)
    assert resp_a_open.status_code == 200
    a_open_ids = [item["id"] for item in resp_a_open.json()["items"]]
    assert rec_a1.id not in a_open_ids
    assert rec_a2.id in a_open_ids

    # Org B active list has rec_b1
    resp_b_open = client.get("/api/v1/recommendations", params={"status": "OPEN"}, headers=headers_b)
    assert resp_b_open.status_code == 200
    b_open_ids = [item["id"] for item in resp_b_open.json()["items"]]
    assert rec_b1.id in b_open_ids


def test_historical_recommendations_preserved_in_all_views(
    client: TestClient, db_session: Session, auth_headers, test_setup
):
    """32. Test that historical recommendation records are preserved in the DB and visible in ALL view."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    ano = AnomalyRecord(
        organisation_id=org_a.id,
        metric="energy",
        value=300.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(ano)
    db_session.commit()

    rec = AIRecommendation(
        organisation_id=org_a.id,
        anomaly_id=ano.id,
        metric="energy",
        current_value=300.0,
        severity="HIGH",
        status=AIRecommendation.STATUS_ACTIVE,
        summary="Historical preservation test",
        data_sufficient=True,
    )
    db_session.add(rec)
    db_session.commit()

    client.post(f"/api/v1/anomalies/{ano.id}/resolve", headers=headers)

    # Row still exists in DB
    existing_rec = db_session.query(AIRecommendation).filter(AIRecommendation.id == rec.id).first()
    assert existing_rec is not None
    assert existing_rec.status == "RESOLVED"

    # Visible in ALL view
    resp_all = client.get("/api/v1/recommendations", params={"status": "ALL"}, headers=headers)
    assert resp_all.status_code == 200
    all_ids = [item["id"] for item in resp_all.json()["items"]]
    assert rec.id in all_ids


def test_recommendation_block_context_preserved_after_resolve(
    client: TestClient, db_session: Session, auth_headers, test_setup
):
    """33. Test that recommendation context (block name, block_id, metric, actions) remains preserved when resolved."""
    org_a = test_setup["org_a"]
    headers = auth_headers("admin_a@test.com", User.ROLE_ADMIN, org_a.id)

    ano = AnomalyRecord(
        organisation_id=org_a.id,
        block_id="block-science",
        facility_id="Science Block",
        metric="water",
        value=110.0,
        severity=AnomalyRecord.SEVERITY_HIGH,
        status=AnomalyRecord.STATUS_OPEN,
        timestamp=_utcnow(),
    )
    db_session.add(ano)
    db_session.commit()

    rec = AIRecommendation(
        organisation_id=org_a.id,
        block_id="block-science",
        facility_id="Science Block",
        anomaly_id=ano.id,
        metric="water",
        current_value=110.0,
        severity="HIGH",
        priority="HIGH",
        status=AIRecommendation.STATUS_ACTIVE,
        summary="Water usage in Science Block is significantly above baseline",
        recommended_actions="Inspect pipes, taps, and water-consuming equipment in Science Block",
        possible_causes="Possible plumbing leakage in Science Block",
        data_sufficient=True,
    )
    db_session.add(rec)
    db_session.commit()

    client.post(f"/api/v1/anomalies/{ano.id}/resolve", headers=headers)

    # Verify context is preserved
    resp = client.get(f"/api/v1/recommendations/{org_a.id}", params={"status": "RESOLVED"}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    target_rec = next((item for item in items if item["id"] == rec.id), None)
    assert target_rec is not None
    assert target_rec["facility_id"] == "Science Block"
    assert target_rec["metric"] == "water"
    assert "Science Block" in target_rec["summary"]
    assert "Science Block" in target_rec["recommended_actions"][0]
