"""Tests for the agent's per-turn prompt, notes and seeded fake profile."""

from datetime import datetime

from src.agents.conversation import build_turn_prompt, engagement_notes, summarize_earlier_turns
from src.agents.fake_profile import build_fake_profile, format_fake_profile
from src.agents.persona import Persona
from src.agents.policy import EngagementMode
from src.api.schemas import ConversationMessage, ExtractedIntelligence, Message
from src.detection.detector import DetectionResult


def _msg(sender: str, text: str) -> ConversationMessage:
    return ConversationMessage(sender=sender, text=text, timestamp=datetime(2026, 1, 21))


def _new(text: str) -> Message:
    return Message(sender="scammer", text=text, timestamp=datetime(2026, 1, 21))


def test_fake_profile_is_stable_per_conversation() -> None:
    first = build_fake_profile("conv-a")
    assert build_fake_profile("conv-a")["account_number"] == first["account_number"]
    assert build_fake_profile("conv-b")["account_number"] != first["account_number"]


def test_fake_profile_formats_card_in_groups_of_four() -> None:
    profile = build_fake_profile("conv-a")
    groups = profile["card_number_formatted"].split(" ")
    assert "".join(groups) == profile["card_number_raw"]
    assert all(len(g) == 4 for g in groups[:3])
    section = format_fake_profile(profile)
    assert f"- Bank Account: {profile['account_number']}" in section
    assert f"- Customer ID: {profile['customer_id']}" in section


def test_prompt_without_history_says_so() -> None:
    prompt = build_turn_prompt(_new("verify now"), [], max_turns=8)
    assert "No previous messages" in prompt
    assert '"verify now"' in prompt


def test_prompt_labels_speakers() -> None:
    history = [_msg("scammer", "I am from SBI"), _msg("user", "which branch?")]
    prompt = build_turn_prompt(_new("Koramangala"), history, max_turns=8)
    assert "[SCAMMER]: I am from SBI" in prompt
    assert "[YOU]: which branch?" in prompt


def test_long_history_is_summarised_beyond_the_window() -> None:
    history = [_msg("scammer", "call +919876543210 now")] + [
        _msg("user" if i % 2 else "scammer", f"turn {i}") for i in range(1, 10)
    ]
    prompt = build_turn_prompt(_new("hello"), history, max_turns=4)

    assert "[SUMMARY OF EARLIER 6 MESSAGES]" in prompt
    assert "phone: +919876543210" in prompt
    assert "RECENT CONVERSATION HISTORY" in prompt
    assert "turn 9" in prompt


def test_summary_of_nothing_is_empty() -> None:
    assert summarize_earlier_turns([]) == ""


def test_engagement_notes_list_mode_type_and_intel_counts() -> None:
    notes = engagement_notes(
        DetectionResult(is_scam=True, confidence=0.9, scam_type="banking_fraud"),
        Persona(),
        EngagementMode.AGGRESSIVE,
        turn_number=3,
        extracted_intel=ExtractedIntelligence(upiIds=["a@ybl", "b@ybl"], caseIds=["REF1"]),
    )
    assert notes.startswith("Mode: aggressive | Type: banking_fraud | Confidence: 90% | Turn: 3")
    assert "Extracted: 2 UPI ID(s), 1 Case ID(s)" in notes
