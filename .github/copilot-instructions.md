# Sticky-Net: AI Agentic Honey-Pot System

# Important Note:
Remember that your context window is limited - especially the output size. So you should ALWAYS work in discrete steps and run each step using #runSubagent

## Project Overview

An AI-powered honeypot system that detects scam messages and autonomously engages scammers to extract actionable intelligence (bank accounts, UPI IDs, phishing links) through multi-turn conversations.

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Runtime** | Python 3.11+ |
| **API Framework** | FastAPI |
| **AI SDK** | `google-genai` (v1.51.0+) |
| **LLM Provider** | Google Vertex AI (Gemini 3 Flash/Pro) |
| **Database** | Firestore (conversation state & intelligence) |
| **Containerization** | Docker |
| **Deployment** | Google Cloud Run |
| **Local Dev** | Docker Compose |

## Testing Instructions
For each time running any test, always run 
.venv/bin/python -m pytest tests/ -v

## Vertex AI Models
See [docs/VERTEX_API_DOCS.md](./../docs/VERTEX_API_DOCS.md) for details on the models used.

## Architecture

See [docs/ARCHITECTURE.md](./../docs/ARCHITECTURE.md) for detailed architecture documentation.

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│              Incoming Message + Metadata + History                  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 STAGE 0: Regex Pre-Filter (~10ms)                   │
│  • Obvious scam → Skip AI, engage immediately                       │
│  • Obvious safe → Skip AI, return neutral                           │
│  • Uncertain → Continue to AI                                       │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│           STAGE 1: AI Scam Classifier (gemini-3-flash-preview)      │
│  • Fast semantic classification (~150ms)                            │
│  • Context-aware (uses conversation history)                        │
│  • Returns: is_scam, confidence, scam_type                          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
      Not Scam (conf < 0.6)              Is Scam (conf ≥ 0.6)
              │                                     │
              ▼                                     ▼
┌─────────────────────────┐     ┌──────────────────────────────────────┐
│  Return neutral         │     │      STAGE 2: Engagement Policy      │
│  Continue monitoring    │     │  • conf 0.6-0.85: CAUTIOUS (10 turns)│
└─────────────────────────┘     │  • conf > 0.85: AGGRESSIVE (25 turns)│
                                └───────────────┬──────────────────────┘
                                                │
                                                ▼
                                ┌─────────────────────────────────────┐
                                │  STAGE 3: AI Engagement Agent       │
                                │  (gemini-3-pro-preview)             │
                                │  • Believable human persona         │
                                │  • Intelligence extraction          │
                                │  • Exit conditions enforced         │
                                └───────────────┬─────────────────────┘
                                                │
                                                ▼
                                ┌─────────────────────────────────────┐
                                │  STAGE 4: Intelligence Extractor    │
                                │  • Bank account regex               │
                                │  • UPI ID patterns                  │
                                │  • Phishing URL detection           │
                                └─────────────────────────────────────┘
```

## API Contract

### Request Format
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

### Response Format
```json
{
  "status": "success",
  "scamDetected": true,
  "engagementMetrics": {
    "engagementDurationSeconds": 420,
    "totalMessagesExchanged": 18
  },
  "extractedIntelligence": {
    "bankAccounts": ["XXXX-XXXX-XXXX"],
    "upiIds": ["scammer@upi"],
    "phishingLinks": ["http://malicious-link.example"]
  },
  "agentNotes": "Scammer used urgency tactics and payment redirection"
}
```

## Development Milestones

| # | Milestone | Description | Instruction File |
|---|-----------|-------------|------------------|
| 1 | **Project Setup** | Scaffold structure, dependencies, Docker, local dev | `milestone-1-project-setup.instructions.md` |
| 2 | **API Layer** | FastAPI endpoints, authentication, request validation | `milestone-2-api-layer.instructions.md` |
| 3 | **Scam Detection** | Fraud indicator analysis, confidence scoring | `milestone-3-scam-detection.instructions.md` |
| 4 | **Agent Engagement** | Agent with human persona, multi-turn | `milestone-4-agent-engagement.instructions.md` |
| 5 | **Intelligence Extraction** | Bank/UPI/URL pattern extraction | `milestone-5-intelligence-extraction.instructions.md` |
| 6 | **Deployment** | GCP Cloud Run deployment, CI/CD pipeline | `milestone-6-deployment.instructions.md` |

## Coding Standards

### Python Style
- Use Python 3.11+ features (type hints, match statements)
- Follow PEP 8 with 100 char line limit
- Use `async/await` for I/O operations
- Type hints required for all function signatures
- Docstrings for all public functions (Google style)

### File Organization
- One class per file (generally)
- Keep modules focused and small (<300 lines)
- Use `__all__` for explicit exports

### Error Handling
- Use custom exceptions in `src/exceptions.py`
- Never expose internal errors to API responses
- Log errors with structured context

## Agent Behavior Rules

1. **Never reveal detection** — Maintain believable human persona at all times
2. **Adaptive responses** — Vary tactics based on scammer's approach
3. **Natural extraction** — Ask clarifying questions that prompt intelligence sharing
4. **Context awareness** — Use full `conversationHistory` for coherent responses
5. **Safety limits** — Max engagement turns, timeout handling