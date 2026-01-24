"""Main honeypot agent implementation using Gemini 3 Pro."""

import hashlib
import os
import random
import time
import uuid
from dataclasses import dataclass

import structlog
from google import genai
from google.genai import types

from config.settings import get_settings
from src.api.schemas import ConversationMessage, Message, Metadata, SenderType
from src.detection.detector import DetectionResult
from src.agents.prompts import (
    HONEYPOT_SYSTEM_PROMPT,
    EXTRACTION_QUESTIONS,
    BENEFICIARY_EXTRACTION_STRATEGIES,
    MISSING_INTEL_PROMPTS,
    format_scam_indicators,
)
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

        # Get/update persona state
        persona = self.persona_manager.update_persona(
            conv_id,
            scam_intensity=detection.confidence,
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
        try:
            response = await self._generate_response(prompt, persona, fake_data_section)
        except Exception as e:
            self.logger.error("Failed to generate response", error=str(e))
            response = self._get_fallback_response(detection)

        # Calculate duration
        duration = int(time.time() - start_time)

        # Check if engagement should continue
        state = EngagementState(
            mode=engagement_mode,
            turn_count=actual_turn,
            duration_seconds=duration,
            intelligence_complete=False,  # Set by intelligence extractor
            scammer_suspicious=False,  # Detect from response patterns
            turns_since_new_info=0,  # Track over time
        )
        should_continue = self.policy.should_continue(state)
        exit_reason = self.policy.get_exit_reason(state) if not should_continue else None

        # Generate notes with actual turn number
        notes = self._generate_notes(detection, persona, engagement_mode, actual_turn)

        return EngagementResult(
            response=response,
            duration_seconds=duration,
            notes=notes,
            conversation_id=conv_id,
            turn_number=actual_turn,
            engagement_mode=engagement_mode,
            should_continue=should_continue,
            exit_reason=exit_reason,
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
        """Build conversation prompt for Gemini with targeted extraction directives."""
        # Format scam indicators
        scam_indicators = [m.description for m in detection.matched_patterns[:5]]
        indicators_text = format_scam_indicators(scam_indicators) if scam_indicators else "General suspicious behavior"

        # Format conversation history
        history_text = ""
        for msg in history[-10:]:  # Last 10 messages for context
            sender = "SCAMMER" if msg.sender == SenderType.SCAMMER else "YOU"
            history_text += f"[{sender}]: {msg.text}\n"

        # Build targeted extraction directive based on what's missing
        extraction_directive = self._build_extraction_directive(
            missing_intel or [],
            extracted_intel or {},
        )

        prompt = f"""CONVERSATION HISTORY:
{history_text if history_text else "No previous messages"}

SCAMMER'S NEW MESSAGE:
"{message.text}"

YOUR TASK:
Generate a response as the naive, trusting victim. Your emotional state is: {persona.emotional_state.value}
This is turn {persona.engagement_turn} of the conversation.

Remember:
- Stay in character as a confused, worried person
- Ask questions that extract intelligence (bank accounts, UPI IDs, links)
- Keep responses short (1-3 sentences)
- Show willingness to comply but need guidance

DETECTED SCAM INDICATORS: {indicators_text}

{extraction_directive}

Generate your response:"""

        return prompt

    def _build_extraction_directive(
        self,
        missing_intel: list[str],
        extracted_intel: dict,
    ) -> str:
        """Build a targeted extraction directive based on what intelligence is missing."""
        if not missing_intel:
            return ""

        directives = []
        
        # Get extracted values for reference in prompts
        upi_ids = extracted_intel.get("upi_ids", [])
        bank_accounts = extracted_intel.get("bank_accounts", [])
        
        # Priority 1: Beneficiary name (CRITICAL for mule identification)
        if "beneficiary_name" in missing_intel:
            if upi_ids:
                # We have UPI but no name - use validation attack
                upi = upi_ids[0]
                example = random.choice(BENEFICIARY_EXTRACTION_STRATEGIES["upi_validation"])
                example = example.format(upi_id=upi)
                directives.append(f"""
**CRITICAL EXTRACTION TARGET: BENEFICIARY NAME**
You have the UPI ID "{upi}" but NOT the account holder's name. 
This is the MOST IMPORTANT piece of intelligence to extract.
Use the "validation attack" - pretend you're entering the UPI and need to verify the name.
Example approach: "{example}"
DO NOT exit or end the conversation until you get the name!""")
            elif bank_accounts:
                # We have bank account but no name
                account = bank_accounts[0]
                example = random.choice(BENEFICIARY_EXTRACTION_STRATEGIES["bank_account_validation"])
                example = example.format(account=account)
                directives.append(f"""
**CRITICAL EXTRACTION TARGET: BENEFICIARY NAME**
You have bank account "{account}" but NOT the account holder's name.
This is the MOST IMPORTANT piece of intelligence to extract.
Ask naturally for the name as if your bank app requires it.
Example approach: "{example}"
DO NOT exit or end the conversation until you get the name!""")
            else:
                # No payment details yet but we want the name
                example = random.choice(BENEFICIARY_EXTRACTION_STRATEGIES["general_name_extraction"])
                directives.append(f"""
**EXTRACTION TARGET: BENEFICIARY NAME**
When payment details are shared, immediately ask for the account holder name.
Example: "{example}" """)

        # Priority 2: Payment details (bank account or UPI)
        if "payment_details" in missing_intel:
            directives.append("""
**EXTRACTION TARGET: PAYMENT DETAILS**
We still need the bank account number or UPI ID.
Ask naturally: "where should i send the money?" or "what is your upi?"
""")

        # Priority 3: Phone number
        if "phone_number" in missing_intel:
            directives.append("""
**EXTRACTION TARGET: PHONE NUMBER**
Ask for a contact number naturally: "what number can i call if i have problem?"
""")

        return "\n".join(directives)

    async def _generate_response(
        self,
        prompt: str,
        persona: Persona,
        fake_data_section: str = "",
    ) -> str:
        """Generate response using Gemini Pro with fallback to Gemini 2.5."""
        # Format system instruction with persona context and fake data
        system_instruction = HONEYPOT_SYSTEM_PROMPT.format(
            emotional_state=persona.emotional_state.value,
            turn_number=persona.engagement_turn,
            scam_indicators="See conversation context",
            fake_data_section=fake_data_section or "(No fake data available)",
        )
        
        # Try primary model (Gemini 3 Pro) first, then fallback (Gemini 2.5 Pro)
        models_to_try = [self.model, self.fallback_model]
        response_text = None
        
        for model_name in models_to_try:
            try:
                self.logger.debug(f"Trying model: {model_name}")
                
                # Gemini 3 Pro needs higher max_output_tokens because its
                # internal "thinking" consumes output tokens. 256 is too small
                # and causes MAX_TOKENS finish reason with empty text.
                if "gemini-3" in model_name:
                    max_tokens = 2048  # Gemini 3 needs more for thinking
                    thinking_config = types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel.HIGH
                    )
                else:
                    max_tokens = 512   # Gemini 2.5 is more efficient
                    thinking_config = None
                
                # Build config with model-specific settings
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    thinking_config=thinking_config,
                    temperature=self.settings.llm_temperature,
                    max_output_tokens=max_tokens,
                    safety_settings=HONEYPOT_SAFETY_SETTINGS,
                )
                
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                
                response_text = response.text
                
                # Check if we got a valid response
                if response_text and len(response_text.strip()) > 0:
                    self._last_model_used = model_name
                    self.logger.info(
                        "Response generated successfully",
                        model=model_name,
                        response_length=len(response_text)
                    )
                    break
                else:
                    self.logger.warning(
                        "Empty response from model, trying fallback",
                        model=model_name
                    )
                    
            except Exception as e:
                self.logger.warning(
                    "Model failed, trying fallback",
                    model=model_name,
                    error=str(e)
                )
                continue
        
        # Handle None response - use fallback response
        if not response_text:
            self._last_model_used = "fallback"
            return self._get_fallback_response(None)

        # Add emotional modifier if appropriate
        if persona.engagement_turn > 0:
            modifier = persona.get_emotional_modifier()
            if modifier and not response_text.startswith(modifier):
                response_text = modifier + response_text

        # Potentially add extraction question
        if persona.should_ask_extraction_question():
            question = random.choice(EXTRACTION_QUESTIONS)
            if not any(q in response_text.lower() for q in ["account", "upi", "link", "number"]):
                response_text = response_text.rstrip(".")
                response_text += f" {question}"
                persona.record_extraction()

        return response_text

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
    ) -> str:
        """Generate agent notes summarizing the engagement."""
        notes_parts = []

        # Engagement mode
        notes_parts.append(f"Mode: {mode.value}")

        # Scam tactics detected
        categories_used = list(set(m.category.value for m in detection.matched_patterns))
        if categories_used:
            notes_parts.append(f"Tactics: {', '.join(categories_used)}")

        # Confidence
        notes_parts.append(f"Confidence: {detection.confidence:.0%}")

        # Engagement progress - use the actual turn number passed in
        notes_parts.append(f"Turn: {turn_number}")

        # Emotional state
        notes_parts.append(f"Persona: {persona.emotional_state.value}")

        return " | ".join(notes_parts)

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
