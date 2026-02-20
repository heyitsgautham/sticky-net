"""
Tests for the scammer simulator module.
"""

import pytest

from eval_framework.scammer_simulator import ScammerSimulator, build_scripted_followups
from eval_framework.scenarios import (
    BANK_FRAUD_SCENARIO,
    UPI_FRAUD_SCENARIO,
    PHISHING_SCENARIO,
)


class TestScriptedFollowups:
    def test_bank_fraud_has_all_turns(self):
        msgs = build_scripted_followups(BANK_FRAUD_SCENARIO)
        assert len(msgs) == 10

    def test_upi_fraud_has_all_turns(self):
        msgs = build_scripted_followups(UPI_FRAUD_SCENARIO)
        assert len(msgs) == 10

    def test_phishing_has_all_turns(self):
        msgs = build_scripted_followups(PHISHING_SCENARIO)
        assert len(msgs) == 10

    def test_bank_fraud_embeds_fake_data(self):
        msgs = build_scripted_followups(BANK_FRAUD_SCENARIO)
        all_text = " ".join(msgs)
        fake = BANK_FRAUD_SCENARIO["fakeData"]
        for key, value in fake.items():
            assert value in all_text, f"Fake data {key}={value} not found in followups"

    def test_upi_fraud_embeds_fake_data(self):
        msgs = build_scripted_followups(UPI_FRAUD_SCENARIO)
        all_text = " ".join(msgs)
        fake = UPI_FRAUD_SCENARIO["fakeData"]
        for key, value in fake.items():
            assert value in all_text, f"Fake data {key}={value} not found in followups"

    def test_phishing_embeds_fake_data(self):
        msgs = build_scripted_followups(PHISHING_SCENARIO)
        all_text = " ".join(msgs)
        fake = PHISHING_SCENARIO["fakeData"]
        for key, value in fake.items():
            assert value in all_text, f"Fake data {key}={value} not found in followups"


class TestScammerSimulatorScripted:
    @pytest.fixture
    def simulator(self):
        return ScammerSimulator(mode="scripted")

    @pytest.mark.asyncio
    async def test_returns_turn_message(self, simulator):
        msg = await simulator.generate_followup(
            scenario=BANK_FRAUD_SCENARIO,
            turn_number=2,
            conversation_history=[],
            agent_last_response="I'm concerned about my account.",
        )
        assert len(msg) > 0
        # Turn 2 should mention the phone number
        assert "+91-9823456710" in msg

    @pytest.mark.asyncio
    async def test_fallback_when_turns_exhausted(self, simulator):
        """Should return a generic message when scripted turns run out."""
        msg = await simulator.generate_followup(
            scenario=BANK_FRAUD_SCENARIO,
            turn_number=99,  # Way beyond configured turns
            conversation_history=[],
            agent_last_response="Tell me more.",
        )
        assert len(msg) > 0  # Should still return something

    @pytest.mark.asyncio
    async def test_initial_message_turn_1(self, simulator):
        msg = await simulator.generate_followup(
            scenario=BANK_FRAUD_SCENARIO,
            turn_number=1,
            conversation_history=[],
            agent_last_response="",
        )
        assert "URGENT" in msg or "compromised" in msg


class TestScammerSimulatorAIFallback:
    """Test that AI mode falls back gracefully without a client."""

    @pytest.fixture
    def simulator(self):
        return ScammerSimulator(mode="ai", genai_client=None)

    @pytest.mark.asyncio
    async def test_ai_without_client_falls_back(self, simulator):
        msg = await simulator.generate_followup(
            scenario=BANK_FRAUD_SCENARIO,
            turn_number=2,
            conversation_history=[],
            agent_last_response="Tell me more.",
        )
        assert len(msg) > 0  # Should fall back to scripted
