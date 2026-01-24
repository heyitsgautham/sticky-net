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

    # Beneficiary Name Tests
    def test_extracts_account_holder_name(self, extractor: IntelligenceExtractor):
        """Should extract account holder names."""
        text = "Account Holder: Rahul Kumar"
        result = extractor.extract(text)
        assert "Rahul Kumar" in result.beneficiary_names

    def test_extracts_name_from_upi_context(self, extractor: IntelligenceExtractor):
        """Should extract name when mentioned with UPI."""
        text = "the name will show as 'Rahul Kumar' when you enter the UPI"
        result = extractor.extract(text)
        assert any("Rahul Kumar" in name for name in result.beneficiary_names)

    def test_extracts_beneficiary_name(self, extractor: IntelligenceExtractor):
        """Should extract beneficiary names."""
        text = "Beneficiary Name: Priya Sharma"
        result = extractor.extract(text)
        assert "Priya Sharma" in result.beneficiary_names

    def test_extracts_name_from_transfer_context(self, extractor: IntelligenceExtractor):
        """Should extract names from transfer recipient context."""
        text = "Transfer to Vikram Singh - Officer"
        result = extractor.extract(text)
        assert any("Vikram Singh" in name for name in result.beneficiary_names)

    # Bank Name Tests
    def test_extracts_sbi_bank_name(self, extractor: IntelligenceExtractor):
        """Should extract SBI bank name."""
        text = "Bank: SBI (State Bank of India)"
        result = extractor.extract(text)
        assert any("SBI" in bank or "State Bank of India" in bank for bank in result.bank_names)

    def test_extracts_hdfc_bank_name(self, extractor: IntelligenceExtractor):
        """Should extract HDFC bank name."""
        text = "Transfer to HDFC Bank account"
        result = extractor.extract(text)
        assert any("HDFC" in bank for bank in result.bank_names)

    def test_extracts_icici_bank_name(self, extractor: IntelligenceExtractor):
        """Should extract ICICI bank name."""
        text = "Use ICICI Bank for the transfer"
        result = extractor.extract(text)
        assert any("ICICI" in bank for bank in result.bank_names)

    def test_extracts_multiple_bank_names(self, extractor: IntelligenceExtractor):
        """Should extract multiple bank names."""
        text = "You can transfer from SBI, HDFC, or Axis Bank"
        result = extractor.extract(text)
        assert len(result.bank_names) >= 2

    # IFSC Code Tests
    def test_extracts_ifsc_code(self, extractor: IntelligenceExtractor):
        """Should extract valid IFSC codes."""
        text = "IFSC Code: SBIN0001234"
        result = extractor.extract(text)
        assert "SBIN0001234" in result.ifsc_codes

    def test_extracts_hdfc_ifsc(self, extractor: IntelligenceExtractor):
        """Should extract HDFC IFSC code."""
        text = "Use IFSC: HDFC0001234"
        result = extractor.extract(text)
        assert "HDFC0001234" in result.ifsc_codes

    def test_extracts_ifsc_without_prefix(self, extractor: IntelligenceExtractor):
        """Should extract IFSC code without prefix label."""
        text = "The code is ICIC0002345"
        result = extractor.extract(text)
        assert "ICIC0002345" in result.ifsc_codes

    def test_ignores_invalid_ifsc(self, extractor: IntelligenceExtractor):
        """Should ignore invalid IFSC patterns."""
        text = "Code: ABC123"  # Too short, wrong format
        result = extractor.extract(text)
        assert "ABC123" not in result.ifsc_codes

    # WhatsApp Number Tests
    def test_extracts_whatsapp_number(self, extractor: IntelligenceExtractor):
        """Should extract WhatsApp numbers."""
        text = "WhatsApp Number: +91 9876543210"
        result = extractor.extract(text)
        assert any("9876543210" in num for num in result.whatsapp_numbers)

    def test_extracts_whatsapp_with_prefix(self, extractor: IntelligenceExtractor):
        """Should extract WhatsApp numbers with various prefixes."""
        text = "Contact on WhatsApp: 9123456789"
        result = extractor.extract(text)
        assert any("9123456789" in num for num in result.whatsapp_numbers)

    def test_extracts_wa_shorthand(self, extractor: IntelligenceExtractor):
        """Should extract numbers with WA prefix."""
        text = "WA: 8765432109"
        result = extractor.extract(text)
        assert any("8765432109" in num for num in result.whatsapp_numbers)

    def test_extracts_whatsapp_formatted_number(self, extractor: IntelligenceExtractor):
        """Should extract formatted WhatsApp numbers."""
        text = "Send screenshot to WhatsApp +91-98765-43210"
        result = extractor.extract(text)
        assert any("9876543210" in num for num in result.whatsapp_numbers)

    # Full Extraction Tests
    def test_extracts_multiple_types(self, extractor: IntelligenceExtractor):
        """Should extract multiple intelligence types."""
        text = """
        Send Rs. 5000 to A/C: 12345678901234
        Or use UPI: scammer@ybl
        For help call 9999888877
        Or visit http://bit.ly/verify-account
        Email: help@scam.com
        Account Holder: Rahul Kumar
        Bank: SBI
        IFSC Code: SBIN0001234
        WhatsApp Number: +91 9876543210
        """
        result = extractor.extract(text)

        assert len(result.bank_accounts) >= 1
        assert len(result.upi_ids) >= 1
        assert len(result.phone_numbers) >= 1
        assert len(result.phishing_links) >= 1
        assert len(result.emails) >= 1
        assert len(result.beneficiary_names) >= 1
        assert len(result.bank_names) >= 1
        assert len(result.ifsc_codes) >= 1
        assert len(result.whatsapp_numbers) >= 1

    def test_has_intelligence_property(self, extractor: IntelligenceExtractor):
        """Should correctly report if intelligence found."""
        empty_result = extractor.extract("Hello, how are you?")
        assert not empty_result.has_intelligence

        intel_result = extractor.extract("Pay to fake@ybl")
        assert intel_result.has_intelligence

    def test_has_intelligence_with_new_fields(self, extractor: IntelligenceExtractor):
        """Should report has_intelligence for new field types."""
        # Test beneficiary name alone
        result = extractor.extract("Account Holder: Rahul Kumar")
        assert result.has_intelligence

        # Test bank name alone
        result = extractor.extract("Transfer to SBI account")
        assert result.has_intelligence

        # Test IFSC alone
        result = extractor.extract("IFSC: SBIN0001234")
        assert result.has_intelligence

    def test_to_dict_format(self, extractor: IntelligenceExtractor):
        """Should convert to correct API format."""
        result = extractor.extract("UPI: test@ybl")
        data = result.to_dict()

        assert "bankAccounts" in data
        assert "upiIds" in data
        assert "phoneNumbers" in data
        assert "phishingLinks" in data
        assert "beneficiaryNames" in data
        assert "bankNames" in data
        assert "ifscCodes" in data
        assert "whatsappNumbers" in data
        assert "test@ybl" in data["upiIds"]

    def test_to_dict_includes_new_fields_data(self, extractor: IntelligenceExtractor):
        """Should include new field data in to_dict output."""
        text = """
        Account Holder: Rahul Kumar
        Bank: HDFC Bank
        IFSC Code: HDFC0001234
        WhatsApp: +91 9876543210
        """
        result = extractor.extract(text)
        data = result.to_dict()

        assert any("Rahul Kumar" in name for name in data["beneficiaryNames"])
        assert any("HDFC" in bank for bank in data["bankNames"])
        assert "HDFC0001234" in data["ifscCodes"]
        assert any("9876543210" in num for num in data["whatsappNumbers"])


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


