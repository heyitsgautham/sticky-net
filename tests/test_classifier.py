"""Tests for ScamClassifier.classify against a fake Gemini client.

The root conftest makes genai.Client return ``offline_services``, so each test
scripts that fake's generate_content to stand in for Vertex AI.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.api.schemas import ConversationMessage, Metadata
from src.detection.classifier import ClassificationResult, ScamClassifier


def _gemini(text: str) -> SimpleNamespace:
    part = SimpleNamespace(text=text)
    return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))])


def _verdict(**fields: object) -> SimpleNamespace:
    body = {"is_scam": True, "confidence": 0.9, "scam_type": "banking_fraud", **fields}
    return _gemini(json.dumps(body))


async def test_classify_parses_the_primary_model_reply(offline_services: MagicMock) -> None:
    offline_services.models.generate_content.side_effect = None
    offline_services.models.generate_content.return_value = _verdict(
        threat_indicators=["urgency"], reasoning="account threat"
    )
    classifier = ScamClassifier()

    result = await classifier.classify("Your account is blocked")

    assert result.is_scam is True
    assert result.confidence == pytest.approx(0.9)
    assert result.scam_type == "banking_fraud"
    assert result.threat_indicators == ["urgency"]
    assert classifier._last_model_used == classifier.model


async def test_classify_falls_back_when_the_primary_model_fails(
    offline_services: MagicMock,
) -> None:
    offline_services.models.generate_content.side_effect = [
        RuntimeError("503 from gemini-3"),
        _verdict(scam_type="job_offer"),
    ]
    classifier = ScamClassifier()

    result = await classifier.classify("Earn 5000 daily from home")

    assert result.scam_type == "job_offer"
    assert classifier._last_model_used == classifier.fallback_model
    models = [c.kwargs["model"] for c in offline_services.models.generate_content.call_args_list]
    assert models == [classifier.model, classifier.fallback_model]


async def test_classify_falls_back_on_an_empty_reply(offline_services: MagicMock) -> None:
    offline_services.models.generate_content.side_effect = [_gemini(""), _verdict()]
    classifier = ScamClassifier()

    result = await classifier.classify("verify now")

    assert result.is_scam is True
    assert classifier._last_model_used == classifier.fallback_model


async def test_classify_returns_uncertain_when_every_model_fails(
    offline_services: MagicMock,
) -> None:
    result = await ScamClassifier().classify("hello")

    assert result.is_scam is False
    assert result.confidence == 0.5
    assert "All models failed" in result.reasoning


async def test_prompt_carries_history_metadata_and_previous_verdict(
    offline_services: MagicMock,
) -> None:
    offline_services.models.generate_content.side_effect = None
    offline_services.models.generate_content.return_value = _verdict()
    history = [ConversationMessage(sender="scammer", text="I am from SBI", timestamp=0)]

    await ScamClassifier().classify(
        "share the OTP",
        history=history,
        metadata=Metadata(channel="WhatsApp", locale="IN"),
        previous_classification=ClassificationResult(is_scam=True, confidence=0.7),
    )

    prompt = offline_services.models.generate_content.call_args.kwargs["contents"]
    assert "[SCAMMER]: I am from SBI" in prompt
    assert "channel=WhatsApp" in prompt
    assert "is_scam=True, confidence=0.7" in prompt
    assert '"share the OTP"' in prompt
