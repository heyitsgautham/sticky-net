#!/usr/bin/env python3
"""
Standalone evaluation runner that writes full logs to files.
Run: .venv/bin/python eval_framework/run_full_eval.py
"""
import asyncio
import json
import sys
import os
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval_framework.runner import EvalRunner
from eval_framework.scenarios import get_scenario_suite

LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

API_URL = os.environ.get("EVAL_API_URL", "http://localhost:8080")
API_KEY = os.environ.get("EVAL_API_KEY", "test-api-key")


async def main():
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"eval_full_{timestamp}.log"
    json_file = LOGS_DIR / f"eval_report_{timestamp}.json"

    # Open log file for writing
    with open(log_file, "w") as lf:
        def log(msg: str = ""):
            print(msg, flush=True)
            lf.write(msg + "\n")
            lf.flush()

        log(f"={'='*70}")
        log(f"  STICKY-NET FULL EVALUATION RUN")
        log(f"  Time: {datetime.utcnow().isoformat()}Z")
        log(f"  API: {API_URL}")
        log(f"  Suite: extended (5 scenarios)")
        log(f"={'='*70}\n")

        runner = EvalRunner(base_url=API_URL, api_key=API_KEY, timeout=30.0)
        scenarios, weights = get_scenario_suite("extended")

        all_scenario_results = []
        all_turns_log = []

        for scenario, weight in zip(scenarios, weights):
            scenario_id = scenario["scenarioId"]
            scenario_name = scenario["name"]
            scam_type = scenario["scamType"]
            fake_data = scenario["fakeData"]
            turns_config = scenario.get("turns", [])
            metadata = scenario.get("metadata", {"channel": "SMS", "language": "English", "locale": "IN"})

            log(f"\n{'#'*70}")
            log(f"  SCENARIO: {scenario_name}")
            log(f"  ID: {scenario_id} | Type: {scam_type} | Weight: {weight*100:.0f}%")
            log(f"  Fake Data: {json.dumps(fake_data, indent=2)}")
            log(f"  Max Turns: {len(turns_config)}")
            log(f"{'#'*70}")

            # Run through the runner
            scenario_with_weight = {**scenario, "weight": int(weight * 100)}
            start = time.monotonic()
            try:
                result = await runner.run_scenario(scenario_with_weight, use_detailed=False, verbose=False)
            except Exception as e:
                log(f"\n  *** ERROR running scenario: {e}")
                continue
            elapsed = time.monotonic() - start

            # Log every turn in full
            for turn in result.turns:
                log(f"\n  --- Turn {turn.turn_number} ---")
                log(f"  SCAMMER MESSAGE:")
                log(f"    {turn.scammer_message}")
                log(f"  AGENT RESPONSE:")
                log(f"    {turn.agent_response}")
                log(f"  Response Time: {turn.response_time_seconds:.2f}s")
                if turn.expected_extractions:
                    log(f"  Expected Extractions: {turn.expected_extractions}")
                if turn.error:
                    log(f"  *** ERROR: {turn.error}")

                all_turns_log.append({
                    "scenario": scenario_id,
                    "turn": turn.turn_number,
                    "scammerMessage": turn.scammer_message,
                    "agentResponse": turn.agent_response,
                    "responseTime": turn.response_time_seconds,
                    "expectedExtractions": turn.expected_extractions,
                    "error": turn.error,
                })

            # Log score breakdown
            if result.score:
                d = result.score.to_dict()
                log(f"\n  {'─'*50}")
                log(f"  SCORE BREAKDOWN ({scenario_name}):")
                log(f"    Scam Detection:        {d['scamDetection']}/20")
                log(f"    Intel Extraction:       {d['intelligenceExtraction']}/30")
                log(f"    Conversation Quality:   {d['conversationQuality']}/30")
                cq = d["conversationQualityBreakdown"]
                log(f"      - Turn Count:         {cq['turnCount']}/8")
                log(f"      - Questions Asked:    {cq['questionsAsked']}/4")
                log(f"      - Relevant Questions: {cq['relevantQuestions']}/3")
                log(f"      - Red Flags:          {cq['redFlagIdentification']}/8")
                log(f"      - Elicitation:        {cq['informationElicitation']}/7")
                log(f"    Engagement Quality:     {d['engagementQuality']}/10")
                log(f"    Response Structure:      {d['responseStructure']}/10")
                log(f"    ─────────────────────────")
                log(f"    TOTAL:                  {d['total']}/100")
                log(f"    Duration:               {result.total_duration_seconds:.1f}s")

                if d.get("intelMatched"):
                    log(f"    ✓ Intel Matched: {d['intelMatched']}")
                if d.get("intelMissed"):
                    log(f"    ✗ Intel Missed:  {d['intelMissed']}")
                if d.get("missingRequiredFields"):
                    log(f"    ✗ Missing Required: {d['missingRequiredFields']}")
                if d.get("missingOptionalFields"):
                    log(f"    ⚠ Missing Optional: {d['missingOptionalFields']}")

                # Log extracted intelligence
                log(f"\n    Extracted Intelligence:")
                ei = result.final_output.get("extractedIntelligence", {})
                for key, values in ei.items():
                    if values:
                        log(f"      {key}: {values}")

            all_scenario_results.append(result)

        # ── FINAL SUMMARY ──
        log(f"\n\n{'█'*70}")
        log(f"  FINAL EVALUATION SUMMARY")
        log(f"{'█'*70}")
        log(f"\n  {'Scenario':<30} {'Weight':>7} {'Score':>7} {'Det':>5} {'Intel':>7} {'Conv':>6} {'Eng':>5} {'Str':>5}")
        log(f"  {'─'*73}")

        weighted_total = 0.0
        for sr in all_scenario_results:
            if sr.score:
                d = sr.score.to_dict()
                row = (
                    f"  {sr.scenario_name[:28]:<30} "
                    f"{sr.weight*100:>5.0f}% "
                    f"{sr.score.total:>6.1f} "
                    f"{d['scamDetection']:>5} "
                    f"{d['intelligenceExtraction']:>6.1f} "
                    f"{d['conversationQuality']:>5.1f} "
                    f"{d['engagementQuality']:>5} "
                    f"{d['responseStructure']:>5}"
                )
                log(row)
                weighted_total += sr.score.total * sr.weight

        log(f"  {'─'*73}")
        log(f"\n  Weighted Scenario Score: {weighted_total:.1f} / 100")
        log(f"  Final Score (with 10% code quality): {weighted_total * 0.9:.1f} + code_quality / 100")

        # ── ISSUES & IMPROVEMENT HINTS ──
        log(f"\n\n{'='*70}")
        log(f"  ISSUES & IMPROVEMENT HINTS")
        log(f"{'='*70}")

        for sr in all_scenario_results:
            if not sr.score:
                continue
            d = sr.score.to_dict()
            cq = d["conversationQualityBreakdown"]
            issues = []

            if d["scamDetection"] < 20:
                issues.append("CRITICAL: Scam NOT detected — classifier missed this scenario")
            if sr.score.intel_missed:
                issues.append(f"Intel missed: {sr.score.intel_missed}")
            if cq["turnCount"] < 8:
                issues.append(f"Turn count only {len(sr.turns)}/10 — agent may be exiting early")
            if cq["questionsAsked"] < 4:
                issues.append(f"Only score {cq['questionsAsked']}/4 on questions — add more ? in responses")
            if cq["relevantQuestions"] < 3:
                issues.append(f"Relevant questions {cq['relevantQuestions']}/3 — ask about identity/company/verification")
            if cq["redFlagIdentification"] < 8:
                issues.append(f"Red flag score {cq['redFlagIdentification']}/8 — mention urgency/OTP/suspicious in responses")
            if cq["informationElicitation"] < 5:
                issues.append(f"Elicitation {cq['informationElicitation']}/7 — probe for phone/account/email more")
            if d["engagementQuality"] < 10:
                issues.append(f"Engagement {d['engagementQuality']}/10 — check duration/message metrics")
            if sr.score.missing_required_fields:
                issues.append(f"Missing REQUIRED fields: {sr.score.missing_required_fields}")
            if sr.score.missing_optional_fields:
                issues.append(f"Missing optional fields: {sr.score.missing_optional_fields}")

            # Check response times
            slow_turns = [t for t in sr.turns if t.response_time_seconds > 25]
            if slow_turns:
                issues.append(f"{len(slow_turns)} turns exceeded 25s — risk of 30s timeout")

            errors = [t for t in sr.turns if t.error]
            if errors:
                issues.append(f"{len(errors)} turns had errors")

            if issues:
                log(f"\n  [{sr.scenario_name}]:")
                for issue in issues:
                    log(f"    - {issue}")
            else:
                log(f"\n  [{sr.scenario_name}]: ✓ All good!")

        log(f"\n\nEvaluation completed at {datetime.utcnow().isoformat()}Z")

        # ── Write JSON report ──
        report = {
            "meta": {
                "apiUrl": API_URL,
                "suite": "extended",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "totalDurationSeconds": sum(sr.total_duration_seconds for sr in all_scenario_results),
            },
            "weightedScenarioScore": round(weighted_total, 2),
            "estimatedFinalScore": round(weighted_total * 0.9, 2),
            "scenarios": [sr.to_dict() for sr in all_scenario_results],
            "allTurns": all_turns_log,
        }
        with open(json_file, "w") as jf:
            json.dump(report, jf, indent=2, ensure_ascii=False)

        log(f"\n📄 JSON report: {json_file}")
        log(f"📄 Full log:    {log_file}")

    return weighted_total


if __name__ == "__main__":
    score = asyncio.run(main())
    sys.exit(0 if score >= 80 else 1)
