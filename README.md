# Sticky-Net 🕸️

<p align="center">
  <strong>AI-Powered Honeypot System for Scam Detection & Intelligence Extraction</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19-61DAFB.svg" alt="React 19">
  <img src="https://img.shields.io/badge/Gemini-3.0-purple.svg" alt="Gemini 3.0">
  <img src="https://img.shields.io/badge/Tailwind-CSS-38B2AC.svg" alt="Tailwind CSS">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
</p>

---

## 🎯 Overview

**Sticky-Net** is an AI-powered honeypot system that autonomously detects scam messages and engages scammers through multi-turn conversations to extract actionable intelligence. The system uses Google's Gemini 3 models to classify threats and generate believable human responses, wasting scammers' time while gathering evidence for law enforcement.

### Core Capabilities

- 🔍 **Hybrid Scam Detection** — Fast regex pre-filter + AI semantic classification
- 🎭 **Believable Persona** — Maintains a naive, confused victim character
- 🏦 **Intelligence Extraction** — Bank accounts, UPI IDs, phone numbers, phishing links
- ⏱️ **Adaptive Engagement** — Cautious (10 turns) or Aggressive (25 turns) modes
- 🌐 **Interactive Web UI** — React-based landing page with live demo interface
- 🛡️ **Production-Ready** — Docker, Cloud Run deployment, structured logging

