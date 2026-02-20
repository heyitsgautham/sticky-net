"""
Full GUVI-style evaluation — runs ALL scenarios and produces a
comprehensive results table with weighted final score.

This module replicates the complete GUVI hackathon evaluation pipeline.
"""

import json
import time
import pytest
from pathlib import Path
from datetime import datetime

from guvi_scoring_engine import ScoreBreakdown, weighted_final_score
from scenario_runner import ScenarioResult, print_results_table


SCAM_CATEGORIES = [
    "bank_fraud",
    "upi_fraud",
    "phishing",
    "job_scam",
    "lottery_scam",
    "investment_scam",
    "government_scam",
    "delivery_scam",
    "romance_scam",
    "tech_support_scam",
    "mixed_language",
    "edge_cases",
]


class TestFullEvaluation:
    """Complete GUVI-style evaluation across all scam scenarios."""

    def test_full_evaluation_all_scam_scenarios(self, runner, scenarios_dir):
        """
        Run ALL scam scenarios (excluding non_scam) and produce:
          - Per-scenario score breakdown
          - Category averages
          - Weighted final score
          - Issues report
        """
        all_results: list[ScenarioResult] = []
        category_scores: dict[str, list[float]] = {}

        for category in SCAM_CATEGORIES:
            cat_dir = scenarios_dir / category
            if not cat_dir.exists():
                continue

            files = sorted(cat_dir.glob("*.json"))
            if not files:
                continue

            cat_results = []
            for f in files:
                with open(f) as fp:
                    scenario = json.load(fp)

                result = runner.run_scenario(scenario)
                all_results.append(result)
                cat_results.append(result.score.total)

            if cat_results:
                category_scores[category] = cat_results

        # Print results table
        print_results_table(all_results)

        # Print category averages
        print("\nCATEGORY AVERAGES")
        print("-" * 50)
        for cat, scores in sorted(category_scores.items()):
            avg = sum(scores) / len(scores)
            print(f"  {cat:<25} {avg:5.1f}/100 ({len(scores)} scenarios)")

        # Calculate weighted final score (equal weights across all scenarios)
        if all_results:
            n = len(all_results)
            equal_weights = [1.0 / n] * n
            breakdowns = [r.score for r in all_results]
            final = weighted_final_score(breakdowns, equal_weights)
            print(f"\nFINAL WEIGHTED SCORE (equal weights): {final:.1f}/100")

        # Calculate GUVI-style 3-category weighted score
        primary_categories = {
            "bank_fraud": 0.35,
            "upi_fraud": 0.35,
            "phishing": 0.30,
        }
        primary_breakdowns = []
        primary_weights = []
        for cat, weight in primary_categories.items():
            if cat in category_scores:
                avg = sum(category_scores[cat]) / len(category_scores[cat])
                bd = ScoreBreakdown(scenario_id=f"avg_{cat}")
                # Store total in scam_detection for simplicity, then override
                primary_breakdowns.append(ScoreBreakdown(
                    scenario_id=f"avg_{cat}",
                    scam_detection=avg * 20 / 100,
                    intelligence_extraction=avg * 40 / 100,
                    engagement_quality=avg * 20 / 100,
                    response_structure=avg * 20 / 100,
                ))
                primary_weights.append(weight)

        if primary_breakdowns and primary_weights:
            # Normalize weights
            total_w = sum(primary_weights)
            norm_weights = [w / total_w for w in primary_weights]
            guvi_final = weighted_final_score(primary_breakdowns, norm_weights)
            print(f"GUVI-STYLE WEIGHTED SCORE (35/35/30): {guvi_final:.1f}/100")

        # Report issues
        all_issues = []
        for r in all_results:
            if r.score.issues:
                all_issues.append((r.scenario_id, r.score.issues))

        if all_issues:
            print(f"\nSCENARIOS WITH ISSUES ({len(all_issues)}):")
            for sid, issues in all_issues:
                print(f"\n  {sid}:")
                for issue in issues[:5]:  # Limit to 5 issues per scenario
                    print(f"    - {issue}")

        # Save results to JSON
        results_dir = scenarios_dir.parent / "results"
        results_dir.mkdir(exist_ok=True)
        results_file = results_dir / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        results_data = {
            "timestamp": datetime.now().isoformat(),
            "total_scenarios": len(all_results),
            "category_averages": {
                k: {"avg": sum(v) / len(v), "count": len(v)}
                for k, v in category_scores.items()
            },
            "scenarios": [
                {
                    "id": r.scenario_id,
                    "type": r.scam_type,
                    "total": r.score.total,
                    "detection": r.score.scam_detection,
                    "intel": r.score.intelligence_extraction,
                    "engagement": r.score.engagement_quality,
                    "structure": r.score.response_structure,
                    "issues": r.score.issues,
                    "errors": r.conversation.errors,
                }
                for r in all_results
            ],
        }

        with open(results_file, "w") as f:
            json.dump(results_data, f, indent=2)
        print(f"\nResults saved to: {results_file}")

        # Assertions
        assert len(all_results) > 0, "No scenarios were run"


