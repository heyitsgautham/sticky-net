#!/usr/bin/env python3
"""
GUVI Evaluation Runner for Sticky-Net

Standalone script that replicates the GUVI hackathon evaluation by:
  1. Sending multi-turn scammer messages to a running server
  2. Collecting extracted intelligence from /api/v1/analyze/detailed
  3. Scoring with GUVI's 4-dimension rubric (100 pts total)
  4. Producing a summary table and saving results to JSON

Follows the same approach as multi-turn-testing/judge_simulator.py
but uses the GUVI scoring engine from EVAL_SYS.md.

Usage:
    # First start the server:
    #   python -m uvicorn src.main:app --host 0.0.0.0 --port 8080
    # Then run:
    python simulated-testing/run_evaluation.py
    python simulated-testing/run_evaluation.py --url http://localhost:8080
    python simulated-testing/run_evaluation.py --scenario scenarios/bank_fraud/
    python simulated-testing/run_evaluation.py --category bank_fraud
"""

import argparse
import glob
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
SCENARIOS_DIR = SCRIPT_DIR / "scenarios"
RESULTS_DIR = SCRIPT_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# GUVI scoring: fakeData key → extractedIntelligence response key
FAKE_DATA_KEY_MAPPING = {
    "bankAccount": "bankAccounts",
    "upiId": "upiIds",
    "phoneNumber": "phoneNumbers",
    "phishingLink": "phishingLinks",
    "emailAddress": "emailAddresses",
}

ALL_SCAM_CATEGORIES = [
    "bank_fraud", "upi_fraud", "phishing", "job_scam", "lottery_scam",
    "investment_scam", "government_scam", "delivery_scam", "romance_scam",
    "tech_support_scam", "mixed_language", "edge_cases", "non_scam",
]


# ---------------------------------------------------------------------------
# GUVI Scoring (from EVAL_SYS.md — exact replication)
# ---------------------------------------------------------------------------
@dataclass
class ScoreBreakdown:
    """Per-scenario score breakdown matching GUVI's 4 dimensions."""
    scenario_id: str = ""
    scam_detection: float = 0.0       # /20
    intelligence_extraction: float = 0.0  # /40
    engagement_quality: float = 0.0   # /20
    response_structure: float = 0.0   # /20
    issues: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return (self.scam_detection + self.intelligence_extraction +
                self.engagement_quality + self.response_structure)

    def summary(self) -> str:
        parts = [
            f"  {self.scenario_id}: {self.total:.1f}/100",
            f"    Detection:    {self.scam_detection:.0f}/20",
            f"    Intelligence: {self.intelligence_extraction:.0f}/40",
            f"    Engagement:   {self.engagement_quality:.0f}/20",
            f"    Structure:    {self.response_structure:.0f}/20",
        ]
        if self.issues:
            parts.append("    Issues:")
            for issue in self.issues:
                parts.append(f"      - {issue}")
        return "\n".join(parts)


def score_scam_detection(final_output: dict) -> tuple[float, list[str]]:
    """20 pts if scamDetected == True."""
    issues = []
    detected = final_output.get("scamDetected", False)
    if detected is True or detected == "true" or detected == 1:
        return 20.0, issues
    issues.append(f"scamDetected={detected} (expected True)")
    return 0.0, issues


def score_intelligence(final_output: dict, fake_data: dict) -> tuple[float, list[str]]:
    """10 pts per fakeData item matched (substring), capped at 40."""
    issues = []
    if not fake_data:
        return 0.0, issues

    intel = final_output.get("extractedIntelligence", {})
    score = 0.0

    for fake_key, fake_value in fake_data.items():
        response_key = FAKE_DATA_KEY_MAPPING.get(fake_key, fake_key)
        found = False

        # Check in the mapped response key
        values = intel.get(response_key, [])
        if isinstance(values, list):
            for v in values:
                if fake_value in str(v):
                    found = True
                    break
        elif isinstance(values, str):
            if fake_value in values:
                found = True

        # Also search across ALL intel fields (broader match)
        if not found:
            for key, val in intel.items():
                if isinstance(val, list):
                    for v in val:
                        if fake_value in str(v):
                            found = True
                            break
                elif isinstance(val, str):
                    if fake_value in val:
                        found = True
                if found:
                    break

        if found:
            score += 10.0
        else:
            issues.append(f"Missing {fake_key}={fake_value} (looked in {response_key})")

    return min(score, 40.0), issues


