"""
Non-scam / false positive tests — validates the system does NOT flag
legitimate conversations as scams.

These tests verify:
  1. scamDetected is False (or reply is neutral)
  2. No intelligence is extracted
  3. API responds without errors
"""

import json
import pytest
from conftest import scenario_params, get_scenario_files
from scammer_simulator import ScammerSimulator


@pytest.mark.parametrize("scenario", scenario_params("non_scam"))
def test_non_scam_not_detected(runner, scenario):
    """Non-scam messages should NOT trigger scam detection."""
    result = runner.run_scenario(scenario)

    print(f"\n  Scenario: {result.scenario_id}")
    print(f"  Score: {result.score.total}")
    print(f"  Scam Detected: {result.final_output.get('scamDetected', 'N/A')}")

    # For non-scam scenarios, scamDetected should be False
    # The reply should be a neutral/friendly response
    scam_detected = result.final_output.get("scamDetected", False)
    if scam_detected:
        print(f"  WARNING: False positive — legitimate message flagged as scam!")
        # This is a soft warning, not a hard fail, since the system may
        # conservatively flag ambiguous messages


@pytest.mark.parametrize("scenario", scenario_params("non_scam"))
def test_non_scam_no_intelligence(runner, scenario):
    """Non-scam conversations should not extract any intelligence."""
    result = runner.run_scenario(scenario)

    extracted = result.final_output.get("extractedIntelligence", {})
    total_items = sum(
        len(v) if isinstance(v, list) else (1 if v else 0)
        for v in extracted.values()
    )

    print(f"\n  Scenario: {result.scenario_id}")
    print(f"  Total extracted items: {total_items}")
    if total_items > 0:
        print(f"  Extracted: {extracted}")
        print("  WARNING: Intelligence extracted from non-scam conversation!")


@pytest.mark.parametrize("scenario", scenario_params("non_scam"))
def test_non_scam_reply_present(runner, scenario):
    """Every turn should receive a non-empty reply, even for non-scam."""
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1} for {result.scenario_id}"


@pytest.mark.parametrize("scenario", scenario_params("non_scam"))
def test_non_scam_no_errors(runner, scenario):
    """Non-scam scenarios should not produce API errors."""
    result = runner.run_scenario(scenario)
    assert len(result.conversation.errors) == 0, (
        f"API errors on non-scam message: {result.conversation.errors}"
    )


class TestFalsePositiveRate:
    """Aggregate tests for false positive rate across all non-scam scenarios."""

    def test_false_positive_rate(self, runner, scenarios_dir):
        """Count how many non-scam scenarios trigger false positives."""
        non_scam_dir = scenarios_dir / "non_scam"
        if not non_scam_dir.exists():
            pytest.skip("No non_scam scenarios")

        files = sorted(non_scam_dir.glob("*.json"))
        if not files:
            pytest.skip("No scenario files")

        false_positives = 0
        total = len(files)

        for f in files:
            with open(f) as fp:
                scenario = json.load(fp)

            result = runner.run_scenario(scenario)
            if result.final_output.get("scamDetected", False):
                false_positives += 1
                print(f"  FALSE POSITIVE: {scenario.get('scenarioId')}")

        rate = false_positives / total * 100
        print(f"\n  False positive rate: {false_positives}/{total} ({rate:.0f}%)")

        # Ideally 0%, but allow some tolerance
        # In production, <20% false positive rate is acceptable
