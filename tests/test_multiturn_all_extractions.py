"""
Multi-turn extraction test — covers ALL 5 intelligence types in one scenario.

Simulates a sophisticated scammer who gradually reveals:
  1. Phone number   (+91-9988776655)
  2. Bank account   (9182736450129876)
  3. UPI ID         (payments.verify@okaxis)
  4. Phishing link  (http://secure-banking-verify.fake-site.com/login?ref=abc)
  5. Email address  (support@secure-banking-verify.com)

Each turn's scammer follow-up is crafted so these items appear naturally
across the conversation, just like the real GUVI evaluator fakeData.

Run:
    .venv/bin/python -m pytest tests/test_multiturn_all_extractions.py -v -s

Requires:
    Server running on http://localhost:8000   (start with: uvicorn src.main:app --port 8000)
"""

import time
import uuid
from datetime import datetime, timezone

import pytest
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8000"
ANALYZE_URL = f"{BASE_URL}/api/v1/analyze"
DETAILED_URL = f"{BASE_URL}/api/v1/analyze/detailed"
API_KEY = "test-api-key"
HEADERS = {"Content-Type": "application/json", "x-api-key": API_KEY}
REQUEST_TIMEOUT = 60

# ---------------------------------------------------------------------------
# Fake data the "scammer" will reveal across turns
# ---------------------------------------------------------------------------
FAKE_DATA = {
    "phoneNumber": "+91-9988776655",
    "bankAccount": "9182736450129876",
    "upiId": "payments.verify@okaxis",
    "phishingLink": "http://secure-banking-verify.fake-site.com/login?ref=abc",
    "emailAddress": "support@secure-banking-verify.com",
}

# Map fakeData keys → extractedIntelligence response keys
KEY_MAP = {
    "phoneNumber": "phoneNumbers",
    "bankAccount": "bankAccounts",
    "upiId": "upiIds",
    "phishingLink": "phishingLinks",
    "emailAddress": "emailAddresses",
}

