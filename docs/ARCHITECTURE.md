# Sticky-Net Architecture

> **Production-ready honeypot system with hybrid AI/Regex detection and multi-turn scammer engagement**

---

## System Overview

Sticky-Net is an AI-powered honeypot that:
1. **Detects scam messages** using a hybrid approach (regex pre-filter + AI classification)
2. **Engages scammers** with a believable human persona
3. **Extracts intelligence** (bank accounts, UPI IDs, phishing URLs)

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
│                    STAGE 0: Regex Pre-Filter                        │
│                         (Fast Path: ~10ms)                          │
├─────────────────────────────────────────────────────────────────────┤
│  • Obvious Scam (95%+ confidence):                                  │
│    - "send OTP/PIN/CVV", "account blocked immediately"              │
│    → SKIP AI → Engage directly                                      │
│                                                                     │
│  • Obvious Safe (allowlist):                                        │
│    - Banking notifications, OTP from known services                 │
│    → SKIP AI → Return neutral response                              │
│                                                                     │
│  • Uncertain (~70% of messages):                                    │
│    → Continue to AI Classification                                  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 STAGE 1: AI Scam Classifier                         │
│              (Gemini 3 Flash: ~150ms, $0.0001/call)                 │
├─────────────────────────────────────────────────────────────────────┤
│  MODEL: gemini-3-flash-preview                                      │
│                                                                     │
│  INPUT:                                                             │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  • Current message                                          │    │
│  │  • Conversation history (last 3-5 turns)                   │    │
│  │  • Metadata: channel, locale, timestamp                    │    │
│  │  • Previous classification (if exists)                     │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  OUTPUT:                                                            │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  {                                                          │    │
│  │    "is_scam": true,                                         │    │
│  │    "confidence": 0.87,                                      │    │
│  │    "scam_type": "banking_fraud",                           │    │
│  │    "threat_indicators": ["urgency", "payment_request"]     │    │
│  │  }                                                          │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  FALLBACK: On API failure → Use regex + heuristics                 │
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
│  • Continue monitoring  │     │  conf 0.6-0.85: CAUTIOUS mode       │
└─────────────────────────┘     │    • Max 10 turns                    │
                                │    • Quick extraction attempts       │
                                │                                      │
                                │  conf > 0.85: AGGRESSIVE mode        │
                                │    • Max 25 turns                    │
                                │    • Full persona engagement         │
                                └───────────────┬─────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   STAGE 3: AI Engagement Agent                       │
│                (Gemini 3 Pro: ~500ms, $0.01/call)                   │
├─────────────────────────────────────────────────────────────────────┤
│  MODEL: gemini-3-pro-preview                                        │
│                                                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐   │
│  │ Persona       │  │ Conversation  │  │ Intelligence          │   │
│  │ Manager       │  │ Memory        │  │ Extractor             │   │
│  ├───────────────┤  ├───────────────┤  ├───────────────────────┤   │
│  │ Emotional     │  │ Full history  │  │ Bank account regex    │   │
│  │ state machine │  │ tracking      │  │ UPI ID patterns       │   │
│  │ Turn-based    │  │ Context       │  │ Phishing URL capture  │   │
│  │ adaptation    │  │ windowing     │  │ Entity validation     │   │
│  └───────────────┘  └───────────────┘  └───────────────────────┘   │
│                                                                     │
│  EXIT CONDITIONS (EngagementPolicy):                                │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  ✓ Intelligence complete (bank + UPI + link extracted)     │    │
│  │  ✓ Max turns reached (10 cautious / 25 aggressive)         │    │
│  │  ✓ Max duration exceeded (10 minutes)                      │    │
│  │  ✓ Scammer becomes hostile/suspicious                      │    │
│  │  ✓ No new information in last 5 turns (stale)              │    │
│  │  ✓ Conversation goes off-topic                             │    │
│  └────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STAGE 4: Response Builder                         │
├─────────────────────────────────────────────────────────────────────┤
│  OUTPUT:                                                            │
│  {                                                                  │
│    "status": "success",                                             │
│    "scamDetected": true,                                            │
│    "confidence": 0.87,                                              │
│    "scamType": "banking_fraud",                                     │
│    "response": "Oh no, which account? I have SBI and HDFC...",     │
│    "engagementMetrics": {                                           │
│      "turnNumber": 3,                                               │
│      "engagementMode": "aggressive",                                │
│      "engagementDurationSeconds": 180,                              │
│      "shouldContinue": true                                         │
│    },                                                               │
│    "extractedIntelligence": {                                       │
│      "bankAccounts": ["1234567890"],                                │
│      "upiIds": ["scammer@paytm"],                                   │
│      "phishingLinks": []                                            │
│    },                                                               │
│    "agentNotes": "Scammer used RBI impersonation tactic"           │
│  }                                                                  │
│                                                                     │
│  PERSIST: Save conversation state to Firestore                      │
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
└─────────────────────────────────────────────────────────────────────┘

     ┌──────────────┐
     │   MONITORING │ ◄─── Initial state for all conversations
     │  (Neutral)   │      Every message still gets classified
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
            │ Exit condition met
            ▼
     ┌──────────────┐
     │   COMPLETE   │ ◄─── Intelligence extracted or limits reached
     │              │      Conversation archived
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

