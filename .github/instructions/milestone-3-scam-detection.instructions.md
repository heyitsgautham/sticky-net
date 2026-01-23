---
#applyTo: "**"
---

# Milestone 3: Scam Detection (Hybrid Architecture)

> **Goal**: Implement the hybrid scam detection module using regex pre-filter + AI classification with Gemini 3 Flash.

## Architecture Overview

```
Message → [Regex Pre-Filter: 10ms] → Obvious scam? → Engage directly
                │                  → Obvious safe? → Return neutral
                │                  → Uncertain? → Continue ↓
                ▼
         [AI Classifier: 150ms] → is_scam + confidence + scam_type
         (gemini-3-flash-preview)
                │
                ▼
         Route to engagement or monitoring based on confidence
```

## Prerequisites

- Milestone 1 & 2 completed
- API layer functional
- Google Cloud project with Vertex AI enabled
- `google-genai` library installed

## Tasks

### 3.1 Define Scam Detection Patterns (Regex Pre-Filter)

#### src/detection/patterns.py

```python
"""Scam detection patterns and indicators for regex pre-filter."""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Pattern as RePattern


class ScamCategory(str, Enum):
    """Categories of scam tactics."""

    URGENCY = "urgency"
    AUTHORITY = "authority"
    THREAT = "threat"
    REQUEST = "request"
    FINANCIAL = "financial"
    PHISHING = "phishing"


class PreFilterResult(str, Enum):
    """Result of regex pre-filter classification."""
    
    OBVIOUS_SCAM = "obvious_scam"      # Skip AI, engage immediately
    OBVIOUS_SAFE = "obvious_safe"      # Skip AI, return neutral
    UNCERTAIN = "uncertain"            # Needs AI classification


@dataclass
class Pattern:
    """A scam indicator pattern."""

    category: ScamCategory
    pattern: RePattern[str]
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

# ============================================================
# INSTANT SCAM PATTERNS - Skip AI, engage immediately (95%+ confidence)
# ============================================================
INSTANT_SCAM_PATTERNS = [
    re.compile(r"send\s+(your\s+)?(otp|password|pin|cvv)", re.I),
    re.compile(r"verify\s+within\s+\d+\s+(hours?|minutes?)", re.I),
    re.compile(r"account\s+(will\s+be\s+)?(blocked|suspended|locked).*immediately", re.I),
    re.compile(r"click\s+(here|link).*verify", re.I),
    re.compile(r"(lottery|jackpot|won)\s+[₹$]?\s*\d+", re.I),
    re.compile(r"share\s+(your\s+)?(otp|cvv|pin)\s+(to|for)", re.I),
    re.compile(r"(arrest|legal\s+action).*immediately", re.I),
]

# ============================================================
# SAFE PATTERNS - Skip AI, return neutral (legitimate messages)
# ============================================================
SAFE_PATTERNS = [
    re.compile(r"your\s+otp\s+is\s+\d{4,6}", re.I),  # OTP delivery from services
    re.compile(r"transaction\s+of\s+rs\.?\s*\d+.*debited", re.I),  # Bank notifications
    re.compile(r"your\s+order\s+#?\d+\s+has\s+been", re.I),  # Order confirmations
    re.compile(r"otp\s+for\s+.*is\s+\d{4,6}", re.I),  # OTP format
]

# All weighted patterns for scoring
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
    """Match text against all weighted patterns."""
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


def pre_filter(text: str) -> PreFilterResult:
    """
    Fast regex pre-filter to skip AI for obvious cases.
    
    Returns:
        OBVIOUS_SCAM: High-confidence scam, skip AI and engage immediately
        OBVIOUS_SAFE: Legitimate message, skip AI and return neutral
        UNCERTAIN: Needs AI classification
    """
    # Check for obvious scams first
    for pattern in INSTANT_SCAM_PATTERNS:
        if pattern.search(text):
            return PreFilterResult.OBVIOUS_SCAM
    
    # Check for safe patterns
    for pattern in SAFE_PATTERNS:
        if pattern.search(text):
            return PreFilterResult.OBVIOUS_SAFE
    
    # Uncertain - needs AI classification
    return PreFilterResult.UNCERTAIN
```

### 3.2 Implement AI Scam Classifier

#### src/detection/classifier.py

