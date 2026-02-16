---
#applyTo: "**"
---

# Milestone 5: Intelligence Extraction (Hybrid Approach)

> **Goal**: Implement a hybrid intelligence extraction system that combines fast regex patterns with AI-powered extraction during engagement to maximize captured intelligence.

## Why Hybrid Extraction?

**Regex-only limitations:**
- ❌ Misses obfuscated data ("nine eight seven six..." spelled out)
- ❌ Cannot understand contextual references ("send to my same account")
- ❌ Fails on non-standard formats scammers may use
- ❌ No semantic understanding of implicit information

**Hybrid approach benefits:**
- ✅ Regex: Fast, deterministic, catches standard formats (~1ms)
- ✅ AI: Extracts from natural language during engagement (already paying for Pro call)
- ✅ Combined: Maximum intelligence capture with deduplication

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HYBRID EXTRACTION PIPELINE                        │
└─────────────────────────────────────────────────────────────────────┘

                    Scammer Message
                          │
          ┌───────────────┴───────────────┐
          │                               │
          ▼                               ▼
┌─────────────────────┐       ┌─────────────────────────────────────┐
│   REGEX EXTRACTOR   │       │     AI EXTRACTOR (During Engage)    │
│     (Always runs)   │       │   (Gemini 3 Pro - already called)   │
├─────────────────────┤       ├─────────────────────────────────────┤
│ • Standard formats  │       │ • Structured output extraction      │
│ • 9-18 digit nums   │       │ • Obfuscated numbers               │
│ • user@provider     │       │ • Contextual references            │
│ • +91 phones        │       │ • Implicit information             │
│ • http/https URLs   │       │ • Semantic validation              │
│ ~1ms                │       │ ~0ms extra (piggybacks on engage)  │
└─────────┬───────────┘       └───────────────┬─────────────────────┘
          │                                   │
          └───────────────┬───────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   MERGE & DEDUPLICATE │
              │   • Union of both     │
              │   • Normalize formats │
              │   • Validate entities │
              └───────────────────────┘
