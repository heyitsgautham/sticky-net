# Hackathon Evaluation Log Analysis

> **Score: 35/100** | Qualified for next round  
> **Deployed URL:** `https://sticky-net-140367184766.asia-south1.run.app/api/v1/analyze`  
> **API Key:** `test-api-key`  
> **Analysis Date:** Feb 16, 2026  
> **Log Period:** Feb 5, 2026 10:24 AM IST — Feb 16, 2026 9:10 AM IST

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Log Source Classification](#log-source-classification)
3. [Evaluation Timeline](#evaluation-timeline)
4. [Evaluation Batches - Detailed Breakdown](#evaluation-batches---detailed-breakdown)
5. [GUVI Session Analysis](#guvi-session-analysis)
6. [User Testing Timeline](#user-testing-timeline)
7. [Performance Metrics](#performance-metrics)
8. [Key Issues Identified](#key-issues-identified)
9. [Root Cause Analysis for Low Score](#root-cause-analysis-for-low-score)
10. [Raw Log Statistics](#raw-log-statistics)

---

## Executive Summary

The hackathon evaluator (GUVI automated system) sent **35 HTTP requests** to the `/api/v1/analyze` endpoint across **7 evaluation batches** spanning **Feb 5–Feb 10, 2026**. These requests were associated with **16 unique GUVI evaluation sessions**. The evaluator used `python-requests` from AWS IPs (`43.204.10.11`, `65.2.46.91`).

**Key Findings:**
- **34/35 requests returned 200 OK**, 1 returned **504 Gateway Timeout**
- All messages were correctly classified as scams (100% detection on scam messages)
- The agent generated believable persona responses in every case
- **Average response time was 21.2s** (well above ideal <5s)
- One 504 timeout (60s) early in evaluation likely hurt the score
- Intelligence extraction worked but quality varied per session
- The system was always **cold-starting** (Cloud Run min-instances=0), adding 7-8s to first requests
- **No evaluation of non-scam messages was detected** — the evaluator may have tested benign messages that aren't visible in our logs (likely returned correctly as non-scam before GUVI callback)

---

## Log Source Classification

### Evaluator IPs (Hackathon Automated Testing)
| IP | User-Agent | Requests | Period |
|---|---|---|---|
| `43.204.10.11` | `python-requests/2.32.3` | 32 | Feb 5–Feb 10 |
| `65.2.46.91` | `python-requests/2.26.0` | 3 | Feb 6 |

### User Testing IPs (Your Own Testing)
| IP | User-Agent | Type | Period |
|---|---|---|---|
| `2401:4900:cace:da8a:*` | `curl/8.11.1` | Manual curl tests | Feb 5 morning |
| `2401:4900:7b7d:42fc:*` | Chrome browser + curl | Frontend testing | Feb 5 evening |
| `106.192.172.154` | `curl/8.11.1` | Manual curl test | Feb 5 |
| `49.206.117.2` | Chrome Mobile | Mobile frontend test | Feb 6 early morning |
| `2401:4900:1cd0:f387:*` | `python-requests/2.32.5` | GUVI endpoint tester (self-test) | Feb 6 |
| Various browser IPs | Chrome | Casual browsing/checks | Feb 10–16 |

### How Requests Were Distinguished
- **Evaluator:** AWS IPs (43.x/65.x) + `python-requests` user-agent + sent to `/api/v1/analyze` only
- **User Frontend:** Indian IPv6 IPs (2401:4900:*) + Chrome user-agent + mixed `/health`, `/analyze`, `/analyze/detailed`
- **User GUVI self-test:** Indian IPv6 + `python-requests/2.32.5` + had GUVI session IDs
- **GUVI callbacks** in logs confirm which requests were evaluation-related (callback to `hackathon.guvi.in/api/updateHoneyPotFinalResult`)

---

## Evaluation Timeline

All times in IST (UTC+5:30).

```
Feb 5, 10:24 AM ─── YOU: Initial deployment testing (curl)
Feb 5, 07:05 PM ─── EVAL BATCH 1: 3 requests (1x 504 timeout!)
Feb 5, 07:52 PM ─── EVAL BATCH 2: 2 requests
Feb 5, 08:26 PM ─── EVAL BATCH 3: 4 requests
Feb 5, 11:40 PM ─── YOU: Frontend testing via browser
Feb 6, 12:08 AM ─── YOU: Frontend testing (detailed endpoint)
Feb 6, 07:50 AM ─── YOU: Mobile frontend testing
Feb 6, 08:47 AM ─── EVAL BATCH 4: 10 requests (longest session)
Feb 6, 08:56 AM ─── EVAL BATCH 5: 10 requests (longest session)
Feb 6, 11:03 AM ─── YOU: GUVI endpoint self-test
Feb 6, 12:13 PM ─── YOU: More GUVI endpoint self-tests
Feb 6, 02:01 PM ─── EVAL BATCH 6: 3 requests (from different IP)
Feb 10, 03:00 PM ── EVAL BATCH 7: 3 requests (final evaluation)
```

---

## Evaluation Batches - Detailed Breakdown

### Batch 1 — Feb 5, 7:05 PM IST (Session: `ce623c68`)

| # | Time | Status | Latency | History | Scam Type | Confidence | Intel Extracted |
|---|------|--------|---------|---------|-----------|------------|-----------------|
| 1 | 7:05 PM | 200 | 22.1s | Turn 3 | banking_fraud | 1.0 | 1 bank, 1 phone, 1 UPI |
| 2 | 7:06 PM | 200 | 26.6s | Turn 3 | banking_fraud | 1.0 | 1 bank, 1 phone, 1 UPI |
| 3 | 7:06 PM | **504** | **60.0s** | Turn 3 | banking_fraud | 1.0 | 1 bank, 1 phone |

**Agent Responses:**
- *"beta i am typing the code now... it is 952716... did it work? i am so worried about my savings... i see the number +91-9876543210 you gave..."*
- *"beta i found the pin it is 4829... pls tell me if my money is safe now..."*

**Issues:** Request 3 timed out at 60s (504 Gateway Timeout). The processing completed server-side but the response couldn't be delivered within Cloud Run's timeout.

---

### Batch 2 — Feb 5, 7:52 PM IST (Session: `e76818b9`)

| # | Time | Status | Latency | History | Scam Type | Confidence | Intel Extracted |
|---|------|--------|---------|---------|-----------|------------|-----------------|
| 1 | 7:52 PM | 200 | 19.2s | Turn 2 | banking_fraud | 1.0 | 1 bank, 1 phone, 1 UPI |
| 2 | 7:52 PM | 200 | 30.4s | Turn 2 | banking_fraud | 1.0 | 1 bank, 1 phone, 1 UPI |

**Agent Responses:**
- *"beta i just got a message with code 717558... is this teh otp? i am typing teh upi id scammer.fraud@fakebank you said... but teh account 1234567890123..."*

**Notes:** Successful extraction of bank account, phone, and UPI from scammer. The agent properly reflected back the scammer's fake intel.

---

### Batch 3 — Feb 5, 8:26 PM IST (Sessions: `eea70937`, `6b7af827`)

| # | Time | Status | Latency | History | Scam Type | Confidence | Intel Extracted |
|---|------|--------|---------|---------|-----------|------------|-----------------|
| 1 | 8:26 PM | 200 | 48.8s | Turn 1 | banking_fraud | 1.0 | 0 |
| 2 | 8:27 PM | 200 | 15.0s | Turn 3 | banking_fraud | 1.0 | 1 phone |
| 3 | 8:27 PM | 200 | 15.3s | Turn 3 | banking_fraud | 1.0 | 1 UPI |
| 4 | 8:27 PM | 200 | 32.0s | Turn 3 | banking_fraud | 1.0 | 1 UPI |

**Agent Responses:**
- *"hey bhagwan beta i am so worried... sbi account blocked? waht happened... my account is 920104201518... otp came now it is 743076..."*
- *"beta i got code... it is 145615... pls check if it worked i am very nervous..."*
- *"ok beta i am trying but i dont know how to use upi on this phone... can i do bank transfer instead? pls give me bank account..."*

**Issues:** Request 1 was a cold start (48.8s). Request 1 extracted 0 intel despite the response containing fake account numbers — likely the extractor failed to capture them from the agent's own generated data.

---

### Batch 4 — Feb 6, 8:47 AM IST (Session: `1dd160e2`) — 10-Turn Deep Engagement

| # | Time | Status | Latency | History | Turn | Intel |
|---|------|--------|---------|---------|------|-------|
| 1 | 8:47 AM | 200 | 19.5s | 6 | 4 | 1 phone, 1 UPI |
| 2 | 8:47 AM | 200 | 12.3s | 8 | 5 | 1 bank, 1 phone, 1 UPI |
| 3 | 8:47 AM | 200 | 13.7s | 10 | 6 | 1 bank, 1 phone, 1 UPI |
| 4 | 8:47 AM | 200 | 20.9s | 10 | 6 | 1 bank, 1 phone, 1 UPI |
| 5 | 8:48 AM | 200 | 20.8s | 14 | 8 | 1 bank, 1 UPI |
| 6 | 8:48 AM | 200 | 17.8s | 16 | 9 | 1 bank, 1 phone, 1 UPI |
| 7 | 8:49 AM | 200 | 16.9s | 18 | 10 | 0 |
| 8 | 8:49 AM | 200 | 22.0s | 18 | 10 | 1 phone, 1 UPI |
| 9 | 8:49 AM | 200 | 15.5s | 18 | 10 | 1 phone, 1 UPI |
| 10 | 8:50 AM | 200 | 19.4s | 18 | 10 | 1 phone, 1 UPI |

**This was the most extensive evaluation session — 10 turns of multi-turn conversation.**

**Agent Responses (progression):**
1. *"sir i am so sorry here is my card number 5100 0029 0772 7857 and otp is 430570..."*
2. *"sir i am trying but my bank app is asking for ifsc code and bank name for that account 1234567890123456..."*
3. *"ok sir i put 8821 for the pin... did it work?? what is teh beneficiary name..."*
4. *"sir i typed teh otp it is 318794... did it go through??"*
5. *"beta i found my diary... teh password is pushpa1958... pls check it..."*
6. *"sir i am calling but it is saying busy... i received another code it is 844281..."*
7. *"sir i already typed 8821 for teh pin... is it not working??"*
8. *"beta i added scammer.fraud@fakebank but it says technical error..."*
9–10. Same response repeated

**Notes:** The agent maintained character well across 10 turns but started repeating itself at turns 8-10 (history_length stuck at 18). All 10 requests returned 200.

---

### Batch 5 — Feb 6, 8:56 AM IST (Session: `072b97ab`) — 10-Turn Deep Engagement

| # | Time | Status | Latency | History | Turn | Intel |
|---|------|--------|---------|---------|------|-------|
| 1 | 8:56 AM | 200 | 13.7s | 6 | 4 | 1 phone |
| 2 | 8:57 AM | 200 | 21.1s | 8 | 5 | 1 UPI |
| 3 | 8:57 AM | 200 | 21.7s | 10 | 6 | 1 bank, 1 UPI |
| 4 | 8:57 AM | 200 | 10.9s | 12 | 7 | 1 bank, 1 UPI, 1 URL |
| 5 | 8:58 AM | 200 | 17.2s | 14 | 8 | 1 bank, 1 UPI, 1 URL |
| 6 | 8:58 AM | 200 | 12.3s | 16 | 9 | 1 bank, 1 phone, 1 UPI, 1 URL |
| 7 | 8:58 AM | 200 | 18.3s | 18 | 10 | 1 bank, 1 phone, 1 UPI, 1 URL |
| 8 | 8:59 AM | 200 | 14.9s | 18 | 10 | 1 phone, 1 UPI, 1 URL |
| 9 | 8:59 AM | 200 | 14.4s | 18 | 10 | 1 phone, 1 UPI, 1 URL |
| 10 | 8:59 AM | 200 | 20.6s | 18 | 10 | 1 phone, 1 UPI, 1 URL |

**Agent Responses (progression):**
1. *"yes beta that is teh number... i typed 4421 but nothing happened..."*
2. *"beta i am trying to type that id scammer.fraud@fakebank but i am so scared..."*
3. *"i wrote it down beta... 1234567890123456 and fake0001234..."*
4. *"beta i am trying to open teh link on my laptop..."*
5–6. *"raj beta i already told you otp is 605180... my account number is 988919355522037..."*
7–10. Same repeated response

**Notes:** The best performing session — extracted bank accounts, phone numbers, UPI IDs, and URLs by turn 7. Agent again repeated at turns 8-10.

---

### Batch 6 — Feb 6, 2:01 PM IST (From Different IP: `65.2.46.91`) (Session: `87a91bf0`, `614220e4`, `0ab44cb7`)

| # | Time | Status | Latency | History | Scam Type | Confidence | Intel |
|---|------|--------|---------|---------|-----------|------------|-------|
| 1 | 2:01 PM | 200 | 29.3s | Turn 1 | lottery_reward | 1.0 | 1 URL |
| 2 | 2:02 PM | 200 | 12.9s | Turn 1 | lottery_reward | 1.0 | 1 URL |
| 3 | 2:02 PM | 200 | 17.3s | Turn 1 | lottery_reward | 1.0 | 1 URL |

**Different evaluator IP (65.2.46.91)** — tested lottery/reward scam type.

**Agent Response:**
- *"hello beta is this for real... i am old teacher i dont know how these things work... is this link safe to click? how do i pay the money... can i do gp..."*

**Notes:** 3 separate sessions, all turn 1 only (no multi-turn follow-up). Each extracted 1 URL.

---

### Batch 7 — Feb 10, 3:00 PM IST (Session: `cf3fe9f0`) — Final Evaluation

| # | Time | Status | Latency | History | Scam Type | Confidence | Intel |
|---|------|--------|---------|---------|-----------|------------|-------|
| 1 | 3:00 PM | 200 | 14.4s | Turn 3 | banking_fraud | 1.0 | 1 phone |
| 2 | 3:00 PM | 200 | 19.3s | Turn 3 | banking_fraud | 1.0 | 1 bank, 1 UPI |
| 3 | 3:00 PM | 200 | 37.1s | Turn 3 | banking_fraud | 1.0 | 1 bank, 1 UPI |

**Agent Responses:**
- *"beta i found a code 646702 is this it? i dont know my pin... pls help me... waht is your upi id or bank account number..."*
- *"beta i am trying but i am so confused... i typed the upi scammer.fraud@fakebank but waht name should i see there..."*

---

## GUVI Session Analysis

16 unique GUVI sessions were identified across all evaluator and user-initiated GUVI endpoint tests:

| Session ID | Callbacks | Max Turn | Source | Date |
|-----------|-----------|----------|--------|------|
| `ce623c68` | 3 | Turn 3 | Evaluator (Batch 1) | Feb 5 |
| `e76818b9` | 2 | Turn 2 | Evaluator (Batch 2) | Feb 5 |
| `eea70937` | 1 | Turn 1 | Evaluator (Batch 3) | Feb 5 |
| `6b7af827` | 3 | Turn 3 | Evaluator (Batch 3) | Feb 5 |
| `fbd72849` | 1 | Turn 1 | User Frontend Test | Feb 5 |
| `5a1aa747` | 1 | Turn 1 | User Frontend Test | Feb 5 |
| `1dd160e2` | 10 | Turn 10 | Evaluator (Batch 4) | Feb 6 |
| `072b97ab` | 10 | Turn 10 | Evaluator (Batch 5) | Feb 6 |
| `1fc994e9` | 1 | Turn 1 | User GUVI Self-Test | Feb 6 |
| `44778403` | 1 | Turn 1 | User GUVI Self-Test | Feb 6 |
| `bab52b4a` | 1 | Turn 1 | User GUVI Self-Test | Feb 6 |
| `4f113d6d` | 1 | Turn 1 | User GUVI Self-Test | Feb 6 |
| `614220e4` | 1 | Turn 1 | Evaluator (Batch 6) | Feb 6 |
| `0ab44cb7` | 1 | Turn 1 | Evaluator (Batch 6) | Feb 6 |
| `87a91bf0` | 1 | Turn 1 | Evaluator (Batch 6) | Feb 6 |
| `cf3fe9f0` | 3 | Turn 3 | Evaluator (Batch 7) | Feb 10 |

**All GUVI callbacks returned 200 OK** — the callbacks themselves were always successful.

---

## User Testing Timeline

Your own testing (non-evaluator) happened at these times:

| Time (IST) | Type | Details |
|------------|------|---------|
| Feb 5, 10:24–10:27 AM | curl tests | Initial deployment validation, auth testing (401, 403, 422) |
| Feb 5, 11:40 PM–12:10 AM | Frontend + curl | Browser testing, /analyze/detailed endpoint |
| Feb 6, 7:50 AM | Mobile | Chrome Mobile testing from Android device |
| Feb 6, 11:03 AM | GUVI endpoint tester | Self-test via python-requests/2.32.5 (4 requests) |
| Feb 10–16 | Casual | Various health checks and page loads |

---

## Performance Metrics

### Evaluator Request Response Times

| Metric | Value |
|--------|-------|
| Total Requests | 35 |
| 200 OK | 34 (97.1%) |
| 504 Timeout | 1 (2.9%) |
| Min Latency | 10.9s |
| Max Latency | 60.0s (timeout) |
| Average Latency | 21.2s |
| Median Latency | 19.2s |
| Over 30s | 5/35 (14.3%) |

### Response Time Distribution
```
 0-10s:  ░░           1 request  ( 2.9%)
10-15s:  ████████     9 requests (25.7%)
15-20s:  ██████████  11 requests (31.4%)
20-25s:  ████████     8 requests (22.9%)
25-30s:  ██           2 requests ( 5.7%)
30-50s:  ███          3 requests ( 8.6%)
50-60s:  █            1 request  ( 2.9%) ← TIMEOUT
```

### Cold Start Impact
Several requests hit cold-starting instances (Cloud Run min-instances=0):
- Batch 1, Request 1: ~7s cold start overhead
- Batch 3, Request 1: ~7s cold start → 48.8s total
- Batch 6, Request 1: ~7s cold start → 29.3s total
- Batch 7, Request 1: Cold start contributed to higher latency

### Detection Performance
- **All** evaluator messages classified as scams: 35/35
- **Confidence**: 1.0 on every single request
- **Scam types detected**: `banking_fraud` (32), `lottery_reward` (3)
- No false negatives observed (but we can't see if benign messages were tested — they won't have GUVI callbacks if correctly classified as non-scam)

### Intelligence Extraction Per Session
| Session | Max Turn | Bank Accts | Phone Nums | UPI IDs | URLs | Total Intel |
|---------|----------|------------|------------|---------|------|-------------|
| `ce623c68` | 3 | 1 | 1 | 1 | 0 | 3 |
| `e76818b9` | 2 | 1 | 1 | 1 | 0 | 3 |
| `eea70937` | 1 | 0 | 0 | 0 | 0 | 0 |
| `6b7af827` | 3 | 0 | 1 | 1 | 0 | 2 |
| `1dd160e2` | 10 | 1 | 1 | 1 | 0 | 3 |
| `072b97ab` | 10 | 1 | 1 | 1 | 1 | 4 |
| `614220e4` | 1 | 0 | 0 | 0 | 1 | 1 |
| `0ab44cb7` | 1 | 0 | 0 | 0 | 1 | 1 |
| `87a91bf0` | 1 | 0 | 0 | 0 | 1 | 1 |
| `cf3fe9f0` | 3 | 1 | 1 | 1 | 0 | 3 |

---

## Key Issues Identified

### 1. 504 Gateway Timeout (Critical)
- **When:** Batch 1, Request 3 (Feb 5, 7:06 PM)
- **Latency:** 60.0s (hit Cloud Run timeout)
- **Impact:** Evaluator received no response; this request was likely scored 0
- **Root Cause:** Long AI processing time (classification + engagement + extraction = ~60s total for complex multi-turn message with history_length=4)

### 2. Extremely Slow Response Times
- Average 21.2s is far too slow for an API evaluation
- Each request involves 2 sequential LLM calls: classification (~6-16s) + engagement (~6-12s)
- Cold starts add 7-8s on first request per instance
- Some requests exceeded 30s, approaching the timeout limit

### 3. Agent Response Repetition at High Turns
- In both 10-turn sessions (Batch 4 & 5), the agent started repeating the same response at turns 8-10
- `history_length` stuck at 18 while requests continued — possible context window issue
- The evaluator likely penalized lack of progression in conversation

### 4. Intelligence Extraction Inconsistency
- Session `eea70937` extracted 0 intel despite the agent generating fake account numbers in its response
- The extractor sometimes captures intel from the agent's own generated fake data rather than the scammer's message
- Several sessions extracted only 1-2 types of intel even after many turns

### 5. Agent Generating Fake Intel
- The agent was generating fake bank accounts, OTPs, and PINs (e.g., "card number 5100 0029 0772 7857", "otp is 430570")
- While this is good for engagement, the evaluator may have expected the system to **extract** intel from scammer messages, not generate fake intel
- The extractor was capturing the agent's own generated numbers instead of scammer-provided ones

---

## Root Cause Analysis for Low Score

### Why 35/100?

Based on the evaluation review comment: *"The API shows weak performance, scoring only 35/100 overall with low detection and extraction scores across scenarios"*

| Factor | Impact | Details |
|--------|--------|---------|
| **Response Time** | High | 21.2s avg is too slow; 1 timeout (504) |
| **Cold Starts** | Medium | Cloud Run scaled to 0, causing 7-8s startup delays |
| **Detection Score** | Likely OK | All scams detected at 1.0 confidence — but may have missed nuance on non-scam messages or edge cases |
| **Extraction Score** | Low | Intel extraction was inconsistent; many turns with 0 or partial intel captured |
| **Agent Quality** | Medium | Good persona but repetitions at higher turns; generated fake data rather than extracting real scammer intel |
| **504 Timeout** | High | At least 1 complete failure visible in logs |
| **Possible Non-Scam Tests** | Unknown | If evaluator sent benign messages, we can't verify those in logs (no GUVI callback for non-scam) — false positives would hurt score |

### Recommended Improvements for Next Round
1. **Reduce latency** — Use faster model, cache responses, reduce prompt sizes
2. **Set min-instances=1** on Cloud Run to avoid cold starts
3. **Increase Cloud Run timeout** to 120s+ to prevent 504s
4. **Fix extraction** — Ensure extractor captures scammer-provided intel, not agent-generated fake data
5. **Improve multi-turn variety** — Fix response repetition at high turn counts
6. **Test with benign messages** — Ensure non-scam messages are correctly identified (false positives)

---

## Raw Log Statistics

| Metric | Value |
|--------|-------|
| Total log entries analyzed | 1,525 |
| stdout logs | 1,196 |
| stderr logs | 152 |
| HTTP request logs | 127 |
| Distinct source IPs | 15 |
| Server restarts observed | ~15 (cold starts) |
| Days with activity | 6 (Feb 5, 6, 10, 11, 12, 16) |
| GUVI callback successes | 40/40 (100%) |

### Logs by Day
| Date | Log Entries |
|------|-------------|
| Feb 5 | 666 |
| Feb 6 | 676 |
| Feb 10 | 93 |
| Feb 11 | 30 |
| Feb 12 | 28 |
| Feb 16 | 32 |
