"""Credentials are masked in log output, whichever logger wrote them."""

import json
import logging
from collections.abc import Iterator

import pytest
import structlog

from src.log_redaction import REDACTED, is_secret_name, redact_text, redact_value
from src.logging_config import configure_logging

KEY = "sk-live-4f9a8c7e2b"


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    structlog.reset_defaults()
    configure_logging("INFO", "console")
    root.handlers, root.level = handlers, level


def _records(text: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_structlog_fields_named_like_secrets_are_masked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("INFO", "json")
    structlog.get_logger("t").info("auth", api_key=KEY, x_api_key=KEY, session_id="s-1")

    out = capsys.readouterr().out
    [record] = _records(out)
    assert record["api_key"] == REDACTED
    assert record["x_api_key"] == REDACTED
    assert record["session_id"] == "s-1"
    assert KEY not in out


def test_nested_header_dicts_are_masked(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "json")
    headers = {"x-api-key": KEY, "Authorization": f"Bearer {KEY}", "accept": "*/*"}
    structlog.get_logger("t").info("request", headers=headers)

    out = capsys.readouterr().out
    [record] = _records(out)
    assert record["headers"] == {"x-api-key": REDACTED, "Authorization": REDACTED, "accept": "*/*"}
    assert KEY not in out


def test_stdlib_messages_with_inline_keys_are_masked(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "json")
    logging.getLogger("src.api.callback").warning("retrying with x-api-key: %s", KEY)

    out = capsys.readouterr().out
    [record] = _records(out)
    assert record["event"] == f"retrying with x-api-key: {REDACTED}"
    assert KEY not in out


def test_console_format_is_masked_too(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", "console")
    structlog.get_logger("t").warning("oops", password=KEY)
    assert KEY not in capsys.readouterr().out


def test_honeypot_intelligence_is_not_masked() -> None:
    # Scammer bank and UPI details are the product's output, not our secrets.
    intel = {"upiIds": ["fraud@okaxis"], "bankAccounts": ["123456789012"]}
    assert redact_value(intel) == intel


@pytest.mark.parametrize(
    "name",
    ["api_key", "API-KEY", "x-api-key", "GUVI_API_KEY", "client_secret", "refresh_token"],
)
def test_secret_names(name: str) -> None:
    assert is_secret_name(name)


@pytest.mark.parametrize("name", ["session_id", "tokens_used", "keyword", "upiIds", "monkey"])
def test_ordinary_names(name: str) -> None:
    assert not is_secret_name(name)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"apiKey":"abc123"}', f'{{"apiKey":"{REDACTED}"}}'),
        ("curl -H 'x-api-key: abc123'", f"curl -H 'x-api-key: {REDACTED}'"),
        ("Authorization: Bearer abc.def.ghi", f"Authorization: Bearer {REDACTED}"),
        ("?api_key=abc123&page=2", f"?api_key={REDACTED}&page=2"),
        ("no secrets here", "no secrets here"),
    ],
)
def test_inline_patterns(text: str, expected: str) -> None:
    assert redact_text(text) == expected


def test_lists_and_tuples_keep_their_type() -> None:
    assert redact_value(["Bearer abc"]) == [f"Bearer {REDACTED}"]
    assert redact_value(("Bearer abc", 3)) == (f"Bearer {REDACTED}", 3)
