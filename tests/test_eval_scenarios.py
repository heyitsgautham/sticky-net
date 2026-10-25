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
    .venv/bin/python -m pytest tests/test_eval_scenarios.py -m integration -v

Requires:
    Server running on http://localhost:8000
"""

import time
import uuid
from datetime import UTC, datetime

import pytest
import requests

from tests.live_eval_support import (
    ANALYZE_URL,
    BASE_URL,
    HEADERS,
    REQUEST_TIMEOUT,
    SCENARIOS,
    ScoreBreakdown,
    run_multi_turn,
    score_scenario,
)

# These tests drive a live server, which calls Gemini for real.
# They are deselected by default; run them with `pytest -m integration`.
pytestmark = pytest.mark.integration


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
        ts = datetime.now(UTC).isoformat()
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
        ts = datetime.now(UTC).isoformat()
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
        ts = datetime.now(UTC).isoformat()
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
        assert any(fake in str(u) for u in upis), f"Expected UPI ID '{fake}' in {upis}"

    def test_phone_number_extracted(self, result):
        intel = result["response"].get("extractedIntelligence", {})
        phones = intel.get("phoneNumbers", [])
        fake = result["scenario"]["fakeData"]["phoneNumber"]
        fake_normalized = fake.replace("-", "")
        assert any(fake in str(p) or fake_normalized in str(p).replace("-", "") for p in phones), (
            f"Expected phone '{fake}' in {phones}"
        )

    def test_engagement_multiple_turns(self, result):
        assert len(result["turns"]) >= 5, f"Expected >= 5 turns, got {len(result['turns'])}"

    def test_all_turns_under_30s(self, result):
        for t in result["turns"]:
            assert t["elapsed"] < 30, f"Turn {t['turn']} took {t['elapsed']}s (limit 30s)"

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
        assert any(fake in str(u) for u in upis), f"Expected UPI ID '{fake}' in {upis}"

    def test_phone_number_extracted(self, result):
        intel = result["response"].get("extractedIntelligence", {})
        phones = intel.get("phoneNumbers", [])
        fake = result["scenario"]["fakeData"]["phoneNumber"]
        fake_normalized = fake.replace("-", "")
        assert any(fake in str(p) or fake_normalized in str(p).replace("-", "") for p in phones), (
            f"Expected phone '{fake}' in {phones}"
        )

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
        assert any(fake in str(lnk) for lnk in links), f"Expected phishing link '{fake}' in {links}"

    def test_email_extracted(self, result):
        intel = result["response"].get("extractedIntelligence", {})
        emails = intel.get("emailAddresses", [])
        fake = result["scenario"]["fakeData"]["emailAddress"]
        assert any(fake in str(e) for e in emails), f"Expected email '{fake}' in {emails}"

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
        weighted = sum(bd.total * (s["weight"] / total_weight) for s, bd in all_scores)

        report_lines = ["\n========== GUVI EVALUATION REPORT =========="]
        for scenario, bd in all_scores:
            report_lines.append(
                f"\n  {scenario['scenarioId']} (weight={scenario['weight']}): {bd.total:.1f}/100"
            )
            report_lines.append(f"    Detection:    {bd.scam_detection:.0f}/20")
            report_lines.append(f"    Intelligence: {bd.intelligence_extraction:.0f}/40")
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
            assert bd.scam_detection == 20.0, f"{scenario['scenarioId']}: scam not detected"


# ---------------------------------------------------------------------------
# Tests — Response structure validation
# ---------------------------------------------------------------------------
class TestResponseStructure:
    """Validate the response format matches GUVI evaluation expectations."""

    @pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["scenarioId"])
    def test_analyze_response_has_status_and_reply(self, _server_health, scenario):
        """The /analyze endpoint must return {status, reply}."""
        ts = datetime.now(UTC).isoformat()
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
        ts = datetime.now(UTC).isoformat()
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
                "timestamp": datetime.now(UTC).isoformat(),
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
        ts = datetime.now(UTC).isoformat()

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
                "timestamp": datetime.now(UTC).isoformat(),
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
