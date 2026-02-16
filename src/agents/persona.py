"""Human persona management for the honeypot agent."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PersonaTrait(str, Enum):
    """Persona personality traits."""

    TRUSTING = "trusting"
    WORRIED = "worried"
    CONFUSED = "confused"
    COOPERATIVE = "cooperative"
    TECH_NAIVE = "tech_naive"


class EmotionalState(str, Enum):
    """Current emotional state of the persona."""

    CALM = "calm"
    ANXIOUS = "anxious"
    PANICKED = "panicked"
    RELIEVED = "relieved"
    SUSPICIOUS = "suspicious"  # Use sparingly, only late in conversation
    # Context-aware states based on scam type
    INTERESTED = "interested"  # For job offers - curious about opportunity
    EXCITED = "excited"  # For lottery/rewards - happy about winning
    CAUTIOUS = "cautious"  # For impersonation - intimidated but careful
    NEUTRAL = "neutral"  # For unknown scam types - no strong emotion


@dataclass
class Persona:
    """Represents the honeypot's human persona."""

    traits: list[PersonaTrait] = field(default_factory=lambda: [
        PersonaTrait.TRUSTING,
        PersonaTrait.WORRIED,
        PersonaTrait.TECH_NAIVE,
    ])
    emotional_state: EmotionalState = EmotionalState.CALM
    engagement_turn: int = 0

    # Conversation memory
    claimed_issues: list[str] = field(default_factory=list)
    mentioned_details: dict[str, Any] = field(default_factory=dict)

    def update_emotional_state(self, scam_intensity: float, scam_type: str | None = None) -> None:
        """
        Update emotional state based on scam type and intensity.
        
        Different scam types evoke different emotional responses:
        - job_offer: Interest/curiosity (excited about opportunity)
        - banking_fraud: Panic/anxiety (scared about account)
        - lottery_reward: Excitement (happy about winning)
        - impersonation: Caution/nervousness (intimidated by authority)
        - others/None: Neutral/calm (confused, no strong emotion)
        """
        # Map scam types to appropriate emotions
        scam_type_emotions = {
            "job_offer": (EmotionalState.INTERESTED, EmotionalState.INTERESTED),  # (high, low)
            "banking_fraud": (EmotionalState.PANICKED, EmotionalState.ANXIOUS),
            "lottery_reward": (EmotionalState.EXCITED, EmotionalState.EXCITED),
            "impersonation": (EmotionalState.CAUTIOUS, EmotionalState.CAUTIOUS),
            "others": (EmotionalState.NEUTRAL, EmotionalState.CALM),
        }
        
        # Get emotions for this scam type, default to neutral/calm for unknown types
        high_emotion, low_emotion = scam_type_emotions.get(
            scam_type, (EmotionalState.NEUTRAL, EmotionalState.CALM)
        )
        
        # Use intensity to determine which emotion variant
        if scam_intensity > 0.6:
            self.emotional_state = high_emotion
        else:
            self.emotional_state = low_emotion

    def increment_turn(self) -> None:
        """Increment the engagement turn counter."""
        self.engagement_turn += 1


class PersonaManager:
    """Manages persona state across conversation turns."""

    def __init__(self) -> None:
        """Initialize persona manager."""
        self.personas: dict[str, Persona] = {}

    def get_or_create_persona(self, conversation_id: str) -> Persona:
        """Get existing persona or create new one for a conversation."""
        if conversation_id not in self.personas:
            self.personas[conversation_id] = Persona()
        return self.personas[conversation_id]

    def update_persona(
        self,
        conversation_id: str,
        scam_intensity: float,
        scam_type: str | None = None,
    ) -> Persona:
        """Update persona state after a turn."""
        persona = self.get_or_create_persona(conversation_id)
        persona.increment_turn()
        persona.update_emotional_state(scam_intensity, scam_type)
        return persona

    def get_persona_context(self, conversation_id: str) -> dict[str, Any]:
        """Get persona context for prompt injection."""
        persona = self.get_or_create_persona(conversation_id)
        return {
            "emotional_state": persona.emotional_state.value,
            "engagement_turn": persona.engagement_turn,
        }

    def clear_persona(self, conversation_id: str) -> None:
        """Clear persona for a completed conversation."""
        self.personas.pop(conversation_id, None)
