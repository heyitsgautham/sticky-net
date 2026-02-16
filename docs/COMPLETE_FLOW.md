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
│    ┌────────────────────────────────────────────────────────────┐       │
│    │ AI Classifier (Gemini 3 Flash)                             │       │
│    │ (~150ms, context-aware)                                    │       │
│    │ • Semantic Analysis with conversation history              │       │
│    │ • Confidence Scoring (0.0 to 1.0)                          │       │
│    │ • Scam Type Classification                                 │       │
│    │ • Model: gemini-3-flash-preview                            │       │
│    │ • Fallback: gemini-2.5-flash                               │       │
│    └────────────────────────────────────────────────────────────┘       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE EXTRACTION (Regex)                       │
│    ┌───────────────────────────────────────────────────────────────┐    │
│    │ Regex-based extraction (runs on ALL messages, ~5ms)          │    │
│    │ • Bank Accounts (9-18 digits)                                 │    │
│    │ • UPI IDs (username@provider)                                 │    │
│    │ • Phone Numbers (Indian: 6-9 prefix, 10 digits)              │    │
│    │ • Beneficiary Names (account holder names)                    │    │
│    │ • IFSC Codes, WhatsApp Numbers                               │    │
│    │ • Phishing Links (suspicious URLs)                           │    │
│    └───────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
        ┌────────────────────────┴────────────────────────┐
        │                                                  │
    Not Scam (conf < 0.6)                          Is Scam (conf ≥ 0.6)
        │                                                  │
        ▼                                                  ▼
┌───────────────────┐                    ┌─────────────────────────────────┐
│ Return neutral    │                    │ ENGAGEMENT POLICY CHECK         │
│ response          │                    │ • High-value intel complete?    │
│ Continue monitor  │                    │   → Exit with polite excuse     │
└───────────────────┘                    │ • Max turns/duration reached?   │
                                         │   → Exit with excuse            │
                                         │ • Still missing intel?          │
                                         │   → Continue engagement         │
                                         └─────────────────────────────────┘
                                                           │
                                                           ▼
                                         ┌─────────────────────────────────┐
                                         │ AI ENGAGEMENT AGENT             │
                                         │ (Gemini 3 Flash, One-Pass JSON) │
                                         │ • Persona: Pushpa Verma (65+)   │
                                         │ • Fake data generation          │
                                         │ • Targeted extraction prompts   │
                                         │ • Believable human responses    │
                                         │ • Returns reply + LLM intel     │
                                         └─────────────────────────────────┘
                                                           │
                                                           ▼
                                         ┌─────────────────────────────────┐
                                         │ INTELLIGENCE MERGE              │
                                         │ • Validate LLM intel with regex │
                                         │ • Merge regex + validated LLM   │
                                         │ • Deduplicate all fields        │
                                         └─────────────────────────────────┘
                                                           │
                                                           ▼
                                         ┌─────────────────────────────────┐
                                         │ RESPONSE BUILDER                │
                                         │ • Format API response           │
                                         │ • Include merged intel          │
                                         │ • Return agent notes            │
                                         └─────────────────────────────────┘
```

---

## 3. Request Lifecycle

### Complete Request Journey

```
Time ──────────────────────────────────────────────────────────────────────▶

│ T+0ms       │ T+5ms         │ T+15ms        │ T+200ms       │ T+210ms     │ T+710ms     │
│             │               │               │               │             │             │
▼             ▼               ▼               ▼               ▼             ▼             ▼
┌─────────┐   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ ┌───────────┐
│ Request │──▶│ Middleware  │─▶│ Regex       │─▶│ AI Class.  │─▶│ Regex     │─▶│ Agent     │
│ Arrives │   │ Auth+Timer  │ │ Pre-filter  │ │ (if needed) │ │ Extraction│ │ One-Pass  │
└─────────┘   └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ └─────┬─────┘
                                                                                  │
                                                               ┌──────────────────┘
                                                               ▼
                                                        ┌─────────────┐
                                                        │ Merge Intel │
                                                        │ (LLM+Regex) │
                                                        └──────┬──────┘
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
| AI Classification | ~150ms | Gemini 3 Flash semantic analysis |
| Regex Extraction | ~5ms | Fast, deterministic intel extraction |
| Policy Check | ~1ms | Exit condition evaluation |
| AI Engagement (One-Pass) | ~500ms | Gemini 3 Flash returns reply + LLM extraction |
| Intel Merge | ~2ms | Validate LLM intel with regex, merge, dedupe |
| **Total (scam)** | **~660ms** | Full pipeline with One-Pass JSON |
| **Total (safe)** | **~160ms** | Early exit for non-scam messages |

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

## 6. Stage 2: AI Scam Detection

