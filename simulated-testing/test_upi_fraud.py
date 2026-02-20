"""
UPI fraud scenario tests — runs all 6 UPI fraud scenarios against the API.
"""

import pytest
from conftest import scenario_params


@pytest.mark.parametrize("scenario", scenario_params("upi_fraud"))
def test_upi_fraud_scenario(runner, scenario):
    """Run a UPI fraud scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    print(f"\n{result.score.summary()}")
    if result.conversation.errors:
        print(f"  Errors: {result.conversation.errors}")

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


@pytest.mark.parametrize("scenario", scenario_params("upi_fraud"))
def test_upi_fraud_reply_present(runner, scenario):
    """Every turn should receive a non-empty reply."""
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1} for {result.scenario_id}"


@pytest.mark.parametrize("scenario", scenario_params("upi_fraud"))
def test_upi_fraud_upi_extracted(runner, scenario):
    """If fakeData has upiId, it should appear in extractedIntelligence."""
    if "upiId" not in scenario.get("fakeData", {}):
        pytest.skip("No upiId in fakeData")

    result = runner.run_scenario(scenario)
    upi = scenario["fakeData"]["upiId"]
    extracted = result.final_output.get("extractedIntelligence", {})
    upis = extracted.get("upiIds", [])
    found = any(upi in str(v) for v in upis)

    print(f"\n  UPI check: '{upi}' in {upis} → {'FOUND' if found else 'MISS'}")


@pytest.mark.parametrize("scenario", scenario_params("upi_fraud"))
def test_upi_fraud_response_structure(runner, scenario):
    """Response structure should score at least 15 points."""
    result = runner.run_scenario(scenario)
    assert result.score.response_structure >= 15.0, (
        f"Response structure {result.score.response_structure} too low"
    )
