"""
Mixed language scenario tests — Hinglish, Tanglish, Bengali-English.

Tests that scam detection and intelligence extraction work across
code-mixed language conversations.
"""

import pytest
from conftest import scenario_params


@pytest.mark.parametrize("scenario", scenario_params("mixed_language"))
def test_mixed_language_scenario(runner, scenario):
    """Run a mixed-language scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    print(f"\n{result.score.summary()}")
    lang = scenario.get("metadata", {}).get("language", "Unknown")
    print(f"  Language: {lang}")
    if result.conversation.errors:
        print(f"  Errors: {result.conversation.errors}")

    assert result.score.scam_detection == 20.0, (
        f"Scam not detected for {result.scenario_id} ({lang})"
    )
    assert result.score.total >= scenario.get("expected_score", {}).get("min", 40), (
        f"Score {result.score.total} below minimum for {result.scenario_id}. "
        f"Issues: {result.score.issues}"
    )
    assert len(result.conversation.errors) == 0


@pytest.mark.parametrize("scenario", scenario_params("mixed_language"))
def test_mixed_language_reply_present(runner, scenario):
    """Every turn should receive a non-empty reply regardless of language."""
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1} for {result.scenario_id}"


@pytest.mark.parametrize("scenario", scenario_params("mixed_language"))
def test_mixed_language_intel_extraction(runner, scenario):
    """Verify intelligence extraction works for mixed-language messages."""
    result = runner.run_scenario(scenario)
    fake_data = scenario.get("fakeData", {})

    if not fake_data:
        pytest.skip("No fakeData to check")

    # Report extraction results
    extracted = result.final_output.get("extractedIntelligence", {})
    from guvi_scoring_engine import FAKE_DATA_KEY_MAPPING

    for key, value in fake_data.items():
        output_key = FAKE_DATA_KEY_MAPPING.get(key, key)
        values = extracted.get(output_key, [])
        found = any(value in str(v) for v in values) if isinstance(values, list) else value in str(values)
        status = "FOUND" if found else "MISS"
        print(f"  {key}: '{value}' → {status} (in {values})")


@pytest.mark.parametrize("scenario", scenario_params("mixed_language"))
def test_mixed_language_response_structure(runner, scenario):
    """Response structure should have at least required fields."""
    result = runner.run_scenario(scenario)
    assert result.score.response_structure >= 15.0