```

## Prerequisites

- Milestones 1-4 completed
- Agent engagement module functional
- Conversation flow established

## Tasks

### 5.1 Define Extraction Patterns

#### src/intelligence/patterns.py

```python
"""Regex patterns and validators for intelligence extraction."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Pattern


class IntelligenceType(str, Enum):
    """Types of intelligence that can be extracted."""

    BANK_ACCOUNT = "bank_account"
    UPI_ID = "upi_id"
    PHONE_NUMBER = "phone_number"
    URL = "url"
    EMAIL = "email"


class ExtractionSource(str, Enum):
    """Source of extraction."""

    REGEX = "regex"
    AI = "ai"
    MERGED = "merged"


@dataclass
class ExtractionPattern:
    """Pattern configuration for extraction."""

    pattern: Pattern[str]
    intel_type: IntelligenceType
    description: str
    validator: callable = None  # Optional validation function


# Bank Account Patterns
# Indian bank accounts: 9-18 digits, various formats
BANK_ACCOUNT_PATTERNS = [
    # Plain 9-18 digit number
    ExtractionPattern(
        pattern=re.compile(r"\b\d{9,18}\b"),
        intel_type=IntelligenceType.BANK_ACCOUNT,
        description="Plain bank account number (9-18 digits)",
    ),
    # Formatted with spaces/hyphens: XXXX-XXXX-XXXX-XXXX
    ExtractionPattern(
        pattern=re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{0,6}\b"),
        intel_type=IntelligenceType.BANK_ACCOUNT,
        description="Formatted bank account number",
    ),
    # Account number with prefix like "A/C" or "Account:"
    ExtractionPattern(
        pattern=re.compile(
            r"(?:a/c|account|acc)[\s:]*#?\s*(\d{9,18})",
            re.IGNORECASE,
        ),
        intel_type=IntelligenceType.BANK_ACCOUNT,
        description="Account number with prefix",
    ),
]

# UPI ID Patterns
# Format: username@provider (e.g., name@ybl, name@paytm, name@okicici)
UPI_PROVIDERS = [
    "ybl", "paytm", "okicici", "oksbi", "okhdfcbank", "okaxis",
    "apl", "upi", "ibl", "axisb", "sbi", "icici", "hdfc",
    "kotak", "barodampay", "aubank", "indus", "federal",
]

UPI_PATTERN = ExtractionPattern(
    pattern=re.compile(
        rf"\b[\w.-]+@(?:{'|'.join(UPI_PROVIDERS)})\b",
        re.IGNORECASE,
    ),
    intel_type=IntelligenceType.UPI_ID,
    description="UPI ID (username@provider)",
)

# Also catch generic UPI-like patterns
UPI_GENERIC_PATTERN = ExtractionPattern(
    pattern=re.compile(r"\b[\w.-]{3,}@[a-zA-Z]{2,15}\b"),
    intel_type=IntelligenceType.UPI_ID,
    description="Generic UPI-like ID",
)

# Phone Number Patterns (Indian)
PHONE_PATTERNS = [
    # +91 prefix
    ExtractionPattern(
        pattern=re.compile(r"\+91[-\s]?\d{10}\b"),
        intel_type=IntelligenceType.PHONE_NUMBER,
        description="Indian phone with +91",
    ),
    # 10 digits starting with 6-9
    ExtractionPattern(
        pattern=re.compile(r"\b[6-9]\d{9}\b"),
        intel_type=IntelligenceType.PHONE_NUMBER,
        description="Indian mobile number (10 digits)",
    ),
    # Formatted with spaces/hyphens
    ExtractionPattern(
        pattern=re.compile(r"\b[6-9]\d{2}[-\s]?\d{3}[-\s]?\d{4}\b"),
        intel_type=IntelligenceType.PHONE_NUMBER,
        description="Formatted Indian mobile",
    ),
]

# URL Patterns
URL_PATTERN = ExtractionPattern(
    pattern=re.compile(
        r"https?://[^\s<>\"'{}|\\^`\[\]]+",
        re.IGNORECASE,
    ),
    intel_type=IntelligenceType.URL,
    description="HTTP/HTTPS URL",
)

# Suspicious URL indicators for phishing detection
SUSPICIOUS_URL_INDICATORS = [
    "bit.ly", "tinyurl", "t.co", "goo.gl",  # URL shorteners
    "login", "verify", "update", "secure", "account",  # Phishing keywords
    "kyc", "otp", "bank", "sbi", "hdfc", "icici",  # Bank-related
    ".tk", ".ml", ".ga", ".cf", ".gq",  # Free TLDs often used in phishing
    "telegram", "wa.me", "whatsapp",  # Messaging links
]

# Email Pattern
EMAIL_PATTERN = ExtractionPattern(
    pattern=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    intel_type=IntelligenceType.EMAIL,
    description="Email address",
)


def get_all_patterns() -> list[ExtractionPattern]:
    """Get all extraction patterns."""
    return (
        BANK_ACCOUNT_PATTERNS +
        [UPI_PATTERN, UPI_GENERIC_PATTERN] +
        PHONE_PATTERNS +
        [URL_PATTERN, EMAIL_PATTERN]
    )


def is_suspicious_url(url: str) -> bool:
    """Check if URL contains suspicious indicators."""
    url_lower = url.lower()
    return any(indicator in url_lower for indicator in SUSPICIOUS_URL_INDICATORS)


# AI Extraction prompt template for structured output
AI_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "bank_accounts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Bank account numbers found (digits only, 9-18 chars)"
        },
        "upi_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "UPI IDs in format username@provider"
        },
        "phone_numbers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Indian phone numbers (10 digits, may have +91)"
        },
        "urls": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Suspicious URLs shared by scammer"
        },
        "emails": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Email addresses"
        }
    },
    "required": ["bank_accounts", "upi_ids", "phone_numbers", "urls", "emails"]
}
```

### 5.2 Implement Hybrid Intelligence Extractor

#### src/intelligence/extractor.py

```python
"""Hybrid intelligence extraction from conversation messages.

Combines fast regex patterns with AI-powered extraction during engagement
for maximum intelligence capture.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.intelligence.patterns import (
    IntelligenceType,
    ExtractionSource,
    ExtractionPattern,
    get_all_patterns,
    is_suspicious_url,
    BANK_ACCOUNT_PATTERNS,
    UPI_PATTERN,
    UPI_GENERIC_PATTERN,
    PHONE_PATTERNS,
    URL_PATTERN,
    EMAIL_PATTERN,
)

logger = structlog.get_logger()


@dataclass
class ExtractedEntity:
    """A single extracted intelligence entity."""

    value: str
    intel_type: IntelligenceType
    source: ExtractionSource = ExtractionSource.REGEX
    confidence: float = 1.0
    is_suspicious: bool = False
    context: str = ""