### Why AI-Only Detection?

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AI-ONLY DETECTION BENEFITS                           │
├─────────────────────────────────────────────────────────────────────────┤
│ ✅ Simpler architecture — single detection path                        │
│ ✅ Semantic understanding of context and conversation flow             │
│ ✅ Catches multi-stage scams that start benign                         │
│ ✅ Context-aware — uses full conversation history                      │
│ ✅ Handles obfuscated data ("nine eight seven..." spelled out)         │
│ ✅ Understands implicit threats and manipulation tactics               │
│ ✅ Scam type classification for persona adaptation                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Detection Pipeline

```
                         Incoming Message
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    AI CLASSIFICATION                                     │
│               (Gemini 3 Flash, ~150ms)                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Model: gemini-3-flash-preview (fallback: gemini-2.5-flash)            │
│                                                                         │
│  Configuration:                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ temperature: 0.1 (deterministic outputs)                        │   │
│  │ max_output_tokens: 10000                                        │   │
│  │ timeout: 90 seconds                                             │   │
│  │ max_retries: 2                                                  │   │
│  │ retry_delay: 1.0 seconds                                        │   │
│  │ safety_settings: BLOCK_ONLY_HIGH (all harm categories)          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Prompt Construction:                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ CONVERSATION HISTORY: [full context]                            │   │
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
│  Output (JSON):                                                         │
│  {                                                                      │
│    "is_scam": true,                                                     │
│    "confidence": 0.87,                                                  │
│    "scam_type": "banking_fraud",                                        │
│    "threat_indicators": ["urgency", "otp_request", "account_threat"],   │
│    "reasoning": "Message uses classic OTP phishing pattern..."         │
│  }                                                                      │
│                                                                         │
│  Scam Types:                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ job_offer: Part-time job, work from home, YouTube liking        │   │
│  │ banking_fraud: KYC update, account blocked, verify account      │   │
│  │ lottery_reward: Lottery winner, reward points, cashback         │   │
│  │ impersonation: Police, CBI, bank official impersonation         │   │
│  │ others: Any scam that doesn't fit above categories              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CONFIDENCE ESCALATION                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  CRITICAL: confidence = max(current, previous)                         │
│  → Confidence can only INCREASE over conversation                      │
│  → Prevents false negative oscillation                                 │
│                                                                         │
│  Thresholds:                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ conf < 0.60  → NOT_SCAM (return neutral response)              │   │
│  │ conf 0.60-0.85 → CAUTIOUS engagement (10 turns max)            │   │
│  │ conf ≥ 0.85  → AGGRESSIVE engagement (25 turns max)            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```
---

## 7. Stage 3: Intelligence Extraction

### Hybrid Extraction Architecture (One-Pass JSON)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HYBRID EXTRACTION PIPELINE                            │
│                       (One-Pass JSON Architecture)                       │
└─────────────────────────────────────────────────────────────────────────┘

                         Scammer Message
                               │
                               ▼
                    ┌─────────────────────┐
                    │  REGEX EXTRACTION   │  ◀── Fast, deterministic (~5ms)
                    │  (Runs FIRST)       │
                    ├─────────────────────┤
                    │ • Bank accounts     │
                    │ • UPI IDs           │
                    │ • Phone numbers     │
                    │ • URLs              │
                    │ • IFSC codes        │
                    └──────────┬──────────┘
                               │
                               ▼
         ┌─────────────────────────────────────────────────┐
         │     AGENT (Gemini 3 Pro) - ONE-PASS JSON        │
         │     Returns BOTH in single call (~500ms):       │
         ├─────────────────────────────────────────────────┤
         │ {                                               │
         │   "reply_text": "oh no what do i do...",       │
         │   "emotional_tone": "panicked",                │
         │   "extracted_intelligence": {                  │
         │     "bank_accounts": [...],                    │
         │     "upi_ids": [...],                          │
         │     "phone_numbers": [...],                    │
         │     "beneficiary_names": [...],                │
         │     "urls": [...],                             │
         │     "crypto_addresses": [...],                 │
         │     "other_critical_info": [                   │
         │       {"label": "TeamViewer ID", "value": ...}│
         │     ]                                          │
         │   }                                            │
         │ }                                              │
         └──────────────────────┬──────────────────────────┘
                                │
                                ▼
         ┌─────────────────────────────────────────────────┐
         │  VALIDATE LLM EXTRACTION WITH REGEX             │
         │  • UPI IDs must match user@provider pattern     │
         │  • IFSC codes must match [A-Z]{4}0[A-Z0-9]{6}  │
         │  • Bank accounts must be 9-18 digits            │
         │  • Phone numbers must start with 6-9            │
         └──────────────────────┬──────────────────────────┘
                                │
                                ▼
         ┌─────────────────────────────────────────────────┐
         │  MERGE & DEDUPLICATE                            │
         │  • Union of regex + validated LLM results       │
         │  • Normalize formats (strip whitespace, etc.)   │
         │  • Remove duplicates                            │
         └──────────────────────┬──────────────────────────┘
                                │
                                ▼
                         Final Response
                    (Merged intelligence used
                     for exit checks + API response)
