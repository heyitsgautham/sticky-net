---
#applyTo: "**"
---

# Milestone 3: Scam Detection

> **Goal**: Implement the scam detection module that analyzes messages for fraud indicators and returns confidence scores.

## Prerequisites

- Milestone 1 & 2 completed
- API layer functional
- LangChain MCP available for documentation reference

## Tasks

### 3.1 Define Scam Detection Patterns

#### src/detection/patterns.py

```python
"""Scam detection patterns and indicators."""

from dataclasses import dataclass, field
from enum import Enum
import re


class ScamCategory(str, Enum):
    """Categories of scam tactics."""

    URGENCY = "urgency"
    AUTHORITY = "authority"
    THREAT = "threat"
    REQUEST = "request"
    FINANCIAL = "financial"
    PHISHING = "phishing"


@dataclass
class Pattern:
    """A scam indicator pattern."""

    category: ScamCategory
    pattern: re.Pattern
    weight: float  # 0.0 to 1.0 importance
    description: str


@dataclass
class PatternMatch:
    """A matched pattern result."""

    category: ScamCategory
    matched_text: str
    weight: float
    description: str


# Urgency patterns - Create immediate pressure
URGENCY_PATTERNS = [
    Pattern(
        category=ScamCategory.URGENCY,
        pattern=re.compile(r"\b(immediate(?:ly)?|urgent(?:ly)?|asap|right\s+now)\b", re.I),
        weight=0.7,
        description="Immediate action language",
    ),
    Pattern(
        category=ScamCategory.URGENCY,
        pattern=re.compile(r"\b(today|within\s+\d+\s+(?:hour|minute|day)s?)\b", re.I),
        weight=0.6,
        description="Time pressure",
    ),
    Pattern(
        category=ScamCategory.URGENCY,
        pattern=re.compile(r"\b(hurry|quick(?:ly)?|fast|don'?t\s+delay)\b", re.I),
        weight=0.5,
        description="Speed pressure",
    ),
    Pattern(
        category=ScamCategory.URGENCY,
        pattern=re.compile(r"\b(last\s+chance|final\s+warning|expires?\s+(?:today|soon))\b", re.I),
        weight=0.8,
        description="Deadline pressure",
    ),
]

# Authority patterns - Impersonate trusted entities
AUTHORITY_PATTERNS = [
    Pattern(
        category=ScamCategory.AUTHORITY,
        pattern=re.compile(
            r"\b(RBI|Reserve\s+Bank|SBI|HDFC|ICICI|Axis|bank\s+of\s+india)\b", re.I
        ),
        weight=0.8,
        description="Bank impersonation",
    ),
    Pattern(
        category=ScamCategory.AUTHORITY,
        pattern=re.compile(
            r"\b(government|ministry|police|cyber\s*cell|income\s*tax|IT\s+department)\b", re.I
        ),
        weight=0.9,
        description="Government impersonation",
    ),
    Pattern(
        category=ScamCategory.AUTHORITY,
        pattern=re.compile(r"\b(official|authorized|verified|genuine)\b", re.I),
        weight=0.4,
        description="Authority claim",
    ),
    Pattern(
        category=ScamCategory.AUTHORITY,
        pattern=re.compile(r"\b(customer\s+(?:care|support|service)|helpline|helpdesk)\b", re.I),
        weight=0.5,
        description="Support impersonation",
    ),
]

# Threat patterns - Create fear
THREAT_PATTERNS = [
    Pattern(
        category=ScamCategory.THREAT,
        pattern=re.compile(
            r"\b(block(?:ed)?|suspend(?:ed)?|deactivat(?:e|ed)|terminat(?:e|ed))\b", re.I
        ),
        weight=0.8,
        description="Account threat",
    ),
    Pattern(
        category=ScamCategory.THREAT,
        pattern=re.compile(r"\b(arrest(?:ed)?|legal\s+action|court|lawsuit|police\s+case)\b", re.I),
        weight=0.9,
        description="Legal threat",
    ),
    Pattern(
        category=ScamCategory.THREAT,
        pattern=re.compile(r"\b(fine|penalty|fee|charge)\b", re.I),
        weight=0.5,
        description="Financial penalty threat",
    ),
    Pattern(
        category=ScamCategory.THREAT,
        pattern=re.compile(r"\b(fraud(?:ulent)?|suspicious|unauthorized|illegal)\b", re.I),
        weight=0.6,
        description="Fraud accusation",
    ),
]

# Request patterns - Ask for sensitive data
REQUEST_PATTERNS = [
    Pattern(
        category=ScamCategory.REQUEST,
        pattern=re.compile(r"\b(OTP|one\s*time\s*password|verification\s+code)\b", re.I),
        weight=0.95,
        description="OTP request",
    ),
    Pattern(
        category=ScamCategory.REQUEST,
        pattern=re.compile(r"\b(PIN|CVV|card\s+number|expiry)\b", re.I),
        weight=0.95,
        description="Card details request",
    ),
    Pattern(
        category=ScamCategory.REQUEST,
        pattern=re.compile(r"\b(password|credentials?|login\s+details?)\b", re.I),
        weight=0.9,
        description="Password request",
    ),
    Pattern(
        category=ScamCategory.REQUEST,
        pattern=re.compile(r"\b(verify|confirm|validate|update)\s+(?:your)?\s*(?:account|details?|KYC)\b", re.I),
        weight=0.7,
        description="Verification request",
    ),
    Pattern(
        category=ScamCategory.REQUEST,
        pattern=re.compile(r"\b(KYC|know\s+your\s+customer|Aadhaar|PAN)\b", re.I),
        weight=0.6,
        description="KYC request",
    ),
]

# Financial patterns - Money/payment related
FINANCIAL_PATTERNS = [
    Pattern(
        category=ScamCategory.FINANCIAL,
        pattern=re.compile(r"\b(transfer|send|pay|deposit)\s+(?:money|amount|₹|\$|Rs\.?)\b", re.I),
        weight=0.8,
        description="Money transfer request",
    ),
    Pattern(
        category=ScamCategory.FINANCIAL,
        pattern=re.compile(r"\b(refund|cashback|reward|prize|lottery|winner)\b", re.I),
        weight=0.7,
        description="Money lure",
    ),
    Pattern(
        category=ScamCategory.FINANCIAL,
        pattern=re.compile(r"\b(UPI|NEFT|IMPS|bank\s+transfer|Google\s*Pay|PhonePe|Paytm)\b", re.I),
        weight=0.5,
        description="Payment method mention",
    ),
    Pattern(
        category=ScamCategory.FINANCIAL,
        pattern=re.compile(r"[₹$]\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*\s*(?:rupees?|Rs\.?)", re.I),
        weight=0.4,
        description="Money amount",
    ),
]

# Phishing patterns - Links and downloads
PHISHING_PATTERNS = [
    Pattern(
        category=ScamCategory.PHISHING,
        pattern=re.compile(r"https?://(?!(?:www\.)?(?:google|microsoft|apple|amazon|gov\.in))[^\s]+", re.I),
        weight=0.6,
        description="Suspicious link",
    ),
    Pattern(
        category=ScamCategory.PHISHING,
        pattern=re.compile(r"\b(click\s+(?:here|link|below)|download|install|open)\b", re.I),
        weight=0.5,
        description="Click/download request",
    ),
    Pattern(
        category=ScamCategory.PHISHING,
        pattern=re.compile(r"(?:bit\.ly|tinyurl|goo\.gl|t\.co|shorturl)/\S+", re.I),
        weight=0.8,
        description="Shortened URL",
    ),
]

# All patterns combined
ALL_PATTERNS: list[Pattern] = [
    *URGENCY_PATTERNS,
    *AUTHORITY_PATTERNS,
    *THREAT_PATTERNS,
    *REQUEST_PATTERNS,
    *FINANCIAL_PATTERNS,
    *PHISHING_PATTERNS,
]


def get_patterns_by_category(category: ScamCategory) -> list[Pattern]:
    """Get all patterns for a specific category."""
    return [p for p in ALL_PATTERNS if p.category == category]


def match_all_patterns(text: str) -> list[PatternMatch]:
    """Match text against all patterns."""
    matches = []
    for pattern in ALL_PATTERNS:
        for match in pattern.pattern.finditer(text):
            matches.append(
                PatternMatch(
                    category=pattern.category,
                    matched_text=match.group(),
                    weight=pattern.weight,
                    description=pattern.description,
                )
            )
    return matches
```

