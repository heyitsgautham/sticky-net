"""Sentry error tracking: off without a DSN, scrubbed and tagged with one."""

from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import sentry_sdk
from fastapi.testclient import TestClient
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

from src.error_tracking import capture_exception, init_error_tracking, scrub_event
from src.log_redaction import REDACTED
from src.main import app
from tests.helpers import make_settings

DSN = "https://public@errors.example.invalid/1"


class RecordingTransport(Transport):
    """Keeps events in memory instead of sending them anywhere."""

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        super().__init__(options)
        self.events: list[dict[str, Any]] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        for item in envelope.items:
            if item.type == "event" and item.payload.json is not None:
                self.events.append(item.payload.json)


@pytest.fixture
def transport() -> Iterator[RecordingTransport]:
    recorder = RecordingTransport()
    assert init_error_tracking(
        make_settings(error_tracking_dsn=DSN, environment="staging"),
        transport=recorder,
        default_integrations=False,
    )
    yield recorder
    sentry_sdk.get_client().close()
    sentry_sdk.init()  # back to a disabled client for the rest of the suite


def _flush() -> None:
    sentry_sdk.flush()


def test_no_dsn_means_no_client() -> None:
    assert init_error_tracking(make_settings()) is False
    assert not sentry_sdk.is_initialized()
    capture_exception(RuntimeError("ignored"))  # must not raise


def test_captured_exception_carries_tags_and_release(transport: RecordingTransport) -> None:
    capture_exception(ValueError("bad reply"), route="/api/v1/analyze", session_id="s-1")
    _flush()

    [event] = transport.events
    assert event["exception"]["values"][0]["type"] == "ValueError"
    assert event["tags"] == {"route": "/api/v1/analyze", "session_id": "s-1"}
    assert event["environment"] == "staging"
    assert event["release"].startswith("sticky-net@")


def test_none_context_values_are_not_tagged(transport: RecordingTransport) -> None:
    capture_exception(ValueError("x"), session_id=None, component="guvi_callback")
    _flush()
    assert transport.events[0]["tags"] == {"component": "guvi_callback"}


def test_route_errors_are_reported(transport: RecordingTransport) -> None:
    body = {
        "sessionId": "track-1",
        "message": {"sender": "scammer", "text": "pay", "timestamp": "2026-01-21T10:15:30Z"},
    }
    with patch("src.api.routes.get_detector", side_effect=RuntimeError("vertex down")):
        response = TestClient(app).post("/api/v1/analyze/detailed", json=body)
    _flush()

    assert response.status_code == 200
    [event] = transport.events
    assert event["tags"]["route"] == "/api/v1/analyze/detailed"
    assert event["tags"]["session_id"] == "track-1"


async def test_callback_failures_are_reported(transport: RecordingTransport) -> None:
    from src.api.routes import _fire_callback

    with patch("src.api.routes.send_guvi_callback", new=AsyncMock(side_effect=OSError("down"))):
        await _fire_callback(session_id="cb-1")
    _flush()

    assert transport.events[0]["tags"] == {"component": "guvi_callback", "session_id": "cb-1"}


def test_scrub_event_masks_credentials() -> None:
    event: Any = {
        "request": {"headers": {"x-api-key": "live-key", "accept": "*/*"}},
        "extra": {"note": "Bearer abc.def"},
        "message": "kept",
    }
    scrubbed = scrub_event(event, {})
    assert scrubbed["request"]["headers"] == {"x-api-key": REDACTED, "accept": "*/*"}
    assert scrubbed["extra"]["note"] == f"Bearer {REDACTED}"
    assert scrubbed["message"] == "kept"