@dataclass
class ExtractionResult:
    """Complete extraction result from a conversation."""

    bank_accounts: list[str] = field(default_factory=list)
    upi_ids: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    phishing_links: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    all_entities: list[ExtractedEntity] = field(default_factory=list)
    source: ExtractionSource = ExtractionSource.REGEX

    @property
    def has_intelligence(self) -> bool:
        """Check if any intelligence was extracted."""
        return bool(
            self.bank_accounts or
            self.upi_ids or
            self.phone_numbers or
            self.phishing_links or
            self.emails
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response format."""
        return {
            "bankAccounts": self.bank_accounts,
            "upiIds": self.upi_ids,
            "phoneNumbers": self.phone_numbers,
            "phishingLinks": self.phishing_links,
            "emails": self.emails,
        }

    def merge_with(self, other: "ExtractionResult") -> "ExtractionResult":
        """Merge with another extraction result, deduplicating entities."""
        return ExtractionResult(
            bank_accounts=list(set(self.bank_accounts + other.bank_accounts)),
            upi_ids=list(set(self.upi_ids + other.upi_ids)),
            phone_numbers=list(set(self.phone_numbers + other.phone_numbers)),
            phishing_links=list(set(self.phishing_links + other.phishing_links)),
            emails=list(set(self.emails + other.emails)),
            all_entities=self.all_entities + other.all_entities,
            source=ExtractionSource.MERGED,
        )


class IntelligenceExtractor:
    """
    Hybrid intelligence extractor combining regex and AI extraction.

    Regex extraction:
    - Fast (~1ms), deterministic
    - Catches standard formats
    - Always runs on every message

    AI extraction:
    - Piggybacks on engagement LLM call (no extra cost)
    - Catches obfuscated data, contextual references
    - Returns structured output alongside response
    """

    def __init__(self) -> None:
        """Initialize extractor with patterns."""
        self.logger = logger.bind(component="IntelligenceExtractor")
        self.patterns = get_all_patterns()

    def extract(self, text: str) -> ExtractionResult:
        """
        Extract all intelligence from text using regex patterns.

        Args:
            text: Text to extract from (single message or full conversation)

        Returns:
            ExtractionResult with all extracted entities
        """
        result = ExtractionResult(source=ExtractionSource.REGEX)

        # Extract each type of intelligence
        result.bank_accounts = self._extract_bank_accounts(text)
        result.upi_ids = self._extract_upi_ids(text)
        result.phone_numbers = self._extract_phone_numbers(text)
        result.phishing_links = self._extract_urls(text)
        result.emails = self._extract_emails(text)

        self.logger.info(
            "Regex extraction complete",
            bank_accounts=len(result.bank_accounts),
            upi_ids=len(result.upi_ids),
            phone_numbers=len(result.phone_numbers),
            urls=len(result.phishing_links),
            emails=len(result.emails),
        )

        return result

    def extract_from_conversation(
        self,
        messages: list[dict[str, Any]],
    ) -> ExtractionResult:
        """
        Extract intelligence from a full conversation using regex.

        Args:
            messages: List of message dicts with 'text' field

        Returns:
            ExtractionResult with deduplicated entities
        """
        # Combine all message texts
        full_text = " ".join(msg.get("text", "") for msg in messages)
        return self.extract(full_text)

    def parse_ai_extraction(
        self,
        ai_extracted: dict[str, Any] | None,
    ) -> ExtractionResult:
        """
        Parse AI-extracted intelligence from structured output.

        Args:
            ai_extracted: Dict from AI structured output with intelligence fields

        Returns:
            ExtractionResult from AI extraction
        """
        if not ai_extracted:
            return ExtractionResult(source=ExtractionSource.AI)

        result = ExtractionResult(source=ExtractionSource.AI)

        # Parse and validate each field
        raw_accounts = ai_extracted.get("bank_accounts", [])
        for acc in raw_accounts:
            clean = self._clean_number(str(acc))
            if self._is_valid_bank_account(clean):
                result.bank_accounts.append(clean)

        raw_upi = ai_extracted.get("upi_ids", [])
        for upi in raw_upi:
            if "@" in str(upi):
                result.upi_ids.append(str(upi).lower())

        raw_phones = ai_extracted.get("phone_numbers", [])
        for phone in raw_phones:
            clean = self._clean_number(str(phone))
            if self._is_valid_phone(clean):
                result.phone_numbers.append(clean)

        raw_urls = ai_extracted.get("urls", [])
        for url in raw_urls:
            if is_suspicious_url(str(url)):
                result.phishing_links.append(str(url))

        raw_emails = ai_extracted.get("emails", [])
        for email in raw_emails:
            if "@" in str(email) and "." in str(email):
                result.emails.append(str(email).lower())

        self.logger.info(
            "AI extraction parsed",
            bank_accounts=len(result.bank_accounts),
            upi_ids=len(result.upi_ids),
            phone_numbers=len(result.phone_numbers),
            urls=len(result.phishing_links),
            emails=len(result.emails),
        )

        return result

    def merge_extractions(
        self,
        regex_result: ExtractionResult,
        ai_result: ExtractionResult,
    ) -> ExtractionResult:
        """
        Merge regex and AI extraction results.

        Args:
            regex_result: Result from regex extraction
            ai_result: Result from AI extraction

        Returns:
            Merged and deduplicated ExtractionResult
        """
        merged = regex_result.merge_with(ai_result)

        self.logger.info(
            "Extractions merged",
            total_bank_accounts=len(merged.bank_accounts),
            total_upi_ids=len(merged.upi_ids),
            total_phone_numbers=len(merged.phone_numbers),
            total_urls=len(merged.phishing_links),
            total_emails=len(merged.emails),
        )

        return merged

    def _extract_bank_accounts(self, text: str) -> list[str]:
        """Extract bank account numbers."""
        accounts = set()

        for pattern_config in BANK_ACCOUNT_PATTERNS:
            matches = pattern_config.pattern.findall(text)
            for match in matches:
                # Clean and validate
                clean = self._clean_number(match)
                if self._is_valid_bank_account(clean):
                    accounts.add(clean)

        return list(accounts)

    def _extract_upi_ids(self, text: str) -> list[str]:
        """Extract UPI IDs."""
        upi_ids = set()

        # Known provider pattern
        matches = UPI_PATTERN.pattern.findall(text)
        upi_ids.update(m.lower() for m in matches)

        # Generic pattern (filter out emails)
        generic_matches = UPI_GENERIC_PATTERN.pattern.findall(text)
        for match in generic_matches:
            # Exclude if looks like email (has standard email TLD)
            if not self._looks_like_email(match):
                upi_ids.add(match.lower())

        return list(upi_ids)

    def _extract_phone_numbers(self, text: str) -> list[str]:
        """Extract phone numbers."""
        phones = set()

        for pattern_config in PHONE_PATTERNS:
            matches = pattern_config.pattern.findall(text)
            for match in matches:
                clean = self._clean_number(match)
                if self._is_valid_phone(clean):
                    phones.add(clean)

        return list(phones)

    def _extract_urls(self, text: str) -> list[str]:
        """Extract URLs, flagging suspicious ones."""
        urls = set()

        matches = URL_PATTERN.pattern.findall(text)
        for url in matches:
            # Clean trailing punctuation
            clean_url = url.rstrip(".,;:!?)")

            # Only include suspicious URLs (likely phishing)
            if is_suspicious_url(clean_url):
                urls.add(clean_url)

        return list(urls)

    def _extract_emails(self, text: str) -> list[str]:
        """Extract email addresses."""
        emails = set()

        matches = EMAIL_PATTERN.pattern.findall(text)
        for email in matches:
            # Exclude UPI IDs that look like emails
            if not self._is_upi_provider(email):
                emails.add(email.lower())

        return list(emails)

    def _clean_number(self, number: str) -> str:
        """Remove formatting from numbers."""
        return re.sub(r"[-\s]", "", number)

    def _is_valid_bank_account(self, number: str) -> bool:
        """Validate bank account number."""
        # Must be 9-18 digits
        if not number.isdigit():
            return False
        if len(number) < 9 or len(number) > 18:
            return False
        # Exclude obviously fake patterns
        if number == "0" * len(number):
            return False
        if len(set(number)) == 1:  # All same digit
            return False
        return True

    def _is_valid_phone(self, number: str) -> bool:
        """Validate Indian phone number."""
        # Remove +91 prefix if present
        clean = number.lstrip("+91").lstrip("91")
        if len(clean) != 10:
            return False
        if not clean[0] in "6789":  # Indian mobile starts with 6-9
            return False
        return True

    def _looks_like_email(self, text: str) -> bool:
        """Check if text looks like an email address."""
        email_tlds = [".com", ".org", ".net", ".in", ".co", ".edu", ".gov"]
        return any(text.lower().endswith(tld) for tld in email_tlds)

    def _is_upi_provider(self, email: str) -> bool:
        """Check if email domain is actually a UPI provider."""
        upi_providers = ["ybl", "paytm", "okicici", "oksbi", "upi"]
        domain = email.split("@")[-1].split(".")[0].lower()
        return domain in upi_providers


# Singleton instance
_extractor_instance: IntelligenceExtractor | None = None


def get_extractor() -> IntelligenceExtractor:
    """Get or create extractor instance."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = IntelligenceExtractor()
    return _extractor_instance
```

### 5.3 Create Module Init

#### src/intelligence/__init__.py

```python
"""Intelligence extraction module."""

from src.intelligence.extractor import (
    IntelligenceExtractor,
    ExtractionResult,
    ExtractedEntity,
    get_extractor,
)
from src.intelligence.patterns import (
    IntelligenceType,
    ExtractionSource,
    is_suspicious_url,
    AI_EXTRACTION_SCHEMA,
)

__all__ = [
    "IntelligenceExtractor",
    "ExtractionResult",
    "ExtractedEntity",
    "get_extractor",
    "IntelligenceType",
    "ExtractionSource",
    "is_suspicious_url",
    "AI_EXTRACTION_SCHEMA",
]
```

### 5.4 Update Honeypot Agent for Hybrid Extraction

The key insight is that we're **already calling Gemini 3 Pro** during engagement. We can modify the prompt to also return extracted intelligence as structured output — **at no extra cost**.

#### Update to src/agents/honeypot_agent.py

Add this to the engagement prompt to enable AI extraction:

```python
# In the HoneypotAgent class, modify the engagement prompt:

EXTRACTION_INSTRUCTION = """
INTELLIGENCE EXTRACTION:
While generating your response, also extract any actionable intelligence 
the scammer has shared. Look for:

1. Bank account numbers (9-18 digits, may be spelled out or formatted)
2. UPI IDs (format: username@provider like xyz@ybl, abc@paytm)
3. Phone numbers (Indian: 10 digits starting with 6-9, may have +91)
4. Suspicious URLs (phishing links, URL shorteners, fake banking sites)
5. Email addresses

IMPORTANT: Scammers may obfuscate data:
- "nine eight seven six five four three two one zero" = 9876543210
- "account ending in 1234" = partial account number
- "same UPI as before" = reference to previous message
- Links hidden in text or using URL shorteners

Return your response AND extracted intelligence in this JSON format:
{
    "response": "Your conversational response here",
    "extracted_intelligence": {
        "bank_accounts": ["1234567890123"],
        "upi_ids": ["scammer@ybl"],
        "phone_numbers": ["9876543210"],
        "urls": ["http://phishing-site.tk"],
        "emails": ["scammer@example.com"]
    },
    "agent_notes": "Brief analysis of scammer tactics"
}
"""

# Updated engage method signature:
async def engage(
    self,
    message: Message,
    history: list[Message],
    detection: ClassificationResult,
    state: ConversationState
) -> EngagementResult:
    """
    Generate engagement response with hybrid intelligence extraction.

    This method:
    1. Generates a believable human response
    2. Extracts intelligence via AI (from the same LLM call)
    3. Merges with regex extraction for comprehensive coverage
    """
    from src.intelligence import get_extractor, AI_EXTRACTION_SCHEMA

    persona = self.persona_manager.get_persona(state)

    # Build prompt with extraction instructions
    prompt = self._build_prompt(message, history, persona)
    prompt += EXTRACTION_INSTRUCTION

    response = self.client.models.generate_content(
        model=self.model,
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.HIGH
            ),
            system_instruction=HONEYPOT_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=AI_EXTRACTION_SCHEMA,  # Structured output
        )
    )

    # Parse AI response
    parsed = json.loads(response.text)
    agent_response = parsed.get("response", "")
    ai_extracted = parsed.get("extracted_intelligence", {})
    agent_notes = parsed.get("agent_notes", "")

    # Get regex extraction from full conversation
    extractor = get_extractor()
    full_text = " ".join([msg.text for msg in history] + [message.text])
    regex_result = extractor.extract(full_text)

    # Parse AI extraction
    ai_result = extractor.parse_ai_extraction(ai_extracted)

    # Merge both extraction sources
    merged_intelligence = extractor.merge_extractions(regex_result, ai_result)

    return EngagementResult(
        response=agent_response,
        persona_state=persona.emotional_state,
        turn_number=state.turn_count,
        extracted_intelligence=merged_intelligence,
        agent_notes=agent_notes,
    )
