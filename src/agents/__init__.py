"""Agent module for honeypot engagement."""

from src.agents.honeypot_agent import HoneypotAgent, EngagementResult, get_agent
from src.agents.persona import Persona, PersonaManager, PersonaTrait, EmotionalState
from src.agents.policy import EngagementPolicy, EngagementMode, EngagementState
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
