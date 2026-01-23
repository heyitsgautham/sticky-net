"""AI-based scam classification using Gemini 3 Flash."""

import json
from dataclasses import dataclass, field

import structlog
from google import genai
from google.genai import types

from config.settings import get_settings
from src.api.schemas import ConversationMessage, Metadata

logger = structlog.get_logger()


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

    CLASSIFICATION_PROMPT = """Analyze if this message/conversation is a scam attempt.

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

ANALYSIS GUIDELINES:
1. Consider if the conversation shows ESCALATION toward scam tactics
2. Check for multi-stage scam patterns (benign start → malicious intent)
3. Look for: urgency, authority impersonation, threats, data requests, financial manipulation
4. Consider the full context, not just the current message

Return ONLY valid JSON (no markdown):
{{"is_scam": boolean, "confidence": float (0.0-1.0), "scam_type": string or null, "threat_indicators": [list of strings], "reasoning": "brief explanation"}}
"""

    def __init__(self) -> None:
        """Initialize the classifier with Gemini 3 Flash."""
        self.settings = get_settings()
        self.client = genai.Client()
        self.model = self.settings.flash_model  # gemini-3-flash-preview
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
            # Call Gemini 3 Flash with LOW thinking for speed
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel.LOW  # Fast classification
                    ),
                    temperature=0.1,  # Low temperature for consistent classification
                ),
            )

            return self._parse_response(response.text)

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
            sender = "SCAMMER" if msg.sender.value == "scammer" else "USER"
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
                response=response_text[:200],
            )
            return ClassificationResult(
                is_scam=False,
                confidence=0.5,
                reasoning=f"Parse error: {str(e)}",
            )
