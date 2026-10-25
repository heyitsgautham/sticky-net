"""Entry-point limits on request size, and the catch-all error handler."""

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.schemas import MAX_HISTORY_MESSAGES, MAX_MESSAGE_CHARS, AnalyzeRequest
from src.main import app

FALLBACK = "sorry i didnt understand that... can you say again?"


def _body(text: str = "hello", history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "sessionId": "limits-test",
        "message": {"sender": "scammer", "text": text, "timestamp": "2026-01-21T10:15:30Z"},
        "conversationHistory": history or [],
    }


def _turn(text: str = "hi") -> dict[str, Any]:
    return {"sender": "scammer", "text": text, "timestamp": "2026-01-21T10:14:00Z"}


def test_a_full_evaluator_conversation_fits() -> None:
    request = AnalyzeRequest(**_body(history=[_turn() for _ in range(20)]))
    assert len(request.conversationHistory) == 20


@pytest.mark.parametrize(
    "body",
    [
        _body(history=[_turn() for _ in range(MAX_HISTORY_MESSAGES + 1)]),
        _body(history=[_turn("x" * (MAX_MESSAGE_CHARS + 1))]),
        _body(text="x" * (MAX_MESSAGE_CHARS + 1)),
    ],
    ids=["too-many-history-messages", "oversized-history-message", "oversized-message"],
)
def test_oversized_requests_get_the_fallback_reply(
    client: TestClient, body: dict[str, Any]
) -> None:
    with patch("src.api.routes.get_detector") as detector:
        response = client.post("/api/v1/analyze", json=body)

    # The evaluator scores non-200 turns as zero, so limits answer 200 with a stall.
    assert response.status_code == 200
    assert response.json()["reply"] == FALLBACK
    detector.assert_not_called()


def test_unhandled_errors_return_json_without_details() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    with patch("src.api.routes.init_session_start_time", side_effect=RuntimeError("secret path")):
        response = client.post("/api/v1/analyze", json=_body())

    assert response.status_code == 500
    assert response.json() == {"status": "error", "detail": "internal error"}
    assert "secret" not in response.text
