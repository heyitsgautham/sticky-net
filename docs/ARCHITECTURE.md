# Sticky-Net Architecture

> **Production-ready honeypot system with AI-powered scam detection and multi-turn scammer engagement**

---

## System Overview

Sticky-Net is an AI-powered honeypot that:
1. **Detects scam messages** using AI classification with Gemini 3 Flash
2. **Engages scammers** with a believable elderly human persona (Pushpa Verma)
3. **Extracts intelligence** (bank accounts, UPI IDs, phone numbers, beneficiary names, phishing URLs)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│              Incoming Message + Metadata + History                  │
│         { message, conversationHistory, channel, locale, time }     │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STAGE 1: AI Scam Classifier                      │
│              (Gemini 3 Flash: ~150ms, context-aware)                │
├─────────────────────────────────────────────────────────────────────┤
│  MODEL: gemini-3-flash-preview (fallback: gemini-2.5-flash)         │
│                                                                     │
│  INPUT:                                                             │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  • Current message                                          │    │
│  │  • Conversation history (full context)                      │    │
│  │  • Metadata: channel, locale, timestamp                    │    │
│  │  • Previous classification (if exists)                     │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  CONFIGURATION:                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  • Temperature: 0.1 (deterministic outputs)                 │    │
│  │  • Max Output Tokens: 10000                                 │    │
│  │  • Timeout: 90 seconds                                      │    │
│  │  • Max Retries: 2                                           │    │
│  │  • Safety Settings: BLOCK_ONLY_HIGH (all categories)        │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  OUTPUT:                                                            │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  {                                                          │    │
│  │    "is_scam": true,                                         │    │
│  │    "confidence": 0.87,                                      │    │
│  │    "scam_type": "banking_fraud",                           │    │
│  │    "threat_indicators": ["urgency", "payment_request"],    │    │
│  │    "reasoning": "Message uses classic OTP phishing..."     │    │
│  │  }                                                          │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  SCAM TYPES:                                                        │
│  • job_offer: Part-time job, work from home, YouTube liking        │
│  • banking_fraud: KYC update, account blocked, verify account      │
│  • lottery_reward: Lottery winner, reward points, cashback         │
│  • impersonation: Police, CBI, bank official impersonation         │
│  • others: Any scam that doesn't fit above categories              │
│                                                                     │
│  FALLBACK: On API failure → Try gemini-2.5-flash                   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
      Not Scam (conf < 0.6)              Is Scam (conf ≥ 0.6)
              │                                     │
              ▼                                     ▼
┌─────────────────────────┐     ┌─────────────────────────────────────┐
│  Return Neutral         │     │      STAGE 2: Engagement Policy     │
│  Response               │     │         (Confidence Routing)        │
│  • Log for analysis     │     ├─────────────────────────────────────┤
│  • Continue monitoring  │     │  conf 0.60-0.85: CAUTIOUS mode      │
└─────────────────────────┘     │    • Max 10 turns                    │
                                │    • Quick extraction attempts       │
                                │                                      │
                                │  conf ≥ 0.85: AGGRESSIVE mode        │
                                │    • Max 25 turns                    │
                                │    • Full persona engagement         │
                                └───────────────┬─────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│          STAGE 3: AI Engagement Agent (One-Pass JSON)               │