def score_engagement(final_output: dict) -> tuple[float, list[str]]:
    """
    20 pts total:
      +5 if engagementDurationSeconds > 0
      +5 if engagementDurationSeconds > 60
      +5 if totalMessagesExchanged > 0
      +5 if totalMessagesExchanged >= 5
    """
    issues = []
    score = 0.0
    metrics = final_output.get("engagementMetrics", {})
    duration = metrics.get("engagementDurationSeconds", 0)
    messages = metrics.get("totalMessagesExchanged", 0)

    if duration > 0:
        score += 5.0
    else:
        issues.append("engagementDurationSeconds == 0")
    if duration > 60:
        score += 5.0
    else:
        issues.append(f"engagementDurationSeconds={duration} (want >60)")
    if messages > 0:
        score += 5.0
    else:
        issues.append("totalMessagesExchanged == 0")
    if messages >= 5:
        score += 5.0
    else:
        issues.append(f"totalMessagesExchanged={messages} (want >=5)")

    return score, issues


def score_structure(final_output: dict) -> tuple[float, list[str]]:
    """
    20 pts total:
      +5 if status present
      +5 if scamDetected present
      +5 if extractedIntelligence present
      +2.5 if engagementMetrics present
      +2.5 if agentNotes present
    """
    issues = []
    score = 0.0

    if "status" in final_output:
        score += 5.0
    else:
        issues.append("Missing 'status'")

    if "scamDetected" in final_output:
        score += 5.0
    else:
        issues.append("Missing 'scamDetected'")

    if "extractedIntelligence" in final_output:
        score += 5.0
    else:
        issues.append("Missing 'extractedIntelligence'")

    if "engagementMetrics" in final_output:
        score += 2.5
    else:
        issues.append("Missing 'engagementMetrics'")

    if final_output.get("agentNotes"):
        score += 2.5
    else:
        issues.append("Missing/empty 'agentNotes'")

    return score, issues


def score_scenario(final_output: dict, fake_data: dict, scenario_id: str) -> ScoreBreakdown:
    """Full 100-point scoring for one scenario."""
    bd = ScoreBreakdown(scenario_id=scenario_id)

    det, det_issues = score_scam_detection(final_output)
    bd.scam_detection = det
    bd.issues.extend(det_issues)

    intel, intel_issues = score_intelligence(final_output, fake_data)
    bd.intelligence_extraction = intel
    bd.issues.extend(intel_issues)

    eng, eng_issues = score_engagement(final_output)
    bd.engagement_quality = eng
    bd.issues.extend(eng_issues)

    struct, struct_issues = score_structure(final_output)
    bd.response_structure = struct
    bd.issues.extend(struct_issues)

    return bd


