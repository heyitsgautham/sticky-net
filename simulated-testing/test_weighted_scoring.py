"""
Weighted scoring tests — validates the weighted final score calculation
across multiple scenario groups, replicating GUVI's evaluation approach.
"""

import json
import pytest
from pathlib import Path

from guvi_scoring_engine import ScoreBreakdown, weighted_final_score
from conftest import get_scenario_files


class TestWeightedScoringCalculation:
    """Test weighted final score across scenario groups."""

    def test_three_scenarios_guvi_default(self, runner, scenarios_dir):
        """
        Run 3 representative scenarios with GUVI default weights [0.35, 0.35, 0.30].
        Mirrors the exact evaluation from SAMPLE_CASE.md.
        """
        # Pick one scenario from each of the 3 primary categories
        scenario_files = [
            scenarios_dir / "bank_fraud" / "bank_fraud_01_sbi_otp.json",
            scenarios_dir / "upi_fraud" / "upi_fraud_01_cashback.json",
            scenarios_dir / "phishing" / "phishing_01_amazon_deal.json",
        ]

        # Skip if any file is missing
        for f in scenario_files:
            if not f.exists():
                pytest.skip(f"Missing scenario file: {f}")

        breakdowns = []
        for f in scenario_files:
            with open(f) as fp:
                scenario = json.load(fp)
            result = runner.run_scenario(scenario)
            breakdowns.append(result.score)
            print(f"\n  {result.scenario_id}: {result.score.total:.1f}/100")

        weights = [0.35, 0.35, 0.30]
        final = weighted_final_score(breakdowns, weights)
        print(f"\n  Weighted Final Score: {final:.1f}/100")

        # Should be a meaningful score (system is working)
        assert final >= 0.0
        assert final <= 100.0

    def test_five_scenarios_equal_weights(self, runner, scenarios_dir):
        """
        Run 5 diverse scenarios with equal weights [0.20 each].
        Tests broad coverage across scam types.
        """
        scenario_files = [
            scenarios_dir / "bank_fraud" / "bank_fraud_01_sbi_otp.json",
            scenarios_dir / "upi_fraud" / "upi_fraud_01_cashback.json",
            scenarios_dir / "phishing" / "phishing_01_amazon_deal.json",
            scenarios_dir / "job_scam" / "job_scam_01_wfh.json",
            scenarios_dir / "lottery_scam" / "lottery_01_kaun_banega.json",
        ]

        for f in scenario_files:
            if not f.exists():
                pytest.skip(f"Missing scenario file: {f}")

        breakdowns = []
        for f in scenario_files:
            with open(f) as fp:
                scenario = json.load(fp)
            result = runner.run_scenario(scenario)
            breakdowns.append(result.score)
            print(f"\n  {result.scenario_id}: {result.score.total:.1f}/100")

        weights = [0.20] * 5
        final = weighted_final_score(breakdowns, weights)
        print(f"\n  Weighted Final Score: {final:.1f}/100")

        assert final >= 0.0
        assert final <= 100.0

    def test_high_weight_scenario_dominates(self, runner, scenarios_dir):
        """
        A high-weight scenario should dominate the final score.
        If bank_fraud (90% weight) scores low, final score should be low.
        """
        scenario_files = [
            scenarios_dir / "bank_fraud" / "bank_fraud_01_sbi_otp.json",
            scenarios_dir / "phishing" / "phishing_01_amazon_deal.json",
        ]

        for f in scenario_files:
            if not f.exists():
                pytest.skip(f"Missing scenario file: {f}")

        breakdowns = []
        for f in scenario_files:
            with open(f) as fp:
                scenario = json.load(fp)
            result = runner.run_scenario(scenario)
            breakdowns.append(result.score)

        # Heavy weight on first scenario
        weights = [0.90, 0.10]
        final = weighted_final_score(breakdowns, weights)

        # Final score should be close to the first scenario's score
        expected_approx = breakdowns[0].total * 0.9 + breakdowns[1].total * 0.1
        assert abs(final - expected_approx) < 0.01

        print(f"\n  Scenario 1 (90% weight): {breakdowns[0].total:.1f}")
        print(f"  Scenario 2 (10% weight): {breakdowns[1].total:.1f}")
        print(f"  Weighted Final: {final:.1f}")


class TestWeightedScoringEdgeCases:
    """Edge cases in weighted scoring calculation."""

    def test_single_scenario_weight_1(self):
        bd = ScoreBreakdown(
            scam_detection=20,
            intelligence_extraction=30,
            engagement_quality=15,
            response_structure=17.5,
        )
        result = weighted_final_score([bd], [1.0])
        assert result == pytest.approx(82.5)

    def test_all_perfect_scores(self):
        bds = [
            ScoreBreakdown(
                scam_detection=20,
                intelligence_extraction=40,
                engagement_quality=20,
                response_structure=20,
            )
            for _ in range(3)
        ]
        result = weighted_final_score(bds, [0.35, 0.35, 0.30])
        assert result == pytest.approx(100.0)

    def test_all_zero_scores(self):
        bds = [ScoreBreakdown() for _ in range(3)]
        result = weighted_final_score(bds, [0.35, 0.35, 0.30])
        assert result == pytest.approx(0.0)

    def test_mixed_scores(self):
        bds = [
            ScoreBreakdown(scam_detection=20, intelligence_extraction=30,
                           engagement_quality=20, response_structure=20),  # 90
            ScoreBreakdown(scam_detection=20, intelligence_extraction=40,
                           engagement_quality=20, response_structure=20),  # 100
            ScoreBreakdown(scam_detection=20, intelligence_extraction=20,
                           engagement_quality=15, response_structure=20),  # 75
        ]
        result = weighted_final_score(bds, [0.35, 0.35, 0.30])
        expected = 90 * 0.35 + 100 * 0.35 + 75 * 0.30
        assert result == pytest.approx(expected)
