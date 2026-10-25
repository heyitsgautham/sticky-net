"""Error replies must not carry exception text to the client."""

from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

SECRET_DETAIL = "Firestore credentials at /secrets/service-account.json rejected"


def _body() -> dict[str, Any]:
    return {
        "sessionId": "disclosure-test",
        "message": {"sender": "scammer", "text": "pay now", "timestamp": "2026-01-21T10:15:30Z"},
        "conversationHistory": [],
        "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
    }


def test_detailed_endpoint_hides_exception_text() -> None:
    client = TestClient(app)
    with patch("src.api.routes.get_detector", side_effect=RuntimeError(SECRET_DETAIL)):
        response = client.post("/api/v1/analyze/detailed", json=_body())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["scamDetected"] is False
    assert SECRET_DETAIL not in response.text
    assert "RuntimeError" not in response.text
    assert body["agentNotes"] == "Analysis failed; see server logs for details."


def test_analyze_endpoint_hides_exception_text() -> None:
    client = TestClient(app)
    with patch("src.api.routes.get_detector", side_effect=RuntimeError(SECRET_DETAIL)):
        response = client.post("/api/v1/analyze", json=_body())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["reply"] == "Sorry, I'm having trouble right now. Can we talk later?"
    assert SECRET_DETAIL not in response.text


def test_validation_errors_do_not_echo_the_input() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/analyze", json={"message": {"text": SECRET_DETAIL}})

    assert response.status_code == 200
    assert SECRET_DETAIL not in response.text
