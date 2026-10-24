"""AI-based scam classification using Gemini 3 Flash."""

import asyncio
import functools
import json
import os
from dataclasses import dataclass, field
from enum import Enum

import structlog
from google import genai
from google.genai import types

from config.settings import get_settings
from src import llm
from src.api.schemas import ConversationMessage, Metadata


class ScamType(str, Enum):
    """Types of scams that can be detected."""

    JOB_OFFER = "job_offer"  # Part-time job, work from home, YouTube liking scams
    BANKING_FRAUD = "banking_fraud"  # KYC update, account blocked, verify account
    LOTTERY_REWARD = "lottery_reward"  # Lottery winner, reward points, cashback
    IMPERSONATION = "impersonation"  # Police, CBI, bank official impersonation
    OTHERS = "others"  # Any scam that doesn't fit above categories


logger = structlog.get_logger()


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

    CLASSIFICATION_PROMPT = """Classify if this message is a SCAM. Return ONLY valid JSON.

HISTORY:
{history}

NEW MESSAGE: "{message}"

METADATA: channel={channel}, locale={locale}

PREVIOUS ASSESSMENT: {previous_assessment}

SCAM = deception/coercion via: impersonation, false pretenses, threats, credential theft, or phishing.
NOT SCAM = transparent personal requests without deception.

SCAM TYPES: "job_offer" | "banking_fraud" | "lottery_reward" | "impersonation" | "others"

Return ONLY: {{"is_scam": bool, "confidence": float, "scam_type": str|null, "threat_indicators": [str], "reasoning": "brief"}}
"""

    def __init__(self) -> None:
        """Initialize the classifier with Gemini 3 Flash and fallback to 2.5."""
        self.settings = get_settings()

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

                        # Thinking set to MINIMAL for fast classification
                        config = types.GenerateContentConfig(
                            temperature=0.1,  # Low temperature for consistent classification
                            safety_settings=CLASSIFIER_SAFETY_SETTINGS,
                            max_output_tokens=1024,
                            thinking_config=types.ThinkingConfig(
                                thinking_budget=0,
                            ),
                        )

                        # Wrap API call with timeout (async with executor)
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
                                "Classification successful",
                                model=model_name,
                                response_length=len(response_text),
                                attempt=attempt + 1,
                            )
                            break
                        else:
                            self.logger.warning(
                                "Empty response from model, trying fallback", model=model_name
                            )
                            break  # Don't retry on empty response, try fallback model

                    except TimeoutError:
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
                            error=str(e),
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
            sender_str = msg.sender.value if hasattr(msg.sender, "value") else str(msg.sender)
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
