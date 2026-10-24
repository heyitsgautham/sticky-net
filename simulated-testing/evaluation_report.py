"""Summary table and JSON results file for an evaluation run."""

import json
from datetime import datetime
from pathlib import Path

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
