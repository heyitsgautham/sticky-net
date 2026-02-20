#!/usr/bin/env python3
"""
Sticky-Net Evaluation CLI

Run the hackathon evaluation locally against your API to measure
performance and identify improvements.

Usage:
    # Quick eval with standard 3 scenarios:
    python -m eval_framework.cli --url http://localhost:8080

    # Extended eval with 5 scenarios:
    python -m eval_framework.cli --url http://localhost:8080 --suite extended

    # Single scenario:
    python -m eval_framework.cli --url http://localhost:8080 --scenario bank_fraud_01

    # Save JSON report:
    python -m eval_framework.cli --url http://localhost:8080 --output report.json

    # Use detailed endpoint for richer intelligence capture:
    python -m eval_framework.cli --url http://localhost:8080 --detailed

    # Quiet mode (JSON only):
    python -m eval_framework.cli --url http://localhost:8080 --quiet --output report.json
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from eval_framework.runner import EvalRunner, EvalResult
from eval_framework.scenarios import get_scenario, get_scenario_suite, ALL_SCENARIOS


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sticky-Net Hackathon Evaluation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m eval_framework.cli                                    # Standard eval, localhost
  python -m eval_framework.cli --url https://my-api.run.app       # Against deployed API
  python -m eval_framework.cli --suite extended --output eval.json # Extended eval with report
  python -m eval_framework.cli --scenario bank_fraud_01            # Single scenario
  python -m eval_framework.cli --list-scenarios                    # Show available scenarios
        """,
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="API base URL (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--api-key",
        default="test-api-key",
        help="API key for x-api-key header (default: test-api-key)",
    )
    parser.add_argument(
        "--suite",
        choices=["standard", "extended"],
        default="standard",
        help="Scenario suite: 'standard' (3 scenarios) or 'extended' (5 scenarios)",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="Run a single scenario by ID (e.g., bank_fraud_01)",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Use /api/v1/analyze/detailed endpoint for richer response data",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Save JSON evaluation report to a file",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output (useful with --output)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List all available scenarios and exit",
    )

    return parser.parse_args()


def list_scenarios():
    """Print available scenarios."""
    print("\nAvailable Evaluation Scenarios:")
    print("─" * 60)
    for sid, s in ALL_SCENARIOS.items():
        fake_keys = list(s.get("fakeData", {}).keys())
        print(
            f"  {sid:<20} {s['name']:<30} "
            f"type={s['scamType']}, turns={s['maxTurns']}, "
            f"intel={fake_keys}"
        )
    print()

    print("Scenario Suites:")
    print("─" * 60)
    scenarios, weights = get_scenario_suite("standard")
    print(f"  standard  ({len(scenarios)} scenarios): ", end="")
    print(", ".join(f"{s['scenarioId']} ({w*100:.0f}%)" for s, w in zip(scenarios, weights)))

    scenarios, weights = get_scenario_suite("extended")
    print(f"  extended  ({len(scenarios)} scenarios): ", end="")
    print(", ".join(f"{s['scenarioId']} ({w*100:.0f}%)" for s, w in zip(scenarios, weights)))
    print()


async def run_eval(args) -> EvalResult:
    """Run the evaluation with parsed arguments."""
    runner = EvalRunner(
        base_url=args.url,
        api_key=args.api_key,
        timeout=args.timeout,
    )

    if args.scenario:
        # Single scenario
        scenario = get_scenario(args.scenario)
        result = await runner.run_evaluation(
            scenarios=[scenario],
            weights=[1.0],
            use_detailed=args.detailed,
            verbose=not args.quiet,
        )
    else:
        # Full suite
        scenarios, weights = get_scenario_suite(args.suite)
        result = await runner.run_evaluation(
            scenarios=scenarios,
            weights=weights,
            use_detailed=args.detailed,
            verbose=not args.quiet,
        )

    return result


def main():
    args = parse_args()

    if args.list_scenarios:
        list_scenarios()
        sys.exit(0)

    # Run evaluation
    result = asyncio.run(run_eval(args))

    # Save report if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report = result.to_dict()
        report["meta"] = {
            "apiUrl": args.url,
            "suite": args.suite if not args.scenario else f"single:{args.scenario}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "detailed": args.detailed,
        }
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to {output_path}")

    # Exit code: 0 if score >= 80, 1 otherwise (useful for CI)
    if result.weighted_score >= 80:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
