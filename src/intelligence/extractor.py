"""AI-first intelligence extraction with regex validation.

The AI (LLM) is the PRIMARY extractor - it understands semantic context
(e.g., "Your account" = victim's, "Transfer to" = scammer's).

Regex is ONLY used for FORMAT VALIDATION of AI-extracted data.
Suspicious keyword extraction is done entirely by AI (not regex) because:
- Scammers use misspellings, variations, and novel phrasing
- Context matters (AI understands semantic urgency)
- We're already calling the LLM, so no extra cost
"""

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.api.schemas import ExtractedIntelligence, OtherIntelItem
from src.intelligence.validators import (
    ExtractionSource,
    UPI_PROVIDERS,
    validate_beneficiary_name,
)

logger = structlog.get_logger()


@dataclass
class ExtractionResult:
    """Extraction result (kept for backward compatibility)."""

    bank_accounts: list[str] = field(default_factory=list)
    upi_ids: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    phishing_links: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    beneficiary_names: list[str] = field(default_factory=list)
    bank_names: list[str] = field(default_factory=list)
    ifsc_codes: list[str] = field(default_factory=list)
    whatsapp_numbers: list[str] = field(default_factory=list)
    suspicious_keywords: list[str] = field(default_factory=list)
    source: ExtractionSource = ExtractionSource.AI

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
            self.whatsapp_numbers or
            self.suspicious_keywords
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
            "suspiciousKeywords": self.suspicious_keywords,
        }


