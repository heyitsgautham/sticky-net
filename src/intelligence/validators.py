"""Validators for AI-extracted intelligence data.

This module provides validation functions for intelligence extracted by the AI.
The AI handles extraction; these validators ensure the format is correct.
"""

import re
from enum import Enum
from typing import Any


class ExtractionSource(str, Enum):
    """Source of extraction."""

    REGEX = "regex"
    AI = "ai"
    MERGED = "merged"


# =============================================================================
# REGEX PATTERNS FOR VALIDATION
# =============================================================================

# Bank Account Pattern: 9-18 digits
BANK_ACCOUNT_PATTERN = re.compile(r"^\d{9,18}$")

# UPI ID Pattern: username@provider
UPI_PROVIDERS = [
    # Paytm
    "ptaxis", "ptyes", "ptsbi", "pthdfc", "paytm",
    # Google Pay
    "okhdfcbank", "okicici", "oksbi", "okaxis",
    # PhonePe
    "ybl", "ibl", "axl",
    # Slice
    "sliceaxis", "slicepay", "slc",
    # Kotak
    "kotak", "kotak811",
    # Cred
    "axisb", "yescred", "yescurie",
    # Amazon Pay
    "apl", "yapl", "rapl",
    # Fampay
    "fam", "yesfam",
    # IND Money
    "inhdfc",
    # Salary Se
    "seyes",
    # Mahamobile Plus
    "mahb",
    # BharatPe
    "bpunity",
    # WhatsApp Pay
    "waicici",
    # BHIM
    "upi",
    # Jupiter
    "jupiteraxis",
    # Bank of India
    "boi", "mboi",
    # Payzapp
    "pz",
    # Central Bank
    "centralbank",
    # Aditya Birla
    "abcdicici",
    # DLB
    "dlb",
    # Zomato
    "zoicici",
    # IndusInd
    "indus", "indie",
    # JKB
    "jkb",
    # Airtel
    "airtel",
    # PNB
    "pnb",
    # Jio
    "jio",
    # SBI
    "sbi",
    # Yes Bank
    "yespop", "yespay", "yes",
    # Bank of Baroda
    "barodampay",
    # Shriram
    "shriramhdfcbank",
    # Timepay
    "timecosmos",
    # Cheq
    "trans",
    # Citrus/PayU
    "payu",
    # ICICI
    "icici",
    # IOB
    "iob",
    # Jar
    "jarunity",
    # DBS
    "dbs",
    # KB Axis
    "kbaxis",
    # Equitas
    "equitas",
    # Kredit.Pe
    "kphdfc",
    # Navi
    "naviaxis",
    # Money View
    "mvhdfc",
    # OkCredit
    "axb",
    # Bajaj
    "abfspay",
    # Paulpay
    "paulpay",
    # OneCard
    "oneyes",
    # Fi
    "fifederal", "federal",
    # Canara
    "cnrb",
    # Fincare
    "fincarebank", "finobank",
    # Mobikwik
    "ikwik",
    # Rio Money
    "rmrbl",
    # Flipkart
    "fkaxis",
    # Samsung
    "pingpay",
    # FreeCharge
    "freecharge",
    # SIB
    "sib",
    # HSBC
    "hsbc",
    # SuperMoney
    "superyes",
    # Freo
    "freoicici",
    # IDBI Bank
    "idbi",
    # BHIM Axis Pay
    "axisbank",
    # BHIM Bandhan
    "bandhan",
    # BHIM KBL UPI
    "kbl",
    # BHIM UCO UPI
    "uco",
    # Citi Mobile
    "citi", "citigold",
    # Groww Pay
    "yesg",
    # Indian Bank (IndOASIS)
    "indianbank", "allbank",
    # Union Bank of India
    "unionbankofindia", "uboi", "unionbank",
    # TataNeu
    "tapicici",
    # Genwise
    "gwaxis",
    # TwidPay
    "yestp",
    # Niyo
    "niyoicici",
    # HDFC
    "hdfc",
    # AU Bank
    "aubank",
]

