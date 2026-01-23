"""Scam detection patterns and indicators for regex pre-filter."""

from dataclasses import dataclass
from enum import Enum
import re
from typing import Pattern as RePattern


class ScamCategory(str, Enum):
    """Categories of scam tactics."""

    URGENCY = "urgency"
    AUTHORITY = "authority"
    THREAT = "threat"
    REQUEST = "request"
    FINANCIAL = "financial"
    PHISHING = "phishing"


class PreFilterResult(str, Enum):
    """Result of regex pre-filter classification."""

    OBVIOUS_SCAM = "obvious_scam"  # Skip AI, engage immediately
    OBVIOUS_SAFE = "obvious_safe"  # Skip AI, return neutral
    UNCERTAIN = "uncertain"  # Needs AI classification


@dataclass
class Pattern:
    """A scam indicator pattern."""

    category: ScamCategory
    pattern: RePattern[str]
    weight: float  # 0.0 to 1.0 importance
    description: str


@dataclass
class PatternMatch:
    """A matched pattern result."""

    category: ScamCategory
    matched_text: str
    weight: float
    description: str


# ============================================================
# URGENCY PATTERNS - Create immediate pressure
# ============================================================
URGENCY_PATTERNS = [
    Pattern(
        category=ScamCategory.URGENCY,
        pattern=re.compile(r"\b(immediate(?:ly)?|urgent(?:ly)?|asap|right\s+now)\b", re.I),
        weight=0.7,
        description="Immediate action language",
    ),
    Pattern(
        category=ScamCategory.URGENCY,
        pattern=re.compile(r"\b(today|within\s+\d+\s+(?:hour|minute|day)s?)\b", re.I),
        weight=0.6,
        description="Time pressure",
    ),
    Pattern(
        category=ScamCategory.URGENCY,
        pattern=re.compile(r"\b(hurry|quick(?:ly)?|fast|don'?t\s+delay)\b", re.I),
        weight=0.5,
        description="Speed pressure",
    ),
    Pattern(
        category=ScamCategory.URGENCY,
        pattern=re.compile(
            r"\b(last\s+chance|final\s+warning|expires?\s+(?:today|soon))\b", re.I
        ),
        weight=0.8,
        description="Deadline pressure",
    ),
]

# ============================================================
# AUTHORITY PATTERNS - Impersonate trusted entities
# ============================================================
AUTHORITY_PATTERNS = [
    Pattern(
        category=ScamCategory.AUTHORITY,
        pattern=re.compile(
            r"\b(RBI|Reserve\s+Bank|SBI|HDFC|ICICI|Axis|bank\s+of\s+india)\b", re.I
        ),
        weight=0.8,
        description="Bank impersonation",
    ),
    Pattern(
        category=ScamCategory.AUTHORITY,
        pattern=re.compile(
            r"\b(government|ministry|police|cyber\s*cell|income\s*tax|IT\s+department)\b",
            re.I,
        ),
        weight=0.9,
        description="Government impersonation",
    ),
    Pattern(
        category=ScamCategory.AUTHORITY,
        pattern=re.compile(r"\b(official|authorized|verified|genuine)\b", re.I),
        weight=0.4,
        description="Authority claim",
    ),
    Pattern(
        category=ScamCategory.AUTHORITY,
        pattern=re.compile(
            r"\b(customer\s+(?:care|support|service)|helpline|helpdesk)\b", re.I
        ),
        weight=0.5,
        description="Support impersonation",
    ),
]

# ============================================================
# THREAT PATTERNS - Create fear
# ============================================================
THREAT_PATTERNS = [
    Pattern(
        category=ScamCategory.THREAT,
        pattern=re.compile(
            r"\b(block(?:ed)?|suspend(?:ed)?|deactivat(?:e|ed)|terminat(?:e|ed))\b", re.I
        ),
        weight=0.8,
        description="Account threat",
    ),
    Pattern(
        category=ScamCategory.THREAT,
        pattern=re.compile(
            r"\b(arrest(?:ed)?|legal\s+action|court|lawsuit|police\s+case)\b", re.I
        ),
        weight=0.9,
        description="Legal threat",
    ),
    Pattern(
        category=ScamCategory.THREAT,
        pattern=re.compile(r"\b(fine|penalty|fee|charge)\b", re.I),
        weight=0.5,
        description="Financial penalty threat",
    ),
    Pattern(
        category=ScamCategory.THREAT,
        pattern=re.compile(
            r"\b(fraud(?:ulent)?|suspicious|unauthorized|illegal)\b", re.I
        ),
        weight=0.6,
        description="Fraud accusation",
    ),
]

# ============================================================
# REQUEST PATTERNS - Ask for sensitive data
# ============================================================
REQUEST_PATTERNS = [
    Pattern(
        category=ScamCategory.REQUEST,
        pattern=re.compile(r"\b(OTP|one\s*time\s*password|verification\s+code)\b", re.I),
        weight=0.95,
        description="OTP request",
    ),
    Pattern(
        category=ScamCategory.REQUEST,
        pattern=re.compile(r"\b(PIN|CVV|card\s+number|expiry)\b", re.I),
        weight=0.95,
        description="Card details request",
    ),
    Pattern(
        category=ScamCategory.REQUEST,
        pattern=re.compile(r"\b(password|credentials?|login\s+details?)\b", re.I),
        weight=0.9,
        description="Password request",
    ),
    Pattern(
        category=ScamCategory.REQUEST,
        pattern=re.compile(
            r"\b(verify|confirm|validate|update)\s+(?:your)?\s*(?:account|details?|KYC)\b",
            re.I,
        ),
        weight=0.7,
        description="Verification request",
    ),
    Pattern(
        category=ScamCategory.REQUEST,
        pattern=re.compile(r"\b(KYC|know\s+your\s+customer|Aadhaar|PAN)\b", re.I),
        weight=0.6,
        description="KYC request",
    ),
]

