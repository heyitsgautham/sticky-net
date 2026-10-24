"""Agent module for honeypot engagement."""

from src.agents.honeypot_agent import EngagementResult, HoneypotAgent, get_agent
from src.agents.persona import EmotionalState, Persona, PersonaManager, PersonaTrait
from src.agents.policy import EngagementMode, EngagementPolicy, EngagementState
from src.agents.prompts import (
    HONEYPOT_SYSTEM_PROMPT,
    get_response_strategy,
)

__all__ = [
    "HoneypotAgent",
    "EngagementResult",
    "get_agent",
    "Persona",
    "PersonaManager",
    "PersonaTrait",
    "EmotionalState",
    "EngagementPolicy",
    "EngagementMode",
    "EngagementState",
    "HONEYPOT_SYSTEM_PROMPT",
    "get_response_strategy",
]