```python
"""AI-based scam classification using Gemini 3 Flash."""

import json
from dataclasses import dataclass
from typing import Any

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
    threat_indicators: list[str] | None = None
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
        previous_classification: ClassificationResult | None = None,
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
            prev_text = f"is_scam={previous_classification.is_scam}, confidence={previous_classification.confidence}"
        
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
                )
            )
            
            return self._parse_response(response.text)
            
        except Exception as e:
            self.logger.error("AI classification failed", error=str(e))
            # Return uncertain result on failure
            return ClassificationResult(
                is_scam=False,
                confidence=0.5,
                reasoning=f"AI classification failed: {str(e)}"
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
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            data = json.loads(text)
            
            return ClassificationResult(
                is_scam=bool(data.get("is_scam", False)),
                confidence=float(data.get("confidence", 0.5)),
                scam_type=data.get("scam_type"),
                threat_indicators=data.get("threat_indicators", []),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.warning("Failed to parse AI response", error=str(e), response=response_text[:200])
            return ClassificationResult(
                is_scam=False,
                confidence=0.5,
                reasoning=f"Parse error: {str(e)}"
            )
```

### 3.3 Implement Hybrid Scam Detector

#### src/detection/detector.py

```python
"""Hybrid scam detection: regex pre-filter + AI classification."""

from dataclasses import dataclass, field
from typing import Any

import structlog

from src.api.schemas import ConversationMessage, Metadata
from src.detection.patterns import (
    ScamCategory,
    PatternMatch,
    PreFilterResult,
    match_all_patterns,
    pre_filter,
)
from src.detection.classifier import ScamClassifier, ClassificationResult

logger = structlog.get_logger()


@dataclass
class DetectionResult:
    """Result of hybrid scam detection."""

    is_scam: bool
    confidence: float  # 0.0 to 1.0
    scam_type: str | None = None
    matched_patterns: list[PatternMatch] = field(default_factory=list)
    category_scores: dict[ScamCategory, float] = field(default_factory=dict)
    reasoning: str = ""
    detection_method: str = "hybrid"  # "regex_fast_path" | "ai_classification" | "hybrid"


class ScamDetector:
    """
    Hybrid scam detector combining regex pre-filter with AI classification.
    
    Flow:
    1. Regex pre-filter for obvious cases (fast path)
    2. AI classification for uncertain cases (semantic understanding)
    3. Combined result with confidence and reasoning
    """

    # Thresholds
    SCAM_THRESHOLD = 0.6
    OBVIOUS_SCAM_CONFIDENCE = 0.95
    OBVIOUS_SAFE_CONFIDENCE = 0.05

    def __init__(self) -> None:
        """Initialize the detector with AI classifier."""
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
        Analyze a message for scam indicators using hybrid approach.

        Args:
            message: The message text to analyze
            history: Previous messages in the conversation
            metadata: Additional context about the message
            previous_result: Previous detection result for state tracking

        Returns:
            DetectionResult with scam classification and confidence
        """
        self.logger.info("Analyzing message", message_length=len(message))

        # Step 1: Regex pre-filter for fast path
        pre_filter_result = pre_filter(message)
        pattern_matches = match_all_patterns(message)
        
        if pre_filter_result == PreFilterResult.OBVIOUS_SCAM:
            self.logger.info("Obvious scam detected via regex fast path")
            return self._build_result(
                is_scam=True,
                confidence=self.OBVIOUS_SCAM_CONFIDENCE,
                matches=pattern_matches,
                reasoning="Obvious scam pattern detected (fast path)",
                method="regex_fast_path",
            )
        
        if pre_filter_result == PreFilterResult.OBVIOUS_SAFE:
            self.logger.info("Obvious safe message detected via regex fast path")
            return self._build_result(
                is_scam=False,
                confidence=self.OBVIOUS_SAFE_CONFIDENCE,
                matches=pattern_matches,
                reasoning="Legitimate message pattern detected (fast path)",
                method="regex_fast_path",
            )
        
        # Step 2: AI classification for uncertain cases
        self.logger.info("Uncertain message, using AI classification")
        
        # Convert previous result to ClassificationResult for AI context
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
        
        # Step 3: Combine regex patterns with AI result
        final_confidence = self._combine_confidence(
            ai_confidence=ai_result.confidence,
            pattern_matches=pattern_matches,
            previous_confidence=previous_result.confidence if previous_result else None,
        )
        
        return self._build_result(
            is_scam=final_confidence >= self.SCAM_THRESHOLD,
            confidence=final_confidence,
            matches=pattern_matches,
            reasoning=ai_result.reasoning,
            method="ai_classification",
            scam_type=ai_result.scam_type,
        )
    
    def _combine_confidence(
        self,
        ai_confidence: float,
        pattern_matches: list[PatternMatch],
        previous_confidence: float | None,
    ) -> float:
        """Combine AI confidence with pattern matching and history."""
        # Start with AI confidence
        confidence = ai_confidence
        
        # Boost based on pattern matches
        if pattern_matches:
            pattern_boost = min(0.15, len(pattern_matches) * 0.03)
            confidence = min(1.0, confidence + pattern_boost)
        
        # KEY: Confidence can only INCREASE (prevents false negative oscillation)
        if previous_confidence is not None:
            confidence = max(confidence, previous_confidence)
        
        return confidence
    
    def _build_result(
        self,
        is_scam: bool,
        confidence: float,
        matches: list[PatternMatch],
        reasoning: str,
        method: str,
        scam_type: str | None = None,
    ) -> DetectionResult:
        """Build detection result with category scores."""
        category_scores = self._calculate_category_scores(matches)
        
        return DetectionResult(
            is_scam=is_scam,
            confidence=confidence,
            scam_type=scam_type,
            matched_patterns=matches,
            category_scores=category_scores,
            reasoning=reasoning,
            detection_method=method,
        )
    
    def _calculate_category_scores(
        self, matches: list[PatternMatch]
    ) -> dict[ScamCategory, float]:
        """Calculate normalized scores per category."""
        scores: dict[ScamCategory, list[float]] = {cat: [] for cat in ScamCategory}

        for match in matches:
            scores[match.category].append(match.weight)

        return {
            cat: min(1.0, sum(weights) / max(1, len(weights)) if weights else 0.0)
            for cat, weights in scores.items()
        }
```