# ============================================================
# FINANCIAL PATTERNS - Money/payment related
# ============================================================
FINANCIAL_PATTERNS = [
    Pattern(
        category=ScamCategory.FINANCIAL,
        pattern=re.compile(
            r"\b(transfer|send|pay|deposit)\s+(?:money|amount|₹|\$|Rs\.?)\b", re.I
        ),
        weight=0.8,
        description="Money transfer request",
    ),
    Pattern(
        category=ScamCategory.FINANCIAL,
        pattern=re.compile(r"\b(refund|cashback|reward|prize|lottery|winner)\b", re.I),
        weight=0.7,
        description="Money lure",
    ),
    Pattern(
        category=ScamCategory.FINANCIAL,
        pattern=re.compile(
            r"\b(UPI|NEFT|IMPS|bank\s+transfer|Google\s*Pay|PhonePe|Paytm)\b", re.I
        ),
        weight=0.5,
        description="Payment method mention",
    ),
    Pattern(
        category=ScamCategory.FINANCIAL,
        pattern=re.compile(
            r"[₹$]\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*\s*(?:rupees?|Rs\.?)",
            re.I,
        ),
        weight=0.4,
        description="Money amount",
    ),
]

# ============================================================
# PHISHING PATTERNS - Links and downloads
# ============================================================
PHISHING_PATTERNS = [
    Pattern(
        category=ScamCategory.PHISHING,
        pattern=re.compile(
            r"https?://(?!(?:www\.)?(?:google|microsoft|apple|amazon|gov\.in))[^\s]+",
            re.I,
        ),
        weight=0.6,
        description="Suspicious link",
    ),
    Pattern(
        category=ScamCategory.PHISHING,
        pattern=re.compile(
            r"\b(click\s+(?:here|link|below)|download|install|open)\b", re.I
        ),
        weight=0.5,
        description="Click/download request",
    ),
    Pattern(
        category=ScamCategory.PHISHING,
        pattern=re.compile(r"(?:bit\.ly|tinyurl|goo\.gl|t\.co|shorturl)/\S+", re.I),
        weight=0.8,
        description="Shortened URL",
    ),
]

# ============================================================
# INSTANT SCAM PATTERNS - Skip AI, engage immediately (95%+ confidence)
# ============================================================
INSTANT_SCAM_PATTERNS = [
    re.compile(r"send\s+(your\s+)?(otp|password|pin|cvv)", re.I),
    re.compile(r"verify\s+within\s+\d+\s+(hours?|minutes?)", re.I),
    re.compile(r"account\s+(will\s+be\s+)?(blocked|suspended|locked).*immediately", re.I),
    re.compile(r"click\s+(here|link).*verify", re.I),
    re.compile(r"(lottery|jackpot|won)\s+[₹$]?\s*\d+", re.I),
    re.compile(r"share\s+(your\s+)?(otp|cvv|pin)\s+(to|for)", re.I),
    re.compile(r"(arrest|legal\s+action).*immediately", re.I),
]

# ============================================================
# SAFE PATTERNS - Skip AI, return neutral (legitimate messages)
# ============================================================
SAFE_PATTERNS = [
    re.compile(r"your\s+otp\s+is\s+\d{4,6}", re.I),  # OTP delivery from services
    re.compile(
        r"transaction\s+of\s+rs\.?\s*\d+.*debited", re.I
    ),  # Bank notifications
    re.compile(r"your\s+order\s+#?\d+\s+has\s+been", re.I),  # Order confirmations
    re.compile(r"otp\s+for\s+.*is\s+\d{4,6}", re.I),  # OTP format
]

# ============================================================
# ALL PATTERNS - Combined list for weighted scoring
# ============================================================
ALL_PATTERNS: list[Pattern] = [
    *URGENCY_PATTERNS,
    *AUTHORITY_PATTERNS,
    *THREAT_PATTERNS,
    *REQUEST_PATTERNS,
    *FINANCIAL_PATTERNS,
    *PHISHING_PATTERNS,
]


def get_patterns_by_category(category: ScamCategory) -> list[Pattern]:
    """Get all patterns for a specific category."""
    return [p for p in ALL_PATTERNS if p.category == category]


def match_all_patterns(text: str) -> list[PatternMatch]:
    """Match text against all weighted patterns."""
    matches = []
    for pattern in ALL_PATTERNS:
        for match in pattern.pattern.finditer(text):
            matches.append(
                PatternMatch(
                    category=pattern.category,
                    matched_text=match.group(),
                    weight=pattern.weight,
                    description=pattern.description,
                )
            )
    return matches


def pre_filter(text: str) -> PreFilterResult:
    """
    Fast regex pre-filter to skip AI for obvious cases.

    Returns:
        OBVIOUS_SCAM: High-confidence scam, skip AI and engage immediately
        OBVIOUS_SAFE: Legitimate message, skip AI and return neutral
        UNCERTAIN: Needs AI classification
    """
    # Check for obvious scams first
    for pattern in INSTANT_SCAM_PATTERNS:
        if pattern.search(text):
            return PreFilterResult.OBVIOUS_SCAM

    # Check for safe patterns
    for pattern in SAFE_PATTERNS:
        if pattern.search(text):
            return PreFilterResult.OBVIOUS_SAFE

    # Uncertain - needs AI classification
    return PreFilterResult.UNCERTAIN