```

### Benefits of One-Pass JSON Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ONE-PASS JSON BENEFITS                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ✅ LOWER LATENCY                                                       │
│     • Single LLM call: ~500ms (vs ~650ms with separate calls)           │
│     • No orchestration overhead between engagement + extraction         │
│                                                                          │
│  ✅ CONTEXT-AWARE REPLIES                                               │
│     • Reply text can naturally reference extracted intel                │
│     • "i am sending to [extracted UPI]... what name shows?"             │
│                                                                          │
│  ✅ SIMPLER ARCHITECTURE                                                │
│     • No call orchestration needed                                      │
│     • Single prompt, single response parsing                            │
│     • Easier to debug and maintain                                      │
│                                                                          │
│  ✅ HYBRID VALIDATION                                                   │
│     • LLM catches obfuscated data ("nine eight seven...")              │
│     • Regex validates structured fields (UPI, IFSC)                     │
│     • Best of both worlds                                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
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
    CRYPTO_ADDRESS = "crypto_address"  # Bitcoin, Ethereum, etc. wallets
    OTHER_CRITICAL = "other_critical"  # Ad-hoc high-value data
```

### Extended Intelligence Fields (One-Pass JSON)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXTENDED INTELLIGENCE SCHEMA                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  extracted_intelligence: {                                              │
│    // Standard fields (regex + LLM validated)                           │
│    bank_accounts: ["12345678901234"],                                   │
│    upi_ids: ["scammer@ybl"],                                            │
│    phone_numbers: ["+91-9876543210"],                                   │
│    beneficiary_names: ["Rahul Kumar"],                                  │
│    urls: ["http://fake-bank.com/verify"],                               │
│    whatsapp_numbers: ["+91-8888899999"],                                │
│    ifsc_codes: ["SBIN0001234"],                                         │
│                                                                          │
│    // NEW: Dedicated crypto field                                       │
│    crypto_addresses: [                                                  │
│      "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",  // Bitcoin         │
│      "0x742d35Cc6634C0532925a3b844Bc9e7595f..."     // Ethereum        │
│    ],                                                                    │
│                                                                          │
│    // NEW: Flexible field for ad-hoc high-value data                    │
│    other_critical_info: [                                               │
│      {"label": "TeamViewer ID", "value": "123 456 789"},               │
│      {"label": "AnyDesk ID", "value": "987654321"},                    │
│      {"label": "Reference Number", "value": "TXN20260125001"},         │
│      {"label": "Ticket ID", "value": "SUPPORT-789456"}                 │
│    ]                                                                     │
│  }                                                                       │
│                                                                          │
│  PURPOSE of other_critical_info:                                        │
│  • Captures high-value data that doesn't fit standard fields            │
│  • LLM uses judgment to identify scammer-provided identifiers           │
│  • Examples: remote desktop IDs, reference numbers, case IDs            │
│  • Each entry has label + value for flexible categorization             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
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
├── Prefixed: (?:a/c|account|acc)[\s:]*#?\s*(\d{9,18})
│   Example: "A/C: 123456789012345"
└── Validation:
    • 9-18 digits
    • Not all same digit (e.g., not 1111111111)
    • Not phone-like (10-12 digits starting 6-9)

UPI IDs:
├── Known providers: [\w.-]+@(?:ybl|paytm|okicici|oksbi|okhdfcbank|okaxis|
│                     apl|upi|ibl|axisb|sbi|icici|hdfc|kotak|barodampay|
│                     aubank|indus|federal)
│   Example: "john@ybl", "scammer@paytm"
└── Validation: Must match user@provider pattern

PHONE NUMBERS (Indian):
├── With +91: \+91[-\s]?\d{10}
├── Plain 10-digit: [6-9]\d{9}
├── With 91 prefix: 91[6-9]\d{9}
└── Validation:
    • Exactly 10 digits after cleaning
    • Must start with 6, 7, 8, or 9

BENEFICIARY NAMES (CRITICAL for mule identification):
├── Patterns:
│   • "name shows as 'Name'"
│   • "Account Holder: Name"
│   • "Transfer to Name"
│   • "beneficiary name: Name"
└── Validation:
    • 3-50 characters
    • Mostly alphabetic
    • Filtered through blocklist (action words, banking terms, honorifics)