UPI_ID_PATTERN = re.compile(
    rf"^[\w.-]+@(?:{'|'.join(UPI_PROVIDERS)})$",
    re.IGNORECASE,
)

# Generic UPI pattern for loose validation
UPI_GENERIC_PATTERN = re.compile(r"^[\w.-]+@[a-zA-Z]{2,15}$")

# Phone Number Pattern: Indian mobile (10 digits starting with 6-9)
PHONE_PATTERN = re.compile(r"^[6-9]\d{9}$")

# Phone with country code pattern
PHONE_WITH_COUNTRY_CODE_PATTERN = re.compile(r"^(?:\+?91)?[6-9]\d{9}$")

# IFSC Code Pattern: 4 letters + 0 + 6 alphanumeric
IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$", re.IGNORECASE)

# Email Pattern
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$")

# URL Pattern - more flexible to catch various link formats
URL_PATTERN = re.compile(
    r"^https?://[^\s<>\"'{}|\\^`\[\]]+$",
    re.IGNORECASE,
)

# Pattern for URLs without http/https prefix - VERY flexible to catch phishing links
# Examples: sbi-bank.pay.in/xY7834, bit.ly/xyz, hdfc-secure.co.in/verify
URL_WITHOUT_PROTOCOL_PATTERN = re.compile(
    r"^[a-zA-Z0-9][a-zA-Z0-9\-\.]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s]*)?$",
    re.IGNORECASE,
)

# Even more flexible pattern for catching suspicious-looking links with bank/brand names
SUSPICIOUS_LINK_PATTERN = re.compile(
    r"[a-zA-Z0-9][a-zA-Z0-9\-\.]*(?:bank|pay|secure|verify|login|upi|kyc|account|update)[a-zA-Z0-9\-\.]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s]*)?",
    re.IGNORECASE,
)

# Suspicious URL indicators for phishing detection
SUSPICIOUS_URL_INDICATORS = [
    # URL shorteners (very common in scams)
    "bit.ly", "tinyurl", "t.co", "goo.gl", "is.gd", "cutt.ly", "rebrand.ly",
    "ow.ly", "buff.ly", "adf.ly", "bc.vc", "j.mp", "v.gd", "x.co",
    "shorturl", "short.io", "rb.gy", "clck.ru", "tinu.be", "tiny.cc",
    "s.id", "shrtco.de", "1link.in", "linktr.ee", "lnk.to",
    # Phishing keywords
    "login", "verify", "update", "secure", "account", "signin", "password",
    "confirm", "authenticate", "validation", "unlock", "suspend", "blocked",
    "expired", "reactivate", "restore", "recover", "reset", "renew",
    # KYC/OTP scam keywords
    "kyc", "otp", "bank", "sbi", "hdfc", "icici", "axis", "kotak", "pnb",
    "aadhaar", "aadhar", "pan-", "pancard", "e-kyc", "ekyc",
    # Fake payment/UPI domains
    ".pay.", "pay.in", "-pay", "pay-", "upi-", "-upi", "payment",
    "bhim", "rupay", "npci", "imps", "neft", "rtgs",
    # Brand impersonation (common in Indian scams)
    "amazon", "flipkart", "paytm", "phonepe", "gpay", "google-pay",
    "kbc", "jio", "airtel", "vodafone", "bsnl", "netflix", "hotstar",
    "swiggy", "zomato", "ola", "uber", "myntra", "ajio",
    # Prize/lottery/refund scam keywords
    "prize", "claim", "refund", "reward", "winner", "lucky", "lottery",
    "cashback", "bonus", "offer", "gift", "free", "win", "congratulation",
    # Job scam keywords
    "jobs", "hiring", "vacancy", "career", "recruitment", "salary", "earning",
    "work-from-home", "part-time", "income", "money-making",
    # Free/suspicious TLDs often used in phishing
    ".tk", ".ml", ".ga", ".cf", ".gq",  # Free domains
    ".xyz", ".work", ".top", ".site", ".online", ".club", ".icu", ".buzz",
    ".co.in",  # Often abused for Indian phishing
    ".info", ".biz", ".ws", ".cc", ".pw", ".space", ".life", ".live",
    ".click", ".link", ".download", ".stream", ".in/",
    ".store", ".shop", ".app", ".me", ".vip", ".pro",
    # Messaging links
    "telegram", "wa.me", "whatsapp", "t.me", "chat.whatsapp",
    # Form/survey scams
    "forms.gle", "docs.google", "survey", "form", "fill",
    # Suspicious subdomains/paths
    "-secure", "-verify", "-login", "-update", "-bank",
    "secure-", "verify-", "login-", "update-", "bank-",
    # Indian bank name impersonation
    "sbi-", "-sbi", "hdfc-", "-hdfc", "icici-", "-icici",
    "axis-", "-axis", "kotak-", "-kotak", "pnb-", "-pnb",
    "bob-", "-bob", "canara-", "-canara", "union-", "-union",
    "idbi-", "-idbi", "yes-", "-yes", "rbi-", "-rbi",
    # Random alphanumeric paths (common in phishing)
    "/xY", "/aB", "/Xy", "/Ab", "/kY", "/mN", "/pQ", "/rS",
]

