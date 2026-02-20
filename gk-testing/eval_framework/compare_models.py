#!/usr/bin/env python3
"""Compare Gemini 3 Flash vs 2.5 Flash: response time and conversation quality.

Runs the same 2 scenarios (bank_fraud + tech_support) against the live server.
Between runs, modifies config/settings.py to swap models, waits for uvicorn reload.

Usage: .venv/bin/python eval_framework/compare_models.py
"""

import asyncio
import json
import os
import re
import sys
import time
import httpx
from datetime import datetime, timezone
from pathlib import Path

API_URL = "http://localhost:8080"
DETECT_URL = f"{API_URL}/api/v1/analyze"
HEALTH_URL = f"{API_URL}/health"
SETTINGS_PATH = Path(__file__).parent.parent / "config" / "settings.py"

MODELS_TO_TEST = [
    ("Gemini 3 Flash", "gemini-3-flash-preview"),
    ("Gemini 2.5 Flash", "gemini-2.5-flash-preview-04-17"),
]

# Two representative scenarios: bank_fraud scored 96, tech_support scored 61.5
SCENARIOS = [
    {
        "name": "Bank Fraud (simple)",
        "turns": [
            "URGENT: Your SBI account has been compromised due to unauthorized login. Your account will be permanently blocked in 2 hours unless you verify your identity immediately.",
            "I am Senior Officer Rajesh Kumar from SBI Fraud Prevention Cell. For immediate assistance call me at +91-9823456710.",
            "To verify your identity, please transfer Rs 1 to our secure UPI: sbi.security@axisbank. Standard security procedure.",
            "If UPI is not available, transfer to account 50100487652341, IFSC: SBIN0001234.",
            "Time is running out. Send to UPI sbi.security@axisbank or account 50100487652341. Call +91-9823456710.",
        ],
    },
    {
        "name": "Tech Support (hard)",
        "turns": [
            "CRITICAL ALERT: Your computer has been compromised with malware. Your personal data including bank details are being stolen. Call Microsoft Certified Support immediately.",
            "I am Microsoft Certified Security Engineer. Your case ID: MS-SEC-2026-78432. Call us at +91-7890123456 for remote assistance.",
            "Email our security team at techsupport@microsoft-help-india.com. Case MS-SEC-2026-78432 requires urgent action.",
            "The hackers are from Eastern Europe attacking your system. We need to install protective software. Call +91-7890123456 now.",
            "To fix remotely, we need TeamViewer. Security restoration fee Rs 2,999. Email techsupport@microsoft-help-india.com for payment link.",
        ],
    },
]


def swap_model_in_settings(model_name: str):
    """Swap the pro_model in config/settings.py to trigger uvicorn reload."""
    content = SETTINGS_PATH.read_text()
    new_content = re.sub(
        r'(pro_model: str = ")[^"]+(")',
        rf'\g<1>{model_name}\g<2>',
        content,
        count=1,
    )
    SETTINGS_PATH.write_text(new_content)
    print(f"  [config] pro_model set to: {model_name}")


async def wait_for_reload(expected_model: str, max_wait: int = 15):
    """Wait for uvicorn to reload by polling health endpoint."""
    print(f"  [reload] Waiting for server reload...", end="", flush=True)
    async with httpx.AsyncClient() as client:
        for i in range(max_wait):
            await asyncio.sleep(1)
            try:
                r = await client.get(HEALTH_URL, timeout=3)
                if r.status_code == 200:
                    print(f" ready ({i+1}s)")
                    return True
            except Exception:
                print(".", end="", flush=True)
    print(" timeout!")
    return False


