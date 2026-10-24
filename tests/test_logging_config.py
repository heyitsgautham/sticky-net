"""Tests for the shared structlog and stdlib logging setup."""

import json
import logging
from collections.abc import Iterator

import pytest
import structlog
from pydantic import ValidationError

from config.settings import Settings
from src.logging_config import configure_logging


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    """Put back the root handlers and structlog config each test replaces."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    structlog.reset_defaults()
    configure_logging("INFO", "console")
    root.handlers, root.level = handlers, level


def _json_lines(text: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_json_format_renders_structlog_events_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "json")

    structlog.get_logger("sticky.test").info("scam detected", confidence=0.9)

    [record] = _json_lines(capsys.readouterr().out)
    assert record["event"] == "scam detected"
    assert record["confidence"] == 0.9
    assert record["level"] == "info"
    assert record["logger"] == "sticky.test"
    assert "timestamp" in record


def test_json_format_also_covers_stdlib_loggers(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "json")

    logging.getLogger("src.api.session_store").warning("Firestore unavailable: %s", "timeout")

    [record] = _json_lines(capsys.readouterr().out)
    assert record["event"] == "Firestore unavailable: timeout"
    assert record["level"] == "warning"
    assert record["logger"] == "src.api.session_store"


def test_level_filters_lower_records(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("WARNING", "json")

    structlog.get_logger("sticky.test").info("dropped")
    structlog.get_logger("sticky.test").error("kept")

    assert [r["event"] for r in _json_lines(capsys.readouterr().out)] == ["kept"]


def test_json_format_serialises_exceptions(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "json")

    try:
        raise ValueError("bad payload")
    except ValueError:
        structlog.get_logger("sticky.test").exception("request failed")

    [record] = _json_lines(capsys.readouterr().out)
    assert "ValueError: bad payload" in str(record["exception"])


def test_console_format_is_not_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "console")

    structlog.get_logger("sticky.test").info("hello", turn=3)

    out = capsys.readouterr().out
    assert "hello" in out
    assert "turn=3" in out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out.splitlines()[0])


class TestLogSettings:
    """LOG_LEVEL and LOG_FORMAT are validated when Settings loads."""

    def test_accepts_any_case(self) -> None:
        settings = Settings(
            api_key="k", google_cloud_project="p", log_level="debug", log_format="CONSOLE"
        )
        assert settings.log_level == "DEBUG"
        assert settings.log_format == "console"

    def test_rejects_unknown_format(self) -> None:
        with pytest.raises(ValidationError, match="log_format"):
            Settings(api_key="k", google_cloud_project="p", log_format="xml")

    def test_rejects_unknown_level(self) -> None:
        with pytest.raises(ValidationError, match="log_level"):
            Settings(api_key="k", google_cloud_project="p", log_level="LOUD")
