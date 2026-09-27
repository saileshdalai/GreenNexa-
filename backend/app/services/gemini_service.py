"""
GreenNexa — Official Google Gemini API Service.

Integrates the official google-genai SDK (gemini-3.6-flash) with
automatic function calling, strict tenant isolation, multilingual synthesis,
and robust graceful fallbacks.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
]

SYSTEM_INSTRUCTION = """
You are the GreenNexa Facility Intelligence AI Assistant, an AI-powered decision partner
for government and institutional estates across India (colleges, universities, hospitals,
corporate tech parks, public-sector units, and municipal facilities).

CRITICAL OPERATIONAL RULES:
1. TRUTHFUL DATA GROUNDING:
   All quantitative values, telemetry readings, baselines, anomaly counts, and forecasts
   MUST be obtained from the provided GreenNexa tools. NEVER invent or hallucinate sensor
   readings, block names, or numerical percentages.

2. MULTILINGUAL RESPONSES:
   Always respond in the specific language requested by the conversation setting or user message:
   - English: Clear, professional, actionable facility management language.
   - Hinglish: Conversational Hindi-English blend (e.g. "Energy consumption baseline se 15% zyada hai").
   - Odia (Unicode Script): Authentic Odia in Odia script (ଓଡ଼ିଆ), e.g. "ବ୍ଲକ C ରେ ଶକ୍ତି ବ୍ୟବହାର ସର୍ବାଧିକ ଅଛି।"
   - Roman Odia: Conversational Romanized Odia (e.g. "Aaji Block C re water usage 890 L achhi, jaha baseline ru besi achhi.").

3. WHAT-IF SCENARIOS:
   When the user asks hypothetical or operational adjustment questions (e.g., "AC 2 ghanta kam chalile energy kete heba?",
   "What if we reduce water usage by 10%?", "Agar thermostat 2 degree badhayein toh kitni bachat hogi?"):
   - Call the corresponding scenario tool (run_energy_scenario, run_water_scenario, run_waste_scenario, run_traffic_scenario).
   - Report the simulated baseline, projected consumption, net savings (kWh/Liters/kg), cost savings in ₹ INR, and CO2 avoided.
   - Transparently list the key assumptions returned by the tool.
   - Always label the projection as a "[Modelled Scenario Estimate]".

4. DECISION-SUPPORT FRAMING:
   Present recommendations and forecasts as decision-support guidance for facility engineers,
   not official regulatory compliance measurements.

5. TOOL CALLING EFFICIENCY:
   Call ONLY the single most direct and relevant tool needed to answer the user question.
   Once you receive the tool output, provide your final response immediately. Do not call multiple redundant tools.
"""


class GeminiAssistantService:
    """
    Dedicated service for interacting with Google Gemini API via official google-genai SDK.
    """

    def __init__(self) -> None:
        self._api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self._client: Optional[genai.Client] = None
        if self._api_key:
            try:
                self._client = genai.Client(
                    api_key=self._api_key,
                    http_options=types.HttpOptions(
                        timeout=15000,
                        retry_options=types.HttpRetryOptions(attempts=1),
                    ),
                )
                masked_key = self._api_key[:6] + "..." + self._api_key[-4:] if len(self._api_key) > 10 else "***"
                logger.info("GeminiAssistantService initialized successfully with key %s", masked_key)
            except Exception as e:
                logger.warning("Failed to initialize Google GenAI client: %s", e)
                self._client = None

    def is_available(self) -> bool:
        """Return True if Gemini client is successfully initialized with a valid key."""
        return self._client is not None and bool(self._api_key)

    def generate_chat_response(
        self,
        user_message: str,
        target_language: str,
        tools: List[Callable[..., Any]],
        session_history: Optional[List[Dict[str, str]]] = None,
        context_hint: Optional[str] = None,
    ) -> Optional[str]:
        """
        Execute chat interaction using candidate Gemini models with automatic tool calling.
        Returns the natural language reply string or None on failure to trigger fallback.
        """
        if not self.is_available() or not self._client:
            logger.debug("GeminiAssistantService unavailable; proceeding to fallback.")
            return None

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
            tools=tools,
        )

        # Build user prompt with language constraint and optional dashboard context
        prompt_parts: List[str] = []
        if target_language:
            prompt_parts.append(f"[Requested Language: {target_language}]")
        if context_hint:
            prompt_parts.append(f"[Dashboard Context: {context_hint}]")
        if session_history:
            prompt_parts.append("[Previous Conversation Context:]")
            for msg in session_history[-4:]:
                prompt_parts.append(f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}")
        prompt_parts.append(f"User Query: {user_message}")

        full_prompt = "\n".join(prompt_parts)

        # Try candidate models in cascade
        for model_name in CANDIDATE_MODELS:
            try:
                chat = self._client.chats.create(
                    model=model_name,
                    config=config,
                )
                response = chat.send_message(full_prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                err_msg = str(e)
                if self._api_key and self._api_key in err_msg:
                    err_msg = err_msg.replace(self._api_key, "[REDACTED_API_KEY]")
                logger.warning("Gemini model %s failed: %s (attempting next candidate)", model_name, err_msg[:120])
                continue

        logger.warning("All candidate Gemini models failed or exhausted quota; proceeding to fallback.")
        return None


gemini_service = GeminiAssistantService()
