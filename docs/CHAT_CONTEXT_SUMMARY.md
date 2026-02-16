# Sticky-Net Chat Context Summary

> **Created**: 26 January 2026  
> **Purpose**: Context continuity for future chat sessions

---

## Project Overview

**Sticky-Net** is an AI-powered honeypot system for the **India AI Impact Buildathon** hackathon that:
1. Detects scam messages using Gemini AI (Flash for classification, Pro for engagement)
2. Engages scammers with a believable human persona (elderly Indian victim)
3. Extracts intelligence (bank accounts, UPI IDs, phishing links)

---

## Current State: ✅ Ready for Hackathon Evaluation

### What's Working
- ✅ All 145 tests passing
- ✅ API endpoint compliant with hackathon format
- ✅ Successfully tested with hackathon endpoint tester
- ✅ Local development setup complete
- ✅ ngrok tunneling working

### Tech Stack
| Component | Technology |
|-----------|------------|
| Runtime | Python 3.11 |
| Framework | FastAPI |
| AI Models | Gemini 3 Flash (classification), Gemini 3 Pro (engagement) |
| AI SDK | `google-genai` via Vertex AI |
| Deployment | Local + ngrok (Cloud Run ready) |

---

## API Endpoint Details

### Endpoint
```
POST /api/v1/analyze
```

### Authentication
```
Header: x-api-key: test-api-key
```

### Request Format
```json
{
  "message": {
    "sender": "scammer",
    "text": "Your bank account will be blocked today.",
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

### Response Format (matches hackathon requirements)
```json
{
  "status": "success",
  "scamDetected": true,
  "scamType": "banking_fraud",
  "confidence": 1.0,
  "engagementMetrics": {
    "engagementDurationSeconds": 12,
    "totalMessagesExchanged": 1
  },
  "extractedIntelligence": {
    "bankAccounts": [],
    "upiIds": [],
    "phoneNumbers": [],
    "phishingLinks": [],
    "emails": [],
    "beneficiaryNames": [],
    "bankNames": ["SBI"],
    "ifscCodes": [],
    "whatsappNumbers": [],
    "other_critical_info": []
  },
  "agentNotes": "Mode: aggressive | Type: banking_fraud | Confidence: 100%",
  "agentResponse": "beta i am very scared what does compromised mean??"
}
```

---

## Local Development Commands

### Start API Server
```bash
cd /Users/gauthamkrishna/Projects/sticky-net
.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8080
```

### Start ngrok Tunnel
```bash
ngrok http 8080
```

### Run Tests
```bash
.venv/bin/python -m pytest tests/ -v
```

### Test API Locally
```bash
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-api-key" \
  -d '{"message":{"sender":"scammer","text":"Your bank account will be blocked.","timestamp":"2026-01-21T10:15:30Z"},"conversationHistory":[],"metadata":{"channel":"SMS","language":"English","locale":"IN"}}'
```

---

## Hackathon Endpoint Tester Results

### Test Details
- **Tester URL**: `https://hackathon.guvi.in/timeline?hackathon-id=a90c3b95-4406-46b9-870d-b52d0e430a6f`
- **Test Status**: ✅ "Success! Honeypot testing completed."
- **Server Response**: 200 OK

### Server Logs During Test
```
IP: 43.204.10.11 (AWS India - hackathon server)
Message: 158 chars (SBI compromise scam)
Detection: is_scam=True, confidence=1.0, scam_type=banking_fraud
Response: 200 OK
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/main.py` | FastAPI app entry point |
| `src/api/routes.py` | API endpoints |
| `src/api/schemas.py` | Request/response Pydantic models |
| `src/api/middleware.py` | API key authentication |
| `src/detection/classifier.py` | Gemini Flash scam classification |
| `src/agents/honeypot_agent.py` | Gemini Pro engagement agent |
| `src/intelligence/extractor.py` | Bank/UPI/URL extraction |
| `config/settings.py` | Environment configuration |
| `.env` | Environment variables (API_KEY, GCP project, etc.) |

---

## Environment Variables (in .env)

```bash
API_KEY=test-api-key
GOOGLE_CLOUD_PROJECT=sticky-net-485205
GOOGLE_APPLICATION_CREDENTIALS=./secrets/service-account.json
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=True
FLASH_MODEL=gemini-3-flash-preview
PRO_MODEL=gemini-3-pro-preview
```

---

## Next Steps (if continuing)

1. **Cloud Run Deployment**: Follow `milestone-6-deployment.instructions.md`
2. **Final Submission**: Replace ngrok URL with Cloud Run URL
3. **Performance Optimization**: Consider response caching for faster latency

---

## Important Documentation

- Hackathon Docs: `docs/DOCUMENTATION.md`
- Problem Statement: `docs/PROBLEM_STATEMENT.md`
- Submission Rules: `docs/SUBMISSION.md`
- Architecture: `docs/ARCHITECTURE.md`
- Vertex AI Docs: `docs/VERTEX_API_DOCS.md`

---

## Testing Evidence Location

Test results stored in: `endpoint-testing/test-1/`
- `ui.txt` - UI screenshot/results
- `network_tab.txt` - Browser network requests
- `server_logs.txt` - Uvicorn server logs during test