│           (Gemini 3 Flash: ~500ms, persona-driven)                  │
├─────────────────────────────────────────────────────────────────────┤
│  MODEL: gemini-3-flash-preview (fallback: gemini-2.5-pro)           │
│                                                                     │
│  CONFIGURATION:                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  • Temperature: 0.7 (creative, varied responses)            │    │
│  │  • Max Output Tokens: 65536 (for Gemini 3 thinking)         │    │
│  │  • Context Window: 8 turns                                  │    │
│  │  • Safety Settings: BLOCK_NONE (allows scam roleplay)       │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║  ONE-PASS ARCHITECTURE: Single LLM call returns BOTH:         ║ │
│  ║  • Conversational reply (persona-driven engagement)           ║ │
│  ║  • Extracted intelligence (bank accounts, UPI IDs, etc.)      ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│                                                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐   │
│  │ Persona       │  │ Conversation  │  │ Hybrid Extraction     │   │
│  │ (Pushpa)      │  │ Memory        │  │ (LLM + Regex)         │   │
│  ├───────────────┤  ├───────────────┤  ├───────────────────────┤   │
│  │ 65+ elderly   │  │ Full history  │  │ LLM: flexible extract │   │
│  │ teacher       │  │ tracking      │  │ Regex: validation     │   │
│  │ Tech-confused │  │ 8-turn window │  │ Merge & deduplicate   │   │
│  │ Trusting      │  │               │  │ other_critical_info   │   │
│  └───────────────┘  └───────────────┘  └───────────────────────┘   │
│                                                                     │
│  EXIT CONDITIONS (checked before engagement):                       │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  ✓ High-value intel complete (bank/UPI + phone + name)     │    │
│  │  ✓ Max turns reached (10 cautious / 25 aggressive)         │    │
│  │  ✓ Max duration exceeded (10 minutes / 600s)               │    │
│  │  ✓ Scammer becomes suspicious                              │    │
│  │  ✓ No new information in 5 turns (stale)                   │    │
│  └────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STAGE 4: Response Builder                         │
├─────────────────────────────────────────────────────────────────────┤
│  AGENT JSON OUTPUT (from One-Pass LLM call):                        │
│  {                                                                  │
│    "reply_text": "oh no which account? i have sbi and hdfc...",    │
│    "emotional_tone": "panicked",                                    │
│    "extracted_intelligence": {                                      │
│      "bank_accounts": ["1234567890"],                               │
│      "upi_ids": ["scammer@paytm"],                                  │
│      "phone_numbers": ["9888899999"],                               │
│      "beneficiary_names": ["Rahul Kumar"],                          │
│      "urls": [],                                                    │
│      "whatsapp_numbers": [],                                        │
│      "ifsc_codes": ["SBIN0001234"],                                 │
│      "crypto_addresses": [],                                        │
│      "other_critical_info": [                                       │
│        {"label": "TeamViewer ID", "value": "123456789"}             │
│      ]                                                              │
│    }                                                                │
│  }                                                                  │
│                                                                     │
│  API RESPONSE (final):                                              │
│  {                                                                  │
│    "status": "success",                                             │
│    "scamDetected": true,                                            │
│    "confidence": 0.87,                                              │
│    "scamType": "banking_fraud",                                     │
│    "agentResponse": "oh no which account? i have sbi and hdfc...", │
│    "engagementMetrics": { ... },                                    │
│    "extractedIntelligence": { ... merged LLM + regex ... },        │
│    "agentNotes": "Mode: aggressive | Type: banking_fraud | ..."    │
│  }                                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Conversation State Machine

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONVERSATION STATE MACHINE                        │
│                                                                     │
│   Key Principle: State can ONLY escalate, never de-escalate         │
│   Once scam detected → stays in engagement mode                     │
│   Confidence can only INCREASE (prevents false negatives)          │
└─────────────────────────────────────────────────────────────────────┘

     ┌──────────────┐
     │   MONITORING │ ◄─── Initial state for all conversations
     │  (Neutral)   │      Every message gets classified
     └──────┬───────┘
            │
            │ Scam detected (conf ≥ 0.6)
            ▼
     ┌──────────────┐
     │   ENGAGING   │ ◄─── Honeypot active, persona engaged
     │  (Cautious/  │      Confidence can only INCREASE
     │  Aggressive) │      Mode can escalate (cautious → aggressive)
     └──────┬───────┘
            │
            │ Exit condition met (intel complete, max turns, etc.)
            ▼
     ┌──────────────┐
     │   COMPLETE   │ ◄─── Intelligence extracted or limits reached
     │              │      Returns exit response
     └──────────────┘