### 3.4 Create Detection Module Init

#### src/detection/__init__.py

```python
"""Scam detection module with hybrid regex + AI approach."""

from src.detection.detector import ScamDetector, DetectionResult
from src.detection.classifier import ScamClassifier, ClassificationResult
from src.detection.patterns import (
    ScamCategory,
    Pattern,
    PatternMatch,
    PreFilterResult,
    pre_filter,
    match_all_patterns,
)

__all__ = [
    "ScamDetector",
    "DetectionResult",
    "ScamClassifier",
    "ClassificationResult",
    "ScamCategory",
    "Pattern",
    "PatternMatch",
    "PreFilterResult",
    "pre_filter",
    "match_all_patterns",
]
```

### 3.5 Write Detection Tests

#### tests/test_detection.py

```python
"""Tests for hybrid scam detection module."""

import pytest
from unittest.mock import AsyncMock, patch

from src.detection.detector import ScamDetector, DetectionResult
from src.detection.classifier import ScamClassifier, ClassificationResult
from src.detection.patterns import (
    ScamCategory,
    PreFilterResult,
    match_all_patterns,
    pre_filter,
    URGENCY_PATTERNS,
    REQUEST_PATTERNS,
)


class TestRegexPreFilter:
    """Tests for regex pre-filter fast path."""

    def test_obvious_scam_otp_request(self):
        """Should detect obvious OTP scam via fast path."""
        result = pre_filter("Send your OTP immediately to verify account")
        assert result == PreFilterResult.OBVIOUS_SCAM

    def test_obvious_scam_account_blocked(self):
        """Should detect account blocked scam via fast path."""
        result = pre_filter("Your account will be blocked immediately! Click here")
        assert result == PreFilterResult.OBVIOUS_SCAM

    def test_obvious_safe_otp_delivery(self):
        """Should recognize legitimate OTP delivery."""
        result = pre_filter("Your OTP is 123456 for login")
        assert result == PreFilterResult.OBVIOUS_SAFE

    def test_obvious_safe_bank_notification(self):
        """Should recognize legitimate bank notification."""
        result = pre_filter("Transaction of Rs. 500 debited from your account")
        assert result == PreFilterResult.OBVIOUS_SAFE

    def test_uncertain_message(self):
        """Ambiguous messages should return UNCERTAIN."""
        result = pre_filter("Hi, I'm calling from customer support about your account")
        assert result == PreFilterResult.UNCERTAIN

    def test_uncertain_normal_greeting(self):
        """Normal greetings should return UNCERTAIN."""
        result = pre_filter("Hello, how are you today?")
        assert result == PreFilterResult.UNCERTAIN


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


class TestScamDetector:
    """Tests for hybrid ScamDetector class."""

    @pytest.fixture
    def detector(self) -> ScamDetector:
        """Create detector instance."""
        return ScamDetector()

    @pytest.mark.asyncio
    async def test_obvious_scam_uses_fast_path(self, detector: ScamDetector):
        """Obvious scams should use regex fast path, not AI."""
        message = "URGENT: Send OTP immediately or your account will be blocked!"
        
        result = await detector.analyze(message)

        assert result.is_scam is True
        assert result.confidence >= 0.9
        assert result.detection_method == "regex_fast_path"

    @pytest.mark.asyncio
    async def test_obvious_safe_uses_fast_path(self, detector: ScamDetector):
        """Obvious safe messages should use regex fast path."""
        message = "Your OTP is 456789 for Amazon login"
        
        result = await detector.analyze(message)

        assert result.is_scam is False
        assert result.confidence <= 0.1
        assert result.detection_method == "regex_fast_path"

    @pytest.mark.asyncio
    @patch.object(ScamClassifier, 'classify')
    async def test_uncertain_uses_ai_classification(
        self, mock_classify: AsyncMock, detector: ScamDetector
    ):
        """Uncertain messages should use AI classification."""
        mock_classify.return_value = ClassificationResult(
            is_scam=True,
            confidence=0.75,
            scam_type="support_scam",
            reasoning="Support impersonation pattern"
        )
        
        message = "Hi, I'm from customer support. There's an issue with your account."
        
        result = await detector.analyze(message)

        assert result.detection_method == "ai_classification"
        mock_classify.assert_called_once()

    @pytest.mark.asyncio
    async def test_confidence_never_decreases(self, detector: ScamDetector):
        """Confidence should never decrease from previous detection."""
        previous_result = DetectionResult(
            is_scam=True,
            confidence=0.8,
            reasoning="Previous scam detection",
            detection_method="ai_classification",
        )
        
        # Even a benign-looking follow-up should not reduce confidence
        with patch.object(detector.classifier, 'classify') as mock_classify:
            mock_classify.return_value = ClassificationResult(
                is_scam=False,
                confidence=0.3,
                reasoning="Seems benign"
            )
            
            result = await detector.analyze(
                "Okay, I understand",
                previous_result=previous_result
            )

        # Confidence should stay at 0.8, not drop to 0.3
        assert result.confidence >= 0.8


class TestScamClassifier:
    """Tests for AI ScamClassifier."""

    @pytest.fixture
    def classifier(self) -> ScamClassifier:
        """Create classifier instance."""
        return ScamClassifier()

    def test_format_history(self, classifier: ScamClassifier):
        """Should format conversation history correctly."""
        from src.api.schemas import ConversationMessage, SenderType
        from datetime import datetime

        history = [
            ConversationMessage(
                sender=SenderType.SCAMMER,
                text="Your account is blocked",
                timestamp=datetime.now(),
            ),
            ConversationMessage(
                sender=SenderType.USER,
                text="What? How do I fix it?",
                timestamp=datetime.now(),
            ),
        ]

        result = classifier._format_history(history)

        assert "[SCAMMER]:" in result
        assert "[USER]:" in result
        assert "Your account is blocked" in result

    def test_parse_valid_response(self, classifier: ScamClassifier):
        """Should parse valid JSON response."""
        response = '{"is_scam": true, "confidence": 0.85, "scam_type": "banking", "reasoning": "Test"}'
        
        result = classifier._parse_response(response)

        assert result.is_scam is True
        assert result.confidence == 0.85
        assert result.scam_type == "banking"

    def test_parse_invalid_response(self, classifier: ScamClassifier):
        """Should handle invalid JSON gracefully."""
        response = "This is not valid JSON"
        
        result = classifier._parse_response(response)

        # Should return safe default, not crash
        assert result.is_scam is False
        assert result.confidence == 0.5
```

