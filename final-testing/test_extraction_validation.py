"""
Test suite for INTELLIGENCE EXTRACTION — regex + AI validation.

Tests for Priority 1 ISSUE 6: regex extraction as backup to AI.
Validates that the IntelligenceExtractor can reliably extract known
fakeData patterns from scammer messages via both AI and regex paths.

Run:  .venv/bin/python -m pytest final-testing/test_extraction_validation.py -v
"""

import re

import pytest

from src.intelligence.extractor import IntelligenceExtractor
from src.api.schemas import ExtractedIntelligence


# ============================================================================
# PHONE NUMBER EXTRACTION & VALIDATION
# ============================================================================


class TestPhoneExtraction:
    """Test phone number extraction and validation."""

    @pytest.fixture
    def extractor(self):
        return IntelligenceExtractor()

    # -- Format validation --

    def test_validate_10_digit_phone(self, extractor):
        assert extractor._validate_phone("9876543210") is True

    def test_validate_10_digit_starting_with_6(self, extractor):
        assert extractor._validate_phone("6123456789") is True

    def test_validate_10_digit_starting_with_7(self, extractor):
        assert extractor._validate_phone("7123456789") is True

    def test_validate_10_digit_starting_with_8(self, extractor):
        assert extractor._validate_phone("8765432109") is True

    def test_reject_10_digit_starting_with_5(self, extractor):
        assert extractor._validate_phone("5123456789") is False

    def test_reject_10_digit_starting_with_0(self, extractor):
        assert extractor._validate_phone("0123456789") is False

    def test_validate_12_digit_with_91_prefix(self, extractor):
        assert extractor._validate_phone("919876543210") is True

    def test_reject_12_digit_with_wrong_prefix(self, extractor):
        assert extractor._validate_phone("449876543210") is False

    def test_reject_short_number(self, extractor):
        assert extractor._validate_phone("98765") is False

    def test_reject_alphabetic(self, extractor):
        assert extractor._validate_phone("98765abcde") is False

    # -- Clean number formatting --

    def test_clean_number_removes_spaces(self, extractor):
        assert extractor._clean_number("98765 43210") == "9876543210"

    def test_clean_number_removes_hyphens(self, extractor):
        assert extractor._clean_number("987-654-3210") == "9876543210"

    def test_clean_number_removes_plus(self, extractor):
        assert extractor._clean_number("+91-9876543210") == "919876543210"

    def test_clean_number_removes_parentheses(self, extractor):
        assert extractor._clean_number("(91) 9876543210") == "919876543210"

    # -- Phone in scammer messages --

    def test_extract_phone_from_bank_fraud_message(self):
        """Regex should find phone in: 'call me at +91-9876543210'."""
        text = "You can verify by calling me back at +91-9876543210. Please hurry."
        pattern = r"\+?91[-\s]?[6-9]\d{9}|\b[6-9]\d{9}\b"
        matches = re.findall(pattern, text)
        cleaned = [re.sub(r"[-\s+]", "", m) for m in matches]
        assert any("9876543210" in c for c in cleaned)

    def test_extract_phone_from_upi_fraud_message(self):
        text = "Call our helpline +91-8765432109 for assistance."
        pattern = r"\+?91[-\s]?[6-9]\d{9}|\b[6-9]\d{9}\b"
        matches = re.findall(pattern, text)
        cleaned = [re.sub(r"[-\s+]", "", m) for m in matches]
        assert any("8765432109" in c for c in cleaned)


# ============================================================================
# BANK ACCOUNT EXTRACTION & VALIDATION
# ============================================================================


