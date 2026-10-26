"""The response contract clients of the analyze API depend on.

These tests pin the status code, the exact key set and the value types of every
reply, across the success, fallback, error and rate-limit paths. They run the real
detector, agent and extractor; only Gemini is faked (to fail, so the agent uses its
canned replies). The shapes were fixed for the GUVI evaluator, which read these
field names; the only status added since is 429 for clients over the rate limit.
"""

import uuid
from collections.abc import Callable, Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config.settings import Settings
from src.api.rate_limit import limiter
from src.api.schemas import MAX_MESSAGE_CHARS
from src.detection.detector import DetectionResult
from src.main import app

SCAM = "Your SBI account will be blocked today. Share the OTP and pay to fraud.help@okaxis now."
HARMLESS = "Hello, how are you doing today?"
VALIDATION_REPLY = {
    "status": "success",
    "reply": "sorry i didnt understand that... can you say again?",
}
ERROR_REPLY = "Sorry, I'm having trouble right now. Can we talk later?"

# Every /analyze reply has these keys; per-turn replies leave all but two as null.
HONEYPOT_KEYS = {
    "status",
    "reply",
    "sessionId",
    "scamDetected",
    "scamType",
    "confidenceLevel",
    "totalMessagesExchanged",
    "engagementDurationSeconds",
    "extractedIntelligence",
    "agentNotes",
}
FINAL_ONLY_KEYS = HONEYPOT_KEYS - {"status", "reply"}
SUMMARY_INTEL_KEYS = {
    "bankAccounts",
    "upiIds",
    "phoneNumbers",
    "phishingLinks",
    "emailAddresses",
    "suspiciousKeywords",
    "caseIds",
    "policyNumbers",
    "orderNumbers",
}
DETAILED_KEYS = {
    "status",
    "scamDetected",
    "scamType",
    "confidence",
    "engagementMetrics",
    "extractedIntelligence",
    "agentNotes",
    "agentResponse",
}
DETAILED_INTEL_KEYS = SUMMARY_INTEL_KEYS | {
    "beneficiaryNames",
    "bankNames",
    "ifscCodes",
    "whatsappNumbers",
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def harmless_verdict() -> Any:
    """Make the detector call the message harmless.

    With Gemini faked to fail, the real classifier errs on the side of engaging, so the
    not-a-scam path needs an explicit verdict.
    """
    verdict = DetectionResult(is_scam=False, confidence=0.1)
    with patch("src.detection.detector.ScamDetector.analyze", new=AsyncMock(return_value=verdict)):
        yield


@pytest.fixture
def session_id() -> str:
    return f"contract-{uuid.uuid4()}"


def _body(
    text: str, session_id: str, history: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    return {
        "sessionId": session_id,
        "message": {"sender": "scammer", "text": text, "timestamp": "2026-01-21T10:15:30Z"},
        "conversationHistory": [
            {**m, "timestamp": "2026-01-21T10:14:00Z"} for m in (history or [])
        ],
        "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
    }


def _per_turn(response: Any, status: str = "success") -> dict[str, Any]:
    """Assert the shape of an ordinary /analyze turn and return its body."""
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert set(body) == HONEYPOT_KEYS
    assert body["status"] == status
    assert isinstance(body["reply"], str) and body["reply"]
    assert {key: body[key] for key in FINAL_ONLY_KEYS} == dict.fromkeys(FINAL_ONLY_KEYS)
    return body


class TestAnalyzeTurns:
    def test_scam_turn(self, client: TestClient, session_id: str) -> None:
        _per_turn(client.post("/api/v1/analyze", json=_body(SCAM, session_id)))

    def test_harmless_turn(
        self, client: TestClient, session_id: str, harmless_verdict: None
    ) -> None:
        _per_turn(client.post("/api/v1/analyze", json=_body(HARMLESS, session_id)))

    def test_follow_up_turn_with_history(self, client: TestClient, session_id: str) -> None:
        history = [{"sender": "scammer", "text": SCAM}, {"sender": "user", "text": "which bank?"}]
        response = client.post("/api/v1/analyze", json=_body("Send it now", session_id, history))
        _per_turn(response)

    def test_agent_timeout_still_answers(self, client: TestClient, session_id: str) -> None:
        with patch(
            "src.agents.honeypot_agent.HoneypotAgent.engage",
            new=AsyncMock(side_effect=TimeoutError),
        ):
            _per_turn(client.post("/api/v1/analyze", json=_body(SCAM, session_id)))

    def test_internal_error_is_status_error(self, client: TestClient, session_id: str) -> None:
        with patch("src.detection.detector.ScamDetector.analyze", side_effect=RuntimeError("x")):
            body = _per_turn(
                client.post("/api/v1/analyze", json=_body(SCAM, session_id)), status="error"
            )
        assert body["reply"] == ERROR_REPLY

    def test_session_id_is_optional(self, client: TestClient) -> None:
        body = _body(SCAM, "unused")
        del body["sessionId"]
        _per_turn(client.post("/api/v1/analyze", json=body))


class TestAnalyzeFallbacks:
    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"message": "not an object"},
            {"message": {"sender": "scammer"}},
            {"message": {"sender": "scammer", "text": "x" * (MAX_MESSAGE_CHARS + 1)}},
        ],
        ids=["empty", "message-not-object", "no-text", "oversized"],
    )
    def test_bad_bodies_get_exactly_the_two_key_reply(
        self, client: TestClient, payload: dict[str, Any]
    ) -> None:
        response = client.post("/api/v1/analyze", json=payload)
        assert response.status_code == 200
        assert response.json() == VALIDATION_REPLY

    def test_non_json_body(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/analyze", content=b"hello", headers={"content-type": "text/plain"}
        )
        assert response.status_code == 200
        assert response.json() == VALIDATION_REPLY