WHATSAPP NUMBERS:
├── "WhatsApp: +91 9876543210"
├── "message on WhatsApp 9876543210"
└── wa.me/919876543210 links

URLS (Phishing Detection):
├── Pattern: https?://[\w.-]+(?:\.[a-z]{2,10})+(?:/[^\s<>\"'{}|\\^`\[\]]*)?
└── Suspicious Indicators:
    • URL shorteners: bit.ly, tinyurl, t.co, goo.gl, is.gd, cutt.ly
    • Phishing keywords: login, verify, update, secure, account, signin
    • KYC/OTP: kyc, otp, bank, sbi, hdfc, icici, axis
    • Brand impersonation: amazon, flipkart, paytm, phonepe, gpay
    • Prize/lottery: prize, claim, refund, reward, winner, lottery
    • Free TLDs: .tk, .ml, .ga, .cf, .gq, .xyz, .work, .top

IFSC CODES:
├── Pattern: [A-Z]{4}0[A-Z0-9]{6}
└── Example: "SBIN0001234"
```

### Beneficiary Name Blocklist

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BENEFICIARY NAME BLOCKLIST                            │
│           (Words that should NOT be extracted as names)                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Action Words: now, before, paying, please, urgent, click, here, send,  │
│                pay, fast, verification                                   │
│                                                                          │
│  Banking Terms: account, bank, upi, payment, money, transfer, amount,   │
│                 rupees, rs, inr, credited, debited, pending, failed,    │
│                 success, transaction, beneficiary, receiver, sender     │
│                                                                          │
│  Honorifics: sir, madam, ji, mr, mrs, ms, dr, shri, smt, sahab         │
│                                                                          │
│  Support Terms: customer, user, member, client, support, help, desk,    │
│                 center, service, team, officer, dear                    │
│                                                                          │
│  Instructions: call, contact, message, reply, confirm, complete,        │
│                submit, enter, provide, share, receive, collect          │
│                                                                          │
│  Common Words: the, and, for, with, from, holder, number, today,        │
│                immediately, asap, quick, verify, update, link, otp,     │
│                pin, password, name                                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
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
# When high-value intelligence is complete, use these believable excuses (17 variations):
EXIT_RESPONSES = [
    "okay i am calling that number now, hold on...",
    "wait my son just came home, let me ask him to help me with this",
    "one second, someone is at the door, i will call you back",
    "okay i sent the money, now my phone is dying, i need to charge it",
    "hold on, i am getting another call from my bank, let me check",
    "oh no my doorbell is ringing, someone is at the door... i will do this later",
    "sorry my neighbor aunty just came, i have to go help her with something urgent",
    "arey my grandson is crying, i need to check on him... one minute",
    "oh god my cooking is burning on the stove! i smell smoke!! wait wait",
    "wait my daughter-in-law is calling me for lunch, i have to go eat first",
    "oh the milk is boiling over! wait wait i have to go to kitchen!!",
    "my blood pressure medicine time ho gaya, i feel dizzy... let me take rest",
    "ji actually i just remembered i have doctor appointment today, need to leave now",
    "sorry sir power cut ho gaya, my phone battery is only 2%... will call you back",
    "wait i am getting another call, it shows BANK on my phone... should i pick up??",
    "hold on my beti is asking who i am talking to, she looks worried...",
    "one second, my husband just came and he is asking what i am doing on phone",
]
```

---

## 9. Stage 5: AI Agent Engagement (One-Pass JSON)

