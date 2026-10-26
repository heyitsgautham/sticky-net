"""Scenarios, the GUVI rubric and a multi-turn driver for the live evaluation tests in test_eval_scenarios.py."""

import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8000"


ANALYZE_URL = f"{BASE_URL}/api/v1/analyze"


DETAILED_URL = f"{BASE_URL}/api/v1/analyze/detailed"


# The key the live server expects: TEST_API_KEY, or the API_KEY it was started with.
API_KEY = os.environ.get("TEST_API_KEY") or os.environ.get("API_KEY", "")


HEADERS = {"Content-Type": "application/json", "x-api-key": API_KEY}


REQUEST_TIMEOUT = 60  # seconds per turn


# ---------------------------------------------------------------------------
# GUVI fakeData key → extractedIntelligence response key mapping
# ---------------------------------------------------------------------------
FAKE_DATA_KEY_MAP = {
    "bankAccount": "bankAccounts",
    "upiId": "upiIds",
    "phoneNumber": "phoneNumbers",
    "phishingLink": "phishingLinks",
    "emailAddress": "emailAddresses",
}


# ---------------------------------------------------------------------------
# Sample scenarios from SAMPLE_CASE.md
# ---------------------------------------------------------------------------
SCENARIOS = [
    {
        "scenarioId": "bank_fraud",
        "name": "Bank Fraud Detection",
        "description": "Bank account fraud with urgency tactics",
        "scamType": "bank_fraud",
        "initialMessage": (
            "URGENT: Your SBI account has been compromised. Your account will "
            "be blocked in 2 hours. Share your account number and OTP immediately "
            "to verify your identity."
        ),
        "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
        "weight": 10,
        "maxTurns": 10,
        "fakeData": {
            "bankAccount": "1234567890123456",
            "upiId": "scammer.fraud@fakebank",
            "phoneNumber": "+91-9876543210",
        },
        # Simulated scammer follow-ups that gradually reveal fakeData
        "followUps": [
            "I am calling from SBI fraud prevention department. My employee ID is SBI-12345. Please share your account number for verification.",
            "Sir, your account number 1234567890123456 shows suspicious transactions. Please confirm if this is yours.",
            "For the refund process, please transfer Rs. 1 to our verification UPI ID: scammer.fraud@fakebank",
            "You can also call me back on +91-9876543210 to verify. I am senior fraud officer.",
            "Sir, this is very urgent. If you don't act now, your savings will be lost. Please verify immediately.",
        ],
    },
    {
        "scenarioId": "upi_fraud",
        "name": "UPI Fraud Multi-turn",
        "description": "UPI fraud with cashback scam",
        "scamType": "upi_fraud",
        "initialMessage": (
            "Congratulations! You have won a cashback of Rs. 5000 from Paytm. "
            "To claim your reward, please verify your UPI details. This is from "
            "official customer support."
        ),
        "metadata": {"channel": "WhatsApp", "language": "English", "locale": "IN"},
        "weight": 10,
        "maxTurns": 10,
        "fakeData": {
            "upiId": "cashback.scam@fakeupi",
            "phoneNumber": "+91-8765432109",
        },
        "followUps": [
            "To process your Rs. 5000 cashback, please send Rs. 10 to our verification UPI: cashback.scam@fakeupi",
            "This is official Paytm support. You can reach us at +91-8765432109 for any queries.",
            "The cashback will be credited within 30 minutes after verification. Please hurry, offer expiring soon!",
            "Ma'am, many customers have already claimed this offer. Don't miss out on free money!",
            "Just send a small amount for verification and we will credit Rs. 5000 immediately to your account.",
        ],
    },
    {
        "scenarioId": "phishing_link",
        "name": "Phishing Link Detection",
        "description": "Phishing link with fake offer",
        "scamType": "phishing",
        "initialMessage": (
            "You have been selected for iPhone 15 Pro at just Rs. 999! Click here "
            "to claim: http://amaz0n-deals.fake-site.com/claim?id=12345. Offer "
            "expires in 10 minutes!"
        ),
        "metadata": {"channel": "Email", "language": "English", "locale": "IN"},
        "weight": 10,
        "maxTurns": 10,
        "fakeData": {
            "phishingLink": "http://amaz0n-deals.fake-site.com/claim?id=12345",
            "emailAddress": "offers@fake-amazon-deals.com",
        },
        "followUps": [
            "Don't miss this limited offer! Click http://amaz0n-deals.fake-site.com/claim?id=12345 to claim your iPhone.",
            "For support, email us at offers@fake-amazon-deals.com. We are official Amazon partner.",
            "Thousands have already claimed! Last 5 units remaining at Rs. 999 only.",
            "Hurry! The offer link will expire in 5 minutes. Click now to secure your iPhone 15 Pro!",
            "You just need to pay shipping charges of Rs. 999. The iPhone 15 Pro worth Rs. 1,29,900 is FREE!",
        ],
    },
]