## Verification Checklist

- [ ] `src/detection/patterns.py` defines regex patterns AND pre-filter logic
- [ ] `src/detection/classifier.py` implements AI classification with Gemini 3 Flash
- [ ] `src/detection/detector.py` implements hybrid detection flow
- [ ] Pre-filter correctly identifies OBVIOUS_SCAM, OBVIOUS_SAFE, UNCERTAIN
- [ ] AI classifier uses `gemini-3-flash-preview` with LOW thinking level
- [ ] Confidence never decreases (state escalation only)
- [ ] Fallback to regex on AI failure
- [ ] Tests cover fast path, AI path, and edge cases
- [ ] All tests pass: `pytest tests/test_detection.py -v`

## Testing Examples

```python
# Quick test in Python REPL
import asyncio
from src.detection.detector import ScamDetector

detector = ScamDetector()

# Test obvious scam (fast path)
result = asyncio.run(detector.analyze(
    "URGENT: Send OTP now or account blocked!"
))
print(f"Fast path - Is scam: {result.is_scam}, Method: {result.detection_method}")

# Test uncertain message (AI path)
result = asyncio.run(detector.analyze(
    "Hi, I'm from customer support about your account"
))
print(f"AI path - Is scam: {result.is_scam}, Confidence: {result.confidence:.2f}")
```

## Next Steps

After completing this milestone, proceed to **Milestone 4: Agent Engagement** to implement the Gemini 3 Pro-based honeypot agent.

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
