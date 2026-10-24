"""Behaviour tests for /api/v1/analyze and /api/v1/analyze/detailed.

The detector and agent are replaced with fakes, so these exercise the route
logic itself: regex backup extraction, intel accumulation, the final-turn
summary, the timeout fallback and error handling.
"""

import asyncio
import uuid
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.agents.honeypot_agent import EngagementResult
from src.agents.policy import EngagementMode
from src.api.schemas import ExtractedIntelligence
from src.detection.detector import DetectionResult
from src.exceptions import ScamDetectionError

SCAM_TEXT = "Your SBI account is blocked. Call +91-9876543210 or pay to fraud.help@okaxis now."


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


def _engagement(reply: str, intel: ExtractedIntelligence | None = None) -> EngagementResult:
    return EngagementResult(
        response=reply,
        duration_seconds=1,
        notes="",
        conversation_id="conv-1",
        turn_number=1,
        engagement_mode=EngagementMode.AGGRESSIVE,
        should_continue=True,
        extracted_intelligence=intel,
    )


@pytest.fixture
def session_id() -> str:
    return f"route-{uuid.uuid4()}"


@pytest.fixture
def detector() -> Iterator[MagicMock]:
    fake = MagicMock()
    fake.analyze = AsyncMock(
        return_value=DetectionResult(is_scam=True, confidence=0.92, scam_type="banking_fraud")
    )
    with patch("src.api.routes.get_detector", return_value=fake):
        yield fake


@pytest.fixture
def agent() -> Iterator[MagicMock]:
    fake = MagicMock()
    fake.engage = AsyncMock(return_value=_engagement("which account sir?"))
    fake._generate_notes = MagicMock(return_value="notes")
    with patch("src.api.routes.get_agent", return_value=fake):
        yield fake


@pytest.fixture
def callback() -> Iterator[AsyncMock]:
    with patch("src.api.routes.send_guvi_callback", new_callable=AsyncMock) as fake:
        fake.return_value = True
        yield fake


class TestAnalyze:
    def test_regex_backup_feeds_the_callback(
        self,
        client: TestClient,
        detector: MagicMock,
        agent: MagicMock,
        callback: AsyncMock,
        session_id: str,
    ) -> None:
        response = client.post("/api/v1/analyze", json=_body(SCAM_TEXT, session_id))

        assert response.json()["reply"] == "which account sir?"
        intel = callback.await_args.kwargs["intelligence"]
        assert "fraud.help@okaxis" in intel["upiIds"]
        assert any(p.endswith("9876543210") for p in intel["phoneNumbers"])
        assert callback.await_args.kwargs["session_id"] == session_id
        assert callback.await_args.kwargs["scam_type"] == "banking_fraud"

    def test_agent_is_told_which_intel_is_still_missing(
        self, client: TestClient, detector: MagicMock, agent: MagicMock, callback: AsyncMock
    ) -> None:
        client.post("/api/v1/analyze", json=_body("hello sir", f"route-{uuid.uuid4()}"))

        missing = agent.engage.await_args.kwargs["missing_intel"]
        assert "UPI ID" in missing
        assert "bank account number" in missing

    def test_turn_number_counts_scammer_messages(
        self, client: TestClient, detector: MagicMock, agent: MagicMock, callback: AsyncMock
    ) -> None:
        history = [
            {"sender": "scammer", "text": "hi"},
            {"sender": "user", "text": "who is this"},
            {"sender": "scammer", "text": "bank calling"},
        ]
        client.post("/api/v1/analyze", json=_body("verify now", "s-turns", history))

        assert agent.engage.await_args.kwargs["turn_number"] == 3

    def test_agent_timeout_returns_a_stalling_reply(
        self,
        client: TestClient,
        detector: MagicMock,
        agent: MagicMock,
        callback: AsyncMock,
        session_id: str,
    ) -> None:
        agent.engage = AsyncMock(side_effect=asyncio.TimeoutError)

        response = client.post("/api/v1/analyze", json=_body(SCAM_TEXT, session_id))

        data = response.json()
        assert data["status"] == "success"
        assert data["reply"]

    def test_application_error_returns_status_error(
        self, client: TestClient, detector: MagicMock, session_id: str
    ) -> None:
        detector.analyze = AsyncMock(side_effect=ScamDetectionError("classifier down"))

        data = client.post("/api/v1/analyze", json=_body(SCAM_TEXT, session_id)).json()

        assert data["status"] == "error"
        assert "trouble" in data["reply"]


