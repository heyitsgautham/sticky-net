"""Unit tests for the helpers shared by the analyze routes."""

import time

from src.api import session_store
from src.api.final_output import (
    engagement_seconds,
    merge_regex_backup,
    missing_intel,
    to_scam_type,
)
from src.api.schemas import ExtractedIntelligence, ScamType
from src.intelligence.extractor import ExtractionResult


def test_merge_regex_backup_unions_without_duplicates() -> None:
    llm = ExtractedIntelligence(upiIds=["a@ybl"], ifscCodes=["SBIN0001234"])
    regex = ExtractionResult(upi_ids=["a@ybl", "b@okaxis"], emails=["x@fake.com"])

    merged = merge_regex_backup(llm, regex)

    assert sorted(merged.upiIds) == ["a@ybl", "b@okaxis"]
    assert merged.emailAddresses == ["x@fake.com"]
    assert merged.ifscCodes == ["SBIN0001234"]  # LLM-only fields survive


def test_merge_regex_backup_without_finds_returns_input() -> None:
    llm = ExtractedIntelligence(upiIds=["a@ybl"])
    assert merge_regex_backup(llm, ExtractionResult()) is llm


def test_missing_intel_lists_only_empty_fields() -> None:
    hints = missing_intel({"upiIds": {"a@ybl"}, "phoneNumbers": set()})
    assert "UPI ID" not in hints
    assert "phone number" in hints
    assert "case / reference ID" in hints


def test_to_scam_type() -> None:
    assert to_scam_type("job_offer") is ScamType.JOB_OFFER
    assert to_scam_type("crypto_pump") is ScamType.OTHERS
    assert to_scam_type(None) is None


def test_engagement_seconds_has_a_per_turn_floor() -> None:
    session_store.init_session_start_time("floor-test")
    assert engagement_seconds("floor-test", turns=4, fallback_start=time.time()) == 100


def test_engagement_seconds_uses_real_elapsed_time_when_longer() -> None:
    session_store._START_TIMES["elapsed-test"] = time.time() - 500
    assert engagement_seconds("elapsed-test", turns=1, fallback_start=time.time()) >= 500