### 3.2 Implement Scam Detector

#### src/detection/detector.py

```python
"""Scam detection logic."""

from dataclasses import dataclass, field
from typing import Any

import structlog

from src.api.schemas import ConversationMessage, Metadata
from src.detection.patterns import (
    ScamCategory,
    PatternMatch,
    match_all_patterns,
)

logger = structlog.get_logger()


@dataclass
class DetectionResult:
    """Result of scam detection analysis."""

    is_scam: bool
    confidence: float  # 0.0 to 1.0
    matched_patterns: list[PatternMatch] = field(default_factory=list)
    category_scores: dict[ScamCategory, float] = field(default_factory=dict)
    reasoning: str = ""


class ScamDetector:
    """
    Analyzes messages for scam indicators.

    Uses pattern matching with weighted scoring to determine
    if a message is likely a scam attempt.
    """

    # Threshold for classifying as scam
    SCAM_THRESHOLD = 0.5

    # Minimum patterns needed for high confidence
    MIN_PATTERNS_HIGH_CONFIDENCE = 3

    # Category combination bonuses (multiple tactics = more suspicious)
    MULTI_CATEGORY_BONUS = 0.1

    def __init__(self) -> None:
        """Initialize the detector."""
        self.logger = logger.bind(component="ScamDetector")

    async def analyze(
        self,
        message: str,
        history: list[ConversationMessage] | None = None,
        metadata: Metadata | None = None,
    ) -> DetectionResult:
        """
        Analyze a message for scam indicators.

        Args:
            message: The message text to analyze
            history: Previous messages in the conversation
            metadata: Additional context about the message

        Returns:
            DetectionResult with scam classification and confidence
        """
        self.logger.info("Analyzing message", message_length=len(message))

        # Match patterns in current message
        matches = match_all_patterns(message)

        # Also check conversation history for context
        history_matches = []
        if history:
            for msg in history:
                if msg.sender.value == "scammer":
                    history_matches.extend(match_all_patterns(msg.text))

        all_matches = matches + history_matches

        # Calculate category scores
        category_scores = self._calculate_category_scores(all_matches)

        # Calculate overall confidence
        confidence = self._calculate_confidence(matches, category_scores)

        # Determine if it's a scam
        is_scam = confidence >= self.SCAM_THRESHOLD

        # Generate reasoning
        reasoning = self._generate_reasoning(matches, category_scores, is_scam)

        result = DetectionResult(
            is_scam=is_scam,
            confidence=confidence,
            matched_patterns=matches,
            category_scores=category_scores,
            reasoning=reasoning,
        )

        self.logger.info(
            "Detection complete",
            is_scam=is_scam,
            confidence=f"{confidence:.2f}",
            pattern_count=len(matches),
        )

        return result

    def _calculate_category_scores(
        self, matches: list[PatternMatch]
    ) -> dict[ScamCategory, float]:
        """Calculate normalized scores per category."""
        scores: dict[ScamCategory, list[float]] = {cat: [] for cat in ScamCategory}

        for match in matches:
            scores[match.category].append(match.weight)

        # Average the weights per category, capped at 1.0
        return {
            cat: min(1.0, sum(weights) / max(1, len(weights)) if weights else 0.0)
            for cat, weights in scores.items()
        }

    def _calculate_confidence(
        self,
        matches: list[PatternMatch],
        category_scores: dict[ScamCategory, float],
    ) -> float:
        """Calculate overall scam confidence score."""
        if not matches:
            return 0.0

        # Base confidence from pattern weights
        total_weight = sum(m.weight for m in matches)
        base_confidence = min(1.0, total_weight / 3.0)  # Normalize

        # Bonus for multiple categories (scammers use multiple tactics)
        active_categories = sum(1 for score in category_scores.values() if score > 0)
        multi_category_bonus = min(0.3, (active_categories - 1) * self.MULTI_CATEGORY_BONUS)

        # High-weight patterns boost confidence
        high_weight_count = sum(1 for m in matches if m.weight >= 0.8)
        high_weight_bonus = min(0.2, high_weight_count * 0.05)

        # Calculate final confidence
        confidence = base_confidence + multi_category_bonus + high_weight_bonus

        return min(1.0, max(0.0, confidence))

    def _generate_reasoning(
        self,
        matches: list[PatternMatch],
        category_scores: dict[ScamCategory, float],
        is_scam: bool,
    ) -> str:
        """Generate human-readable reasoning for the detection."""
        if not matches:
            return "No scam indicators detected in the message."

        # Get top categories
        top_categories = sorted(
            [(cat, score) for cat, score in category_scores.items() if score > 0],
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        category_descriptions = {
            ScamCategory.URGENCY: "urgency/time pressure tactics",
            ScamCategory.AUTHORITY: "authority impersonation",
            ScamCategory.THREAT: "threatening language",
            ScamCategory.REQUEST: "sensitive data requests",
            ScamCategory.FINANCIAL: "financial manipulation",
            ScamCategory.PHISHING: "phishing attempts",
        }

        if is_scam:
            tactics = [category_descriptions[cat] for cat, _ in top_categories]
            return f"Scam detected using: {', '.join(tactics)}."
        else:
            return f"Low confidence scam indicators found. Monitoring recommended."
```