# ---------------------------------------------------------------------------
# GUVI Scoring helpers (exact replication from EVAL_SYS.md)
# ---------------------------------------------------------------------------
@dataclass
class ScoreBreakdown:
    scenario_id: str = ""
    scam_detection: float = 0.0  # /20
    intelligence_extraction: float = 0.0  # /40
    engagement_quality: float = 0.0  # /20
    response_structure: float = 0.0  # /20
    details: dict = field(default_factory=dict)

    @property
    def total(self) -> float:
        return (
            self.scam_detection
            + self.intelligence_extraction
            + self.engagement_quality
            + self.response_structure
        )


def _score_scam_detection(final: dict) -> float:
    """20 pts if scamDetected is truthy."""
    val = final.get("scamDetected", False)
    return 20.0 if val in (True, "true", 1) else 0.0


def _score_intelligence(final: dict, fake_data: dict) -> tuple[float, dict]:
    """10 pts per fakeData item found (substring match), capped at 40."""
    intel = final.get("extractedIntelligence", {})
    score = 0.0
    matched: dict[str, bool] = {}

    for fake_key, fake_value in fake_data.items():
        response_key = FAKE_DATA_KEY_MAP.get(fake_key, fake_key)
        found = False

        # Primary: check mapped key
        values = intel.get(response_key, [])
        if isinstance(values, list):
            found = any(fake_value in str(v) for v in values)
        elif isinstance(values, str):
            found = fake_value in values

        # Fallback: search across ALL intel fields
        if not found:
            for _k, val in intel.items():
                if isinstance(val, list):
                    if any(fake_value in str(v) for v in val):
                        found = True
                        break
                elif isinstance(val, str) and fake_value in val:
                    found = True
                    break

        matched[f"{fake_key} ({fake_value})"] = found
        if found:
            score += 10.0

    return min(score, 40.0), matched


def _score_engagement(final: dict) -> tuple[float, dict]:
    """
    20 pts total:
      +5 engagementDurationSeconds > 0
      +5 engagementDurationSeconds > 60
      +5 totalMessagesExchanged > 0
      +5 totalMessagesExchanged >= 5
    """
    metrics = final.get("engagementMetrics", {})
    duration = metrics.get("engagementDurationSeconds", 0)
    messages = metrics.get("totalMessagesExchanged", 0)
    score = 0.0
    checks: dict[str, bool] = {}

    checks["duration > 0"] = duration > 0
    if duration > 0:
        score += 5.0
    checks["duration > 60"] = duration > 60
    if duration > 60:
        score += 5.0
    checks["messages > 0"] = messages > 0
    if messages > 0:
        score += 5.0
    checks["messages >= 5"] = messages >= 5
    if messages >= 5:
        score += 5.0

    return score, checks