# ---------------------------------------------------------------------------
# Evaluation Runner (modeled after judge_simulator.py)
# ---------------------------------------------------------------------------
class EvaluationRunner:
    """Runs scenario evaluations against a live Sticky-Net server."""

    def __init__(self, base_url: str, api_key: str, *, use_detailed: bool = True):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        # Use /detailed endpoint for full intelligence data
        if use_detailed:
            self.endpoint = f"{self.base_url}/api/v1/analyze/detailed"
        else:
            self.endpoint = f"{self.base_url}/api/v1/analyze"
        self.use_detailed = use_detailed

    def send_message(
        self,
        message_text: str,
        conversation_history: list[dict],
        metadata: dict,
        session_id: str | None = None,
    ) -> tuple[dict, float]:
        """Send a message to the API and return (response_json, elapsed_seconds)."""
        timestamp = datetime.utcnow().isoformat() + "Z"

        request_body = {
            "message": {
                "sender": "scammer",
                "text": message_text,
                "timestamp": timestamp,
            },
            "conversationHistory": conversation_history,
            "metadata": metadata,
        }
        if session_id:
            request_body["sessionId"] = session_id

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        start = time.time()
        try:
            resp = requests.post(
                self.endpoint,
                json=request_body,
                headers=headers,
                timeout=180,
            )
            elapsed = time.time() - start

            if resp.status_code == 200:
                return resp.json(), elapsed
            else:
                return {
                    "error": True,
                    "status_code": resp.status_code,
                    "body": resp.text[:500],
                }, elapsed
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start
            return {"error": True, "exception": str(e)}, elapsed

    def run_scenario(self, scenario: dict) -> dict:
        """
        Run a single scenario.

        Supports both formats:
          - simulated-testing format: {scenarioId, scamType, turns, fakeData, metadata}
          - multi-turn-testing format: {scenario_name, scam_type, turns, expected_extractions}
        """
        # Detect format
        scenario_id = scenario.get("scenarioId") or scenario.get("scenario_name", "unknown")
        scam_type = scenario.get("scamType") or scenario.get("scam_type", "unknown")
        metadata = scenario.get("metadata", {"channel": "SMS", "language": "English", "locale": "IN"})
        fake_data = scenario.get("fakeData", {})
        turns = scenario.get("turns", [])

        # If no explicit turns, build from initialMessage + fakeData
        if not turns and "initialMessage" in scenario:
            turns = self._build_turns(scenario)

        print(f"\n{'='*60}")
        print(f"SCENARIO: {scenario_id}")
        print(f"Type: {scam_type} | Turns: {len(turns)}")
        print(f"{'='*60}")

        conversation_history: list[dict] = []
        cumulative_intel: dict[str, list] = {}
        all_turn_results: list[dict] = []
        last_response: dict = {}
        total_elapsed = 0.0
        session_id = None  # Let server generate, or reuse

        for turn_data in turns:
            turn_num = turn_data.get("turn", len(all_turn_results) + 1)
            scammer_msg = turn_data.get("scammer_message", "")
            if not scammer_msg:
                continue

            print(f"\n--- Turn {turn_num} ---")
            print(f"SCAMMER: {scammer_msg[:80]}{'...' if len(scammer_msg) > 80 else ''}")

            response, elapsed = self.send_message(
                scammer_msg, conversation_history, metadata, session_id
            )
            total_elapsed += elapsed

            turn_result = {
                "turn": turn_num,
                "scammer_message": scammer_msg,
                "response_time_seconds": round(elapsed, 3),
                "api_response": response,
            }

            if response.get("error"):
                print(f"  ERROR: {response}")
                all_turn_results.append(turn_result)
                continue

            last_response = response

            # Extract fields from response
            if self.use_detailed:
                agent_reply = response.get("agentResponse", "")
                scam_detected = response.get("scamDetected", False)
                confidence = response.get("confidence", 0)
                extracted_intel = response.get("extractedIntelligence", {})
            else:
                agent_reply = response.get("reply", "")
                scam_detected = "N/A"
                confidence = "N/A"
                extracted_intel = {}

            print(f"AGENT: {agent_reply[:80]}{'...' if len(str(agent_reply)) > 80 else ''}")
            print(f"[Scam: {scam_detected} | Conf: {confidence} | Time: {elapsed:.2f}s]")

            # Accumulate intelligence across turns
            for key, values in extracted_intel.items():
                if isinstance(values, list) and values:
                    if key not in cumulative_intel:
                        cumulative_intel[key] = []
                    for v in values:
                        if v and str(v) not in [str(x) for x in cumulative_intel[key]]:
                            cumulative_intel[key].append(v)

            # Validate expected_extractions (multi-turn-testing format)
            expected = turn_data.get("expected_extractions", [])
            if expected:
                matched, missed = self._validate_extractions(expected, cumulative_intel)
                if missed:
                    print(f"  ✗ Missing: {missed}")
                else:
                    print(f"  ✓ All {len(matched)} expected extractions found")

            all_turn_results.append(turn_result)

            # Update conversation history
            conversation_history.append({
                "sender": "scammer",
                "text": scammer_msg,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
            conversation_history.append({
                "sender": "user",
                "text": str(agent_reply),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

        # Build final output for GUVI scoring
        final_output = self._build_final_output(
            last_response, cumulative_intel, conversation_history, total_elapsed
        )

        # Score with GUVI rubric
        breakdown = score_scenario(final_output, fake_data, scenario_id)

        print(f"\n  SCORE: {breakdown.total:.1f}/100  "
              f"(D:{breakdown.scam_detection:.0f} "
              f"I:{breakdown.intelligence_extraction:.0f} "
              f"E:{breakdown.engagement_quality:.0f} "
              f"S:{breakdown.response_structure:.0f})")
        if breakdown.issues:
            print(f"  Issues: {len(breakdown.issues)}")
            for issue in breakdown.issues[:5]:
                print(f"    - {issue}")

        return {
            "scenario_id": scenario_id,
            "scam_type": scam_type,
            "fake_data": fake_data,
            "total_turns": len(all_turn_results),
            "turns": all_turn_results,
            "cumulative_intelligence": cumulative_intel,
            "final_output": final_output,
            "score": {
                "total": breakdown.total,
                "scam_detection": breakdown.scam_detection,
                "intelligence_extraction": breakdown.intelligence_extraction,
                "engagement_quality": breakdown.engagement_quality,
                "response_structure": breakdown.response_structure,
                "issues": breakdown.issues,
            },
            "total_duration_seconds": round(total_elapsed, 3),
        }

    def _build_final_output(
        self,
        last_response: dict,
        cumulative_intel: dict,
        history: list[dict],
        duration: float,
    ) -> dict:
        """Build the final_output dict for GUVI scoring."""
        return {
            "status": last_response.get("status", "success"),
            "scamDetected": last_response.get("scamDetected", False),
            "extractedIntelligence": cumulative_intel,
            "engagementMetrics": {
                "engagementDurationSeconds": max(int(duration), 1),
                "totalMessagesExchanged": len(history),
            },
            "agentNotes": last_response.get("agentNotes", ""),
        }

    def _validate_extractions(
        self, expected: list[str], actual_intel: dict
    ) -> tuple[list[str], list[str]]:
        """Validate expected values against cumulative intelligence (like judge_simulator)."""
        actual_flat = set()
        for key, values in actual_intel.items():
            if isinstance(values, list):
                for v in values:
                    if v:
                        actual_flat.add(str(v).lower().strip())

        matched, missed = [], []
        for item in expected:
            item_lower = item.lower().strip()
            item_digits = re.sub(r"\D", "", item_lower)
            found = False
            for actual in actual_flat:
                actual_digits = re.sub(r"\D", "", actual)
                if (item_lower in actual or actual in item_lower or
                        (item_digits and len(item_digits) >= 9 and item_digits == actual_digits)):
                    found = True
                    break
            if found:
                matched.append(item)
            else:
                missed.append(item)

        return matched, missed

    def _build_turns(self, scenario: dict) -> list[dict]:
        """Build turns from initialMessage + fakeData follow-ups."""
        turns = [{"turn": 1, "scammer_message": scenario["initialMessage"]}]
        fake_data = scenario.get("fakeData", {})

        bank = fake_data.get("bankAccount", "")
        upi = fake_data.get("upiId", "")
        phone = fake_data.get("phoneNumber", "")
        link = fake_data.get("phishingLink", "")
        email = fake_data.get("emailAddress", "")

        if phone:
            turns.append({"turn": 2, "scammer_message":
                f"Sir/Madam, I am calling from the official department. "
                f"You can verify by calling me at {phone}. Please hurry."})
        else:
            turns.append({"turn": 2, "scammer_message":
                "Sir/Madam, this is very urgent. Please cooperate immediately."})

        if upi and bank:
            turns.append({"turn": 3, "scammer_message":
                f"Your account {bank} has a problem. "
                f"Please send Rs 1 to {upi} for verification."})
        elif upi:
            turns.append({"turn": 3, "scammer_message":
                f"To verify, please send Rs 1 to our official UPI: {upi}."})
        elif link:
            turns.append({"turn": 3, "scammer_message":
                f"Please click this link to proceed: {link}."})
        else:
            turns.append({"turn": 3, "scammer_message":
                "Please share your details immediately for verification."})

        parts = []
        if bank and bank not in str(turns):
            parts.append(f"Your account {bank} needs immediate action")
        if email:
            parts.append(f"email us at {email}")
        if link and link not in str(turns):
            parts.append(f"visit {link}")
        if upi and upi not in str(turns):
            parts.append(f"our UPI is {upi}")
        if phone and phone not in str(turns):
            parts.append(f"call us at {phone}")
        if parts:
            turns.append({"turn": 4, "scammer_message": ". ".join(parts) + ". Act NOW!"})

        turns.append({"turn": len(turns) + 1, "scammer_message":
            "FINAL WARNING. If you do not comply within 5 minutes, "
            "we will take strict action."})

        return turns


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
def print_summary_table(all_results: list[dict]):
    """Print a GUVI-style summary table."""
    print("\n" + "=" * 100)
    print("GUVI EVALUATION SUMMARY")
    print("=" * 100)
    header = (
        f"{'Scenario':<38} {'Score':>6} {'Det':>4} {'Intel':>5} "
        f"{'Eng':>4} {'Str':>4} {'Issues':>6} {'Time':>7}"
    )
    print(header)
    print("-" * 100)

    for r in all_results:
        s = r["score"]
        name = r["scenario_id"][:36]
        row = (
            f"{name:<38} "
            f"{s['total']:5.1f} "
            f"{s['scam_detection']:4.0f} "
            f"{s['intelligence_extraction']:5.0f} "
            f"{s['engagement_quality']:4.0f} "
            f"{s['response_structure']:4.0f} "
            f"{len(s['issues']):5d} "
            f"{r['total_duration_seconds']:6.1f}s"
        )
        print(row)

    print("-" * 100)
    n = len(all_results)
    if n > 0:
        avg_total = sum(r["score"]["total"] for r in all_results) / n
        avg_det = sum(r["score"]["scam_detection"] for r in all_results) / n
        avg_intel = sum(r["score"]["intelligence_extraction"] for r in all_results) / n
        avg_eng = sum(r["score"]["engagement_quality"] for r in all_results) / n
        avg_str = sum(r["score"]["response_structure"] for r in all_results) / n
        total_time = sum(r["total_duration_seconds"] for r in all_results)
        print(
            f"{'AVERAGE (' + str(n) + ' scenarios)':<38} "
            f"{avg_total:5.1f} "
            f"{avg_det:4.0f} "
            f"{avg_intel:5.0f} "
            f"{avg_eng:4.0f} "
            f"{avg_str:4.0f} "
            f"{'':>6} "
            f"{total_time:6.1f}s"
        )

        # Category breakdown
        categories: dict[str, list[float]] = {}
        for r in all_results:
            cat = r["scam_type"]
            categories.setdefault(cat, []).append(r["score"]["total"])

        print(f"\nCATEGORY BREAKDOWN:")
        for cat, scores in sorted(categories.items()):
            avg = sum(scores) / len(scores)
            print(f"  {cat:<30} {avg:5.1f}/100  ({len(scores)} scenarios)")

    print("=" * 100)


def save_results(all_results: list[dict], results_dir: Path) -> str:
    """Save results to timestamped JSON file."""
    results_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = results_dir / f"eval_{ts}.json"

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_scenarios": len(all_results),
        "average_score": (
            sum(r["score"]["total"] for r in all_results) / max(len(all_results), 1)
        ),
        "scenarios": all_results,
    }

    with open(filepath, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    return str(filepath)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def load_scenarios(path: Path) -> list[tuple[str, dict]]:
    """Load scenario JSON files from a path (file or directory, recursive)."""
    scenarios = []
    if path.is_file():
        with open(path) as f:
            scenarios.append((str(path), json.load(f)))
    elif path.is_dir():
        for json_file in sorted(path.rglob("*.json")):
            try:
                with open(json_file) as f:
                    scenarios.append((str(json_file), json.load(f)))
            except json.JSONDecodeError as e:
                print(f"WARNING: {json_file}: {e}")
    return scenarios


def main():
    parser = argparse.ArgumentParser(
        description="GUVI Evaluation Runner for Sticky-Net",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python simulated-testing/run_evaluation.py
    python simulated-testing/run_evaluation.py --url http://localhost:8080
    python simulated-testing/run_evaluation.py --category bank_fraud
    python simulated-testing/run_evaluation.py --scenario scenarios/bank_fraud/sbi_otp.json
    python simulated-testing/run_evaluation.py --all
        """,
    )
    parser.add_argument("--url", default="http://localhost:8080",
                        help="Base URL of the running server (default: http://localhost:8080)")
    parser.add_argument("--api-key", default="test-api-key",
                        help="API key (default: test-api-key)")
    parser.add_argument("--scenario", default=None,
                        help="Path to a specific scenario file or directory")
    parser.add_argument("--category", default=None,
                        help="Run all scenarios in a category (e.g., bank_fraud)")
    parser.add_argument("--all", action="store_true",
                        help="Run ALL scenarios across all categories")
    parser.add_argument("--basic", action="store_true",
                        help="Use /api/v1/analyze (basic) instead of /detailed")
    parser.add_argument("--save", action="store_true", default=True,
                        help="Save results to JSON (default: True)")

    args = parser.parse_args()

    runner = EvaluationRunner(
        base_url=args.url,
        api_key=args.api_key,
        use_detailed=not args.basic,
    )

    # Determine which scenarios to load
    if args.scenario:
        scenario_path = Path(args.scenario)
        if not scenario_path.exists() and not scenario_path.is_absolute():
            # Try relative to script dir
            scenario_path = SCRIPT_DIR / args.scenario
        if not scenario_path.exists():
            # Also try relative to CWD
            scenario_path = Path.cwd() / args.scenario
        scenarios = load_scenarios(scenario_path)
    elif args.category:
        cat_dir = SCENARIOS_DIR / args.category
        if not cat_dir.exists():
            print(f"ERROR: Category directory not found: {cat_dir}")
            sys.exit(1)
        scenarios = load_scenarios(cat_dir)
    elif args.all:
        scenarios = load_scenarios(SCENARIOS_DIR)
    else:
        # Default: run just bank_fraud + upi_fraud + phishing (primary categories)
        scenarios = []
        for cat in ["bank_fraud", "upi_fraud", "phishing"]:
            cat_dir = SCENARIOS_DIR / cat
            if cat_dir.exists():
                scenarios.extend(load_scenarios(cat_dir))

    if not scenarios:
        print("No scenarios found! Check the scenarios/ directory.")
        sys.exit(1)

    print(f"\nGUVI Evaluation Runner — Sticky-Net")
    print(f"Endpoint: {runner.endpoint}")
    print(f"Scenarios: {len(scenarios)}")
    print(f"{'='*60}")

    all_results = []
    for path, scenario in scenarios:
        try:
            result = runner.run_scenario(scenario)
            all_results.append(result)
        except Exception as e:
            print(f"\nERROR running {path}: {e}")
            import traceback
            traceback.print_exc()

    # Print summary
    if all_results:
        print_summary_table(all_results)

        if args.save:
            filepath = save_results(all_results, RESULTS_DIR)
            print(f"\nResults saved to: {filepath}")


if __name__ == "__main__":
    main()