# Indian Bank Names
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

# Blocklist of common false positive words for beneficiary name extraction
BENEFICIARY_NAME_BLOCKLIST = {
    # Action words commonly mistaken for names
    "now", "before", "paying", "name", "sir", "madam", "ji",
    "please", "urgent", "click", "here", "send", "pay", "fast",
    # Financial/banking terms
    "verification", "account", "bank", "upi", "payment", "money",
    "transfer", "today", "immediately", "urgent", "asap", "quick",
    "verify", "update", "link", "otp", "pin", "password", "amount",
    "rupees", "rs", "inr", "credited", "debited", "pending", "failed",
    "success", "transaction", "beneficiary", "receiver", "sender",
    # Common false positive phrases
    "the", "and", "for", "with", "from", "holder", "number",
    "dear", "customer", "user", "member", "client", "support",
    "help", "desk", "center", "service", "team", "officer",
    # Title/honorific words
    "mr", "mrs", "ms", "dr", "shri", "smt", "sahab",
    # Common verbs/actions
    "call", "contact", "message", "reply", "confirm", "complete",
    "submit", "enter", "provide", "share", "receive", "collect",
}


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_phone_number(phone: str) -> bool:
    """
    Validate an Indian phone number.

    Args:
        phone: Phone number string (may include +91 prefix)

    Returns:
        True if valid Indian mobile number, False otherwise
    """
    if not phone:
        return False

    # Clean the number: remove spaces, hyphens, and leading +
    clean = re.sub(r"[-\s+]", "", phone)

    # Remove country code prefix if present
    if clean.startswith("91") and len(clean) in (11, 12):
        clean = clean[2:]

    # Must be exactly 10 digits starting with 6-9
    return bool(PHONE_PATTERN.match(clean))


def validate_upi_id(upi_id: str) -> bool:
    """
    Validate a UPI ID.

    Args:
        upi_id: UPI ID string (format: username@provider)

    Returns:
        True if valid UPI ID format, False otherwise
    """
    if not upi_id or "@" not in upi_id:
        return False

    clean = upi_id.strip().lower()

    # Check against known providers first (strict)
    if UPI_ID_PATTERN.match(clean):
        return True

    # Fall back to generic pattern (loose)
    return bool(UPI_GENERIC_PATTERN.match(clean))


