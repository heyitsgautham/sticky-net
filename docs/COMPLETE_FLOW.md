# Sticky-Net: Complete System Flow Documentation

> **Comprehensive technical documentation of the AI-powered honeypot system for scam detection and intelligence extraction**

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Request Lifecycle](#3-request-lifecycle)
4. [Stage 0: Application Entry Point](#4-stage-0-application-entry-point)
5. [Stage 1: API Layer & Request Handling](#5-stage-1-api-layer--request-handling)
6. [Stage 2: Hybrid Scam Detection](#6-stage-2-hybrid-scam-detection)
7. [Stage 3: Intelligence Extraction](#7-stage-3-intelligence-extraction)
8. [Stage 4: Engagement Policy & Exit Conditions](#8-stage-4-engagement-policy--exit-conditions)
9. [Stage 5: AI Agent Engagement](#9-stage-5-ai-agent-engagement)
10. [Stage 6: Response Generation](#10-stage-6-response-generation)
11. [Data Flow Diagram](#11-data-flow-diagram)
12. [Component Deep Dives](#12-component-deep-dives)
13. [Error Handling](#13-error-handling)
14. [Configuration & Settings](#14-configuration--settings)
15. [Security Considerations](#15-security-considerations)

---

## 1. System Overview

### What is Sticky-Net?

Sticky-Net is an **AI-powered honeypot system** designed to:

1. **Detect scam messages** using a hybrid approach (fast regex patterns + AI semantic analysis)
2. **Autonomously engage scammers** with a believable human persona
3. **Extract actionable intelligence** (bank accounts, UPI IDs, phone numbers, beneficiary names)
4. **Waste scammer time** while gathering evidence for law enforcement

### Core Philosophy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         STICKY-NET PRINCIPLES                            │
├─────────────────────────────────────────────────────────────────────────┤
│  1. NEVER reveal that the system knows it's a scam                      │
│  2. Act as a naive, trusting, tech-confused victim                      │
│  3. Extract MAXIMUM intelligence before exiting                         │
│  4. Confidence can only INCREASE (prevents false negative oscillation)  │
│  5. Prioritize beneficiary name extraction (identifies mule accounts)   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Runtime** | Python 3.11+ | Core language |
| **API Framework** | FastAPI | REST API endpoints |
| **AI SDK** | `google-genai` v1.51+ | Gemini model access |
| **Primary Models** | Gemini 3 Flash/Pro | Scam detection & engagement |
| **Fallback Models** | Gemini 2.5 Flash/Pro | Reliability fallback |
| **Logging** | structlog | Structured JSON logging |
| **Validation** | Pydantic | Request/response validation |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           INCOMING REQUEST                              │
│         { message, conversationHistory, metadata }                      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MIDDLEWARE LAYER                                     │
│    ┌─────────────────┐    ┌─────────────────────────────────────┐       │
│    │ API Key Auth    │───▶│ Request Timing (X-Process-Time)     │       │
│    └─────────────────┘    └─────────────────────────────────────┘       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    DETECTION LAYER                                       │
│    ┌─────────────────┐         ┌────────────────────────────────┐       │
│    │ Regex Pre-Filter│────────▶│ AI Classifier (Gemini 3 Flash) │       │
│    │ (~10ms)         │         │ (~150ms)                       │       │
│    │ • Obvious Scam  │         │ • Semantic Analysis            │       │
│    │ • Obvious Safe  │         │ • Context-Aware                │       │
│    │ • Uncertain     │         │ • Confidence Scoring           │       │
│    └─────────────────┘         └────────────────────────────────┘       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE EXTRACTION                               │
│    ┌───────────────────────────────────────────────────────────────┐    │
│    │ Regex-based extraction (runs on ALL messages)                 │    │
│    │ • Bank Accounts (9-18 digits)                                  │    │
│    │ • UPI IDs (username@provider)                                  │    │
│    │ • Phone Numbers (Indian: 6-9 prefix, 10 digits)               │    │
│    │ • Beneficiary Names (account holder names)                     │    │
│    │ • IFSC Codes, Bank Names, WhatsApp Numbers                    │    │
│    │ • Phishing Links (suspicious URLs)                            │    │
│    └───────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
        ┌────────────────────────┴────────────────────────┐
        │                                                  │
    Not Scam                                           Is Scam
        │                                                  │
        ▼                                                  ▼
┌───────────────────┐                    ┌─────────────────────────────────┐
│ Return neutral    │                    │ ENGAGEMENT POLICY CHECK         │
│ response          │                    │ • High-value intel complete?    │
│ Continue monitor  │                    │   → Exit with polite excuse     │
└───────────────────┘                    │ • Still missing intel?          │
                                         │   → Continue engagement         │
                                         └─────────────────────────────────┘
                                                           │
                                                           ▼
                                         ┌─────────────────────────────────┐
                                         │ AI ENGAGEMENT AGENT             │
                                         │ (Gemini 3 Pro)                  │
                                         │ • Persona management            │
                                         │ • Fake data generation          │
                                         │ • Targeted extraction prompts   │
                                         │ • Believable human responses    │
                                         └─────────────────────────────────┘
                                                           │
                                                           ▼
                                         ┌─────────────────────────────────┐
                                         │ RESPONSE BUILDER                │
                                         │ • Format API response           │
                                         │ • Include extracted intel       │
                                         │ • Return agent notes            │
                                         └─────────────────────────────────┘
```

---

## 3. Request Lifecycle

### Complete Request Journey

```
Time ──────────────────────────────────────────────────────────────────────▶

│ T+0ms       │ T+5ms         │ T+15ms        │ T+200ms       │ T+700ms     │
│             │               │               │               │             │
▼             ▼               ▼               ▼               ▼             ▼
┌─────────┐   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐
│ Request │──▶│ Middleware  │─▶│ Regex       │─▶│ AI Class.  │─▶│ AI Agent  │
│ Arrives │   │ Auth+Timer  │ │ Pre-filter  │ │ (if needed) │ │ Engagement│
└─────────┘   └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘
                                                                     │
                                                                     ▼
                                                              ┌───────────┐
                                                              │ Response  │
                                                              │ Returned  │
                                                              └───────────┘
```

### Timing Breakdown

| Stage | Typical Duration | Description |
|-------|------------------|-------------|
| Middleware | ~2ms | API key validation, timing start |
| Regex Pre-filter | ~10ms | Pattern matching for obvious cases |
| AI Classification | ~150ms | Gemini 3 Flash semantic analysis |
| Intelligence Extraction | ~5ms | Regex extraction of all intel types |
| Policy Check | ~1ms | Exit condition evaluation |
| AI Engagement | ~500ms | Gemini 3 Pro response generation |
| **Total (scam)** | **~700ms** | Full pipeline for scam engagement |
| **Total (safe)** | **~200ms** | Early exit for non-scam messages |

---

## 4. Stage 0: Application Entry Point

### File: `src/main.py`

The application starts with FastAPI initialization and configuration.

```python
# Application creation flow
def create_app() -> FastAPI:
    """
    1. Load settings from environment/.env
    2. Create FastAPI instance with metadata
    3. Configure CORS (permissive in debug, restrictive in production)
    4. Setup middleware (auth + timing)
    5. Mount API routes
    6. Mount static files for web UI
    """
```

### Startup Sequence

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION STARTUP                             │
└─────────────────────────────────────────────────────────────────────────┘

1. Load Configuration
   ┌────────────────────────────────────────────────────────────────────┐
   │ Settings loaded from:                                              │
   │ • Environment variables (GOOGLE_CLOUD_PROJECT, API_KEY, etc.)      │
   │ • .env file (local development)                                    │
   │ • Default values in Settings class                                 │
   └────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
2. Configure Logging
   ┌────────────────────────────────────────────────────────────────────┐
   │ structlog configured with:                                         │
   │ • JSON output format                                               │
   │ • ISO timestamp                                                    │
   │ • Log level filtering                                              │
   │ • Exception formatting                                             │
   └────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
3. Initialize FastAPI
   ┌────────────────────────────────────────────────────────────────────┐
   │ FastAPI(                                                           │
   │   title="Sticky-Net",                                              │
   │   description="AI Agentic Honey-Pot",                              │
   │   docs_url="/docs" if debug else None,  # Hide docs in production  │
   │   lifespan=lifespan,  # Startup/shutdown handlers                  │
   │ )                                                                  │
   └────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
4. Setup Middleware Chain
   ┌────────────────────────────────────────────────────────────────────┐
   │ Order matters! Applied in reverse order of addition:               │
   │                                                                    │
   │ Request ──▶ CORS ──▶ APIKeyAuth ──▶ RequestTiming ──▶ Route        │
   │                                                                    │
   │ Response ◀── CORS ◀── APIKeyAuth ◀── RequestTiming ◀── Route       │
   └────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
5. Mount Routes
   ┌────────────────────────────────────────────────────────────────────┐
   │ /health          - Health check endpoint                           │ 
   │ /                - Web UI (index.html)                             │
   │ /api/v1/analyze  - Main analysis endpoint                          │
   │ /docs            - OpenAPI documentation (debug only)              │
   │ /static/*        - Static files                                    │
   └────────────────────────────────────────────────────────────────────┘
```

---

## 5. Stage 1: API Layer & Request Handling

### Request Schema

```python
# File: src/api/schemas.py

class AnalyzeRequest(BaseModel):
    """
    Main API request structure.
    
    Fields:
    - message: Current message from the scammer
    - conversationHistory: List of previous messages (for context)
    - metadata: Channel, language, locale information
    """
    message: Message
    conversationHistory: list[ConversationMessage] = []
    metadata: Metadata = Metadata()
```

### Request Validation Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         REQUEST VALIDATION                               │
└─────────────────────────────────────────────────────────────────────────┘

Incoming JSON:
{
  "message": {
    "sender": "scammer",
    "text": "Your account blocked. Send OTP now!",
    "timestamp": "2026-01-24T10:00:00Z"
  },
  "conversationHistory": [...],
  "metadata": {"channel": "SMS", "locale": "IN"}
}
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PYDANTIC VALIDATION                                                    │
├────────────────────────────────────────────────────────────────────────┤
│ ✓ message.sender must be "scammer" or "user"                          │
│ ✓ message.text length: 1-5000 characters                              │
│ ✓ message.timestamp must be valid ISO format                          │
│ ✓ metadata.channel must be SMS/WhatsApp/Email/Chat                    │
│ ✓ conversationHistory items validated recursively                      │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                            Validation Failed?
                            ┌───────┴───────┐
                            │               │
                           YES              NO
                            │               │
                            ▼               ▼
                   ┌─────────────┐   Continue to
                   │ 422 Error   │   Processing
                   │ with detail │
                   └─────────────┘
```

### Middleware Processing

#### API Key Authentication (`src/api/middleware.py`)

```python
class APIKeyMiddleware:
    """
    Validates X-API-Key header for protected endpoints.
    
    Exempt paths (no auth required):
    - /health
    - /docs, /openapi.json, /redoc
    - / (web UI)
    - /static/* (static files)
    """
    
    # Flow:
    # 1. Check if path is exempt
    # 2. Extract X-API-Key from headers
    # 3. Compare with settings.api_key
    # 4. Return 401/403 on failure, continue on success
```

#### Request Timing Middleware

```python
class RequestTimingMiddleware:
    """
    Tracks request processing time.
    
    Adds X-Process-Time header to response:
    X-Process-Time: 0.7234 (seconds)
    """
```

---

## 6. Stage 2: Hybrid Scam Detection

### Why Hybrid Detection?

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    REGEX-ONLY LIMITATIONS                               │
├─────────────────────────────────────────────────────────────────────────┤
│ ❌ Misses obfuscated data ("nine eight seven..." spelled out)           │
│ ❌ Cannot understand contextual references ("same account as before")   │
│ ❌ Fails on non-standard formats scammers may use                       │
│ ❌ No semantic understanding of implicit threats                        │
│ ❌ Multi-stage scams look benign initially                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    HYBRID APPROACH BENEFITS                             │
├─────────────────────────────────────────────────────────────────────────┤
│ ✅ Regex: Fast (~10ms), deterministic, catches standard patterns        │
│ ✅ AI: Semantic understanding, context-aware, catches sophisticated scams│
│ ✅ Combined: Maximum detection accuracy with minimal latency            │
│ ✅ Fallback: Regex provides baseline if AI fails                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Detection Pipeline

```
                         Incoming Message
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 2A: REGEX PRE-FILTER                           │
│                         (~10ms, no cost)                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Pattern Categories Checked:                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ URGENCY: "immediately", "urgent", "within X hours"              │   │
│  │ AUTHORITY: "RBI", "SBI", "cyber cell", "government"             │   │
│  │ THREAT: "blocked", "suspended", "legal action", "arrest"        │   │
│  │ REQUEST: "OTP", "PIN", "CVV", "verify", "KYC"                   │   │
│  │ FINANCIAL: "transfer money", "pay now", "UPI ID"                │   │
│  │ PHISHING: suspicious URLs, URL shorteners                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Result Classification:                                                 │
│  ┌────────────────┬────────────────────────────────────────────────┐   │
│  │ OBVIOUS_SCAM   │ High-weight patterns matched (e.g., "send OTP")│   │
│  │ OBVIOUS_SAFE   │ Matches safe patterns (e.g., actual OTP msg)   │   │
│  │ UNCERTAIN      │ Needs AI analysis                              │   │
│  └────────────────┴────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
    OBVIOUS_SCAM            UNCERTAIN               OBVIOUS_SAFE
          │                       │                       │
          ▼                       ▼                       ▼
   ┌─────────────┐     ┌─────────────────┐      ┌─────────────────┐
   │ Skip AI     │     │ Continue to     │      │ Skip AI         │
   │ conf=0.95   │     │ AI Classifier   │      │ conf=0.05       │
   │ Engage now! │     │                 │      │ Return neutral  │
   └─────────────┘     └────────┬────────┘      └─────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 2B: AI CLASSIFICATION                          │
│                  (Gemini 3 Flash, ~150ms, ~$0.0001)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Model: gemini-3-flash-preview (fallback: gemini-2.5-flash)            │
│                                                                         │
│  Prompt Construction:                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ CONVERSATION HISTORY: [last 5 messages for context]             │   │
│  │ NEW MESSAGE: "Your account blocked. Send OTP now!"              │   │
│  │ METADATA: channel=SMS, locale=IN                                │   │
│  │ PREVIOUS ASSESSMENT: is_scam=true, confidence=0.72 (if exists) │   │
│  │                                                                 │   │
│  │ ANALYSIS GUIDELINES:                                            │   │
│  │ 1. Consider conversation ESCALATION patterns                    │   │
│  │ 2. Check for multi-stage scam setup                            │   │
│  │ 3. Look for urgency, threats, data requests                    │   │
│  │ 4. Use FULL context, not just current message                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Configuration:                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ thinking_level: LOW (fast classification, not deep reasoning)  │   │
│  │ temperature: 0.1 (consistent, deterministic outputs)           │   │
│  │ safety_settings: BLOCK_ONLY_HIGH (allow scam content analysis) │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Output (JSON):                                                         │
│  {                                                                      │
│    "is_scam": true,                                                     │
│    "confidence": 0.87,                                                  │
│    "scam_type": "banking_fraud",                                        │
│    "threat_indicators": ["urgency", "otp_request", "account_threat"],   │
│    "reasoning": "Message uses classic OTP phishing pattern..."         │
│  }                                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 2C: CONFIDENCE COMBINATION                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Final confidence = f(AI_confidence, pattern_matches, previous_conf)   │
│                                                                         │
│  Adjustments:                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. Pattern boost: +0.03 per matched pattern (max +0.15)        │   │
│  │ 2. CRITICAL: confidence = max(current, previous)               │   │
│  │    → Confidence can only INCREASE over conversation            │   │
│  │    → Prevents false negative oscillation                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Thresholds:                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ conf < 0.60  → NOT_SCAM (monitoring mode)                      │   │
│  │ conf 0.60-0.85 → CAUTIOUS engagement (10 turns max)            │   │
│  │ conf > 0.85  → AGGRESSIVE engagement (25 turns max)            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Pattern Categories Detail

```python
# File: src/detection/patterns.py

# Each pattern has:
# - category: ScamCategory enum
# - pattern: Compiled regex
# - weight: 0.0-1.0 importance score
# - description: Human-readable explanation

URGENCY_PATTERNS = [
    # "immediately", "urgent", "asap", "right now" → weight 0.7
    # "today", "within X hours" → weight 0.6
    # "hurry", "quickly", "fast" → weight 0.5
    # "last chance", "final warning", "expires" → weight 0.8
]

AUTHORITY_PATTERNS = [
    # Bank names: RBI, SBI, HDFC, ICICI → weight 0.8
    # Government: ministry, police, cyber cell → weight 0.9
    # Support: customer care, helpline → weight 0.5
]

THREAT_PATTERNS = [
    # Account threats: blocked, suspended, deactivated → weight 0.8
    # Legal threats: arrest, legal action, court → weight 0.9
    # Fraud accusations → weight 0.6
]

REQUEST_PATTERNS = [
    # OTP/code requests → weight 0.95 (very high!)
    # Card details: PIN, CVV → weight 0.95
    # Password requests → weight 0.9
    # KYC/verification → weight 0.6-0.7
]
```

---

## 7. Stage 3: Intelligence Extraction

### Hybrid Extraction Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HYBRID EXTRACTION PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────┘

                    Scammer Message (+ full history)
                          │
          ┌───────────────┴───────────────┐
          │                               │
          ▼                               ▼
┌─────────────────────┐       ┌─────────────────────────────────────┐
│   REGEX EXTRACTOR   │       │     AI EXTRACTOR (During Engage)    │
│     (Always runs)   │       │   (Gemini 3 Pro - same call)        │
├─────────────────────┤       ├─────────────────────────────────────┤
│ • Standard formats  │       │ • Structured output extraction      │
│ • 9-18 digit nums   │       │ • Obfuscated numbers               │
│ • user@provider     │       │ • Contextual references            │
│ • +91 phones        │       │ • Implicit information             │
│ • http/https URLs   │       │ • Semantic validation              │
│ ~5ms                │       │ ~0ms extra (piggybacks on engage)  │
└─────────┬───────────┘       └───────────────┬─────────────────────┘
          │                                   │
          └───────────────┬───────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   MERGE & DEDUPLICATE │
              │   • Union of both     │
              │   • Normalize formats │
              │   • Validate entities │
              └───────────────────────┘
```

### Intelligence Types

```python
# File: src/intelligence/patterns.py

class IntelligenceType(str, Enum):
    BANK_ACCOUNT = "bank_account"      # 9-18 digit account numbers
    UPI_ID = "upi_id"                  # username@provider format
    PHONE_NUMBER = "phone_number"      # Indian mobile (6-9 prefix)
    URL = "url"                        # Suspicious/phishing links
    EMAIL = "email"                    # Email addresses
    BENEFICIARY_NAME = "beneficiary_name"  # Account holder names (CRITICAL!)
    BANK_NAME = "bank_name"            # Indian bank names
    IFSC_CODE = "ifsc_code"            # Bank branch codes
    WHATSAPP_NUMBER = "whatsapp_number"  # WhatsApp contact numbers
```

### Extraction Patterns Detail

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE EXTRACTION PATTERNS                      │
└─────────────────────────────────────────────────────────────────────────┘

BANK ACCOUNTS:
├── Plain: \b\d{9,18}\b
│   Example: "123456789012345"
├── Formatted: \b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{0,6}\b
│   Example: "1234-5678-9012-3456"
└── Prefixed: (?:a/c|account|acc)[\s:]*#?\s*(\d{9,18})
    Example: "A/C: 123456789012345"

UPI IDs:
├── Known providers: [\w.-]+@(?:ybl|paytm|okicici|oksbi|...)
│   Example: "john@ybl", "scammer@paytm"
└── Generic: [\w.-]{3,}@[a-zA-Z]{2,15}
    Example: "fraudster@okaxis"

PHONE NUMBERS (Indian):
├── With +91: \+91[-\s]?\d{10}
├── Plain 10-digit: [6-9]\d{9}
├── Formatted: [6-9]\d{2}[-\s]?\d{3}[-\s]?\d{4}
└── With 91 prefix: 91[6-9]\d{9}

BENEFICIARY NAMES (CRITICAL for mule identification):
├── "name shows as 'Name'"
├── "Account Holder: Name"
├── "Transfer to Name"
└── "Name - Title" (e.g., "Rahul Kumar - KYC Support")

WHATSAPP NUMBERS:
├── "WhatsApp: +91 9876543210"
├── "message on WhatsApp 9876543210"
└── wa.me/919876543210 links
```

### Validation Rules

```python
# File: src/intelligence/extractor.py

def _is_valid_bank_account(self, number: str) -> bool:
    """
    Validates bank account numbers:
    - Must be 9-18 digits
    - Cannot be all zeros
    - Cannot be all same digit (e.g., 1111111111)
    """

def _is_valid_phone(self, number: str) -> bool:
    """
    Validates Indian phone numbers:
    - Removes +91/91 prefix
    - Must be exactly 10 digits
    - Must start with 6, 7, 8, or 9
    """

def _is_valid_name(self, name: str) -> bool:
    """
    Validates beneficiary names:
    - Must have at least 2 characters
    - Must contain letters (not just numbers)
    - Excludes common non-names
    """
```

---

## 8. Stage 4: Engagement Policy & Exit Conditions

### Engagement Modes

```python
# File: src/agents/policy.py

class EngagementMode(str, Enum):
    NONE = "none"           # conf < 0.60 - monitoring only
    CAUTIOUS = "cautious"   # conf 0.60-0.85 - limited engagement
    AGGRESSIVE = "aggressive"  # conf > 0.85 - full engagement
```

### High-Value Intelligence Completion

```
┌─────────────────────────────────────────────────────────────────────────┐
│                HIGH-VALUE INTELLIGENCE CHECK                             │
│                                                                          │
│  Intelligence is COMPLETE when we have ALL of:                          │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ ✓ (Bank Account OR UPI ID) - payment destination                │    │
│  │ ✓ AND Phone Number - scammer contact                           │    │
│  │ ✓ AND Beneficiary Name - mule account holder identity          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Why beneficiary name is CRITICAL:                                      │
│  • Identifies the actual mule account holder                            │
│  • Essential for law enforcement to trace money trail                   │
│  • Without it, bank account alone is less actionable                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Exit Conditions

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXIT CONDITION EVALUATION                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Check order (first match triggers exit):                               │
│                                                                          │
│  1. MAX TURNS REACHED                                                   │
│     ┌──────────────────────────────────────────────────────────────┐   │
│     │ CAUTIOUS mode: 10 turns max                                   │   │
│     │ AGGRESSIVE mode: 25 turns max                                 │   │
│     │ Reason: "Max turns reached (10)" or "Max turns reached (25)" │   │
│     └──────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  2. MAX DURATION EXCEEDED                                               │
│     ┌──────────────────────────────────────────────────────────────┐   │
│     │ 600 seconds (10 minutes) maximum                              │   │
│     │ Reason: "Max duration exceeded (600s)"                        │   │
│     └──────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  3. INTELLIGENCE COMPLETE                                               │
│     ┌──────────────────────────────────────────────────────────────┐   │
│     │ All high-value intel extracted (bank/UPI + phone + name)     │   │
│     │ Reason: "Intelligence extraction complete"                    │   │
│     │ EXIT RESPONSE: Random polite excuse                          │   │
│     └──────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  4. SCAMMER SUSPICIOUS                                                  │
│     ┌──────────────────────────────────────────────────────────────┐   │
│     │ Detected when scammer becomes hostile/distrustful            │   │
│     │ Reason: "Scammer became suspicious"                          │   │
│     └──────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  5. STALE CONVERSATION                                                  │
│     ┌──────────────────────────────────────────────────────────────┐   │
│     │ No new intelligence in 5+ consecutive turns                  │   │
│     │ Reason: "No new information in 5 turns"                      │   │
│     └──────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Exit Responses

```python
# When high-value intelligence is complete, use these believable excuses:
EXIT_RESPONSES = [
    "okay i am calling that number now, hold on...",
    "wait my son just came home, let me ask him to help me with this",
    "one second, someone is at the door, i will call you back",
    "okay i sent the money, now my phone is dying, i need to charge it",
    "hold on, i am getting another call from my bank, let me check",
]
```

---

## 9. Stage 5: AI Agent Engagement

### HoneypotAgent Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HONEYPOT AGENT COMPONENTS                             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         HoneypotAgent                                    │
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │ PersonaManager  │  │ EngagementPolicy│  │ FakeDataGenerator       │  │
│  │                 │  │                 │  │                         │  │
│  │ • Emotional     │  │ • Mode routing  │  │ • Credit cards          │  │
│  │   state machine │  │ • Exit checks   │  │ • Bank accounts         │  │
│  │ • Turn-based    │  │ • Intel check   │  │ • OTPs, Aadhaar, PAN   │  │
│  │   adaptation    │  │ • Thresholds    │  │ • Persona details       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Gemini 3 Pro Client                          │    │
│  │  Primary: gemini-3-pro-preview                                  │    │
│  │  Fallback: gemini-2.5-pro                                       │    │
│  │  Config:                                                        │    │
│  │    • thinking_level: HIGH (deep reasoning for believable text) │    │
│  │    • safety_settings: BLOCK_NONE (allow scam roleplay)         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Persona Management

```python
# File: src/agents/persona.py

class EmotionalState(str, Enum):
    CALM = "calm"           # Default, early conversation
    ANXIOUS = "anxious"     # Worried, mid-conversation
    PANICKED = "panicked"   # Very scared, high-pressure scams
    RELIEVED = "relieved"   # Lottery/reward scams
    SUSPICIOUS = "suspicious"  # Use sparingly, late conversation only
```

### Emotional State Mapping

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EMOTIONAL STATE TRANSITIONS                           │
└─────────────────────────────────────────────────────────────────────────┘

Scam Type Detection → Emotional Response:

banking_fraud, account_threat:
    ├── conf < 0.5  → CALM
    ├── conf 0.5-0.8 → ANXIOUS
    └── conf > 0.8  → PANICKED

job_offer, recruitment:
    └── Any conf → ANXIOUS (interested but worried)

lottery, prize, reward:
    └── Any conf → RELIEVED (excited/hopeful)

police, government, authority:
    └── Any conf → ANXIOUS (worried about authority)

Turn-based modifiers:
    Turn 1-2: "what is this about?", "i dont understand"
    Turn 3-5: "this is concerning", "what should i do"
    Turn 6+:  "ok i will try", "let me see if i can do this"
```

### Fake Data Generation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FAKE DATA STRATEGY                                    │
│                                                                          │
│  Purpose: Make the victim appear compliant while buying time             │
│                                                                          │
│  Key Features:                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • Luhn-valid card numbers (pass format checks, fail transactions)│    │
│  │ • Realistic IFSC codes (valid bank prefix, fake branch)         │    │
│  │ • Indian elderly names (typical scam targets)                   │    │
│  │ • Consistent across conversation (seeded by conversation_id)    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Generated Data:                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Credit Card: 4000 1234 5678 9012 (Luhn-valid, invalid BIN)     │    │
│  │ Expiry: 08/27                                                   │    │
│  │ CVV: 456                                                        │    │
│  │ Bank Account: 12345678901234 (valid format)                    │    │
│  │ IFSC: SBIN0999999 (valid prefix, fake branch)                  │    │
│  │ OTP: 847291                                                     │    │
│  │ Aadhaar: 2345 6789 0123                                        │    │
│  │ PAN: ABCDE1234F                                                │    │
│  │ Name: Kamala Sharma                                            │    │
│  │ Age: 63                                                        │    │
│  │ Address: 45, Gandhi Nagar, Mumbai                              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ALWAYS follow fake data with extraction question:                       │
│  "ok my card number is [CARD]. what name should appear on your side?"   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### System Prompt Structure

```python
# File: src/agents/prompts.py

HONEYPOT_SYSTEM_PROMPT = """
## Your Persona
- Middle-aged, not very tech-savvy, trusting of authority figures
- Emotional state: {emotional_state}

## Engagement Strategy
1. Show concern but confusion
2. Request specifics (extract intel)
3. Express willingness to comply
4. Delay tactics
5. Feign technical difficulties

## CRITICAL RULES
- NEVER reveal you know it's a scam
- NEVER use security terms like "phishing", "fraud"
- DO ask for payment details "to verify"
- DO make small mistakes requiring re-explanation

## VARIATION RULES
- Do NOT repeat same opening phrases
- Type like elderly person: lowercase, simple, occasional typos
- Vary based on turn number

## Intelligence Targets
- Bank accounts
- UPI IDs
- Phone numbers
- Links
- BENEFICIARY NAME (CRITICAL - always ask for name when you have UPI/account)

## FAKE DATA STRATEGY
When asked for sensitive data, GIVE IT using provided fake values.
{fake_data_section}
ALWAYS follow with question to extract more intel.
"""
```

### Targeted Extraction Directives

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXTRACTION DIRECTIVE GENERATION                       │
│                                                                          │
│  Based on what's MISSING, the prompt includes specific instructions:     │
│                                                                          │
│  Missing: beneficiary_name (have UPI)                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ **CRITICAL EXTRACTION TARGET: BENEFICIARY NAME**                │    │
│  │ You have the UPI "scammer@ybl" but NOT the account holder name. │    │
│  │ Use the "validation attack" - pretend you need to verify name.  │    │
│  │ Example: "i am typing scammer@ybl... what name should pop up?"  │    │
│  │ DO NOT exit until you get the name!                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Missing: payment_details                                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ **EXTRACTION TARGET: PAYMENT DETAILS**                          │    │
│  │ Ask naturally: "where should i send the money?"                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Missing: phone_number                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ **EXTRACTION TARGET: PHONE NUMBER**                             │    │
│  │ Ask: "what number can i call if i have problem?"                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Stage 6: Response Generation

### Response Building Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RESPONSE GENERATION FLOW                              │
└─────────────────────────────────────────────────────────────────────────┘

               ┌───────────────────────────────────────┐
               │ Collected Data:                       │
               │ • Detection result (confidence, type) │
               │ • Extracted intelligence              │
               │ • Agent response text                 │
               │ • Engagement state                    │
               │ • Turn number                         │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    BUILD API RESPONSE                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  AnalyzeResponse:                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ status: "success"                                               │    │
│  │ scamDetected: true                                              │    │
│  │                                                                 │    │
│  │ engagementMetrics:                                              │    │
│  │   engagementDurationSeconds: 2                                  │    │
│  │   totalMessagesExchanged: 5                                     │    │
│  │                                                                 │    │
│  │ extractedIntelligence:                                          │    │
│  │   bankAccounts: ["12345678901234"]                             │    │
│  │   upiIds: ["scammer@ybl"]                                      │    │
│  │   phoneNumbers: ["9876543210"]                                 │    │
│  │   phishingLinks: ["http://bit.ly/fake"]                        │    │
│  │                                                                 │    │
│  │ agentNotes: "Mode: aggressive | Intel: bank+phone | Turn: 5"   │    │
│  │ agentResponse: "ok i am typing 9876543210... what name shows?" │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Final Response Schema

```json
{
  "status": "success",
  "scamDetected": true,
  "engagementMetrics": {
    "engagementDurationSeconds": 2,
    "totalMessagesExchanged": 5
  },
  "extractedIntelligence": {
    "bankAccounts": ["12345678901234"],
    "upiIds": ["scammer@ybl"],
    "phoneNumbers": ["9876543210"],
    "phishingLinks": ["http://bit.ly/fake-bank"]
  },
  "agentNotes": "Mode: aggressive | Intel: bank+phone+upi extracted | Turn: 5 | Still need: beneficiary_name",
  "agentResponse": "ok i am typing scammer@ybl in my app... what name should it show? want to make sure before sending"
}
```

---

## 11. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE DATA FLOW                                    │
└─────────────────────────────────────────────────────────────────────────┘

     CLIENT                    STICKY-NET                     GOOGLE AI
        │                          │                              │
        │  POST /api/v1/analyze    │                              │
        │ ─────────────────────────▶                              │
        │  {message, history}      │                              │
        │                          │                              │
        │                    ┌─────┴─────┐                        │
        │                    │ Middleware │                        │
        │                    │ • Auth     │                        │
        │                    │ • Timing   │                        │
        │                    └─────┬─────┘                        │
        │                          │                              │
        │                    ┌─────┴─────┐                        │
        │                    │ Regex     │                        │
        │                    │ Pre-filter│                        │
        │                    └─────┬─────┘                        │
        │                          │                              │
        │                          │ (if uncertain)               │
        │                          │                              │
        │                          │  classify(message)           │
        │                          │ ─────────────────────────────▶
        │                          │                              │
        │                          │  {is_scam, confidence}       │
        │                          │ ◀─────────────────────────────
        │                          │                              │
        │                    ┌─────┴─────┐                        │
        │                    │ Intel     │                        │
        │                    │ Extractor │                        │
        │                    └─────┬─────┘                        │
        │                          │                              │
        │                          │ (if scam detected)           │
        │                          │                              │
        │                          │  engage(message, persona)    │
        │                          │ ─────────────────────────────▶
        │                          │                              │
        │                          │  {response_text}             │
        │                          │ ◀─────────────────────────────
        │                          │                              │
        │  {scamDetected: true,    │                              │
        │   agentResponse: "...",  │                              │
        │   intelligence: {...}}   │                              │
        │ ◀─────────────────────────                              │
        │                          │                              │
```

---

## 12. Component Deep Dives

### 12.1 ScamDetector (`src/detection/detector.py`)

```python
class ScamDetector:
    """
    Hybrid scam detector combining regex pre-filter with AI classification.
    
    Key Methods:
    - analyze(): Main entry point for message analysis
    - _combine_confidence(): Merges AI + pattern confidence
    - _calculate_category_scores(): Aggregates pattern weights by category
    
    Important Constants:
    - SCAM_THRESHOLD = 0.6 (minimum confidence to flag as scam)
    - OBVIOUS_SCAM_CONFIDENCE = 0.95 (confidence for regex fast-path scams)
    - OBVIOUS_SAFE_CONFIDENCE = 0.05 (confidence for allowlisted messages)
    """
```

### 12.2 ScamClassifier (`src/detection/classifier.py`)

```python
class ScamClassifier:
    """
    AI-based scam classifier using Gemini 3 Flash.
    
    Features:
    - Primary model: gemini-3-flash-preview
    - Fallback model: gemini-2.5-flash (if primary fails)
    - Low thinking level for speed
    - Context-aware (uses conversation history)
    
    Safety Settings:
    - BLOCK_ONLY_HIGH for all harm categories
    - Allows analysis of scam content without triggering safety blocks
    """
```

### 12.3 IntelligenceExtractor (`src/intelligence/extractor.py`)

```python
class IntelligenceExtractor:
    """
    Regex-based intelligence extraction.
    
    Extraction Methods:
    - _extract_bank_accounts(): 9-18 digit numbers (excludes phone numbers)
    - _extract_upi_ids(): username@provider patterns
    - _extract_phone_numbers(): Indian mobile formats
    - _extract_beneficiary_names(): Account holder names
    - _extract_urls(): Suspicious/phishing links
    - _extract_whatsapp_numbers(): WhatsApp-specific contacts
    
    Validation:
    - Luhn check for card numbers (if implementing)
    - Phone prefix validation (must start with 6-9)
    - Name validation (excludes non-name patterns)
    """
```

### 12.4 HoneypotAgent (`src/agents/honeypot_agent.py`)

```python
class HoneypotAgent:
    """
    AI agent that engages scammers with believable human persona.
    
    Key Components:
    - PersonaManager: Manages emotional state and behavior
    - EngagementPolicy: Determines engagement mode and exit conditions
    - FakeDataGenerator: Provides fake financial data
    
    Gemini Configuration:
    - Primary model: gemini-3-pro-preview
    - Fallback: gemini-2.5-pro
    - Thinking level: HIGH (for sophisticated reasoning)
    - Safety: BLOCK_NONE (allows scam roleplay)
    
    Response Strategy:
    - Build targeted extraction directives based on missing intel
    - Include fake data for apparent compliance
    - Vary emotional tone based on scam type and turn number
    """
```

### 12.5 PersonaManager (`src/agents/persona.py`)

```python
class PersonaManager:
    """
    Manages persona state across conversation turns.
    
    Emotional States:
    - CALM: Default, early conversation
    - ANXIOUS: Worried, mid-conversation
    - PANICKED: Very scared (high-confidence banking scams)
    - RELIEVED: Lottery/reward scams
    - SUSPICIOUS: Used sparingly, late conversation
    
    Persona Traits:
    - TRUSTING, WORRIED, TECH_NAIVE (default)
    - Influences response style and extraction probability
    """
```

### 12.6 FakeDataGenerator (`src/agents/fake_data.py`)

```python
class FakeDataGenerator:
    """
    Generates believable but invalid financial data.
    
    Features:
    - Luhn-valid credit card numbers (pass format checks, fail transactions)
    - Real bank IFSC prefixes with fake branch codes
    - Elderly Indian names (typical scam targets)
    - Consistent data per conversation (seeded by conversation_id)
    
    Generated Data Types:
    - Credit cards (Visa, Mastercard, RuPay)
    - Bank accounts with IFSC
    - OTPs, Aadhaar, PAN
    - Persona details (name, age, address)
    """
```

---

## 13. Error Handling

### Exception Hierarchy

```python
# File: src/exceptions.py

class StickyNetError(Exception):
    """Base exception for all Sticky-Net errors."""

class ScamDetectionError(StickyNetError):
    """Error during scam detection stage."""

class AgentEngagementError(StickyNetError):
    """Error during agent engagement."""

class IntelligenceExtractionError(StickyNetError):
    """Error during intelligence extraction."""

class ConfigurationError(StickyNetError):
    """Error in configuration or environment."""
```

### Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ERROR HANDLING STRATEGY                               │
└─────────────────────────────────────────────────────────────────────────┘

AI Classification Failure:
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Try primary model (gemini-3-flash-preview)                          │
│ 2. On failure, try fallback model (gemini-2.5-flash)                   │
│ 3. If both fail, return uncertain result (confidence=0.5)              │
│ 4. Continue with regex-based detection                                 │
└────────────────────────────────────────────────────────────────────────┘

AI Engagement Failure:
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Try primary model (gemini-3-pro-preview)                            │
│ 2. On failure, try fallback model (gemini-2.5-pro)                     │
│ 3. If both fail, return fallback response from templates               │
└────────────────────────────────────────────────────────────────────────┘

Request Validation Failure:
┌────────────────────────────────────────────────────────────────────────┐
│ • Pydantic validation errors → 422 Unprocessable Entity               │
│ • Missing API key → 401 Unauthorized                                  │
│ • Invalid API key → 403 Forbidden                                     │
└────────────────────────────────────────────────────────────────────────┘

Internal Errors:
┌────────────────────────────────────────────────────────────────────────┐
│ • StickyNetError → 500 with error message                             │
│ • Unexpected Exception → 500 "Internal server error" (no details)     │
│ • All errors logged with structured context                           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Configuration & Settings

### Environment Variables

```bash
# Required
API_KEY=your-secure-api-key
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Optional with defaults
PORT=8080
DEBUG=false
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=true

# AI Models (defaults to Gemini 3 with 2.5 fallback)
FLASH_MODEL=gemini-3-flash-preview
PRO_MODEL=gemini-3-pro-preview
FALLBACK_FLASH_MODEL=gemini-2.5-flash
FALLBACK_PRO_MODEL=gemini-2.5-pro
LLM_TEMPERATURE=0.7

# Engagement Policy
MAX_ENGAGEMENT_TURNS_CAUTIOUS=10
MAX_ENGAGEMENT_TURNS_AGGRESSIVE=25
MAX_ENGAGEMENT_DURATION_SECONDS=600
CAUTIOUS_CONFIDENCE_THRESHOLD=0.60
AGGRESSIVE_CONFIDENCE_THRESHOLD=0.85

# Firestore (optional)
FIRESTORE_COLLECTION=conversations
FIRESTORE_EMULATOR_HOST=localhost:8080  # For local development
```

### Settings Class

```python
# File: config/settings.py

class Settings(BaseSettings):
    """
    Application configuration with Pydantic validation.
    
    Features:
    - Loads from environment variables
    - Loads from .env file (local development)
    - Type validation and defaults
    - Cached singleton instance via @lru_cache
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
```

---

## 15. Security Considerations

### API Security

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SECURITY MEASURES                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  API Key Authentication:                                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • X-API-Key header required for /api/v1/* endpoints            │    │
│  │ • Constant-time comparison to prevent timing attacks            │    │
│  │ • Keys stored in environment, never in code                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  CORS Configuration:                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • DEBUG=true: Allow all origins (development only)             │    │
│  │ • DEBUG=false: Restrictive CORS (production)                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Documentation Access:                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • /docs, /redoc: Only accessible when DEBUG=true               │    │
│  │ • Hidden in production to reduce attack surface                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Input Validation:                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • Message text: 1-5000 characters                              │    │
│  │ • Sender type: Enum validation                                 │    │
│  │ • Timestamp: ISO format validation                             │    │
│  │ • Pydantic models prevent injection attacks                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Credential Protection:                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • Service account JSON in secrets/ directory                   │    │
│  │ • .gitignore excludes credentials                              │    │
│  │ • Environment variables for sensitive config                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  AI Safety Settings:                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • Classifier: BLOCK_ONLY_HIGH (allows scam analysis)           │    │
│  │ • Agent: BLOCK_NONE (allows scam roleplay for honeypot)        │    │
│  │ • These settings are essential for the system to function      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Fake Data Security

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FAKE DATA SAFEGUARDS                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Credit Cards:                                                          │
│  • Invalid BIN prefixes (won't match real banks)                       │
│  • Luhn-valid (pass format checks, fail processing)                    │
│  • Test BINs: 400000, 411111, etc.                                     │
│                                                                          │
│  Bank Accounts:                                                         │
│  • Real bank IFSC prefixes (SBIN, HDFC, etc.)                         │
│  • Fake branch codes (0999999)                                         │
│  • Numbers that won't match real accounts                              │
│                                                                          │
│  Purpose:                                                               │
│  • Appear legitimate to scammers                                       │
│  • Cannot be used for actual fraud                                     │
│  • Buy time while extracting real intelligence                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Summary

### Request Flow Summary

```
1. REQUEST RECEIVED
   └─▶ Middleware validates API key
   
2. DETECTION PHASE
   ├─▶ Regex pre-filter checks obvious patterns (~10ms)
   ├─▶ If uncertain, AI classifier analyzes semantically (~150ms)
   └─▶ Confidence score determined (can only increase)

3. EXTRACTION PHASE
   └─▶ Regex extracts all intelligence types (~5ms)

4. POLICY DECISION
   ├─▶ If high-value intel complete → EXIT with polite excuse
   └─▶ If intel incomplete → CONTINUE engagement

5. ENGAGEMENT PHASE (if continuing)
   ├─▶ PersonaManager determines emotional state
   ├─▶ FakeDataGenerator provides compliant-looking data
   ├─▶ Extraction directives target missing intel
   └─▶ Gemini 3 Pro generates believable response (~500ms)

6. RESPONSE RETURNED
   └─▶ Full intelligence + agent response + metrics
```

### Key Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Never break character** | Agent never reveals scam awareness |
| **Confidence monotonicity** | Confidence can only increase |
| **Prioritize beneficiary names** | Critical for mule identification |
| **Hybrid detection** | Fast regex + smart AI |
| **Fake data compliance** | Appear cooperative, extract intel |
| **Graceful degradation** | Fallback models when primary fails |
| **Targeted extraction** | Directives based on missing intel |

---

*Document generated: January 24, 2026*
*Version: 1.0*
*Author: Sticky-Net Development Team*
