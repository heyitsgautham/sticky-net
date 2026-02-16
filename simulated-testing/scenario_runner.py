"""
Scenario Runner — orchestrates ScammerSimulator + GUVI scoring.

Runs a full scenario end-to-end:
  1. Drives multi-turn conversation via ScammerSimulator
  2. Builds a final_output dict matching GUVI callback format
  3. Scores using guvi_scoring_engine
  4. Returns ScenarioResult with full breakdown
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from starlette.testclient import TestClient

from guvi_scoring_engine import ScoreBreakdown, score_scenario
from scammer_simulator import ConversationResult, ScammerSimulator


@dataclass
class ScenarioResult:
    """Complete result of a single scenario evaluation."""

    scenario_id: str
    scenario_name: str
    scam_type: str
    weight: float
    score: ScoreBreakdown
    conversation: ConversationResult
    final_output: dict = field(default_factory=dict)
    expected_min_score: float = 0.0
    expected_max_score: float = 100.0

    @property
    def passed(self) -> bool:
        return self.score.total >= self.expected_min_score

    def summary_line(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] {self.scenario_id:<40} "
            f"Score: {self.score.total:5.1f}/100  "
            f"(D:{self.score.scam_detection:.0f} "
            f"I:{self.score.intelligence_extraction:.0f} "
            f"E:{self.score.engagement_quality:.0f} "
            f"S:{self.score.response_structure:.0f})"
        )


class ScenarioRunner:
    """Runs scenarios against the API and scores them."""

    def __init__(
        self,
        client: TestClient,
        headers: dict[str, str],
        *,
        inter_turn_delay: float = 0.0,
    ):
        self.client = client
        self.headers = headers
        self.simulator = ScammerSimulator(
            client, headers, inter_turn_delay=inter_turn_delay
        )

    def run_scenario(self, scenario: dict) -> ScenarioResult:
        """Run a single scenario and return scored result."""
        scenario_id = scenario.get("scenarioId", "unknown")
        fake_data = scenario.get("fakeData", {})

        # Run conversation
        convo = self.simulator.run_scenario(scenario)

        # Build final_output matching GUVI callback format
        final_output = self._build_final_output(convo, scenario)

        # Score it
        breakdown = score_scenario(final_output, fake_data, scenario_id)

        # Expected scores
        expected = scenario.get("expected_score", {})

        return ScenarioResult(
            scenario_id=scenario_id,
            scenario_name=scenario.get("name", ""),
            scam_type=scenario.get("scamType", ""),
            weight=scenario.get("weight", 10),
            score=breakdown,
            conversation=convo,
            final_output=final_output,
            expected_min_score=expected.get("min", 0),
            expected_max_score=expected.get("max", 100),
        )

    def run_scenario_file(self, file_path: str | Path) -> ScenarioResult:
        """Load scenario from JSON file and run it."""
        with open(file_path) as f:
            scenario = json.load(f)
        return self.run_scenario(scenario)

    def run_all_in_directory(
        self, directory: str | Path
    ) -> list[ScenarioResult]:
        """Run all JSON scenarios in a directory (recursively)."""
        results = []
        dir_path = Path(directory)
        for json_file in sorted(dir_path.rglob("*.json")):
            try:
                result = self.run_scenario_file(json_file)
                results.append(result)
            except Exception as e:
                print(f"ERROR loading {json_file}: {e}")
        return results

    def _build_final_output(
        self, convo: ConversationResult, scenario: dict
    ) -> dict:
        """
        Build a final_output dict matching GUVI's expected format.

        Uses the /api/v1/analyze/detailed endpoint on the last turn
        to get full intelligence extraction, or falls back to accumulating
        from the session state.
        """
        # Send the last scammer message to the detailed endpoint for full intel
        turns = scenario.get("turns", [])
        if not turns and "initialMessage" in scenario:
            turns = self.simulator._build_turns_from_scenario(scenario)

        # Use the detailed endpoint with the full conversation history
        # to get the complete extracted intelligence
        if turns:
            last_turn = turns[-1]
            metadata = scenario.get("metadata", {
                "channel": "SMS",
                "language": "English",
                "locale": "IN",
            })

            request_body = {
                "sessionId": convo.session_id,
                "message": {
                    "sender": "scammer",
                    "text": last_turn.get("scammer_message", "Please respond."),
                    "timestamp": "2026-01-21T10:30:00Z",
                },
                "conversationHistory": convo.conversation_history,
                "metadata": metadata,
            }

            try:
                resp = self.client.post(
                    "/api/v1/analyze/detailed",
                    json=request_body,
                    headers=self.headers,
                    timeout=30,
                )
                if resp.status_code == 200:
                    detailed = resp.json()
                    return self._detailed_to_final_output(
                        detailed, convo, scenario
                    )
            except Exception:
                pass  # Fall through to best-effort

        # Fallback: build from conversation data alone
        return self._fallback_final_output(convo, scenario)

    def _detailed_to_final_output(
        self, detailed: dict, convo: ConversationResult, scenario: dict
    ) -> dict:
        """Convert detailed endpoint response to GUVI final_output format."""
        extracted = detailed.get("extractedIntelligence", {})

        # Map schema fields to callback fields
        callback_intel = {
            "bankAccounts": extracted.get("bankAccounts", []),
            "upiIds": extracted.get("upiIds", []),
            "phoneNumbers": extracted.get("phoneNumbers", []),
            "phishingLinks": extracted.get("phishingLinks", []),
            "emailAddresses": extracted.get("emails", []),
            "suspiciousKeywords": extracted.get("suspiciousKeywords", []),
        }

        return {
            "sessionId": convo.session_id,
            "status": detailed.get("status", "success"),
            "scamDetected": detailed.get("scamDetected", False),
            "totalMessagesExchanged": convo.total_messages + 2,
            "extractedIntelligence": callback_intel,
            "engagementMetrics": {
                "engagementDurationSeconds": max(int(convo.duration_seconds), 1),
                "totalMessagesExchanged": convo.total_messages + 2,
            },
            "agentNotes": detailed.get("agentNotes", ""),
        }

    def _fallback_final_output(
        self, convo: ConversationResult, scenario: dict
    ) -> dict:
        """Build final_output from conversation result without detailed endpoint."""
        return {
            "sessionId": convo.session_id,
            "status": "success",
            "scamDetected": len(convo.replies) > 0,
            "totalMessagesExchanged": convo.total_messages,
            "extractedIntelligence": {
                "bankAccounts": [],
                "upiIds": [],
                "phoneNumbers": [],
                "phishingLinks": [],
                "emailAddresses": [],
            },
            "engagementMetrics": {
                "engagementDurationSeconds": max(int(convo.duration_seconds), 1),
                "totalMessagesExchanged": convo.total_messages,
            },
            "agentNotes": "",
        }


def load_scenario(file_path: str | Path) -> dict:
    """Load a scenario JSON file."""
    with open(file_path) as f:
        return json.load(f)


def load_all_scenarios(directory: str | Path) -> list[dict]:
    """Load all scenario JSON files from a directory (recursively)."""
    scenarios = []
    dir_path = Path(directory)
    for json_file in sorted(dir_path.rglob("*.json")):
        with open(json_file) as f:
            scenarios.append(json.load(f))
    return scenarios


def print_results_table(results: list[ScenarioResult]) -> None:
    """Print a summary table of all scenario results."""
    print("\n" + "=" * 90)
    print("GUVI EVALUATION RESULTS")
    print("=" * 90)
    print(
        f"{'Scenario':<40} {'Score':>6} {'Det':>4} {'Int':>4} "
        f"{'Eng':>4} {'Str':>4} {'Status':>6}"
    )
    print("-" * 90)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(
            f"{r.scenario_id:<40} "
            f"{r.score.total:5.1f} "
            f"{r.score.scam_detection:4.0f} "
            f"{r.score.intelligence_extraction:4.0f} "
            f"{r.score.engagement_quality:4.0f} "
            f"{r.score.response_structure:4.0f} "
            f"  {status}"
        )

    print("-" * 90)
    avg = sum(r.score.total for r in results) / max(len(results), 1)
    passed = sum(1 for r in results if r.passed)
    print(
        f"{'AVERAGE':<40} {avg:5.1f}    "
        f"Passed: {passed}/{len(results)}"
    )
    print("=" * 90)
