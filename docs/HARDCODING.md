# Hardcoding Report - Sticky-Net

> **Generated**: February 5, 2026  
> **Purpose**: Document all hardcoded patterns, regex extractions, pre-made responses, and static data in the system

---

## Table of Contents

1. [Regex Patterns for Extraction/Validation](#1-regex-patterns-for-extractionvalidation)
2. [Hardcoded Keyword/Indicator Lists](#2-hardcoded-keywordindicator-lists)
3. [Hardcoded Persona](#3-hardcoded-persona-single-static-identity)
4. [Pre-made Response Templates](#4-pre-made-response-templates)
5. [Hardcoded Detection Thresholds](#5-hardcoded-detection-thresholds)
6. [Hardcoded Fake Data Generation](#6-hardcoded-fake-data-generation)
7. [Scam Classification Prompt](#7-scam-classification-prompt-hardcoding)
8. [Risk Summary](#risk-summary)
9. [Key Concerns](#key-concerns)
10. [What's Done Well](#whats-done-well)
11. [Recommendations](#recommendations)

---

## 1. Regex Patterns for Extraction/Validation

| File | Pattern | Purpose | Risk |
|------|---------|---------|------|
| `src/intelligence/extractor.py` | `r'^\d{9,18}$'` | Bank account validation (9-18 digits) | Low |
| `src/intelligence/extractor.py` | `r'^[\w.-]+@({providers})$'` | UPI ID with ~140 hardcoded providers | **Medium** |
| `src/intelligence/extractor.py` | `r'^[\w.-]+@[a-zA-Z][a-zA-Z0-9]*$'` | Fallback UPI validation | Low |
| `src/intelligence/extractor.py` | `r'^[6-9]\d{9}$'` | Indian mobile (starts 6-9, 10 digits) | Low |
| `src/intelligence/extractor.py` | `r'^\+91[6-9]\d{9}$'` | Phone with +91 prefix | Low |
| `src/intelligence/extractor.py` | `r'^[A-Z]{4}0[A-Z0-9]{6}$'` | IFSC code format | Low |
| `src/intelligence/extractor.py` | `r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'` | Email validation | Low |
| `src/intelligence/extractor.py` | `r'https?://[^\s<>"\'{}|\\^`\[\]]+` | URL extraction | Low |
| `src/intelligence/extractor.py` | `r'(?<![/@])(?:[a-zA-Z0-9-]+\.)+(?:com|net|org|...)\b'` | URLs without http/https | Low |
| `src/detection/detector.py` | `r'https?://[^\s]+'` | URL detection in scam messages | Low |

### Notes
- Regex patterns are used for **format validation** after AI extraction, not primary detection
- The UPI provider list requires periodic updates as new providers emerge

---

## 2. Hardcoded Keyword/Indicator Lists

### 2.1 SUSPICIOUS_URL_INDICATORS
**File**: `src/intelligence/extractor.py` (Lines ~218-263)

```python
SUSPICIOUS_URL_INDICATORS = [
    # URL shorteners (very common in scams)
    "bit.ly", "tinyurl", "t.co", "goo.gl", "is.gd", "cutt.ly",
    "shorturl.at", "tiny.cc", "rb.gy", "clck.ru",
    
    # Phishing keywords
    "login", "verify", "update", "secure", "account", "signin", "password",
    "confirm", "validate", "suspend", "locked", "urgent", "alert",
    
    # KYC/OTP scam keywords
    "kyc", "otp", "bank", "sbi", "hdfc", "icici", "axis", "kotak", "pnb",
    "canara", "bob", "union", "indian", "central", "uco", "yes",
    
    # Brand impersonation
    "amazon", "flipkart", "paytm", "phonepe", "gpay", "googlepay",
    "netflix", "hotstar", "jio", "airtel", "vi", "bsnl",
    
    # Free TLDs often used in scams
    ".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".work", ".click",
    
    # Additional suspicious patterns
    "prize", "winner", "lottery", "reward", "gift", "free", "claim",
    "bitcoin", "crypto", "investment", "trading", "forex",
]
```

**Count**: ~80 keywords  
**Risk**: **HIGH** - Static list may miss new scam domains or flag legitimate sites

---

### 2.2 UPI_PROVIDERS
**File**: `src/intelligence/extractor.py` (Lines ~28-155)

```python
UPI_PROVIDERS = [
    # Paytm variants
    "ptaxis", "ptyes", "ptsbi", "pthdfc", "paytm",
    
    # Google Pay / BHIM variants
    "okhdfcbank", "okicici", "oksbi", "okaxis",
    
    # Bank-specific handles
    "ybl", "ibl", "axl", "sbi", "icici", "hdfc",
    # ... ~140 total providers
]
```

**Count**: ~140 providers  
**Risk**: **MEDIUM** - New UPI providers launch frequently (Cred, Jupiter, Fi, etc.)

---

### 2.3 INDIAN_BANK_NAMES
**File**: `src/intelligence/extractor.py` (Lines ~266-297)

```python
INDIAN_BANK_NAMES = [
    "SBI", "State Bank of India", "State Bank",
    "PNB", "Punjab National Bank",
    "HDFC", "HDFC Bank",
    "ICICI", "ICICI Bank",
    "Axis", "Axis Bank",
    "Kotak", "Kotak Mahindra",
    "Yes Bank", "IndusInd",
    "Bank of Baroda", "BOB",
    "Union Bank", "Canara Bank",
    "Bank of India", "Central Bank",
    "Indian Bank", "UCO Bank",
    "IDBI", "IDFC First",
    "Federal Bank", "South Indian Bank",
    "Karnataka Bank", "Karur Vysya",
    # ... 48 total banks
]
```

**Count**: 48 banks  
**Risk**: **LOW** - Used for reference/validation, not detection

---

### 2.4 BENEFICIARY_NAME_BLOCKLIST
**File**: `src/intelligence/extractor.py` (Lines ~300-318)

```python
BENEFICIARY_NAME_BLOCKLIST = {
    "now", "before", "paying", "name", "sir", "madam", "ji",
    "please", "urgent", "click", "here", "send", "pay", "fast",
    "verification", "account", "bank", "upi", "payment", "money",
    "transfer", "amount", "rupees", "rs", "inr", "otp", "kyc",
    "update", "verify", "confirm", "details", "information",
}
```

**Count**: ~30 words  
**Risk**: **MEDIUM** - May block valid names that are common words

---

## 3. Hardcoded Persona (Single Static Identity)

**File**: `src/agents/engagement.py`

### HONEYPOT_PERSONA_PROMPT

```markdown
## CORE PERSONA: PUSHPA VERMA
- Age: 65+, retired school teacher from Delhi
- Tech literacy: Very low
- Personality: Trusting, easily panicked by authority figures
- Typing style: mostly lowercase, minimal punctuation, occasional typos
- Emotional: Gets scared easily, apologizes often, says "beta" or "sir/madam"
- Background: Lives alone, son works in Bangalore, daughter is married
```

**Risk**: **MEDIUM**
- The same persona identity is used for every engagement
- Repeated scammers could potentially recognize the pattern
- However, LLM generates varied responses within this persona framework

---

## 4. Pre-made Response Templates

### 4.1 Normal Responses (Non-Scam)
**File**: `src/agents/engagement.py`

```python
normal_responses = [
    "Hello! How can I help you today?",
    "Hi there! Is everything alright?",
    "Hey! What can I do for you?",
    "Hello! Yes, I'm here. What's up?",
    "Hi! I'm listening. What did you want to tell me?",
]
```

**Count**: 5 responses  
**Risk**: **LOW** - Simple greetings for non-scam messages

---

### 4.2 Exit Responses (Intelligence Complete)
**File**: `src/agents/engagement.py`

```python
exit_responses = [
    "okay i am calling that number now, hold on...",
    "wait my son just came home, let me ask him to help me with this",
    "one second, someone is at the door, i will call you back",
    "let me check with my daughter first, she knows about these things",
    "i think i should ask my neighbor, he works in IT",
    "my phone battery is very low, let me charge it and call you back",
    "okay okay, let me write down all the details first",
    "wait i need to find my reading glasses to see the screen properly",
    "hold on, my other phone is ringing, maybe it's my son",
    "let me sit down first, i am feeling a bit dizzy from all this tension",
    "oh no my doorbell is ringing, someone is at the door...",
    "sorry my neighbor aunty just came, i have to go help her with something urgent",
    "arey my grandson is crying, i need to check on him... one minute",
    "oh god my cooking is burning on the stove! i smell smoke!! wait wait",
    "my milk is boiling over! let me quickly check the kitchen",
    "sorry sir my back pain is starting again, i need to take medicine and rest",
    "wait i am getting another call from unknown number, maybe its important",
    "let me first drink water, i am feeling very stressed from all this",
    "one moment, i think i heard my pressure cooker whistle",
    "arey the electricity just went! load shedding... let me find candle",
]
```

**Count**: 20 responses  
**Risk**: **MEDIUM** - Static exit lines could become recognizable over time

---

### 4.3 Fallback Responses (LLM Failure)
**File**: `src/agents/engagement.py`

```python
fallback_responses = [
    "I'm sorry, I'm a bit confused. Can you explain that again?",
    "My phone is acting up. What do I need to do exactly?",
    "I didn't understand. Can you tell me step by step?",
    "Okay, but what should I do first? I'm worried.",
]
```

**Count**: 4 responses  
**Risk**: **LOW** - Only used as emergency fallback when AI fails

---

### 4.4 Response Strategies by Category
**File**: `src/agents/engagement.py`

```python
RESPONSE_STRATEGIES = {
    "urgency": [
        "wait what is happening. i am at work can this wait",
        "ok ok let me understand. what exactly do i need to do here",
        # ...
    ],
    "authority": [
        "you are from {authority}. how do i know this is real",
        "yes i want to help. what papers do you need from me",
        # ...
    ],
    "financial": [
        "i dont have much money right now. how much is it exactly",
        "which account do i send to. i want to make sure its correct",
        # ...
    ],
    "threat": [
        "please dont do that. i will cooperate just tell me what to do",
        "i dont want legal problem. how do i fix this",
        # ...
    ],
}
```

**Risk**: **LOW** - These are examples/guidance; actual responses are LLM-generated

---

## 5. Hardcoded Detection Thresholds

| File | Constant | Value | Configurable? |
|------|----------|-------|---------------|
| `config/settings.py` | `cautious_confidence_threshold` | 0.60 | ✅ Yes (env var) |
| `config/settings.py` | `aggressive_confidence_threshold` | 0.85 | ✅ Yes (env var) |
| `src/detection/detector.py` | `SCAM_THRESHOLD` | 0.6 | ❌ **Hardcoded** |
| `src/agents/engagement.py` | `stale_turn_threshold` | 5 | ❌ **Hardcoded** |
| `src/agents/engagement.py` | `max_engagement_turns` | 50 | ✅ Yes (settings) |

### Issue
`SCAM_THRESHOLD` in detector.py is hardcoded at 0.6 despite `cautious_confidence_threshold` being configurable in settings.py. These should be synchronized.

---

## 6. Hardcoded Fake Data Generation

**File**: `src/intelligence/fake_data.py`

### 6.1 Name Lists

```python
FEMALE_FIRST_NAMES = [
    "Kamala", "Lakshmi", "Saraswati", "Parvati", "Sita",
    "Radha", "Durga", "Ganga", "Savitri", "Shakuntala",
    "Meera", "Rukmini", "Annapurna", "Sumitra", "Kausalya",
    "Pushpa", "Shanti", "Vimala", "Padma", "Usha",
    "Saroj", "Geeta", "Leela", "Sudha", "Nirmala",
]

MALE_FIRST_NAMES = [
    "Ramesh", "Suresh", "Rajesh", "Mahesh", "Ganesh",
    "Prakash", "Anil", "Vijay", "Rajan", "Mohan",
    # ...
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar",
    "Agarwal", "Jain", "Patel", "Reddy", "Rao",
    # ...
]
```

**Risk**: **LOW** - Provides variety for consistent fake victim data

---

### 6.2 Location Data

```python
CITIES = [
    ("Mumbai", "Maharashtra"),
    ("Delhi", "Delhi"),
    ("Bangalore", "Karnataka"),
    ("Chennai", "Tamil Nadu"),
    ("Kolkata", "West Bengal"),
    # ... ~30 cities
]
```

**Risk**: **LOW** - Standard Indian city list

---

### 6.3 Invalid Card BINs

```python
INVALID_VISA_BINS = ["400000", "411111", "400012", "400023", "499999"]
INVALID_MASTERCARD_BINS = ["510000", "520000", "540000", "559999"]
INVALID_RUPAY_BINS = ["607000", "608000", "652000"]
```

**Risk**: **LOW** - Intentionally invalid test BINs to waste scammer time

---

### 6.4 Bank IFSC Prefixes

```python
BANK_IFSC_PREFIXES = {
    "SBIN": "State Bank of India",
    "HDFC": "HDFC Bank",
    "ICIC": "ICICI Bank",
    "UTIB": "Axis Bank",
    "KKBK": "Kotak Mahindra Bank",
    # ...
}
```

**Risk**: **LOW** - Standard IFSC prefix mapping

---

## 7. Scam Classification Prompt Hardcoding

**File**: `src/detection/detector.py`

### CLASSIFICATION_PROMPT

A large static prompt containing:
- What constitutes a scam vs legitimate message
- Scam signal indicators (urgency, authority, payment flags, phishing, threats)
- Scam type classifications
- Response format instructions

**Risk**: **MEDIUM**
- Comprehensive but static
- Novel scam types may not be covered
- However, LLM has flexibility to detect patterns beyond examples

---

## Risk Summary

| Risk Level | Count | Items |
|------------|-------|-------|
| **High** | 1 | `SUSPICIOUS_URL_INDICATORS` - static list of ~80 scam keywords |
| **Medium** | 5 | UPI_PROVIDERS, Persona (Pushpa), Exit responses, Name blocklist, Detection prompt |
| **Low** | 15+ | Regex patterns, configurable thresholds, fake data, greetings, fallbacks |

---

## Key Concerns

### 1. Single Persona "Pushpa Verma"
The same identity (65+ retired teacher from Delhi) is used for every engagement. Repeat scammers could recognize the pattern.

### 2. Static URL Indicators
The ~80 suspicious keywords may:
- Miss new scam domains/patterns
- Flag legitimate sites with common words

### 3. Hardcoded Exit Responses
20 pre-written exit lines could become recognizable:
- "my cooking is burning on the stove!"
- "my grandson is crying"
- "load shedding... let me find candle"

### 4. UPI Provider List Staleness
~140 providers listed, but new ones launch frequently:
- Cred (@cred)
- Jupiter (@jupiter)
- Fi (@fi)
- Slice (@slice)

### 5. Threshold Mismatch
`SCAM_THRESHOLD = 0.6` is hardcoded in detector.py despite `cautious_confidence_threshold` being configurable in settings.py.

---

## What's Done Well

### ✅ AI-First Detection
Regex patterns are used for **format validation** after AI extraction, not as the primary detection mechanism. The LLM handles semantic understanding.

### ✅ Configurable Core Thresholds
Most critical thresholds are environment-configurable via settings:
- `CAUTIOUS_CONFIDENCE_THRESHOLD`
- `AGGRESSIVE_CONFIDENCE_THRESHOLD`
- `MAX_ENGAGEMENT_TURNS`

### ✅ LLM-Generated Responses
Actual engagement responses come from Gemini, not from hardcoded templates. Templates are fallbacks only.

### ✅ Seeded Fake Data Generation
Fake victim data uses consistent seeding per conversation for coherence while maintaining variety across conversations.

### ✅ Fallback Providers Pattern
UPI validation has a fallback regex `r'^[\w.-]+@[a-zA-Z][a-zA-Z0-9]*$'` for unknown providers.

---

## Recommendations

### High Priority

1. **Make URL Indicators Configurable**
   - Move `SUSPICIOUS_URL_INDICATORS` to external config file
   - Allow runtime updates without code changes

2. **Synchronize Thresholds**
   - Replace hardcoded `SCAM_THRESHOLD = 0.6` in detector.py with `settings.cautious_confidence_threshold`

### Medium Priority

3. **Dynamic Persona Generation**
   - Consider rotating between 3-5 different personas
   - Or let LLM generate persona variations

4. **Expand Exit Response Variety**
   - Add more exit responses
   - Or generate them dynamically via LLM

5. **UPI Provider Updates**
   - Create mechanism to update provider list without deployment
   - Or rely more heavily on fallback regex

### Low Priority

6. **Externalize Classification Prompt**
   - Move `CLASSIFICATION_PROMPT` to config file
   - Allow updates without code changes

7. **Add Missing Thresholds to Settings**
   - Make `stale_turn_threshold` configurable
   - Add to settings.py with environment variable support

---

## Appendix: File Locations

| Category | File Path |
|----------|-----------|
| Intelligence Extraction | `src/intelligence/extractor.py` |
| Fake Data Generation | `src/intelligence/fake_data.py` |
| Scam Detection | `src/detection/detector.py` |
| Agent Engagement | `src/agents/engagement.py` |
| Configuration | `config/settings.py` |