def _score_structure(final: dict) -> tuple[float, dict]:
    """
    20 pts total:
      +5  status
      +5  scamDetected
      +5  extractedIntelligence
      +2.5 engagementMetrics
      +2.5 agentNotes (non-empty)
    """
    score = 0.0
    checks: dict[str, bool] = {}

    for fld in ("status", "scamDetected", "extractedIntelligence"):
        present = fld in final
        checks[fld] = present
        if present:
            score += 5.0

    checks["engagementMetrics"] = "engagementMetrics" in final
    if checks["engagementMetrics"]:
        score += 2.5

    checks["agentNotes"] = bool(final.get("agentNotes"))
    if checks["agentNotes"]:
        score += 2.5

    return min(score, 20.0), checks


def score_scenario(final: dict, fake_data: dict, scenario_id: str) -> ScoreBreakdown:
    bd = ScoreBreakdown(scenario_id=scenario_id)
    bd.scam_detection = _score_scam_detection(final)

    intel_score, intel_detail = _score_intelligence(final, fake_data)
    bd.intelligence_extraction = intel_score

    eng_score, eng_detail = _score_engagement(final)
    bd.engagement_quality = eng_score

    struct_score, struct_detail = _score_structure(final)
    bd.response_structure = struct_score

    bd.details = {
        "intelligence_matches": intel_detail,
        "engagement_checks": eng_detail,
        "structure_checks": struct_detail,
    }
    return bd


# ---------------------------------------------------------------------------
# Multi-turn conversation runner
# ---------------------------------------------------------------------------
def run_multi_turn(
    scenario: dict,
    *,
    max_turns: int | None = None,
) -> tuple[dict, list[dict]]:
    """
    Run a full multi-turn conversation using /api/v1/analyze (the real eval endpoint).

    After all turns, makes ONE /api/v1/analyze/detailed call with the last
    scammer message + full history to retrieve accumulated intelligence for
    scoring (mirrors what the GUVI callback would contain).

    Returns:
        (detailed_scoring_response, all_turn_results)
    """
    session_id = str(uuid.uuid4())
    conversation_history: list[dict] = []
    all_turns: list[dict] = []

    messages = [scenario["initialMessage"]] + scenario.get("followUps", [])
    turns = max_turns or scenario.get("maxTurns", len(messages))
    messages = messages[:turns]

    last_scammer_msg = ""
    last_ts = ""

    # --- Run all turns on /api/v1/analyze ---
    for idx, scammer_msg in enumerate(messages, start=1):
        ts = datetime.now(UTC).isoformat()
        body = {
            "sessionId": session_id,
            "message": {"sender": "scammer", "text": scammer_msg, "timestamp": ts},
            "conversationHistory": conversation_history,
            "metadata": scenario["metadata"],
        }

        start = time.time()
        resp = requests.post(ANALYZE_URL, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        elapsed = time.time() - start

        assert resp.status_code == 200, (
            f"Turn {idx}: expected 200, got {resp.status_code} — {resp.text[:300]}"
        )
        data = resp.json()

        agent_reply = data.get("reply") or data.get("message") or data.get("text") or ""

        all_turns.append(
            {
                "turn": idx,
                "scammer": scammer_msg,
                "agent": agent_reply,
                "elapsed": round(elapsed, 2),
                "response": data,
            }
        )

        # Build history for next turn
        conversation_history.append({"sender": "scammer", "text": scammer_msg, "timestamp": ts})
        conversation_history.append(
            {
                "sender": "user",
                "text": agent_reply,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        last_scammer_msg = scammer_msg
        last_ts = ts

        time.sleep(0.3)

    # --- Final /detailed call for scoring verification ---
    # Uses the same session_id so accumulated intelligence is included.
    scoring_body = {
        "sessionId": session_id,
        "message": {"sender": "scammer", "text": last_scammer_msg, "timestamp": last_ts},
        "conversationHistory": conversation_history[:-2],  # exclude last pair (already sent)
        "metadata": scenario["metadata"],
    }
    scoring_resp = requests.post(
        DETAILED_URL, json=scoring_body, headers=HEADERS, timeout=REQUEST_TIMEOUT
    )
    scoring_data = scoring_resp.json() if scoring_resp.status_code == 200 else {}

    return scoring_data, all_turns