### HoneypotAgent Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HONEYPOT AGENT COMPONENTS                             │
│                       (One-Pass JSON Architecture)                       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         HoneypotAgent                                    │
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │ Persona         │  │ EngagementPolicy│  │ FakeDataGenerator       │  │
│  │ (Pushpa Verma)  │  │                 │  │                         │  │
│  │                 │  │ • Mode routing  │  │ • Credit cards          │  │
│  │ • 65+ elderly   │  │ • Exit checks   │  │ • Bank accounts         │  │
│  │   teacher       │  │ • Intel check   │  │ • OTPs, Aadhaar, PAN   │  │
│  │ • Tech-confused │  │ • Thresholds    │  │ • Persona details       │  │
│  │ • Trusting      │  │                 │  │                         │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Gemini 3 Flash Client                        │    │
│  │  Primary: gemini-3-flash-preview                                │    │
│  │  Fallback: gemini-2.5-pro                                       │    │
│  │  Config:                                                        │    │
│  │    • temperature: 0.7 (creative, varied responses)              │    │
│  │    • max_output_tokens: 65536 (for Gemini 3 thinking)          │    │
│  │    • context_window: 8 turns                                    │    │
│  │    • safety_settings: BLOCK_NONE (allows scam roleplay)         │    │
│  │                                                                 │    │
│  │  ONE-PASS JSON OUTPUT:                                          │    │
│  │  {                                                              │    │
│  │    "reply_text": "conversational response to scammer",         │    │
│  │    "emotional_tone": "panicked",                               │    │
│  │    "extracted_intelligence": { bank_accounts, upi_ids, ... }   │    │
│  │  }                                                              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### One-Pass JSON Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ONE-PASS JSON ENGAGEMENT FLOW                         │
└─────────────────────────────────────────────────────────────────────────┘

     Scammer Message + History + Regex-Extracted Intel
                          │
                          ▼
     ┌────────────────────────────────────────────────────────────────────┐
     │  BUILD PROMPT                                                      │
     │  • Persona: Pushpa Verma (65+ elderly retired teacher)            │
     │  • Emotional state based on scam type + confidence + turn         │
     │  • Conversation history (8-turn window)                           │
     │  • Already-extracted intelligence (from regex)                    │
     │  • Fake data for compliance                                       │
     │  • Extraction directives for missing intel                        │
     └────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
     ┌────────────────────────────────────────────────────────────────────┐
     │  SINGLE LLM CALL (Gemini 3 Flash, ~500ms)                         │
     │  Returns JSON with BOTH:                                          │
     │  • reply_text: Believable engagement response                     │
     │  • extracted_intelligence: LLM-identified intel from conversation │
     └────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
     ┌────────────────────────────────────────────────────────────────────┐
     │  VALIDATE + MERGE                                                  │
     │  • LLM extraction validated against regex patterns                │
     │  • Merged with pre-extracted regex intel                          │
     │  • Deduplicated final intelligence set                            │
     └────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
                  EngagementResult {
                    response: "reply text",
                    extracted_intelligence: { merged intel },
                    turn_number: N
                  }
```

### Persona: Pushpa Verma

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PERSONA: PUSHPA VERMA                                 │
│                 65+ Elderly Retired School Teacher from Delhi           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TRAITS:                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • trusting: Believes what they're told                          │    │
│  │ • easily_panicked: Easily panicked                              │    │
│  │ • tech_confused: Needs step-by-step explanation                 │    │
│  │ • cooperative: Wants to help/comply                             │    │
│  │ • old_fashioned: Struggles with smartphones                     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  TYPING STYLE:                                                          │
│  • Mostly lowercase                                                     │
│  • Minimal punctuation                                                  │
│  • Occasional typos                                                     │
│  • Simple vocabulary                                                    │
│  • Hindi-English mixing (Hinglish)                                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Emotional States by Scam Type

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EMOTIONAL STATE MAPPING                               │
└─────────────────────────────────────────────────────────────────────────┘

Available Emotional States:
┌─────────────────────────────────────────────────────────────────────────┐
│ CALM: Default state                                                     │
│ ANXIOUS: Worried but manageable                                        │
│ PANICKED: Very scared                                                  │
│ RELIEVED: Temporary relief                                             │
│ COOPERATIVE: Use sparingly, only late in conversation                  │
│ INTERESTED: For job offers - curious about opportunity                 │
│ EXCITED: For lottery/rewards - happy about winning                     │
│ CAUTIOUS: For impersonation - intimidated but careful                  │
│ NEUTRAL: For unknown scam types                                        │
└─────────────────────────────────────────────────────────────────────────┘

Emotional Mapping by Scam Type:
┌─────────────────────────────────────────────────────────────────────────┐
│ Scam Type       │ High Intensity (>0.6) │ Low Intensity (≤0.6)         │
├─────────────────┼───────────────────────┼──────────────────────────────┤
│ job_offer       │ INTERESTED            │ INTERESTED                   │
│ banking_fraud   │ PANICKED              │ ANXIOUS                      │
│ lottery_reward  │ EXCITED               │ EXCITED                      │
│ impersonation   │ CAUTIOUS              │ CAUTIOUS                     │
│ others          │ NEUTRAL               │ CALM                         │
└─────────────────────────────────────────────────────────────────────────┘

NOTE: The LLM interprets these states and generates natural responses.
      No hardcoded phrases are injected.
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
│  Generated Data Types:                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Credit Card: Luhn-valid 16-digit with invalid BINs              │    │
│  │              BINs: 400000, 411111, 510000, 520000, 607000, etc. │    │
│  │              Example: 4000 1234 5678 9012                       │    │
│  │ Expiry: MM/YY format                                            │    │
│  │ CVV: 3 digits                                                   │    │
│  │ Bank Account: 11-16 digits starting with 9                      │    │
│  │ IFSC: Real bank prefix + fake branch (9XXXXX)                   │    │
│  │ OTP: 6 digits (avoiding 000000, 123456, 654321)                 │    │
│  │ Aadhaar: 12 digits starting with 2-9                            │    │
│  │ PAN: Format AAAAP9999A                                          │    │
│  │ Persona: Elderly Indian name (55-80 years), address with PIN    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ALWAYS follow fake data with extraction question:                       │
│  "ok my card number is [CARD]. what name should appear on your side?"   │
│                                                                          │
│  NOTE: Fake data is seeded by conversation_id to ensure                 │
│        consistency across multiple turns in the same conversation.      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Intelligence Extraction Priority

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXTRACTION PRIORITY                                   │
│                    (Targets for engagement)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PHASE 1: Payment Method                                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Bank Account OR UPI ID                                          │    │
│  │ → "where should i send the money?"                              │    │
│  │ → "what is your upi id?"                                        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  PHASE 2: Beneficiary Name (HIGHEST VALUE)                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Account holder name (identifies mule account)                   │    │
│  │ → "Validation Attack": Pretend app needs to verify name         │    │
│  │ → "i am typing [UPI]... what name should pop up?"              │    │
│  │ → "my app is showing [NAME], is that correct?"                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  PHASE 3: Phone Number                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Scammer contact for law enforcement                             │    │
│  │ → "what number can i call if i have problem?"                  │    │
│  │ → "can you send me message on whatsapp?"                       │    │
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
  "scamType": "banking_fraud",
  "confidence": 0.92,
  "engagementMetrics": {
    "engagementDurationSeconds": 2,
    "totalMessagesExchanged": 5
  },
  "extractedIntelligence": {
    "bankAccounts": ["12345678901234"],
    "upiIds": ["scammer@ybl"],
    "phoneNumbers": ["9876543210"],
    "beneficiaryNames": ["Rahul Kumar"],
    "phishingLinks": ["http://bit.ly/fake-bank"],
    "emails": [],
    "bankNames": [],
    "whatsappNumbers": ["+91-8888899999"],
    "ifscCodes": ["SBIN0001234"],
    "other_critical_info": [
      {"label": "TeamViewer ID", "value": "123 456 789"}
    ]
  },
  "agentNotes": "Mode: aggressive | Type: banking_fraud | Confidence: 92% | Turn: 5 | Persona: panicked",
  "agentResponse": "ok i am typing scammer@ybl in my app... it shows Rahul Kumar, is that right?"
}
```