```

### 5.5 Write Extraction Tests

#### tests/test_extractor.py

```python
"""Tests for intelligence extraction module."""

import pytest

from src.intelligence.extractor import IntelligenceExtractor, ExtractionResult
from src.intelligence.patterns import is_suspicious_url, IntelligenceType, ExtractionSource


class TestIntelligenceExtractor:
    """Tests for IntelligenceExtractor class."""

    @pytest.fixture
    def extractor(self) -> IntelligenceExtractor:
        """Create extractor instance."""
        return IntelligenceExtractor()

    # Bank Account Tests
    def test_extracts_plain_bank_account(self, extractor: IntelligenceExtractor):
        """Should extract plain bank account numbers."""
        text = "Transfer to account 123456789012"
        result = extractor.extract(text)
        assert "123456789012" in result.bank_accounts

    def test_extracts_formatted_bank_account(self, extractor: IntelligenceExtractor):
        """Should extract formatted bank accounts."""
        text = "Account number is 1234-5678-9012-3456"
        result = extractor.extract(text)
        assert any("1234567890123456" in acc for acc in result.bank_accounts)

    def test_extracts_prefixed_bank_account(self, extractor: IntelligenceExtractor):
        """Should extract accounts with A/C prefix."""
        text = "A/C: 12345678901234"
        result = extractor.extract(text)
        assert "12345678901234" in result.bank_accounts

    def test_ignores_invalid_bank_accounts(self, extractor: IntelligenceExtractor):
        """Should ignore obviously invalid accounts."""
        text = "Number is 00000000000"  # All zeros
        result = extractor.extract(text)
        assert "00000000000" not in result.bank_accounts

    # UPI Tests
    def test_extracts_standard_upi(self, extractor: IntelligenceExtractor):
        """Should extract standard UPI IDs."""
        text = "Send money to john@ybl"
        result = extractor.extract(text)
        assert "john@ybl" in result.upi_ids

    def test_extracts_paytm_upi(self, extractor: IntelligenceExtractor):
        """Should extract Paytm UPI."""
        text = "UPI: merchant123@paytm"
        result = extractor.extract(text)
        assert "merchant123@paytm" in result.upi_ids

    def test_extracts_multiple_upi(self, extractor: IntelligenceExtractor):
        """Should extract multiple UPI IDs."""
        text = "Pay to user@oksbi or backup@okicici"
        result = extractor.extract(text)
        assert len(result.upi_ids) == 2

    # Phone Number Tests
    def test_extracts_10_digit_phone(self, extractor: IntelligenceExtractor):
        """Should extract 10-digit Indian mobile."""
        text = "Call me on 9876543210"
        result = extractor.extract(text)
        assert "9876543210" in result.phone_numbers

    def test_extracts_phone_with_91(self, extractor: IntelligenceExtractor):
        """Should extract phone with +91."""
        text = "Contact: +91-9876543210"
        result = extractor.extract(text)
        assert any("9876543210" in p for p in result.phone_numbers)

    def test_ignores_invalid_phone(self, extractor: IntelligenceExtractor):
        """Should ignore phones not starting with 6-9."""
        text = "Number: 1234567890"
        result = extractor.extract(text)
        assert "1234567890" not in result.phone_numbers

    # URL Tests
    def test_extracts_suspicious_url(self, extractor: IntelligenceExtractor):
        """Should extract suspicious URLs."""
        text = "Click here: http://bit.ly/abc123"
        result = extractor.extract(text)
        assert any("bit.ly" in url for url in result.phishing_links)

    def test_extracts_bank_phishing_url(self, extractor: IntelligenceExtractor):
        """Should extract bank-related phishing URLs."""
        text = "Verify at https://sbi-login-verify.tk/kyc"
        result = extractor.extract(text)
        assert len(result.phishing_links) > 0

    def test_ignores_normal_url(self, extractor: IntelligenceExtractor):
        """Should ignore non-suspicious URLs."""
        text = "Visit https://google.com for search"
        result = extractor.extract(text)
        assert "google.com" not in str(result.phishing_links)

    # Email Tests
    def test_extracts_email(self, extractor: IntelligenceExtractor):
        """Should extract email addresses."""
        text = "Contact support@example.com"
        result = extractor.extract(text)
        assert "support@example.com" in result.emails

    # Full Extraction Tests
    def test_extracts_multiple_types(self, extractor: IntelligenceExtractor):
        """Should extract multiple intelligence types."""
        text = """
        Send Rs. 5000 to A/C: 12345678901234
        Or use UPI: scammer@ybl
        For help call 9999888877
        Or visit http://bit.ly/verify-account
        Email: help@scam.com
        """
        result = extractor.extract(text)

        assert len(result.bank_accounts) >= 1
        assert len(result.upi_ids) >= 1
        assert len(result.phone_numbers) >= 1
        assert len(result.phishing_links) >= 1
        assert len(result.emails) >= 1

    def test_has_intelligence_property(self, extractor: IntelligenceExtractor):
        """Should correctly report if intelligence found."""
        empty_result = extractor.extract("Hello, how are you?")
        assert not empty_result.has_intelligence

        intel_result = extractor.extract("Pay to fake@ybl")
        assert intel_result.has_intelligence

    def test_to_dict_format(self, extractor: IntelligenceExtractor):
        """Should convert to correct API format."""
        result = extractor.extract("UPI: test@ybl")
        data = result.to_dict()

        assert "bankAccounts" in data
        assert "upiIds" in data
        assert "phoneNumbers" in data
        assert "phishingLinks" in data
        assert "test@ybl" in data["upiIds"]


