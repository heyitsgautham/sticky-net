"""
Pytest wrapper for run_evaluation.py — runs against a live server.

Usage:
    # Start server first:
    #   python -m uvicorn src.main:app --host 0.0.0.0 --port 8080
    # Then run:
    #   .venv/bin/python -m pytest simulated-testing/test_live_evaluation.py -v -s
    #   .venv/bin/python -m pytest simulated-testing/test_live_evaluation.py -v -s -k bank_fraud

Requires a running server at SERVER_URL (default http://localhost:8080).
"""

import json
import os
import sys
from pathlib import Path

import pytest
import requests

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SCENARIOS_DIR = SCRIPT_DIR / "scenarios"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_evaluation import EvaluationRunner, ScoreBreakdown, score_scenario

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SERVER_URL = os.environ.get("STICKY_NET_URL", "http://localhost:8080")
API_KEY = os.environ.get("API_KEY", "test-api-key")


def is_server_running() -> bool:
    """Check if the Sticky-Net server is reachable."""
    try:
        resp = requests.get(f"{SERVER_URL}/health", timeout=5)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


# Skip all tests if server is not running
pytestmark = pytest.mark.skipif(
    not is_server_running(),
    reason=f"Server not running at {SERVER_URL}. Start with: python -m uvicorn src.main:app --port 8080"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def runner():
    """EvaluationRunner connected to the live server."""
    return EvaluationRunner(base_url=SERVER_URL, api_key=API_KEY, use_detailed=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_scenario_files(category: str) -> list[Path]:
    cat_dir = SCENARIOS_DIR / category
    if not cat_dir.exists():
        return []
    return sorted(cat_dir.glob("*.json"))


def load_scenario(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def scenario_params(category: str):
    """Generate pytest.param for each scenario in a category."""
    files = get_scenario_files(category)
    params = []
    for f in files:
        data = load_scenario(f)
        sid = data.get("scenarioId", f.stem)
        params.append(pytest.param(data, id=sid))
    return params


# ---------------------------------------------------------------------------
# Tests by category
# ---------------------------------------------------------------------------
class TestBankFraud:
    @pytest.mark.parametrize("scenario", scenario_params("bank_fraud"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["total"] > 0, f"Zero score: {result['score']['issues']}"

    @pytest.mark.parametrize("scenario", scenario_params("bank_fraud"))
    def test_scam_detected(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["scam_detection"] == 20.0, "Scam not detected"


class TestUPIFraud:
    @pytest.mark.parametrize("scenario", scenario_params("upi_fraud"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["total"] > 0

    @pytest.mark.parametrize("scenario", scenario_params("upi_fraud"))
    def test_scam_detected(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["scam_detection"] == 20.0


class TestPhishing:
    @pytest.mark.parametrize("scenario", scenario_params("phishing"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["total"] > 0


class TestJobScam:
    @pytest.mark.parametrize("scenario", scenario_params("job_scam"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["total"] > 0


class TestLotteryScam:
    @pytest.mark.parametrize("scenario", scenario_params("lottery_scam"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["total"] > 0


class TestInvestmentScam:
    @pytest.mark.parametrize("scenario", scenario_params("investment_scam"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["total"] > 0


class TestGovernmentScam:
    @pytest.mark.parametrize("scenario", scenario_params("government_scam"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["total"] > 0


class TestDeliveryScam:
    @pytest.mark.parametrize("scenario", scenario_params("delivery_scam"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["total"] > 0


class TestRomanceScam:
    @pytest.mark.parametrize("scenario", scenario_params("romance_scam"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["total"] > 0


class TestTechSupportScam:
    @pytest.mark.parametrize("scenario", scenario_params("tech_support_scam"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["total"] > 0


class TestMixedLanguage:
    @pytest.mark.parametrize("scenario", scenario_params("mixed_language"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        assert result["score"]["total"] > 0


class TestEdgeCases:
    @pytest.mark.parametrize("scenario", scenario_params("edge_cases"))
    def test_scenario(self, runner, scenario):
        result = runner.run_scenario(scenario)
        # Edge cases may have lower scores, just check no crash
        assert "score" in result


class TestNonScam:
    @pytest.mark.parametrize("scenario", scenario_params("non_scam"))
    def test_not_detected_as_scam(self, runner, scenario):
        result = runner.run_scenario(scenario)
        # Non-scam should NOT have scamDetected=True
        assert result["score"]["scam_detection"] == 0.0, \
            f"False positive: non-scam scenario detected as scam"


class TestFullEvaluation:
    """Run all scam scenarios and check aggregate scores."""

    def test_full_run(self, runner):
        """Run all scam categories and report aggregate score."""
        all_results = []
        scam_categories = [
            "bank_fraud", "upi_fraud", "phishing", "job_scam",
            "lottery_scam", "investment_scam", "government_scam",
            "delivery_scam", "romance_scam", "tech_support_scam",
            "mixed_language", "edge_cases",
        ]

        for cat in scam_categories:
            for f in get_scenario_files(cat):
                scenario = load_scenario(f)
                try:
                    result = runner.run_scenario(scenario)
                    all_results.append(result)
                except Exception as e:
                    print(f"ERROR: {f.name}: {e}")

        if not all_results:
            pytest.skip("No scenarios executed")

        # Print summary
        from run_evaluation import print_summary_table
        print_summary_table(all_results)

        avg = sum(r["score"]["total"] for r in all_results) / len(all_results)
        print(f"\nFINAL AVERAGE: {avg:.1f}/100 across {len(all_results)} scenarios")

        # The system should score at least something
        assert avg > 0, "Average score is 0 across all scenarios"
