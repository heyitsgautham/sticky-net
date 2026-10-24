"""Main honeypot agent implementation using Gemini 3 Pro."""

import asyncio
import functools
import json
import os
import random
import time
import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from google import genai
from google.genai import types

from config.settings import get_settings
from src import llm
from src.agents.conversation import (
    build_turn_prompt,
    engagement_notes,
    summarize_earlier_turns,
)
from src.agents.fake_profile import build_fake_profile, format_fake_profile
from src.agents.persona import Persona, PersonaManager
from src.agents.policy import EngagementMode, EngagementPolicy, EngagementState
from src.agents.prompts import HONEYPOT_SYSTEM_PROMPT
from src.agents.reply_parser import parse_agent_reply
from src.api.schemas import (
    ConversationMessage,
    ExtractedIntelligence,
    Message,
    Metadata,
)
from src.detection.detector import DetectionResult

# Safety settings for Gemini to allow scam roleplay (for honeypot context)
# Using BLOCK_NONE for Gemini 3 Preview models which have stricter default filters
HONEYPOT_SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
]

logger = structlog.get_logger()


@dataclass
class EngagementResult:
    """Result of agent engagement."""

    response: str
    duration_seconds: int
    notes: str
    conversation_id: str
    turn_number: int
    engagement_mode: EngagementMode
    should_continue: bool
    exit_reason: str | None = None
    extracted_intelligence: ExtractedIntelligence | None = None


