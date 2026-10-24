"""Tests for the regex fast path that flags obvious scams without an LLM call."""

import pytest

from src.detection.detector import ScamDetector


@pytest.mark.parametrize(
    "message",
    [
        "Your SBI account is blocked. Pay now to restore it.",
        "Your account is now frozen due to KYC issues",
        "Your account will be blocked today",
        "Your account has been suspended",
        "Your account is being deactivated",
    ],
)
def test_account_threats_are_caught_in_any_tense(message: str) -> None:
    result = ScamDetector._regex_classify(message)

    assert result is not None
    assert result.is_scam
    assert result.scam_type == "banking_fraud"
    assert "account_threat" in result.threat_indicators


@pytest.mark.parametrize(
    "message",
    [
        "Hello, how are you doing today?",
        "Your OTP is 482913. Do not share it with anyone.",
    ],
)
def test_ordinary_messages_are_left_to_the_classifier(message: str) -> None:
    assert ScamDetector._regex_classify(message) is None
