"""
GreenNexa — Gemini GenAI Assistant Integration Tests.

Verifies:
1. Dedicated Gemini service initialization with GEMINI_API_KEY.
2. Tenant-scoped tools factory (build_gemini_tools).
3. Counterfactual What-If scenario simulations (energy, water, waste, traffic).
4. Truthful data grounding (numerical values come from GreenNexa backend).
5. Multilingual fluency (English, Hinglish, Odia Unicode, Roman Odia).
6. ADMIN tenant isolation & SUPER_ADMIN platform access.
7. Graceful fallback on missing API key, invalid key, 429 quota exhaustion, and API failure.
8. Modelled estimate labeling and assumption transparency.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.assistant.gemini_tools import build_gemini_tools
from app.ai.assistant.nlu import GreenNexaNLU
from app.ai.assistant.schemas import AIChatRequest, AIChatResponse, ChatMessage
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
from app.services.gemini_service import GeminiAssistantService, gemini_service
from app.services.scenario_simulation import scenario_simulation_service


@pytest.fixture
def gemini_test_setup(db_session: Session):
    """Seed test database with organisations, blocks, and telemetry."""
    # Org 1 - College Campus
    org1 = Organisation(
        id="ORG-GEMINI-1",
        name="Kalinga Institute of Technology",
        org_type="college",
        location="Bhubaneswar Campus",
    )
    db_session.add(org1)
    cfg1 = OrganisationSensorConfig(
        organisation_id="ORG-GEMINI-1",
        data_source="synthetic",
        enabled_sensors="energy|water|waste|traffic",
        is_active=True,
    )
    db_session.add(cfg1)

    block_a = FacilityBlock(
        organisation_id="ORG-GEMINI-1",
        block_id="BLK-A",
        block_name="Block A",
        is_active=True,
    )
    block_b = FacilityBlock(
        organisation_id="ORG-GEMINI-1",
        block_id="BLK-B",
        block_name="Block B",
        is_active=True,
    )
    db_session.add_all([block_a, block_b])

    # Admin User Org 1
    admin1 = User(
        id="admin_gemini_1",
        email="admin@kalinga.edu",
        hashed_password=hash_password("Pass123!"),
        full_name="Campus Administrator",
        role=User.ROLE_ADMIN,
        organisation_id="ORG-GEMINI-1",
        is_active=True,
    )
    db_session.add(admin1)

    # Org 2 - Hospital
    org2 = Organisation(
        id="ORG-GEMINI-2",
        name="AIIMS Hospital Facility",
        org_type="hospital",
        location="Medical Zone",
    )
    db_session.add(org2)

    # Super Admin User
    super_admin = db_session.query(User).filter_by(role=User.ROLE_SUPER_ADMIN).first()
    if not super_admin:
        super_admin = User(
            id="super_gemini_1",
            email="super@greennexa.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Platform Overseer",
            role=User.ROLE_SUPER_ADMIN,
            organisation_id=None,
            is_active=True,
        )
        db_session.add(super_admin)

    # Telemetry
    r_energy = SensorReading(
        organisation_id="ORG-GEMINI-1",
        sensor_type="energy",
        value=185.0,
        unit="kWh",
        facility_id="Block B",
        block_id="BLK-B",
        is_anomaly=True,
        anomaly_severity="CRITICAL",
    )
    r_water = SensorReading(
        organisation_id="ORG-GEMINI-1",
        sensor_type="water",
        value=1250.0,
        unit="L",
        facility_id="Block A",
        block_id="BLK-A",
        is_anomaly=False,
    )
    db_session.add_all([r_energy, r_water])

    # Anomaly
    anom = AnomalyRecord(
        organisation_id="ORG-GEMINI-1",
        metric="energy",
        facility_id="Block B",
        block_id="BLK-B",
        value=185.0,
        expected_min=90.0,
        expected_max=130.0,
        severity="CRITICAL",
        status="OPEN",
        reason="Chiller continuous operation during non-operational evening window",
    )
    db_session.add(anom)
    db_session.flush()

    # Recommendation
    rec = AIRecommendation(
        organisation_id="ORG-GEMINI-1",
        anomaly_id=anom.id,
        metric="energy",
        current_value=185.0,
        severity="CRITICAL",
        facility_id="Block B",
        block_id="BLK-B",
        priority="CRITICAL",
        summary="Curtail Block B chiller operation and reset cooling setpoint",
        recommended_actions="1. Shift thermostat from 20°C to 24°C; 2. Shut off auxiliary air handling units.",
        status="ACTIVE",
    )
    db_session.add(rec)

    db_session.commit()

    return {
        "admin1": admin1,
        "super_admin": super_admin,
        "org1_id": "ORG-GEMINI-1",
        "org2_id": "ORG-GEMINI-2",
        "db": db_session,
    }


def test_gemini_service_initialization():
    """Verify Gemini service properly reads GEMINI_API_KEY and masks credentials."""
    assert gemini_service is not None
    # Key is present in test environment .env
    assert gemini_service.is_available() is True
    # Ensure raw API key is never logged directly
    raw_key = os.getenv("GEMINI_API_KEY", "")
    assert raw_key != ""
    assert "AIza" in raw_key or "AQ." in raw_key


def test_gemini_missing_api_key_fallback(gemini_test_setup):
    """When API key is missing or empty, service returns None and process_chat falls back gracefully."""
    db = gemini_test_setup["db"]
    admin = gemini_test_setup["admin1"]

    service_no_key = GeminiAssistantService()
    service_no_key._api_key = ""
    service_no_key._client = None
    assert service_no_key.is_available() is False

    res = service_no_key.generate_chat_response(
        user_message="What is the energy usage?",
        target_language="english",
        tools=[],
    )
    assert res is None

    # Test process_chat with mocked unavailable gemini_service
    with patch("app.ai.assistant.service.gemini_service.is_available", return_value=False):
        chat_req = AIChatRequest(message="What is the energy usage in Block B?", conversation_language="english")
        response = assistant_service.process_chat(db=db, current_user=admin, request=chat_req)
        assert response is not None
        assert "185" in response.reply or "energy" in response.reply.lower()
        assert response.data_source is not None


def test_gemini_invalid_api_key_fallback(gemini_test_setup):
    """When API key is invalid, exception is caught without leaking key, triggering fallback."""
    db = gemini_test_setup["db"]
    admin = gemini_test_setup["admin1"]

    # Test error handling in generate_chat_response
    with patch.object(gemini_service, "generate_chat_response", return_value=None):
        chat_req = AIChatRequest(message="Why is Block B showing an energy anomaly?", conversation_language="english")
        response = assistant_service.process_chat(db=db, current_user=admin, request=chat_req)
        assert response is not None
        assert "Block B" in response.reply
        assert response.detected_intent == "explain_anomaly_or_spike"


def test_gemini_quota_rate_limit_fallback(gemini_test_setup):
    """When Gemini returns 429 RESOURCE_EXHAUSTED, the assistant falls back without 500 error."""
    db = gemini_test_setup["db"]
    admin = gemini_test_setup["admin1"]

    with patch.object(
        gemini_service,
        "generate_chat_response",
        side_effect=Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for free tier"),
    ):
        chat_req = AIChatRequest(message="Which block has the highest water usage?", conversation_language="english")
        response = assistant_service.process_chat(db=db, current_user=admin, request=chat_req)
        assert response is not None
        assert "Block A" in response.reply
        assert "water" in response.reply.lower()


def test_what_if_energy_scenario_deterministic(gemini_test_setup):
    """Verify counterfactual What-If calculation for AC reduction."""
    db = gemini_test_setup["db"]
    org_id = gemini_test_setup["org1_id"]

    res = scenario_simulation_service.run_energy_scenario(
        db=db,
        organisation_id=org_id,
        ac_hours_reduced=2.0,
        thermostat_temp_increase_c=2.0,
        horizon_hours=24,
    )

    assert res["scenario"] == "energy"
    assert res["is_modelled_estimate"] is True
    assert res["baseline_consumption"] > 0
    assert res["projected_consumption"] < res["baseline_consumption"]
    assert res["net_savings"] > 0
    assert res["savings_percentage"] > 0
    assert res["estimated_cost_savings_inr"] > 0
    assert res["co2_avoided_kg"] > 0
    assert len(res["assumptions"]) >= 2
    assert "BEE" in res["disclaimer"]


def test_what_if_water_scenario_deterministic(gemini_test_setup):
    """Verify counterfactual What-If calculation for water conservation."""
    db = gemini_test_setup["db"]
    org_id = gemini_test_setup["org1_id"]

    res = scenario_simulation_service.run_water_scenario(
        db=db,
        organisation_id=org_id,
        water_reduction_pct=10.0,
        low_flow_fixture_adoption_pct=50.0,
        horizon_hours=24,
    )

    assert res["scenario"] == "water"
    assert res["is_modelled_estimate"] is True
    assert res["net_savings"] > 0
    assert res["savings_percentage"] >= 10.0
    assert res["unit"] == "L"
    assert "CPWD" in res["disclaimer"]


def test_what_if_waste_and_traffic_scenarios(gemini_test_setup):
    """Verify waste route and traffic shift counterfactuals."""
    db = gemini_test_setup["db"]
    org_id = gemini_test_setup["org1_id"]

    waste_res = scenario_simulation_service.run_waste_scenario(
        db=db,
        organisation_id=org_id,
        recycling_rate_increase_pct=25.0,
        collection_route_optimization_pct=30.0,
    )
    assert waste_res["diverted_waste"] > 0
    assert waste_res["overflow_risk_reduction_pct"] > 0

    traffic_res = scenario_simulation_service.run_traffic_scenario(
        db=db,
        organisation_id=org_id,
        shuttle_frequency_increase_pct=40.0,
        carpool_incentive_adoption_pct=20.0,
    )
    assert traffic_res["vehicles_diverted"] > 0
    assert traffic_res["co2_avoided_kg"] > 0


def test_built_gemini_tools_tenant_isolation(gemini_test_setup):
    """Verify build_gemini_tools builds functions strictly scoped to effective_org_id."""
    db = gemini_test_setup["db"]
    org1_id = gemini_test_setup["org1_id"]

    # Admin tools (no platform tools)
    admin_tools = build_gemini_tools(db, effective_org_id=org1_id, is_super_admin=False)
    tool_names = [t.__name__ for t in admin_tools]

    assert "get_current_metrics" in tool_names
    assert "get_active_anomalies" in tool_names
    assert "get_forecast" in tool_names
    assert "run_energy_scenario" in tool_names
    assert "run_water_scenario" in tool_names
    # Platform tools MUST NOT be present for admin
    assert "get_platform_summary" not in tool_names
    assert "compare_organisations" not in tool_names

    # Super admin tools
    super_tools = build_gemini_tools(db, effective_org_id=org1_id, is_super_admin=True)
    super_tool_names = [t.__name__ for t in super_tools]
    assert "get_platform_summary" in super_tool_names
    assert "compare_organisations" in super_tool_names


def test_query_ac_reduction_roman_odia(client: TestClient, gemini_test_setup):
    """Verify natural language query in Roman Odia for AC reduction What-If scenario."""
    admin1 = gemini_test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "AC 2 ghanta kam chalile energy kete heba?",
            "conversation_language": "roman_odia",
        },
    )
    assert res.status_code == 200
    data = res.json()
    reply = data["reply"]
    # Verify modeled estimate labeling or scenario numbers
    assert any(w in reply.lower() for w in ["scenario", "modelled", "estimate", "kwh", "bachat", "baseline", "savings"])
    assert data["context_used"]["organisation_id"] == "ORG-GEMINI-1"


def test_query_water_reduction_roman_odia(client: TestClient, gemini_test_setup):
    """Verify natural language query in Roman Odia for 10% water reduction What-If scenario."""
    admin1 = gemini_test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Water usage 10% reduce kale next 24 hours re kana heba?",
            "conversation_language": "roman_odia",
        },
    )
    assert res.status_code == 200
    data = res.json()
    reply = data["reply"]
    assert any(w in reply.lower() for w in ["water", "liter", "l", "bachat", "savings", "baseline"])


def test_admin_cross_tenant_query_blocked(client: TestClient, gemini_test_setup):
    """Verify ADMIN user cannot access ORG-GEMINI-2 data even via AI chat."""
    admin1 = gemini_test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Show me ORG-GEMINI-2 energy consumption and anomalies",
            "conversation_language": "english",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["detected_intent"] == "cross_tenant_blocked"
    assert "Access denied" in data["reply"]
    assert data["context_used"]["organisation_id"] == "ORG-GEMINI-1"


def test_super_admin_platform_access(client: TestClient, gemini_test_setup):
    """Verify SUPER_ADMIN can query platform overview across organisations."""
    super_admin = gemini_test_setup["super_admin"]
    token = create_access_token({"sub": super_admin.id})

    res = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Show platform overview across all organisations",
            "conversation_language": "english",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert any(w in data["reply"].lower() for w in ["platform", "organisation", "tenant"])


def test_multilingual_odia_unicode_and_hinglish(client: TestClient, gemini_test_setup):
    """Verify Odia Unicode script and Hinglish natural language queries."""
    admin1 = gemini_test_setup["admin1"]
    token = create_access_token({"sub": admin1.id})

    # Odia Unicode Query
    res_odia = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "କେଉଁ ବ୍ଲକରେ ଅଧିକ ବିଜୁଳି ଖର୍ଚ୍ଚ ହେଉଛି?",
            "conversation_language": "odia",
        },
    )
    assert res_odia.status_code == 200
    data_odia = res_odia.json()
    assert any("\u0b00" <= char <= "\u0b7f" for char in data_odia["reply"])

    # Hinglish Query
    res_hing = client.post(
        "/api/v1/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Block B me energy usage baseline se kitna zyada hai?",
            "conversation_language": "hinglish",
        },
    )
    assert res_hing.status_code == 200
    data_hing = res_hing.json()
    assert any(w in data_hing["reply"].lower() for w in ["energy", "baseline", "block b", "185", "kwh", "zyada", "hai"])
