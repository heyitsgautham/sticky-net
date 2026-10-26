"""Repo-wide pytest setup: test settings and no outside network calls.

Every suite (tests/, final-testing/) gets these, so no test can reach
Vertex AI, Firestore or the GUVI evaluator by accident.
"""

import os

# Set test environment variables before anything imports the app or Settings.
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("DEBUG", "true")
# The suite sends hundreds of requests from one client; tests/security/test_rate_limit.py
# turns limiting back on with its own small limits.
os.environ["RATE_LIMIT_ENABLED"] = "false"
# Never POST to the real GUVI evaluation endpoint from a test run.
os.environ["GUVI_CALLBACK_ENABLED"] = "false"

from collections.abc import Iterator  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def offline_services(monkeypatch: pytest.MonkeyPatch) -> Iterator[MagicMock]:
    """Keep every test offline.

    Any ``genai.Client`` built during a test is a fake whose ``generate_content``
    raises, so code under test takes its no-LLM fallback path instead of calling
    Vertex AI. Firestore is marked unavailable so the session store stays in memory.
    Tests that need a specific LLM reply patch the client themselves.
    """
    import src.agents.honeypot_agent as agent_module
    import src.api.session_store as session_store
    import src.detection.detector as detector_module

    fake_client = MagicMock(name="genai.Client()")
    fake_client.models.generate_content.side_effect = RuntimeError(
        "Gemini calls are disabled in tests"
    )
    monkeypatch.setattr("google.genai.Client", MagicMock(return_value=fake_client))
    monkeypatch.setattr(session_store, "_firestore_available", False)
    monkeypatch.setattr(session_store, "_firestore_client", None)
    monkeypatch.setattr(detector_module, "_detector_instance", None)
    monkeypatch.setattr(agent_module, "_agent_instance", None)
    yield fake_client