class TestRealWorldConversation:
    """Tests using real scam conversation data."""

    @pytest.fixture
    def extractor(self) -> IntelligenceExtractor:
        """Create extractor instance."""
        return IntelligenceExtractor()

    def test_extracts_from_hdfc_kyc_scam_conversation(self, extractor: IntelligenceExtractor):
        """Should extract all intelligence from a real HDFC KYC scam conversation."""
        # Real conversation from testing (from improvements.txt)
        conversation = """
        ALERT: Dear Customer, your HDFC Bank account will be BLOCKED within 24 hours 
        due to pending KYC update. To avoid suspension, click the link immediately to 
        verify your PAN card: http://hdfc-netbanking-kyc-update.com/verify or reply 'HELP'.
        
        Ma'am, customer care lines are busy due to server maintenance. You do not have 
        time for calls!! Your account is getting blocked in 10 MINUTES. You must verify 
        online immediately. Click the link: http://hdfc-netbanking-kyc-update.com/verify 
        Open it now and enter your Customer ID and Password to stop the blocking.
        
        Okay ma'am, listen carefully. Since your internet is slow, you can do a manual 
        verification to stop the block. You need to send a small refundable token amount 
        of ₹10 to verify your account is active. Send immediately to our Official UPI ID: 
        hdfc.kyc.verification@okhdfcbank SEND SCREENSHOT once done. Hurry, only 5 minutes left!!
        
        Yes, ma'am, relax. That is the correct official ID. When you enter it, the name 
        will show as 'Rahul Kumar - KYC Support' or just 'Rahul Kumar'. That is our 
        verification officer. Please proceed!
        
        Stop panicking and listen! If UPI is failing, you must do an IMPS transfer 
        immediately. Note down these details carefully:
        Bank: SBI (State Bank of India)
        Account Holder: Rahul Kumar
        Account No: 30987654321
        IFSC Code: SBIN0001234
        Transfer ₹100 (minimum limit for IMPS) right now. Do not delay!!
        
        Madam, DO NOT WASTE TIME! SBI is the Central Nodal Agency for all HDFC KYC updates. 
        It is government approved. Yes, send the screenshot immediately to our Verification 
        Manager on WhatsApp. WhatsApp Number: +91 98765 43210 Add this number and send 
        the photo NOW. If you do not send it in 60 seconds, your account will be deleted 
        permanently!
        """

        result = extractor.extract(conversation)

        # Verify all intelligence types are extracted
        # Bank account
        assert "30987654321" in result.bank_accounts

        # UPI ID
        assert "hdfc.kyc.verification@okhdfcbank" in result.upi_ids

        # Phishing link
        assert any(
            "hdfc-netbanking-kyc-update.com" in url 
            for url in result.phishing_links
        )

        # Beneficiary name (Rahul Kumar)
        assert any("Rahul Kumar" in name for name in result.beneficiary_names)

        # Bank names (SBI and HDFC mentioned)
        assert any("SBI" in bank or "State Bank of India" in bank for bank in result.bank_names)
        assert any("HDFC" in bank for bank in result.bank_names)

        # IFSC code
        assert "SBIN0001234" in result.ifsc_codes

        # WhatsApp number
        assert any("9876543210" in num for num in result.whatsapp_numbers)

    def test_conversation_extraction_as_messages(self, extractor: IntelligenceExtractor):
        """Should extract from conversation passed as message list."""
        messages = [
            {"text": "Your HDFC Bank account will be BLOCKED. Click http://hdfc-kyc.tk/verify"},
            {"text": "Send ₹10 to UPI: hdfc.kyc@okhdfcbank"},
            {"text": "Name will show as 'Rahul Kumar'"},
            {"text": "Bank: SBI, Account: 30987654321, IFSC: SBIN0001234"},
            {"text": "Send screenshot to WhatsApp: +91 9876543210"},
        ]

        result = extractor.extract_from_conversation(messages)

        assert "30987654321" in result.bank_accounts
        assert "hdfc.kyc@okhdfcbank" in result.upi_ids
        assert any("Rahul Kumar" in name for name in result.beneficiary_names)
        assert "SBIN0001234" in result.ifsc_codes
        assert any("9876543210" in num for num in result.whatsapp_numbers)

    def test_deduplicates_across_conversation(self, extractor: IntelligenceExtractor):
        """Should deduplicate repeated intelligence in conversation."""
        messages = [
            {"text": "Send to WhatsApp: +91 9876543210"},
            {"text": "Reminder: WhatsApp number is +91 9876543210"},
            {"text": "Final: Send to +91 9876543210 on WhatsApp"},
        ]

        result = extractor.extract_from_conversation(messages)

        # Should only have one instance despite being mentioned 3 times
        whatsapp_count = sum(
            1 for num in result.whatsapp_numbers 
            if "9876543210" in num
        )
        assert whatsapp_count == 1
