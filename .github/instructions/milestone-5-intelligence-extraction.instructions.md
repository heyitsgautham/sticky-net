---
#applyTo: "**"
---

# Milestone 5: Intelligence Extraction

> **Goal**: Implement entity extraction to identify bank accounts, UPI IDs, phone numbers, and phishing URLs from scammer messages.

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
```

### 5.2 Implement Intelligence Extractor

#### src/intelligence/extractor.py

```python
"""Intelligence extraction from conversation messages."""

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.intelligence.patterns import (
    IntelligenceType,
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
    source_text: str
    confidence: float
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


class IntelligenceExtractor:
    """
    Extracts actionable intelligence from conversation text.

    Identifies bank accounts, UPI IDs, phone numbers, URLs, and emails
    using regex patterns and validation.
    """

    def __init__(self) -> None:
        """Initialize extractor with patterns."""
        self.logger = logger.bind(component="IntelligenceExtractor")
        self.patterns = get_all_patterns()

    def extract(self, text: str) -> ExtractionResult:
        """
        Extract all intelligence from text.

        Args:
            text: Text to extract from (single message or full conversation)

        Returns:
            ExtractionResult with all extracted entities
        """
        result = ExtractionResult()

        # Extract each type of intelligence
        result.bank_accounts = self._extract_bank_accounts(text)
        result.upi_ids = self._extract_upi_ids(text)
        result.phone_numbers = self._extract_phone_numbers(text)
        result.phishing_links = self._extract_urls(text)
        result.emails = self._extract_emails(text)

        self.logger.info(
            "Extraction complete",
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
        Extract intelligence from a full conversation.

        Args:
            messages: List of message dicts with 'text' field

        Returns:
            ExtractionResult with deduplicated entities
        """
        # Combine all message texts
        full_text = " ".join(msg.get("text", "") for msg in messages)
        return self.extract(full_text)

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
    is_suspicious_url,
)

__all__ = [
    "IntelligenceExtractor",
    "ExtractionResult",
    "ExtractedEntity",
    "get_extractor",
    "IntelligenceType",
    "is_suspicious_url",
]
```

### 5.4 Write Extraction Tests

#### tests/test_extractor.py

```python
"""Tests for intelligence extraction module."""

import pytest

from src.intelligence.extractor import IntelligenceExtractor, ExtractionResult
from src.intelligence.patterns import is_suspicious_url, IntelligenceType


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
```

## Verification Checklist

- [ ] `src/intelligence/patterns.py` defines all regex patterns
- [ ] `src/intelligence/extractor.py` implements extraction logic
- [ ] Bank accounts (9-18 digits) extracted correctly
- [ ] UPI IDs (username@provider) extracted
- [ ] Phone numbers (Indian format) extracted
- [ ] Suspicious URLs flagged as phishing links
- [ ] Email addresses extracted
- [ ] Entities deduplicated across conversation
- [ ] All tests pass: `pytest tests/test_extractor.py -v`

## Integration Example

```python
# Usage in routes.py
from src.intelligence.extractor import get_extractor

@router.post("/api/v1/analyze")
async def analyze_message(request: AnalyzeRequest):
    # ... detection and engagement logic ...

    # Extract intelligence from full conversation
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

## Next Steps

After completing this milestone, proceed to **Milestone 6: Deployment** to set up Docker, CI/CD, and Google Cloud Run deployment.
