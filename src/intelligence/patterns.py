"""Regex patterns and indicator lists used to recognise Indian payment and phishing data.

validators.py applies these; extractor.py reuses the indicator lists.
"""

import re

# =============================================================================
# REGEX PATTERNS FOR VALIDATION
# =============================================================================

# Bank Account Pattern: 9-18 digits
BANK_ACCOUNT_PATTERN = re.compile(r"^\d{9,18}$")

# UPI ID Pattern: username@provider
UPI_PROVIDERS = [
    # Paytm
    "ptaxis",
    "ptyes",
    "ptsbi",
    "pthdfc",
    "paytm",
    # Google Pay
    "okhdfcbank",
    "okicici",
    "oksbi",
    "okaxis",
    # PhonePe
    "ybl",
    "ibl",
    "axl",
    # Slice
    "sliceaxis",
    "slicepay",
    "slc",
    # Kotak
    "kotak",
    "kotak811",
    # Cred
    "axisb",
    "yescred",
    "yescurie",
    # Amazon Pay
    "apl",
    "yapl",
    "rapl",
    # Fampay
    "fam",
    "yesfam",
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
    "boi",
    "mboi",
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
    "indus",
    "indie",
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
    "yespop",
    "yespay",
    "yes",
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
    "fifederal",
    "federal",
    # Canara
    "cnrb",
    # Fincare
    "fincarebank",
    "finobank",
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
    "citi",
    "citigold",
    # Groww Pay
    "yesg",
    # Indian Bank (IndOASIS)
    "indianbank",
    "allbank",
    # Union Bank of India
    "unionbankofindia",
    "uboi",
    "unionbank",
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
    "bit.ly",
    "tinyurl",
    "t.co",
    "goo.gl",
    "is.gd",
    "cutt.ly",
    "rebrand.ly",
    "ow.ly",
    "buff.ly",
    "adf.ly",
    "bc.vc",
    "j.mp",
    "v.gd",
    "x.co",
    "shorturl",
    "short.io",
    "rb.gy",
    "clck.ru",
    "tinu.be",
    "tiny.cc",
    "s.id",
    "shrtco.de",
    "1link.in",
    "linktr.ee",
    "lnk.to",
    # Phishing keywords
    "login",
    "verify",
    "update",
    "secure",
    "account",
    "signin",
    "password",
    "confirm",
    "authenticate",
    "validation",
    "unlock",
    "suspend",
    "blocked",
    "expired",
    "reactivate",
    "restore",
    "recover",
    "reset",
    "renew",
    # KYC/OTP scam keywords
    "kyc",
    "otp",
    "bank",
    "sbi",
    "hdfc",
    "icici",
    "axis",
    "kotak",
    "pnb",
    "aadhaar",
    "aadhar",
    "pan-",
    "pancard",
    "e-kyc",
    "ekyc",
    # Fake payment/UPI domains
    ".pay.",
    "pay.in",
    "-pay",
    "pay-",
    "upi-",
    "-upi",
    "payment",
    "bhim",
    "rupay",
    "npci",
    "imps",
    "neft",
    "rtgs",
    # Brand impersonation (common in Indian scams)
    "amazon",
    "flipkart",
    "paytm",
    "phonepe",
    "gpay",
    "google-pay",
    "kbc",
    "jio",
    "airtel",
    "vodafone",
    "bsnl",
    "netflix",
    "hotstar",
    "swiggy",
    "zomato",
    "ola",
    "uber",
    "myntra",
    "ajio",
    # Prize/lottery/refund scam keywords
    "prize",
    "claim",
    "refund",
    "reward",
    "winner",
    "lucky",
    "lottery",
    "cashback",
    "bonus",
    "offer",
    "gift",
    "free",
    "win",
    "congratulation",
    # Job scam keywords
    "jobs",
    "hiring",
    "vacancy",
    "career",
    "recruitment",
    "salary",
    "earning",
    "work-from-home",
    "part-time",
    "income",
    "money-making",
    # Free/suspicious TLDs often used in phishing
    ".tk",
    ".ml",
    ".ga",
    ".cf",
    ".gq",  # Free domains
    ".xyz",
    ".work",
    ".top",
    ".site",
    ".online",
    ".club",
    ".icu",
    ".buzz",
    ".co.in",  # Often abused for Indian phishing
    ".info",
    ".biz",
    ".ws",
    ".cc",
    ".pw",
    ".space",
    ".life",
    ".live",
    ".click",
    ".link",
    ".download",
    ".stream",
    ".in/",
    ".store",
    ".shop",
    ".app",
    ".me",
    ".vip",
    ".pro",
    # Messaging links
    "telegram",
    "wa.me",
    "whatsapp",
    "t.me",
    "chat.whatsapp",
    # Form/survey scams
    "forms.gle",
    "docs.google",
    "survey",
    "form",
    "fill",
    # Suspicious subdomains/paths
    "-secure",
    "-verify",
    "-login",
    "-update",
    "-bank",
    "secure-",
    "verify-",
    "login-",
    "update-",
    "bank-",
    # Indian bank name impersonation
    "sbi-",
    "-sbi",
    "hdfc-",
    "-hdfc",
    "icici-",
    "-icici",
    "axis-",
    "-axis",
    "kotak-",
    "-kotak",
    "pnb-",
    "-pnb",
    "bob-",
    "-bob",
    "canara-",
    "-canara",
    "union-",
    "-union",
    "idbi-",
    "-idbi",
    "yes-",
    "-yes",
    "rbi-",
    "-rbi",
    # Random alphanumeric paths (common in phishing)
    "/xY",
    "/aB",
    "/Xy",
    "/Ab",
    "/kY",
    "/mN",
    "/pQ",
    "/rS",
]