### 1. Regex Pre-Filter (`src/detection/patterns.py`)

**Purpose**: Fast-path obvious cases without AI cost

```python
class RegexPreFilter:
    # Instant scam patterns (skip AI, engage immediately)
    INSTANT_SCAM_PATTERNS = [
        r"send\s+(otp|password|pin|cvv)",
        r"verify\s+within\s+\d+\s+(hours?|minutes?)",
        r"account\s+(blocked|suspended|locked).*immediately",
        r"click\s+(here|link).*verify",
        r"lottery|jackpot|won\s+\$?\d+",
    ]
    
    # Safe patterns (skip AI, return neutral)
    SAFE_PATTERNS = [
        r"your\s+otp\s+is\s+\d{4,6}",      # OTP from services
        r"transaction\s+of\s+rs\.?\s*\d+.*debited",  # Bank notifications
    ]
    
    def classify(self, message: str) -> PreFilterResult:
        # Returns: OBVIOUS_SCAM | OBVIOUS_SAFE | UNCERTAIN
```

### 2. AI Scam Classifier (`src/detection/classifier.py`)

**Model**: `gemini-3-flash-preview` (fast, cheap, semantic understanding)

```python
class ScamClassifier:
    def __init__(self):
        self.client = genai.Client()
        self.model = "gemini-3-flash-preview"
    
    async def classify(
        self,
        message: str,
        history: list[Message],
        metadata: MessageMetadata,
        previous_classification: ClassificationResult | None
    ) -> ClassificationResult:
        
        prompt = f"""
        Analyze if this conversation is a scam attempt.
        
        CONVERSATION HISTORY:
        {self._format_history(history)}
        
        NEW MESSAGE: "{message}"
        
        METADATA: channel={metadata.channel}, locale={metadata.locale}
        
        PREVIOUS ASSESSMENT: {previous_classification}
        
        CONSIDER:
        1. Does the conversation show ESCALATION toward scam tactics?
        2. Is this a multi-stage scam setup?
        3. Combined with history, does this reveal scam intent?
        
        Return JSON: {{"is_scam": bool, "confidence": float, "scam_type": str}}
        """
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.LOW  # Fast classification
                )
            )
        )
        return self._parse_response(response)
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
    
    def get_engagement_mode(self, confidence: float) -> EngagementMode:
        if confidence >= self.AGGRESSIVE_THRESHOLD:
            return EngagementMode.AGGRESSIVE
        elif confidence >= self.CAUTIOUS_THRESHOLD:
            return EngagementMode.CAUTIOUS
        return EngagementMode.NONE
    
    def should_continue(self, state: EngagementState) -> bool:
        max_turns = (self.AGGRESSIVE_MAX_TURNS 
                     if state.mode == EngagementMode.AGGRESSIVE 
                     else self.CAUTIOUS_MAX_TURNS)
        
        return (
            state.turn_count < max_turns and
            state.duration_seconds < self.MAX_DURATION_SECONDS and
            not state.intelligence_complete and
            not state.scammer_suspicious and
            state.turns_since_new_info < self.STALE_TURN_THRESHOLD
        )
```

### 4. Honeypot Agent (`src/agents/honeypot_agent.py`)

**Model**: `gemini-3-pro-preview` (sophisticated reasoning for believable responses)

```python
class HoneypotAgent:
    def __init__(self):
        self.client = genai.Client()
        self.model = "gemini-3-pro-preview"
        self.persona_manager = PersonaManager()
    
    async def engage(
        self,
        message: Message,
        history: list[Message],
        detection: ClassificationResult,
        state: ConversationState
    ) -> EngagementResult:
        
        persona = self.persona_manager.get_persona(state)
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=self._build_prompt(message, history, persona),
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.HIGH  # Deep reasoning
                ),
                system_instruction=HONEYPOT_SYSTEM_PROMPT
            )
        )
        
        return EngagementResult(
            response=response.text,
            persona_state=persona.emotional_state,
            turn_number=state.turn_count
        )
```

### 5. Persona Manager (`src/agents/persona.py`)

**Purpose**: Maintain believable human character across turns