### Intelligence Source Attribution

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE SOURCES                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  REGEX-EXTRACTED (fast, deterministic):                                 │
│  • bankAccounts, upiIds, phoneNumbers, ifscCodes, urls                  │
│                                                                          │
│  LLM-EXTRACTED (flexible, context-aware):                               │
│  • beneficiaryNames (from "name shows as...", "account holder...")     │
│  • cryptoAddresses (various wallet formats)                             │
│  • otherCriticalInfo (ad-hoc identifiers)                               │
│                                                                          │
│  HYBRID (LLM-extracted, regex-validated):                               │
│  • UPI IDs (LLM catches obfuscated, regex validates format)             │
│  • IFSC codes (LLM finds in context, regex validates pattern)           │
│  • Bank accounts (LLM catches spelled-out numbers, regex validates)     │
│                                                                          │
│  Final result is MERGED and DEDUPLICATED from all sources               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
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
    Pure AI scam detector using Gemini 3 Flash.
    
    Key Methods:
    - detect(): Main entry point for message analysis
    - get_engagement_mode(): Returns NONE, CAUTIOUS, or AGGRESSIVE
    
    Important Constants:
    - SCAM_THRESHOLD = 0.6 (minimum confidence to flag as scam)
    - CAUTIOUS_THRESHOLD = 0.60 (minimum for cautious engagement)
    - AGGRESSIVE_THRESHOLD = 0.85 (minimum for aggressive engagement)
    
    Key Feature: Confidence Escalation
    - Confidence can only INCREASE over conversation
    - Prevents false negatives from oscillation
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
    - Context-aware (uses conversation history)
    
    Configuration:
    - Temperature: 0.1 (deterministic outputs)
    - Max Output Tokens: 10000
    - Timeout: 90 seconds
    - Max Retries: 2
    - Retry Delay: 1.0 seconds
    
    Safety Settings:
    - BLOCK_ONLY_HIGH for all harm categories
    - Allows analysis of scam content without triggering safety blocks
    
    Scam Types:
    - job_offer, banking_fraud, lottery_reward, impersonation, others
    """
```

### 12.3 IntelligenceExtractor (`src/intelligence/extractor.py`)

```python
class IntelligenceExtractor:
    """
    Hybrid intelligence extraction (Regex + LLM validation).
    
    REGEX EXTRACTION (runs first, fast, deterministic, ~5ms):
    - extract_bank_accounts(): 9-18 digit numbers (excludes phone numbers)
    - extract_upi_ids(): username@provider patterns (known providers)
    - extract_phone_numbers(): Indian mobile formats (6-9 prefix)
    - extract_beneficiary_names(): Account holder names (multiple patterns)
    - extract_urls(): URLs with phishing detection
    - extract_whatsapp_numbers(): WhatsApp-specific contacts
    - extract_ifsc_codes(): [A-Z]{4}0[A-Z0-9]{6}
    
    LLM EXTRACTION VALIDATION:
    - validate_llm_extraction(): Validates LLM-extracted intel with regex
    - UPI IDs must match user@provider pattern
    - IFSC codes must match [A-Z]{4}0[A-Z0-9]{6}
    - Bank accounts must be 9-18 digits
    
    MERGE OPERATION:
    - merge_intelligence(): Combines regex + validated LLM results
    - Deduplicates all fields
    - Normalizes formats (strip whitespace, etc.)
    
    Extended Fields (for One-Pass JSON):
    - crypto_addresses: Bitcoin, Ethereum, etc. wallet addresses
    - other_critical_info: Ad-hoc high-value data (TeamViewer IDs, etc.)
    
    Validation:
    - Phone: 10 digits, starts with 6-9
    - Bank Account: 9-18 digits, not all same digit, not phone-like
    - Name: 3-50 chars, mostly alphabetic, blocklist filtered
    
    Known UPI Providers:
    ybl, paytm, okicici, oksbi, okhdfcbank, okaxis, apl, upi, ibl,
    axisb, sbi, icici, hdfc, kotak, barodampay, aubank, indus, federal
    """
```

### 12.4 HoneypotAgent (`src/agents/honeypot_agent.py`)

```python
class HoneypotAgent:
    """
    AI agent that engages scammers with believable elderly persona.
    Uses ONE-PASS JSON architecture for efficiency.
    
    Key Components:
    - Persona: Pushpa Verma (65+ elderly retired teacher)
    - EngagementPolicy: Determines engagement mode and exit conditions
    - FakeDataGenerator: Provides fake financial data
    - IntelligenceExtractor: For hybrid LLM+regex extraction
    
    Gemini Configuration:
    - Primary model: gemini-3-flash-preview
    - Fallback: gemini-2.5-pro
    - Temperature: 0.7 (creative, varied responses)
    - Max Output Tokens: 65536 (for Gemini 3 thinking)
    - Context Window: 8 turns
    - Safety: BLOCK_NONE (allows scam roleplay)
    
    ONE-PASS JSON Architecture:
    - Single LLM call returns BOTH reply_text AND extracted_intelligence
    - Lower latency (~500ms vs ~650ms with separate calls)
    - Reply is context-aware of extracted intel
    - LLM extraction validated with regex patterns
    - Results merged with pre-extracted regex intel
    
    Response Strategy:
    - Build targeted extraction directives based on missing intel
    - Include fake data for apparent compliance
    - Emotional state based on scam type + confidence + turn number
    """
```

### 12.5 Persona (`src/agents/persona.py`)

```python
class Persona:
    """
    State tracker for Pushpa Verma persona.
    
    Core Persona: 65+ elderly retired school teacher from Delhi
    
    Traits:
    - trusting: Believes what they're told
    - easily_panicked: Easily panicked
    - tech_confused: Needs step-by-step explanation
    - cooperative: Wants to help/comply
    - old_fashioned: Struggles with smartphones
    
    Key Method:
    - get_emotional_state(scam_type, confidence, turn_number)
      Returns appropriate emotional state based on context
    
    Emotional States:
    - CALM: Default, early conversation
    - ANXIOUS: Worried, mid-conversation
    - PANICKED: Very scared (banking_fraud with high confidence)
    - COOPERATIVE: Ready to comply (later turns)
    - INTERESTED: For job offers
    - EXCITED: For lottery/rewards
    - CAUTIOUS: For impersonation
    - NEUTRAL: For unknown scam types
    
    Design Rationale:
    - LLM generates natural, varied emotional responses
    - State context guides tone without constraining expression
    - Different emotions for different scam types
    """
```

### 12.6 FakeDataGenerator (`src/agents/fake_data.py`)

```python
class FakeDataGenerator:
    """
    Generates believable but invalid financial data.
    Seeded by conversation_id for consistency across turns.
    
    Features:
    - Luhn-valid credit card numbers (pass format checks, fail transactions)
    - Invalid BINs: 400000, 411111, 510000, 520000, 607000, etc.
    - Real bank IFSC prefixes with fake branch codes (9XXXXX)
    - Elderly Indian names (typical scam targets, 55-80 years)
    - Consistent data per conversation (seeded by conversation_id)
    
    Generated Data Types:
    - Credit cards (Luhn-valid, 16 digits)
    - Bank accounts (11-16 digits starting with 9)
    - IFSC codes (real prefix + fake branch)
    - OTPs (6 digits, avoiding obvious patterns)
    - Aadhaar (12 digits starting with 2-9)
    - PAN (format AAAAP9999A)
    - Persona details (name, age, address with PIN)
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
│ 2. On failure, retry up to 2 times with 1 second delay                 │
│ 3. If still failing, try fallback model (gemini-2.5-flash)             │
│ 4. If both fail, return uncertain result (confidence=0.5)              │
└────────────────────────────────────────────────────────────────────────┘

