"""
GreenNexa AI Assistant Service.

Coordinates RBAC & tenant scoping, context resolution, tool execution,
and multilingual response generation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.ai.assistant.gemini_tools import build_gemini_tools
from app.ai.assistant.nlu import GreenNexaNLU
from app.ai.assistant.schemas import AIChatRequest, AIChatResponse, ChatMessage
from app.ai.assistant.tools import GreenNexaDataTools
from app.db.models import Organisation, User
from app.services.gemini_service import gemini_service
from app.services.scenario_simulation import scenario_simulation_service

logger = logging.getLogger(__name__)


PLATFORM_INTENTS = {
    "organisation_count",
    "organisation_count_by_facility_type",
    "admin_count",
    "organisation_list",
    "platform_summary",
    "organisation_comparison",
    "compare_entities",
}


class AIAssistantService:
    """
    Core AI Assistant Orchestrator.
    """

    def process_chat(
        self,
        db: Session,
        current_user: User,
        request: AIChatRequest,
    ) -> AIChatResponse:
        """
        Process user chat request with strict backend security & data scoping.
        """
        user_message = request.message.strip()
        if not user_message:
            return AIChatResponse(
                reply="Please enter a question or command.",
                language="english",
                detected_intent="empty_request",
            )

        is_super_admin = (current_user.role == User.ROLE_SUPER_ADMIN)
        caller_org_id = current_user.organisation_id

        # 1. Extract Session History for Follow-up Conversational Resolution
        last_metric: Optional[str] = None
        last_block: Optional[str] = None
        last_facility_type: Optional[str] = None
        last_intent: Optional[str] = None

        if request.session_history:
            for msg in reversed(request.session_history):
                if msg.role == "assistant":
                    m_extract = GreenNexaNLU.extract_entities(msg.content)
                    if m_extract.get("metric"):
                        last_metric = m_extract["metric"]
                    if m_extract.get("block"):
                        last_block = m_extract["block"]
                    if m_extract.get("facility_type"):
                        last_facility_type = m_extract["facility_type"]
                    if m_extract.get("intent"):
                        last_intent = m_extract["intent"]
                    break

        # 2. Detect Language, Check Mismatch & Extract Entities
        selected_language = (request.conversation_language or "english").lower().strip()
        has_mismatch, detected_language, mismatch_prefix = GreenNexaNLU.check_language_mismatch(
            user_message, selected_language
        )

        context_dict = request.context.model_dump() if request.context else {}
        entities = GreenNexaNLU.extract_entities(user_message, context_dict)

        # Apply follow-up session memory if explicit entity not specified
        if not entities.get("explicit_metric") and last_metric:
            entities["metric"] = last_metric
        if not entities.get("block") and last_block:
            entities["block"] = last_block

        # If user specified a facility type or follow-up count query, classify as facility type count intent
        if entities.get("facility_type") and (
            entities["intent"] == "general_query" or last_intent in ("organisation_count", "organisation_count_by_facility_type")
        ):
            entities["intent"] = "organisation_count_by_facility_type"

        intent = entities["intent"]
        target_metric = entities["metric"] or "energy"
        target_block = entities["block"]
        target_facility_type = entities.get("facility_type")

        # 3. Determine Scope & Enforce Role Boundaries
        effective_org_id: Optional[str] = None
        is_platform_intent = intent in PLATFORM_INTENTS or "all org" in user_message.lower() or "platform" in user_message.lower()

        if is_super_admin:
            if not is_platform_intent and request.context and request.context.organisation_id:
                effective_org_id = request.context.organisation_id
            elif not is_platform_intent:
                first_org = db.query(Organisation).filter_by(is_active=True).first()
                effective_org_id = first_org.id if first_org else caller_org_id
        else:
            # ADMIN role is STRICTLY FORCED to their authenticated organisation_id
            effective_org_id = caller_org_id
            if not effective_org_id:
                return AIChatResponse(
                    reply="Your user account is not associated with an active organisation.",
                    language=selected_language,
                    detected_intent="unauthorized_scope",
                )

            # Block platform-level cross-tenant queries for ADMIN users
            if is_platform_intent or "organisation" in user_message.lower() or "org-" in user_message.lower():
                # Check if user query mentions other orgs or requests platform stats
                lower_msg = user_message.lower()
                other_orgs = db.query(Organisation).filter(Organisation.id != effective_org_id).all()
                has_other_org = any(other.id.lower() in lower_msg or (other.name and other.name.lower() in lower_msg) for other in other_orgs)

                if is_platform_intent or has_other_org:
                    logger.warning(
                        "ADMIN user %s attempted to query platform/cross-tenant stats (%s)",
                        current_user.email,
                        user_message,
                    )
                    denied_msg = {
                        "odia": "ଅନୁମତି ନାହିଁ। ଆଡମିନ୍ ଆକାଉଣ୍ଟ କେବଳ ନିଜ ସଂସ୍ଥାର ତଥ୍ୟ ଦେଖିପାରିବେ।",
                        "roman_odia": "Access denied. Admin accounts can only access telemetry and operational data for their assigned organisation.",
                        "hinglish": "Access denied. Admin accounts sirf apni assigned organisation ka telemetry data dekh sakte hain.",
                        "english": "Access denied. Admin accounts can only access telemetry and operational data for their assigned organisation.",
                    }.get(selected_language, "Access denied. Admin accounts can only access telemetry and operational data for their assigned organisation.")

                    return AIChatResponse(
                        reply=denied_msg,
                        language=selected_language,
                        detected_intent="cross_tenant_blocked",
                        context_used={"organisation_id": effective_org_id},
                    )

        # 4. Attempt Real Google Gemini GenAI Execution (when available)
        if gemini_service.is_available():
            is_ambiguous_metric = (
                intent in ("find_highest_block", "explain_anomaly_or_spike", "current_reading", "delta_from_baseline", "forecast_query")
                and not entities.get("explicit_metric")
                and not (request.context and request.context.module)
                and not (request.context and request.context.metric)
                and not last_metric
            )
            if not is_ambiguous_metric:
                gemini_tools = build_gemini_tools(
                    db=db,
                    effective_org_id=effective_org_id,
                    is_super_admin=is_super_admin,
                )
                context_hint = (
                    f"role={current_user.role}, "
                    f"scope={'PLATFORM' if (is_super_admin and is_platform_intent) else 'ORGANISATION'}, "
                    f"organisation_id={effective_org_id}, "
                    f"metric={target_metric}, "
                    f"block_id={target_block}"
                )
                history_list = (
                    [{"role": msg.role, "content": msg.content} for msg in request.session_history]
                    if request.session_history else None
                )

                try:
                    gemini_reply = gemini_service.generate_chat_response(
                        user_message=user_message,
                        target_language=selected_language,
                        tools=gemini_tools,
                        session_history=history_list,
                        context_hint=context_hint,
                    )
                except Exception as e:
                    logger.warning("Gemini invocation encountered exception: %s (falling back to NLU)", e)
                    gemini_reply = None

                if gemini_reply:
                    followups = GreenNexaNLU._generate_followups(
                        language=selected_language,
                        intent=intent,
                        metric=target_metric,
                        is_super_admin=is_super_admin,
                    )
                    if has_mismatch and mismatch_prefix:
                        gemini_reply = mismatch_prefix + gemini_reply

                    return AIChatResponse(
                        reply=gemini_reply,
                        language=selected_language,
                        detected_intent=intent,
                        data_source="Google Gemini 3.6 Flash (Real-time Telemetry Grounded)",
                        context_used={
                            "organisation_id": effective_org_id if not (is_super_admin and is_platform_intent) else None,
                            "scope": "PLATFORM" if (is_super_admin and is_platform_intent) else "ORGANISATION",
                            "metric": target_metric,
                            "block_id": target_block,
                            "role": current_user.role,
                        },
                        suggested_followups=followups,
                    )

        # 5. Fallback: Gather Data via Controlled Tool Layer
        tool_data: Dict[str, Any] = {}

        if is_super_admin:
            # Always ensure platform_summary is available for Super Admin
            tool_data["platform_summary"] = GreenNexaDataTools.get_platform_summary(db)

        if is_super_admin and is_platform_intent:
            tool_data["organisation_count"] = GreenNexaDataTools.get_total_organisations(db)
            tool_data["admin_count"] = GreenNexaDataTools.get_total_admins(db)
            tool_data["organisation_list"] = GreenNexaDataTools.get_organisation_list(db)
            tool_data["org_comparison"] = GreenNexaDataTools.compare_organisations(db, metric=target_metric)
            if target_facility_type:
                tool_data["facility_type_count"] = GreenNexaDataTools.count_organisations_by_facility_type(db, target_facility_type)
        elif effective_org_id:
            tool_data["organisation_summary"] = GreenNexaDataTools.get_organisation_summary(db, effective_org_id)
            tool_data["current_metric"] = GreenNexaDataTools.get_current_metric(db, effective_org_id, target_metric, target_block)
            tool_data["block_comparison"] = GreenNexaDataTools.get_block_comparison(db, effective_org_id, target_metric)
            tool_data["anomalies"] = GreenNexaDataTools.get_active_anomalies(db, effective_org_id, target_metric, target_block)
            tool_data["recommendations"] = GreenNexaDataTools.get_recommendations(db, effective_org_id, target_metric)
            if target_metric in ("energy", "water"):
                tool_data["forecast"] = GreenNexaDataTools.get_forecast(db, effective_org_id, target_metric)

            # Scenario Simulation Fallback
            if intent == "scenario_simulation":
                import re
                low_msg = user_message.lower()
                ac_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:ghanta|hours?|hr)", low_msg)
                ac_hours = float(ac_m.group(1)) if ac_m else (2.0 if "ac" in low_msg else 0.0)
                pct_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", low_msg)
                pct_val = float(pct_m.group(1)) if pct_m else (10.0 if "reduce" in low_msg or "kam" in low_msg else 0.0)
                temp_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:degree|celsius|°c)", low_msg)
                temp_val = float(temp_m.group(1)) if temp_m else 0.0

                if target_metric == "water":
                    tool_data["scenario_simulation"] = scenario_simulation_service.run_water_scenario(
                        db, effective_org_id, water_reduction_pct=pct_val or 10.0
                    )
                elif target_metric == "waste":
                    tool_data["scenario_simulation"] = scenario_simulation_service.run_waste_scenario(
                        db, effective_org_id, recycling_rate_increase_pct=pct_val or 15.0
                    )
                elif target_metric == "traffic":
                    tool_data["scenario_simulation"] = scenario_simulation_service.run_traffic_scenario(
                        db, effective_org_id, shuttle_frequency_increase_pct=pct_val or 20.0
                    )
                else:
                    tool_data["scenario_simulation"] = scenario_simulation_service.run_energy_scenario(
                        db,
                        effective_org_id,
                        ac_hours_reduced=ac_hours or 2.0,
                        thermostat_temp_increase_c=temp_val,
                        solar_offset_pct=pct_val if "solar" in low_msg else 0.0,
                    )

        # 6. Generate Response via Multilingual Engine
        reply, citation, followups = GreenNexaNLU.generate_response(
            language=selected_language,
            intent=intent,
            entities=entities,
            tool_data=tool_data,
            is_super_admin=is_super_admin,
        )

        if has_mismatch and mismatch_prefix:
            reply = mismatch_prefix + reply

        return AIChatResponse(
            reply=reply,
            language=selected_language,
            detected_intent=intent,
            data_source=citation,
            context_used={
                "organisation_id": effective_org_id if not (is_super_admin and is_platform_intent) else None,
                "scope": "PLATFORM" if (is_super_admin and is_platform_intent) else "ORGANISATION",
                "metric": target_metric,
                "block_id": target_block,
                "role": current_user.role,
            },
            suggested_followups=followups,
        )


assistant_service = AIAssistantService()