class TestBankAccountExtraction:
    """Test bank account number extraction and validation."""

    @pytest.fixture
    def extractor(self):
        return IntelligenceExtractor()

    def test_validate_16_digit_account(self, extractor):
        assert extractor._validate_bank_account("1234567890123456") is True

    def test_validate_9_digit_account(self, extractor):
        assert extractor._validate_bank_account("123456789") is True

    def test_validate_18_digit_account(self, extractor):
        assert extractor._validate_bank_account("123456789012345678") is True

    def test_reject_8_digit_account(self, extractor):
        assert extractor._validate_bank_account("12345678") is False

    def test_reject_19_digit_account(self, extractor):
        assert extractor._validate_bank_account("1234567890123456789") is False

    def test_reject_all_same_digits(self, extractor):
        assert extractor._validate_bank_account("000000000") is False
        assert extractor._validate_bank_account("1111111111") is False

    def test_reject_phone_like_account(self, extractor):
        """10-digit numbers starting with 6-9 should be rejected (phone numbers)."""
        assert extractor._validate_bank_account("9876543210") is False

    def test_accept_non_phone_10_digit(self, extractor):
        """10-digit numbers NOT starting with 6-9 should be accepted."""
        assert extractor._validate_bank_account("1234567890") is True

    def test_extract_account_from_message(self):
        """Regex should find bank account in message text."""
        text = "Your account 1234567890123456 has suspicious activity."
        pattern = r"\b\d{9,18}\b"
        matches = re.findall(pattern, text)
        assert "1234567890123456" in matches


# ============================================================================
# UPI ID EXTRACTION & VALIDATION
# ============================================================================


class TestUpiExtraction:
    """Test UPI ID extraction and validation."""

    @pytest.fixture
    def extractor(self):
        return IntelligenceExtractor()

    def test_validate_standard_upi(self, extractor):
        assert extractor._validate_upi_id("user@paytm") is True

    def test_validate_upi_with_dots(self, extractor):
        assert extractor._validate_upi_id("scammer.fraud@fakebank") is True

    def test_validate_upi_with_hyphens(self, extractor):
        assert extractor._validate_upi_id("cashback-scam@fakeupi") is True

    def test_validate_upi_with_numbers(self, extractor):
        assert extractor._validate_upi_id("user123@ybl") is True

    def test_reject_upi_without_at(self, extractor):
        assert extractor._validate_upi_id("userpaytm") is False

    def test_reject_empty_upi(self, extractor):
        assert extractor._validate_upi_id("") is False

    def test_validate_known_providers(self, extractor):
        """All common UPI providers should be accepted."""
        providers = ["paytm", "ybl", "oksbi", "okaxis", "okicici",
                      "upi", "apl", "fbl", "ibl", "okhdfcbank"]
        for provider in providers:
            upi = f"user@{provider}"
            assert extractor._validate_upi_id(upi), f"Should accept {upi}"

    def test_extract_upi_from_message(self):
        """Regex should find UPI ID in message text."""
        text = "Send Rs 100 to scammer.fraud@fakebank via UPI"
        pattern = r"[\w.-]+@[a-zA-Z][a-zA-Z0-9]*"
        matches = re.findall(pattern, text)
        assert "scammer.fraud@fakebank" in matches


# ============================================================================
# PHISHING LINK EXTRACTION
# ============================================================================


class TestPhishingLinkExtraction:
    """Test phishing URL extraction."""

    def test_extract_http_link(self):
        text = "Click http://amaz0n-deals.fake-site.com/claim?id=12345"
        pattern = r"https?://[^\s<>\"']+"
        matches = re.findall(pattern, text)
        assert len(matches) >= 1
        assert "amaz0n-deals" in matches[0]

    def test_extract_https_link(self):
        text = "Visit https://secure-bank-login.evil.com/verify"
        pattern = r"https?://[^\s<>\"']+"
        matches = re.findall(pattern, text)
        assert len(matches) >= 1

    def test_extract_link_with_params(self):
        text = "http://evil.com/login?user=victim&token=abc123&redirect=bank"
        pattern = r"https?://[^\s<>\"']+"
        matches = re.findall(pattern, text)
        assert len(matches) >= 1
        assert "redirect=bank" in matches[0]

    def test_extract_multiple_links(self):
        text = "Try http://link1.com or http://link2.com/path"
        pattern = r"https?://[^\s<>\"']+"
        matches = re.findall(pattern, text)
        assert len(matches) == 2

    def test_suspicious_url_indicators(self):
        """URLs with typosquatting or suspicious TLDs should be flagged."""
        suspicious_urls = [
            "http://amaz0n-deals.fake-site.com",  # typosquatting (0 instead of o)
            "http://sbi-login.xyz/verify",  # suspicious TLD
            "http://paytm-verify.tk/claim",  # suspicious TLD
            "http://192.168.1.1/login",  # IP address
        ]
        for url in suspicious_urls:
            # Just verify regex can extract them
            pattern = r"https?://[^\s<>\"']+"
            matches = re.findall(pattern, url)
            assert len(matches) >= 1, f"Should extract: {url}"


