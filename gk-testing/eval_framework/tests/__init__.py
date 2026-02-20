"""
Pytest-based evaluation tests.

These tests validate the scoring engine accuracy and can run the full
evaluation against a live API server.

Run:
    .venv/bin/python -m pytest eval_framework/tests/ -v
    .venv/bin/python -m pytest eval_framework/tests/ -v -k "scoring"   # Scoring only
    .venv/bin/python -m pytest eval_framework/tests/ -v -k "live"      # Live API tests
"""