```

---

## Multi-Stage Scam Detection (Context-Aware)

Every message is classified with full conversation history:

```
TURN 1: "Hi, I'm from support"
┌─────────────────────────────────────────────────────────────────┐
│ Classification:                                                 │
│   • is_scam: false, confidence: 0.25                           │
│   • Action: Monitor, return neutral response                    │
└─────────────────────────────────────────────────────────────────┘
                              │
TURN 2: "There's unusual activity on your account"
┌─────────────────────────────────────────────────────────────────┐
│ Classification (with history):                                  │
│   • is_scam: true, confidence: 0.72 ← ESCALATED                │
│   • Action: Switch to CAUTIOUS engagement                       │
└─────────────────────────────────────────────────────────────────┘
                              │
TURN 3: "Send your OTP to verify"
┌─────────────────────────────────────────────────────────────────┐
│ Classification (with full history):                             │
│   • is_scam: true, confidence: 0.95 ← HIGH                     │
│   • Action: AGGRESSIVE engagement                               │
└─────────────────────────────────────────────────────────────────┘


CONFIDENCE PROGRESSION:

1.0 │                                    ████████████
    │                               █████
0.85│─────────────────────────█████──────────────────── AGGRESSIVE
    │                    █████
    │               █████
0.6 │──────────█████─────────────────────────────────── CAUTIOUS
    │     █████
    │█████
0.25│
    └──────────────────────────────────────────────────
         1      2      3      4      5      6    Turns
```

---

## Component Details

### 1. AI Scam Classifier (`src/detection/classifier.py`)

**Model**: `gemini-3-flash-preview` (fallback: `gemini-2.5-flash`)

```python
class ScamClassifier:
    """
    AI-based scam classifier using Gemini 3 Flash.
    
    Configuration:
    - Temperature: 0.1 (deterministic outputs)
    - Max Output Tokens: 10000
    - Timeout: 90 seconds
    - Max Retries: 2
    - Retry Delay: 1.0 seconds
    
    Safety Settings: BLOCK_ONLY_HIGH for all harm categories
    (HARASSMENT, HATE_SPEECH, SEXUALLY_EXPLICIT, DANGEROUS_CONTENT)
    """
    
    def __init__(self):
        self.client = genai.Client()
        self.model = settings.flash_model  # "gemini-3-flash-preview"
        self.fallback_model = settings.fallback_flash_model  # "gemini-2.5-flash"
    
    async def classify(
        self,
        message: str,
        history: list[Message],
        metadata: MessageMetadata,
        previous_classification: ClassificationResult | None
    ) -> ClassificationResult:
        # Returns: is_scam, confidence, scam_type, threat_indicators, reasoning
```

**Scam Types (Enum)**:
| Type | Description |
|------|-------------|
| `job_offer` | Part-time job, work from home, YouTube liking scams |
| `banking_fraud` | KYC update, account blocked, verify account |
| `lottery_reward` | Lottery winner, reward points, cashback |
| `impersonation` | Police, CBI, bank official impersonation |
| `others` | Any scam that doesn't fit above categories |

### 2. Scam Detector (`src/detection/detector.py`)

**Purpose**: Wraps the AI classifier with confidence escalation logic

```python
class ScamDetector:
    """
    Pure AI detection (no regex pre-filtering).
    
    Key Features:
    - Uses ScamClassifier for AI-based detection
    - SCAM_THRESHOLD = 0.6 (minimum confidence to flag as scam)
    - Confidence escalation: confidence can only INCREASE from previous
    """
    
    def get_engagement_mode(self, confidence: float) -> EngagementMode:
        if confidence >= self.AGGRESSIVE_THRESHOLD:  # 0.85
            return EngagementMode.AGGRESSIVE
        elif confidence >= self.CAUTIOUS_THRESHOLD:   # 0.60
            return EngagementMode.CAUTIOUS
        return EngagementMode.NONE
