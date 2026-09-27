"""
GreenNexa AI Assistant API Router.

Routes:
  POST /api/v1/ai/chat        — Execute AI assistant chat request with backend RBAC & data scoping
  GET  /api/v1/ai/suggestions — Get dynamic starter prompt suggestions based on role and screen context
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.assistant.schemas import AIChatRequest, AIChatResponse, AISuggestionsResponse
from app.ai.assistant.service import assistant_service
from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["GreenNexa AI Assistant"])


@router.post(
    "/chat",
    response_model=AIChatResponse,
    summary="Chat with GreenNexa AI Assistant",
    description=(
        "Send a natural-language query (English, Hinglish, or Roman Odia + English mixed) "
        "to the GreenNexa AI Assistant. Enforces strict backend data isolation and role boundaries."
    ),
)
def chat_with_assistant(
    body: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIChatResponse:
    """
    Process AI chat query with role-based scoping and real telemetry data grounding.
    """
    try:
        return assistant_service.process_chat(db=db, current_user=current_user, request=body)
    except Exception as e:
        logger.exception("Error processing AI assistant chat: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your AI request. Please try again.",
        )


@router.get(
    "/suggestions",
    response_model=AISuggestionsResponse,
    summary="Get contextual AI prompt suggestions",
)
def get_ai_suggestions(
    module: Optional[str] = Query(None, description="Current dashboard module (e.g. energy, water, waste)"),
    block_id: Optional[str] = Query(None, description="Currently selected block ID or block name"),
    current_user: User = Depends(get_current_user),
) -> AISuggestionsResponse:
    """
    Return quick prompt suggestions tailored to user role and active dashboard context.
    """
    suggestions: List[str] = []

    if current_user.role == User.ROLE_SUPER_ADMIN:
        suggestions = [
            "Which organisations currently have critical anomalies?",
            "Compare water usage across organisations.",
            "Show platform-wide telemetry & health overview.",
            "Which organisation has the highest energy anomaly count?",
        ]
    else:
        mod_clean = (module or "").lower().strip()
        loc_str = f" in {block_id}" if block_id else ""

        if mod_clean == "water":
            suggestions = [
                f"Why is water consumption high{loc_str}?",
                f"Aaj {block_id or 'Block C'} re water usage kete badhichi?",
                "What is the 24h water forecast?",
                "What actions are recommended for water conservation?",
            ]
        elif mod_clean == "energy":
            suggestions = [
                f"Which block has the highest energy usage?",
                f"Mo organisation re sabuthu besi energy usage keun block re achhi?",
                "How much higher is energy usage than baseline?",
                "Explain today's critical energy anomalies.",
            ]
        elif mod_clean == "waste":
            suggestions = [
                f"Which block has reached critical waste capacity?",
                "Show active waste management recommendations.",
                "Energy usage aji kete?",
            ]
        else:
            suggestions = [
                "Can you explain today's critical anomalies?",
                "Which block has the highest water usage?",
                "Aaj Block C re water usage kete badhichi?",
                "Show active sustainability recommendations.",
            ]

    return AISuggestionsResponse(
        role=current_user.role,
        scope=current_user.organisation_id or "PLATFORM_GLOBAL",
        suggestions=suggestions,
    )
