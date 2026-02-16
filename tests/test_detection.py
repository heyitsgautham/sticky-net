"""Tests for pure AI scam detection module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from src.detection.detector import ScamDetector, DetectionResult
from src.detection.classifier import ScamClassifier, ClassificationResult


# Mock genai.Client at module level for all tests that need it
@pytest.fixture
def mock_genai_client():
    """Mock the genai.Client to avoid API credentials issues."""
    with patch("src.detection.classifier.genai.Client") as mock_client:
        yield mock_client


class TestScamDetector:
    """Tests for pure AI ScamDetector class."""

    @pytest.fixture
    def detector(self, mock_genai_client) -> ScamDetector:
        """Create detector instance with mocked AI client."""
        return ScamDetector()

    @pytest.mark.asyncio
    async def test_detects_scam_above_threshold(self, detector: ScamDetector):
        """Messages with confidence >= 0.6 should be classified as scam."""
        with patch.object(detector.classifier, 'classify') as mock_classify:
            mock_classify.return_value = ClassificationResult(
                is_scam=True,
                confidence=0.75,
                scam_type="banking_fraud",
                reasoning="Bank impersonation detected",
                threat_indicators=["urgency", "account_threat"]
            )
            
            message = "Your account is blocked. Send OTP immediately!"
            result = await detector.analyze(message)

            assert result.is_scam is True
            # Regex fast-path catches this with its own confidence (>= 0.75)
            assert result.confidence >= 0.75
            assert result.scam_type == "banking_fraud"

    @pytest.mark.asyncio
    async def test_not_scam_below_threshold(self, detector: ScamDetector):
        """Non-scam messages get safety-net engagement (cautious mode)."""
        with patch.object(detector.classifier, 'classify') as mock_classify:
            mock_classify.return_value = ClassificationResult(
                is_scam=False,
                confidence=0.25,
                reasoning="Normal greeting"
            )
            
            message = "Hello, how are you?"
            result = await detector.analyze(message)

            # Safety net: always engage cautiously even if both regex + LLM miss
            assert result.is_scam is True
            assert result.confidence >= 0.65

    @pytest.mark.asyncio
    async def test_confidence_never_decreases(self, detector: ScamDetector):
        """Confidence should never decrease from previous detection."""
        previous_result = DetectionResult(
            is_scam=True,
            confidence=0.8,
            reasoning="Previous scam detection",
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
    async def test_uses_conversation_history(self, detector: ScamDetector):
        """Detector should pass conversation history to classifier."""
        from src.api.schemas import ConversationMessage, SenderType
        
        with patch.object(detector.classifier, 'classify') as mock_classify:
            mock_classify.return_value = ClassificationResult(
                is_scam=True,
                confidence=0.85,
                scam_type="support_scam",
                reasoning="Multi-turn scam pattern"
            )
            
            history = [
                ConversationMessage(
                    sender=SenderType.SCAMMER,
                    text="Hi, I'm from support",
                    timestamp=datetime.now(),
                ),
            ]
            
            result = await detector.analyze(
                message="There's a problem with your account",
                history=history,
            )

            # Verify classifier was called with history
            call_args = mock_classify.call_args
            assert call_args.kwargs.get('history') == history

    @pytest.mark.asyncio
    async def test_uses_metadata(self, detector: ScamDetector):
        """Detector should pass metadata to classifier."""
        from src.api.schemas import Metadata
        
        with patch.object(detector.classifier, 'classify') as mock_classify:
            mock_classify.return_value = ClassificationResult(
                is_scam=False,
                confidence=0.3,
                reasoning="Normal message"
            )
            
            metadata = Metadata(channel="SMS", language="English", locale="IN")
            
            result = await detector.analyze(
                message="Hello there",
                metadata=metadata,
            )

            # Verify classifier was called with metadata
            call_args = mock_classify.call_args
            assert call_args.kwargs.get('metadata') == metadata


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
