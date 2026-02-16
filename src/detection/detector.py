"""Regex-first scam detection with AI fallback.

Uses fast regex pattern matching as the primary classifier (~10ms),
falling back to LLM classification only when regex is inconclusive.
This saves ~150ms per turn on the common path.
"""

import re
from dataclasses import dataclass, field

import structlog

from src.api.schemas import ConversationMessage, Metadata
from src.detection.classifier import ScamClassifier, ClassificationResult

logger = structlog.get_logger()


@dataclass
class DetectionResult:
    """Result of scam detection."""
    is_scam: bool
    confidence: float  # 0.0 to 1.0
    scam_type: str | None = None
    reasoning: str = ""
    threat_indicators: list[str] = field(default_factory=list)


# ── Regex scam patterns (Stage 0 fast path) ──────────────────────────────────
# These catch the vast majority of scam messages in < 10ms.
INSTANT_SCAM_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # (compiled pattern, scam_type, description)
    # Credential theft
    (re.compile(r"send\s+(your\s+)?(otp|password|pin|cvv)", re.I), "banking_fraud", "credential_request"),
    (re.compile(r"share\s+(your\s+)?(otp|cvv|pin)\s+(to|for|with)", re.I), "banking_fraud", "credential_request"),
    (re.compile(r"(otp|password|pin|cvv).*immediately", re.I), "banking_fraud", "credential_urgency"),
    # Account threats
    (re.compile(r"account\s+(will\s+be\s+|is\s+being\s+|has\s+been\s+)?(blocked|suspended|locked|compromised|frozen|deactivated)", re.I), "banking_fraud", "account_threat"),
    (re.compile(r"(block|suspend|freeze|deactivate).*account", re.I), "banking_fraud", "account_threat"),
    # Urgency + verification
    (re.compile(r"verify\s+within\s+\d+\s+(hours?|minutes?)", re.I), "banking_fraud", "urgency_verification"),
    (re.compile(r"(urgent|immediately|right\s+now).*verify", re.I), "banking_fraud", "urgency_verification"),
    (re.compile(r"verify.*immediately", re.I), "banking_fraud", "urgency_verification"),
    # Phishing links
    (re.compile(r"click\s+(here|link|below).*verify", re.I), "others", "phishing_click"),
    (re.compile(r"click\s+(here|link|below).*claim", re.I), "others", "phishing_click"),
    (re.compile(r"https?://[^\s]*(?:fake|phish|amaz0n|g00gle|free-?gift|claim|verify-?account)", re.I), "others", "phishing_url"),
    # Lottery / reward
    (re.compile(r"(lottery|jackpot|won|winner|prize)\s+[₹$£]?\s*\d+", re.I), "lottery_reward", "lottery_prize"),
    (re.compile(r"(congratulations|congrats).*won", re.I), "lottery_reward", "lottery_prize"),
    (re.compile(r"(cashback|reward|prize).*claim", re.I), "lottery_reward", "reward_claim"),
    (re.compile(r"claim\s+(your|the)\s+(reward|prize|cashback|offer)", re.I), "lottery_reward", "reward_claim"),
    # Legal threats
    (re.compile(r"(arrest|legal\s+action|fir|warrant).*immediately", re.I), "impersonation", "legal_threat"),
    (re.compile(r"(police|cbi|ed|cyber\s+cell).*action", re.I), "impersonation", "authority_threat"),
    # KYC / bank impersonation
    (re.compile(r"(kyc|pan|aadhaar)\s+(update|verify|link|expire)", re.I), "banking_fraud", "kyc_scam"),
    (re.compile(r"(sbi|hdfc|icici|axis|rbi|sebi)\s+(customer|support|official|department|helpdesk)", re.I), "impersonation", "bank_impersonation"),
    # Job / investment scams
    (re.compile(r"(part\s*-?\s*time|work\s+from\s+home).*earn", re.I), "job_offer", "job_scam"),
    (re.compile(r"earn\s+[₹$]?\s*\d+.*daily", re.I), "job_offer", "job_scam"),
    # Generic urgency keywords (broad net)
    (re.compile(r"(offer|deal)\s+expires?\s+in\s+\d+", re.I), "others", "urgency_offer"),
    (re.compile(r"selected\s+for.*free", re.I), "lottery_reward", "free_selection"),
]

# Patterns that indicate safe / legitimate messages (not scams)
SAFE_PATTERNS: list[re.Pattern] = [
    re.compile(r"your\s+otp\s+is\s+\d{4,6}", re.I),
    re.compile(r"transaction\s+of\s+rs\.?\s*\d+.*debited", re.I),
    re.compile(r"your\s+order\s+#?\d+\s+has\s+been", re.I),
    re.compile(r"otp\s+for\s+.*is\s+\d{4,6}", re.I),
]


