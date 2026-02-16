# Improvement Analysis Report

> **Current Score: 35/100** | Target: 85+/100  
> Based on: [HACKATHON_EVALUATION_LOG_ANALYSIS.md](HACKATHON_EVALUATION_LOG_ANALYSIS.md), [EVAL_SYS.md](../final-submission-docs/EVAL_SYS.md), [SAMPLE_CASE.md](../final-submission-docs/SAMPLE_CASE.md)

---

## Table of Contents

1. [Scoring System Deep-Dive](#1-scoring-system-deep-dive)
2. [Score Reconstruction — What We Likely Got](#2-score-reconstruction--what-we-likely-got)
3. [Critical Architecture Mismatch](#3-critical-architecture-mismatch)
4. [Issue-by-Issue Breakdown](#4-issue-by-issue-breakdown)
5. [Improvement Plan — Prioritized](#5-improvement-plan--prioritized)
6. [Implementation Roadmap](#6-implementation-roadmap)

---

## 1. Scoring System Deep-Dive

The evaluator scores each **scenario** independently out of 100, then takes a weighted average across all scenarios.

### Per-Scenario Scoring (100 pts)

| Category | Max Points | How It's Scored |
|----------|-----------|-----------------|
| **Scam Detection** | 20 | `scamDetected: true` in finalOutput → 20 pts. False/missing → 0 |
| **Intelligence Extraction** | 40 | 10 pts per type matched against `fakeData` (bank, UPI, phone, link) |
| **Engagement Quality** | 20 | Duration > 0s (+5), > 60s (+5), Messages > 0 (+5), Messages ≥ 5 (+5) |
| **Response Structure** | 20 | `status` (+5), `scamDetected` (+5), `extractedIntelligence` (+5), `engagementMetrics` (+2.5), `agentNotes` (+2.5) |

### Key Evaluation Mechanics
- **Multi-turn**: Up to 10 turns per scenario. An AI generates scammer follow-ups based on our replies.
- **Fake data**: Each scenario has pre-planted data (`fakeData`) the scammer AI will share during conversation. The evaluator checks if we **extracted** that specific data.
- **finalOutput**: The evaluator checks the **GUVI callback** payload, NOT the HTTP response. Our `/api/v1/analyze` returns `{status, reply}` but scoring is based on what we send to `hackathon.guvi.in/api/updateHoneyPotFinalResult`.
- **Weighted average**: `Final Score = Σ(Scenario_Score × Weight)`. Poor performance on high-weight scenarios kills the total.

### Sample Scenarios (from SAMPLE_CASE.md)

| Scenario | Type | fakeData to Extract | Weight |
|----------|------|---------------------|--------|
| bank_fraud | banking_fraud | bankAccount, upiId, phoneNumber | 10 (35% est.) |
| upi_fraud | upi_fraud | upiId, phoneNumber | 10 (35% est.) |
| phishing_link | phishing | phishingLink, emailAddress | 10 (30% est.) |

---

## 2. Score Reconstruction — What We Likely Got

### Understanding the Evaluation Flow

The evaluator:
1. Sends `initialMessage` as Turn 1
2. Reads our `reply` from the HTTP response
3. AI generates scammer follow-up (injecting fakeData gradually)
4. Sends follow-up as Turn 2, then 3, etc. up to 10
5. After last turn, waits 10 seconds for our `finalOutput` via GUVI callback
6. Scores based on the **last callback** received for each session

### What Our System Does Per Request

For **every** incoming message (every turn), we:
1. Classify the message (LLM call → ~6-16s)
2. Generate engagement response (LLM call → ~6-12s)  
3. Extract intelligence from agent's JSON response
4. Send a GUVI callback **on every turn** with current cumulative intel
5. Return `{status: "success", reply: "..."}` to evaluator

### The Critical Problem: Callback Payload Structure

Our GUVI callback sends:
```json
{
  "sessionId": "...",
  "scamDetected": true,
  "totalMessagesExchanged": 18,
  "extractedIntelligence": {
    "bankAccounts": [...],
    "upiIds": [...],
    "phishingLinks": [...],
    "phoneNumbers": [...],
    "suspiciousKeywords": [...]
  },
  "agentNotes": "..."
}
```

The evaluator expects:
```json
{
  "sessionId": "...",
  "scamDetected": true,
  "totalMessagesExchanged": 18,
  "extractedIntelligence": {
    "bankAccounts": [...],
    "upiIds": [...],
    "phishingLinks": [...],
    "phoneNumbers": [...],
    "emailAddresses": [...]
  },
  "agentNotes": "...",
  "engagementMetrics": {
    "engagementDurationSeconds": ...,
    "totalMessagesExchanged": ...
  }
}
```

**Missing from our callback:**
- ❌ `engagementMetrics` field entirely (costs 2.5 pts per scenario)
- ❌ `emailAddresses` field (phishing scenario has `emailAddress` in fakeData — costs 10 pts on that scenario)
- ❌ `engagementDurationSeconds` is always 0 in our code (costs 10 pts per scenario — both duration thresholds)

### Estimated Score Reconstruction

Assuming 3 scenarios (bank_fraud 35%, upi_fraud 35%, phishing 30%) based on EVAL_SYS.md example weights:

#### Scenario 1: bank_fraud (weight: 35%)
fakeData: `bankAccount: 1234567890123456`, `upiId: scammer.fraud@fakebank`, `phoneNumber: +91-9876543210`

| Category | Expected | Our Result | Points |
|----------|----------|------------|--------|
| Scam Detection | scamDetected=true | ✅ Sent in callback | **20** |
| Intel: bankAccount | Extract 1234567890123456 | ⚠️ Depends on scammer sharing it. Logs show we extracted it in some turns | **10** (partial) |
| Intel: upiId | Extract scammer.fraud@fakebank | ⚠️ Logs show we extracted it | **10** (partial) |
| Intel: phoneNumber | Extract +91-9876543210 | ⚠️ Logs show we extracted it | **10** (partial) |
| Engagement: duration > 0 | engagementDurationSeconds > 0 | ❌ **Always 0** in callback | **0** |
| Engagement: duration > 60 | engagementDurationSeconds > 60 | ❌ **Always 0** | **0** |
| Engagement: messages > 0 | totalMessagesExchanged > 0 | ✅ We send this | **5** |
| Engagement: messages ≥ 5 | totalMessagesExchanged ≥ 5 | ⚠️ Only if 10 turns reached | **5** (maybe) |
| Structure: status | Present | ❌ **Not in callback** | **0** |
| Structure: scamDetected | Present | ✅ Present | **5** |
| Structure: extractedIntelligence | Present | ✅ Present | **5** |
| Structure: engagementMetrics | Present | ❌ **Missing from callback** | **0** |
| Structure: agentNotes | Present | ✅ Present | **2.5** |
| **Subtotal** | | | **~62.5-72.5** |

But wait — the intelligence extraction score depends on whether the **scammer AI actually shared** the fakeData during conversation. From the logs:
- The scammer AI embeds the fakeData values in its messages (e.g., mentions `1234567890123456` as the target account)
- Our agent extracts what it sees in the scammer's messages
- But our extraction is **AI-only** — and it sometimes fails to capture values, returning 0 intel on some turns
- The evaluator likely checks the **final callback** — if our last callback had 0 intel, we get 0/40

#### Scenario 2: upi_fraud (weight: 35%)
fakeData: `upiId: cashback.scam@fakeupi`, `phoneNumber: +91-8765432109`

- Max possible extraction: 20 pts (2 items × 10 pts)
- Same structural issues as bank_fraud
- UPI fraud may use different messaging patterns our agent may not handle as well

#### Scenario 3: phishing (weight: 30%)
fakeData: `phishingLink: http://amaz0n-deals.fake-site.com/claim?id=12345`, `emailAddress: offers@fake-amazon-deals.com`

- Our callback doesn't have `emailAddresses` field → **0 pts for email extraction**
- We do extract phishing links → **10 pts possible**
- Same structural issues

### Overall Estimated Score Breakdown

| Issue | Points Lost Per Scenario | Impact |
|-------|--------------------------|--------|
| `engagementDurationSeconds` always 0 | -10 (both duration checks fail) | **Most damaging** |
| `engagementMetrics` missing from callback | -2.5 | Medium |
| `status` missing from callback | -5 | High |
| `emailAddresses` not in callback | -10 on phishing scenario | High on phishing |
| Intel extraction inconsistency | -10 to -30 variable | **Critical** |
| 504 timeout on some scenarios | -100 on that turn's callback | **Catastrophic** if that was best turn |

**Estimated per-scenario score: 30-50/100**  
**Weighted final: ~35/100** ← matches actual score

---

## 3. Critical Architecture Mismatch

### Problem: The Evaluator Expects a "Final Output", Not Per-Turn Callbacks

The evaluator documentation says:
> *"After the conversation ends, you should submit a finalOutput to the session log"*

Our system sends a callback **on every single turn**. The evaluator likely takes the **last callback** as the finalOutput. This means:

1. **If our last turn had bad intel extraction → low score** (even if earlier turns had good intel)
2. **If our last turn had `totalMessagesExchanged: 2` → low engagement score** (because each callback resets context)

### Problem: Two LLM Calls Per Request = Double Latency

Our pipeline: `Classify (LLM) → Engage (LLM)` = two sequential Gemini calls.

| Step | Latency |
|------|---------|
| Cold start (Cloud Run) | 7-8s |
| Classification (gemini-3-flash) | 6-16s |
| Engagement (gemini-3-flash) | 6-12s |
| Intel extraction + validation | <100ms |
| GUVI callback | <1s |
| **Total** | **15-37s** |

The evaluator requirement is **< 30 seconds**. We're borderline and sometimes exceed it.

### Problem: No State Accumulation Across Turns

Each request is stateless. We don't track:
- Cumulative intelligence across turns (we only extract from current turn)
- Engagement duration (always hardcoded to 0)
- Turn timing for calculating actual engagement duration
- Which fakeData we've already extracted

---

## 4. Issue-by-Issue Breakdown

### ISSUE 1: `engagementDurationSeconds` is Always 0 (CRITICAL — -10 pts/scenario)

**Where:** `src/api/routes.py` line ~370 (`AnalyzeResponse`) and callback payload  
**Why:** We never track actual duration between first and last request of a session  
**Impact:** Fails both duration checks (> 0 and > 60), losing 10 pts per scenario  

**Fix:** Track first-request timestamp per session (in-memory dict or Firestore). Calculate elapsed duration on each callback.

---

### ISSUE 2: `engagementMetrics` Missing from GUVI Callback (HIGH — -2.5 pts/scenario)

**Where:** `src/api/callback.py` — `CallbackPayload` model  
**Why:** The callback payload has `totalMessagesExchanged` at top level but no `engagementMetrics` object  
**Impact:** Evaluator checks for `engagementMetrics` field for 2.5 bonus points  

**Fix:** Add `engagementMetrics` to callback payload:
```python
class CallbackPayload(BaseModel):
    sessionId: str
    scamDetected: bool
    totalMessagesExchanged: int
    extractedIntelligence: CallbackIntelligence
    agentNotes: str
    engagementMetrics: dict = {}  # ADD THIS
```

---

### ISSUE 3: `status` Field Missing from Callback (HIGH — -5 pts/scenario)

**Where:** `src/api/callback.py` — `CallbackPayload` model  
**Why:** The response structure scoring checks for `status` field in finalOutput  
**Impact:** -5 pts per scenario  

**Fix:** Add `status: "success"` to callback payload.

---

### ISSUE 4: `emailAddresses` Not in Callback Intelligence (HIGH — -10 pts on phishing)

**Where:** `src/api/callback.py` — `CallbackIntelligence` model  
**Why:** Our callback sends `phoneNumbers`, `bankAccounts`, `upiIds`, `phishingLinks`, `suspiciousKeywords` but NOT `emailAddresses`  
**Impact:** Phishing scenario has `emailAddress: "offers@fake-amazon-deals.com"` as fakeData — we can never score those 10 pts  

**Fix:** Add `emailAddresses` to `CallbackIntelligence` and populate it from agent extraction.

---

### ISSUE 5: Intelligence Not Accumulated Across Turns (CRITICAL — variable pts)

**Where:** `src/api/routes.py` — each request processes independently  
**Why:** We extract intel only from the current turn's messages. If the scammer shared a phone number in Turn 3 but our Turn 5 callback only has Turn 5 intel, we lose that phone number.  
**Impact:** The evaluator scores the **last callback** — if we don't accumulate, we lose previously-extracted intel  

**Fix:** Maintain a per-session intelligence store (in-memory dict keyed by sessionId). On each turn:
1. Extract new intel from current turn
2. Merge with accumulated intel from previous turns
3. Send accumulated intel in callback

---

### ISSUE 6: AI-Only Extraction is Unreliable (HIGH — -10 to -30 pts)

**Where:** `src/intelligence/extractor.py` — regex extraction is `DEPRECATED`  
**Why:** The AI sometimes:
- Fails to extract obvious values from scammer messages
- Extracts the agent's own fake data instead of scammer's fakeData
- Returns 0 items despite values being present in conversation  
**Impact:** From logs — Turn 1 of Batch 3 extracted 0 intel; Turn 7 of Batch 4 extracted 0 intel  

**Fix:** 
1. **Re-enable regex extraction as validation layer** — use regex to scan the scammer's message + full conversation for known patterns (phone, bank account, UPI, URL, email)
2. **Merge AI + regex results** — union of both sets, not AI-only
3. **Always scan the latest scammer message** for fakeData patterns, regardless of what the AI thinks

---

### ISSUE 7: Two LLM Calls Per Request (MEDIUM — causes timeouts)

**Where:** `src/api/routes.py` → `detector.analyze()` + `agent.engage()`  
**Why:** Classification and engagement are separate LLM calls  
**Impact:** 15-37s latency, 504 timeout risk. Evaluator requires < 30s.  

**Fix Options:**
1. **Single-pass approach**: Skip classification for messages in active scam sessions (if sessionId already flagged). Only classify on Turn 1.
2. **Use flash model for classification** (it already does, but consider skipping entirely after Turn 1)
3. **Cache classification result per session**: Once flagged as scam, don't re-classify
4. **Parallel execution**: Run classification and engagement simultaneously (risky but faster)

---

### ISSUE 8: Agent Repeats at High Turn Counts (LOW — -engagement quality)

**Where:** `src/agents/honeypot_agent.py` — `context_window_turns: 8`  
**Why:** After Turn 8, conversation history is truncated to last 8 turns. Agent loses earlier context and starts repeating.  
**Impact:** Evaluator's scammer AI might stop providing fakeData if our responses aren't progressing  

**Fix:**  
1. Include a "conversation summary" of earlier turns when truncating
2. Track what intel was already discussed to avoid re-asking
3. Increase context window or use smarter summarization

---

### ISSUE 9: Cold Start Latency (MEDIUM — 7-8s overhead)

**Where:** Cloud Run configuration — `min-instances=0`  
**Why:** First request per batch hits cold start (import, model init, connection setup)  
**Impact:** Adds 7-8s to Turn 1 of each scenario, pushing close to 30s timeout  

**Fix:** Set `min-instances=1` in Cloud Run configuration (`--min-instances=1` in deploy command or `cloudbuild.yaml`).

---

### ISSUE 10: 504 Gateway Timeout (CRITICAL — scenario failure)

**Where:** Cloud Run default timeout is 60s, but actual processing sometimes exceeds it  
**Why:** Classification + Engagement + Retries can exceed 60s  
**Impact:** Batch 1, Request 3 got 504 — this was likely during an evaluation scenario  

**Fix:**
1. Set Cloud Run timeout to 300s (`--timeout=300`)
2. Reduce LLM call latency (use flash models, reduce prompt size)
3. Add request-level timeout tracking and abort before Cloud Run timeout hits

---

## 5. Improvement Plan — Prioritized

### Priority 0: MUST FIX (30+ pts recovery)

| # | Fix | Points Recovered | Effort |
|---|-----|-------------------|--------|
| 1 | **Add real `engagementDurationSeconds`** — track session start times and calculate elapsed | +10/scenario | Low |
| 2 | **Add `engagementMetrics` to callback** | +2.5/scenario | Low |
| 3 | **Add `status` field to callback** | +5/scenario | Low |
| 4 | **Add `emailAddresses` to callback intel** | +10 on phishing | Low |
| 5 | **Accumulate intel across turns** — per-session store | +10-30 variable | Medium |

**Expected recovery: +27.5 to +57.5 pts**

### Priority 1: HIGH IMPACT (15+ pts recovery)

| # | Fix | Points Recovered | Effort |
|---|-----|-------------------|--------|
| 6 | **Re-enable regex extraction as backup** to AI extraction | +10-20 variable | Medium |
| 7 | **Skip classification after Turn 1** — cache scam result per session | -6-16s latency | Medium |
| 8 | **Set min-instances=1** on Cloud Run | -7-8s cold start | Low |

### Priority 2: OPTIMIZATION

| # | Fix | Impact | Effort |
|---|-----|--------|--------|
| 9 | Increase Cloud Run timeout to 300s | Prevents 504 | Low |
| 10 | Add conversation summary for history > 8 turns | Better agent quality | Medium |
| 11 | Switch engagement model to flash (already partially done) | -3-5s latency | Low |
| 12 | Reduce system prompt token count | -2-3s latency | Medium |

---

## 6. Implementation Roadmap

### Phase 1: Callback Fix (1-2 hours) — Recover ~25 pts

**Files to modify:**
- `src/api/callback.py` — Add `status`, `engagementMetrics`, `emailAddresses` to payload
- `src/api/routes.py` — Track session timing, pass duration to callback

```python
# callback.py - Updated models
class CallbackIntelligence(BaseModel):
    bankAccounts: list[str] = []
    upiIds: list[str] = []
    phishingLinks: list[str] = []
    phoneNumbers: list[str] = []
    emailAddresses: list[str] = []  # ADD
    suspiciousKeywords: list[str] = []

class CallbackPayload(BaseModel):
    sessionId: str
    status: str = "success"  # ADD
    scamDetected: bool
    totalMessagesExchanged: int
    extractedIntelligence: CallbackIntelligence
    engagementMetrics: dict = {}  # ADD
    agentNotes: str
```

```python
# routes.py - Session timing tracker (in-memory)
import time

SESSION_START_TIMES: dict[str, float] = {}

# In analyze_message():
if session_id not in SESSION_START_TIMES:
    SESSION_START_TIMES[session_id] = time.time()

duration = int(time.time() - SESSION_START_TIMES[session_id])

# Pass to callback:
await send_guvi_callback(
    session_id=session_id,
    scam_detected=True,
    total_messages=total_messages_exchanged,
    intelligence=callback_intelligence,
    agent_notes=final_notes,
    engagement_duration=duration,  # NEW
)
```

### Phase 2: Intelligence Accumulation (2-3 hours) — Recover ~15 pts

**Files to modify:**
- `src/api/routes.py` — Add per-session intelligence store
- `src/intelligence/extractor.py` — Re-enable regex as validation/backup

```python
# routes.py - Intelligence accumulator
from typing import Dict, Set

SESSION_INTEL: Dict[str, dict] = {}

def accumulate_intel(session_id: str, new_intel: ExtractedIntelligence) -> dict:
    """Merge new intel with existing session intel."""
    if session_id not in SESSION_INTEL:
        SESSION_INTEL[session_id] = {
            "bankAccounts": set(),
            "upiIds": set(),
            "phoneNumbers": set(),
            "phishingLinks": set(),
            "emailAddresses": set(),
        }
    
    store = SESSION_INTEL[session_id]
    store["bankAccounts"].update(new_intel.bankAccounts)
    store["upiIds"].update(new_intel.upiIds)
    store["phoneNumbers"].update(new_intel.phoneNumbers)
    store["phishingLinks"].update(new_intel.phishingLinks)
    store["emailAddresses"].update(new_intel.emails)
    
    return {k: list(v) for k, v in store.items()}
```

### Phase 3: Latency Optimization (2-3 hours) — Prevent timeouts

**Files to modify:**
- `src/api/routes.py` — Cache classification per session, skip for Turn 2+
- `config/settings.py` — Adjust timeout settings
- `cloudbuild.yaml` — Set `--min-instances=1`, `--timeout=300`

```python
# routes.py - Classification cache
SESSION_CLASSIFICATIONS: dict[str, DetectionResult] = {}

# In analyze_message():
if session_id in SESSION_CLASSIFICATIONS:
    detection_result = SESSION_CLASSIFICATIONS[session_id]
    log.info("Using cached classification", session_id=session_id)
else:
    detection_result = await detector.analyze(...)
    SESSION_CLASSIFICATIONS[session_id] = detection_result
```

### Phase 4: Regex Backup Extraction (1-2 hours) — Recover ~10 pts

**Files to modify:**
- `src/intelligence/extractor.py` — Re-enable regex to scan scammer messages

```python
# extractor.py - Re-enable regex scan on scammer message
def extract_from_text(self, text: str) -> dict:
    """Regex extraction from scammer's latest message."""
    intel = {
        "phoneNumbers": re.findall(r'\+?91[-\s]?\d{10}|\b\d{10}\b', text),
        "bankAccounts": re.findall(r'\b\d{9,18}\b', text),  # Refined
        "upiIds": re.findall(r'[\w.-]+@[\w]+', text),
        "phishingLinks": re.findall(r'https?://[^\s]+', text),
        "emailAddresses": re.findall(r'[\w.-]+@[\w.-]+\.\w+', text),
    }
    return intel
```

### Expected Final Score After All Fixes

| Category | Before | After | Improvement |
|----------|--------|-------|-------------|
| Scam Detection | 20/20 | 20/20 | — |
| Intelligence Extraction | ~10/40 | ~30-40/40 | +20-30 |
| Engagement Quality | ~5/20 | 20/20 | +15 |
| Response Structure | ~12.5/20 | 20/20 | +7.5 |
| **Per-Scenario Total** | **~47.5** | **~90-100** | **+42.5-52.5** |

With weighted average across scenarios:
- **Before:** ~35/100
- **After:** ~85-95/100

---

## Summary

The 35/100 score was NOT caused by poor scam detection or bad agent behavior. The system correctly detected all scams and generated convincing persona responses. The score was destroyed by **structural issues in the GUVI callback payload**:

1. **`engagementDurationSeconds` always 0** → -10 pts/scenario
2. **`status` field missing** → -5 pts/scenario  
3. **`engagementMetrics` object missing** → -2.5 pts/scenario
4. **`emailAddresses` not sent** → -10 pts on phishing
5. **Intelligence not accumulated across turns** → variable loss
6. **AI-only extraction unreliable** → variable loss

The first 4 fixes are trivial (~1 hour of code changes) and would recover approximately **25-30 points** immediately. Adding intelligence accumulation and regex backup would push the score to 85+.
