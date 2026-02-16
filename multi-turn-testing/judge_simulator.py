#!/usr/bin/env python3
"""
Judge Simulator for Sticky-Net Honeypot API

Simulates how hackathon judges will test the API with scripted multi-turn scenarios.
Validates intelligence extraction and logs results for analysis.

Usage:
    python judge_simulator.py --url http://localhost:8080
    python judge_simulator.py --scenario scenarios/01_banking_kyc_fraud.json
    python judge_simulator.py --api-key my-secret-key
"""

import argparse
import glob
import json
import os
import time
from datetime import datetime
from typing import Any

import requests


class JudgeSimulator:
    """Simulates judge testing of the Sticky-Net API with scripted scenarios."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.endpoint = f"{self.base_url}/api/v1/analyze"
        self.logs_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(self.logs_dir, exist_ok=True)

    def load_scenario(self, scenario_path: str) -> dict:
        """Load a scenario from a JSON file."""
        with open(scenario_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_all_scenarios(self, scenarios_dir: str) -> list[tuple[str, dict]]:
        """Load all scenario files from the scenarios directory."""
        pattern = os.path.join(scenarios_dir, "*.json")
        scenario_files = sorted(glob.glob(pattern))
        scenarios = []
        for path in scenario_files:
            try:
                scenario = self.load_scenario(path)
                scenarios.append((path, scenario))
            except json.JSONDecodeError as e:
                print(f"WARNING: Failed to parse {path}: {e}")
        return scenarios

    def send_message(
        self,
        message_text: str,
        conversation_history: list[dict],
        metadata: dict,
    ) -> tuple[dict, float]:
        """Send a message to the API and return response with timing."""
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

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        start_time = time.time()
        try:
            response = requests.post(
                self.endpoint,
                json=request_body,
                headers=headers,
                timeout=180,  # Allow time for Gemini retries (90s x 2 + buffer)
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                return response.json(), elapsed
            else:
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "body": response.text,
                }, elapsed

        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start_time
            return {"error": True, "exception": str(e)}, elapsed

    def flatten_intelligence(self, extracted_intel: dict) -> set[str]:
        """Flatten all extracted intelligence values into a set for comparison."""
        all_values = set()

        # Standard fields
        fields = [
            "bankAccounts",
            "upiIds",
            "phoneNumbers",
            "phishingLinks",
            "emails",
            "beneficiaryNames",
            "bankNames",
            "ifscCodes",
            "whatsappNumbers",
        ]

        for field in fields:
            values = extracted_intel.get(field, [])
            if isinstance(values, list):
                for v in values:
                    if v:
                        all_values.add(str(v).lower().strip())

        # Handle other_critical_info (list of dicts with "label" and "value")
        other_info = extracted_intel.get("other_critical_info", [])
        if isinstance(other_info, list):
            for item in other_info:
                if isinstance(item, dict) and "value" in item:
                    all_values.add(str(item["value"]).lower().strip())
                elif isinstance(item, str):
                    all_values.add(item.lower().strip())

        return all_values

    def normalize_for_comparison(self, value: str) -> str:
        """Normalize a value for fuzzy comparison by removing special characters."""
        import re
        # Remove common special characters but keep alphanumeric and basic punctuation
        normalized = value.lower().strip()
        # For phone numbers and bank accounts: extract just digits
        digits_only = re.sub(r'\D', '', normalized)
        # If it looks like a phone number (10-12 digits) or bank account (9-18 digits)
        if 9 <= len(digits_only) <= 18:
            # Return digits only for numeric identifiers
            return digits_only
        # For names: replace dots, hyphens with spaces and normalize
        normalized = re.sub(r'[.\-_]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def validate_extractions(
        self,
        expected: list[str],
        actual_intel: dict,
    ) -> tuple[list[str], list[str]]:
        """
        Validate expected extractions against actual.
        Returns (matched, missed) lists.
        """
        actual_flat = self.flatten_intelligence(actual_intel)
        matched = []
        missed = []

        for expected_item in expected:
            expected_lower = expected_item.lower().strip()
            expected_normalized = self.normalize_for_comparison(expected_item)
            found = False

            # Check for exact match, partial match, or normalized match
            for actual_item in actual_flat:
                actual_normalized = self.normalize_for_comparison(actual_item)
                # Check various matching strategies
                if (expected_lower in actual_item or 
                    actual_item in expected_lower or
                    expected_normalized == actual_normalized or
                    expected_normalized in actual_normalized or
                    actual_normalized in expected_normalized):
                    found = True
                    break

            if found:
                matched.append(expected_item)
            else:
                missed.append(expected_item)

        return matched, missed

    def run_scenario(self, scenario: dict) -> dict:
        """Run a single scenario and return results."""
        scenario_name = scenario.get("scenario_name", "Unknown")
        metadata = scenario.get("metadata", {"channel": "SMS", "language": "English", "locale": "IN"})
        turns = scenario.get("turns", [])

        results = {
            "scenario_name": scenario_name,
            "scam_type": scenario.get("scam_type", "unknown"),
            "difficulty": scenario.get("difficulty", "unknown"),
            "description": scenario.get("description", ""),
            "total_turns": len(turns),
            "turns": [],
            "summary": {
                "total_expected": 0,
                "total_matched": 0,
                "total_missed": 0,
                "passed_turns": 0,
                "failed_turns": 0,
                "total_intel_extracted": 0,
            },
            "started_at": datetime.utcnow().isoformat() + "Z",
            "ended_at": None,
            "total_duration_seconds": 0,
        }

        conversation_history = []
        cumulative_intel = {}  # Track all intel extracted so far

        print(f"\n{'='*60}")
        print(f"SCENARIO: {scenario_name}")
        print(f"Type: {scenario.get('scam_type', 'unknown')} | Difficulty: {scenario.get('difficulty', 'unknown')}")
        print(f"{'='*60}")

        for turn_data in turns:
            turn_num = turn_data.get("turn", 0)
            scammer_message = turn_data.get("scammer_message", "")
            expected_extractions = turn_data.get("expected_extractions", [])

            print(f"\n--- Turn {turn_num} ---")
            print(f"SCAMMER: {scammer_message[:80]}{'...' if len(scammer_message) > 80 else ''}")

            # Send message to API
            response, elapsed = self.send_message(scammer_message, conversation_history, metadata)

            turn_result = {
                "turn": turn_num,
                "scammer_message": scammer_message,
                "expected_extractions": expected_extractions,
                "response_time_seconds": round(elapsed, 3),
                "api_response": response,
                "validation": {},
            }

            if response.get("error"):
                print(f"ERROR: API request failed - {response}")
                turn_result["validation"] = {
                    "status": "error",
                    "matched": [],
                    "missed": expected_extractions,
                }
                results["summary"]["total_missed"] += len(expected_extractions)
                results["summary"]["failed_turns"] += 1
            else:
                agent_response = response.get("agentResponse") or "[No response from agent]"
                scam_detected = response.get("scamDetected", False)
                confidence = response.get("confidence", 0)
                extracted_intel = response.get("extractedIntelligence", {})

                print(f"AGENT: {agent_response[:80]}{'...' if len(agent_response) > 80 else ''}")
                print(f"[Scam: {scam_detected} | Conf: {confidence:.2f} | Time: {elapsed:.2f}s]")

                # Merge with cumulative intel
                for key, values in extracted_intel.items():
                    if isinstance(values, list):
                        if key not in cumulative_intel:
                            cumulative_intel[key] = []
                        cumulative_intel[key].extend(values)

                # Validate against cumulative intel (intelligence builds up over turns)
                matched, missed = self.validate_extractions(expected_extractions, cumulative_intel)

                validation_status = "pass" if len(missed) == 0 else "fail"
                turn_result["validation"] = {
                    "status": validation_status,
                    "matched": matched,
                    "missed": missed,
                }

                results["summary"]["total_expected"] += len(expected_extractions)
                results["summary"]["total_matched"] += len(matched)
                results["summary"]["total_missed"] += len(missed)

                if validation_status == "pass":
                    results["summary"]["passed_turns"] += 1
                    print(f"✓ Validation PASSED ({len(matched)}/{len(expected_extractions)} extractions)")
                else:
                    results["summary"]["failed_turns"] += 1
                    print(f"✗ Validation FAILED - Missing: {missed}")

                # Update conversation history
                scammer_timestamp = datetime.utcnow().isoformat() + "Z"
                agent_timestamp = datetime.utcnow().isoformat() + "Z"

                conversation_history.append({
                    "sender": "scammer",
                    "text": scammer_message,
                    "timestamp": scammer_timestamp,
                })
                conversation_history.append({
                    "sender": "user",
                    "text": agent_response,
                    "timestamp": agent_timestamp,
                })

            results["turns"].append(turn_result)

        # Final summary
        results["ended_at"] = datetime.utcnow().isoformat() + "Z"
        results["summary"]["total_intel_extracted"] = len(self.flatten_intelligence(cumulative_intel))
        results["total_duration_seconds"] = sum(t["response_time_seconds"] for t in results["turns"])

        return results

    def save_log(self, scenario_name: str, results: dict) -> str:
        """Save detailed log to JSON file."""
        # Clean scenario name for filename
        clean_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in scenario_name)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{clean_name}_{timestamp}.json"
        filepath = os.path.join(self.logs_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return filepath

    def print_summary_table(self, all_results: list[dict]):
        """Print a summary table of all scenario results."""
        print("\n" + "=" * 90)
        print("SUMMARY")
        print("=" * 90)

        # Header
        header = f"{'Scenario':<35} {'Turns':>6} {'Pass':>6} {'Fail':>6} {'Intel':>7} {'Verdict':>10}"
        print(header)
        print("-" * 90)

        total_scenarios = len(all_results)
        passed_scenarios = 0
        total_turns = 0
        total_passed = 0
        total_failed = 0

        for result in all_results:
            name = result["scenario_name"][:33]
            turns = result["total_turns"]
            passed = result["summary"]["passed_turns"]
            failed = result["summary"]["failed_turns"]
            intel = result["summary"]["total_intel_extracted"]

            # Verdict logic: PASS if no failed turns with expected extractions
            # A turn with no expected extractions always passes
            if failed == 0:
                verdict = "PASS"
                passed_scenarios += 1
            else:
                verdict = "FAIL"

            row = f"{name:<35} {turns:>6} {passed:>6} {failed:>6} {intel:>7} {verdict:>10}"
            print(row)

            total_turns += turns
            total_passed += passed
            total_failed += failed

        print("-" * 90)
        print(f"{'TOTAL':<35} {total_turns:>6} {total_passed:>6} {total_failed:>6}")
        print(f"\nScenarios: {passed_scenarios}/{total_scenarios} PASSED")
        print("=" * 90)

    def run(self, scenario_path: str | None = None):
        """Run the simulator on one or all scenarios."""
        scenarios_dir = os.path.join(os.path.dirname(__file__), "scenarios")

        if scenario_path:
            # Make path absolute if relative
            if not os.path.isabs(scenario_path):
                scenario_path = os.path.join(os.path.dirname(__file__), scenario_path)
            
            # Check if it's a directory or file
            if os.path.isdir(scenario_path):
                # Run all scenarios in the directory
                scenarios = self.load_all_scenarios(scenario_path)
            else:
                # Run single scenario file
                scenarios = [(scenario_path, self.load_scenario(scenario_path))]
        else:
            # Run all scenarios from default directory
            scenarios = self.load_all_scenarios(scenarios_dir)

        if not scenarios:
            print("No scenarios found!")
            return

        print(f"\nJudge Simulator - Sticky-Net API Testing")
        print(f"API Endpoint: {self.endpoint}")
        print(f"Scenarios to run: {len(scenarios)}")

        all_results = []

        for path, scenario in scenarios:
            try:
                results = self.run_scenario(scenario)
                log_path = self.save_log(scenario.get("scenario_name", "unknown"), results)
                results["log_file"] = log_path
                all_results.append(results)
                print(f"\nLog saved: {log_path}")
            except Exception as e:
                print(f"\nERROR running scenario {path}: {e}")
                import traceback
                traceback.print_exc()

        # Print summary
        if all_results:
            self.print_summary_table(all_results)


def main():
    parser = argparse.ArgumentParser(
        description="Judge Simulator for Sticky-Net Honeypot API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python judge_simulator.py
    python judge_simulator.py --url http://localhost:8080
    python judge_simulator.py --scenario scenarios/01_banking_kyc_fraud.json
    python judge_simulator.py --api-key my-secret-key
        """,
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Base URL of the Sticky-Net API (default: http://localhost:8080)",
    )

    parser.add_argument(
        "--api-key",
        default="test-api-key",
        help="API key for authentication (default: test-api-key)",
    )

    parser.add_argument(
        "--scenario",
        default=None,
        help="Path to a specific scenario file (optional, runs all if not specified)",
    )

    args = parser.parse_args()

    simulator = JudgeSimulator(base_url=args.url, api_key=args.api_key)
    simulator.run(scenario_path=args.scenario)


if __name__ == "__main__":
    main()
