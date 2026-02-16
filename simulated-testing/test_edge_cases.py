"""
Edge case scenario tests — boundary conditions, unusual patterns.

Tests system resilience against:
  - Rapid intel dumps (all data at once)
  - Slow intel drip (data over 10 turns)
  - Suspicious scammers
  - Very long/short messages
  - Normal-to-scam transitions
  - Multiple identities
  - Max turn conversations
"""

import pytest
from conftest import scenario_params


@pytest.mark.parametrize("scenario", scenario_params("edge_cases"))
def test_edge_case_scenario(runner, scenario):
    """Run an edge case scenario and validate GUVI scoring."""
    result = runner.run_scenario(scenario)

    print(f"\n{result.score.summary()}")
    print(f"  Turns: {len(result.conversation.replies)}")
    print(f"  Duration: {result.conversation.duration_seconds:.1f}s")
    if result.conversation.errors:
        print(f"  Errors: {result.conversation.errors}")

    min_score = scenario.get("expected_score", {}).get("min", 30)
    assert result.score.total >= min_score, (
        f"Score {result.score.total} below minimum {min_score} for "
        f"{result.scenario_id}. Issues: {result.score.issues}"
    )
    assert len(result.conversation.errors) == 0, (
        f"API errors: {result.conversation.errors}"
    )


@pytest.mark.parametrize("scenario", scenario_params("edge_cases"))
def test_edge_case_reply_present(runner, scenario):
    """Every turn should receive a non-empty reply."""
    result = runner.run_scenario(scenario)
    for i, reply in enumerate(result.conversation.replies):
        assert reply, f"Empty reply at turn {i + 1} for {result.scenario_id}"


# ======================================================================
# Targeted edge case tests
# ======================================================================
class TestRapidIntelDump:
    """Test that all intel is extracted when dumped in a single message."""

    def test_rapid_dump_extraction(self, runner, scenarios_dir):
        import json
        path = scenarios_dir / "edge_cases" / "edge_01_rapid_intel_dump.json"
        if not path.exists():
            pytest.skip("Scenario file not found")
        with open(path) as f:
            scenario = json.load(f)

        result = runner.run_scenario(scenario)
        print(f"\n{result.score.summary()}")

        # With all data in turn 1, extraction should be good
        assert result.score.scam_detection == 20.0
        assert result.score.intelligence_extraction >= 10.0, (
            "Should extract at least 1 item from rapid dump"
        )


class TestSlowDrip:
    """Test intelligence accumulation over 10 turns."""

    def test_slow_drip_accumulation(self, runner, scenarios_dir):
        import json
        path = scenarios_dir / "edge_cases" / "edge_02_slow_drip.json"
        if not path.exists():
            pytest.skip("Scenario file not found")
        with open(path) as f:
            scenario = json.load(f)

        result = runner.run_scenario(scenario)
        print(f"\n{result.score.summary()}")

        # Should have high engagement (10 turns, long duration)
        assert result.score.engagement_quality >= 10.0, (
            "10-turn conversation should score well on engagement"
        )


class TestNormalToScam:
    """Test transition from normal conversation to scam."""

    def test_transition_detection(self, runner, scenarios_dir):
        import json
        path = scenarios_dir / "edge_cases" / "edge_06_normal_to_scam.json"
        if not path.exists():
            pytest.skip("Scenario file not found")
        with open(path) as f:
            scenario = json.load(f)

        result = runner.run_scenario(scenario)
        print(f"\n{result.score.summary()}")

        # System should eventually detect the scam
        # Even if first few turns were non-scam
        assert result.score.total >= 20.0, (
            "Should score at least on detection after transition"
        )


class TestVeryShortMessages:
    """Test handling of 1-3 word scammer messages."""

    def test_short_messages_no_crash(self, runner, scenarios_dir):
        import json
        path = scenarios_dir / "edge_cases" / "edge_05_very_short_messages.json"
        if not path.exists():
            pytest.skip("Scenario file not found")
        with open(path) as f:
            scenario = json.load(f)

        result = runner.run_scenario(scenario)
        print(f"\n{result.score.summary()}")

        # Should not crash and should respond to all turns
        assert len(result.conversation.errors) == 0


class TestMaxTurns:
    """Test full 10-turn conversation with spread-out intel."""

    def test_max_turns_engagement(self, runner, scenarios_dir):
        import json
        path = scenarios_dir / "edge_cases" / "edge_08_max_turns.json"
        if not path.exists():
            pytest.skip("Scenario file not found")
        with open(path) as f:
            scenario = json.load(f)

        result = runner.run_scenario(scenario)
        print(f"\n{result.score.summary()}")

        # Full 10-turn conversation should max engagement
        assert result.score.engagement_quality >= 10.0
        assert len(result.conversation.replies) >= 8, (
            "Should have responses for most turns"
        )
