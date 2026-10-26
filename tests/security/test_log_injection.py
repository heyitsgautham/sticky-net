"""A caller-chosen session ID cannot forge extra log lines."""

import json
import logging
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog

from src.api import session_store
from src.api.callback import RESPONSE_SNIPPET_CHARS, send_guvi_callback
from src.logging_config import configure_logging

FORGED = 'abc\n2026-01-01 00:00:00 [error    ] Admin login succeeded user="root"'


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    structlog.reset_defaults()
    configure_logging("INFO", "console")
    root.handlers, root.level = handlers, level


def _settings(enabled: bool) -> MagicMock:
    settings = MagicMock()
    settings.guvi_callback_enabled = enabled
    settings.guvi_callback_url = "https://callback.example.invalid/result"
    settings.guvi_callback_timeout = 1.0
    return settings


async def _send() -> bool:
    return await send_guvi_callback(
        session_id=FORGED,
        scam_detected=True,
        total_messages=2,
        intelligence={},
        agent_notes="n",
    )


@pytest.mark.parametrize("fmt", ["json", "console"])
async def test_callback_logs_keep_the_session_id_on_one_line(
    fmt: str, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("INFO", fmt)  # type: ignore[arg-type]
    with patch("src.api.callback.get_settings", return_value=_settings(enabled=False)):
        assert await _send() is True

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 1
    assert not any(line.startswith("2026-01-01") for line in lines)
    if fmt == "json":
        record = json.loads(lines[0])
        assert record["session_id"] == FORGED
        assert record["event"] == "GUVI callback disabled, skipping"


async def test_rejected_callback_logs_a_short_body(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "json")
    response = MagicMock(status_code=500, text="x" * 5000)
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("src.api.callback.get_settings", return_value=_settings(enabled=True)),
        patch("src.api.callback.httpx.AsyncClient", return_value=client),
    ):
        assert await _send() is False

    [record] = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line]
    assert record["event"] == "GUVI callback rejected"
    assert record["status_code"] == 500
    assert len(record["body"]) == RESPONSE_SNIPPET_CHARS


def test_session_store_logs_the_session_id_as_a_field(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("DEBUG", "json")
    broken = MagicMock()
    broken.collection.side_effect = RuntimeError("firestore down")
    monkeypatch.setattr(session_store, "_firestore_client", broken)
    monkeypatch.setattr(session_store, "_firestore_available", True)

    session_store.get_session_start_time(FORGED)

    [record] = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line]
    assert record["event"] == "Firestore read failed"
    assert record["session_id"] == FORGED
    assert record["error"] == "firestore down"