class TestSuspiciousUrl:
    """Tests for URL suspicion detection."""

    def test_shortener_is_suspicious(self):
        """URL shorteners should be suspicious."""
        assert is_suspicious_url("https://bit.ly/abc")
        assert is_suspicious_url("http://tinyurl.com/xyz")
        assert is_suspicious_url("https://t.co/short")

    def test_phishing_keywords_suspicious(self):
        """URLs with phishing keywords should be suspicious."""
        assert is_suspicious_url("https://fake-bank.com/login")
        assert is_suspicious_url("http://verify-account.com/kyc")
        assert is_suspicious_url("https://sbi-update.com/otp")

    def test_free_tld_suspicious(self):
        """Free TLDs often used in phishing."""
        assert is_suspicious_url("https://fake-site.tk")
        assert is_suspicious_url("http://scam.ml")

    def test_normal_url_not_suspicious(self):
        """Normal URLs should not be flagged."""
        assert not is_suspicious_url("https://google.com")
        assert not is_suspicious_url("https://github.com/repo")


class TestExtractionFromConversation:
    """Tests for conversation-level extraction."""

    def test_extracts_from_multiple_messages(self):
        """Should extract from all messages."""
        extractor = IntelligenceExtractor()
        messages = [
            {"text": "Your account has issues"},
            {"text": "Send 500 to A/C: 12345678901234"},
            {"text": "Or use UPI: scam@ybl"},
        ]

        result = extractor.extract_from_conversation(messages)

        assert len(result.bank_accounts) >= 1
        assert len(result.upi_ids) >= 1

    def test_deduplicates_entities(self):
        """Should not duplicate same entity."""
        extractor = IntelligenceExtractor()
        messages = [
            {"text": "Send to scam@ybl"},
            {"text": "Remember: scam@ybl is the UPI"},
            {"text": "Final reminder: scam@ybl"},
        ]

        result = extractor.extract_from_conversation(messages)

        assert result.upi_ids.count("scam@ybl") == 1


