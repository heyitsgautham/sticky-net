"""AI-based scam classification using Gemini 3 Flash."""

import asyncio
import json
import os
from dataclasses import dataclass, field
from enum import Enum

import structlog
from google import genai
from google.genai import types

from config.settings import get_settings
from src.api.schemas import ConversationMessage, Metadata


class ScamType(str, Enum):
    """Types of scams that can be detected."""

    JOB_OFFER = "job_offer"  # Part-time job, work from home, YouTube liking scams
    BANKING_FRAUD = "banking_fraud"  # KYC update, account blocked, verify account
    LOTTERY_REWARD = "lottery_reward"  # Lottery winner, reward points, cashback
    IMPERSONATION = "impersonation"  # Police, CBI, bank official impersonation
    OTHERS = "others"  # Any scam that doesn't fit above categories

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


# Safety settings for Gemini to allow scam content analysis (for honeypot context)
CLASSIFIER_SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
]


@dataclass
class ClassificationResult:
    """Result of AI scam classification."""

    is_scam: bool
    confidence: float  # 0.0 to 1.0
    scam_type: str | None = None
    threat_indicators: list[str] = field(default_factory=list)
    reasoning: str = ""


class ScamClassifier:
    """
    AI-based scam classifier using Gemini 3 Flash.

    Uses semantic understanding to catch sophisticated scams
    that regex patterns would miss.
    """

    CLASSIFICATION_PROMPT = """Analyze if this message/conversation is a SCAM attempt.

CONVERSATION HISTORY:
{history}

NEW MESSAGE:
"{message}"

METADATA:
- Channel: {channel}
- Locale: {locale}
- Timestamp: {timestamp}

PREVIOUS ASSESSMENT (if any):
{previous_assessment}

═══════════════════════════════════════════════════════════════════════════════
CRITICAL: WHAT IS A SCAM vs WHAT IS NOT A SCAM
═══════════════════════════════════════════════════════════════════════════════

A SCAM involves DECEPTION or COERCION. At least ONE of these must be present:
  ✗ IMPERSONATION: Pretending to be someone else (bank, government, police, tech support)
  ✗ FALSE PRETENSES: Lying about a situation (your account is blocked, you won a lottery)
  ✗ THREATS/COERCION: Threatening consequences (arrest, account closure, legal action)
  ✗ DATA THEFT: Requesting OTPs, passwords, CVV, PINs to steal credentials
  ✗ PHISHING: Fake links to steal login credentials

NOT A SCAM - Personal/Direct Requests (even if annoying):
  ✓ Direct money requests from someone identifying themselves transparently
  ✓ Friend/acquaintance asking for money urgently (even if suspicious relationship)
  ✓ Informal requests like "send me ₹5000 to my UPI" WITHOUT impersonation/threats
  ✓ Begging or guilt-tripping WITHOUT impersonation

KEY DISTINCTION:
- "I'm Ravi, urgently need ₹5000, send to ravi@upi" → NOT SCAM (transparent request)
- "I'm from SBI, your account is blocked, send ₹5000 to verify@upi" → SCAM (impersonation + false pretense)
- "Send money or your account will be closed" → SCAM (threat/coercion)
- "Hey bro, can you lend me 10k? I'll pay back" → NOT SCAM (direct personal request)

═══════════════════════════════════════════════════════════════════════════════
ANALYSIS GUIDELINES
═══════════════════════════════════════════════════════════════════════════════

1. Does the sender IMPERSONATE an authority (bank, police, company)?
2. Does the message contain FALSE CLAIMS (account blocked, lottery won, unauthorized transaction)?
3. Are there THREATS or COERCION tactics (arrest, account closure, legal action)?
4. Is there a request for SENSITIVE DATA (OTP, password, CVV)?
5. Is there a PHISHING LINK designed to steal credentials?

If NONE of the above → NOT A SCAM (even if it's a money request)

═══════════════════════════════════════════════════════════════════════════════
SCAM SIGNAL INDICATORS (Red Flags to Watch For)
═══════════════════════════════════════════════════════════════════════════════

• ARTIFICIAL URGENCY:
  - "Expires in X minutes/hours", "Act now", "Immediate action required"
  - "Last chance", "Hurry", "Limited time offer", "Today only"
  - Time pressure designed to prevent rational thinking

• AUTHORITY IMPERSONATION:
  - Fake RBI, SEBI, TRAI officials demanding verification
  - Police/CBI/ED threatening arrest or legal action
  - Bank officials claiming account issues requiring immediate action
  - Government entities demanding Aadhaar/PAN linking

• PAYMENT REQUEST RED FLAGS:
  - OTP, PIN, CVV, or password requests (no legitimate entity asks for these)
  - UPI transfers to unknown/personal accounts for "verification"
  - "Refundable" security deposits or processing fees
  - Requests to install remote access apps (TeamViewer, AnyDesk)

• PHISHING INDICATORS:
  - Suspicious links with misspellings (amaz0n, g00gle)
  - URL shorteners: bit.ly, tinyurl, short.io (hiding real destination)
  - "Click to verify", "Login to secure your account"
  - Links to non-official domains pretending to be banks/services

• THREAT TACTICS:
  - "Account will be blocked/suspended/frozen"
  - "Arrest warrant issued", "FIR registered against you"
  - "Legal action will be taken", "Case filed"
  - "Your family will be informed"

• FINANCIAL LURES:
  - Lottery/prize winnings you never entered
  - Job offers requiring upfront payment or "registration fees"
  - Refund scams claiming overpayment
  - Investment schemes promising unrealistic returns
  - "You've been selected" for exclusive opportunities

SCAM TYPE CLASSIFICATION (required if is_scam=true):
- "job_offer": Part-time job offers, work from home, YouTube/Instagram liking tasks, easy money schemes
- "banking_fraud": KYC update requests, account blocked warnings, verify account, link Aadhaar/PAN
- "lottery_reward": Lottery winner announcements, reward points expiring, cashback offers, lucky draw
- "impersonation": Police/CBI/ED officer impersonation, bank manager calls, government official threats
- "others": Investment scams, crypto schemes, romance scams, tech support scams

Return ONLY valid JSON (no markdown):
{{"is_scam": boolean, "confidence": float (0.0-1.0), "scam_type": "job_offer"|"banking_fraud"|"lottery_reward"|"impersonation"|"others"|null, "threat_indicators": [list of strings], "reasoning": "brief explanation"}}
"""

    def __init__(self) -> None:
        """Initialize the classifier with Gemini 3 Flash and fallback to 2.5."""
        self.settings = get_settings()
        
        # Set credentials path in environment if configured
        if self.settings.google_application_credentials:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.settings.google_application_credentials
        
        # Initialize Gemini client with Vertex AI credentials from settings
        self.client = genai.Client(
            vertexai=self.settings.google_genai_use_vertexai,
            project=self.settings.google_cloud_project,
            location=self.settings.google_cloud_location,
        )
        
        # Primary model (Gemini 3 Flash) and fallback (Gemini 2.5 Flash)
        self.model = self.settings.flash_model  # gemini-3-flash-preview
        self.fallback_model = self.settings.fallback_flash_model  # gemini-2.5-flash
        self._last_model_used: str | None = None  # Track which model was used
        self.logger = logger.bind(component="ScamClassifier")

    async def classify(
        self,
        message: str,
        history: list[ConversationMessage] | None = None,
        metadata: Metadata | None = None,
        previous_classification: "ClassificationResult | None" = None,
    ) -> ClassificationResult:
        """
        Classify a message using AI.

        Args:
            message: The message text to analyze
            history: Previous messages in the conversation
            metadata: Message metadata (channel, locale, etc.)
            previous_classification: Previous classification result for context

        Returns:
            ClassificationResult with is_scam, confidence, and scam_type
        """
        self.logger.info("Classifying message with AI", message_length=len(message))

        # Format history for prompt
        history_text = self._format_history(history) if history else "No previous messages"

        # Format previous assessment
        prev_text = "None"
        if previous_classification:
            prev_text = (
                f"is_scam={previous_classification.is_scam}, "
                f"confidence={previous_classification.confidence}"
            )

        # Build prompt
        prompt = self.CLASSIFICATION_PROMPT.format(
            history=history_text,
            message=message,
            channel=metadata.channel if metadata else "unknown",
            locale=metadata.locale if metadata else "unknown",
            timestamp=metadata.language if metadata else "unknown",
            previous_assessment=prev_text,
        )

        try:
            # Try primary model (Gemini 3 Flash) first, then fallback (Gemini 2.5 Flash)
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
                            f"Trying classification model: {model_name}",
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            timeout=timeout_seconds,
                        )
                        
                        # Build config (thinking is high by default in Gemini 3)
                        config = types.GenerateContentConfig(
                            temperature=0.1,  # Low temperature for consistent classification
                            safety_settings=CLASSIFIER_SAFETY_SETTINGS,
                            max_output_tokens=10000,
                        )
                        
                        # Wrap API call with timeout (async with executor)
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
                                "Classification successful",
                                model=model_name,
                                response_length=len(response_text),
                                attempt=attempt + 1,
                            )
                            break
                        else:
                            self.logger.warning(
                                "Empty response from model, trying fallback",
                                model=model_name
                            )
                            break  # Don't retry on empty response, try fallback model
                            
                    except asyncio.TimeoutError:
                        self.logger.warning(
                            "Gemini API timeout during classification",
                            model=model_name,
                            attempt=attempt + 1,
                            timeout_seconds=timeout_seconds,
                        )
                        if attempt < max_retries:
                            self.logger.info(
                                f"Retrying classification after {retry_delay}s delay",
                                remaining_retries=max_retries - attempt,
                            )
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            self.logger.error(
                                "Max retries exceeded for classification model",
                                model=model_name,
                            )
                            break  # Try fallback model
                            
                    except Exception as e:
                        self.logger.warning(
                            "Classification model failed, trying fallback",
                            model=model_name,
                            error=str(e)
                        )
                        break  # Don't retry on other errors, try fallback model
                
                # If we got a valid response, break out of model loop
                if response_text and len(response_text.strip()) > 0:
                    break
            
            if response_text:
                return self._parse_response(response_text)
            else:
                raise Exception("All models failed to generate response")

        except Exception as e:
            self.logger.error("AI classification failed", error=str(e))
            # Return uncertain result on failure
            return ClassificationResult(
                is_scam=False,
                confidence=0.5,
                reasoning=f"AI classification failed: {str(e)}",
            )

    def _format_history(self, history: list[ConversationMessage]) -> str:
        """Format conversation history for the prompt."""
        if not history:
            return "No previous messages"

        lines = []
        for msg in history[-5:]:  # Last 5 messages for context
            # Handle both enum and string sender types
            sender_str = msg.sender.value if hasattr(msg.sender, 'value') else str(msg.sender)
            sender = "SCAMMER" if sender_str == "scammer" else "USER"
            lines.append(f"[{sender}]: {msg.text}")

        return "\n".join(lines)

    def _parse_response(self, response_text: str) -> ClassificationResult:
        """Parse AI response JSON into ClassificationResult."""
        try:
            # Clean response (remove markdown if present)
            text = response_text.strip()
            if text.startswith("```"):
                # Extract content between code fences
                lines = text.split("\n")
                # Find start and end of code block
                start_idx = 1 if lines[0].startswith("```") else 0
                end_idx = len(lines)
                for i in range(len(lines) - 1, 0, -1):
                    if lines[i].strip() == "```":
                        end_idx = i
                        break
                text = "\n".join(lines[start_idx:end_idx])
                # Remove json language identifier if present
                if text.startswith("json"):
                    text = text[4:].strip()

            data = json.loads(text)

            return ClassificationResult(
                is_scam=bool(data.get("is_scam", False)),
                confidence=float(data.get("confidence", 0.5)),
                scam_type=data.get("scam_type"),
                threat_indicators=data.get("threat_indicators", []),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            self.logger.warning(
                "Failed to parse AI response",
                error=str(e),
                response=response_text,
            )
            return ClassificationResult(
                is_scam=False,
                confidence=0.5,
                reasoning=f"Parse error: {str(e)}",
            )