```python
class PersonaManager:
    EMOTIONAL_STATES = {
        "calm": "Slightly confused, asking for clarification",
        "anxious": "Worried, expressing concern about account",
        "panicked": "Very scared, willing to do anything to fix it",
        "cooperative": "Ready to share information to 'resolve' issue"
    }
    
    def get_persona_context(self, state: ConversationState) -> str:
        emotional_state = self._calculate_emotion(
            turn=state.turn_count,
            scam_intensity=state.confidence
        )
        
        return f"""
        You are a naive, trusting person who:
        - Emotional state: {self.EMOTIONAL_STATES[emotional_state]}
        - Turn {state.turn_count}: {"confused" if turn < 5 else "cooperative"}
        - Ask questions that extract: bank details, UPI IDs, links
        - NEVER reveal you know it's a scam
        """
```

### 6. Intelligence Extractor (`src/intelligence/extractor.py`)

**Purpose**: Extract actionable data using regex patterns

```python
class IntelligenceExtractor:
    PATTERNS = {
        "bank_account": r'\b\d{9,18}\b',
        "upi_id": r'\b[\w.-]+@[a-zA-Z]+\b',
        "phone": r'\b[6-9]\d{9}\b',
        "url": r'https?://[^\s<>"{}|\\^`\[\]]+',
    }
    
    def extract(self, text: str) -> ExtractedIntelligence:
        return ExtractedIntelligence(
            bank_accounts=self._find_all("bank_account", text),
            upi_ids=self._find_all("upi_id", text),
            phishing_links=self._find_suspicious_urls(text)
        )
```

---

## Firestore State Schema

```python
@dataclass
class ConversationState:
    conversation_id: str
    mode: EngagementMode          # MONITORING | CAUTIOUS | AGGRESSIVE | COMPLETE
    
    # Classification tracking
    current_confidence: float     # Highest confidence seen (never decreases)
    is_scam_detected: bool        # True once detected (never resets)
    scam_type: str | None
    
    # History
    history: list[Message]        # Full conversation
    turn_count: int
    
    # Engagement metrics
    started_at: datetime
    last_message_at: datetime
    intelligence_extracted: ExtractedIntelligence
    
    # Exit tracking
    turns_since_new_info: int
    should_continue: bool
```

---

## Configuration Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `FLASH_MODEL` | `gemini-3-flash-preview` | Fast scam classification |
| `PRO_MODEL` | `gemini-3-pro-preview` | Engagement response generation |
| `CLASSIFICATION_TIMEOUT_MS` | 200 | Max time for AI classifier |
| `CAUTIOUS_CONFIDENCE` | 0.60 | Min confidence to engage cautiously |
| `AGGRESSIVE_CONFIDENCE` | 0.85 | Min confidence for full engagement |
| `MAX_TURNS_CAUTIOUS` | 10 | Turn limit for uncertain scams |
| `MAX_TURNS_AGGRESSIVE` | 25 | Turn limit for high-confidence scams |
| `MAX_DURATION_SECONDS` | 600 | 10-minute engagement cap |
| `STALE_THRESHOLD` | 5 | Turns without new info before exit |

---

## Cost Analysis

| Stage | Model | Cost/Call | % Messages | Effective Cost |
|-------|-------|-----------|------------|----------------|
| Regex Pre-Filter | — | $0 | 100% | $0 |
| AI Classifier | Gemini 3 Flash | $0.0001 | ~30% (uncertain) | $0.00003 |
| Engagement | Gemini 3 Pro | $0.01 | ~10% (scams) | $0.001 |

**Total cost per message: ~$0.001**

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
  "conversationHistory": [],
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
  "confidence": 0.87,
  "scamType": "banking_fraud",
  "agentResponse": "Oh no! What do I need to do? Which account?",
  "engagementMetrics": {
    "turnNumber": 1,
    "engagementMode": "aggressive",
    "engagementDurationSeconds": 2,
    "shouldContinue": true
  },
  "extractedIntelligence": {
    "bankAccounts": [],
    "upiIds": [],
    "phishingLinks": []
  },
  "agentNotes": "Detected urgency + threat tactics. Engagement initiated."
}
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Runtime** | Python 3.11+ |
| **API Framework** | FastAPI |
| **AI SDK** | `google-genai` (v1.51.0+) |
| **LLM Provider** | Google Vertex AI (Gemini 3 Flash/Pro) |
| **Database** | Firestore |
| **Containerization** | Docker |
| **Deployment** | Google Cloud Run |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Hybrid detection (regex + AI) | Speed for obvious cases, accuracy for edge cases |
| Gemini Flash for classification | Fast (~150ms), cheap (~$0.0001), semantic understanding |
| Gemini Pro for engagement | Deep reasoning for believable human-like responses |
| Every message classified | Catches multi-stage scams that start benign |
| Confidence only increases | Prevents false negatives from state oscillation |
| State machine (monitor→engage→complete) | Clear lifecycle management |
| Exit conditions | Prevents infinite loops, saves costs |
| Regex for intelligence extraction | Deterministic, fast, reliable for structured data |
