"""Hybrid intelligence extraction from conversation messages.

Combines fast regex patterns with AI-powered extraction during engagement
for maximum intelligence capture.
"""

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.intelligence.patterns import (
    IntelligenceType,
    ExtractionSource,
    BANK_ACCOUNT_PATTERNS,
    UPI_PATTERN,
    UPI_GENERIC_PATTERN,
    PHONE_PATTERNS,
    URL_PATTERN,
    EMAIL_PATTERN,
    IFSC_PATTERN,
    BANK_NAME_PATTERN,
    BENEFICIARY_NAME_PATTERNS,
    WHATSAPP_PATTERNS,
    INDIAN_BANK_NAMES,
    is_suspicious_url,
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
    beneficiary_names: list[str] = field(default_factory=list)
    bank_names: list[str] = field(default_factory=list)
    ifsc_codes: list[str] = field(default_factory=list)
    whatsapp_numbers: list[str] = field(default_factory=list)
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
            self.emails or
            self.beneficiary_names or
            self.bank_names or
            self.ifsc_codes or
            self.whatsapp_numbers
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response format."""
        return {
            "bankAccounts": self.bank_accounts,
            "upiIds": self.upi_ids,
            "phoneNumbers": self.phone_numbers,
            "phishingLinks": self.phishing_links,
            "emails": self.emails,
            "beneficiaryNames": self.beneficiary_names,
            "bankNames": self.bank_names,
            "ifscCodes": self.ifsc_codes,
            "whatsappNumbers": self.whatsapp_numbers,
        }

    def merge_with(self, other: "ExtractionResult") -> "ExtractionResult":
        """Merge with another extraction result, deduplicating entities."""
        return ExtractionResult(
            bank_accounts=list(set(self.bank_accounts + other.bank_accounts)),
            upi_ids=list(set(self.upi_ids + other.upi_ids)),
            phone_numbers=list(set(self.phone_numbers + other.phone_numbers)),
            phishing_links=list(set(self.phishing_links + other.phishing_links)),
            emails=list(set(self.emails + other.emails)),
            beneficiary_names=list(set(self.beneficiary_names + other.beneficiary_names)),
            bank_names=list(set(self.bank_names + other.bank_names)),
            ifsc_codes=list(set(self.ifsc_codes + other.ifsc_codes)),
            whatsapp_numbers=list(set(self.whatsapp_numbers + other.whatsapp_numbers)),
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

    def extract(self, text: str) -> ExtractionResult:
        """
        Extract all intelligence from text using regex patterns.

        Args:
            text: Text to extract from (single message or full conversation)

        Returns:
            ExtractionResult with all extracted entities
        """
        result = ExtractionResult(source=ExtractionSource.REGEX)

        # Extract phone numbers first (they overlap with bank account pattern)
        result.phone_numbers = self._extract_phone_numbers(text)
        phone_set = set(result.phone_numbers)
        
        # Extract each type of intelligence
        result.bank_accounts = self._extract_bank_accounts(text, phone_set)
        result.upi_ids = self._extract_upi_ids(text)
        result.phishing_links = self._extract_urls(text)
        result.emails = self._extract_emails(text)
        
        # Extract new intelligence types
        result.beneficiary_names = self._extract_beneficiary_names(text)
        result.bank_names = self._extract_bank_names(text)
        result.ifsc_codes = self._extract_ifsc_codes(text)
        result.whatsapp_numbers = self._extract_whatsapp_numbers(text)

        self.logger.info(
            "Regex extraction complete",
            bank_accounts=len(result.bank_accounts),
            upi_ids=len(result.upi_ids),
            phone_numbers=len(result.phone_numbers),
            urls=len(result.phishing_links),
            emails=len(result.emails),
            beneficiary_names=len(result.beneficiary_names),
            bank_names=len(result.bank_names),
            ifsc_codes=len(result.ifsc_codes),
            whatsapp_numbers=len(result.whatsapp_numbers),
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

        # Parse new intelligence types
        raw_beneficiaries = ai_extracted.get("beneficiary_names", [])
        for name in raw_beneficiaries:
            clean_name = str(name).strip()
            if self._is_valid_name(clean_name):
                result.beneficiary_names.append(clean_name)

        raw_banks = ai_extracted.get("bank_names", [])
        for bank in raw_banks:
            clean_bank = str(bank).strip()
            if clean_bank:
                result.bank_names.append(clean_bank)

        raw_ifsc = ai_extracted.get("ifsc_codes", [])
        for ifsc in raw_ifsc:
            clean_ifsc = str(ifsc).strip().upper()
            if self._is_valid_ifsc(clean_ifsc):
                result.ifsc_codes.append(clean_ifsc)

        raw_whatsapp = ai_extracted.get("whatsapp_numbers", [])
        for wa_num in raw_whatsapp:
            clean = self._clean_number(str(wa_num))
            if self._is_valid_phone(clean):
                result.whatsapp_numbers.append(clean)

        self.logger.info(
            "AI extraction parsed",
            bank_accounts=len(result.bank_accounts),
            upi_ids=len(result.upi_ids),
            phone_numbers=len(result.phone_numbers),
            urls=len(result.phishing_links),
            emails=len(result.emails),
            beneficiary_names=len(result.beneficiary_names),
            bank_names=len(result.bank_names),
            ifsc_codes=len(result.ifsc_codes),
            whatsapp_numbers=len(result.whatsapp_numbers),
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
            total_beneficiary_names=len(merged.beneficiary_names),
            total_bank_names=len(merged.bank_names),
            total_ifsc_codes=len(merged.ifsc_codes),
            total_whatsapp_numbers=len(merged.whatsapp_numbers),
        )

        return merged

    def _extract_bank_accounts(self, text: str, phone_numbers: set[str] | None = None) -> list[str]:
        """Extract bank account numbers, excluding phone numbers."""
        accounts = set()
        phone_set = phone_numbers or set()

        for pattern_config in BANK_ACCOUNT_PATTERNS:
            matches = pattern_config.pattern.findall(text)
            for match in matches:
                # Clean and validate
                clean = self._clean_number(match)
                if self._is_valid_bank_account(clean):
                    # CRITICAL: Check if this looks like a phone number before accepting as bank account
                    # This prevents misclassification of numbers like 919123456789 (12 digit phone with country code)
                    if self._looks_like_phone(clean):
                        continue
                    # Also exclude if already in phone_set
                    if clean in phone_set:
                        continue
                    accounts.add(clean)

        return list(accounts)

    def _extract_upi_ids(self, text: str) -> list[str]:
        """Extract UPI IDs."""
        upi_ids = set()

        # Known provider pattern - these are definitely UPI IDs
        matches = UPI_PATTERN.pattern.findall(text)
        upi_ids.update(m.lower() for m in matches)

        # Only use generic pattern if explicitly has "upi" keyword nearby
        # This avoids false positives from email-like patterns
        # Generic pattern (filter out emails)
        generic_matches = UPI_GENERIC_PATTERN.pattern.findall(text)
        for match in generic_matches:
            # Exclude if looks like email (has standard email TLD or common domain)
            if self._looks_like_email(match):
                continue
            # Exclude if already captured by known provider pattern
            if match.lower() in upi_ids:
                continue
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

    def _extract_beneficiary_names(self, text: str) -> list[str]:
        """Extract beneficiary/account holder names."""
        names = set()

        for pattern_config in BENEFICIARY_NAME_PATTERNS:
            matches = pattern_config.pattern.findall(text)
            for match in matches:
                # Clean the name
                clean_name = str(match).strip().strip("'\"")
                if self._is_valid_name(clean_name):
                    # Title case the name for consistency
                    names.add(clean_name.title())

        return list(names)

    def _extract_bank_names(self, text: str) -> list[str]:
        """Extract Indian bank names."""
        banks = set()

        matches = BANK_NAME_PATTERN.pattern.findall(text)
        for match in matches:
            # Normalize bank name (uppercase for abbreviations, title case for full names)
            clean_bank = str(match).strip()
            # Standardize common abbreviations
            upper_bank = clean_bank.upper()
            if upper_bank in ["SBI", "PNB", "BOB", "BOI", "UCO", "PSB", "IOB", "HDFC", "ICICI", "IDBI", "RBL", "IDFC"]:
                banks.add(upper_bank)
            elif upper_bank in ["AXIS", "KOTAK", "FEDERAL", "BANDHAN", "CANARA", "EQUITAS", "UJJIVAN", "INDUSIND"]:
                banks.add(clean_bank.title())
            else:
                banks.add(clean_bank.title())

        return list(banks)

    def _extract_ifsc_codes(self, text: str) -> list[str]:
        """Extract IFSC codes."""
        ifsc_codes = set()

        matches = IFSC_PATTERN.pattern.findall(text)
        for match in matches:
            clean_ifsc = str(match).strip().upper()
            if self._is_valid_ifsc(clean_ifsc):
                ifsc_codes.add(clean_ifsc)

        return list(ifsc_codes)

    def _extract_whatsapp_numbers(self, text: str) -> list[str]:
        """Extract WhatsApp phone numbers."""
        whatsapp_nums = set()

        for pattern_config in WHATSAPP_PATTERNS:
            matches = pattern_config.pattern.findall(text)
            for match in matches:
                clean = self._clean_number(str(match))
                if self._is_valid_phone(clean):
                    whatsapp_nums.add(clean)

        return list(whatsapp_nums)

    def _clean_number(self, number: str) -> str:
        """Remove formatting from numbers."""
        return re.sub(r"[-\s]", "", number)
    def _looks_like_phone(self, number: str) -> bool:
        """
        Check if a number looks like a phone number, not a bank account.
        
        A number is definitely a phone if:
        - It's exactly 10 digits starting with 6,7,8,9
        - It starts with +91 or 91 followed by exactly 10 digits (12 digits total with 91 prefix)
        - It matches Indian phone patterns
        """
        if not number or not number.isdigit():
            return False
        
        # Pattern 1: Exactly 10 digits starting with 6,7,8,9 → Definitely a phone
        if len(number) == 10 and number[0] in "6789":
            return True
        
        # Pattern 2: 12 digits starting with 91 followed by valid 10-digit phone
        # e.g., 919876543210 → 91 + 9876543210
        if len(number) == 12 and number.startswith("91"):
            suffix = number[2:]  # Remove the 91 prefix
            if suffix[0] in "6789":  # Check if remaining 10 digits starts with 6-9
                return True
        
        # Pattern 3: 13 digits starting with +91 → already handled by _clean_number
        # but just in case
        if len(number) == 13 and number.startswith("91"):
            suffix = number[2:]
            if len(suffix) == 10 and suffix[0] in "6789":
                return True
        
        return False
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
        clean = number
        if clean.startswith("+91"):
            clean = clean[3:]
        elif clean.startswith("91") and len(clean) == 12:
            clean = clean[2:]
        # Remove any remaining non-digits
        clean = re.sub(r"\D", "", clean)
        if len(clean) != 10:
            return False
        if clean[0] not in "6789":  # Indian mobile starts with 6-9
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

    def _is_valid_name(self, name: str) -> bool:
        """Validate beneficiary name."""
        if not name or len(name) < 2:
            return False
        # Should contain only letters, spaces, and common name characters
        if not re.match(r"^[A-Za-z][A-Za-z\s.''-]+$", name):
            return False
        # Should have reasonable length (2-50 characters)
        if len(name) > 50:
            return False
        # Should not be common words that might be false positives
        common_words = ["the", "and", "for", "with", "from", "bank", "account", "transfer", "send", "pay"]
        if name.lower() in common_words:
            return False
        return True

    def _is_valid_ifsc(self, ifsc: str) -> bool:
        """Validate IFSC code format."""
        # IFSC format: 4 letters (bank code) + 0 + 6 alphanumeric
        if not ifsc or len(ifsc) != 11:
            return False
        # First 4 characters must be letters
        if not ifsc[:4].isalpha():
            return False
        # 5th character must be 0
        if ifsc[4] != '0':
            return False
        # Last 6 characters must be alphanumeric
        if not ifsc[5:].isalnum():
            return False
        return True


# Singleton instance
_extractor_instance: IntelligenceExtractor | None = None


def get_extractor() -> IntelligenceExtractor:
    """Get or create extractor instance."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = IntelligenceExtractor()
    return _extractor_instance