```

### 3. Engagement Policy (`src/agents/policy.py`)

**Purpose**: Route scams to appropriate engagement intensity

```python
@dataclass
class EngagementPolicy:
    # Confidence thresholds
    CAUTIOUS_THRESHOLD = 0.60
    AGGRESSIVE_THRESHOLD = 0.85
    
    # Turn limits
    CAUTIOUS_MAX_TURNS = 10
    AGGRESSIVE_MAX_TURNS = 25
    
    # Time limits
    MAX_DURATION_SECONDS = 600  # 10 minutes
    
    # Stale detection
    STALE_TURN_THRESHOLD = 5   # Exit if no new info in 5 turns
    
    def is_high_value_intel_complete(self, intel: dict) -> bool:
        """
        High-value intel is complete when we have ALL of:
        - (Bank Account OR UPI ID)
        - AND Phone Number
        - AND Beneficiary Name
        """
```

### 4. Honeypot Agent (`src/agents/honeypot_agent.py`)

**Model**: `gemini-3-flash-preview` (fallback: `gemini-2.5-pro`)

**Architecture**: One-Pass JSON — single LLM call returns both conversational reply AND extracted intelligence.

```python
class HoneypotAgent:
    """
    AI agent that engages scammers with believable elderly persona.
    
    Configuration:
    - Temperature: 0.7 (creative, varied responses)
    - Max Output Tokens: 65536 (for Gemini 3 thinking)
    - Context Window: 8 turns
    - Safety Settings: BLOCK_NONE (allows scam roleplay)
    """
    
    def __init__(self):
        self.client = genai.Client()
        self.model = settings.flash_model  # "gemini-3-flash-preview"
        self.fallback_model = settings.fallback_pro_model  # "gemini-2.5-pro"
        self.persona = Persona()
        self.fake_data_generator = FakeDataGenerator()
    
    async def engage(
        self,
        message: Message,
        history: list[Message],
        detection: ClassificationResult,
        state: ConversationState
    ) -> EngagementResult:
        # Returns JSON with BOTH reply_text AND extracted_intelligence
```

### 5. Persona (`src/agents/persona.py`)

**Purpose**: State tracker for persona — Pushpa Verma (65+ elderly retired teacher)

**Persona Traits**:
| Trait | Description |
|-------|-------------|
| `trusting` | Believes what they're told |
| `easily_panicked` | Easily panicked |
| `tech_confused` | Needs step-by-step explanation |
| `cooperative` | Wants to help/comply |
| `old_fashioned` | Struggles with smartphones |

**Emotional States by Scam Type**:
| Scam Type | High Intensity (>0.6) | Low Intensity (≤0.6) |
|-----------|----------------------|---------------------|
| `job_offer` | INTERESTED | INTERESTED |
| `banking_fraud` | PANICKED | ANXIOUS |
| `lottery_reward` | EXCITED | EXCITED |
| `impersonation` | CAUTIOUS | CAUTIOUS |
| `others` | NEUTRAL | CALM |

```python
class Persona:
    """
    Pure state tracker - LLM handles emotional expression.
    
    Emotional States:
    - CALM: Default, early conversation
    - ANXIOUS: Worried, mid-conversation
    - PANICKED: Very scared, high-pressure scams
    - COOPERATIVE: Ready to comply, later turns
    - INTERESTED: For job offers
    - EXCITED: For lottery/rewards
    - CAUTIOUS: For impersonation
    """
    
    def get_emotional_state(
        self, 
        scam_type: str | None, 
        confidence: float, 
        turn_number: int
    ) -> str:
        # Returns appropriate emotional state based on context
