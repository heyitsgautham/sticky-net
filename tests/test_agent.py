"""Tests for honeypot agent module."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.agents.honeypot_agent import EngagementResult, HoneypotAgent
from src.agents.persona import Persona
from src.agents.prompts import (
    format_scam_indicators,
    get_response_strategy,
)
from src.api.schemas import ConversationMessage, Message, Metadata, SenderType
from src.detection.detector import DetectionResult


def create_mock_gemini_response(text: str) -> MagicMock:
    """Create a mock Gemini response with proper candidates structure.

    Gemini 3 models return responses with candidates containing content parts.
    This helper creates a properly structured mock for testing.
    """
    mock_part = MagicMock()
    mock_part.text = text

    mock_content = MagicMock()
    mock_content.parts = [mock_part]

    mock_candidate = MagicMock()
    mock_candidate.content = mock_content

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]
    mock_response.text = text  # Keep for backward compatibility

    return mock_response


class TestPrompts:
    """Tests for prompt utilities."""

    def test_get_response_strategy_returns_list(self):
        """Should return response strategies."""
        strategies = get_response_strategy("urgency")
        assert isinstance(strategies, list)
        assert len(strategies) > 0

    def test_get_response_strategy_fallback(self):
        """Should return default for unknown category."""
        strategies = get_response_strategy("unknown")
        assert isinstance(strategies, list)

    def test_format_scam_indicators_empty(self):
        """Should handle empty indicators."""
        result = format_scam_indicators([])
        assert "detected" in result.lower()

    def test_format_scam_indicators_list(self):
        """Should format indicator list."""
        result = format_scam_indicators(["urgency", "authority"])
        assert "urgency" in result
        assert "authority" in result


class TestHoneypotAgent:
    """Tests for HoneypotAgent class."""

    @pytest.fixture
    def mock_detection(self) -> DetectionResult:
        """Create mock detection result."""
        return DetectionResult(
            is_scam=True,
            confidence=0.85,
            scam_type="banking_fraud",
            reasoning="Scam detected",
        )

    @pytest.fixture
    def mock_message(self) -> Message:
        """Create mock message."""
        return Message(
            sender=SenderType.SCAMMER,
            text="Your account will be blocked! Share OTP immediately!",
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def mock_metadata(self) -> Metadata:
        """Create mock metadata."""
        return Metadata(channel="SMS", language="English", locale="IN")

    @patch("src.agents.honeypot_agent.genai.Client")
    @pytest.mark.asyncio
    async def test_engage_returns_result(
        self,
        mock_client_class,
        mock_message: Message,
        mock_metadata: Metadata,
        mock_detection: DetectionResult,
    ):
        """Agent engagement should return valid result."""
        # Setup mock Gemini client
        mock_client = MagicMock()
        mock_response = create_mock_gemini_response("Oh no! What should I do?")
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        agent = HoneypotAgent()
        result = await agent.engage(
            message=mock_message,
            history=[],
            metadata=mock_metadata,
            detection=mock_detection,
        )

        assert isinstance(result, EngagementResult)
        assert result.response != ""
        assert result.conversation_id != ""
        assert result.duration_seconds >= 0

    @patch("src.agents.honeypot_agent.genai.Client")
    @pytest.mark.asyncio
    async def test_engage_uses_history(
        self,
        mock_client_class,
        mock_message: Message,
        mock_metadata: Metadata,
        mock_detection: DetectionResult,
    ):
        """Agent should use conversation history."""
        mock_client = MagicMock()
        mock_response = create_mock_gemini_response("I understand, please help me.")
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        history = [
            ConversationMessage(
                sender=SenderType.SCAMMER,
                text="Your account has issues",
                timestamp=datetime.now(),
            ),
            ConversationMessage(
                sender=SenderType.USER,
                text="What issues?",
                timestamp=datetime.now(),
            ),
        ]

        agent = HoneypotAgent()
        result = await agent.engage(
            message=mock_message,
            history=history,
            metadata=mock_metadata,
            detection=mock_detection,
        )

        # Verify LLM was called
        mock_client.models.generate_content.assert_called_once()
        # Verify result is valid
        assert result.response != ""

    @patch("src.agents.honeypot_agent.genai.Client")
    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(
        self,
        mock_client_class,
        mock_message: Message,
        mock_metadata: Metadata,
        mock_detection: DetectionResult,
    ):
        """Should return fallback response on LLM error."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("LLM Error")
        mock_client_class.return_value = mock_client

        agent = HoneypotAgent()
        result = await agent.engage(
            message=mock_message,
            history=[],
            metadata=mock_metadata,
            detection=mock_detection,
        )

        # Should still return a valid response
        assert result.response != ""
        assert len(result.response) > 10

    @patch("src.agents.honeypot_agent.genai.Client")
    def test_end_conversation(self, mock_client_class):
        """Should clean up persona on end."""
        mock_client_class.return_value = MagicMock()

        agent = HoneypotAgent()
        # Create a persona first
        agent.persona_manager.get_or_create_persona("conv-123")

        # End conversation
        agent.end_conversation("conv-123")

        # Persona should be cleared (new one created on access)
        new_persona = agent.persona_manager.get_or_create_persona("conv-123")
        assert new_persona.engagement_turn == 0


