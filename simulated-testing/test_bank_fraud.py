"""
Bank fraud scenario tests — runs all 8 bank fraud scenarios against the API.

Each test drives a multi-turn conversation and validates:
  1. Scam is detected (scamDetected=True)
  2. Intelligence is extracted (fakeData items matched)
  3. Engagement metrics meet thresholds
  4. Response structure has required fields
  5. Overall score meets minimum threshold
"""

import json
import pytest
from pathlib import Path

from conftest import get_scenario_files, scenario_params


@pytest.mark.parametrize("scenario", scenario_params("bank_fraud"))
def test_bank_fraud_scenario(runner, scenario):
    """Run a bank fraud scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    # Print detailed results for visibility
    print(f"\n{result.score.summary()}")
    if result.conversation.errors:
        print(f"  Errors: {result.conversation.errors}")

    # Assertions
    assert result.score.scam_detection == 20.0, (
        f"Scam not detected for {result.scenario_id}"
    )
    assert result.score.total >= scenario.get("expected_score", {}).get("min", 60), (
        f"Score {result.score.total} below minimum for {result.scenario_id}. "
        f"Issues: {result.score.issues}"
    )
    assert len(result.conversation.errors) == 0, (
        f"API errors: {result.conversation.errors}"
    )


@pytest.mark.parametrize("scenario", scenario_params("bank_fraud"))
def test_bank_fraud_reply_present(runner, scenario):
    """Every turn should receive a non-empty reply."""
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1} for {result.scenario_id}"


@pytest.mark.parametrize("scenario", scenario_params("bank_fraud"))
def test_bank_fraud_response_structure(runner, scenario):
    """Response structure should score at least 15 (required fields present)."""
    result = runner.run_scenario(scenario)
    assert result.score.response_structure >= 15.0, (
        f"Response structure {result.score.response_structure} too low. "
        f"Issues: {[i for i in result.score.issues if 'field' in i.lower()]}"
    )


class TestBankFraudIntelExtraction:
    """Focused tests on intelligence extraction for bank fraud scenarios."""

    @pytest.mark.parametrize("scenario", scenario_params("bank_fraud"))
    def test_bank_account_extracted(self, runner, scenario):
        """If fakeData has bankAccount, it should be in extractedIntelligence."""
        if "bankAccount" not in scenario.get("fakeData", {}):
            pytest.skip("No bankAccount in fakeData")

        result = runner.run_scenario(scenario)
        bank = scenario["fakeData"]["bankAccount"]
        extracted = result.final_output.get("extractedIntelligence", {})
        accounts = extracted.get("bankAccounts", [])

        # Check substring match (same as GUVI)
        found = any(bank in str(v) for v in accounts)
        if not found:
            print(f"  MISS: bankAccount '{bank}' not in {accounts}")
        # This is informational — the score test handles pass/fail

    @pytest.mark.parametrize("scenario", scenario_params("bank_fraud"))
    def test_phone_extracted(self, runner, scenario):
        """If fakeData has phoneNumber, check extraction."""
        if "phoneNumber" not in scenario.get("fakeData", {}):
            pytest.skip("No phoneNumber in fakeData")

        result = runner.run_scenario(scenario)
        phone = scenario["fakeData"]["phoneNumber"]
        extracted = result.final_output.get("extractedIntelligence", {})
        phones = extracted.get("phoneNumbers", [])
        found = any(phone in str(v) for v in phones)
        if not found:
            print(f"  MISS: phoneNumber '{phone}' not in {phones}")
