"""Tests for personas and the persona manager."""

from src.agents.persona import EmotionalState, Persona, PersonaManager, PersonaTrait


class TestPersona:
    """Tests for Persona class."""

    def test_initial_state(self):
        """Persona should start with default values."""
        persona = Persona()
        assert persona.emotional_state == EmotionalState.CALM
        assert persona.engagement_turn == 0
        assert PersonaTrait.TRUSTING in persona.traits

    def test_emotional_state_updates_with_intensity(self):
        """Emotional state should reflect scam type and intensity."""
        persona = Persona()

        # Banking fraud with high intensity -> PANICKED
        persona.update_emotional_state(0.9, scam_type="banking_fraud")
        assert persona.emotional_state == EmotionalState.PANICKED

        # Banking fraud with lower intensity -> ANXIOUS
        persona.update_emotional_state(0.5, scam_type="banking_fraud")
        assert persona.emotional_state == EmotionalState.ANXIOUS

        # Job offer -> INTERESTED (not scared!)
        persona.update_emotional_state(0.9, scam_type="job_offer")
        assert persona.emotional_state == EmotionalState.INTERESTED

        # Unknown/None scam type -> NEUTRAL/CALM
        persona.update_emotional_state(0.9, scam_type=None)
        assert persona.emotional_state == EmotionalState.NEUTRAL

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
        """Should update persona state with scam type awareness."""
        manager = PersonaManager()

        # Banking fraud should cause panic
        persona = manager.update_persona("conv-123", scam_intensity=0.9, scam_type="banking_fraud")

        assert persona.engagement_turn == 1
        assert persona.emotional_state == EmotionalState.PANICKED

        # Job offer should cause interest, not panic
        persona2 = manager.update_persona("conv-456", scam_intensity=0.9, scam_type="job_offer")
        assert persona2.emotional_state == EmotionalState.INTERESTED

    def test_get_persona_context(self):
        """Should return context dict with emotional_state and engagement_turn only."""
        manager = PersonaManager()
        manager.get_or_create_persona("conv-123")

        context = manager.get_persona_context("conv-123")

        assert "emotional_state" in context
        assert "engagement_turn" in context
        # These should NOT be in the context (removed hardcoded strings)
        assert "emotional_modifier" not in context
        assert "turn_guidance" not in context
