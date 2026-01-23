"""Tests for hybrid scam detection module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

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


# Mock genai.Client at module level for all tests that need it
@pytest.fixture
def mock_genai_client():
    """Mock the genai.Client to avoid API credentials issues."""
    with patch("src.detection.classifier.genai.Client") as mock_client:
        yield mock_client


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

    def test_obvious_scam_lottery_win(self):
        """Should detect lottery scam via fast path."""
        result = pre_filter("You have won $50000 in lottery!")
        assert result == PreFilterResult.OBVIOUS_SCAM

    def test_obvious_safe_otp_delivery(self):
        """Should recognize legitimate OTP delivery."""
        result = pre_filter("Your OTP is 123456 for login")
        assert result == PreFilterResult.OBVIOUS_SAFE

    def test_obvious_safe_bank_notification(self):
        """Should recognize legitimate bank notification."""
        result = pre_filter("Transaction of Rs. 500 debited from your account")
        assert result == PreFilterResult.OBVIOUS_SAFE

    def test_obvious_safe_order_confirmation(self):
        """Should recognize order confirmation."""
        result = pre_filter("Your order #12345 has been shipped")
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

    def test_threat_pattern_matches_blocked(self):
        """Threat patterns should match account threats."""
        matches = match_all_patterns("Your account will be blocked today")
        threat_matches = [m for m in matches if m.category == ScamCategory.THREAT]
        assert len(threat_matches) >= 1

    def test_financial_pattern_matches_upi(self):
        """Financial patterns should match payment methods."""
        matches = match_all_patterns("Send money via UPI to this account")
        financial_matches = [m for m in matches if m.category == ScamCategory.FINANCIAL]
        assert len(financial_matches) >= 1

    def test_no_matches_for_normal_message(self):
        """Normal messages should have few or no matches."""
        matches = match_all_patterns("Hello, how are you doing today?")
        assert len(matches) <= 1


class TestScamDetector:
    """Tests for hybrid ScamDetector class."""

    @pytest.fixture
    def detector(self, mock_genai_client) -> ScamDetector:
        """Create detector instance with mocked AI client."""
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
    async def test_uncertain_uses_ai_classification(self, detector: ScamDetector):
        """Uncertain messages should use AI classification."""
        with patch.object(detector.classifier, 'classify') as mock_classify:
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

    @pytest.mark.asyncio
    async def test_category_scores_calculated(self, detector: ScamDetector):
        """Category scores should be calculated from pattern matches."""
        message = "URGENT: Your SBI account will be blocked! Share OTP now!"
        
        result = await detector.analyze(message)
        
        assert ScamCategory.URGENCY in result.category_scores
        assert ScamCategory.AUTHORITY in result.category_scores


class TestScamClassifier:
    """Tests for AI ScamClassifier."""

    @pytest.fixture
    def classifier(self, mock_genai_client) -> ScamClassifier:
        """Create classifier instance with mocked AI client."""
        return ScamClassifier()

    def test_format_history_with_messages(self, classifier: ScamClassifier):
        """Should format conversation history correctly."""
        from src.api.schemas import ConversationMessage, SenderType

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

    def test_format_history_empty(self, classifier: ScamClassifier):
        """Should handle empty history."""
        result = classifier._format_history([])
        assert result == "No previous messages"

    def test_parse_valid_response(self, classifier: ScamClassifier):
        """Should parse valid JSON response."""
        response = '{"is_scam": true, "confidence": 0.85, "scam_type": "banking", "threat_indicators": ["urgency"], "reasoning": "Test"}'
        
        result = classifier._parse_response(response)

        assert result.is_scam is True
        assert result.confidence == 0.85
        assert result.scam_type == "banking"

    def test_parse_response_with_markdown(self, classifier: ScamClassifier):
        """Should handle JSON wrapped in markdown code blocks."""
        response = '```json\n{"is_scam": true, "confidence": 0.9, "scam_type": null, "reasoning": "Test"}\n```'
        
        result = classifier._parse_response(response)

        assert result.is_scam is True
        assert result.confidence == 0.9

    def test_parse_invalid_response(self, classifier: ScamClassifier):
        """Should handle invalid JSON gracefully."""
        response = "This is not valid JSON"
        
        result = classifier._parse_response(response)

        assert result.is_scam is False
        assert result.confidence == 0.5
