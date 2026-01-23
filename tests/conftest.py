"""Pytest fixtures and configuration."""

import os

# Set test environment variables before importing app
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("DEBUG", "true")

import pytest
from fastapi.testclient import TestClient

from src.main import app


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
