#!/usr/bin/env python3
"""Quick test to verify timeout and retry settings."""

from config.settings import get_settings

s = get_settings()
print("Settings loaded successfully:")
print(f"  api_timeout_seconds: {s.api_timeout_seconds}")
print(f"  gemini_max_retries: {s.gemini_max_retries}")
print(f"  gemini_retry_delay_seconds: {s.gemini_retry_delay_seconds}")

# Verify values — updated to safe limits (20s per model, 0 retries → max ~23s total)
assert s.api_timeout_seconds == 20, f"Expected 20, got {s.api_timeout_seconds}"
assert s.gemini_max_retries == 0, f"Expected 0, got {s.gemini_max_retries}"
assert s.gemini_retry_delay_seconds == 0.5, f"Expected 0.5, got {s.gemini_retry_delay_seconds}"

print("\n✅ All settings verified correctly!")