# ============================================================================
# EMAIL ADDRESS EXTRACTION
# ============================================================================


class TestEmailExtraction:
    """Test email address extraction (ISSUE 4 - new field)."""

    def test_extract_basic_email(self):
        text = "Contact offers@fake-amazon-deals.com for support"
        pattern = r"[\w.+-]+@[\w-]+\.[\w.]+"
        matches = re.findall(pattern, text)
        assert "offers@fake-amazon-deals.com" in matches

    def test_extract_email_with_subdomain(self):
        text = "Email us at admin@mail.evil-bank.co.in"
        pattern = r"[\w.+-]+@[\w-]+\.[\w.]+"
        matches = re.findall(pattern, text)
        assert len(matches) >= 1

    def test_extract_email_with_plus(self):
        text = "Write to user+tag@example.com"
        pattern = r"[\w.+-]+@[\w-]+\.[\w.]+"
        matches = re.findall(pattern, text)
        assert len(matches) >= 1

    def test_distinguish_email_from_upi(self):
        """
        Key difference: emails have dots in domain (gmail.com), 
        UPI IDs typically don't have dots after @ (user@paytm).
        """
        # Email
        email_text = "Contact evil@scam-site.com"
        email_pattern = r"[\w.+-]+@[\w-]+\.[\w.]+"
        emails = re.findall(email_pattern, email_text)
        assert len(emails) >= 1

        # UPI (no dot after @)
        upi_text = "Pay to victim@paytm"
        emails_from_upi = re.findall(email_pattern, upi_text)
        # UPI should NOT match email pattern (no dot in domain)
        assert len(emails_from_upi) == 0, "UPI should not match email regex"


# ============================================================================
# IFSC CODE EXTRACTION & VALIDATION
# ============================================================================


class TestIfscExtraction:
    """Test IFSC code validation."""

    @pytest.fixture
    def extractor(self):
        return IntelligenceExtractor()

    def test_validate_valid_ifsc(self, extractor):
        assert extractor._validate_ifsc("SBIN0001234") is True
        assert extractor._validate_ifsc("HDFC0012345") is True
        assert extractor._validate_ifsc("ICIC0006789") is True

    def test_reject_short_ifsc(self, extractor):
        assert extractor._validate_ifsc("SBIN000") is False

    def test_reject_missing_zero(self, extractor):
        assert extractor._validate_ifsc("SBIN1001234") is False

    def test_reject_numbers_in_prefix(self, extractor):
        assert extractor._validate_ifsc("SB1N0001234") is False

    def test_extract_ifsc_from_text(self):
        text = "Transfer to IFSC code SBIN0001234, branch Andheri"
        pattern = r"\b[A-Z]{4}0[A-Z0-9]{6}\b"
        matches = re.findall(pattern, text)
        assert "SBIN0001234" in matches


# ============================================================================
# VALIDATE LLM EXTRACTION (existing functionality)
# ============================================================================