AI Engagement Failure:
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Try primary model (gemini-3-flash-preview)                          │
│ 2. On failure, try fallback model (gemini-2.5-pro)                     │
│ 3. If both fail, return generic engagement response                    │
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
│ • All errors logged with structured context (structlog)              │
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

# AI Models (defaults to Gemini 3 Flash with fallbacks)
FLASH_MODEL=gemini-3-flash-preview
FALLBACK_FLASH_MODEL=gemini-2.5-flash
FALLBACK_PRO_MODEL=gemini-2.5-pro
LLM_TEMPERATURE=0.7
LLM_TIMEOUT=90
MAX_RETRIES=2
RETRY_DELAY=1.0

# Engagement Policy
MAX_ENGAGEMENT_TURNS_CAUTIOUS=10
MAX_ENGAGEMENT_TURNS_AGGRESSIVE=25
MAX_ENGAGEMENT_DURATION_SECONDS=600
CAUTIOUS_CONFIDENCE_THRESHOLD=0.60
AGGRESSIVE_CONFIDENCE_THRESHOLD=0.85
CONTEXT_WINDOW=8

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
│  │ • Classifier: BLOCK_ONLY_HIGH (allows scam analysis)            │    │
│  │ • Agent: BLOCK_NONE (allows scam roleplay for honeypot)         │    │
│  │ • Categories: HARASSMENT, HATE_SPEECH, SEXUALLY_EXPLICIT,       │    │
│  │   DANGEROUS_CONTENT                                             │    │
│  │ • These settings are essential for the system to function       │    │
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