class TestFullEvaluationSummary:
    """Summary-level checks on the full evaluation."""

    def test_all_scenario_files_valid_json(self, scenarios_dir):
        """Every .json file in scenarios/ should be valid JSON with required fields."""
        errors = []
        for json_file in sorted(scenarios_dir.rglob("*.json")):
            try:
                with open(json_file) as f:
                    data = json.load(f)

                # Check required fields
                required = ["scenarioId", "scamType", "turns", "metadata"]
                for field in required:
                    if field not in data:
                        errors.append(f"{json_file.name}: missing '{field}'")

                # Check turns have scammer_message
                for turn in data.get("turns", []):
                    if "scammer_message" not in turn:
                        errors.append(
                            f"{json_file.name}: turn {turn.get('turn', '?')} "
                            f"missing 'scammer_message'"
                        )
            except json.JSONDecodeError as e:
                errors.append(f"{json_file.name}: invalid JSON — {e}")

        if errors:
            print("\nJSON validation errors:")
            for err in errors:
                print(f"  - {err}")

        assert len(errors) == 0, f"{len(errors)} scenario file issues found"

    def test_fake_data_keys_valid(self, scenarios_dir):
        """All fakeData keys should be in the allowed mapping."""
        valid_keys = {"bankAccount", "upiId", "phoneNumber", "phishingLink", "emailAddress"}
        errors = []

        for json_file in sorted(scenarios_dir.rglob("*.json")):
            with open(json_file) as f:
                data = json.load(f)

            fake_data = data.get("fakeData", {})
            for key in fake_data:
                if key not in valid_keys:
                    errors.append(f"{json_file.name}: unknown fakeData key '{key}'")

        if errors:
            print("\nInvalid fakeData keys:")
            for err in errors:
                print(f"  - {err}")

        assert len(errors) == 0, f"{len(errors)} invalid fakeData keys found"

    def test_scenario_count(self, scenarios_dir):
        """Verify we have a comprehensive set of scenarios."""
        total = len(list(scenarios_dir.rglob("*.json")))
        print(f"\n  Total scenario files: {total}")

        # We should have at least 40 scenarios
        assert total >= 40, f"Only {total} scenarios — expected at least 40"

        # Count per category
        for category in SCAM_CATEGORIES + ["non_scam"]:
            cat_dir = scenarios_dir / category
            if cat_dir.exists():
                count = len(list(cat_dir.glob("*.json")))
                print(f"  {category}: {count}")

    def test_fake_data_in_scammer_messages(self, scenarios_dir):
        """
        Verify that fakeData values appear in scammer messages.
        This ensures the scoring engine can match them.
        """
        warnings = []

        for json_file in sorted(scenarios_dir.rglob("*.json")):
            with open(json_file) as f:
                data = json.load(f)

            fake_data = data.get("fakeData", {})
            if not fake_data:
                continue

            # Concatenate all scammer messages
            all_messages = " ".join(
                turn.get("scammer_message", "")
                for turn in data.get("turns", [])
            )

            for key, value in fake_data.items():
                if value not in all_messages:
                    warnings.append(
                        f"{json_file.name}: fakeData '{key}'='{value}' "
                        f"NOT found in any scammer_message"
                    )

        if warnings:
            print(f"\n  {len(warnings)} fakeData values not in scammer messages:")
            for w in warnings[:20]:
                print(f"    - {w}")

        # This is a critical check — if fakeData isn't in messages,
        # the system can't extract it
        assert len(warnings) == 0, (
            f"{len(warnings)} fakeData values missing from scammer messages"
        )
