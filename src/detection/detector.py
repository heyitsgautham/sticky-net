"""Pure AI scam detection using Gemini classifier."""

from dataclasses import dataclass, field

import structlog

from src.api.schemas import ConversationMessage, Metadata
from src.detection.classifier import ScamClassifier, ClassificationResult

logger = structlog.get_logger()


@dataclass
class DetectionResult:
    """Result of AI scam detection."""
    is_scam: bool
    confidence: float  # 0.0 to 1.0
    scam_type: str | None = None
    reasoning: str = ""
    threat_indicators: list[str] = field(default_factory=list)


class ScamDetector:
    """Pure AI scam detector using Gemini classification."""

    SCAM_THRESHOLD = 0.6

    def __init__(self) -> None:
        self.logger = logger.bind(component="ScamDetector")
        self.classifier = ScamClassifier()

    async def analyze(
        self,
        message: str,
        history: list[ConversationMessage] | None = None,
        metadata: Metadata | None = None,
        previous_result: DetectionResult | None = None,
    ) -> DetectionResult:
        """
        Analyze a message using pure AI classification.
        
        All messages are routed directly to the AI classifier.
        Confidence can only escalate (never decrease from previous).
        """
        self.logger.info("Analyzing message", message_length=len(message))

        # Build previous classification for context
        prev_classification = None
        if previous_result:
            prev_classification = ClassificationResult(
                is_scam=previous_result.is_scam,
                confidence=previous_result.confidence,
                scam_type=previous_result.scam_type,
            )

        # Call AI classifier
        ai_result = await self.classifier.classify(
            message=message,
            history=history,
            metadata=metadata,
            previous_classification=prev_classification,
        )

        # Confidence can only INCREASE from previous (prevents oscillation)
        # This maintains persistent suspicion once a conversation is flagged
        final_confidence = ai_result.confidence
        if previous_result is not None:
            final_confidence = max(final_confidence, previous_result.confidence)

        # Determine if this is a scam based on AI classification AND confidence threshold
        # The threshold ensures we only act on high-confidence classifications
        if ai_result.is_scam:
            # AI says it's a scam - check if confidence meets threshold
            is_scam = final_confidence >= self.SCAM_THRESHOLD
        else:
            # AI says it's NOT a scam - trust the AI unless previous result overrides
            is_scam = False
            if previous_result and previous_result.is_scam:
                # Once flagged as scam, maintain that status (persistent suspicion)
                is_scam = True

        self.logger.info(
            "Classification complete",
            is_scam=is_scam,
            confidence=final_confidence,
            scam_type=ai_result.scam_type,
            ai_is_scam=ai_result.is_scam,
        )

        return DetectionResult(
            is_scam=is_scam,
            confidence=final_confidence,
            scam_type=ai_result.scam_type,
            reasoning=ai_result.reasoning,
            threat_indicators=ai_result.threat_indicators,
        )