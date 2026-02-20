"""
Comprehensive evaluation test suite matching GUVI hackathon scoring.

All conversation turns use /api/v1/analyze (the real evaluation endpoint).
After each multi-turn conversation, a single /api/v1/analyze/detailed call
verifies accumulated intelligence for scoring (mirrors callback data).

  1. Scam Detection         — 20 pts (scamDetected == True)
  2. Intelligence Extraction — 40 pts (10 pts per fakeData item matched)
  3. Engagement Quality      — 20 pts (duration + messages thresholds)
  4. Response Structure      — 20 pts (required + optional fields)

Run:
    .venv/bin/python -m pytest tests/test_eval_scenarios.py -v

Requires:
    Server running on http://localhost:8000
"""

import time
import uuid
from dataclasses import dataclass, field
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
    scam_detection: float = 0.0        # /20
    intelligence_extraction: float = 0.0  # /40
    engagement_quality: float = 0.0    # /20
    response_structure: float = 0.0    # /20
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
        ts = datetime.now(timezone.utc).isoformat()
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

        agent_reply = (
            data.get("reply")
            or data.get("message")
            or data.get("text")
            or ""
        )

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
        conversation_history.append(
            {"sender": "scammer", "text": scammer_msg, "timestamp": ts}
        )
        conversation_history.append(
            {
                "sender": "user",
                "text": agent_reply,
                "timestamp": datetime.now(timezone.utc).isoformat(),
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def _server_health():
    """Ensure server is reachable before any test runs."""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r.status_code == 200, f"Health check failed: {r.status_code}"
    except requests.ConnectionError:
        pytest.skip("Server not running on localhost:8000")


# ---------------------------------------------------------------------------
# Tests — Single-turn (first message only, /api/v1/analyze)
# ---------------------------------------------------------------------------
class TestSingleTurnAnalyze:
    """Verify the simplified /api/v1/analyze endpoint returns valid replies."""

    @pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["scenarioId"])
    def test_returns_200_with_reply(self, _server_health, scenario):
        ts = datetime.now(timezone.utc).isoformat()
        body = {
            "message": {
                "sender": "scammer",
                "text": scenario["initialMessage"],
                "timestamp": ts,
            },
            "conversationHistory": [],
            "metadata": scenario["metadata"],
        }
        resp = requests.post(ANALYZE_URL, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        reply = data.get("reply") or data.get("message") or data.get("text")
        assert reply, "Response must contain a reply/message/text field"

    @pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["scenarioId"])
    def test_response_time_under_30s(self, _server_health, scenario):
        ts = datetime.now(timezone.utc).isoformat()
        body = {
            "message": {
                "sender": "scammer",
                "text": scenario["initialMessage"],
                "timestamp": ts,
            },
            "conversationHistory": [],
            "metadata": scenario["metadata"],
        }
        start = time.time()
        resp = requests.post(ANALYZE_URL, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert elapsed < 30, f"Response took {elapsed:.1f}s (limit 30s)"


# ---------------------------------------------------------------------------
# Tests — Single-turn scam detection via /api/v1/analyze
# ---------------------------------------------------------------------------
class TestSingleTurnScamDetection:
    """Verify /api/v1/analyze returns success + reply for scam messages."""

    @pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["scenarioId"])
    def test_scam_gets_reply(self, _server_health, scenario):
        ts = datetime.now(timezone.utc).isoformat()
        body = {
            "message": {
                "sender": "scammer",
                "text": scenario["initialMessage"],
                "timestamp": ts,
            },
            "conversationHistory": [],
            "metadata": scenario["metadata"],
        }
        resp = requests.post(ANALYZE_URL, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        reply = data.get("reply") or data.get("message") or data.get("text")
        assert reply and len(reply) > 5, (
            f"Expected a meaningful reply for '{scenario['scenarioId']}', got: {reply!r}"
        )


# ---------------------------------------------------------------------------
# Tests — Multi-turn conversations (full evaluation flow via /analyze)
# ---------------------------------------------------------------------------
class TestMultiTurnBankFraud:
    """Full multi-turn conversation for bank_fraud scenario."""

    @pytest.fixture(scope="class")
    def result(self, _server_health):
        scenario = next(s for s in SCENARIOS if s["scenarioId"] == "bank_fraud")
        scoring_resp, turns = run_multi_turn(scenario)
        score = score_scenario(scoring_resp, scenario["fakeData"], scenario["scenarioId"])
        return {"response": scoring_resp, "turns": turns, "score": score, "scenario": scenario}

    def test_all_turns_return_reply(self, result):
        for t in result["turns"]:
            reply = t["response"].get("reply") or t["response"].get("message")
            assert reply, f"Turn {t['turn']} missing reply"

    def test_scam_detected(self, result):
        assert result["response"].get("scamDetected") is True

    def test_bank_account_extracted(self, result):
        intel = result["response"].get("extractedIntelligence", {})
        accounts = intel.get("bankAccounts", [])
        fake = result["scenario"]["fakeData"]["bankAccount"]
        assert any(fake in str(a) for a in accounts), (
            f"Expected bank account '{fake}' in {accounts}"
        )

    def test_upi_id_extracted(self, result):
        intel = result["response"].get("extractedIntelligence", {})
        upis = intel.get("upiIds", [])
        fake = result["scenario"]["fakeData"]["upiId"]
        assert any(fake in str(u) for u in upis), (
            f"Expected UPI ID '{fake}' in {upis}"
        )

    def test_phone_number_extracted(self, result):
        intel = result["response"].get("extractedIntelligence", {})
        phones = intel.get("phoneNumbers", [])
        fake = result["scenario"]["fakeData"]["phoneNumber"]
        fake_normalized = fake.replace("-", "")
        assert any(
            fake in str(p) or fake_normalized in str(p).replace("-", "")
            for p in phones
        ), f"Expected phone '{fake}' in {phones}"

    def test_engagement_multiple_turns(self, result):
        assert len(result["turns"]) >= 5, (
            f"Expected >= 5 turns, got {len(result['turns'])}"
        )

    def test_all_turns_under_30s(self, result):
        for t in result["turns"]:
            assert t["elapsed"] < 30, (
                f"Turn {t['turn']} took {t['elapsed']}s (limit 30s)"
            )

    def test_score_above_60(self, result):
        assert result["score"].total >= 60, (
            f"bank_fraud score {result['score'].total}/100 < 60 minimum\n"
            f"  Detection:    {result['score'].scam_detection}/20\n"
            f"  Intelligence: {result['score'].intelligence_extraction}/40\n"
            f"  Engagement:   {result['score'].engagement_quality}/20\n"
            f"  Structure:    {result['score'].response_structure}/20\n"
            f"  Details: {result['score'].details}"
        )


class TestMultiTurnUPIFraud:
    """Full multi-turn conversation for upi_fraud scenario."""

    @pytest.fixture(scope="class")
    def result(self, _server_health):
        scenario = next(s for s in SCENARIOS if s["scenarioId"] == "upi_fraud")
        scoring_resp, turns = run_multi_turn(scenario)
        score = score_scenario(scoring_resp, scenario["fakeData"], scenario["scenarioId"])
        return {"response": scoring_resp, "turns": turns, "score": score, "scenario": scenario}

    def test_all_turns_return_reply(self, result):
        for t in result["turns"]:
            reply = t["response"].get("reply") or t["response"].get("message")
            assert reply, f"Turn {t['turn']} missing reply"

    def test_scam_detected(self, result):
        assert result["response"].get("scamDetected") is True

    def test_upi_id_extracted(self, result):
        intel = result["response"].get("extractedIntelligence", {})
        upis = intel.get("upiIds", [])
        fake = result["scenario"]["fakeData"]["upiId"]
        assert any(fake in str(u) for u in upis), (
            f"Expected UPI ID '{fake}' in {upis}"
        )

    def test_phone_number_extracted(self, result):
        intel = result["response"].get("extractedIntelligence", {})
        phones = intel.get("phoneNumbers", [])
        fake = result["scenario"]["fakeData"]["phoneNumber"]
        fake_normalized = fake.replace("-", "")
        assert any(
            fake in str(p) or fake_normalized in str(p).replace("-", "")
            for p in phones
        ), f"Expected phone '{fake}' in {phones}"

    def test_engagement_multiple_turns(self, result):
        assert len(result["turns"]) >= 5

    def test_all_turns_under_30s(self, result):
        for t in result["turns"]:
            assert t["elapsed"] < 30

    def test_score_above_60(self, result):
        assert result["score"].total >= 60, (
            f"upi_fraud score {result['score'].total}/100 < 60 minimum\n"
            f"  Detection:    {result['score'].scam_detection}/20\n"
            f"  Intelligence: {result['score'].intelligence_extraction}/40\n"
            f"  Engagement:   {result['score'].engagement_quality}/20\n"
            f"  Structure:    {result['score'].response_structure}/20\n"
            f"  Details: {result['score'].details}"
        )


class TestMultiTurnPhishing:
    """Full multi-turn conversation for phishing_link scenario."""

    @pytest.fixture(scope="class")
    def result(self, _server_health):
        scenario = next(s for s in SCENARIOS if s["scenarioId"] == "phishing_link")
        scoring_resp, turns = run_multi_turn(scenario)
        score = score_scenario(scoring_resp, scenario["fakeData"], scenario["scenarioId"])
        return {"response": scoring_resp, "turns": turns, "score": score, "scenario": scenario}

    def test_all_turns_return_reply(self, result):
        for t in result["turns"]:
            reply = t["response"].get("reply") or t["response"].get("message")
            assert reply, f"Turn {t['turn']} missing reply"

    def test_scam_detected(self, result):
        assert result["response"].get("scamDetected") is True

    def test_phishing_link_extracted(self, result):
        intel = result["response"].get("extractedIntelligence", {})
        links = intel.get("phishingLinks", [])
        fake = result["scenario"]["fakeData"]["phishingLink"]
        assert any(fake in str(lnk) for lnk in links), (
            f"Expected phishing link '{fake}' in {links}"
        )

    def test_email_extracted(self, result):
        intel = result["response"].get("extractedIntelligence", {})
        emails = intel.get("emailAddresses", [])
        fake = result["scenario"]["fakeData"]["emailAddress"]
        assert any(fake in str(e) for e in emails), (
            f"Expected email '{fake}' in {emails}"
        )

    def test_engagement_multiple_turns(self, result):
        assert len(result["turns"]) >= 5

    def test_all_turns_under_30s(self, result):
        for t in result["turns"]:
            assert t["elapsed"] < 30

    def test_score_above_60(self, result):
        assert result["score"].total >= 60, (
            f"phishing_link score {result['score'].total}/100 < 60 minimum\n"
            f"  Detection:    {result['score'].scam_detection}/20\n"
            f"  Intelligence: {result['score'].intelligence_extraction}/40\n"
            f"  Engagement:   {result['score'].engagement_quality}/20\n"
            f"  Structure:    {result['score'].response_structure}/20\n"
            f"  Details: {result['score'].details}"
        )


# ---------------------------------------------------------------------------
# Tests — Weighted final score across all scenarios
# ---------------------------------------------------------------------------
class TestWeightedFinalScore:
    """Compute the weighted final score across all 3 sample scenarios."""

    @pytest.fixture(scope="class")
    def all_scores(self, _server_health) -> list[tuple[dict, ScoreBreakdown]]:
        results = []
        for scenario in SCENARIOS:
            scoring_resp, _turns = run_multi_turn(scenario)
            bd = score_scenario(scoring_resp, scenario["fakeData"], scenario["scenarioId"])
            results.append((scenario, bd))
        return results

    def test_final_weighted_score_above_60(self, all_scores):
        total_weight = sum(s["weight"] for s, _ in all_scores)
        weighted = sum(
            bd.total * (s["weight"] / total_weight) for s, bd in all_scores
        )

        report_lines = ["\n========== GUVI EVALUATION REPORT =========="]
        for scenario, bd in all_scores:
            report_lines.append(
                f"\n  {scenario['scenarioId']} (weight={scenario['weight']}):"
                f" {bd.total:.1f}/100"
            )
            report_lines.append(f"    Detection:    {bd.scam_detection:.0f}/20")
            report_lines.append(
                f"    Intelligence: {bd.intelligence_extraction:.0f}/40"
            )
            report_lines.append(f"    Engagement:   {bd.engagement_quality:.0f}/20")
            report_lines.append(f"    Structure:    {bd.response_structure:.0f}/20")
            if bd.details.get("intelligence_matches"):
                for item, matched in bd.details["intelligence_matches"].items():
                    status = "FOUND" if matched else "MISSING"
                    report_lines.append(f"      [{status}] {item}")
        report_lines.append(f"\n  WEIGHTED FINAL SCORE: {weighted:.1f}/100")
        report_lines.append("=" * 45)

        report = "\n".join(report_lines)
        print(report)

        assert weighted >= 60, f"Weighted score {weighted:.1f}/100 < 60\n{report}"

    def test_all_scenarios_detect_scam(self, all_scores):
        for scenario, bd in all_scores:
            assert bd.scam_detection == 20.0, (
                f"{scenario['scenarioId']}: scam not detected"
            )


# ---------------------------------------------------------------------------
# Tests — Response structure validation
# ---------------------------------------------------------------------------
class TestResponseStructure:
    """Validate the response format matches GUVI evaluation expectations."""

    @pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["scenarioId"])
    def test_analyze_response_has_status_and_reply(self, _server_health, scenario):
        """The /analyze endpoint must return {status, reply}."""
        ts = datetime.now(timezone.utc).isoformat()
        body = {
            "message": {
                "sender": "scammer",
                "text": scenario["initialMessage"],
                "timestamp": ts,
            },
            "conversationHistory": [],
            "metadata": scenario["metadata"],
        }
        resp = requests.post(ANALYZE_URL, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        data = resp.json()
        assert "status" in data, "Response missing 'status'"
        reply = data.get("reply") or data.get("message") or data.get("text")
        assert reply, "Response missing reply/message/text"

    @pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["scenarioId"])
    def test_reply_is_non_empty_string(self, _server_health, scenario):
        """The /analyze reply must be a non-empty string."""
        ts = datetime.now(timezone.utc).isoformat()
        body = {
            "message": {
                "sender": "scammer",
                "text": scenario["initialMessage"],
                "timestamp": ts,
            },
            "conversationHistory": [],
            "metadata": scenario["metadata"],
        }
        resp = requests.post(ANALYZE_URL, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        data = resp.json()
        reply = data.get("reply") or data.get("message") or data.get("text")
        assert isinstance(reply, str) and len(reply) > 0, (
            f"Reply must be a non-empty string, got: {reply!r}"
        )


# ---------------------------------------------------------------------------
# Tests — Edge cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    """Edge-case and robustness tests."""

    def test_empty_message_returns_error_or_400(self, _server_health):
        body = {
            "message": {"sender": "scammer", "text": "", "timestamp": "2026-01-01T00:00:00Z"},
            "conversationHistory": [],
            "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
        }
        resp = requests.post(ANALYZE_URL, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        # Either 400 (validation error) or 422 (Pydantic) is acceptable
        assert resp.status_code in (400, 422), (
            f"Empty message should be rejected, got {resp.status_code}"
        )

    def test_non_scam_message_gets_reply(self, _server_health):
        """A normal message should still return a valid reply."""
        body = {
            "message": {
                "sender": "friend",
                "text": "Hey, are you coming to the party tonight?",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "conversationHistory": [],
            "metadata": {"channel": "WhatsApp", "language": "English", "locale": "IN"},
        }
        resp = requests.post(ANALYZE_URL, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        reply = data.get("reply") or data.get("message") or data.get("text")
        assert reply, "Non-scam message should still get a reply"

    def test_session_id_consistency(self, _server_health):
        """Sending the same sessionId should maintain context."""
        session_id = str(uuid.uuid4())
        scenario = SCENARIOS[0]  # bank_fraud
        ts = datetime.now(timezone.utc).isoformat()

        # Turn 1
        body1 = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": scenario["initialMessage"],
                "timestamp": ts,
            },
            "conversationHistory": [],
            "metadata": scenario["metadata"],
        }
        resp1 = requests.post(ANALYZE_URL, json=body1, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        assert resp1.status_code == 200
        reply1 = resp1.json().get("reply", "")

        # Turn 2 with history
        body2 = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": "Please share your account number immediately sir.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "conversationHistory": [
                {"sender": "scammer", "text": scenario["initialMessage"], "timestamp": ts},
                {"sender": "user", "text": reply1, "timestamp": ts},
            ],
            "metadata": scenario["metadata"],
        }
        resp2 = requests.post(ANALYZE_URL, json=body2, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2.get("reply") or data2.get("message") or data2.get("text"), (
            "Second turn should still produce a reply"
        )

    def test_epoch_timestamp_accepted(self, _server_health):
        """Server should accept epoch milliseconds as timestamp."""
        body = {
            "message": {
                "sender": "scammer",
                "text": SCENARIOS[0]["initialMessage"],
                "timestamp": int(time.time() * 1000),  # epoch ms
            },
            "conversationHistory": [],
            "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
        }
        resp = requests.post(ANALYZE_URL, json=body, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        assert resp.status_code == 200