class TestAIExtraction:
    """Tests for AI extraction parsing."""

    @pytest.fixture
    def extractor(self) -> IntelligenceExtractor:
        """Create extractor instance."""
        return IntelligenceExtractor()

    def test_parses_ai_extracted_bank_account(self, extractor: IntelligenceExtractor):
        """Should parse AI-extracted bank accounts."""
        ai_data = {
            "bank_accounts": ["123456789012", "9876543210123"],
            "upi_ids": [],
            "phone_numbers": [],
            "urls": [],
            "emails": [],
        }
        result = extractor.parse_ai_extraction(ai_data)
        assert "123456789012" in result.bank_accounts
        assert result.source == ExtractionSource.AI

    def test_parses_ai_extracted_upi(self, extractor: IntelligenceExtractor):
        """Should parse AI-extracted UPI IDs."""
        ai_data = {
            "bank_accounts": [],
            "upi_ids": ["scammer@paytm", "fraud@ybl"],
            "phone_numbers": [],
            "urls": [],
            "emails": [],
        }
        result = extractor.parse_ai_extraction(ai_data)
        assert "scammer@paytm" in result.upi_ids
        assert "fraud@ybl" in result.upi_ids

    def test_validates_ai_extracted_phone(self, extractor: IntelligenceExtractor):
        """Should validate AI-extracted phone numbers."""
        ai_data = {
            "bank_accounts": [],
            "upi_ids": [],
            "phone_numbers": ["9876543210", "1234567890"],  # Second is invalid
            "urls": [],
            "emails": [],
        }
        result = extractor.parse_ai_extraction(ai_data)
        assert "9876543210" in result.phone_numbers
        assert "1234567890" not in result.phone_numbers  # Invalid, doesn't start with 6-9

    def test_handles_empty_ai_extraction(self, extractor: IntelligenceExtractor):
        """Should handle empty/null AI extraction."""
        result = extractor.parse_ai_extraction(None)
        assert not result.has_intelligence
        assert result.source == ExtractionSource.AI

    def test_handles_obfuscated_number_from_ai(self, extractor: IntelligenceExtractor):
        """Should handle cleaned numbers from AI."""
        ai_data = {
            "bank_accounts": ["1234 5678 9012 34"],  # AI might return formatted
            "upi_ids": [],
            "phone_numbers": ["+91-9876543210"],  # With country code
            "urls": [],
            "emails": [],
        }
        result = extractor.parse_ai_extraction(ai_data)
        # Should clean and validate
        assert any("12345678901234" in acc for acc in result.bank_accounts)


