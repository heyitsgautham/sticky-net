"""Tests for reading Gemini output: text extraction, fence stripping, agent reply parsing."""

import json
from types import SimpleNamespace

import pytest

from src.agents.reply_parser import parse_agent_reply
from src.llm import response_text, strip_code_fences


def _response(*parts: object) -> SimpleNamespace:
    return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=list(parts)))])


def test_response_text_joins_text_parts_and_skips_thought_signatures() -> None:
    response = _response(
        SimpleNamespace(text="hello "),
        SimpleNamespace(thought_signature=b"sig"),
        SimpleNamespace(text="sir"),
    )
    assert response_text(response) == "hello sir"  # type: ignore[arg-type]


def test_response_text_without_candidates_is_empty() -> None:
    assert response_text(SimpleNamespace(candidates=None)) == ""  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("raw", "inner"),
    [
        ('```json\n{"a": 1}\n```', '{"a": 1}'),
        ('```\n{"a": 1}\n```', '{"a": 1}'),
        ('  {"a": 1}  ', '{"a": 1}'),
    ],
)
def test_strip_code_fences(raw: str, inner: str) -> None:
    assert strip_code_fences(raw) == inner


def test_full_json_reply_returns_text_and_intel() -> None:
    raw = json.dumps(
        {
            "reply_text": "which bank sir?",
            "emotional_tone": "worried",
            "extracted_intelligence": {"upiIds": ["fraud@ybl"]},
        }
    )

    reply, intel = parse_agent_reply(f"```json\n{raw}\n```")

    assert reply == "which bank sir?"
    assert intel is not None
    assert intel.upiIds == ["fraud@ybl"]


def test_partial_json_still_yields_reply_and_salvaged_intel() -> None:
    # emotional_tone is missing, so the full model fails to validate.
    raw = json.dumps(
        {"reply_text": "ok beta", "extracted_intelligence": {"phoneNumbers": ["9876543210"]}}
    )

    reply, intel = parse_agent_reply(raw)

    assert reply == "ok beta"
    assert intel is not None
    assert intel.phoneNumbers == ["9876543210"]


def test_partial_json_with_bad_intel_keeps_the_reply() -> None:
    raw = json.dumps({"reply_text": "hmm", "extracted_intelligence": {"upiIds": 5}})

    assert parse_agent_reply(raw) == ("hmm", None)


def test_plain_text_is_used_as_the_reply() -> None:
    assert parse_agent_reply("arre what happened?") == ("arre what happened?", None)