async def run_scenario(client: httpx.AsyncClient, scenario: dict, session_prefix: str) -> dict:
    """Run a single scenario and collect timing + response data."""
    session_id = f"{session_prefix}-{int(time.time())}"
    history = []
    results = []

    for i, scammer_msg in enumerate(scenario["turns"], 1):
        timestamp = int(time.time() * 1000)
        payload = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": scammer_msg,
                "timestamp": timestamp,
            },
            "conversationHistory": history.copy(),
            "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
        }

        start = time.monotonic()
        try:
            resp = await client.post(DETECT_URL, json=payload, timeout=30.0)
            elapsed = time.monotonic() - start
            data = resp.json()
            reply = data.get("reply", data.get("message", data.get("text", "")))
            error = False
        except Exception as e:
            elapsed = time.monotonic() - start
            reply = ""
            error = True

        results.append({
            "turn": i,
            "response_time": round(elapsed, 2),
            "reply_length": len(reply),
            "reply_preview": reply[:120] if reply else "(empty/timeout)",
            "error": error,
            "has_question": "?" in reply if reply else False,
        })

        # Build history for next turn
        history.append({"sender": "scammer", "text": scammer_msg, "timestamp": timestamp})
        if reply:
            history.append({"sender": "user", "text": reply, "timestamp": int(time.time() * 1000)})

    times = [r["response_time"] for r in results if not r["error"]]
    return {
        "scenario": scenario["name"],
        "turns": results,
        "avg_time": round(sum(times) / len(times), 2) if times else 0,
        "max_time": round(max(times), 2) if times else 0,
        "min_time": round(min(times), 2) if times else 0,
        "errors": sum(1 for r in results if r["error"]),
        "successful": len(times),
        "questions": sum(1 for r in results if r["has_question"]),
    }


async def run_model_test(model_label: str, model_name: str) -> list[dict]:
    """Swap model, wait for reload, run scenarios."""
    swap_model_in_settings(model_name)
    await wait_for_reload(model_name)

    print(f"\n{'='*70}")
    print(f"  TESTING: {model_label} ({model_name})")
    print(f"  Time: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC")
    print(f"{'='*70}")

    async with httpx.AsyncClient() as client:
        results = []
        for scenario in SCENARIOS:
            print(f"\n  --- {scenario['name']} ({len(scenario['turns'])} turns) ---")
            result = await run_scenario(client, scenario, model_name[:8])
            results.append(result)

            for t in result["turns"]:
                status = " ERROR" if t["error"] else f"{t['response_time']:>5.1f}s"
                q = "?" if t["has_question"] else " "
                print(f"    Turn {t['turn']}: [{status}] {q} {t['reply_preview'][:70]}")

            print(f"    >> avg={result['avg_time']}s  min={result['min_time']}s  max={result['max_time']}s  errors={result['errors']}  questions={result['questions']}")

    return results


def print_comparison(all_results: dict):
    """Print final comparison table."""
    labels = list(all_results.keys())

    print(f"\n\n{'█'*70}")
    print(f"  FINAL COMPARISON")
    print(f"{'█'*70}")

    header = f"  {'Metric':<28}"
    for label in labels:
        header += f" {label:>18}"
    print(f"\n{header}")
    print(f"  {'─'*70}")

    for i, scenario in enumerate(SCENARIOS):
        print(f"\n  {scenario['name']}")
        metrics = ["avg_time", "min_time", "max_time", "errors", "successful", "questions"]
        units = {"avg_time": "s", "min_time": "s", "max_time": "s", "errors": "", "successful": "", "questions": ""}
        names = {"avg_time": "Avg Time", "min_time": "Min Time", "max_time": "Max Time",
                 "errors": "Errors", "successful": "Successes", "questions": "Questions"}

        for m in metrics:
            row = f"    {names[m]:<26}"
            for label in labels:
                val = all_results[label][i][m]
                row += f" {val:>17}{units[m]}"
            print(row)

    # Overall  
    print(f"\n  OVERALL")
    for label in labels:
        all_times = [t["response_time"] for r in all_results[label] for t in r["turns"] if not t["error"]]
        total_err = sum(r["errors"] for r in all_results[label])
        avg = round(sum(all_times) / len(all_times), 2) if all_times else 0
        print(f"    {label}: avg={avg}s, errors={total_err}/{sum(len(s['turns']) for s in SCENARIOS)}")

    print(f"\n{'█'*70}\n")


async def main():
    print("=" * 70)
    print("  MODEL COMPARISON TEST")
    print(f"  max_output_tokens = 8192 (both models)")
    print(f"  Unused JSON fields removed from prompt")
    print(f"  2 scenarios x 5 turns = 10 API calls per model")
    print("=" * 70)

    # Save original settings
    original_content = SETTINGS_PATH.read_text()

    all_results = {}
    try:
        for label, model_name in MODELS_TO_TEST:
            results = await run_model_test(label, model_name)
            all_results[label] = results

        print_comparison(all_results)
    finally:
        # Restore original settings
        SETTINGS_PATH.write_text(original_content)
        print("  [config] Restored original settings.py")
        print("  [reload] Server will auto-reload to original config")


if __name__ == "__main__":
    asyncio.run(main())
