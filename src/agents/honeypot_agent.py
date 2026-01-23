"""Main honeypot agent for scam engagement."""

from dataclasses import dataclass
from typing import Any


@dataclass
class EngagementResult:
    """Result from agent engagement."""
    
    response: str
    notes: str
    duration_seconds: int = 0


class HoneypotAgent:
    """Honeypot agent for engaging scammers (stub implementation)."""
    
    async def engage(
        self,
        message: Any,
        history: list[Any] | None = None,
        metadata: Any | None = None,
        detection: Any | None = None,
    ) -> EngagementResult:
        """Engage with the scammer and generate response."""
        # Stub implementation - will be replaced in Milestone 4
        return EngagementResult(
            response="I understand, please tell me more.",
            notes="Stub response",
            duration_seconds=0,
        )