def validate_bank_account(account: str) -> bool:
    """
    Validate a bank account number.

    Args:
        account: Bank account number string

    Returns:
        True if valid bank account (9-18 digits), False otherwise
    """
    if not account:
        return False

    # Extract only digits
    digits = re.sub(r"\D", "", account)

    # Must be 9-18 digits
    if len(digits) < 9 or len(digits) > 18:
        return False

    # Exclude obviously fake patterns
    if len(set(digits)) == 1:  # All same digit
        return False

    # Exclude phone-like patterns
    if _looks_like_phone(digits):
        return False

    return True


def validate_ifsc(ifsc: str) -> bool:
    """
    Validate an IFSC code.

    Args:
        ifsc: IFSC code string (format: 4 letters + 0 + 6 alphanumeric)

    Returns:
        True if valid IFSC code format, False otherwise
    """
    if not ifsc or len(ifsc) != 11:
        return False

    return bool(IFSC_PATTERN.match(ifsc.upper()))


def validate_url(url: str) -> bool:
    """
    Validate a URL and check if it's suspicious (potential phishing).

    Args:
        url: URL string

    Returns:
        True if URL is valid AND suspicious, False otherwise
    """
    if not url:
        return False

    # Clean trailing punctuation
    clean_url = url.rstrip(".,;:!?)")
    
    # Check if it's a valid URL with protocol
    has_protocol = URL_PATTERN.match(clean_url)
    
    # Check if it's a valid URL without protocol (like bit.ly/xyz, sbi-bank.pay.in/xY7834)
    has_no_protocol = URL_WITHOUT_PROTOCOL_PATTERN.match(clean_url)
    
    # Check if it matches suspicious link pattern (bank/pay/verify in domain)
    has_suspicious_pattern = SUSPICIOUS_LINK_PATTERN.search(clean_url)
    
    if not has_protocol and not has_no_protocol and not has_suspicious_pattern:
        return False

    # Check for suspicious indicators
    return is_suspicious_url(clean_url)


def validate_email(email: str) -> bool:
    """
    Validate an email address.

    Args:
        email: Email address string

    Returns:
        True if valid email format, False otherwise
    """
    if not email or "@" not in email or "." not in email:
        return False

    clean = email.strip().lower()

    # Check against UPI providers to avoid false positives
    domain = clean.split("@")[-1].split(".")[0]
    if domain in UPI_PROVIDERS:
        return False

    return bool(EMAIL_PATTERN.match(clean))


def is_suspicious_url(url: str) -> bool:
    """
    Check if a URL contains suspicious indicators (potential phishing).

    Args:
        url: URL string to check

    Returns:
        True if URL contains suspicious indicators, False otherwise
    """
    url_lower = url.lower()
    return any(indicator in url_lower for indicator in SUSPICIOUS_URL_INDICATORS)


def validate_beneficiary_name(name: str) -> bool:
    """
    Validate a beneficiary/account holder name, filtering false positives.

    Args:
        name: Name string

    Returns:
        True if valid name, False otherwise
    """
    if not name or len(name) < 3:
        return False

    clean_name = name.strip()

    # Should have reasonable length (3-50 characters)
    if len(clean_name) > 50:
        return False

    # Must be mostly alphabetic (allow spaces and common name punctuation)
    alpha_only = clean_name.replace(" ", "").replace(".", "").replace("'", "").replace("-", "")
    if not alpha_only.isalpha():
        return False

    # Should contain only letters, spaces, and common name characters
    if not re.match(r"^[A-Za-z][A-Za-z\s.''-]+$", clean_name):
        return False

    # Reject if any word is in the blocklist
    words = clean_name.lower().split()
    if any(word in BENEFICIARY_NAME_BLOCKLIST for word in words):
        return False

    # Reject single-word names that are too short (likely false positives)
    if len(words) == 1 and len(clean_name) < 4:
        return False

    return True


# =============================================================================
# EXTRACTION RESULT VALIDATION
# =============================================================================