### Request Flow Summary (One-Pass JSON Architecture)

```
1. REQUEST RECEIVED
   └─▶ Middleware validates API key (x-api-key header)
   
2. DETECTION PHASE
   ├─▶ AI classifier (Gemini 3 Flash) analyzes semantically (~150ms)
   ├─▶ Context-aware: uses full conversation history
   ├─▶ Returns: is_scam, confidence, scam_type, threat_indicators
   └─▶ Confidence can only INCREASE (prevents oscillation)

3. REGEX EXTRACTION (~5ms)
   └─▶ Regex extracts all standard intel types
       (bank accounts, UPI IDs, phone numbers, beneficiary names, URLs, etc.)

4. POLICY DECISION
   ├─▶ If confidence < 0.60 → Return neutral response
   ├─▶ If high-value intel complete → EXIT with random polite excuse
   └─▶ If intel incomplete → CONTINUE engagement

5. ENGAGEMENT PHASE - ONE-PASS JSON (if continuing)
   ├─▶ Persona: Pushpa Verma (65+ elderly teacher)
   ├─▶ Emotional state based on scam type + confidence + turn
   ├─▶ FakeDataGenerator provides compliant-looking data
   ├─▶ Extraction directives target missing intel
   ├─▶ Gemini 3 Flash returns BOTH reply + LLM extraction (~500ms)
   └─▶ LLM extraction validated with regex patterns

6. INTELLIGENCE MERGE
   └─▶ Combine regex + validated LLM extraction, deduplicate

7. RESPONSE RETURNED
   └─▶ Full merged intelligence + agent response + metrics
```

### Key Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Never break character** | Agent never reveals scam awareness |
| **Confidence monotonicity** | Confidence can only increase |
| **Prioritize beneficiary names** | Critical for mule identification |
| **AI-only detection** | Simpler architecture, Gemini 3 Flash |
| **One-Pass JSON** | Single LLM call returns reply + extraction (~500ms) |
| **Hybrid extraction** | LLM catches obfuscated data, regex validates structured fields |
| **Pushpa Verma persona** | 65+ elderly teacher, tech-confused, trusting |
| **Scam-type-aware emotions** | Different emotions for banking vs lottery vs job scams |
| **Fake data compliance** | Appear cooperative, extract intel |
| **Graceful degradation** | Fallback models when primary fails |
| **Targeted extraction** | Directives based on missing intel |
| **17 exit responses** | Natural, varied excuses for graceful exit |

---

*Document generated: January 30, 2026*
*Version: 2.1 (Updated for current implementation)*
*Author: Sticky-Net Development Team*