```

### 6. Intelligence Extractor (`src/intelligence/extractor.py`)

**Purpose**: Hybrid extraction using LLM + regex validation

**Extraction Patterns**:
| Type | Pattern Description |
|------|---------------------|
| **Bank Account** | 9-18 digits; formatted `XXXX-XXXX-XXXX`; prefixed with `A/C`, `Account:` |
| **UPI ID** | Known providers: `[\w.-]+@(ybl|paytm|okicici|oksbi|okhdfcbank|okaxis|...)` |
| **Phone** | `+91` prefix + 10 digits; 10 digits starting [6-9] |
| **Beneficiary Name** | "name shows as", "Account Holder:", "Transfer to Name" |
| **URL** | `https?://` patterns with suspicious indicators |
| **IFSC** | `[A-Z]{4}0[A-Z0-9]{6}` |
| **WhatsApp** | Various patterns with "whatsapp" keyword; `wa.me` links |

```python
class IntelligenceExtractor:
    """
    Hybrid extraction: Regex + LLM validation.
    
    Regex Extraction: Fast, deterministic (~5ms)
    - Bank accounts, UPI IDs, phone numbers, URLs, IFSC codes
    
    LLM Extraction: Flexible, context-aware
    - Beneficiary names (from natural language)
    - Obfuscated data ("nine eight seven..." spelled out)
    - Crypto addresses, other_critical_info
    
    Validation:
    - Phone: Must start with 6-9, exactly 10 digits
    - Bank Account: 9-18 digits, not all same digit, not phone-like
    - UPI: Must match user@provider pattern
    - Name: 3-50 chars, mostly alphabetic, filtered through blocklist
    """
```

**Known UPI Providers**:
```
ybl, paytm, okicici, oksbi, okhdfcbank, okaxis, apl, upi, ibl, 
axisb, sbi, icici, hdfc, kotak, barodampay, aubank, indus, federal
```

**`other_critical_info` Field**: Captures high-value data that doesn't fit standard fields:
- Crypto wallet addresses
- Remote desktop IDs (TeamViewer, AnyDesk)
- Reference/ticket numbers
- App download links (APK links)
- Alternative payment methods

### 7. Fake Data Generator (`src/agents/fake_data.py`)

**Purpose**: Generate believable but invalid financial data to waste scammer time

```python
class FakeDataGenerator:
    """
    Generates fake data seeded by conversation_id for consistency.
    
    Generated Types:
    - Credit Card: Luhn-valid 16-digit with invalid BINs
    - Bank Account: 11-16 digits starting with 9
    - IFSC: Real bank prefix + fake branch (9XXXXX)
    - OTP: 6 digits (avoiding 000000, 123456, 654321)
    - Aadhaar: 12 digits starting with 2-9
    - PAN: Format AAAAP9999A
    - Persona: Elderly Indian name (55-80 years), address with PIN
    """
```

---

## Configuration Parameters

| Parameter | Default Value | Purpose |
|-----------|---------------|---------|
| `FLASH_MODEL` | `gemini-3-flash-preview` | Scam classification & engagement |
| `FALLBACK_FLASH_MODEL` | `gemini-2.5-flash` | Classifier fallback |
| `FALLBACK_PRO_MODEL` | `gemini-2.5-pro` | Engagement fallback |
| `LLM_TEMPERATURE` | `0.7` | Creativity in responses |
| `LLM_TIMEOUT` | `90` seconds | API call timeout |
| `MAX_RETRIES` | `2` | Retry attempts on failure |
| `RETRY_DELAY` | `1.0` seconds | Delay between retries |
| `CAUTIOUS_CONFIDENCE` | `0.60` | Min confidence to engage cautiously |
| `AGGRESSIVE_CONFIDENCE` | `0.85` | Min confidence for aggressive mode |
| `MAX_TURNS_CAUTIOUS` | `10` | Turn limit for cautious mode |
| `MAX_TURNS_AGGRESSIVE` | `25` | Turn limit for aggressive mode |
| `MAX_DURATION_SECONDS` | `600` | 10-minute engagement cap |
| `STALE_THRESHOLD` | `5` | Turns without new info before exit |
| `CONTEXT_WINDOW` | `8` | Number of turns in agent context |