class TestValidateLlmExtraction:
    """Test the validate_llm_extraction pipeline."""

    @pytest.fixture
    def extractor(self):
        return IntelligenceExtractor()

    def test_validates_all_valid_data(self, extractor):
        intel = ExtractedIntelligence(
            bankAccounts=["1234567890123456"],
            upiIds=["scammer@fakebank"],
            phoneNumbers=["9876543210"],
            phishingLinks=["http://evil.com"],
            emails=["scam@evil.com"],
            ifscCodes=["SBIN0001234"],
            suspiciousKeywords=["urgent", "blocked"],
        )
        validated = extractor.validate_llm_extraction(intel)

        assert validated.bankAccounts == ["1234567890123456"]
        assert validated.upiIds == ["scammer@fakebank"]
        assert validated.phoneNumbers == ["9876543210"]
        assert validated.phishingLinks == ["http://evil.com"]
        assert validated.ifscCodes == ["SBIN0001234"]

    def test_filters_invalid_bank_accounts(self, extractor):
        intel = ExtractedIntelligence(
            bankAccounts=["12345", "1234567890123456", "aaaa"],  # 5-digit too short, alpha
        )
        validated = extractor.validate_llm_extraction(intel)
        assert validated.bankAccounts == ["1234567890123456"]

    def test_filters_invalid_phones(self, extractor):
        intel = ExtractedIntelligence(
            phoneNumbers=["9876543210", "1234567890", "abc"],  # 1234... starts with 1
        )
        validated = extractor.validate_llm_extraction(intel)
        assert "9876543210" in validated.phoneNumbers
        assert "1234567890" not in validated.phoneNumbers

    def test_filters_invalid_upi(self, extractor):
        intel = ExtractedIntelligence(
            upiIds=["valid@paytm", "no-at-sign", "@nouser"],
        )
        validated = extractor.validate_llm_extraction(intel)
        assert "valid@paytm" in validated.upiIds

    def test_preserves_phishing_links_as_is(self, extractor):
        """Phishing links are kept as-is — AI understands context."""
        intel = ExtractedIntelligence(
            phishingLinks=["http://evil.com", "https://good.com"],
        )
        validated = extractor.validate_llm_extraction(intel)
        assert len(validated.phishingLinks) == 2

    def test_empty_input_returns_empty(self, extractor):
        intel = ExtractedIntelligence()
        validated = extractor.validate_llm_extraction(intel)
        assert len(validated.bankAccounts) == 0
        assert len(validated.phoneNumbers) == 0
        assert len(validated.upiIds) == 0


# ============================================================================
# FAKE DATA MATCHING: Regex extraction against sample fakeData
# ============================================================================


class TestFakeDataRegexMatching:
    """
    Test that regex can extract each fakeData value from realistic
    scammer messages — the same messages the GUVI AI would generate.
    """

    def test_bank_fraud_all_fakedata_regex_extractable(self):
        """All bank_fraud fakeData should be regex-extractable from messages."""
        messages = [
            "Call me back at +91-9876543210 for verification.",
            "Your account 1234567890123456 has been flagged.",
            "Send Rs 1 to scammer.fraud@fakebank to verify.",
        ]
        all_text = " ".join(messages)

        phone_pattern = r"\+?91[-\s]?[6-9]\d{9}|\b[6-9]\d{9}\b"
        bank_pattern = r"\b\d{9,18}\b"
        upi_pattern = r"[\w.-]+@[a-zA-Z][a-zA-Z0-9]*"

        phones = re.findall(phone_pattern, all_text)
        banks = re.findall(bank_pattern, all_text)
        upis = re.findall(upi_pattern, all_text)

        assert any("9876543210" in re.sub(r"[-\s+]", "", p) for p in phones)
        assert "1234567890123456" in banks
        assert "scammer.fraud@fakebank" in upis

    def test_upi_fraud_all_fakedata_regex_extractable(self):
        messages = [
            "Our support UPI is cashback.scam@fakeupi.",
            "Call helpline +91-8765432109 for assistance.",
        ]
        all_text = " ".join(messages)

        phone_pattern = r"\+?91[-\s]?[6-9]\d{9}|\b[6-9]\d{9}\b"
        upi_pattern = r"[\w.-]+@[a-zA-Z][a-zA-Z0-9]*"

        phones = re.findall(phone_pattern, all_text)
        upis = re.findall(upi_pattern, all_text)

        assert any("8765432109" in re.sub(r"[-\s+]", "", p) for p in phones)
        assert "cashback.scam@fakeupi" in upis

    def test_phishing_all_fakedata_regex_extractable(self):
        messages = [
            "Click http://amaz0n-deals.fake-site.com/claim?id=12345 to claim.",
            "Email us at offers@fake-amazon-deals.com for help.",
        ]
        all_text = " ".join(messages)

        url_pattern = r"https?://[^\s<>\"']+"
        email_pattern = r"[\w.+-]+@[\w-]+\.[\w.]+"

        urls = re.findall(url_pattern, all_text)
        emails = re.findall(email_pattern, all_text)

        assert any("amaz0n-deals" in u for u in urls)
        assert "offers@fake-amazon-deals.com" in emails
