# Sticky-Net Honeypot — Full Evaluation Report

> Generated: February 20, 2026
> Test Job ID: `c0e17b2c-e38c-4112-a8a1-a4047578ba3f`
> Mode: `official` (all 3 scenarios)

---

## Table of Contents

1. [What the Spec Files Ask For](#1-what-the-spec-files-ask-for)
2. [How the Tester Evaluates](#2-how-the-tester-evaluates)
3. [Final Scores — Latest Run](#3-final-scores--latest-run)
4. [Per-Scenario Deep Dive](#4-per-scenario-deep-dive)
5. [What We Are Extracting](#5-what-we-are-extracting)
6. [Timings](#6-timings)
7. [Why the Overall Score Is Lower Than Individual Scores](#7-why-the-overall-score-is-lower-than-individual-scores)
8. [Is the Tester-Agent Testing Correctly?](#8-is-the-tester-agent-testing-correctly)
9. [Score Comparison — Before vs After Fixes](#9-score-comparison--before-vs-after-fixes)
10. [Future Improvements Required](#10-future-improvements-required)
11. [How Our Project Is Structured](#11-how-our-project-is-structured)

---

## 1. What the Spec Files Ask For

There are two governing documents:

| Document | Role |
|---|---|
| `Honeypot API Evaluation System Documentation Updated - feb 19.md` | Defines the entire scoring rubric, API contract, and evaluation process |
| `Scam_Detection_API_Endpoint_Resubmission.md` | Resubmission checklist — fix issues, match format, stable endpoint, public GitHub |

### 1.1 API Contract (what the spec mandates)

**Every request the evaluator sends:**
```json
{
  "sessionId": "uuid-v4",
  "message": { "sender": "scammer", "text": "...", "timestamp": "ISO8601" },
  "conversationHistory": [ ... ],
  "metadata": { "channel": "SMS", "language": "English", "locale": "IN" }
}
```

**Turn-by-turn response (what the spec mandates):**
```json
{ "status": "success", "reply": "Your honeypot response here" }
```

**Final output (sent when `[CONVERSATION_END]` is received):**
```json
{
  "sessionId": "abc123",
  "scamDetected": true,
  "totalMessagesExchanged": 18,
  "engagementDurationSeconds": 240,
  "extractedIntelligence": {
    "phoneNumbers": ["+91-9876543210"],
    "bankAccounts": ["1234..."],
    "upiIds": ["scammer@fakeupi"],
    "phishingLinks": ["http://malicious.com"],
    "emailAddresses": ["scammer@fake.com"]
  },
  "agentNotes": "...",
  "scamType": "bank_fraud",
  "confidenceLevel": 0.95
}
```

### 1.2 Submission Requirements (per both files)

| Requirement | Status |
|---|---|
| Live deployed HTTPS endpoint | ✅ Running (port 8080 / Cloud Run) |
| Valid API key (`x-api-key` header) | ✅ `test-api-key` |
| Public GitHub repository | ⚠️ Required but **code quality scored 0** (not yet linked) |
| README with setup, approach, API docs | ⚠️ Needs improvement |
| Response within 30 seconds | ✅ ~20s average per turn |
| Return HTTP 200 on success | ✅ |
| No hardcoded test responses | ✅ Generic AI-driven detection |

---

## 2. How the Tester Evaluates

The tester-agent (branch: `tester-agent`, running on port 8090) implements the spec's scoring rubric exactly.  
It runs **3 official scenarios** with pre-planted fake intelligence, drives up to **10 turns** of conversation, then sends `[CONVERSATION_END]` and scores the final output.

### 2.1 The 5 Scoring Categories (100 pts total per scenario)

#### Category 1 — Scam Detection (20 pts)

| Condition | Points |
|---|---|
| `scamDetected: true` in final output | **20** |
| `scamDetected: false` or missing | **0** |

Binary. No partial credit. If the API doesn't confirm it detected a scam in the final output, it scores **zero on this category** regardless of conversation quality.

---

#### Category 2 — Extracted Intelligence (30 pts)

Points per item = `30 ÷ total fake data fields in scenario`

The tester plants specific fake phone numbers, UPI IDs, bank accounts, links, emails, and order numbers into the scammer's dialogue. It checks the `extractedIntelligence` object in the final output against this planted data to award points.

| Data Type | Spec Mandates |
|---|---|
| `phoneNumbers` | Any phone numbers shared by scammer |
| `bankAccounts` | Any bank account numbers mentioned |
| `upiIds` | Any UPI IDs provided |
| `phishingLinks` | Any suspicious URLs shared |
| `emailAddresses` | Any email addresses shared |
| `caseIds` | Any case/reference IDs |
| `policyNumbers` | Any policy numbers |
| `orderNumbers` | Any order IDs |

---

#### Category 3 — Conversation Quality (30 pts)

| Sub-category | Max | Threshold |
|---|---|---|
| Turn count | 8 pts | ≥8 turns=8pts, ≥6=6pts, ≥4=3pts |
| Questions asked | 4 pts | ≥5=4pts, ≥3=2pts, ≥1=1pt |
| Relevant questions | 3 pts | ≥3 investigative=3pts, ≥2=2pts, ≥1=1pt |
| Red flag identification | 8 pts | ≥5=8pts, ≥3=5pts, ≥1=2pts |
| Information elicitation | 7 pts | Each attempt earns 1.5pts (max 7) |

Investigative = questions about identity, company, address, website, credentials.

---

#### Category 4 — Engagement Quality (10 pts)

| Condition | Points |
|---|---|
| `engagementDurationSeconds > 0` | 1 pt |
| `engagementDurationSeconds > 60` | 2 pts |
| `engagementDurationSeconds > 180` | 1 pt |
| `totalMessagesExchanged > 0` | 2 pts |
| `totalMessagesExchanged ≥ 5` | 3 pts |
| `totalMessagesExchanged ≥ 10` | 1 pt |

---

#### Category 5 — Response Structure (10 pts)

| Field | Points | Required? |
|---|---|---|
| `sessionId` | 2 pts | Required |
| `scamDetected` | 2 pts | Required |
| `extractedIntelligence` | 2 pts | Required |
| `totalMessagesExchanged` + `engagementDurationSeconds` | 1 pt | Optional |
| `agentNotes` | 1 pt | Optional |
| `scamType` | 1 pt | Optional |
| `confidenceLevel` | 1 pt | Optional |

Missing required fields = **−1 point penalty each**.

---

### 2.2 Final Score Formula

```
Scenario Score = Σ (ScenarioScore × ScenarioWeight / 100)
Final Score    = (Scenario Score × 0.9) + Code Quality Score
```

Code quality is evaluated from the GitHub URL (0–10 pts). If no URL is provided or it can't be reviewed, it defaults to **0**.

---

## 3. Final Scores — Latest Run

> All fixes applied (Fix 1–5). Job completed at 09:25 PM IST, Feb 20 2026.

### 3.1 Summary

| Metric | Value |
|---|---|
| **Final Score** | **89.73 / 100** |
| **Weighted Scenario Score** | **99.7 / 100** |
| **Code Quality Score** | **0 / 10** |

### 3.2 Per-Scenario Scores

| Scenario | Weight | Score | Contribution |
|---|---|---|---|
| Bank Fraud – Account Compromise | 35% | **100 / 100** | 35.0 pts |
| UPI Cashback Scam | 35% | **100 / 100** | 35.0 pts |
| Fake Product Offer / Phishing Link | 30% | **99 / 100** | 29.7 pts |
| **Weighted Scenario Total** | | | **99.7** |
| × 0.9 (scenario weight) | | | **89.73** |
| + Code Quality | | | **+0** |
| **FINAL** | | | **89.73 / 100** |

### 3.3 Score Breakdown — All Categories

| Category | Max | Bank Fraud | UPI Cashback | Phishing |
|---|---|---|---|---|
| Scam Detection | 20 | ✅ 20 | ✅ 20 | ✅ 20 |
| Extracted Intelligence | 30 | ✅ 30 | ✅ 30 | ✅ 30 |
| Conversation Quality | 30 | ✅ 30 | ✅ 30 | ⚠️ 29 |
| Engagement Quality | 10 | ✅ 10 | ✅ 10 | ✅ 10 |
| Response Structure | 10 | ✅ 10 | ✅ 10 | ✅ 10 |
| **Total** | **100** | **100** | **100** | **99** |

---

## 4. Per-Scenario Deep Dive

### 4.1 Bank Fraud – Account Compromise (100/100, Weight 35%)

```
Elapsed: 201.45 seconds (~3.4 min)
Turns: 10 turns, 20 messages exchanged
scamDetected: true
confidenceLevel: 1.0
scamType: banking_fraud
```

**Planted fake intelligence (all extracted ✅):**
| Field | Planted Value | Extracted |
|---|---|---|
| `phoneNumbers` | `+91-9876543210` | ✅ Found |
| `bankAccounts` | `4521876309124521` | ✅ Found |
| `upiIds` | `sbi.verify.kyc@fakebank` | ✅ Found |
| `emailAddresses` | `fraud.dept@sbi-secure-verify.in` | ✅ Found |

Points per item = 30 ÷ 4 = **7.5 pts each**

**Conversation quality metrics:**
- Questions asked: 10 → **4/4 pts**
- Relevant questions: 5 → **3/3 pts**
- Red flags found: 16 → **8/8 pts**
- Elicitation attempts: 7 → **7/7 pts** (7 × 1.5 = 10.5, capped at 7)
- Turn count: 10 → **8/8 pts**

---

### 4.2 UPI Cashback Scam (100/100, Weight 35%)

```
Elapsed: 203.75 seconds (~3.4 min)
Turns: 10 turns, 20 messages exchanged
scamDetected: true
confidenceLevel: 0.8
scamType: lottery_reward  ⚠️ (actual: upi_fraud — classification mismatch, but doesn't affect score)
```

**Planted fake intelligence (all extracted ✅):**
| Field | Planted Value | Extracted |
|---|---|---|
| `phoneNumbers` | `+91-8765432109` | ✅ Found |
| `upiIds` | `cashback.claim2024@fakeupi` | ✅ Found |
| `upiIds` | `phonepe.reward@scamwallet` | ✅ Found |
| `phishingLinks` | `http://phonepe-cashback-claim.fake-rewards.in/claim?id=PP2024LKY` | ✅ Found |

Points per item = 30 ÷ 4 = **7.5 pts each**

> Previously scored 77.5/100 on this scenario (Fix 5 before: scammer messages truncated → UPI IDs never revealed in conversation)

---

### 4.3 Fake Product Offer / Phishing Link (99/100, Weight 30%)

```
Elapsed: 205.77 seconds (~3.4 min)
Turns: 10 turns, 20 messages exchanged
scamDetected: true
confidenceLevel: 0.8
scamType: others  ⚠️ (actual: phishing — classification mismatch, but doesn't affect score)
```

**Planted fake intelligence (all extracted ✅):**
| Field | Planted Value | Extracted |
|---|---|---|
| `phoneNumbers` | `+91-7654321098` | ✅ Found |
| `phishingLinks` | `http://amaz0n-deals.fake-site.com/claim?id=AMZ12345` | ✅ Found |
| `phishingLinks` | `http://secure-amazon-kyc.fakestore.in/verify` | ✅ Found |
| `emailAddresses` | `offers@fake-amazon-deals.in` | ✅ Found |
| `orderNumbers` | `AMZ-ORD-2024-IND-98745` | ✅ Found |

Points per item = 30 ÷ 5 = **6.0 pts each**

**Why 99 instead of 100?**
Conversation quality scored 29/30. Specifically:
```
relevant_questions: 2  → 2/3 pts
(threshold for full marks: ≥3 investigative questions)
```
The honeypot asked only 2 questions classified as investigative (identity/company/address/website) — needed 3 for full marks. Lost **1 point** here.

---

## 5. What We Are Extracting

The extraction pipeline (`src/intelligence/extractor.py`) uses regex patterns to capture:

| Type | Pattern Examples | Current Status |
|---|---|---|
| `phoneNumbers` | `+91-XXXXXXXXXX`, `91XXXXXXXXXX`, 10-digit mobile | ✅ Working |
| `bankAccounts` | 12–19 digit numeric account numbers | ✅ Working |
| `upiIds` | `name@bank`, `name@upi`, `name@okaxis` etc. | ✅ Working |
| `phishingLinks` | `http://`, `https://` URLs | ✅ Working |
| `emailAddresses` | Standard email format | ✅ Working |
| `caseIds` | Reference IDs like `AMZ12345`, `PP2024LKY` | ✅ Working |
| `policyNumbers` | Policy number patterns | ✅ Working |
| `orderNumbers` | Order IDs like `AMZ-ORD-2024-IND-98745` | ✅ Working |
| `suspiciousKeywords` | Urgency/scam trigger phrases | ✅ Bonus extraction |

**Extraction source:** The extractor runs on the **full conversation history** (all honeypot + scammer messages), not just the most recent message.

**Notable behavior:** Our extractor sometimes over-extracts — e.g., `offers@fake` captured from a URL fragment as a UPI ID. This doesn't lose points but shows some noise in the regexes.

---

## 6. Timings

### Per-Scenario Duration

| Scenario | Elapsed | Turns | Avg per Turn |
|---|---|---|---|
| Bank Fraud | 201.45s | 10 | ~20.1s/turn |
| UPI Cashback | 203.75s | 10 | ~20.4s/turn |
| Phishing | 205.77s | 10 | ~20.6s/turn |
| **Total job duration** | **~611s (~10.2 min)** | 30 | **~20.4s/turn avg** |

### Where Time Is Spent per Turn

```
Scammer AI (gemini-2.5-flash, tester)  → ~5–8s
Honeypot AI (gemini-2.5-flash, port 8080) → ~8–12s
Network round-trip                     → <0.5s
─────────────────────────────────────────────
Total per turn                         → ~15–20s
```

### Spec Limit

The spec mandates: **requests must complete within 30 seconds**. We're averaging ~20s — within the 30s limit, but only by ~10s of margin.

### Engagement Duration Reporting

Our `engagementDurationSeconds` is currently reported as **525 seconds** for all scenarios, which is a hardcoded value from the `[CONVERSATION_END]` handler. The **actual** measured elapsed per scenario is ~201–206s. The tester scores based on the reported value (>180s earns full 4 pts) so this passes — but it's inaccurate.

---

## 7. Why the Overall Score Is Lower Than Individual Scores

This is the most important question.

### The Formula

```
Final Score = (Weighted Scenario Score × 0.9) + Code Quality Score
```

Our numbers:
```
Weighted Scenario Score = 99.7
99.7 × 0.9              = 89.73
Code Quality Score      = 0.0
─────────────────────────────
Final Score             = 89.73
```

### The 10-Point Gap Explained

**The spec splits the final score into two parts:**
- **90% → Scenario performance** (how well you detect, engage, extract)
- **10% → Code quality** (evaluated from your GitHub repository)

Even if you score **100/100 on every scenario**, the maximum you can get **without code quality** is:

```
100 × 0.9 + 0 = 90.0
```

We're at **89.73** because of one lost point in phishing conversation quality.  
The remaining **10 points** are entirely from code quality — which requires:
1. A public GitHub repository URL submitted with the API
2. Clean, readable, well-documented code
3. Proper README with setup instructions, tech stack, approach

**Currently: code quality = 0** because the GitHub URL was not submitted (or the evaluator couldn't score it in local testing mode).  

**The ceiling without code quality: 90 pts**  
**The ceiling with perfect code quality: 100 pts**

---

## 8. Is the Tester-Agent Testing Correctly?

**Yes — the tester-agent accurately implements the spec.**

Here's the verification:

| Spec Requirement | Tester Implementation | Status |
|---|---|---|
| 3 scenarios: bank_fraud (35%), upi_fraud (35%), phishing (30%) | ✅ Exact weights used | Correct |
| Up to 10 turns per scenario | ✅ 10 turns used | Correct |
| Scam Detection: 20 pts binary | ✅ Checks `scamDetected` field | Correct |
| Intelligence: 30pts ÷ fake_data_count | ✅ Dynamic scoring per item | Correct |
| Conversation Quality: 5 sub-categories | ✅ turn_count, questions, relevance, red_flags, elicitation | Correct |
| Engagement Quality: 10pts across 6 conditions | ✅ Duration + message count thresholds | Correct |
| Response Structure: 7 fields, 2 required | ✅ sessionId, scamDetected, extractedIntelligence required | Correct |
| Final score = scenario × 0.9 + code | ✅ Applied correctly | Correct |
| `[CONVERSATION_END]` to collect final output | ✅ Sent after max turns | Correct |
| AI-driven scammer using Gemini | ✅ `gemini-2.5-flash` via Vertex AI | Correct |
| Request format matches spec | ✅ sessionId + message + conversationHistory + metadata | Correct |

**Fixes applied to tester to make it work correctly:**

| Fix | Issue | Solution |
|---|---|---|
| Fix 3 | `list_jobs` crashed on `None` final_score | `(j.get("final_score") or {}).get("final_score")` |
| Fix 4 | Scammer Gemini calls failed (no credentials loaded) | Added `load_dotenv()` + credential path resolution in `app.py` |
| Fix 5 | Scammer messages truncated — UPI/phone never revealed | `max_output_tokens`: 200→400, `thinking_budget=0` |

---

## 9. Score Comparison — Before vs After Fixes

| | Before All Fixes | After All Fixes |
|---|---|---|
| Bank Fraud | 99 / 100 | **100 / 100** |
| UPI Cashback | **77.5 / 100** | **100 / 100** |
| Phishing | 82 / 100 | **99 / 100** |
| Weighted Scenario | 86.38 | **99.7** |
| Final Score | **77.74** | **89.73** |
| Improvement | — | **+11.99 pts** |

### Root Causes Fixed

| Fix | What Changed | Score Impact |
|---|---|---|
| Fix 1 — `[CONVERSATION_END]` handling | Honeypot now returns full final output with intelligence when conversation ends | `scamDetected: false → true` on all scenarios; UPI/phishing went from 0→20pts on scam detection |
| Fix 2 — Model changed to `gemini-2.5-flash` | Eliminated 26s timeouts per turn caused by nonexistent `gemini-3-pro-preview` model | Stable responses, full conversation quality engagement |
| Fix 3 — Tester `list_jobs` bug | Prevented 500 errors when checking job status | Operational stability |
| Fix 4 — Tester dotenv/credentials | Scammer agent started using real Gemini AI instead of hardcoded fallback messages | All scammer messages became natural and carried fake intel |
| Fix 5 — Scammer `max_output_tokens` + `thinking_budget=0` | Scammer messages no longer truncated mid-sentence | UPI IDs and phone numbers now appear fully in conversation → extracted by honeypot |

---

## 10. Future Improvements Required

### 10.1 Critical (Direct Score Impact)

| Issue | Impact | Fix |
|---|---|---|
| **Code quality = 0/10** | Caps final score at 90 regardless of scenario performance | Submit proper GitHub URL; add README with setup instructions, architecture, approach |
| **Phishing loses 1 pt (relevant_questions: 2/3)** | Phishing = 99 instead of 100 | Tune engagement agent to ask at least 3 investigative questions (identity, org, website, address) per conversation |

### 10.2 High Priority (Robustness)

| Issue | Current Behavior | Improvement |
|---|---|---|
| `engagementDurationSeconds` hardcoded to 525 | Reports incorrect duration for every scenario | Track actual session start time; compute real elapsed when `[CONVERSATION_END]` arrives |
| `scamType` misclassification | UPI scam → `lottery_reward`; phishing → `others` | Improve scam type classifier to map correctly (doesn't affect score but looks inaccurate in logs) |
| Response time ~20s/turn | Close to the 30s spec limit | Add caching for system prompt generation; consider streaming responses |
| In-memory session store | Sessions lost on server restart | Implement Firestore persistence (already scaffolded in codebase) |
| Over-extraction noise | Captures `offers@fake` as a UPI ID from URL fragments | Add post-processing to filter malformed/partial extractions |

### 10.3 Medium Priority (Polish)

| Issue | Improvement |
|---|---|
| `confidenceLevel` stuck at 0.8 or 1.0 | Compute actual confidence from classifier signal strength |
| `agentNotes` is templated | Generate meaningful agent notes summarising the specific scam tactics observed |
| No conversation context across restarts | Firestore-backed history would survive API restarts |
| Phone number duplicates in extraction | `+91-9876543210` and `919876543210` both extracted — deduplicate and normalise to E.164 format |

### 10.4 Low Priority (Code Quality Boost)

| Improvement | Benefit |
|---|---|
| Add unit tests for extractor patterns | Code quality review |
| Add docstrings to all public functions | Code quality review |
| Create `.env.example` with all variables documented | GitHub repo requirement |
| Architecture diagram in README | Hackathon evaluators appreciate it |
| Add `/health` detailed endpoint with model/version info | Professional impression |

---

## 11. How Our Project Is Structured

### Architecture

```
[Scammer (tester-agent AI)] ←→ [Honeypot API (main branch)]
         port 8090                      port 8080

Honeypot flow:
  Message → Regex Pre-filter → AI Scam Classifier → Engagement Agent → Intelligence Extractor
                                 gemini-2.5-flash        gemini-2.5-flash     regex pipeline
```

### Key File Map

| File | Purpose |
|---|---|
| `src/api/routes.py` | Main request handler; `[CONVERSATION_END]` final output path |
| `src/api/schemas.py` | Pydantic request/response models |
| `src/detection/classifier.py` | AI scam classifier (Stage 1) |
| `src/engagement/agent.py` | Engagement agent driving multi-turn conversation (Stage 3) |
| `src/intelligence/extractor.py` | Regex-based intelligence extractor (Stage 4) |
| `src/session/store.py` | In-memory session state management |
| `config/settings.py` | Environment config (models, API keys, timeouts) |

### Current State — Scores at a Glance

```
┌─────────────────────────────────────────┐
│  LATEST RUN RESULTS (Feb 20 2026)       │
│                                         │
│  Bank Fraud    100 / 100  ✅ Perfect    │
│  UPI Cashback  100 / 100  ✅ Perfect    │
│  Phishing       99 / 100  ⚠️  -1 pt    │
│                                         │
│  Weighted Scenario Score:  99.7 / 100  │
│  Code Quality:              0.0 / 10   │
│                                         │
│  FINAL SCORE:              89.73 / 100 │
│                                         │
│  Potential with code quality: 99.73    │
└─────────────────────────────────────────┘
```

### What Is Working

- ✅ Scam detected correctly on all 3 scenario types
- ✅ All planted intelligence extracted (4/4 bank, 4/4 UPI, 5/5 phishing)
- ✅ 10-turn engagement maintained across all scenarios
- ✅ Response structure fully compliant (all 7 required/optional fields)
- ✅ Engagement metrics exceed all thresholds
- ✅ Multi-turn conversation context maintained within a session
- ✅ Both servers stable across 10+ minute test runs
- ✅ Gemini AI driving natural, varied responses (not hardcoded)

### What Is Not Working

- ❌ Code quality not submitted → 0/10 pts (10% of final score gone)
- ⚠️ `engagementDurationSeconds` hardcoded (cosmetic, doesn't lose score)
- ⚠️ Phishing loses 1 pt on relevant questions (needs 3 investigative, gets 2)
- ⚠️ `scamType` occasionally misclassified (no score impact, but wrong in logs)
- ⚠️ Phone number deduplication creates noisy extraction output
