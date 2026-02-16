"""Main honeypot agent implementation using Gemini 3 Pro."""

import asyncio
import hashlib
import json
import os
import random
import time
import uuid
from dataclasses import dataclass, field

import structlog
from google import genai
from google.genai import types
from pydantic import ValidationError

from config.settings import get_settings
from src.api.schemas import (
    AgentJsonResponse,
    ConversationMessage,
    ExtractedIntelligence,
    Message,
    Metadata,
    OtherIntelItem,
    SenderType,
)
from src.detection.detector import DetectionResult
from src.agents.prompts import HONEYPOT_SYSTEM_PROMPT
from src.agents.persona import PersonaManager, Persona
from src.agents.policy import EngagementPolicy, EngagementMode, EngagementState
from src.agents.fake_data import FakeDataGenerator, FakeCreditCard, FakeBankAccount, FakePersona

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


def _extract_text_from_response(response) -> str:
    """Extract text from Gemini response without triggering thought_signature warning.
    
    Gemini 3 models return 'thought_signature' parts alongside text parts.
    Using response.text triggers a warning. This function extracts only text parts.
    
    Args:
        response: The Gemini GenerateContentResponse object
        
    Returns:
        Concatenated text from all text parts
    """
    if not response.candidates:
        return ""
    
    text_parts = []
    for candidate in response.candidates:
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                # Only extract text parts, skip thought_signature and other non-text parts
                if hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)
    
    return "".join(text_parts)


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
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.settings.google_application_credentials
        
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
        self._fake_data_cache: dict[str, dict] = {}

    async def engage(
        self,
        message: Message,
        history: list[ConversationMessage],
        metadata: Metadata,
        detection: DetectionResult,
        conversation_id: str | None = None,
        turn_number: int | None = None,
        missing_intel: list[str] | None = None,
        extracted_intel: dict | None = None,
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
            message.text,
            extracted_intel.get("phishing_links", []) if extracted_intel else []
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

        # Generate notes with actual turn number (intelligence will be added in routes.py after merging)
        notes = self._generate_notes(detection, persona, engagement_mode, actual_turn, extracted_intel=None)

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

    def _get_fake_data(self, conversation_id: str) -> dict:
        """
        Get or generate fake data for a conversation.
        
        Uses conversation_id as seed to ensure consistent fake data
        across multiple turns of the same conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            Dictionary with all fake data for this conversation
        """
        if conversation_id in self._fake_data_cache:
            return self._fake_data_cache[conversation_id]
        
        # Create deterministic seed from conversation_id
        seed = int(hashlib.md5(conversation_id.encode()).hexdigest()[:8], 16)
        generator = FakeDataGenerator(seed=seed)
        
        # Generate all fake data upfront for consistency
        credit_card = generator.generate_credit_card()
        bank_account = generator.generate_bank_account()
        persona_details = generator.generate_persona_details()
        
        fake_data = {
            "credit_card": credit_card,
            "bank_account": bank_account,
            "persona": persona_details,
            "otp": generator.generate_otp(),
            "aadhaar": generator.generate_aadhaar(),
            "pan": generator.generate_pan(),
            # Pre-formatted strings for easy use in prompts
            "card_number_formatted": f"{credit_card.number[:4]} {credit_card.number[4:8]} {credit_card.number[8:12]} {credit_card.number[12:]}",
            "card_number_raw": credit_card.number,
            "card_expiry": credit_card.expiry,
            "card_cvv": credit_card.cvv,
            "account_number": bank_account.number,
            "ifsc_code": bank_account.ifsc,
            "bank_name": bank_account.bank_name,
            "persona_name": persona_details.name,
            "persona_age": persona_details.age,
            "persona_address": persona_details.address,
            "customer_id": persona_details.customer_id,
        }
        
        self._fake_data_cache[conversation_id] = fake_data
        self.logger.debug(
            "Generated fake data for conversation",
            conversation_id=conversation_id,
            card_type=credit_card.card_type,
            bank=bank_account.bank_name,
            persona=persona_details.name,
        )
        
        return fake_data
    
    def _format_fake_data_section(self, fake_data: dict) -> str:
        """
        Format fake data into a readable section for the prompt.
        
        Args:
            fake_data: Dictionary of fake data from _get_fake_data
            
        Returns:
            Formatted string for inclusion in system prompt
        """
        return f"""- Credit Card: {fake_data['card_number_formatted']} (type: {fake_data['credit_card'].card_type})
- Card Expiry: {fake_data['card_expiry']}
- Card CVV: {fake_data['card_cvv']}
- Bank Account: {fake_data['account_number']}
- IFSC Code: {fake_data['ifsc_code']} ({fake_data['bank_name']})
- OTP/Verification Code: {fake_data['otp']}
- Aadhaar Number: {fake_data['aadhaar']}
- PAN Card: {fake_data['pan']}
- Your Name: {fake_data['persona_name']}
- Your Age: {fake_data['persona_age']}
- Your Address: {fake_data['persona_address']}
- Customer ID: {fake_data['customer_id']}"""

    def _generate_conversation_summary(self, truncated_turns: list[ConversationMessage]) -> str:
        """Generate a concise summary of earlier conversation turns that were
        dropped due to context window limits.

        This preserves key intelligence and context so the agent doesn't
        repeat itself or lose track of what was discussed.

        Args:
            truncated_turns: The older turns that will NOT be included in
                             the full conversation history.

        Returns:
            A short natural-language summary (< 200 words).
        """
        if not truncated_turns:
            return ""

        import re as _re

        # Patterns to detect key intel in older messages
        PHONE_RE = _re.compile(r'\+?91[-\s]?\d{10}|\b\d{10}\b')
        UPI_RE = _re.compile(r'[\w.-]+@[a-zA-Z]{2,}')
        URL_RE = _re.compile(r'https?://[^\s]+', _re.IGNORECASE)
        EMAIL_RE = _re.compile(r'[\w.-]+@[\w.-]+\.\w{2,}')

        scammer_claims: list[str] = []
        agent_actions: list[str] = []
        intel_found: list[str] = []

        for msg in truncated_turns:
            text = msg.text
            sender = msg.sender

            is_scammer = (
                sender == SenderType.SCAMMER
                or (hasattr(sender, 'value') and sender.value == "scammer")
                or str(sender).lower() == "scammer"
            )

            if is_scammer:
                phones = PHONE_RE.findall(text)
                upis = UPI_RE.findall(text)
                urls = URL_RE.findall(text)
                emails = EMAIL_RE.findall(text)

                if phones:
                    intel_found.append(f"phone: {', '.join(phones)}")
                if upis:
                    intel_found.append(f"UPI: {', '.join(upis)}")
                if urls:
                    intel_found.append(f"link: {', '.join(urls)}")
                if emails:
                    intel_found.append(f"email: {', '.join(emails)}")

                gist = text[:80].strip()
                if len(text) > 80:
                    gist += "..."
                scammer_claims.append(gist)
            else:
                gist = text[:60].strip()
                if len(text) > 60:
                    gist += "..."
                agent_actions.append(gist)

        parts: list[str] = []
        parts.append(f"[SUMMARY OF EARLIER {len(truncated_turns)} MESSAGES]")

        if scammer_claims:
            parts.append("Scammer said: " + " | ".join(scammer_claims[:4]))

        if agent_actions:
            parts.append("You replied: " + " | ".join(agent_actions[:3]))

        if intel_found:
            parts.append("Intel found in earlier turns: " + "; ".join(set(intel_found)))

        summary = "\n".join(parts)

        # Enforce word budget
        words = summary.split()
        if len(words) > 200:
            summary = " ".join(words[:200]) + "..."

        return summary

    def _build_prompt(
        self,
        message: Message,
        history: list[ConversationMessage],
        detection: DetectionResult,
        persona: Persona,
        missing_intel: list[str] | None = None,
        extracted_intel: dict | None = None,
        fake_data: dict | None = None,
    ) -> str:
        """Build conversation prompt for Gemini - simplified for agentic prompts."""
        # Limit context to last N turns to reduce latency on deep conversations
        max_turns = self.settings.context_window_turns

        # If history exceeds context window, generate summary of older turns
        summary_text = ""
        if len(history) > max_turns:
            older_turns = history[:-max_turns]
            summary_text = self._generate_conversation_summary(older_turns)
            truncated_history = history[-max_turns:]
        else:
            truncated_history = history

        # Format conversation history
        history_text = ""
        for msg in truncated_history:
            sender = "SCAMMER" if msg.sender == SenderType.SCAMMER else "YOU"
            history_text += f"[{sender}]: {msg.text}\n"

        # Build prompt with optional summary
        if summary_text:
            prompt = f"""{summary_text}

RECENT CONVERSATION HISTORY:
{history_text}

SCAMMER'S NEW MESSAGE:
"{message.text}"

Generate your response as Pushpa Verma:"""
        else:
            prompt = f"""CONVERSATION HISTORY:
{history_text if history_text else "No previous messages"}

SCAMMER'S NEW MESSAGE:
"{message.text}"

Generate your response as Pushpa Verma:"""

        return prompt

    @staticmethod
    def _extract_json_text(raw: str) -> str:
        """Strip markdown code fences and return inner text."""
        text = raw.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _parse_agent_json_response(self, response_text: str) -> AgentJsonResponse | None:
        """Parse the JSON response from the agent. Returns None if parsing fails.

        Handles common LLM quirks:
        - ``other_critical_info`` returned as list[str] instead of list[dict]
        - Markdown code fences around JSON
        """
        try:
            text = self._extract_json_text(response_text)
            data = json.loads(text)

            # Normalise other_critical_info: convert bare strings → OtherIntelItem dicts
            intel = data.get("extracted_intelligence", {})
            raw_other = intel.get("other_critical_info", [])
            if raw_other and isinstance(raw_other[0], str):
                intel["other_critical_info"] = [
                    {"label": "info", "value": v} for v in raw_other
                ]
                data["extracted_intelligence"] = intel

            return AgentJsonResponse(**data)
        except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as e:
            self.logger.warning(f"Failed to parse agent JSON response: {e}")
            return None

    async def _generate_response(
        self,
        prompt: str,
        persona: Persona,
        fake_data_section: str = "",
        extracted_intel: dict | None = None,
        missing_intel: list[str] | None = None,
    ) -> tuple[str, ExtractedIntelligence | None]:
        """Generate response using Gemini Pro with fallback to Gemini 2.5.
        
        Returns:
            Tuple of (response_text, extracted_intelligence)
        """
        
        # Format extracted intelligence as JSON for the prompt
        extracted_intel = extracted_intel or {}
        extracted_intel_json = json.dumps(extracted_intel, indent=2) if extracted_intel else "None yet"
        
        # Format missing intelligence as a readable list
        missing_intel = missing_intel or []
        missing_intel_text = ", ".join(missing_intel) if missing_intel else "All intelligence collected!"
        
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
                    
                    # Gemini 3 Pro needs higher max_output_tokens because its
                    # internal "thinking" consumes output tokens. 256 is too small
                    # and causes MAX_TOKENS finish reason with empty text.
                    # Thinking level is HIGH by default in Gemini 3
                    max_tokens = 65536
                    
                    # Build config with model-specific settings
                    config = types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=self.settings.llm_temperature,
                        max_output_tokens=max_tokens,
                        safety_settings=HONEYPOT_SAFETY_SETTINGS,
                    )
                    
                    # Wrap API call with timeout
                    response = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: self.client.models.generate_content(
                                model=model_name,
                                contents=prompt,
                                config=config,
                            )
                        ),
                        timeout=timeout_seconds,
                    )
                    
                    # Use helper to avoid thought_signature warning in Gemini 3
                    response_text = _extract_text_from_response(response)
                    
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
                        
                except asyncio.TimeoutError:
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
            return self._get_fallback_response(None), None

        # Try to parse as JSON (One-Pass JSON architecture)
        parsed = self._parse_agent_json_response(response_text)
        if parsed:
            self.logger.info(
                "Successfully parsed JSON response from agent",
                emotional_tone=parsed.emotional_tone,
                intel_found=bool(
                    parsed.extracted_intelligence.bankAccounts or
                    parsed.extracted_intelligence.upiIds or
                    parsed.extracted_intelligence.phoneNumbers or
                    parsed.extracted_intelligence.phishingLinks
                )
            )
            return parsed.reply_text, parsed.extracted_intelligence
        
        # Safety net: full Pydantic parse failed, but if the text looks like JSON
        # try to at least extract reply_text so we never return raw JSON as the reply.
        try:
            raw_json = json.loads(self._extract_json_text(response_text))
            if isinstance(raw_json, dict) and "reply_text" in raw_json:
                reply = raw_json["reply_text"]
                self.logger.info("Extracted reply_text from partially-valid JSON")
                # Also try to salvage intelligence even without full validation
                intel_dict = raw_json.get("extracted_intelligence")
                salvaged_intel = None
                if isinstance(intel_dict, dict):
                    try:
                        # Normalise other_critical_info strings → dicts
                        raw_other = intel_dict.get("other_critical_info", [])
                        if raw_other and isinstance(raw_other[0], str):
                            intel_dict["other_critical_info"] = [
                                {"label": "info", "value": v} for v in raw_other
                            ]
                        salvaged_intel = ExtractedIntelligence(**intel_dict)
                    except Exception:
                        pass  # skip intel if it can't be parsed
                return reply, salvaged_intel
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        # Fallback: return raw response if JSON parsing fails
        self.logger.debug("Using raw response (JSON parsing failed)")
        return response_text, None

    def _get_fallback_response(self, detection: DetectionResult) -> str:
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
        """Generate agent notes summarizing the engagement."""
        notes_parts = []

        # Engagement mode
        notes_parts.append(f"Mode: {mode.value}")

        # Scam type if detected
        if detection.scam_type:
            notes_parts.append(f"Type: {detection.scam_type}")

        # Confidence
        notes_parts.append(f"Confidence: {detection.confidence:.0%}")

        # Engagement progress - use the actual turn number passed in
        notes_parts.append(f"Turn: {turn_number}")

        # Emotional state
        notes_parts.append(f"Persona: {persona.emotional_state.value}")
        
        # Add intelligence extraction counts (only from scammer messages)
        if extracted_intel:
            intel_counts = []
            if extracted_intel.bankAccounts:
                intel_counts.append(f"{len(extracted_intel.bankAccounts)} Bank Account(s)")
            if extracted_intel.upiIds:
                intel_counts.append(f"{len(extracted_intel.upiIds)} UPI ID(s)")
            if extracted_intel.phoneNumbers:
                intel_counts.append(f"{len(extracted_intel.phoneNumbers)} Phone(s)")
            if extracted_intel.phishingLinks:
                intel_counts.append(f"{len(extracted_intel.phishingLinks)} URL(s)")
            if extracted_intel.emailAddresses:
                intel_counts.append(f"{len(extracted_intel.emailAddresses)} Email(s)")
            if extracted_intel.ifscCodes:
                intel_counts.append(f"{len(extracted_intel.ifscCodes)} IFSC Code(s)")
            if extracted_intel.whatsappNumbers:
                intel_counts.append(f"{len(extracted_intel.whatsappNumbers)} WhatsApp(s)")
            if extracted_intel.beneficiaryNames:
                intel_counts.append(f"{len(extracted_intel.beneficiaryNames)} Name(s)")
            if extracted_intel.other_critical_info:
                intel_counts.append(f"{len(extracted_intel.other_critical_info)} Other Intel")
            
            if intel_counts:
                notes_parts.append(f"Extracted: {', '.join(intel_counts)}")

        return " | ".join(notes_parts)
    
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
                    message_preview=message_text[:100]
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