class TestMergeExtractions:
    """Tests for merging regex and AI extractions."""

    @pytest.fixture
    def extractor(self) -> IntelligenceExtractor:
        """Create extractor instance."""
        return IntelligenceExtractor()

    def test_merges_unique_entities(self, extractor: IntelligenceExtractor):
        """Should merge unique entities from both sources."""
        regex_result = ExtractionResult(
            bank_accounts=["111111111111"],
            upi_ids=["regex@ybl"],
            source=ExtractionSource.REGEX,
        )
        ai_result = ExtractionResult(
            bank_accounts=["222222222222"],
            upi_ids=["ai@paytm"],
            source=ExtractionSource.AI,
        )

        merged = extractor.merge_extractions(regex_result, ai_result)

        assert len(merged.bank_accounts) == 2
        assert len(merged.upi_ids) == 2
        assert merged.source == ExtractionSource.MERGED

    def test_deduplicates_same_entity(self, extractor: IntelligenceExtractor):
        """Should deduplicate same entity from both sources."""
        regex_result = ExtractionResult(
            upi_ids=["same@ybl"],
            source=ExtractionSource.REGEX,
        )
        ai_result = ExtractionResult(
            upi_ids=["same@ybl"],  # Same entity
            source=ExtractionSource.AI,
        )

        merged = extractor.merge_extractions(regex_result, ai_result)

        assert merged.upi_ids.count("same@ybl") == 1

    def test_ai_catches_missed_by_regex(self, extractor: IntelligenceExtractor):
        """AI should catch entities missed by regex."""
        # Regex extraction from message
        message = "Send to my number nine eight seven six five four three two one zero"
        regex_result = extractor.extract(message)

        # AI would extract the spelled-out number
        ai_result = ExtractionResult(
            phone_numbers=["9876543210"],  # AI understood the spelled-out number
            source=ExtractionSource.AI,
        )

        merged = extractor.merge_extractions(regex_result, ai_result)

        # Regex wouldn't catch it, but merged result has it from AI
        assert "9876543210" in merged.phone_numbers
