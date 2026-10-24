"""Console summary of an evaluation run, with hints for the weakest scores."""

from __future__ import annotations

from eval_framework.results import EvalResult


def print_summary(result: EvalResult) -> None:
    """Print a formatted evaluation summary."""
    print("\n" + "█" * 70)
    print("  EVALUATION RESULTS")
    print("█" * 70)

    # Per-scenario table
    header = f"  {'Scenario':<30} {'Weight':>7} {'Score':>7} {'Det':>5} {'Intel':>7} {'Conv':>6} {'Eng':>5} {'Str':>5}"
    print(header)
    print("  " + "─" * 68)

    for sr in result.scenarios:
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
            print(row)
        elif sr.error:
            print(f"  {sr.scenario_name[:28]:<30} {sr.weight*100:>5.0f}%   ERROR: {sr.error[:30]}")

    print("  " + "─" * 68)
    print(f"\n  Weighted Scenario Score: {result.weighted_score:.1f} / 100")
    print(f"  Code Quality Score:     {result.code_quality_score:.0f} / 10")
    print("  ────────────────────────────")
    print(f"  FINAL SCORE:            {result.final_score:.1f} / 100")
    print()

    # Improvement hints
    print_improvement_hints(result)

def print_improvement_hints(result: EvalResult) -> None:
    """Print actionable improvement suggestions."""
    hints = []

    for sr in result.scenarios:
        if not sr.score:
            continue
        d = sr.score.to_dict()

        if d["scamDetection"] < 20:
            hints.append(f"⚠ {sr.scenario_name}: Scam NOT detected — check classifier")

        if sr.score.intel_missed:
            hints.append(
                f"⚠ {sr.scenario_name}: Missed intel — {sr.score.intel_missed}"
            )

        cq = d["conversationQualityBreakdown"]
        if cq["turnCount"] < 8:
            hints.append(
                f"💡 {sr.scenario_name}: Only {len(sr.turns)} turns — aim for 8+ for max points"
            )
        if cq["questionsAsked"] < 4:
            hints.append(
                f"💡 {sr.scenario_name}: Ask more questions (need ≥5 for max 4pts)"
            )
        if cq["redFlagIdentification"] < 8:
            hints.append(
                f"💡 {sr.scenario_name}: Identify more red flags in responses"
            )
        if cq["informationElicitation"] < 7:
            hints.append(
                f"💡 {sr.scenario_name}: Probe for more scammer details"
            )

        if d["engagementQuality"] < 10:
            hints.append(
                f"💡 {sr.scenario_name}: Engagement quality {d['engagementQuality']}/10 — check duration/message count"
            )

        if sr.score.missing_required_fields:
            hints.append(
                f"🔴 {sr.scenario_name}: Missing required fields: {sr.score.missing_required_fields}"
            )

    if hints:
        print("  IMPROVEMENT HINTS:")
        for h in hints:
            print(f"    {h}")
        print()
