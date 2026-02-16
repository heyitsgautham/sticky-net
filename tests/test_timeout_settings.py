#!/usr/bin/env python3
"""Quick test to verify timeout and retry settings."""

from config.settings import get_settings

s = get_settings()
print("Settings loaded successfully:")
print(f"  api_timeout_seconds: {s.api_timeout_seconds}")
print(f"  gemini_max_retries: {s.gemini_max_retries}")
print(f"  gemini_retry_delay_seconds: {s.gemini_retry_delay_seconds}")

# Verify values
assert s.api_timeout_seconds == 90, f"Expected 90, got {s.api_timeout_seconds}"
assert s.gemini_max_retries == 2, f"Expected 2, got {s.gemini_max_retries}"
assert s.gemini_retry_delay_seconds == 1.0, f"Expected 1.0, got {s.gemini_retry_delay_seconds}"

print("\n✅ All settings verified correctly!")
