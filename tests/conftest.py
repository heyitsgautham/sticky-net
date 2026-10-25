"""Fixtures for the tests/ suite. Repo-wide setup lives in the root conftest.py."""

import pytest
from fastapi.testclient import TestClient

from config.settings import get_settings
from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def api_key() -> str:
    """The API_KEY the test settings were built with."""
    return get_settings().api_key


@pytest.fixture
def auth_headers(api_key: str) -> dict[str, str]:
    """Authentication headers for API requests."""
    return {"x-api-key": api_key}


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
