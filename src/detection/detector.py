"""Scam detection logic."""

from dataclasses import dataclass
from typing import Any


@dataclass
class DetectionResult:
    """Result from scam detection."""
    
    is_scam: bool
    confidence: float
    scam_type: str | None = None
    indicators: list[str] | None = None


class ScamDetector:
    """Scam detection service (stub implementation)."""
    
    async def analyze(
        self,
        message: str,
        history: list[Any] | None = None,
        metadata: Any | None = None,
    ) -> DetectionResult:
        """Analyze message for scam indicators."""
        # Stub implementation - will be replaced in Milestone 3
        return DetectionResult(is_scam=False, confidence=0.0)