class ScamDetector:
    """Regex-first scam detector with AI fallback.

    Flow:
      1. Regex fast-path (~10ms) catches obvious scam patterns
      2. If regex inconclusive → fall back to LLM classifier (~150ms)
      3. If LLM also says not scam → engage cautiously anyway (safety net)
    """

    SCAM_THRESHOLD = 0.6

    def __init__(self) -> None:
        self.logger = logger.bind(component="ScamDetector")
        self._classifier: ScamClassifier | None = None  # lazy-init to avoid cold-start cost

    @property
    def classifier(self) -> ScamClassifier:
        """Lazy-initialize the LLM classifier (only when regex is inconclusive)."""
        if self._classifier is None:
            self._classifier = ScamClassifier()
        return self._classifier

    # ── Regex fast-path ──────────────────────────────────────────────────────

    @staticmethod
    def _regex_classify(message: str) -> DetectionResult | None:
        """Attempt to classify using regex patterns.

        Returns:
            DetectionResult if a definitive match is found, None if inconclusive.
        """
        text = message.strip()

        # Check safe patterns first
        for pattern in SAFE_PATTERNS:
            if pattern.search(text):
                return DetectionResult(
                    is_scam=False,
                    confidence=0.1,
                    reasoning="Matched safe message pattern (OTP delivery / transaction alert)",
                )

        # Check scam patterns
        matched_indicators: list[str] = []
        matched_type: str | None = None
        for pattern, scam_type, indicator in INSTANT_SCAM_PATTERNS:
            if pattern.search(text):
                matched_indicators.append(indicator)
                if matched_type is None:
                    matched_type = scam_type

        if matched_indicators:
            # More matches → higher confidence
            confidence = min(0.95, 0.75 + 0.05 * len(matched_indicators))
            return DetectionResult(
                is_scam=True,
                confidence=confidence,
                scam_type=matched_type,
                reasoning=f"Regex fast-path: matched {len(matched_indicators)} scam indicators",
                threat_indicators=matched_indicators,
            )

        return None  # inconclusive → need LLM

    # ── Main entry point ─────────────────────────────────────────────────────

    async def analyze(
        self,
        message: str,
        history: list[ConversationMessage] | None = None,
        metadata: Metadata | None = None,
        previous_result: DetectionResult | None = None,
    ) -> DetectionResult:
        """Analyze a message using regex-first, LLM-fallback approach.

        1. Regex fast-path for obvious scam patterns
        2. LLM fallback for ambiguous messages
        3. Safety net: if both miss, still engage cautiously
        """
        self.logger.info("Analyzing message", message_length=len(message))

        # ── Step 1: Regex fast-path ──────────────────────────────────────────
        regex_result = self._regex_classify(message)

        if regex_result is not None:
            self.logger.info(
                "Regex fast-path classification",
                is_scam=regex_result.is_scam,
                confidence=regex_result.confidence,
                scam_type=regex_result.scam_type,
                indicators=regex_result.threat_indicators,
            )
            # Maintain persistent suspicion from previous result
            if previous_result and previous_result.is_scam and not regex_result.is_scam:
                regex_result.is_scam = True
                regex_result.confidence = max(regex_result.confidence, previous_result.confidence)
            return regex_result

        # ── Step 2: LLM fallback (regex inconclusive) ────────────────────────
        self.logger.info("Regex inconclusive, falling back to LLM classifier")

        prev_classification = None
        if previous_result:
            prev_classification = ClassificationResult(
                is_scam=previous_result.is_scam,
                confidence=previous_result.confidence,
                scam_type=previous_result.scam_type,
            )

        ai_result = await self.classifier.classify(
            message=message,
            history=history,
            metadata=metadata,
            previous_classification=prev_classification,
        )

        # Confidence can only INCREASE from previous (persistent suspicion)
        final_confidence = ai_result.confidence
        if previous_result is not None:
            final_confidence = max(final_confidence, previous_result.confidence)

        if ai_result.is_scam:
            is_scam = final_confidence >= self.SCAM_THRESHOLD
        else:
            is_scam = False
            if previous_result and previous_result.is_scam:
                is_scam = True

        # ── Step 3: Safety net — engage cautiously even if both miss ─────────
        if not is_scam:
            self.logger.info(
                "Both regex and LLM say not scam — engaging cautiously as safety net"
            )
            is_scam = True
            final_confidence = max(final_confidence, 0.65)
            scam_type = ai_result.scam_type or "others"
            reasoning = (
                f"Safety net: regex inconclusive + LLM confidence {ai_result.confidence:.2f}. "
                "Engaging cautiously to gather signal."
            )
        else:
            scam_type = ai_result.scam_type
            reasoning = ai_result.reasoning

        self.logger.info(
            "Classification complete",
            is_scam=is_scam,
            confidence=final_confidence,
            scam_type=scam_type,
        )

        return DetectionResult(
            is_scam=is_scam,
            confidence=final_confidence,
            scam_type=scam_type,
            reasoning=reasoning,
            threat_indicators=ai_result.threat_indicators,
        )