class TestConversationSummary:
    """Tests for conversation summary generation when history > context window."""

    @patch("src.agents.honeypot_agent.genai.Client")
    def test_summary_generated_for_long_history(self, mock_client_class):
        """Summary should be generated when history exceeds context window."""
        mock_client_class.return_value = MagicMock()
        agent = HoneypotAgent()

        # Create a 12-message history (exceeds default context_window_turns=8)
        history = []
        for i in range(12):
            sender = SenderType.SCAMMER if i % 2 == 0 else SenderType.USER
            text = f"Turn {i + 1} message text here"
            if i == 2:
                text = "Call me at +91-9876543210 for verification"
            history.append(
                ConversationMessage(
                    sender=sender,
                    text=text,
                    timestamp=datetime.now(),
                )
            )

        detection = DetectionResult(
            is_scam=True,
            confidence=0.9,
            scam_type="banking_fraud",
            reasoning="test",
        )
        message = Message(
            sender=SenderType.SCAMMER,
            text="Send money now!",
            timestamp=datetime.now(),
        )

        prompt = agent._build_prompt(
            message=message,
            history=history,
            detection=detection,
            persona=Persona(),
        )

        # Summary header should be present
        assert "SUMMARY OF EARLIER" in prompt
        # Phone number from truncated Turn 3 should appear in summary
        assert "9876543210" in prompt

    @patch("src.agents.honeypot_agent.genai.Client")
    def test_no_summary_for_short_history(self, mock_client_class):
        """No summary should be generated when history fits in context window."""
        mock_client_class.return_value = MagicMock()
        agent = HoneypotAgent()

        history = [
            ConversationMessage(
                sender=SenderType.SCAMMER,
                text="Your account is blocked",
                timestamp=datetime.now(),
            ),
            ConversationMessage(
                sender=SenderType.USER,
                text="Oh no what happened",
                timestamp=datetime.now(),
            ),
        ]

        detection = DetectionResult(
            is_scam=True,
            confidence=0.9,
            scam_type="banking_fraud",
            reasoning="test",
        )
        message = Message(
            sender=SenderType.SCAMMER,
            text="Verify now!",
            timestamp=datetime.now(),
        )

        prompt = agent._build_prompt(
            message=message,
            history=history,
            detection=detection,
            persona=Persona(),
        )

        assert "SUMMARY" not in prompt
        assert "CONVERSATION HISTORY" in prompt

    @patch("src.agents.honeypot_agent.genai.Client")
    def test_summary_preserves_upi_patterns(self, mock_client_class):
        """Summary should capture UPI IDs from truncated turns."""
        mock_client_class.return_value = MagicMock()
        agent = HoneypotAgent()

        # 10-message history; UPI shared in turn 1 (will be truncated with window=8)
        history = []
        history.append(
            ConversationMessage(
                sender=SenderType.SCAMMER,
                text="Send payment to scammer.fraud@ybl right now",
                timestamp=datetime.now(),
            )
        )
        history.append(
            ConversationMessage(
                sender=SenderType.USER,
                text="ok let me try",
                timestamp=datetime.now(),
            )
        )
        for i in range(8):
            sender = SenderType.SCAMMER if i % 2 == 0 else SenderType.USER
            history.append(
                ConversationMessage(
                    sender=sender,
                    text=f"Follow up message {i + 3}",
                    timestamp=datetime.now(),
                )
            )

        detection = DetectionResult(
            is_scam=True,
            confidence=0.9,
            scam_type="upi_fraud",
            reasoning="test",
        )
        message = Message(
            sender=SenderType.SCAMMER,
            text="Did you send?",
            timestamp=datetime.now(),
        )

        prompt = agent._build_prompt(
            message=message,
            history=history,
            detection=detection,
            persona=Persona(),
        )

        assert "SUMMARY" in prompt
        assert "scammer.fraud@ybl" in prompt

    @patch("src.agents.honeypot_agent.genai.Client")
    def test_summary_preserves_urls(self, mock_client_class):
        """Summary should capture phishing URLs from truncated turns."""
        mock_client_class.return_value = MagicMock()
        agent = HoneypotAgent()

        history = []
        history.append(
            ConversationMessage(
                sender=SenderType.SCAMMER,
                text="Click here to verify: http://amaz0n-deals.fake-site.com/claim",
                timestamp=datetime.now(),
            )
        )
        for i in range(9):
            sender = SenderType.USER if i % 2 == 0 else SenderType.SCAMMER
            history.append(
                ConversationMessage(
                    sender=sender,
                    text=f"Message {i + 2}",
                    timestamp=datetime.now(),
                )
            )

        detection = DetectionResult(
            is_scam=True,
            confidence=0.9,
            scam_type="phishing",
            reasoning="test",
        )
        message = Message(
            sender=SenderType.SCAMMER,
            text="Did you click?",
            timestamp=datetime.now(),
        )

        prompt = agent._build_prompt(
            message=message,
            history=history,
            detection=detection,
            persona=Persona(),
        )

        assert "SUMMARY" in prompt
        assert "amaz0n-deals.fake-site.com" in prompt

    @patch("src.agents.honeypot_agent.genai.Client")
    def test_summary_word_budget(self, mock_client_class):
        """Summary should not exceed 200 words."""
        mock_client_class.return_value = MagicMock()
        agent = HoneypotAgent()

        # Create many long messages to test word budget
        history = []
        for i in range(20):
            sender = SenderType.SCAMMER if i % 2 == 0 else SenderType.USER
            history.append(
                ConversationMessage(
                    sender=sender,
                    text=f"This is a very long message number {i + 1} with lots of words to test budget "
                    * 5,
                    timestamp=datetime.now(),
                )
            )

        older_turns = history[:-8]
        summary = agent._generate_conversation_summary(older_turns)

        word_count = len(summary.split())
        assert word_count <= 210, f"Summary has {word_count} words, should be <= ~200"