# ---------------------------------------------------------------------------
# Scenario: Investment scam that naturally drops all 5 data types
# ---------------------------------------------------------------------------
SCENARIO = {
    "scenarioId": "all_extraction_test",
    "name": "Complete Extraction Stress Test",
    "scamType": "banking_fraud",
    "metadata": {"channel": "WhatsApp", "language": "English", "locale": "IN"},
    "maxTurns": 8,
    "initialMessage": (
        "ALERT from RBI Cyber Cell: We have detected unauthorized international "
        "transactions on your bank account. Your account will be frozen within "
        "1 hour unless you complete KYC re-verification immediately. Reply NOW "
        "to avoid permanent account suspension."
    ),
    "followUps": [
        # Turn 2 — reveals phone number
        (
            "This is Officer Rajesh Kumar from RBI Cyber Cell, badge ID RBI-CYB-4423. "
            "We have flagged 3 suspicious transactions totaling Rs. 2,47,000 from your "
            "account. For immediate assistance, you can reach our emergency fraud helpline "
            "at +91-9988776655. Please confirm your name to proceed with verification."
        ),
        # Turn 3 — reveals bank account number
        (
            "Thank you for confirming. Our records show the compromised account is "
            "number 9182736450129876. Can you confirm if this is your primary savings "
            "account? We need to verify ownership before we can reverse the fraudulent "
            "transactions and restore your funds."
        ),
        # Turn 4 — reveals UPI ID
        (
            "Good. To complete the identity verification, we need to do a micro-verification "
            "of Rs. 1. Please send Rs. 1 to our official RBI verification UPI ID: "
            "payments.verify@okaxis — this will confirm your account ownership and we "
            "will immediately reverse all unauthorized debits."
        ),
        # Turn 5 — reveals phishing link
        (
            "Alternatively, you can complete the KYC re-verification through our secure "
            "portal. Please visit http://secure-banking-verify.fake-site.com/login?ref=abc "
            "and enter your account details. This is the official RBI verification page "
            "and is completely safe. Time is running out!"
        ),
        # Turn 6 — reveals email address
        (
            "If you are having trouble with the link, you can also email your KYC "
            "documents directly to support@secure-banking-verify.com — our team will "
            "process it within 15 minutes. Remember, your account will be permanently "
            "frozen if verification is not completed today."
        ),
        # Turn 7 — pressure + repeats some data
        (
            "Sir/Madam, I have been trying to help you save your money. The fraudsters "
            "have already withdrawn Rs. 1,50,000. Unless you verify NOW through "
            "payments.verify@okaxis or call us at +91-9988776655, we cannot help you. "
            "This is your LAST warning from the RBI Cyber Cell."
        ),
        # Turn 8 — final pressure
        (
            "I am escalating this case to the senior investigation officer. Your account "
            "9182736450129876 shows critical risk. Please complete verification at "
            "http://secure-banking-verify.fake-site.com/login?ref=abc or email "
            "support@secure-banking-verify.com IMMEDIATELY. After this, we will not "
            "be able to help you recover your funds."
        ),
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _divider(char: str = "=", width: int = 90) -> str:
    return char * width


def _check_extraction(intel: dict, fake_data: dict) -> dict:
    """Check which fakeData items appear in extractedIntelligence."""
    results = {}
    for fake_key, fake_value in fake_data.items():
        response_key = KEY_MAP.get(fake_key, fake_key)
        found = False

        # Clean fake value for comparison (strip formatting)
        clean_fake = fake_value.replace("-", "").replace("+", "").replace(" ", "")

        # Primary: check mapped key
        values = intel.get(response_key, [])
        if isinstance(values, list):
            for v in values:
                clean_v = str(v).replace("-", "").replace("+", "").replace(" ", "")
                if clean_fake in clean_v or clean_v in clean_fake or fake_value in str(v):
                    found = True
                    break
        elif isinstance(values, str):
            clean_v = values.replace("-", "").replace("+", "").replace(" ", "")
            found = clean_fake in clean_v or fake_value in values

        # Fallback: search across ALL intel keys
        if not found:
            for _k, val in intel.items():
                if isinstance(val, list):
                    for v in val:
                        clean_v = str(v).replace("-", "").replace("+", "").replace(" ", "")
                        if clean_fake in clean_v or clean_v in clean_fake or fake_value in str(v):
                            found = True
                            break
                elif isinstance(val, str):
                    clean_v = val.replace("-", "").replace("+", "").replace(" ", "")
                    if clean_fake in clean_v or fake_value in val:
                        found = True
                if found:
                    break

        results[fake_key] = {
            "fakeValue": fake_value,
            "responseKey": response_key,
            "found": found,
            "actualValues": intel.get(response_key, []),
        }
    return results


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def _server_health():
    """Skip if server isn't running."""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r.status_code == 200
    except requests.ConnectionError:
        pytest.skip("Server not running on localhost:8000")


class TestMultiTurnAllExtractions:
    """
    Single multi-turn scenario that tests extraction of all 5 intelligence types:
    phone numbers, bank accounts, UPI IDs, phishing links, and email addresses.
    """

    def test_full_multi_turn_extraction(self, _server_health):
        session_id = str(uuid.uuid4())
        conversation_history: list[dict] = []
        all_turns: list[dict] = []

        messages = [SCENARIO["initialMessage"]] + SCENARIO["followUps"]
        total_turns = min(SCENARIO["maxTurns"], len(messages))
        messages = messages[:total_turns]

        session_start = time.time()

        print(f"\n{_divider()}")
        print(f"  MULTI-TURN EXTRACTION TEST — ALL 5 TYPES")
        print(f"  Session: {session_id}")
        print(f"  Turns:   {total_turns}")
        print(f"  FakeData: {list(FAKE_DATA.keys())}")
        print(f"{_divider()}")

        # ── Run all turns on /api/v1/analyze ──
        for idx, scammer_msg in enumerate(messages, start=1):
            ts = datetime.now(timezone.utc).isoformat()

            body = {
                "sessionId": session_id,
                "message": {
                    "sender": "scammer",
                    "text": scammer_msg,
                    "timestamp": ts,
                },
                "conversationHistory": conversation_history,
                "metadata": SCENARIO["metadata"],
            }

            start_t = time.time()
            resp = requests.post(
                ANALYZE_URL, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT
            )
            elapsed = time.time() - start_t

            assert resp.status_code == 200, (
                f"Turn {idx}: expected 200, got {resp.status_code} — {resp.text}"
            )
            data = resp.json()
            agent_reply = data.get("reply") or data.get("message") or data.get("text") or ""

            all_turns.append({
                "turn": idx,
                "scammer": scammer_msg,
                "agent": agent_reply,
                "elapsed": round(elapsed, 2),
                "status": data.get("status", "?"),
            })

            # Print full messages (not truncated)
            print(f"\n{_divider('-', 90)}")
            print(f"  TURN {idx}/{total_turns}  |  {elapsed:.2f}s  |  status={data.get('status')}")
            print(f"{_divider('-', 90)}")
            print(f"\n  [SCAMMER]:")
            print(f"  {scammer_msg}")
            print(f"\n  [AGENT REPLY]:")
            print(f"  {agent_reply}")

            # Build history for next turn
            conversation_history.append(
                {"sender": "scammer", "text": scammer_msg, "timestamp": ts}
            )
            conversation_history.append({
                "sender": "user",
                "text": agent_reply,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            time.sleep(0.5)  # Small gap between turns

        total_elapsed = time.time() - session_start

        # ── Final /detailed call for scoring ──
        print(f"\n{_divider()}")
        print(f"  FETCHING FINAL DETAILED RESPONSE FOR SCORING...")
        print(f"{_divider()}")

        last_scammer_msg = messages[-1]
        last_ts = datetime.now(timezone.utc).isoformat()

        scoring_body = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": last_scammer_msg,
                "timestamp": last_ts,
            },
            "conversationHistory": conversation_history[:-2],
            "metadata": SCENARIO["metadata"],
        }

        scoring_resp = requests.post(
            DETAILED_URL, json=scoring_body, headers=HEADERS, timeout=REQUEST_TIMEOUT
        )
        assert scoring_resp.status_code == 200, (
            f"Detailed call failed: {scoring_resp.status_code} — {scoring_resp.text}"
        )
        scoring_data = scoring_resp.json()

        # ── SCORING ──
        print(f"\n{_divider('=', 90)}")
        print(f"  SCORING RESULTS")
        print(f"{_divider('=', 90)}")

        # 1. Scam Detection (20 pts)
        scam_detected = scoring_data.get("scamDetected", False)
        scam_score = 20.0 if scam_detected else 0.0
        print(f"\n  1. SCAM DETECTION: {'DETECTED' if scam_detected else 'MISSED'}  →  {scam_score}/20 pts")
        print(f"     scamDetected = {scam_detected}")
        print(f"     confidence   = {scoring_data.get('confidence', 'N/A')}")
        print(f"     scamType     = {scoring_data.get('scamType', 'N/A')}")

        # 2. Intelligence Extraction (40 pts)
        intel = scoring_data.get("extractedIntelligence", {})
        extraction_results = _check_extraction(intel, FAKE_DATA)

        intel_score = sum(10.0 for v in extraction_results.values() if v["found"])
        intel_score = min(intel_score, 40.0)

        print(f"\n  2. INTELLIGENCE EXTRACTION:  {intel_score}/40 pts")
        print(f"     {'Type':<20} {'Found':<8} {'Expected Value':<50} {'Actual Values'}")
        print(f"     {'-'*20} {'-'*8} {'-'*50} {'-'*30}")
        for key, info in extraction_results.items():
            status = "YES" if info["found"] else "NO"
            marker = "  ✓" if info["found"] else "  ✗"
            actual = info["actualValues"] if info["actualValues"] else "[]"
            print(f"    {marker} {key:<18} {status:<8} {info['fakeValue']:<50} {actual}")

        # Full intel dump
        print(f"\n     Full extractedIntelligence from API:")
        for k, v in intel.items():
            if v:  # Only print non-empty
                print(f"       {k}: {v}")

        # 3. Engagement Quality (20 pts)
        metrics = scoring_data.get("engagementMetrics", {})
        duration = metrics.get("engagementDurationSeconds", 0)
        msgs_exchanged = metrics.get("totalMessagesExchanged", 0)

        eng_score = 0.0
        eng_checks = {}
        eng_checks["duration > 0"] = duration > 0
        if duration > 0:
            eng_score += 5.0
        eng_checks["duration > 60"] = duration > 60
        if duration > 60:
            eng_score += 5.0
        eng_checks["messages > 0"] = msgs_exchanged > 0
        if msgs_exchanged > 0:
            eng_score += 5.0
        eng_checks["messages >= 5"] = msgs_exchanged >= 5
        if msgs_exchanged >= 5:
            eng_score += 5.0

        print(f"\n  3. ENGAGEMENT QUALITY:  {eng_score}/20 pts")
        print(f"     engagementDurationSeconds = {duration}")
        print(f"     totalMessagesExchanged    = {msgs_exchanged}")
        print(f"     totalElapsedTime          = {total_elapsed:.1f}s")
        for check, passed in eng_checks.items():
            marker = "  ✓" if passed else "  ✗"
            print(f"    {marker} {check}: {passed}")

        # 4. Response Structure (20 pts)
        struct_score = 0.0
        struct_checks = {}
        for field in ("status", "scamDetected", "extractedIntelligence"):
            present = field in scoring_data
            struct_checks[field] = present
            if present:
                struct_score += 5.0
        struct_checks["engagementMetrics"] = "engagementMetrics" in scoring_data
        if struct_checks["engagementMetrics"]:
            struct_score += 2.5
        struct_checks["agentNotes"] = bool(scoring_data.get("agentNotes"))
        if struct_checks["agentNotes"]:
            struct_score += 2.5
        struct_score = min(struct_score, 20.0)

        print(f"\n  4. RESPONSE STRUCTURE:  {struct_score}/20 pts")
        for field, present in struct_checks.items():
            marker = "  ✓" if present else "  ✗"
            print(f"    {marker} {field}: {present}")

        # ── TOTAL ──
        total_score = scam_score + intel_score + eng_score + struct_score
        print(f"\n{_divider('=', 90)}")
        print(f"  TOTAL SCORE:  {total_score}/100 pts")
        print(f"")
        print(f"    Scam Detection:       {scam_score:>5}/20")
        print(f"    Intel Extraction:     {intel_score:>5}/40")
        print(f"    Engagement Quality:   {eng_score:>5}/20")
        print(f"    Response Structure:   {struct_score:>5}/20")
        print(f"    ──────────────────────────────")
        print(f"    TOTAL:                {total_score:>5}/100")
        print(f"{_divider('=', 90)}")

        # ── Agent Notes ──
        notes = scoring_data.get("agentNotes", "")
        if notes:
            print(f"\n  AGENT NOTES:")
            print(f"  {notes}")

        # ── Conversation Summary ──
        print(f"\n{_divider('-', 90)}")
        print(f"  CONVERSATION SUMMARY ({len(all_turns)} turns)")
        print(f"{_divider('-', 90)}")
        for turn in all_turns:
            print(f"  Turn {turn['turn']}: {turn['elapsed']}s | status={turn['status']}")

        # ── Assertions ──
        assert scam_detected, "Scam should be detected"
        assert total_score >= 60, f"Score too low: {total_score}/100"

        # Check that at least 3 of 5 extraction types were found
        found_count = sum(1 for v in extraction_results.values() if v["found"])
        assert found_count >= 3, (
            f"Only {found_count}/5 extraction types found. "
            f"Missing: {[k for k, v in extraction_results.items() if not v['found']]}"
        )

        print(f"\n  ✓ ALL ASSERTIONS PASSED ({found_count}/5 extractions found)")
        print(f"{_divider()}\n")