---

## API Contract

### Request
```json
{
  "message": {
    "sender": "scammer",
    "text": "Your bank account will be blocked today. Verify immediately.",
    "timestamp": "2026-01-21T10:15:30Z"
  },
  "conversationHistory": [
    {"sender": "scammer", "text": "...", "timestamp": "..."},
    {"sender": "user", "text": "...", "timestamp": "..."}
  ],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

### Response
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
    "bankAccounts": ["123456789012"],
    "upiIds": ["scammer@upi"],
    "phoneNumbers": ["9876543210"],
    "phishingLinks": ["http://malicious.example"],
    "emails": ["scammer@example.com"],
    "beneficiaryNames": ["John Doe"],
    "bankNames": ["State Bank of India"],
    "ifscCodes": ["SBIN0001234"],
    "whatsappNumbers": ["919876543210"],
    "other_critical_info": [{"label": "Remote Access Tool", "value": "AnyDesk"}]
  },
  "agentNotes": "Mode: aggressive | Type: banking_fraud | Confidence: 92% | Turn: 5 | Persona: panicked",
  "agentResponse": "oh no! what do i need to do to verify?"
}
```

### Exit Responses (17 variations)
When high-value intelligence is complete, random exit phrase is used:
```
- okay i am calling that number now, hold on...
- wait my son just came home, let me ask him to help me with this
- one second, someone is at the door, i will call you back
- okay i sent the money, now my phone is dying, i need to charge it
- hold on, i am getting another call from my bank, let me check
- oh no my doorbell is ringing, someone is at the door...
- sorry my neighbor aunty just came, i have to go help her
- arey my grandson is crying, i need to check on him...
- oh god my cooking is burning on the stove! wait wait
- wait my daughter-in-law is calling me for lunch
- oh the milk is boiling over! wait wait i have to go to kitchen!!
- my blood pressure medicine time ho gaya, i feel dizzy...
- ji actually i just remembered i have doctor appointment today
- sorry sir power cut ho gaya, my phone battery is only 2%...
- wait i am getting another call, it shows BANK on my phone...
- hold on my beti is asking who i am talking to...
- one second, my husband just came and asking what i am doing
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Runtime** | Python 3.11+ |
| **API Framework** | FastAPI |
| **AI SDK** | `google-genai` (v1.51.0+) |
| **LLM Provider** | Google Vertex AI (Gemini 3 Flash) |
| **Logging** | structlog |
| **Validation** | Pydantic |
| **Containerization** | Docker |
| **Deployment** | Google Cloud Run |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| AI-only detection (no regex pre-filter) | Simpler architecture, AI handles all classification |
| Gemini 3 Flash for classification | Fast (~150ms), semantic understanding, context-aware |
| Gemini 3 Flash for engagement | Same model, creative responses with temperature 0.7 |
| Every message classified | Catches multi-stage scams that start benign |
| Confidence only increases | Prevents false negatives from state oscillation |
| State machine (monitor→engage→complete) | Clear lifecycle management |
| Exit on high-value intel complete | Bank/UPI + Phone + Beneficiary Name = complete |
| **One-Pass JSON architecture** | Single LLM call returns reply + extraction — lower latency |
| **Hybrid extraction (LLM + regex)** | LLM catches obfuscated/flexible data, regex validates structured fields |
| **Pushpa Verma persona** | 65+ elderly teacher, tech-confused, trusting — believable target |
| **Scam-type-aware emotions** | Different emotional responses for banking vs lottery vs job scams |
| **`other_critical_info` field** | Captures high-value data that doesn't fit standard fields |
| **17 exit responses** | Natural, varied excuses for graceful conversation exit |