---

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Approach & Strategy](#-approach--strategy)
- [Key Features](#-key-features--improvements)
- [Technology Stack](#-technology-stack)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Web UI Features](#-web-ui-features)
- [Intelligence Extraction](#-intelligence-extraction)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Documentation](#-documentation)
- [License](#-license)

---

## ✨ What's New

### Latest Updates (January 2026)

- 🌐 **Web UI Launch** — Interactive React-based landing page with live demo
- 🎯 **Enhanced Intelligence Extraction** — Now extracts beneficiary names for mule identification
- 🚪 **Smart Exit Conditions** — High-value intelligence completion detection
- 📊 **Monotonic Confidence** — Prevents false negative oscillation
- 🔌 **CORS Support** — Full frontend-backend integration
- 🎨 **Cyberpunk Design** — Dark-mode UI with smooth Framer Motion animations
- 💾 **Conversation Persistence** — Save and manage multiple chat threads
- 📱 **Responsive Design** — Works seamlessly on all devices

---

## 🏗️ Architecture

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
│           STAGE 1: AI Scam Classifier (Gemini 3 Flash)              │
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
                                │  (Gemini 3 Pro)                     │
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

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Never Reveal Detection** | System always maintains believable human persona |
| **Adaptive Engagement** | Varies tactics based on scammer approach |
| **Natural Extraction** | Asks clarifying questions to prompt intelligence sharing |
| **Monotonic Confidence** | Confidence only increases (prevents false negative oscillation) |
| **Beneficiary Priority** | Prioritizes extracting account holder names for mule identification |
| **Safety Limits** | Max turns, timeout handling, exit conditions |

---

## 🧠 Approach & Strategy

Sticky-Net uses a **multi-stage pipeline** to detect scams, engage scammers, and extract intelligence — all driven by generic, pattern-based logic and LLM reasoning (no hardcoded test responses).

### How We Detect Scams

1. **Regex Pre-Filter (Stage 0)** — A fast keyword/pattern scan (~10ms) catches obvious scam indicators (urgency words, account threats, OTP requests). Obvious safe messages are passed through without AI cost.
2. **AI Semantic Classifier (Stage 1)** — Messages that pass the pre-filter are analyzed by **Gemini 3 Flash** for context-aware scam classification. The classifier considers the full `conversationHistory` and outputs a confidence score + scam type.
3. **Monotonic Confidence** — Once a conversation is flagged as a scam, confidence only increases across turns, preventing false negative oscillation.

### How We Extract Intelligence

- **Hybrid Extraction** — Combines fast regex patterns (bank accounts, UPI IDs, phone numbers, URLs, emails) with LLM-powered extraction for context-dependent values.
- **Generic Patterns** — All extraction is pattern-based and works for _any_ phone number, account, UPI ID, or URL — not tied to specific test data.
- **Validation & Deduplication** — Extracted values are validated (e.g., Indian phone number prefix check, UPI provider list) and deduplicated across turns.
- **Accumulated Intelligence** — Intel is accumulated across the full conversation session and reported via the callback endpoint.

### How We Maintain Engagement

- **Believable Persona** — The AI engagement agent (Gemini 3 Pro) roleplays as a naive, confused victim who asks clarifying questions that naturally prompt scammers to share identifying information.
- **Adaptive Engagement Policy** — Confidence 0.6–0.85 triggers CAUTIOUS mode (up to 10 turns); confidence > 0.85 triggers AGGRESSIVE mode (up to 25 turns).
- **Natural Intelligence Elicitation** — The agent asks for phone numbers, account details, and verification steps in a way that feels organic to the scammer.
- **Smart Exit Conditions** — Engagement ends when all critical intel is gathered, the conversation stalls, or the scammer shows awareness.

---

## 🚀 Key Features & Improvements

### Intelligent Exit Conditions

The system includes sophisticated exit logic to maximize intelligence extraction:

1. **High-Value Intelligence Complete** — Stops when all critical intel is gathered:
   - Bank account OR UPI ID
   - Phone number
   - **Beneficiary name** (mule account holder)

2. **Stale Conversation Detection** — Exits if no new info in 3+ turns
3. **Suspicious Scammer Detection** — Exits if scammer shows awareness
4. **Turn & Duration Limits** — Enforces max engagement time/turns
5. **Monotonic Confidence** — Prevents false negatives by only increasing confidence

### Advanced Intelligence Extraction

**Hybrid Extraction System:**
- **Regex Patterns** — Fast extraction for known formats (bank accounts, IFSC codes, phone numbers)
- **AI Extraction** — LLM-powered extraction for context-dependent values (beneficiary names, banks)
- **Validation Layer** — All extracted values are validated before storage
- **Deduplication** — Intelligent merging of regex + AI results

**Supported Intelligence Types:**
- Bank account numbers (9-18 digits with validation)
- UPI IDs (50+ provider validation)
- Phone numbers (Indian format with 6-9 prefix validation)
- Beneficiary/account holder names (critical for mule identification)
- IFSC codes (format validation)
- Bank names (50+ Indian banks)
- Phishing URLs (domain reputation analysis)
- WhatsApp numbers, emails, crypto wallets, TeamViewer IDs

### Enhanced API Response

The API now returns comprehensive intelligence with:
- Real-time confidence scores
- Engagement metrics (duration, message count)
- Structured intelligence by category
- Agent notes explaining scammer tactics
- Believable human response for next turn

### CORS & Frontend Support

- Configurable CORS middleware for frontend integration
- Preflight request handling
- Debug mode for development (`allow_origins=["*"]`)
- Production-ready security settings

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Runtime** | Python 3.11+ | Core language with type hints |
| **API Framework** | FastAPI | REST API with auto-validation || **Frontend** | React 19 | Interactive web UI |
| **UI Framework** | Tailwind CSS + shadcn/ui | Component library & styling |
| **Animations** | Framer Motion | Smooth UI animations || **AI SDK** | `google-genai` v1.51+ | Gemini model access |
| **Primary Models** | Gemini 3 Flash/Pro | Scam detection & engagement |
| **Fallback Models** | Gemini 2.5 Flash/Pro | Reliability fallback |
| **Database** | Google Firestore | Conversation state & intelligence |
| **Validation** | Pydantic v2 | Request/response schemas |
| **Logging** | structlog | Structured JSON logging |
| **Containerization** | Docker | Production deployment |
| **Cloud** | Google Cloud Run | Serverless hosting |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- GCP Service Account with Vertex AI & Firestore access

### Option 1: Local Development (Recommended)

**Backend Setup:**
```bash
# Clone the repository
git clone https://github.com/heyitsguatham/sticky-net.git
cd sticky-net

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your API key and GCP project

# Place GCP service account key
mkdir -p secrets
cp /path/to/service-account.json secrets/

# Run the backend server
uvicorn src.main:app --reload --port 8000
```

**Frontend Setup (Optional):**
```bash
# In a new terminal
cd frontend

# Install Node.js dependencies
npm install

# Set backend URL (optional, defaults to localhost:8000)
echo "REACT_APP_API_URL=http://localhost:8000" > .env

# Start the development server
npm start

# Frontend will be available at http://localhost:3000
```

### Option 2: Docker Compose

```bash
# Build and run backend with Firestore emulator
docker-compose up --build

# The API will be available at http://localhost:8000
# For frontend, use Option 1's frontend setup in a separate terminal
```

### Option 3: Docker Only

```bash
# Build the image
docker build -t sticky-net .

# Run with environment variables
docker run -p 8000:8000 \
  -e API_KEY=your-api-key \
  -e GOOGLE_CLOUD_PROJECT=your-project \
  -e PORT=8000 \
  -v $(pwd)/secrets:/app/secrets:ro \
  sticky-net
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# API Configuration
API_KEY=your-secure-api-key
PORT=8000
DEBUG=true

# Frontend Configuration (frontend/.env)
# REACT_APP_API_URL=http://localhost:8000

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_APPLICATION_CREDENTIALS=./secrets/service-account.json

# AI Models
FLASH_MODEL=gemini-3-flash-preview      # Fast classification
PRO_MODEL=gemini-3-pro-preview          # Engagement responses
FALLBACK_FLASH_MODEL=gemini-2.5-flash   # Fallback classification
FALLBACK_PRO_MODEL=gemini-2.5-pro       # Fallback engagement
LLM_TEMPERATURE=0.7

# Engagement Policy
MAX_ENGAGEMENT_TURNS_CAUTIOUS=10
MAX_ENGAGEMENT_TURNS_AGGRESSIVE=25
MAX_ENGAGEMENT_DURATION_SECONDS=600
CAUTIOUS_CONFIDENCE_THRESHOLD=0.60
AGGRESSIVE_CONFIDENCE_THRESHOLD=0.85

# Timeouts
API_TIMEOUT_SECONDS=90
GEMINI_MAX_RETRIES=2
```

### GCP Service Account

The service account needs the following roles:
- `roles/aiplatform.user` — Vertex AI access
- `roles/datastore.user` — Firestore access

---

## 📡 API Reference

### Base URL

**Local Development:**
```
http://localhost:8000/api/v1
```

**Production (Cloud Run):**
```
https://<your-cloud-run-url>/api/v1
```

**Web UI (when frontend is running):**
```
http://localhost:3000
```

### Authentication

All API requests require an API key header:

```
Content-Type: application/json
x-api-key: your-api-key
```

### Endpoints

#### `POST /api/v1/analyze` — Primary Honeypot Endpoint

This is the main evaluation endpoint. It receives scam messages, detects threats, engages the scammer with a believable reply, extracts intelligence, and asynchronously reports findings via a callback.

**Request:**

```json
{
  "sessionId": "uuid-v4-string",
  "message": {
    "sender": "scammer",
    "text": "URGENT: Your account has been compromised. Share OTP immediately.",
    "timestamp": "2026-01-21T10:15:30Z"
  },
  "conversationHistory": [
    {
      "sender": "scammer",
      "text": "Previous message from scammer",
      "timestamp": "1737451800000"
    },
    {
      "sender": "user",
      "text": "Previous response from honeypot",
      "timestamp": "1737451920000"
    }
  ],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

**Response (200 OK):**

The endpoint returns a simplified JSON with the agent's reply — suitable for multi-turn conversation:

```json
{
  "status": "success",
  "reply": "Oh no! Which account is blocked? I have SBI and HDFC both. Please help me sir!"
}
```

> The evaluator checks for `reply`, `message`, or `text` fields in that order.

#### Final Output (Callback)

After each turn, the system **asynchronously** sends a full intelligence report to the evaluation callback endpoint with the following structure:

```json
{
  "sessionId": "uuid-v4-string",
  "status": "success",
  "scamDetected": true,
  "totalMessagesExchanged": 18,
  "extractedIntelligence": {
    "phoneNumbers": ["+91-9876543210"],
    "bankAccounts": ["1234567890123456"],
    "upiIds": ["scammer.fraud@fakebank"],
    "phishingLinks": ["http://malicious-site.com"],
    "emailAddresses": ["scammer@fake.com"]
  },
  "engagementMetrics": {
    "engagementDurationSeconds": 420,
    "totalMessagesExchanged": 18
  },
  "agentNotes": "Scammer used urgency tactics and payment redirection"
}
```

Intelligence is **accumulated across turns** — each callback contains the full set of intel gathered so far in the session.

#### `POST /api/v1/analyze/detailed` — Frontend Endpoint

Returns the full analysis response including confidence scores, scam type, and complete extracted intelligence. Used by the web UI.

<details>
<summary>Detailed Response Schema</summary>

```json
{
  "status": "success",
  "scamDetected": true,
  "scamType": "banking_fraud",
  "confidence": 0.92,
  "engagementMetrics": {
    "engagementDurationSeconds": 420,
    "totalMessagesExchanged": 18
  },
  "extractedIntelligence": {
    "bankAccounts": ["1234567890123456"],
    "upiIds": ["scammer@paytm"],
    "phoneNumbers": ["+91-9876543210"],
    "beneficiaryNames": ["Rahul Kumar"],
    "phishingLinks": ["http://fake-bank-verify.com"],
    "ifscCodes": ["SBIN0001234"],
    "bankNames": ["State Bank of India"],
    "whatsappNumbers": [],
    "emails": [],
    "other_critical_info": [
      {"label": "TeamViewer ID", "value": "123456789"}
    ]
  },
  "agentNotes": "Scammer used urgency tactics and payment redirection",
  "agentResponse": "Oh no! Which account is blocked?"
}
```

</details>

#### `GET /health`

Health check endpoint.

```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

### Scam Types

The system classifies scams into the following categories (generic detection — not limited to these):

| Type | Description |
|------|-------------|
| `banking_fraud` | Fake bank alerts, account blocking threats |
| `upi_fraud` | Cashback scams, UPI verification requests |
| `job_offer` | Work-from-home scams, fake job offers |
| `lottery_reward` | KBC lottery, prize winning scams |
| `phishing` | Fake product offers with malicious links |
| `impersonation` | Government official, company impersonation |
| `investment_scam` | Investment and trading scheme fraud |
| `others` | Any other type of scam |

> The system is designed to detect **any** scam type generically — it does not rely on hardcoded scenario matching.


---

## 🔍 Intelligence Extraction

Sticky-Net extracts various types of actionable intelligence from scammer messages:

| Type | Pattern Examples | Validation |
|------|------------------|------------|
| **Bank Accounts** | 9-18 digit numbers, formatted with dashes | Length validation, Luhn check |
| **UPI IDs** | `name@paytm`, `phone@upi` | Known provider validation |
| **Phone Numbers** | +91-XXXXX-XXXXX, 10-digit Indian | 6-9 prefix validation |
| **IFSC Codes** | SBIN0001234 | Format: 4 letters + 0 + 6 alphanumeric |
| **Beneficiary Names** | "Account holder: Name" | Pattern matching, NER |
| **Bank Names** | SBI, HDFC, ICICI, etc. | 50+ Indian banks supported |
| **Phishing Links** | Suspicious URLs | Domain reputation, keyword analysis |
| **WhatsApp Numbers** | wa.me links, WhatsApp mentions | Number extraction |
| **Emails** | standard@email.com | RFC 5322 validation |
| **Other Intel** | TeamViewer IDs, Crypto wallets | Flexible key-value extraction |

### Extraction Architecture

The system uses a **hybrid extraction approach**:

1. **Regex Patterns** — Fast, deterministic extraction for known formats
2. **AI Extraction** — LLM-powered extraction for context-dependent values
3. **Validation** — All extracted values are validated before inclusion
4. **Deduplication** — Merged results from both sources, duplicates removed

---

## 🌐 Web UI Features

Sticky-Net includes a modern React-based web interface with:

### Landing Page

- **Hero Section** — Animated introduction with cyberpunk-inspired design
- **Problem Statement** — Visualizes the scale of scam attacks in India
- **Solution Overview** — How Sticky-Net works to combat scams
- **Architecture Diagram** — Interactive system architecture visualization
- **Live Demo** — Interactive chat interface to test scam detection

### Live Demo Dashboard

<p align="center">
  <img src="https://img.shields.io/badge/React-19-blue.svg" alt="React 19">
  <img src="https://img.shields.io/badge/Tailwind-CSS-38B2AC.svg" alt="Tailwind CSS">
  <img src="https://img.shields.io/badge/shadcn%2Fui-Components-000000.svg" alt="shadcn/ui">
</p>

**Key Features:**

- ✨ **Real-time Chat Interface** — Test scam messages against the AI honeypot
- 💾 **Conversation History** — Save and manage multiple conversation threads
- 📊 **Intelligence Display** — Visual extraction of bank accounts, UPI IDs, phone numbers
- 🎭 **Sample Scenarios** — Pre-loaded scam examples (KYC fraud, job offers, lottery scams)
- 🔍 **Confidence Metrics** — Real-time scam confidence scores
- 🎨 **Dark Mode UI** — Cyberpunk-inspired design with smooth animations
- 📱 **Responsive Design** — Works on desktop, tablet, and mobile
- ⚡ **Backend Status** — Live connection indicator with health checks

**Tech Stack:**
- **React 19** — Latest React features with hooks
- **Tailwind CSS** — Utility-first styling
- **shadcn/ui** — High-quality UI components (Radix UI primitives)
- **Framer Motion** — Smooth page and component animations
- **Lucide React** — Modern icon library
- **LocalStorage** — Client-side conversation persistence

**Access the UI:**
1. Start the backend: `uvicorn src.main:app --reload --port 8000`
2. Start the frontend: `cd frontend && npm start`
3. Open: `http://localhost:3000`

---

## 📁 Project Structure

```
sticky-net/
├── src/
│   ├── main.py                 # FastAPI application entry point
│   ├── exceptions.py           # Custom exception classes
│   ├── static/                 # Static files for web UI
│   ├── api/
│   │   ├── routes.py           # API endpoint definitions
│   │   ├── schemas.py          # Pydantic request/response models
│   │   └── middleware.py       # Auth, CORS, timing, error handling
│   ├── detection/
│   │   ├── classifier.py       # AI scam classification (Gemini Flash)
│   │   └── detector.py         # Hybrid detection orchestrator
│   ├── agents/
│   │   ├── honeypot_agent.py   # Main engagement agent
│   │   ├── persona.py          # Victim persona management
│   │   ├── policy.py           # Engagement policy & exit conditions
│   │   ├── prompts.py          # LLM prompt templates
│   │   └── fake_data.py        # Fake data generation for luring
│   └── intelligence/
│       ├── extractor.py        # Hybrid intelligence extraction
│       └── validators.py       # Value validation utilities
├── frontend/
│   ├── src/
│   │   ├── App.js              # Main React app with landing page
│   │   ├── components/
│   │   │   ├── ChatDashboard.jsx  # Live demo interface
│   │   │   └── ui/             # shadcn/ui components
│   │   ├── hooks/              # Custom React hooks
│   │   └── lib/                # Utility functions
│   ├── public/                 # Static assets
│   ├── package.json            # Node.js dependencies
│   └── tailwind.config.js      # Tailwind CSS configuration
├── config/
│   └── settings.py             # Pydantic settings configuration
├── tests/
│   ├── conftest.py             # Pytest fixtures
│   ├── test_api.py             # API endpoint tests
│   ├── test_detection.py       # Scam detection tests
│   ├── test_agent.py           # Engagement agent tests
│   └── test_extractor.py       # Intelligence extraction tests
├── docs/
│   ├── ARCHITECTURE.md         # Detailed architecture documentation
│   ├── COMPLETE_FLOW.md        # End-to-end flow documentation
│   └── DOCUMENTATION.md        # Additional documentation
├── multi-turn-testing/
│   ├── judge_simulator.py      # Multi-turn conversation testing
│   ├── scenarios/              # Test scenario definitions
│   └── logs/                   # Test execution logs
├── secrets/
│   └── service-account.json    # GCP credentials (gitignored)
├── Dockerfile                  # Production Docker image
├── docker-compose.yml          # Local development with Firestore
├── pyproject.toml              # Python project configuration
├── requirements.txt            # Pip requirements (generated)
└── README.md                   # This file
```

---

## 🧪 Testing

Sticky-Net includes comprehensive testing infrastructure for validation and quality assurance.

### Unit Tests

Run the full test suite using pytest:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests with verbose output
.venv/bin/python -m pytest tests/ -v

# Run specific test files
.venv/bin/python -m pytest tests/test_api.py -v
.venv/bin/python -m pytest tests/test_detection.py -v
.venv/bin/python -m pytest tests/test_agent.py -v
.venv/bin/python -m pytest tests/test_extractor.py -v

# Run with coverage report
.venv/bin/python -m pytest tests/ --cov=src --cov-report=html
```

**Test Coverage:**
- ✅ API endpoint validation (auth, request/response schemas)
- ✅ Scam detection logic (regex patterns, AI classification)
- ✅ Engagement agent behavior (persona, response generation)
- ✅ Intelligence extraction (regex + AI hybrid)
- ✅ Exit conditions & engagement policy
- ✅ Fake data generation
- ✅ Input validation & error handling

### Multi-Turn Scenario Testing

The `multi-turn-testing/` directory contains the **Judge Simulator** — a tool that simulates hackathon judges testing the API with realistic multi-turn scam conversations.

**Features:**
- 📝 **Pre-scripted scenarios** in JSON format (banking fraud, job scams, lottery scams)
- 🔄 **Multi-turn conversations** with intelligent turn-by-turn validation
- 📊 **Detailed logging** of API responses, intelligence extraction, metrics
- ✅ **Validation checks** for scam detection, intelligence extraction, engagement quality

**Run the Judge Simulator:**

```bash
# Test all scenarios
python multi-turn-testing/judge_simulator.py --url http://localhost:8000

# Test specific scenario
python multi-turn-testing/judge_simulator.py \
  --scenario multi-turn-testing/scenarios/01_banking_kyc_fraud.json

# With custom API key
python multi-turn-testing/judge_simulator.py \
  --url http://localhost:8000 \
  --api-key your-api-key
```

**Available Test Scenarios:**
- `01_banking_kyc_fraud.json` — Fake bank KYC update scam
- `02_job_offer_scam.json` — Work-from-home payment scam
- `03_lottery_prize_scam.json` — KBC lottery winner scam
- `04_impersonation_scam.json` — Government official impersonation
- `05_payment_fraud.json` — Payment redirection scam

**Output:**
- Logs saved to `multi-turn-testing/logs/`
- Timestamped JSON logs with full API responses
- Summary reports with pass/fail validation

### Frontend Testing

```bash
cd frontend

# Run React tests
npm test

# Run with coverage
npm test -- --coverage
```

### Integration Testing

Test the full stack (backend + frontend):

1. Start backend: `uvicorn src.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm start`
3. Open browser: `http://localhost:3000`
4. Use the Live Demo to test scam scenarios interactively

---

## 🚢 Deployment

### Google Cloud Run Deployment

Sticky-Net is designed for serverless deployment on Google Cloud Run.

**Prerequisites:**
- GCP project with billing enabled
- `gcloud` CLI installed and authenticated
- Vertex AI API enabled
- Firestore database created

**Deploy to Cloud Run:**

```bash
# Set environment variables
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
export SERVICE_NAME=sticky-net

# Build and push container
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  --set-env-vars API_KEY=your-secure-api-key \
  --set-env-vars PORT=8080 \
  --memory 2Gi \
  --timeout 90s \
  --max-instances 10
```

**Frontend Deployment:**

The frontend can be deployed to:
- **Vercel** — `cd frontend && vercel deploy`
- **Netlify** — `cd frontend && npm run build && netlify deploy --prod --dir=build`
- **Firebase Hosting** — `firebase deploy --only hosting`
- **GitHub Pages** — Configure in repository settings

Update `REACT_APP_API_URL` to point to your Cloud Run backend URL.

### Docker Deployment

```bash
# Build production image
docker build -t sticky-net:latest .

# Run in production mode
docker run -d \
  -p 8000:8000 \
  -e API_KEY=your-api-key \
  -e GOOGLE_CLOUD_PROJECT=your-project \
  -e PORT=8000 \
  -e DEBUG=false \
  -v /path/to/secrets:/app/secrets:ro \
  --name sticky-net \
  sticky-net:latest
```

### Environment Variables for Production

```bash
# Security
API_KEY=strong-random-api-key-here
DEBUG=false

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-production-project-id
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/service-account.json

# Models (use stable versions in production)
FLASH_MODEL=gemini-3-flash-preview
PRO_MODEL=gemini-3-pro-preview
FALLBACK_FLASH_MODEL=gemini-2.5-flash
FALLBACK_PRO_MODEL=gemini-2.5-pro

# Timeouts & Limits
PORT=8080
API_TIMEOUT_SECONDS=90
MAX_ENGAGEMENT_TURNS_CAUTIOUS=10
MAX_ENGAGEMENT_TURNS_AGGRESSIVE=25
MAX_ENGAGEMENT_DURATION_SECONDS=600
```

---

## 📚 Documentation

For more detailed information, see:

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Detailed system architecture and design decisions |
| [COMPLETE_FLOW.md](docs/COMPLETE_FLOW.md) | End-to-end request lifecycle with code examples |
| [DOCUMENTATION.md](docs/DOCUMENTATION.md) | Additional technical documentation |
| [VISUAL_DESIGN_SPEC.md](docs/VISUAL_DESIGN_SPEC.md) | Frontend design system and UI specifications |
| [TEST_RESULTS.md](multi-turn-testing/TEST_RESULTS.md) | Multi-turn testing results and analysis |

### Milestone Documentation

The project is organized into 6 development milestones with detailed instructions:

1. **Project Setup** — Scaffolding, dependencies, Docker, local dev
2. **API Layer** — FastAPI endpoints, authentication, request validation
3. **Scam Detection** — Fraud indicator analysis, confidence scoring
4. **Agent Engagement** — Agent with human persona, multi-turn conversations
5. **Intelligence Extraction** — Bank/UPI/URL pattern extraction
6. **Deployment** — GCP Cloud Run deployment, CI/CD pipeline

Each milestone has detailed instructions in `.github/instructions/milestone-*.instructions.md`

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Guidelines:**
- Follow PEP 8 style guidelines (100 char line limit)
- Add type hints to all functions
- Write docstrings (Google style)
- Add unit tests for new features
- Update documentation as needed

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🏆 Submission Information

| Field | Value |
|-------|-------|
| **Deployed URL** | `https://<your-cloud-run-url>/api/v1/analyze` |
| **API Key** | Sent via `x-api-key` header |
| **GitHub URL** | [github.com/heyitsguatham/sticky-net](https://github.com/heyitsguatham/sticky-net) |
| **Method** | `POST` |
| **Response Time** | < 30 seconds per request |
| **Max Turns** | Supports up to 10+ sequential requests per session |

---

## 🙏 Acknowledgments

- **Google Gemini Team** — For the powerful AI models
- **FastAPI** — For the excellent web framework
- **shadcn/ui** — For the beautiful UI components
- **Framer Motion** — For smooth animations
- **Law Enforcement Agencies** — Fighting scams in India

---

## 📞 Contact

**Project Repository:** [github.com/heyitsguatham/sticky-net](https://github.com/heyitsguatham/sticky-net)

**Reporting Scams in India:**
- National Cyber Crime Reporting Portal: [cybercrime.gov.in](https://cybercrime.gov.in)
- Helpline: 1930

---

<p align="center">
  <strong>Built with ❤️ for fighting scammers</strong>
</p>

<p align="center">
  <sub>Sticky-Net: The trap that bites back 🕷️🕸️</sub>
</p>