### 3.3 Create Detection Module Init

#### src/detection/__init__.py

```python
"""Scam detection module."""

from src.detection.detector import ScamDetector, DetectionResult
from src.detection.patterns import ScamCategory, Pattern, PatternMatch

__all__ = [
    "ScamDetector",
    "DetectionResult",
    "ScamCategory",
    "Pattern",
    "PatternMatch",
]
```

### 3.4 Write Detection Tests

#### tests/test_detection.py

```python
"""Tests for scam detection module."""

import pytest

from src.detection.detector import ScamDetector, DetectionResult
from src.detection.patterns import (
    ScamCategory,
    match_all_patterns,
    URGENCY_PATTERNS,
    REQUEST_PATTERNS,
)


class TestPatternMatching:
    """Tests for pattern matching functionality."""

    def test_urgency_pattern_matches_immediately(self):
        """Urgency patterns should match 'immediately'."""
        matches = match_all_patterns("Verify your account immediately!")
        urgency_matches = [m for m in matches if m.category == ScamCategory.URGENCY]
        assert len(urgency_matches) >= 1
        assert any("immediate" in m.matched_text.lower() for m in urgency_matches)

    def test_authority_pattern_matches_bank_names(self):
        """Authority patterns should match bank names."""
        matches = match_all_patterns("This is from SBI bank regarding your account")
        authority_matches = [m for m in matches if m.category == ScamCategory.AUTHORITY]
        assert len(authority_matches) >= 1

    def test_request_pattern_matches_otp(self):
        """Request patterns should match OTP requests."""
        matches = match_all_patterns("Please share your OTP to verify")
        request_matches = [m for m in matches if m.category == ScamCategory.REQUEST]
        assert len(request_matches) >= 1
        assert any("OTP" in m.matched_text.upper() for m in request_matches)

    def test_threat_pattern_matches_blocked(self):
        """Threat patterns should match account threats."""
        matches = match_all_patterns("Your account will be blocked today")
        threat_matches = [m for m in matches if m.category == ScamCategory.THREAT]
        assert len(threat_matches) >= 1

    def test_no_matches_for_normal_message(self):
        """Normal messages should have few or no matches."""
        matches = match_all_patterns("Hello, how are you doing today?")
        assert len(matches) <= 1  # Allow for occasional false positives


class TestScamDetector:
    """Tests for ScamDetector class."""

    @pytest.fixture
    def detector(self) -> ScamDetector:
        """Create detector instance."""
        return ScamDetector()

    @pytest.mark.asyncio
    async def test_detects_obvious_scam(self, detector: ScamDetector):
        """Should detect obvious scam messages."""
        message = (
            "URGENT: Your SBI account will be blocked today! "
            "Share OTP immediately to verify and avoid legal action."
        )
        result = await detector.analyze(message)

        assert result.is_scam is True
        assert result.confidence >= 0.7
        assert len(result.matched_patterns) >= 3

    @pytest.mark.asyncio
    async def test_detects_kyc_scam(self, detector: ScamDetector):
        """Should detect KYC fraud messages."""
        message = "Dear Customer, your KYC is pending. Update now or account will be suspended."
        result = await detector.analyze(message)

        assert result.is_scam is True
        assert result.confidence >= 0.5

    @pytest.mark.asyncio
    async def test_detects_prize_scam(self, detector: ScamDetector):
        """Should detect lottery/prize scams."""
        message = "Congratulations! You won ₹50,00,000 in lottery. Pay ₹5000 fee to claim prize."
        result = await detector.analyze(message)

        assert result.is_scam is True
        assert ScamCategory.FINANCIAL in result.category_scores

    @pytest.mark.asyncio
    async def test_normal_message_not_flagged(self, detector: ScamDetector):
        """Normal messages should not be flagged as scams."""
        message = "Hi, can we meet for coffee tomorrow at 3pm?"
        result = await detector.analyze(message)

        assert result.is_scam is False
        assert result.confidence < 0.5

    @pytest.mark.asyncio
    async def test_bank_notification_not_flagged(self, detector: ScamDetector):
        """Legitimate bank notifications should have lower confidence."""
        message = "Your account balance is ₹15,000. Last transaction: ₹500 at Amazon."
        result = await detector.analyze(message)

        # May have some matches but should not reach scam threshold
        assert result.confidence < 0.7

    @pytest.mark.asyncio
    async def test_returns_reasoning(self, detector: ScamDetector):
        """Detection should include reasoning."""
        message = "Your account is blocked. Call now to verify OTP!"
        result = await detector.analyze(message)

        assert result.reasoning != ""
        assert len(result.reasoning) > 10

    @pytest.mark.asyncio
    async def test_category_scores_populated(self, detector: ScamDetector):
        """Category scores should be calculated."""
        message = "URGENT from RBI: Account blocked! Share OTP immediately!"
        result = await detector.analyze(message)

        assert len(result.category_scores) > 0
        assert result.category_scores[ScamCategory.URGENCY] > 0
        assert result.category_scores[ScamCategory.AUTHORITY] > 0

    @pytest.mark.asyncio
    async def test_conversation_history_context(self, detector: ScamDetector):
        """Should consider conversation history."""
        from src.api.schemas import ConversationMessage, SenderType
        from datetime import datetime

        history = [
            ConversationMessage(
                sender=SenderType.SCAMMER,
                text="Your account has suspicious activity",
                timestamp=datetime.now(),
            ),
        ]

        message = "Share your password to verify"
        result = await detector.analyze(message, history=history)

        # History should boost confidence
        assert result.is_scam is True
```

## Verification Checklist

- [ ] `src/detection/patterns.py` defines all scam indicator patterns
- [ ] Patterns cover: urgency, authority, threat, request, financial, phishing
- [ ] `src/detection/detector.py` implements `ScamDetector` class
- [ ] `DetectionResult` includes confidence score and matched patterns
- [ ] Confidence calculation considers multiple categories
- [ ] Tests cover obvious scams, edge cases, and false positive prevention
- [ ] All tests pass: `pytest tests/test_detection.py -v`

## Testing Examples

```python
# Quick test in Python REPL
from src.detection.detector import ScamDetector

detector = ScamDetector()

# Test obvious scam
import asyncio
result = asyncio.run(detector.analyze(
    "URGENT: Your SBI account blocked! Share OTP now to avoid arrest!"
))
print(f"Is scam: {result.is_scam}, Confidence: {result.confidence:.2f}")
print(f"Reasoning: {result.reasoning}")
```

## Next Steps

After completing this milestone, proceed to **Milestone 4: Agent Engagement** to implement the LangChain-based honeypot agent.