class TestConversationEnd:
    def test_summary_shape_after_a_scam_turn(self, client: TestClient, session_id: str) -> None:
        client.post("/api/v1/analyze", json=_body(SCAM, session_id))
        history = [{"sender": "scammer", "text": SCAM}, {"sender": "user", "text": "oh no"}]

        response = client.post(
            "/api/v1/analyze", json=_body("[CONVERSATION_END]", session_id, history)
        )

        assert response.status_code == 200
        body = response.json()
        assert set(body) == HONEYPOT_KEYS
        assert body["status"] == "success"
        assert body["reply"] == "Thank you for your time. Goodbye."
        assert body["sessionId"] == session_id
        assert body["scamDetected"] is True
        assert isinstance(body["scamType"], str)
        assert isinstance(body["confidenceLevel"], float)
        assert body["totalMessagesExchanged"] == 3
        assert isinstance(body["engagementDurationSeconds"], int)
        assert set(body["extractedIntelligence"]) == SUMMARY_INTEL_KEYS
        assert "fraud.help@okaxis" in body["extractedIntelligence"]["upiIds"]
        assert body["agentNotes"].startswith("Honeypot engaged 3 messages.")

    def test_summary_for_a_session_with_no_scam(self, client: TestClient, session_id: str) -> None:
        response = client.post("/api/v1/analyze", json=_body("[CONVERSATION_END]", session_id))
        body = response.json()
        assert response.status_code == 200
        assert set(body) == HONEYPOT_KEYS
        assert body["scamDetected"] is False
        assert body["confidenceLevel"] == 0.0


class TestDetailed:
    def _detailed(self, response: Any) -> dict[str, Any]:
        assert response.status_code == 200
        body = response.json()
        assert set(body) == DETAILED_KEYS
        assert set(body["engagementMetrics"]) == {
            "engagementDurationSeconds",
            "totalMessagesExchanged",
        }
        assert set(body["extractedIntelligence"]) == DETAILED_INTEL_KEYS
        assert isinstance(body["agentNotes"], str)
        assert isinstance(body["confidence"], float)
        return body

    def test_scam(self, client: TestClient, session_id: str) -> None:
        body = self._detailed(client.post("/api/v1/analyze/detailed", json=_body(SCAM, session_id)))
        assert body["status"] == "success"
        assert body["scamDetected"] is True
        assert body["scamType"] in {
            "banking_fraud",
            "job_offer",
            "lottery_reward",
            "impersonation",
            "others",
        }
        assert body["engagementMetrics"]["totalMessagesExchanged"] == 2
        assert isinstance(body["agentResponse"], str) and body["agentResponse"]
        assert "fraud.help@okaxis" in body["extractedIntelligence"]["upiIds"]

    def test_harmless(self, client: TestClient, session_id: str, harmless_verdict: None) -> None:
        body = self._detailed(
            client.post("/api/v1/analyze/detailed", json=_body(HARMLESS, session_id))
        )
        assert body["scamDetected"] is False
        assert body["scamType"] is None
        assert body["agentResponse"] == "Hello! How can I help you today?"

    def test_error(self, client: TestClient, session_id: str) -> None:
        with patch("src.detection.detector.ScamDetector.analyze", side_effect=RuntimeError("x")):
            body = self._detailed(
                client.post("/api/v1/analyze/detailed", json=_body(SCAM, session_id))
            )
        assert body["status"] == "error"
        assert body["scamDetected"] is False
        assert body["agentResponse"] == ERROR_REPLY


class TestRateLimit:
    @pytest.fixture
    def limit_of_two(self, use_settings: Callable[..., Settings]) -> Iterator[None]:
        limiter.clear()
        use_settings(debug=True, rate_limit_enabled=True, rate_limit_requests=2)
        yield
        limiter.clear()

    @pytest.mark.parametrize("path", ["/api/v1/analyze", "/api/v1/analyze/detailed"])
    def test_turns_past_the_limit_get_429_and_the_rest_are_unchanged(
        self, client: TestClient, session_id: str, limit_of_two: None, path: str
    ) -> None:
        allowed = [client.post(path, json=_body(SCAM, session_id)) for _ in range(2)]
        refused = client.post(path, json=_body(SCAM, session_id))

        assert [r.status_code for r in allowed] == [200, 200]
        expected_keys = HONEYPOT_KEYS if path == "/api/v1/analyze" else DETAILED_KEYS
        assert all(set(r.json()) == expected_keys for r in allowed)

        assert refused.status_code == 429
        assert refused.headers["content-type"] == "application/json"
        assert refused.json() == {"status": "error", "error": "Rate limit exceeded"}
        assert int(refused.headers["retry-after"]) >= 1

    def test_health_is_never_limited(self, client: TestClient, limit_of_two: None) -> None:
        assert [client.get("/health").status_code for _ in range(4)] == [200] * 4


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