class TestConversationEnd:
    def test_returns_accumulated_intelligence(
        self,
        client: TestClient,
        detector: MagicMock,
        agent: MagicMock,
        callback: AsyncMock,
        session_id: str,
    ) -> None:
        client.post("/api/v1/analyze", json=_body(SCAM_TEXT, session_id))
        history = [
            {"sender": "scammer", "text": SCAM_TEXT},
            {"sender": "user", "text": "which account sir?"},
            {"sender": "scammer", "text": "Account 123456789012, email help@sbi-verify.com"},
        ]

        data = client.post(
            "/api/v1/analyze", json=_body("[CONVERSATION_END]", session_id, history)
        ).json()

        assert data["sessionId"] == session_id
        assert data["scamDetected"] is True
        assert data["scamType"] == "banking_fraud"
        assert data["confidenceLevel"] == pytest.approx(0.92)
        assert data["totalMessagesExchanged"] == 4
        assert data["engagementDurationSeconds"] >= 4 * 25
        intel = data["extractedIntelligence"]
        assert "fraud.help@okaxis" in intel["upiIds"]
        assert "123456789012" in intel["bankAccounts"]
        assert "help@sbi-verify.com" in intel["emailAddresses"]
        assert "upi=1" in data["agentNotes"]
        detector.analyze.assert_awaited_once()

    def test_unknown_session_with_honeypot_replies_counts_as_scam(
        self, client: TestClient, session_id: str
    ) -> None:
        history = [
            {"sender": "scammer", "text": "hello"},
            {"sender": "user", "text": "who is this"},
        ]

        data = client.post(
            "/api/v1/analyze", json=_body("[CONVERSATION_END]", session_id, history)
        ).json()

        assert data["scamDetected"] is True
        assert data["scamType"] == "banking_fraud"
        assert data["confidenceLevel"] == pytest.approx(0.85)

    def test_unknown_session_without_engagement_is_not_scam(
        self, client: TestClient, session_id: str
    ) -> None:
        data = client.post("/api/v1/analyze", json=_body("[CONVERSATION_END]", session_id)).json()

        assert data["scamDetected"] is False
        assert data["confidenceLevel"] == 0.0


class TestAnalyzeDetailed:
    def test_returns_full_analysis(
        self, client: TestClient, detector: MagicMock, agent: MagicMock, session_id: str
    ) -> None:
        agent.engage = AsyncMock(
            return_value=_engagement(
                "ok", ExtractedIntelligence(ifscCodes=["SBIN0001234"], bankNames=["SBI"])
            )
        )

        data = client.post("/api/v1/analyze/detailed", json=_body(SCAM_TEXT, session_id)).json()

        assert data["scamDetected"] is True
        assert data["scamType"] == "banking_fraud"
        assert data["agentResponse"] == "ok"
        assert data["agentNotes"] == "notes"
        intel = data["extractedIntelligence"]
        assert "fraud.help@okaxis" in intel["upiIds"]
        assert intel["ifscCodes"] == ["SBIN0001234"]
        assert data["engagementMetrics"]["totalMessagesExchanged"] == 2

    def test_unknown_scam_type_maps_to_others(
        self, client: TestClient, detector: MagicMock, agent: MagicMock, session_id: str
    ) -> None:
        detector.analyze = AsyncMock(
            return_value=DetectionResult(is_scam=True, confidence=0.8, scam_type="crypto")
        )

        data = client.post("/api/v1/analyze/detailed", json=_body(SCAM_TEXT, session_id)).json()

        assert data["scamType"] == "others"

    def test_not_scam_skips_the_agent(
        self, client: TestClient, detector: MagicMock, agent: MagicMock, session_id: str
    ) -> None:
        detector.analyze = AsyncMock(return_value=DetectionResult(is_scam=False, confidence=0.2))

        data = client.post("/api/v1/analyze/detailed", json=_body("hi", session_id)).json()

        assert data["scamDetected"] is False
        assert data["confidence"] == pytest.approx(0.2)
        agent.engage.assert_not_called()

    def test_errors_return_status_error(
        self, client: TestClient, detector: MagicMock, session_id: str
    ) -> None:
        detector.analyze = AsyncMock(side_effect=RuntimeError("boom"))

        data = client.post("/api/v1/analyze/detailed", json=_body(SCAM_TEXT, session_id)).json()

        assert data["status"] == "error"
        assert data["scamDetected"] is False
        assert "boom" in data["agentNotes"]
