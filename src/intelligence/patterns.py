"""Regex patterns and validators for intelligence extraction."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Pattern, Callable, Optional


class IntelligenceType(str, Enum):
    """Types of intelligence that can be extracted."""

    BANK_ACCOUNT = "bank_account"
    UPI_ID = "upi_id"
    PHONE_NUMBER = "phone_number"
    URL = "url"
    EMAIL = "email"
    BENEFICIARY_NAME = "beneficiary_name"
    BANK_NAME = "bank_name"
    IFSC_CODE = "ifsc_code"
    WHATSAPP_NUMBER = "whatsapp_number"


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
    validator: Optional[Callable] = None  # Optional validation function


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
    # +91 prefix with 10 digits
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
    # Formatted with spaces/hyphens (6-9 followed by formatted 9 digits)
    ExtractionPattern(
        pattern=re.compile(r"\b[6-9]\d{2}[-\s]?\d{3}[-\s]?\d{4}\b"),
        intel_type=IntelligenceType.PHONE_NUMBER,
        description="Formatted Indian mobile",
    ),
    # 12 digits starting with 91 (country code + 10 digit phone)
    # e.g., 919876543210, 91 + 9876543210
    ExtractionPattern(
        pattern=re.compile(r"\b91[6-9]\d{9}\b"),
        intel_type=IntelligenceType.PHONE_NUMBER,
        description="Indian phone with 91 country code prefix (12 digits)",
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

# IFSC Code Pattern
# Format: 4 letters (bank code) + 0 + 6 alphanumeric characters
# Example: SBIN0001234, HDFC0000001, ICIC0000123
IFSC_PATTERN = ExtractionPattern(
    pattern=re.compile(
        r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        re.IGNORECASE,
    ),
    intel_type=IntelligenceType.IFSC_CODE,
    description="IFSC Code (4 letters + 0 + 6 alphanumeric)",
)

# Bank Name Patterns
# Common Indian bank names and their variations
INDIAN_BANK_NAMES = [
    # Public Sector Banks
    "SBI", "State Bank of India", "State Bank",
    "PNB", "Punjab National Bank",
    "BOB", "Bank of Baroda", "Baroda Bank",
    "BOI", "Bank of India",
    "Canara Bank", "Canara",
    "Union Bank", "Union Bank of India",
    "Indian Bank",
    "Central Bank", "Central Bank of India",
    "UCO Bank", "UCO",
    "Bank of Maharashtra",
    "Punjab & Sind Bank", "PSB",
    "Indian Overseas Bank", "IOB",
    # Private Sector Banks
    "HDFC", "HDFC Bank",
    "ICICI", "ICICI Bank",
    "Axis Bank", "Axis",
    "Kotak", "Kotak Mahindra", "Kotak Mahindra Bank",
    "Yes Bank",
    "IndusInd", "IndusInd Bank",
    "IDBI", "IDBI Bank",
    "Federal Bank", "Federal",
    "RBL Bank", "RBL",
    "Bandhan Bank", "Bandhan",
    "IDFC First", "IDFC First Bank", "IDFC",
    "AU Small Finance Bank", "AU Bank",
    "Equitas", "Equitas Bank",
    "Ujjivan", "Ujjivan Bank",
    # Payment Banks
    "Paytm Payments Bank", "Paytm Bank",
    "Airtel Payments Bank", "Airtel Bank",
    "Jio Payments Bank", "Jio Bank",
    "Fino Payments Bank", "Fino Bank",
]

# Create regex pattern for bank names (case insensitive)
BANK_NAME_PATTERN = ExtractionPattern(
    pattern=re.compile(
        r"\b(?:" + "|".join(re.escape(name) for name in INDIAN_BANK_NAMES) + r")\b",
        re.IGNORECASE,
    ),
    intel_type=IntelligenceType.BANK_NAME,
    description="Indian bank name",
)

# Beneficiary/Account Holder Name Patterns
# Look for names associated with UPI or bank accounts
BENEFICIARY_NAME_PATTERNS = [
    # "name will show as 'Name'" or "name shows as Name"
    ExtractionPattern(
        pattern=re.compile(
            r"(?:name\s+(?:will\s+)?(?:show|display|appear)s?\s+(?:as)?[\s:]*['\"]?)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})(?=['\"]|\s*[-–]|$|\.|,)",
            re.IGNORECASE,
        ),
        intel_type=IntelligenceType.BENEFICIARY_NAME,
        description="Name shown in UPI/bank transfer",
    ),
    # "Account Holder: Name" or "A/C Holder Name: XYZ" - stop at newline or punctuation
    ExtractionPattern(
        pattern=re.compile(
            r"(?:account\s+holder|a/c\s+holder|beneficiary|payee)[\s:]+(?:name)?[\s:]*['\"]?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})(?=['\"]|\n|$|\.|,)",
            re.IGNORECASE,
        ),
        intel_type=IntelligenceType.BENEFICIARY_NAME,
        description="Account holder name",
    ),
    # "Transfer to Name" or "Send to Name"
    ExtractionPattern(
        pattern=re.compile(
            r"(?:transfer|send|pay)\s+(?:money\s+)?to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})(?:\s*[-–]|\s+(?:sir|madam|ji|sahab))",
            re.IGNORECASE,
        ),
        intel_type=IntelligenceType.BENEFICIARY_NAME,
        description="Transfer recipient name",
    ),
    # "Name - Title" pattern like "Rahul Kumar - KYC Support"
    ExtractionPattern(
        pattern=re.compile(
            r"['\"]([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\s*[-–]\s*(?:KYC|Support|Officer|Manager|Executive|Agent|Verification)",
            re.IGNORECASE,
        ),
        intel_type=IntelligenceType.BENEFICIARY_NAME,
        description="Name with title/role",
    ),
    # "or just 'Name'" pattern
    ExtractionPattern(
        pattern=re.compile(
            r"(?:or\s+)?just\s+['\"]([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})['\"]",
            re.IGNORECASE,
        ),
        intel_type=IntelligenceType.BENEFICIARY_NAME,
        description="Alternate name display",
    ),
]

# WhatsApp Number Patterns
# Phone numbers with WhatsApp context
WHATSAPP_PATTERNS = [
    # "WhatsApp: +91 98765 43210" or "WhatsApp Number: 9876543210"
    ExtractionPattern(
        pattern=re.compile(
            r"(?:whatsapp|wa|whats\s*app)[:\s]*(?:no\.?|number|num)?[:\s]*(?:\+91[-\s]*|91[-\s]+)?([6-9][-\s\d]{9,14})",
            re.IGNORECASE,
        ),
        intel_type=IntelligenceType.WHATSAPP_NUMBER,
        description="WhatsApp number",
    ),
    # "message/contact on WhatsApp +91..."
    ExtractionPattern(
        pattern=re.compile(
            r"(?:message|contact|call|reach)\s+(?:me\s+)?(?:on\s+)?whatsapp[:\s]*(?:\+91[-\s]*|91[-\s]+)?([6-9][-\s\d]{9,14})",
            re.IGNORECASE,
        ),
        intel_type=IntelligenceType.WHATSAPP_NUMBER,
        description="WhatsApp contact number",
    ),
    # "send to WhatsApp +91..."
    ExtractionPattern(
        pattern=re.compile(
            r"(?:send|share)\s+(?:it\s+|screenshot\s+)?(?:to\s+|on\s+)?(?:my\s+)?whatsapp[:\s]*(?:\+91[-\s]*|91[-\s]+)?([6-9][-\s\d]{9,14})",
            re.IGNORECASE,
        ),
        intel_type=IntelligenceType.WHATSAPP_NUMBER,
        description="WhatsApp for sharing",
    ),
    # WhatsApp link: wa.me/919876543210
    ExtractionPattern(
        pattern=re.compile(
            r"wa\.me/(?:\+?91)?([6-9]\d{9})",
            re.IGNORECASE,
        ),
        intel_type=IntelligenceType.WHATSAPP_NUMBER,
        description="WhatsApp link number",
    ),
]


def get_all_patterns() -> list[ExtractionPattern]:
    """Get all extraction patterns."""
    return (
        BANK_ACCOUNT_PATTERNS +
        [UPI_PATTERN, UPI_GENERIC_PATTERN] +
        PHONE_PATTERNS +
        [URL_PATTERN, EMAIL_PATTERN, IFSC_PATTERN, BANK_NAME_PATTERN] +
        BENEFICIARY_NAME_PATTERNS +
        WHATSAPP_PATTERNS
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
        },
        "beneficiary_names": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Names of account holders or UPI beneficiaries (e.g., 'Rahul Kumar')"
        },
        "bank_names": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Names of banks mentioned (e.g., 'SBI', 'HDFC Bank')"
        },
        "ifsc_codes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "IFSC codes (format: 4 letters + 0 + 6 alphanumeric, e.g., 'SBIN0001234')"
        },
        "whatsapp_numbers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "WhatsApp phone numbers mentioned for contact"
        }
    },
    "required": ["bank_accounts", "upi_ids", "phone_numbers", "urls", "emails", "beneficiary_names", "bank_names", "ifsc_codes", "whatsapp_numbers"]
}
