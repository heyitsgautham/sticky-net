"""Pytest fixtures and configuration."""

import os

# Set test environment variables before importing app
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("DEBUG", "true")
# Never POST to the real GUVI evaluation endpoint from a test run.
os.environ["GUVI_CALLBACK_ENABLED"] = "false"

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app


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


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def api_key() -> str:
    """Test API key."""
    return "test-api-key"


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Authentication headers for API requests."""
    return {"x-api-key": "test-api-key"}


@pytest.fixture
def sample_scam_message() -> dict:
    """Sample scam message for testing."""
    return {
        "message": {
            "sender": "scammer",
            "text": "Your bank account will be blocked today. Verify immediately.",
            "timestamp": "2026-01-21T10:15:30Z",
        },
        "conversationHistory": [],
        "metadata": {
            "channel": "SMS",
            "language": "English",
            "locale": "IN",
        },
    }


@pytest.fixture
def sample_legitimate_message() -> dict:
    """Sample legitimate message for testing."""
    return {
        "message": {
            "sender": "user",
            "text": "Hello, how are you doing today?",
            "timestamp": "2026-01-21T10:15:30Z",
        },
        "conversationHistory": [],
        "metadata": {
            "channel": "SMS",
            "language": "English",
            "locale": "IN",
        },
    }