def validate_extraction_result(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and filter AI-extracted intelligence through validators.

    This is the hybrid approach: AI extracts (flexible), validators filter (reliable).

    Args:
        data: Dictionary with AI-extracted intelligence fields

    Returns:
        Dictionary with validated and cleaned intelligence
    """
    validated = {
        "bank_accounts": [],
        "upi_ids": [],
        "phone_numbers": [],
        "urls": [],
        "emails": [],
        "beneficiary_names": [],
        "bank_names": [],
        "ifsc_codes": [],
        "whatsapp_numbers": [],
        "other_critical_info": [],
    }

    # Validate bank accounts
    for acc in data.get("bank_accounts", []) or []:
        if validate_bank_account(str(acc)):
            clean = re.sub(r"\D", "", str(acc))
            validated["bank_accounts"].append(clean)

    # Validate UPI IDs
    for upi in data.get("upi_ids", []) or []:
        if validate_upi_id(str(upi)):
            validated["upi_ids"].append(str(upi).lower())

    # Validate phone numbers
    for phone in data.get("phone_numbers", []) or []:
        if validate_phone_number(str(phone)):
            clean = _clean_phone_number(str(phone))
            validated["phone_numbers"].append(clean)

    # Validate URLs (only keep suspicious ones)
    for url in data.get("urls", []) or []:
        if validate_url(str(url)):
            validated["urls"].append(str(url).rstrip(".,;:!?)"))

    # Validate emails
    for email in data.get("emails", []) or []:
        if validate_email(str(email)):
            validated["emails"].append(str(email).lower())

    # Validate beneficiary names
    for name in data.get("beneficiary_names", []) or []:
        if validate_beneficiary_name(str(name)):
            validated["beneficiary_names"].append(str(name).strip().title())

    # Bank names - keep as-is if not empty (AI is better at context)
    for bank in data.get("bank_names", []) or []:
        clean_bank = str(bank).strip()
        if clean_bank:
            validated["bank_names"].append(clean_bank)

    # Validate IFSC codes
    for ifsc in data.get("ifsc_codes", []) or []:
        if validate_ifsc(str(ifsc)):
            validated["ifsc_codes"].append(str(ifsc).upper())

    # Validate WhatsApp numbers (same as phone)
    for wa in data.get("whatsapp_numbers", []) or []:
        if validate_phone_number(str(wa)):
            clean = _clean_phone_number(str(wa))
            validated["whatsapp_numbers"].append(clean)

    # Keep other_critical_info as-is (AI is better at catching these)
    validated["other_critical_info"] = data.get("other_critical_info", []) or []

    return validated


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _looks_like_phone(number: str) -> bool:
    """
    Check if a number looks like a phone number.

    Phone patterns:
    - 10 digits starting with 6, 7, 8, or 9
    - 12 digits starting with 91 followed by 6, 7, 8, or 9
    - 11 digits starting with 91 (less common but possible)
    """
    if not number.isdigit():
        return False

    # 10 digits starting with 6-9 = phone
    if len(number) == 10 and number[0] in "6789":
        return True

    # 12 digits: 91 + 10 digits starting with 6-9 = phone with country code
    if len(number) == 12 and number.startswith("91") and number[2] in "6789":
        return True

    # 11 digits: 91 + 9 digits (less common)
    if len(number) == 11 and number.startswith("91") and number[2] in "6789":
        return True

    return False


def _clean_phone_number(phone: str) -> str:
    """
    Clean and normalize a phone number to 10 digits.

    Args:
        phone: Phone number string

    Returns:
        Cleaned 10-digit phone number
    """
    # Remove all non-digits
    clean = re.sub(r"\D", "", phone)

    # Remove country code prefix if present
    if clean.startswith("91") and len(clean) in (11, 12):
        clean = clean[2:]

    return clean


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
    "required": [
        "bank_accounts", "upi_ids", "phone_numbers", "urls", "emails",
        "beneficiary_names", "bank_names", "ifsc_codes", "whatsapp_numbers"
    ]
}
