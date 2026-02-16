"""Tests for AI-first intelligence extraction with regex validation."""

import pytest

from src.intelligence.extractor import IntelligenceExtractor, ExtractionResult
from src.intelligence.validators import ExtractionSource
from src.api.schemas import ExtractedIntelligence, OtherIntelItem


class TestAIExtractionValidation:
    """Tests for AI extraction validation (the new AI-first approach)."""

    @pytest.fixture
    def extractor(self) -> IntelligenceExtractor:
        """Create extractor instance."""
        return IntelligenceExtractor()

    # Bank Account Validation Tests
    def test_validates_plain_bank_account(self, extractor: IntelligenceExtractor):
        """Should validate plain bank account numbers."""
        ai_extracted = {"bank_accounts": ["123456789012"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "123456789012" in result.bankAccounts

    def test_validates_formatted_bank_account(self, extractor: IntelligenceExtractor):
        """Should clean and validate formatted bank accounts."""
        ai_extracted = {"bank_accounts": ["1234-5678-9012-3456"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "1234567890123456" in result.bankAccounts

    def test_rejects_invalid_bank_account_too_short(self, extractor: IntelligenceExtractor):
        """Should reject bank accounts that are too short."""
        ai_extracted = {"bank_accounts": ["12345678"]}  # 8 digits, too short
        result = extractor.validate_ai_extraction(ai_extracted)
        assert len(result.bankAccounts) == 0

    def test_rejects_all_same_digit_account(self, extractor: IntelligenceExtractor):
        """Should reject bank accounts with all same digits."""
        ai_extracted = {"bank_accounts": ["000000000000"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert len(result.bankAccounts) == 0

    def test_rejects_phone_like_bank_account(self, extractor: IntelligenceExtractor):
        """Should reject bank accounts that look like phone numbers."""
        ai_extracted = {"bank_accounts": ["9876543210"]}  # 10 digits starting with 9 = phone
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "9876543210" not in result.bankAccounts

    # UPI Validation Tests
    def test_validates_standard_upi(self, extractor: IntelligenceExtractor):
        """Should validate standard UPI IDs."""
        ai_extracted = {"upi_ids": ["john@ybl"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "john@ybl" in result.upiIds

    def test_validates_paytm_upi(self, extractor: IntelligenceExtractor):
        """Should validate Paytm UPI."""
        ai_extracted = {"upi_ids": ["merchant123@paytm"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "merchant123@paytm" in result.upiIds

    def test_validates_multiple_upi(self, extractor: IntelligenceExtractor):
        """Should validate multiple UPI IDs."""
        ai_extracted = {"upi_ids": ["user@oksbi", "backup@okicici"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert len(result.upiIds) == 2

    def test_rejects_invalid_upi_no_at(self, extractor: IntelligenceExtractor):
        """Should reject UPI IDs without @."""
        ai_extracted = {"upi_ids": ["invalidupi"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert len(result.upiIds) == 0

    # Phone Number Validation Tests
    def test_validates_10_digit_phone(self, extractor: IntelligenceExtractor):
        """Should validate 10-digit Indian mobile."""
        ai_extracted = {"phone_numbers": ["9876543210"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "9876543210" in result.phoneNumbers

    def test_validates_phone_with_91(self, extractor: IntelligenceExtractor):
        """Should validate and clean phone with +91."""
        ai_extracted = {"phone_numbers": ["+91-9876543210"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "919876543210" in result.phoneNumbers

    def test_validates_phone_with_spaces(self, extractor: IntelligenceExtractor):
        """Should clean and validate phone with spaces."""
        ai_extracted = {"phone_numbers": ["98765 43210"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "9876543210" in result.phoneNumbers

    def test_rejects_invalid_phone_wrong_start(self, extractor: IntelligenceExtractor):
        """Should reject phones not starting with 6-9."""
        ai_extracted = {"phone_numbers": ["1234567890"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "1234567890" not in result.phoneNumbers

    # IFSC Validation Tests
    def test_validates_ifsc_code(self, extractor: IntelligenceExtractor):
        """Should validate IFSC codes."""
        ai_extracted = {"ifsc_codes": ["SBIN0012345"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "SBIN0012345" in result.ifscCodes

    def test_validates_hdfc_ifsc(self, extractor: IntelligenceExtractor):
        """Should validate HDFC IFSC."""
        ai_extracted = {"ifsc_codes": ["HDFC0001234"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "HDFC0001234" in result.ifscCodes

    def test_rejects_invalid_ifsc_wrong_format(self, extractor: IntelligenceExtractor):
        """Should reject invalid IFSC format."""
        ai_extracted = {"ifsc_codes": ["INVALID123"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert len(result.ifscCodes) == 0

    def test_rejects_ifsc_without_zero(self, extractor: IntelligenceExtractor):
        """Should reject IFSC without 0 in 5th position."""
        ai_extracted = {"ifsc_codes": ["SBIN1012345"]}  # 1 instead of 0 in 5th position
        result = extractor.validate_ai_extraction(ai_extracted)
        assert len(result.ifscCodes) == 0

    # URL Tests (URLs are kept as-is, AI understands context)
    def test_keeps_urls_as_is(self, extractor: IntelligenceExtractor):
        """Should keep URLs as-is from AI extraction."""
        ai_extracted = {"urls": ["https://sbi-verify.com/kyc", "http://bit.ly/scam"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert len(result.phishingLinks) == 2

    # Beneficiary Name Tests
    def test_validates_beneficiary_name(self, extractor: IntelligenceExtractor):
        """Should validate beneficiary names."""
        ai_extracted = {"beneficiary_names": ["Rajesh Kumar"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "Rajesh Kumar" in result.beneficiaryNames

    # Bank Name Tests
    def test_keeps_bank_names_as_is(self, extractor: IntelligenceExtractor):
        """Should keep bank names as-is."""
        ai_extracted = {"bank_names": ["SBI", "HDFC"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "SBI" in result.bankNames
        assert "HDFC" in result.bankNames

    # WhatsApp Number Tests
    def test_validates_whatsapp_number(self, extractor: IntelligenceExtractor):
        """Should validate WhatsApp numbers."""
        ai_extracted = {"whatsapp_numbers": ["9876543210"]}
        result = extractor.validate_ai_extraction(ai_extracted)
        assert "9876543210" in result.whatsappNumbers

    # Other Critical Info Tests
    def test_parses_other_critical_info(self, extractor: IntelligenceExtractor):
        """Should parse other_critical_info items."""
        ai_extracted = {
            "other_critical_info": [
                {"label": "Remote Access Tool", "value": "AnyDesk"},
                {"label": "Crypto Address", "value": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"},
            ]
        }
        result = extractor.validate_ai_extraction(ai_extracted)
        assert len(result.other_critical_info) == 2
        assert result.other_critical_info[0].label == "Remote Access Tool"
        assert result.other_critical_info[0].value == "AnyDesk"

    # Multiple Types Test
    def test_validates_multiple_types(self, extractor: IntelligenceExtractor):
        """Should validate multiple intelligence types together."""
        ai_extracted = {
            "bank_accounts": ["123456789012"],
            "upi_ids": ["scammer@paytm"],
            "phone_numbers": ["9876543210"],
            "ifsc_codes": ["SBIN0012345"],
            "beneficiary_names": ["Rajesh"],
            "urls": ["https://phishing.com"],
        }
        result = extractor.validate_ai_extraction(ai_extracted)
        assert len(result.bankAccounts) == 1
        assert len(result.upiIds) == 1
        assert len(result.phoneNumbers) == 1
        assert len(result.ifscCodes) == 1
        assert len(result.beneficiaryNames) == 1
        assert len(result.phishingLinks) == 1

    # Empty/None Tests
    def test_handles_empty_ai_extraction(self, extractor: IntelligenceExtractor):
        """Should handle empty AI extraction."""
        result = extractor.validate_ai_extraction({})
        assert len(result.bankAccounts) == 0
        assert len(result.upiIds) == 0

    def test_handles_none_ai_extraction(self, extractor: IntelligenceExtractor):
        """Should handle None AI extraction."""
        result = extractor.validate_ai_extraction(None)
        assert len(result.bankAccounts) == 0


class TestLLMExtractionValidation:
    """Tests for validate_llm_extraction method."""

    @pytest.fixture
    def extractor(self) -> IntelligenceExtractor:
        """Create extractor instance."""
        return IntelligenceExtractor()

    def test_validates_llm_extraction(self, extractor: IntelligenceExtractor):
        """Should validate LLM extraction."""
        llm_intel = ExtractedIntelligence(
            bankAccounts=["123456789012", "invalidshort"],
            upiIds=["valid@paytm", "invalid"],
            phoneNumbers=["9876543210", "1234567890"],
            ifscCodes=["SBIN0012345", "INVALID"],
        )
        result = extractor.validate_llm_extraction(llm_intel)
        assert "123456789012" in result.bankAccounts
        assert "invalidshort" not in result.bankAccounts
        assert "valid@paytm" in result.upiIds
        assert "invalid" not in result.upiIds
        assert "9876543210" in result.phoneNumbers
        assert "1234567890" not in result.phoneNumbers
        assert "SBIN0012345" in result.ifscCodes


class TestBackwardCompatibility:
    """Tests for backward compatibility methods."""

    @pytest.fixture
    def extractor(self) -> IntelligenceExtractor:
        """Create extractor instance."""
        return IntelligenceExtractor()

    def test_extract_returns_empty(self, extractor: IntelligenceExtractor):
        """extract() should return empty result (regex extraction disabled)."""
        result = extractor.extract("Transfer to 123456789012")
        assert not result.has_intelligence

    def test_extract_from_conversation_returns_empty(self, extractor: IntelligenceExtractor):
        """extract_from_conversation() should return empty result."""
        messages = [{"sender": "scammer", "text": "Pay to account 123456789012"}]
        result = extractor.extract_from_conversation(messages)
        assert not result.has_intelligence

    def test_parse_ai_extraction_works(self, extractor: IntelligenceExtractor):
        """parse_ai_extraction() should work for backward compatibility."""
        ai_extracted = {
            "bank_accounts": ["123456789012"],
            "upi_ids": ["test@paytm"],
        }
        result = extractor.parse_ai_extraction(ai_extracted)
        assert isinstance(result, ExtractionResult)
        assert "123456789012" in result.bank_accounts
        assert "test@paytm" in result.upi_ids


class TestSuspiciousUrl:
    """Tests for URL handling (kept from original tests)."""

    def test_shortener_is_suspicious(self):
        """Short URL services should be considered suspicious."""
        from src.intelligence.validators import is_suspicious_url
        assert is_suspicious_url("http://bit.ly/abc")
        assert is_suspicious_url("https://tinyurl.com/xyz")

    def test_phishing_keywords_suspicious(self):
        """URLs with phishing keywords should be suspicious."""
        from src.intelligence.validators import is_suspicious_url
        assert is_suspicious_url("http://sbi-login-verify.com")
        assert is_suspicious_url("https://update-kyc-hdfc.in")

    def test_free_tld_suspicious(self):
        """Free TLDs should be suspicious."""
        from src.intelligence.validators import is_suspicious_url
        assert is_suspicious_url("http://scamsite.tk")
        assert is_suspicious_url("https://phishing.ml")

    def test_normal_url_not_suspicious(self):
        """Normal URLs should not be suspicious."""
        from src.intelligence.validators import is_suspicious_url
        assert not is_suspicious_url("https://google.com")
        assert not is_suspicious_url("https://github.com/project")


class TestAIExtractsOnlyScammerDetails:
    """
    Tests to verify the AI-first approach correctly handles the 
    victim vs scammer detail distinction.
    
    These are conceptual tests - the actual distinction is done by the AI,
    and we just validate the format of what the AI returns.
    """

    @pytest.fixture
    def extractor(self) -> IntelligenceExtractor:
        """Create extractor instance."""
        return IntelligenceExtractor()

    def test_ai_should_extract_only_scammer_account(self, extractor: IntelligenceExtractor):
        """
        AI should extract only scammer's account, not victim's.
        
        In this test, we simulate what the AI SHOULD return after
        understanding the context of the scammer's message.
        """
        # Scammer's message: "Your account 9876543210123 has suspicious activity. 
        # Transfer to recovery account 1234567890987"
        #
        # AI understands:
        # - 9876543210123 = victim's account (mentioned with "Your account")
        # - 1234567890987 = scammer's account (mentioned with "Transfer to")
        #
        # AI should return ONLY the scammer's account:
        ai_extracted = {
            "bank_accounts": ["1234567890987"],  # Only scammer's
            "upi_ids": [],
            "phone_numbers": [],
        }
        
        result = extractor.validate_ai_extraction(ai_extracted)
        
        # Validation should pass the scammer's account
        assert "1234567890987" in result.bankAccounts
        # Victim's account should NOT be in the result (AI didn't extract it)
        assert "9876543210123" not in result.bankAccounts

    def test_full_scam_message_ai_extraction(self, extractor: IntelligenceExtractor):
        """
        Test a full scam message where AI correctly identifies all scammer details.
        """
        # What the AI SHOULD extract from:
        # "Hello sir, I am Rajesh Kumar from SBI fraud prevention. 
        # Your account 9876543210123 has suspicious activity. 
        # Transfer to recovery account 1234567890987 IFSC SBIN0012345 
        # or pay via UPI rajesh.sbi.verify@paytm. 
        # Visit https://sbi-secure-verify.com/confirm immediately. 
        # Call me 9123456789 for help."
        
        ai_extracted = {
            "bank_accounts": ["1234567890987"],  # Only recovery account (scammer's)
            "upi_ids": ["rajesh.sbi.verify@paytm"],  # Scammer's UPI
            "phone_numbers": ["9123456789"],  # Scammer's phone ("call me")
            "beneficiary_names": ["Rajesh Kumar"],  # Scammer's name
            "urls": ["https://sbi-secure-verify.com/confirm"],  # Scammer's phishing URL
            "ifsc_codes": ["SBIN0012345"],  # Scammer's bank IFSC
        }
        
        result = extractor.validate_ai_extraction(ai_extracted)
        
        # All scammer's details should be validated
        assert "1234567890987" in result.bankAccounts
        assert "rajesh.sbi.verify@paytm" in result.upiIds
        assert "9123456789" in result.phoneNumbers
        assert "Rajesh Kumar" in result.beneficiaryNames
        assert "https://sbi-secure-verify.com/confirm" in result.phishingLinks
        assert "SBIN0012345" in result.ifscCodes
        
        # Victim's account should NOT appear
        assert "9876543210123" not in result.bankAccounts
