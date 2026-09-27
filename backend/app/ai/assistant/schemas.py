"""
GreenNexa AI Assistant — Pydantic Schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' | 'assistant'")
    content: str = Field(..., description="Message text content")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")


class AIContextData(BaseModel):
    module: Optional[str] = Field(None, description="Current dashboard module (e.g. energy, water, waste)")
    block_id: Optional[str] = Field(None, description="Currently selected block ID or block name")
    organisation_id: Optional[str] = Field(None, description="Organisation ID (for SUPER_ADMIN only)")
    metric: Optional[str] = Field(None, description="Specific sensor metric if focused")


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User question or prompt")
    conversation_language: Optional[str] = Field(default="english", description="'english' | 'hinglish' | 'odia' | 'roman_odia'")
    context: Optional[AIContextData] = Field(default=None, description="Active dashboard context")
    session_history: Optional[List[ChatMessage]] = Field(default=None, description="Recent conversation turns")


class AIChatResponse(BaseModel):
    reply: str = Field(..., description="Assistant text response")
    language: str = Field(default="english", description="Detected input language: 'english' | 'hinglish' | 'roman_odia'")
    detected_intent: str = Field(default="general_query", description="Classified intent")
    data_source: Optional[str] = Field(None, description="Telemetry data basis citation")
    context_used: Optional[Dict[str, Any]] = Field(None, description="Resolved context dictionary")
    suggested_followups: List[str] = Field(default_factory=list, description="Contextual quick follow-up queries")


class AISuggestionsResponse(BaseModel):
    role: str
    scope: str
    suggestions: List[str]
