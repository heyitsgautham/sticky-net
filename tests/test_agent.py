"""Tests for honeypot agent module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agents.honeypot_agent import HoneypotAgent, EngagementResult
from src.agents.persona import Persona, PersonaManager, EmotionalState, PersonaTrait
from src.agents.policy import EngagementPolicy, EngagementMode, EngagementState
from src.agents.prompts import (
    get_response_strategy,
    format_scam_indicators,
    EXTRACTION_QUESTIONS,
)
from src.api.schemas import Message, ConversationMessage, Metadata, SenderType
from src.detection.detector import DetectionResult
from src.detection.patterns import ScamCategory, PatternMatch


class TestPersona:
    """Tests for Persona class."""

    def test_initial_state(self):
        """Persona should start with default values."""
        persona = Persona()
        assert persona.emotional_state == EmotionalState.CALM
        assert persona.engagement_turn == 0
        assert PersonaTrait.TRUSTING in persona.traits

    def test_emotional_state_updates_with_intensity(self):
        """Emotional state should reflect scam intensity when scam_type provided."""
        persona = Persona()

        # Without scam_type, high intensity = ANXIOUS (not PANICKED)
        persona.update_emotional_state(0.9, scam_type=None)
        assert persona.emotional_state == EmotionalState.ANXIOUS

        # With banking scam and high intensity = PANICKED
        persona.update_emotional_state(0.9, scam_type="banking_fraud")
        assert persona.emotional_state == EmotionalState.PANICKED

        # With banking scam and medium intensity = ANXIOUS
        persona.update_emotional_state(0.6, scam_type="banking_fraud")
        assert persona.emotional_state == EmotionalState.ANXIOUS

        # Without scam_type, low intensity = CALM
        persona.update_emotional_state(0.3, scam_type=None)
        assert persona.emotional_state == EmotionalState.CALM

    def test_increment_turn(self):
        """Turn counter should increment."""
        persona = Persona()
        assert persona.engagement_turn == 0

        persona.increment_turn()
        assert persona.engagement_turn == 1

        persona.increment_turn()
        assert persona.engagement_turn == 2

    def test_record_extraction(self):
        """Extraction count should track."""
        persona = Persona()
        assert persona.extracted_info_count == 0

        persona.record_extraction()
        assert persona.extracted_info_count == 1

    def test_get_emotional_modifier(self):
        """Should return varied modifiers for emotional states."""
        persona = Persona()
        
        # CALM state returns one of several options (including empty string)
        persona.emotional_state = EmotionalState.CALM
        calm_options = ["", "ok so ", "let me understand ", "hmm "]
        assert persona.get_emotional_modifier() in calm_options
        
        # PANICKED state returns one of several worried phrases
        persona.emotional_state = EmotionalState.PANICKED
        panicked_options = [
            "ok ok i am scared ",
            "please help me understand ",
            "my hands are shaking ",
            "what do i do ",
            "i dont want trouble ",
        ]
        assert persona.get_emotional_modifier() in panicked_options


class TestPersonaManager:
    """Tests for PersonaManager class."""

    def test_creates_new_persona(self):
        """Should create persona for new conversation."""
        manager = PersonaManager()
        persona = manager.get_or_create_persona("conv-123")

        assert persona is not None
        assert isinstance(persona, Persona)

    def test_returns_existing_persona(self):
        """Should return same persona for same conversation."""
        manager = PersonaManager()

        persona1 = manager.get_or_create_persona("conv-123")
        persona1.increment_turn()

        persona2 = manager.get_or_create_persona("conv-123")

        assert persona1 is persona2
        assert persona2.engagement_turn == 1

    def test_clear_persona(self):
        """Should remove persona when cleared."""
        manager = PersonaManager()

        manager.get_or_create_persona("conv-123")
        manager.clear_persona("conv-123")

        # Should create fresh persona
        new_persona = manager.get_or_create_persona("conv-123")
        assert new_persona.engagement_turn == 0

    def test_update_persona(self):
        """Should update persona state with scam type."""
        manager = PersonaManager()
        
        # Update with banking scam and high intensity
        persona = manager.update_persona("conv-123", scam_intensity=0.9, scam_type="banking_fraud")
        
        assert persona.engagement_turn == 1
        assert persona.emotional_state == EmotionalState.PANICKED
        
        # Update with no scam type should be less panicked
        persona2 = manager.update_persona("conv-456", scam_intensity=0.9, scam_type=None)
        assert persona2.emotional_state == EmotionalState.ANXIOUS

    def test_get_persona_context(self):
        """Should return context dict."""
        manager = PersonaManager()
        manager.get_or_create_persona("conv-123")
        
        context = manager.get_persona_context("conv-123")
        
        assert "emotional_state" in context
        assert "engagement_turn" in context
        assert "emotional_modifier" in context


class TestEngagementPolicy:
    """Tests for EngagementPolicy class."""

    def test_get_engagement_mode_aggressive(self):
        """Should return AGGRESSIVE for high confidence."""
        policy = EngagementPolicy()
        mode = policy.get_engagement_mode(0.90)
        assert mode == EngagementMode.AGGRESSIVE

    def test_get_engagement_mode_cautious(self):
        """Should return CAUTIOUS for medium confidence."""
        policy = EngagementPolicy()
        mode = policy.get_engagement_mode(0.70)
        assert mode == EngagementMode.CAUTIOUS

    def test_get_engagement_mode_none(self):
        """Should return NONE for low confidence."""
        policy = EngagementPolicy()
        mode = policy.get_engagement_mode(0.40)
        assert mode == EngagementMode.NONE

    def test_should_continue_within_limits(self):
        """Should continue when within limits."""
        policy = EngagementPolicy()
        state = EngagementState(
            mode=EngagementMode.AGGRESSIVE,
            turn_count=5,
            duration_seconds=100,
            intelligence_complete=False,
            scammer_suspicious=False,
            turns_since_new_info=2,
        )
        assert policy.should_continue(state) is True

    def test_should_not_continue_max_turns(self):
        """Should not continue when max turns reached."""
        policy = EngagementPolicy()
        state = EngagementState(
            mode=EngagementMode.CAUTIOUS,
            turn_count=15,  # More than cautious limit of 10
            duration_seconds=100,
            intelligence_complete=False,
            scammer_suspicious=False,
            turns_since_new_info=2,
        )
        assert policy.should_continue(state) is False

    def test_get_exit_reason_max_turns(self):
        """Should return correct exit reason."""
        policy = EngagementPolicy()
        state = EngagementState(
            mode=EngagementMode.CAUTIOUS,
            turn_count=15,
            duration_seconds=100,
            intelligence_complete=False,
            scammer_suspicious=False,
            turns_since_new_info=2,
        )
        reason = policy.get_exit_reason(state)
        assert reason is not None
        assert "turns" in reason.lower()

    def test_high_value_intelligence_complete_bank_and_phone(self):
        """Should detect high-value intel with bank account, phone, AND beneficiary name."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=["12345678901234"],
            phone_numbers=["9876543210"],
            beneficiary_names=["RAHUL KUMAR"],
        )
        assert result is True

    def test_high_value_intelligence_complete_upi_and_phone(self):
        """Should detect high-value intel with UPI, phone, AND beneficiary name."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=[],
            phone_numbers=["9876543210"],
            upi_ids=["scammer@ybl"],
            beneficiary_names=["RAHUL KUMAR"],
        )
        assert result is True

    def test_high_value_intelligence_incomplete_no_phone(self):
        """Should return False if no phone number."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=["12345678901234"],
            phone_numbers=[],
            upi_ids=["scammer@ybl"],
            beneficiary_names=["RAHUL KUMAR"],
        )
        assert result is False

    def test_high_value_intelligence_incomplete_no_bank_or_upi(self):
        """Should return False if no bank account or UPI."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=[],
            phone_numbers=["9876543210"],
            upi_ids=[],
            beneficiary_names=["RAHUL KUMAR"],
        )
        assert result is False

    def test_high_value_intelligence_incomplete_empty(self):
        """Should return False if everything is empty."""
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=[],
            phone_numbers=[],
        )
        assert result is False

    def test_high_value_intelligence_incomplete_no_beneficiary(self):
        """Should return False if no beneficiary name (CRITICAL - mule name required)."""
        # Even with UPI and phone, we need the beneficiary name to identify the mule
        result = EngagementPolicy.is_high_value_intelligence_complete(
            bank_accounts=[],
            phone_numbers=["9876543210"],
            upi_ids=["scammer@ybl"],
            beneficiary_names=[],  # Missing!
        )
        assert result is False

    def test_get_missing_intelligence_returns_beneficiary(self):
        """Should identify missing beneficiary name when UPI/phone present."""
        missing = EngagementPolicy.get_missing_intelligence(
            bank_accounts=[],
            phone_numbers=["9876543210"],
            upi_ids=["scammer@ybl"],
            beneficiary_names=[],
        )
        assert "beneficiary_name" in missing
        assert "payment_details" not in missing  # UPI is present
        assert "phone_number" not in missing  # Phone is present

    def test_get_missing_intelligence_complete(self):
        """Should return empty list when all intelligence is present."""
        missing = EngagementPolicy.get_missing_intelligence(
            bank_accounts=["12345678901234"],
            phone_numbers=["9876543210"],
            upi_ids=["scammer@ybl"],
            beneficiary_names=["RAHUL KUMAR"],
        )
        assert missing == []


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

    def test_extraction_questions_exist(self):
        """Should have extraction questions defined."""
        assert len(EXTRACTION_QUESTIONS) > 0
        assert any("account" in q.lower() for q in EXTRACTION_QUESTIONS)
        assert any("upi" in q.lower() for q in EXTRACTION_QUESTIONS)


class TestHoneypotAgent:
    """Tests for HoneypotAgent class."""

    @pytest.fixture
    def mock_detection(self) -> DetectionResult:
        """Create mock detection result."""
        return DetectionResult(
            is_scam=True,
            confidence=0.85,
            matched_patterns=[
                PatternMatch(
                    category=ScamCategory.URGENCY,
                    matched_text="immediately",
                    weight=0.7,
                    description="Urgency tactics",
                ),
            ],
            category_scores={ScamCategory.URGENCY: 0.7},
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
        mock_response = MagicMock()
        mock_response.text = "Oh no! What should I do?"
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
        mock_response = MagicMock()
        mock_response.text = "I understand, please help me."
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
