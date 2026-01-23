"""Intelligence extraction from conversations."""

from dataclasses import dataclass, field


@dataclass
class IntelligenceResult:
    """Extracted intelligence from conversation."""
    
    bank_accounts: list[str] = field(default_factory=list)
    upi_ids: list[str] = field(default_factory=list)
    phishing_links: list[str] = field(default_factory=list)


class IntelligenceExtractor:
    """Extract actionable intelligence from conversations (stub implementation)."""
    
    async def extract(self, messages: list[str]) -> IntelligenceResult:
        """Extract intelligence from message list."""
        # Stub implementation - will be replaced in Milestone 5
        return IntelligenceResult()
