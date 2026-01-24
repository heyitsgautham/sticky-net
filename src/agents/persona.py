"""Human persona management for the honeypot agent."""

import random
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
    extracted_info_count: int = 0

    # Conversation memory
    claimed_issues: list[str] = field(default_factory=list)
    mentioned_details: dict[str, Any] = field(default_factory=dict)

    def update_emotional_state(self, scam_intensity: float, scam_type: str | None = None) -> None:
        """Update emotional state based on scam type and intensity.
        
        When scam_type is known, map it to appropriate emotion.
        When scam_type is None, only use CALM or escalate based on confidence.
        """
        # If no scam type detected, remain calm or cautiously anxious
        if scam_type is None:
            if scam_intensity > 0.8:
                # Only panic if very high confidence AND uncertainty
                self.emotional_state = EmotionalState.ANXIOUS
            else:
                self.emotional_state = EmotionalState.CALM
            return

        # Map scam types to emotions
        scam_type_lower = scam_type.lower().strip()
        
        # Job offer or recruitment scams -> INTERESTED (we want to engage)
        if "job" in scam_type_lower or "offer" in scam_type_lower or "recruitment" in scam_type_lower:
            self.emotional_state = EmotionalState.ANXIOUS  # Interested but slightly worried
            
        # Banking/financial fraud -> ANXIOUS, escalate to PANICKED if high confidence
        elif any(term in scam_type_lower for term in ["banking", "bank", "financial", "account"]):
            if scam_intensity > 0.8:
                self.emotional_state = EmotionalState.PANICKED
            else:
                self.emotional_state = EmotionalState.ANXIOUS
                
        # Lottery/rewards -> EXCITED/HOPEFUL (represented as RELIEVED)
        elif any(term in scam_type_lower for term in ["lottery", "reward", "prize", "jackpot"]):
            self.emotional_state = EmotionalState.RELIEVED
            
        # Impersonation/authority -> ANXIOUS (worried about authority)
        elif any(term in scam_type_lower for term in ["impersonation", "impersonate", "police", "government", "authority"]):
            self.emotional_state = EmotionalState.ANXIOUS
            
        # Phishing/security -> ANXIOUS (worried about security)
        elif any(term in scam_type_lower for term in ["phishing", "security", "verify", "confirm"]):
            self.emotional_state = EmotionalState.ANXIOUS
            
        # Default: use confidence to determine emotion
        else:
            if scam_intensity > 0.8:
                self.emotional_state = EmotionalState.PANICKED
            elif scam_intensity > 0.5:
                self.emotional_state = EmotionalState.ANXIOUS
            else:
                self.emotional_state = EmotionalState.CALM

    def get_emotional_modifier(self) -> str:
        """
        Get text modifier based on emotional state.
        
        Returns varied modifiers to avoid repetition - picks randomly
        from options appropriate to the emotional state.
        """
        modifiers = {
            EmotionalState.CALM: [
                "",
                "ok so ",
                "let me understand ",
                "hmm ",
            ],
            EmotionalState.ANXIOUS: [
                "this is worrying me ",
                "i am concerned now ",
                "wait what ",
                "this doesnt sound right ",
                "one second ",
            ],
            EmotionalState.PANICKED: [
                "ok ok i am scared ",
                "please help me understand ",
                "my hands are shaking ",
                "what do i do ",
                "i dont want trouble ",
            ],
            EmotionalState.RELIEVED: [
                "ok good ",
                "alright then ",
                "that makes sense ",
            ],
            EmotionalState.SUSPICIOUS: [
                "wait ",
                "hold on ",
                "but ",
                "i am not sure ",
            ],
        }
        options = modifiers.get(self.emotional_state, [""])
        return random.choice(options)

    def should_ask_extraction_question(self) -> bool:
        """Determine if it's a good time to ask for intelligence."""
        # More likely to ask after building rapport (turn 2+)
        # Less likely if we've already extracted a lot
        base_probability = 0.4
        turn_bonus = min(0.3, self.engagement_turn * 0.1)
        extraction_penalty = self.extracted_info_count * 0.15

        probability = base_probability + turn_bonus - extraction_penalty
        return random.random() < probability

    def record_extraction(self) -> None:
        """Record that we extracted some intelligence."""
        self.extracted_info_count += 1

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
        extracted_something: bool = False,
    ) -> Persona:
        """Update persona state after a turn.
        
        Args:
            conversation_id: Unique conversation identifier
            scam_intensity: Confidence score (0.0-1.0) of scam detection
            scam_type: Type of scam detected (e.g., 'banking_fraud', 'job_offer')
            extracted_something: Whether intelligence was extracted this turn
        """
        persona = self.get_or_create_persona(conversation_id)
        persona.increment_turn()
        persona.update_emotional_state(scam_intensity, scam_type)
        if extracted_something:
            persona.record_extraction()
        return persona

    def get_turn_guidance(self, turn: int) -> str:
        """
        Get guidance for response style based on turn number.
        
        This helps vary the persona's behavior across the conversation
        to avoid repetitive patterns.
        """
        if turn <= 2:
            return (
                "You are confused and asking basic questions. "
                "Use phrases like 'i dont understand', 'what is this about', 'who is this'."
            )
        elif turn <= 5:
            return (
                "You are worried but trying to understand. "
                "Use phrases like 'this is concerning', 'what should i do', 'is this serious'."
            )
        elif turn <= 10:
            return (
                "You are compliant but slow. "
                "Use phrases like 'ok let me try', 'wait i need to find my glasses', 'how do i do this'."
            )
        else:
            return (
                "You are cooperative but hesitant about money. "
                "Use phrases like 'that is a lot of money', 'let me check my balance', 'my son handles this usually'."
            )

    def get_persona_context(self, conversation_id: str) -> dict[str, Any]:
        """Get persona context for prompt injection."""
        persona = self.get_or_create_persona(conversation_id)
        turn = persona.engagement_turn
        return {
            "emotional_state": persona.emotional_state.value,
            "engagement_turn": turn,
            "emotional_modifier": persona.get_emotional_modifier(),
            "should_extract": persona.should_ask_extraction_question(),
            "turn_guidance": self.get_turn_guidance(turn),
        }

    def clear_persona(self, conversation_id: str) -> None:
        """Clear persona for a completed conversation."""
        self.personas.pop(conversation_id, None)
