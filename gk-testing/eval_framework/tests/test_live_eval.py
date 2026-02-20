"""
Live API evaluation tests.

These tests require a running API server. They are skipped by default
unless the EVAL_API_URL environment variable is set.

Run:
    # Start your server first, then:
    EVAL_API_URL=http://localhost:8080 .venv/bin/python -m pytest eval_framework/tests/test_live_eval.py -v -s

    # Or with custom API key:
    EVAL_API_URL=http://localhost:8080 EVAL_API_KEY=my-key .venv/bin/python -m pytest eval_framework/tests/test_live_eval.py -v -s
"""

import asyncio
import os

import pytest

from eval_framework.runner import EvalRunner
from eval_framework.scenarios import (
    BANK_FRAUD_SCENARIO,
    UPI_FRAUD_SCENARIO,
    PHISHING_SCENARIO,
    STANDARD_SCENARIOS,
    STANDARD_WEIGHTS,
    get_scenario_suite,
)
from eval_framework.scoring import weighted_final_score

API_URL = os.environ.get("EVAL_API_URL", "")
API_KEY = os.environ.get("EVAL_API_KEY", "test-api-key")

skip_no_server = pytest.mark.skipif(
    not API_URL,
    reason="Set EVAL_API_URL=http://localhost:8080 to run live tests",
)


@skip_no_server
class TestLiveSingleScenario:
    """Run individual scenarios against the live API."""

    @pytest.fixture
    def runner(self):
        return EvalRunner(base_url=API_URL, api_key=API_KEY, timeout=30.0)

    @pytest.mark.asyncio
    async def test_bank_fraud_scenario(self, runner):
        """Bank fraud should detect scam and extract bank/UPI/phone."""
        result = await runner.run_scenario(BANK_FRAUD_SCENARIO, verbose=True)
        assert result.score is not None
        assert result.score.scam_detection == 20, "Should detect scam"
        assert result.score.total >= 50, f"Bank fraud score {result.score.total} too low"
        print(f"\n  Bank fraud score: {result.score.total:.1f}/100")

    @pytest.mark.asyncio
    async def test_upi_fraud_scenario(self, runner):
        """UPI fraud should detect scam and extract UPI/phone/email."""
        result = await runner.run_scenario(UPI_FRAUD_SCENARIO, verbose=True)
        assert result.score is not None
        assert result.score.scam_detection == 20, "Should detect scam"
        assert result.score.total >= 50, f"UPI fraud score {result.score.total} too low"
        print(f"\n  UPI fraud score: {result.score.total:.1f}/100")

    @pytest.mark.asyncio
    async def test_phishing_scenario(self, runner):
        """Phishing should detect scam and extract link/email."""
        result = await runner.run_scenario(PHISHING_SCENARIO, verbose=True)
        assert result.score is not None
        assert result.score.scam_detection == 20, "Should detect scam"
        assert result.score.total >= 50, f"Phishing score {result.score.total} too low"
        print(f"\n  Phishing score: {result.score.total:.1f}/100")


@skip_no_server
class TestLiveFullEvaluation:
    """Run the complete evaluation suite against the live API."""

    @pytest.fixture
    def runner(self):
        return EvalRunner(base_url=API_URL, api_key=API_KEY, timeout=30.0)

    @pytest.mark.asyncio
    async def test_standard_suite_competitive(self, runner):
        """Full standard suite should achieve competitive score (≥70)."""
        result = await runner.run_evaluation(
            STANDARD_SCENARIOS, STANDARD_WEIGHTS, verbose=True
        )
        assert result.weighted_score >= 70, (
            f"Weighted score {result.weighted_score:.1f} below competitive threshold of 70"
        )

    @pytest.mark.asyncio
    async def test_standard_suite_winning(self, runner):
        """Full standard suite should achieve winning score (≥85)."""
        result = await runner.run_evaluation(
            STANDARD_SCENARIOS, STANDARD_WEIGHTS, verbose=True
        )
        assert result.weighted_score >= 85, (
            f"Weighted score {result.weighted_score:.1f} below winning threshold of 85"
        )

    @pytest.mark.asyncio
    async def test_all_scenarios_detect_scam(self, runner):
        """Every scenario should be detected as a scam."""
        result = await runner.run_evaluation(
            STANDARD_SCENARIOS, STANDARD_WEIGHTS, verbose=True
        )
        for sr in result.scenarios:
            assert sr.score is not None, f"Scenario {sr.scenario_name} has no score"
            assert sr.score.scam_detection == 20, (
                f"Scenario {sr.scenario_name} failed scam detection"
            )

    @pytest.mark.asyncio
    async def test_response_times_under_30s(self, runner):
        """All responses should complete within 30s (hackathon timeout)."""
        result = await runner.run_evaluation(
            STANDARD_SCENARIOS, STANDARD_WEIGHTS, verbose=True
        )
        for sr in result.scenarios:
            for turn in sr.turns:
                assert turn.response_time_seconds < 30.0, (
                    f"{sr.scenario_name} turn {turn.turn_number}: "
                    f"{turn.response_time_seconds:.1f}s exceeds 30s timeout"
                )


@skip_no_server
class TestLiveRegressionBenchmarks:
    """
    Regression benchmarks — track score improvements over time.
    Update the expected scores as the system improves.
    """

    @pytest.fixture
    def runner(self):
        return EvalRunner(base_url=API_URL, api_key=API_KEY, timeout=30.0)

    @pytest.mark.asyncio
    async def test_intel_extraction_rate(self, runner):
        """At least 60% of fake data should be extracted across all scenarios."""
        result = await runner.run_evaluation(
            STANDARD_SCENARIOS, STANDARD_WEIGHTS, verbose=True
        )
        total_matched = sum(
            len(sr.score.intel_matched) for sr in result.scenarios if sr.score
        )
        total_items = sum(
            len(s.get("fakeData", {})) for s in STANDARD_SCENARIOS
        )
        rate = total_matched / total_items if total_items else 0
        assert rate >= 0.6, (
            f"Intel extraction rate {rate*100:.0f}% below 60% target "
            f"({total_matched}/{total_items})"
        )

    @pytest.mark.asyncio
    async def test_engagement_quality_minimum(self, runner):
        """Every scenario should get at least 6/10 engagement quality."""
        result = await runner.run_evaluation(
            STANDARD_SCENARIOS, STANDARD_WEIGHTS, verbose=True
        )
        for sr in result.scenarios:
            if sr.score:
                assert sr.score.engagement_quality >= 6, (
                    f"{sr.scenario_name}: engagement quality "
                    f"{sr.score.engagement_quality}/10 below 6 minimum"
                )