class IntelligenceExtractor:
    """
    AI-first intelligence extractor with regex validation.

    Architecture:
    - AI (LLM) extracts intelligence with semantic understanding
    - AI distinguishes victim's details from scammer's details
    - Regex only VALIDATES format (not extraction)
    
    This approach solves the problem of victim vs scammer details:
    - AI understands "Your account 123" = victim's (don't extract)
    - AI understands "Transfer to 456" = scammer's (extract)
    - Regex can't understand this context, only formats
    """

    def __init__(self) -> None:
        """Initialize extractor."""
        self.logger = logger.bind(component="IntelligenceExtractor")

    # =========================================================================
    # MAIN API: Validate AI Extraction
    # =========================================================================

    def validate_ai_extraction(
        self,
        ai_extracted: dict[str, Any] | None,
    ) -> ExtractedIntelligence:
        """
        Validate and clean AI-extracted intelligence.

        This is the PRIMARY extraction method. The AI extracts with semantic
        understanding, and we only validate the FORMAT here.

        Args:
            ai_extracted: Dict from AI structured output with intelligence fields

        Returns:
            Validated ExtractedIntelligence
        """
        if not ai_extracted:
            return ExtractedIntelligence()

        # Parse and validate each field
        validated_accounts = []
        for acc in ai_extracted.get("bank_accounts", []):
            clean = self._clean_number(str(acc))
            if self._validate_bank_account(clean):
                validated_accounts.append(clean)

        validated_upi = []
        for upi in ai_extracted.get("upi_ids", []):
            upi_str = str(upi).strip().lower()
            if self._validate_upi_id(upi_str):
                validated_upi.append(upi_str)

        validated_phones = []
        for phone in ai_extracted.get("phone_numbers", []):
            clean = self._clean_number(str(phone))
            if self._validate_phone(clean):
                validated_phones.append(clean)

        validated_ifsc = []
        for ifsc in ai_extracted.get("ifsc_codes", []):
            ifsc_str = str(ifsc).strip().upper()
            if self._validate_ifsc(ifsc_str):
                validated_ifsc.append(ifsc_str)

        # These don't need strict validation - AI understands context better
        validated_urls = [str(url).strip() for url in ai_extracted.get("urls", []) if url]
        validated_emails = [str(email).strip().lower() for email in ai_extracted.get("emails", ai_extracted.get("emailAddresses", [])) if "@" in str(email)]
        validated_names = [str(name).strip() for name in ai_extracted.get("beneficiary_names", []) if self._validate_name(str(name))]
        validated_banks = [str(bank).strip() for bank in ai_extracted.get("bank_names", []) if bank]
        validated_whatsapp = []
        for wa in ai_extracted.get("whatsapp_numbers", []):
            clean = self._clean_number(str(wa))
            if self._validate_phone(clean):
                validated_whatsapp.append(clean)

        # Parse other_critical_info
        other_info = []
        for item in ai_extracted.get("other_critical_info", []):
            if isinstance(item, dict) and item.get("label") and item.get("value"):
                other_info.append(OtherIntelItem(
                    label=str(item["label"]),
                    value=str(item["value"]),
                ))

        # Extract suspicious keywords from AI extraction (if provided) or empty list
        suspicious_keywords = [str(kw).strip().lower() for kw in ai_extracted.get("suspicious_keywords", []) if kw]

        result = ExtractedIntelligence(
            bankAccounts=validated_accounts,
            upiIds=validated_upi,
            phoneNumbers=validated_phones,
            phishingLinks=validated_urls,
            emailAddresses=validated_emails,
            beneficiaryNames=validated_names,
            bankNames=validated_banks,
            ifscCodes=validated_ifsc,
            whatsappNumbers=validated_whatsapp,
            suspiciousKeywords=suspicious_keywords,
            other_critical_info=other_info,
        )

        self.logger.info(
            "AI extraction validated",
            bank_accounts=len(result.bankAccounts),
            upi_ids=len(result.upiIds),
            phone_numbers=len(result.phoneNumbers),
            urls=len(result.phishingLinks),
            beneficiary_names=len(result.beneficiaryNames),
            ifsc_codes=len(result.ifscCodes),
            whatsapp_numbers=len(result.whatsappNumbers),
            suspicious_keywords=len(result.suspiciousKeywords),
            other_info=len(result.other_critical_info),
        )

        return result

    # =========================================================================
    # BACKWARD COMPATIBILITY: These methods are kept for existing code
    # =========================================================================

    def extract(self, text: str) -> ExtractionResult:
        """
        Regex extraction as BACKUP to AI extraction.
        
        Scans text for phone numbers, bank accounts, UPI IDs, URLs, and emails
        using regex patterns. Results are merged with AI extraction to ensure
        no fakeData is missed.
        """
        self.logger.debug("Running regex backup extraction")
        
        phones = []
        for match in re.finditer(r'(?:\+?91[\s-]?)?([6-9]\d{9})\b', text):
            clean = self._clean_number(match.group(0))
            if self._validate_phone(clean):
                phones.append(clean)
        
        # Bank accounts: 9-18 digit numbers (exclude phone-like)
        accounts = []
        for match in re.finditer(r'\b(\d{9,18})\b', text):
            num = match.group(1)
            if self._validate_bank_account(num) and not self._looks_like_phone(num):
                accounts.append(num)
        
        # UPI IDs: word@provider  
        upi_ids = []
        for match in re.finditer(r'([\w.-]+@[a-zA-Z][a-zA-Z0-9]*)', text):
            upi_candidate = match.group(1).lower()
            # Exclude emails (which have dots in domain)
            if '.' not in upi_candidate.split('@')[1]:
                if self._validate_upi_id(upi_candidate):
                    upi_ids.append(upi_candidate)
        
        # Phishing links: http/https URLs
        urls = re.findall(r'https?://[^\s<>"\')]+', text)
        
        # Email addresses: user@domain.tld
        emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', text)
        
        return ExtractionResult(
            bank_accounts=accounts,
            upi_ids=upi_ids,
            phone_numbers=phones,
            phishing_links=urls,
            emails=emails,
            source=ExtractionSource.REGEX,
        )

    def extract_from_conversation(
        self,
        messages: list[dict[str, Any]],
    ) -> ExtractionResult:
        """
        Extract intelligence from all scammer messages in conversation history.
        
        Scans only scammer messages to avoid extracting victim's own data.
        """
        combined = ExtractionResult(source=ExtractionSource.REGEX)
        
        for msg in messages:
            sender = msg.get("sender", "")
            text = msg.get("text", "")
            if sender == "scammer" and text:
                result = self.extract(text)
                combined.bank_accounts.extend(result.bank_accounts)
                combined.upi_ids.extend(result.upi_ids)
                combined.phone_numbers.extend(result.phone_numbers)
                combined.phishing_links.extend(result.phishing_links)
                combined.emails.extend(result.emails)
        
        # Deduplicate
        combined.bank_accounts = list(set(combined.bank_accounts))
        combined.upi_ids = list(set(combined.upi_ids))
        combined.phone_numbers = list(set(combined.phone_numbers))
        combined.phishing_links = list(set(combined.phishing_links))
        combined.emails = list(set(combined.emails))
        
        return combined

    def parse_ai_extraction(
        self,
        ai_extracted: dict[str, Any] | None,
    ) -> ExtractionResult:
        """
        Parse AI-extracted intelligence into ExtractionResult format.
        
        This is a wrapper for backward compatibility.
        """
        validated = self.validate_ai_extraction(ai_extracted)
        return ExtractionResult(
            bank_accounts=validated.bankAccounts,
            upi_ids=validated.upiIds,
            phone_numbers=validated.phoneNumbers,
            phishing_links=validated.phishingLinks,
            emails=validated.emailAddresses,
            beneficiary_names=validated.beneficiaryNames,
            bank_names=validated.bankNames,
            ifsc_codes=validated.ifscCodes,
            whatsapp_numbers=validated.whatsappNumbers,
            suspicious_keywords=validated.suspiciousKeywords,
            source=ExtractionSource.AI,
        )

    def merge_extractions(
        self,
        regex_result: ExtractionResult,
        ai_result: ExtractionResult,
    ) -> ExtractionResult:
        """
        Merge regex and AI results, taking union of both.
        
        Returns ai_result with any additional items from regex_result added.
        """
        merged = ExtractionResult(
            bank_accounts=list(set(ai_result.bank_accounts + regex_result.bank_accounts)),
            upi_ids=list(set(ai_result.upi_ids + regex_result.upi_ids)),
            phone_numbers=list(set(ai_result.phone_numbers + regex_result.phone_numbers)),
            phishing_links=list(set(ai_result.phishing_links + regex_result.phishing_links)),
            emails=list(set(ai_result.emails + regex_result.emails)),  # ExtractionResult uses 'emails'
            beneficiary_names=ai_result.beneficiary_names,
            bank_names=ai_result.bank_names,
            ifsc_codes=ai_result.ifsc_codes,
            whatsapp_numbers=ai_result.whatsapp_numbers,
            suspicious_keywords=ai_result.suspicious_keywords,
            source=ExtractionSource.AI,
        )
        return merged

    def merge_intelligence(
        self,
        regex_intel: ExtractionResult,
        llm_intel: ExtractedIntelligence | None,
    ) -> ExtractedIntelligence:
        """
        Returns validated LLM intelligence only (regex extraction disabled).
        
        Args:
            regex_intel: Ignored (regex extraction is disabled)
            llm_intel: LLM extraction to validate and return

        Returns:
            Validated ExtractedIntelligence from LLM
        """
        if llm_intel is None:
            return ExtractedIntelligence()

        # Validate and return LLM extraction only
        return self.validate_llm_extraction(llm_intel)

    def validate_llm_extraction(self, llm_intel: ExtractedIntelligence) -> ExtractedIntelligence:
        """
        Validate LLM-extracted intelligence using format checks.

        Args:
            llm_intel: Raw LLM extraction

        Returns:
            Validated ExtractedIntelligence
        """
        validated = ExtractedIntelligence(
            bankAccounts=[acc for acc in llm_intel.bankAccounts if self._validate_bank_account(self._clean_number(acc))],
            upiIds=[upi for upi in llm_intel.upiIds if self._validate_upi_id(upi)],
            phoneNumbers=[p for p in llm_intel.phoneNumbers if self._validate_phone(self._clean_number(p))],
            phishingLinks=llm_intel.phishingLinks,  # Keep as-is (AI understands context)
            emailAddresses=llm_intel.emailAddresses,  # Keep as-is
            beneficiaryNames=[n for n in llm_intel.beneficiaryNames if self._validate_name(n)],
            bankNames=llm_intel.bankNames,  # Keep as-is
            ifscCodes=[c for c in llm_intel.ifscCodes if self._validate_ifsc(c.upper())],
            whatsappNumbers=[w for w in llm_intel.whatsappNumbers if self._validate_phone(self._clean_number(w))],
            suspiciousKeywords=llm_intel.suspiciousKeywords,  # Keep as-is
            other_critical_info=llm_intel.other_critical_info,  # Keep as-is
        )

        self.logger.info(
            "LLM extraction validated",
            bank_accounts_in=len(llm_intel.bankAccounts),
            bank_accounts_out=len(validated.bankAccounts),
            upi_ids_in=len(llm_intel.upiIds),
            upi_ids_out=len(validated.upiIds),
            phone_numbers_in=len(llm_intel.phoneNumbers),
            phone_numbers_out=len(validated.phoneNumbers),
            ifsc_codes_in=len(llm_intel.ifscCodes),
            ifsc_codes_out=len(validated.ifscCodes),
            suspicious_keywords=len(validated.suspiciousKeywords),
        )

        return validated

    # =========================================================================
    # FORMAT VALIDATORS (Regex used ONLY for validation, not extraction)
    # =========================================================================

    def _clean_number(self, number: str) -> str:
        """Remove formatting from numbers (spaces, hyphens, parentheses, dots)."""
        return re.sub(r"[-\s().+]", "", number)

    def _validate_bank_account(self, account: str) -> bool:
        """
        Validate bank account number format.
        
        Rules:
        - Must be 9-18 digits
        - Must not be all same digit (e.g., 000000000)
        - Must not look like a phone number
        """
        if not account.isdigit():
            return False
        if len(account) < 9 or len(account) > 18:
            return False
        # Exclude all-same-digit numbers
        if len(set(account)) == 1:
            return False
        # Exclude phone-like patterns
        if self._looks_like_phone(account):
            return False
        return True

    def _validate_upi_id(self, upi: str) -> bool:
        """
        Validate UPI ID format.
        
        Rules:
        - Must contain @
        - Must match user@provider pattern
        - Prefer known providers but accept others
        """
        if "@" not in upi:
            return False
        return bool(re.match(r'^[\w.-]+@[a-zA-Z][a-zA-Z0-9]*$', upi))

    def _validate_phone(self, phone: str) -> bool:
        """
        Validate Indian phone number format.
        
        Rules:
        - 10 digits starting with 6-9
        - Or 12 digits starting with 91 followed by 6-9
        """
        if not phone.isdigit():
            return False
        
        # 10 digits starting with 6-9
        if len(phone) == 10 and phone[0] in "6789":
            return True
        
        # 12 digits: 91 + 10 digits starting with 6-9
        if len(phone) == 12 and phone.startswith("91") and phone[2] in "6789":
            return True
        
        # 11 digits: 91 + 9 digits (truncated, still accept)
        if len(phone) == 11 and phone.startswith("91") and phone[2] in "6789":
            return True

        return False

    def _validate_ifsc(self, ifsc: str) -> bool:
        """
        Validate IFSC code format.
        
        Rules:
        - 11 characters: 4 letters + 0 + 6 alphanumeric
        """
        if not ifsc or len(ifsc) != 11:
            return False
        if not ifsc[:4].isalpha():
            return False
        if ifsc[4] != '0':
            return False
        if not ifsc[5:].isalnum():
            return False
        return True

    def _validate_name(self, name: str) -> bool:
        """Validate beneficiary name."""
        return validate_beneficiary_name(name)

    def _looks_like_phone(self, number: str) -> bool:
        """
        Check if a number looks like a phone number.
        
        Used to exclude phone numbers from bank account extraction.
        """
        if not number.isdigit():
            return False
        
        # 10 digits starting with 6-9 = phone
        if len(number) == 10 and number[0] in "6789":
            return True
        
        # 12 digits: 91 + 10 digits starting with 6-9 = phone
        if len(number) == 12 and number.startswith("91") and number[2] in "6789":
            return True
        
        return False


# Singleton instance
_extractor_instance: IntelligenceExtractor | None = None


def get_extractor() -> IntelligenceExtractor:
    """Get or create extractor instance."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = IntelligenceExtractor()
    return _extractor_instance
