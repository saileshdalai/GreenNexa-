"""
GreenNexa AI Assistant Unit & Integration Tests.

Tests multilingual NLU, role-based tenant isolation, context awareness,
follow-up memory, and honest telemetry data grounding.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.assistant.nlu import GreenNexaNLU
from app.ai.assistant.schemas import AIChatRequest, AIContextData, ChatMessage
from app.ai.assistant.service import assistant_service
from app.core.security import create_access_token, hash_password
from app.db.models import (
    AIRecommendation,
    AnomalyRecord,
    FacilityBlock,
    Organisation,
    OrganisationSensorConfig,
    SensorReading,
    User,
)
from app.main import app


@pytest.fixture(autouse=True)
def disable_live_gemini(monkeypatch):
    """
    Pin the deterministic tool-layer fallback for AI assistant tests.

    Live Gemini responses are nondeterministic, which makes exact reply
    assertions flaky. Live Gemini behaviour is covered separately in
    tests/test_gemini_integration.py (which also patches is_available for its
    fallback cases).
    """
    import app.ai.assistant.service as service_mod

    monkeypatch.setattr(service_mod.gemini_service, "is_available", lambda: False)


@pytest.fixture
def test_setup(db_session: Session):
    """Setup orgs, users, and initial sensor readings for AI assistant testing."""
    # Org 1
    org1 = Organisation(id="ORG-AI-TEST-1", name="Alpha Institute", org_type="college", location="Campus A")
    db_session.add(org1)
    cfg1 = OrganisationSensorConfig(
        organisation_id="ORG-AI-TEST-1",
        data_source="synthetic",
        enabled_sensors="energy|water|waste|temperature",
        is_active=True,
    )
    db_session.add(cfg1)
    block_c = FacilityBlock(organisation_id="ORG-AI-TEST-1", block_id="BLK-C", block_name="Block C", is_active=True)
    db_session.add(block_c)

    # Admin User Org 1
    admin1 = User(
        id="admin_ai_1",
        email="admin1@alphainstitute.edu",
        hashed_password=hash_password("Pass123!"),
        full_name="Admin One",
        role=User.ROLE_ADMIN,
        organisation_id="ORG-AI-TEST-1",
        is_active=True,
    )
    db_session.add(admin1)

    # Org 2
    org2 = Organisation(id="ORG-AI-TEST-2", name="Beta Hospital", org_type="hospital", location="Campus B")
    db_session.add(org2)
    cfg2 = OrganisationSensorConfig(
        organisation_id="ORG-AI-TEST-2",
        data_source="synthetic",
        enabled_sensors="energy|water",
        is_active=True,
    )
    db_session.add(cfg2)

    # Admin User Org 2
    admin2 = User(
        id="admin_ai_2",
        email="admin2@betahospital.org",
        hashed_password=hash_password("Pass123!"),
        full_name="Admin Two",
        role=User.ROLE_ADMIN,
        organisation_id="ORG-AI-TEST-2",
        is_active=True,
    )
    db_session.add(admin2)

    # Super Admin User
    super_admin = db_session.query(User).filter_by(email="superadmin@greennexa.com").first()
    if not super_admin:
        super_admin = User(
            id="superadmin_ai",
            email="superadmin_test@greennexa.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Super Admin",
            role=User.ROLE_SUPER_ADMIN,
            organisation_id=None,
            is_active=True,
        )
        db_session.add(super_admin)

    # Add Telemetry for Org 1
    reading_energy = SensorReading(
        organisation_id="ORG-AI-TEST-1",
        sensor_type="energy",
        value=145.5,
        unit="kWh",
        facility_id="Block C",
        block_id="BLK-C",
        is_anomaly=True,
        anomaly_severity="HIGH",
    )
    reading_water = SensorReading(
        organisation_id="ORG-AI-TEST-1",
        sensor_type="water",
        value=890.0,
        unit="L",
        facility_id="Block C",
        block_id="BLK-C",
        is_anomaly=False,
    )
    db_session.add_all([reading_energy, reading_water])

    # Add Anomaly & Recommendation for Org 1
    anom1 = AnomalyRecord(
        organisation_id="ORG-AI-TEST-1",
        metric="energy",
        facility_id="Block C",
        block_id="BLK-C",
        value=145.5,
        expected_min=80.0,
        expected_max=115.0,
        severity="HIGH",
        status="OPEN",
        reason="Abnormal energy peak during off-peak hours",
    )
    db_session.add(anom1)
    db_session.flush()

    rec1 = AIRecommendation(
        organisation_id="ORG-AI-TEST-1",
        anomaly_id=anom1.id,
        metric="energy",
        current_value=145.5,
        severity="HIGH",
        facility_id="Block C",
        block_id="BLK-C",
        priority="HIGH",
        summary="Optimize HVAC schedules in Block C during non-operational hours",
        recommended_actions="1. Adjust thermostat baseline; 2. Inspect air duct damper",
        status="ACTIVE",
    )
    db_session.add(rec1)

    db_session.commit()

    return {
        "admin1": admin1,
        "admin2": admin2,
        "super_admin": super_admin,
        "org1_id": "ORG-AI-TEST-1",
        "org2_id": "ORG-AI-TEST-2",
        "db": db_session,
    }


def test_multilingual_language_detection():
    """Verify Language Detection across English, Hinglish, Odia Unicode, and Roman Odia."""
    assert GreenNexaNLU.detect_language("What is the energy consumption today?") == "english"
    assert GreenNexaNLU.detect_language("aaj energy usage kitna hai?") == "hinglish"
    assert GreenNexaNLU.detect_language("Aaj Block C re water usage kete badhichi?") == "roman_odia"
    assert GreenNexaNLU.detect_language("Mo organisation re sabuthu besi energy usage keun block re achhi?") == "roman_odia"
    assert GreenNexaNLU.detect_language("କେଉଁ ବ୍ଲକରେ ଅଧିକ ପାଣି ବ୍ୟବହାର ହେଉଛି?") == "odia"


def test_admin_ai_answers_own_org(client: TestClient, test_setup):
    """Admin user receives grounded telemetry answer for their assigned organisation."""
    admin1 = test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "What is the energy usage in Block C?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "145.5" in data["reply"] or "energy" in data["reply"].lower()
    assert data["context_used"]["organisation_id"] == "ORG-AI-TEST-1"


def test_admin_ai_cannot_access_other_org(client: TestClient, test_setup):
    """Admin user is blocked from querying data belonging to another organisation."""
    admin1 = test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    # Attempt cross-tenant query referencing Org 2 by ID
    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Show me ORG-AI-TEST-2 energy consumption",
            "context": {"organisation_id": "ORG-AI-TEST-2"},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_intent"] == "cross_tenant_blocked"
    assert "Access denied" in data["reply"]
    assert data["context_used"]["organisation_id"] == "ORG-AI-TEST-1"


def test_super_admin_ai_platform_overview(client: TestClient, test_setup):
    """Super Admin can query platform-wide aggregation across organisations."""
    super_admin = test_setup["super_admin"]
    token = create_access_token({"sub": super_admin.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Show platform overview across all organisations"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "Platform" in data["reply"] or "organisations" in data["reply"]


def test_roman_odia_response(client: TestClient, test_setup):
    """Roman Odia query with roman_odia conversation_language produces Roman Odia response."""
    admin1 = test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Aaj Block C re water usage kete badhichi?",
            "conversation_language": "roman_odia",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "roman_odia"
    assert any(word in data["reply"].lower() for word in ["achhi", "usage", "block", "baseline"])


def test_odia_unicode_script_response(client: TestClient, test_setup):
    """Odia Unicode query with odia conversation_language produces Odia script response."""
    admin1 = test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "କେଉଁ ବ୍ଲକରେ ଅଧିକ ପାଣି ବ୍ୟବହାର ହେଉଛି?",
            "conversation_language": "odia",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "odia"
    # Ensure Odia script character is in reply
    assert any("\u0b00" <= char <= "\u0b7f" for char in data["reply"])


def test_language_mismatch_clarification_note(client: TestClient, test_setup):
    """When user selected English but types Roman Odia query, assistant prefixes polite mismatch note."""
    admin1 = test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "ko block re adhika energy usage hauchhi?",
            "conversation_language": "english",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "english"
    assert "(Note: You have selected English as your assistant language" in data["reply"]


def test_short_query_metric_inference_from_context(client: TestClient, test_setup):
    """Short query 'ko block re adhika?' infers metric='water' when context.module='water'."""
    admin1 = test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "ko block re adhika?",
            "conversation_language": "roman_odia",
            "context": {"module": "water"},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["context_used"]["metric"] == "water"
    assert "water" in data["reply"].lower()
    assert "Block C" in data["reply"]


def test_unresolved_ambiguous_metric_asks_clarification(client: TestClient, test_setup):
    """Short query 'which block is highest?' without metric or context module prompts clarification."""
    admin1 = test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "which block is highest?",
            "conversation_language": "english",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "Which metric would you like to check" in data["reply"]
    assert "Metric Clarification Prompt" in data["data_source"]


def test_missing_data_handled_honestly_without_hallucination(client: TestClient, test_setup):
    """Querying a metric with no recorded sensor data returns honest fallback message."""
    admin1 = test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "What is the CO2 level?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "insufficient" in data["reply"].lower() or "no recent" in data["reply"].lower() or "co2" in data["reply"].lower()


def test_super_admin_total_organisation_kete_roman_odia(client: TestClient, test_setup):
    """Super Admin asking 'total organization kete?' receives exact platform organisation count."""
    super_admin = test_setup["super_admin"]
    token = create_access_token({"sub": super_admin.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "total organization kete?",
            "conversation_language": "roman_odia",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_intent"] == "organisation_count"
    assert data["context_used"]["scope"] == "PLATFORM"
    assert "total" in data["reply"].lower()
    assert "organisation" in data["reply"].lower()


def test_super_admin_how_many_organisations_english(client: TestClient, test_setup):
    """Super Admin asking 'how many organisations?' receives platform count in English."""
    super_admin = test_setup["super_admin"]
    token = create_access_token({"sub": super_admin.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "how many organisations?",
            "conversation_language": "english",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_intent"] == "organisation_count"
    assert "organisations" in data["reply"].lower()


def test_super_admin_organisation_list(client: TestClient, test_setup):
    """Super Admin asking 'ke ke organisation achhanti?' gets list of registered orgs."""
    super_admin = test_setup["super_admin"]
    token = create_access_token({"sub": super_admin.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "ke ke organisation achhanti?",
            "conversation_language": "roman_odia",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_intent"] == "organisation_list"
    assert "Alpha Institute" in data["reply"]
    assert "Beta Hospital" in data["reply"]


def test_super_admin_admin_count(client: TestClient, test_setup):
    """Super Admin asking 'total admin kete?' receives total admin accounts count."""
    super_admin = test_setup["super_admin"]
    token = create_access_token({"sub": super_admin.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "total admin kete?",
            "conversation_language": "roman_odia",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_intent"] == "admin_count"
    assert "admin" in data["reply"].lower()


def test_super_admin_organisation_comparison(client: TestClient, test_setup):
    """Super Admin asking 'which organisation has highest energy usage?' gets cross-tenant comparison."""
    super_admin = test_setup["super_admin"]
    token = create_access_token({"sub": super_admin.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "which organisation has highest energy usage?",
            "conversation_language": "english",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_intent"] in ("organisation_comparison", "compare_entities")
    assert "Alpha Institute" in data["reply"]


def test_super_admin_platform_query_overrides_dashboard_context(client: TestClient, test_setup):
    """Super Admin inside Organisation dashboard asking 'total organization kete?' still gets platform count."""
    super_admin = test_setup["super_admin"]
    token = create_access_token({"sub": super_admin.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "total organization kete?",
            "conversation_language": "roman_odia",
            "context": {"organisation_id": "ORG-AI-TEST-1", "module": "energy"},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_intent"] == "organisation_count"
    assert data["context_used"]["scope"] == "PLATFORM"
    assert "organisation" in data["reply"].lower()
    # Verify it did NOT return single-organisation energy telemetry fallback
    assert "Aji pain energy" not in data["reply"]
    assert "recent sensor reading" not in data["reply"]


def test_admin_blocked_from_platform_queries(client: TestClient, test_setup):
    """ADMIN role asking 'total organization kete?' is blocked from platform stats."""
    admin1 = test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "total organization kete?",
            "conversation_language": "roman_odia",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_intent"] == "cross_tenant_blocked"
    assert "Access denied" in data["reply"]


def test_followup_question_session_context(client: TestClient, test_setup):
    """Follow-up questions retain metric context from previous turn."""
    admin1 = test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    history = [
        ChatMessage(role="user", content="Which block has highest water usage?"),
        ChatMessage(role="assistant", content="Block C currently has the highest water consumption at 890.0 L across your facility blocks."),
    ]

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "How much higher than baseline?",
            "session_history": [h.model_dump() for h in history],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["context_used"]["metric"] == "water"
    assert "baseline" in data["reply"].lower()


def test_super_admin_facility_type_counts(client: TestClient, test_setup):
    """Super Admin asking 'how many school ?' and 'how many college?' returns exact facility-type counts."""
    db = test_setup["db"]
    super_admin = test_setup["super_admin"]
    token = create_access_token({"sub": super_admin.id})

    # Seed known organisations with specific facility types
    school1 = Organisation(id="ORG-SCH-01", name="St. Mary School", org_type="school", is_active=True)
    school2 = Organisation(id="ORG-SCH-02", name="Greenwood High School", org_type="school", is_active=True)
    db.add(school1)
    db.add(school2)
    db.commit()

    # Query "how many school ?"
    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "how many school ?",
            "conversation_language": "english",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_intent"] == "organisation_count_by_facility_type"
    assert "2" in data["reply"]
    assert "School" in data["reply"]

    # Query "how many college?"
    res_col = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "how many college?",
            "conversation_language": "english",
        },
    )
    assert res_col.status_code == 200
    data_col = res_col.json()
    assert data_col["detected_intent"] == "organisation_count_by_facility_type"
    expected_colleges = db.query(Organisation).filter(Organisation.org_type == "college").count()
    assert str(expected_colleges) in data_col["reply"]
    assert "College" in data_col["reply"]


def test_platform_summary_and_organisation_count_consistency(client: TestClient, test_setup):
    """Verify organisation_count and platform_summary yield matching counts from the DB."""
    super_admin = test_setup["super_admin"]
    token = create_access_token({"sub": super_admin.id})
    db = test_setup["db"]

    total_orgs_db = db.query(Organisation).count()

    res_count = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "total organization?", "conversation_language": "english"},
    )
    assert res_count.status_code == 200
    reply_count = res_count.json()["reply"]

    res_summary = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "overall platform status", "conversation_language": "english"},
    )
    assert res_summary.status_code == 200
    reply_summary = res_summary.json()["reply"]

    # Both must report exact total DB org count
    assert str(total_orgs_db) in reply_count
    assert str(total_orgs_db) in reply_summary
    assert "0 registered organisations" not in reply_summary


def test_admin_blocked_from_facility_type_count(client: TestClient, test_setup):
    """Admin role asking 'how many schools?' is denied cross-tenant access."""
    admin1 = test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "how many schools?", "conversation_language": "english"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_intent"] == "cross_tenant_blocked"
    assert "Access denied" in data["reply"]