class HoneypotAgent:
    """
    AI agent that engages scammers while maintaining a believable human persona.

    Uses Google Gemini 3 Pro with fallback to Gemini 2.5 Pro for sophisticated,
    natural conversation generation.
    """

    def __init__(self) -> None:
        """Initialize the honeypot agent."""
        self.settings = get_settings()
        self.logger = logger.bind(component="HoneypotAgent")
        self.persona_manager = PersonaManager()
        self.policy = EngagementPolicy()

        # Set credentials path in environment if configured
        if self.settings.google_application_credentials:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                self.settings.google_application_credentials
            )

        # Initialize Gemini client with Vertex AI credentials from settings
        self.client = genai.Client(
            vertexai=self.settings.google_genai_use_vertexai,
            project=self.settings.google_cloud_project,
            location=self.settings.google_cloud_location,
        )

        # Primary model (Gemini 3 Pro) and fallback (Gemini 2.5 Pro)
        self.model = self.settings.pro_model  # gemini-3-pro-preview
        self.fallback_model = self.settings.fallback_pro_model  # gemini-2.5-pro
        self._last_model_used: str | None = None  # Track which model was used

        # Fake data generators per conversation (seeded by conversation_id)
        self._fake_data_cache: dict[str, dict[str, Any]] = {}

    async def engage(
        self,
        message: Message,
        history: list[ConversationMessage],
        metadata: Metadata,
        detection: DetectionResult,
        conversation_id: str | None = None,
        turn_number: int | None = None,
        missing_intel: list[str] | None = None,
        extracted_intel: dict[str, list[str]] | None = None,
    ) -> EngagementResult:
        """
        Engage with the scammer and generate a response.

        Args:
            message: The current scammer message
            history: Previous conversation messages
            metadata: Message metadata
            detection: Scam detection result
            conversation_id: Optional existing conversation ID
            turn_number: Optional turn number override (calculated from history length)

        Returns:
            EngagementResult with the agent's response
        """
        start_time = time.time()

        # Generate or use existing conversation ID
        conv_id = conversation_id or str(uuid.uuid4())

        # Calculate the actual turn number
        # If turn_number is provided, use it; otherwise calculate from history
        actual_turn = turn_number if turn_number is not None else len(history) + 1

        self.logger.info(
            "Engaging with scammer",
            conversation_id=conv_id,
            history_length=len(history),
            confidence=detection.confidence,
            turn=actual_turn,
        )

        # Determine engagement mode
        engagement_mode = self.policy.get_engagement_mode(detection.confidence)

        # Get/update persona state with scam_type for context-aware emotions
        persona = self.persona_manager.update_persona(
            conv_id,
            scam_intensity=detection.confidence,
            scam_type=detection.scam_type,
        )
        # Override persona's internal turn with actual calculated turn
        persona.engagement_turn = actual_turn

        # Get fake data for this conversation (consistent across turns)
        fake_data = self._get_fake_data(conv_id)

        # Build conversation prompt for Gemini
        prompt = self._build_prompt(
            message=message,
            history=history,
            detection=detection,
            persona=persona,
            missing_intel=missing_intel or [],
            extracted_intel=extracted_intel or {},
            fake_data=fake_data,
        )

        # Generate response using Gemini 3 Pro
        fake_data_section = self._format_fake_data_section(fake_data)
        llm_extracted_intel: ExtractedIntelligence | None = None
        try:
            response, llm_extracted_intel = await self._generate_response(
                prompt,
                persona,
                fake_data_section,
                extracted_intel=extracted_intel,
                missing_intel=missing_intel,
            )
        except Exception as e:
            self.logger.error("Failed to generate response", error=str(e))
            response = self._get_fallback_response(detection)

        # Calculate duration
        duration = int(time.time() - start_time)

        # Check if scammer's message contains URLs that weren't extracted yet
        has_unextracted_urls = self._has_unextracted_urls(
            message.text, extracted_intel.get("phishing_links", []) if extracted_intel else []
        )

        # Check if engagement should continue
        state = EngagementState(
            mode=engagement_mode,
            turn_count=actual_turn,
            duration_seconds=duration,
            intelligence_complete=False,  # Set by intelligence extractor
            scammer_suspicious=False,  # Detect from response patterns
            turns_since_new_info=0,  # Track over time
            has_unextracted_urls=has_unextracted_urls,
        )
        should_continue = self.policy.should_continue(state)
        exit_reason = self.policy.get_exit_reason(state) if not should_continue else None

        # Generate notes with the actual turn number.
        # routes.py adds intelligence after merging the LLM and regex results.
        notes = self._generate_notes(
            detection, persona, engagement_mode, actual_turn, extracted_intel=None
        )

        return EngagementResult(
            response=response,
            duration_seconds=duration,
            notes=notes,
            conversation_id=conv_id,
            turn_number=actual_turn,
            engagement_mode=engagement_mode,
            should_continue=should_continue,
            exit_reason=exit_reason,
            extracted_intelligence=llm_extracted_intel,
        )

    def _get_fake_data(self, conversation_id: str) -> dict[str, Any]:
        """Return this conversation's fake profile, generating it on first use."""
        if conversation_id not in self._fake_data_cache:
            self._fake_data_cache[conversation_id] = build_fake_profile(conversation_id)
            self.logger.debug("Generated fake data", conversation_id=conversation_id)
        return self._fake_data_cache[conversation_id]

    def _format_fake_data_section(self, fake_data: dict[str, Any]) -> str:
        """Render the fake profile for the system prompt."""
        return format_fake_profile(fake_data)

    def _generate_conversation_summary(self, truncated_turns: list[ConversationMessage]) -> str:
        """Summarise turns that fell out of the context window."""
        return summarize_earlier_turns(truncated_turns)

    def _build_prompt(
        self,
        message: Message,
        history: list[ConversationMessage],
        detection: DetectionResult,
        persona: Persona,
        missing_intel: list[str] | None = None,
        extracted_intel: dict[str, list[str]] | None = None,
        fake_data: dict[str, Any] | None = None,
    ) -> str:
        """Build the turn prompt from the last context_window_turns messages."""
        return build_turn_prompt(message, history, self.settings.context_window_turns)

    async def _generate_response(
        self,
        prompt: str,
        persona: Persona,
        fake_data_section: str = "",
        extracted_intel: dict[str, list[str]] | None = None,
        missing_intel: list[str] | None = None,
    ) -> tuple[str, ExtractedIntelligence | None]:
        """Generate response using Gemini Pro with fallback to Gemini 2.5.

        Returns:
            Tuple of (response_text, extracted_intelligence)
        """

        # Format extracted intelligence as JSON for the prompt
        extracted_intel = extracted_intel or {}
        extracted_intel_json = (
            json.dumps(extracted_intel, indent=2) if extracted_intel else "None yet"
        )

        # Format missing intelligence as a readable list
        missing_intel = missing_intel or []
        missing_intel_text = (
            ", ".join(missing_intel) if missing_intel else "All intelligence collected!"
        )

        # Format system instruction with state injection
        system_instruction = HONEYPOT_SYSTEM_PROMPT.format(
            turn_number=persona.engagement_turn,
            extracted_intelligence=extracted_intel_json,
            missing_intelligence=missing_intel_text,
            fake_data_section=fake_data_section or "(No fake data available)",
        )

        # Try primary model (Gemini 3 Pro) first, then fallback (Gemini 2.5 Pro)
        models_to_try = [self.model, self.fallback_model]
        response_text = None
        timeout_seconds = self.settings.api_timeout_seconds
        max_retries = self.settings.gemini_max_retries
        retry_delay = self.settings.gemini_retry_delay_seconds

        for model_name in models_to_try:
            # Retry loop for timeout handling
            for attempt in range(max_retries + 1):
                try:
                    self.logger.debug(
                        f"Trying model: {model_name}",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        timeout=timeout_seconds,
                    )

                    # thinking_budget=0 = disable thinking to minimize latency.
                    # The prompt + missing_intel injection provides clear targeting
                    # without model needing to reason. Keeps responses under 20s.
                    max_tokens = 2048

                    # Build config with model-specific settings
                    config = types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=self.settings.llm_temperature,
                        max_output_tokens=max_tokens,
                        safety_settings=HONEYPOT_SAFETY_SETTINGS,
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=0,
                        ),
                    )

                    # Wrap API call with timeout
                    response = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            functools.partial(
                                self.client.models.generate_content,
                                model=model_name,
                                contents=prompt,
                                config=config,
                            ),
                        ),
                        timeout=timeout_seconds,
                    )

                    # Use helper to avoid thought_signature warning in Gemini 3
                    response_text = llm.response_text(response)

                    # Check if we got a valid response
                    if response_text and len(response_text.strip()) > 0:
                        self._last_model_used = model_name
                        self.logger.info(
                            "Response generated successfully",
                            model=model_name,
                            response_length=len(response_text),
                            attempt=attempt + 1,
                        )
                        break
                    else:
                        self.logger.warning(
                            "Empty response from model, trying fallback",
                            model=model_name,
                        )
                        break  # Don't retry on empty response, try fallback model

                except TimeoutError:
                    self.logger.warning(
                        "Gemini API timeout",
                        model=model_name,
                        attempt=attempt + 1,
                        timeout_seconds=timeout_seconds,
                    )
                    if attempt < max_retries:
                        self.logger.info(
                            f"Retrying after {retry_delay}s delay",
                            remaining_retries=max_retries - attempt,
                        )
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        self.logger.error(
                            "Max retries exceeded for model",
                            model=model_name,
                        )
                        break  # Try fallback model

                except Exception as e:
                    self.logger.warning(
                        "Model failed, trying fallback",
                        model=model_name,
                        error=str(e),
                    )
                    break  # Don't retry on other errors, try fallback model

            # If we got a valid response, break out of model loop
            if response_text and len(response_text.strip()) > 0:
                break

        # Handle None response - use fallback response
        if not response_text:
            self._last_model_used = "fallback"
            return self._get_fallback_response(), None

        # One-Pass JSON architecture: the reply and the intel come back together
        return parse_agent_reply(response_text)

    def _get_fallback_response(self, detection: DetectionResult | None = None) -> str:
        """Get a fallback response if LLM fails."""
        fallback_responses = [
            "I'm sorry, I'm a bit confused. Can you explain that again?",
            "My phone is acting up. What do I need to do exactly?",
            "I didn't understand. Can you tell me step by step?",
            "Okay, but what should I do first? I'm worried.",
        ]
        return random.choice(fallback_responses)

    def _generate_notes(
        self,
        detection: DetectionResult,
        persona: Persona,
        mode: EngagementMode,
        turn_number: int,
        extracted_intel: ExtractedIntelligence | None = None,
    ) -> str:
        """One-line summary of the engagement for the callback and dashboard."""
        return engagement_notes(detection, persona, mode, turn_number, extracted_intel)

    def _has_unextracted_urls(self, message_text: str, extracted_urls: list[str]) -> bool:
        """
        Check if message contains URLs that haven't been extracted yet.

        Args:
            message_text: The scammer's message text
            extracted_urls: List of URLs already extracted

        Returns:
            True if message contains unextracted URLs
        """
        import re

        # Same pattern as extractor uses
        URL_PATTERN = re.compile(
            r"https?://[\w.-]+(?:\.[a-z]{2,10})+(?:/[^\s<>\"'{}|\\^`\[\]]*)?",
            re.IGNORECASE,
        )

        # Find all URLs in the message
        urls_in_message = URL_PATTERN.findall(message_text)

        if not urls_in_message:
            return False

        # Check if any URLs are new (not in extracted_urls)
        extracted_set = set(url.rstrip(".,;:!?)") for url in extracted_urls)
        for url in urls_in_message:
            clean_url = url.rstrip(".,;:!?)")
            if clean_url not in extracted_set:
                self.logger.info(
                    "Detected unextracted URL in message",
                    url=clean_url,
                    message_preview=message_text[:100],
                )
                return True

        return False

    def end_conversation(self, conversation_id: str) -> None:
        """Clean up persona and fake data when conversation ends."""
        self.persona_manager.clear_persona(conversation_id)
        # Clear fake data cache for this conversation
        if conversation_id in self._fake_data_cache:
            del self._fake_data_cache[conversation_id]


# Singleton instance for reuse
_agent_instance: HoneypotAgent | None = None


def get_agent() -> HoneypotAgent:
    """Get or create the honeypot agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = HoneypotAgent()
    return _agent_instance