```

## Verification Checklist

- [ ] `src/intelligence/patterns.py` defines all regex patterns
- [ ] `src/intelligence/patterns.py` includes `ExtractionSource` enum
- [ ] `src/intelligence/patterns.py` includes `AI_EXTRACTION_SCHEMA`
- [ ] `src/intelligence/extractor.py` implements hybrid extraction logic
- [ ] `IntelligenceExtractor.parse_ai_extraction()` parses AI output
- [ ] `IntelligenceExtractor.merge_extractions()` combines sources
- [ ] Bank accounts (9-18 digits) extracted correctly
- [ ] UPI IDs (username@provider) extracted
- [ ] Phone numbers (Indian format) extracted
- [ ] Suspicious URLs flagged as phishing links
- [ ] Email addresses extracted
- [ ] Entities deduplicated across conversation
- [ ] HoneypotAgent updated to use hybrid extraction
- [ ] All tests pass: `pytest tests/test_extractor.py -v`

## Integration Example

```python
# Usage in routes.py - Hybrid approach
from src.intelligence.extractor import get_extractor

@router.post("/api/v1/analyze")
async def analyze_message(request: AnalyzeRequest):
    # ... detection logic ...

    if detection.is_scam:
        # Engagement agent returns response + AI-extracted intelligence
        engagement_result = await honeypot_agent.engage(
            message=request.message,
            history=request.conversation_history,
            detection=detection,
            state=conversation_state,
        )

        # engagement_result.extracted_intelligence is already merged
        # (regex + AI extraction combined)
        intelligence = engagement_result.extracted_intelligence

    else:
        # For non-scam messages, just do regex extraction
        extractor = get_extractor()
        all_messages = [
            {"text": msg.text} for msg in request.conversation_history
        ] + [{"text": request.message.text}]

        intelligence = extractor.extract_from_conversation(all_messages)

    return AnalyzeResponse(
        # ...
        extracted_intelligence=intelligence.to_dict(),
    )
```

## Benefits of Hybrid Approach

| Scenario | Regex Only | Hybrid (Regex + AI) |
|----------|------------|---------------------|
| "Send to 9876543210" | ✅ Captured | ✅ Captured |
| "nine eight seven six..." | ❌ Missed | ✅ AI understands |
| "same account as before" | ❌ Missed | ✅ AI uses context |
| "A/C ending 1234" | ❌ Partial | ✅ AI notes partial |
| Standard UPI formats | ✅ Captured | ✅ Captured |
| "my paytm is xyz" | ❌ Missed | ✅ AI infers UPI |
| URL shorteners | ✅ Flagged | ✅ Flagged |
| Obfuscated URLs | ❌ Missed | ✅ AI detects |

## Cost Impact

**No additional cost!** The AI extraction piggybacks on the existing Gemini 3 Pro call for engagement. We're already paying for that call — now we get intelligence extraction "for free" by using structured output.

```
Before: Regex only           → Some intelligence missed
After:  Regex + AI (same $)  → Maximum intelligence captured
```

## Next Steps

After completing this milestone, proceed to **Milestone 6: Deployment** to set up Docker, CI/CD, and Google Cloud Run deployment.
