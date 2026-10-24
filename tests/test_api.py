"""Tests for API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.agents.honeypot_agent import EngagementResult
from src.agents.policy import EngagementMode
from src.detection.detector import DetectionResult
from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Authentication headers."""
    return {"x-api-key": "test-api-key"}


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_returns_healthy(self, client: TestClient):
        """Health check should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_check_no_auth_required(self, client: TestClient):
        """Health check should not require authentication."""
        response = client.get("/health")
        assert response.status_code == 200


class TestAuthentication:
    """Tests for API authentication."""

    @patch("src.api.middleware.get_settings")
    def test_missing_api_key_returns_401(
        self, mock_settings, client: TestClient, sample_scam_message: dict
    ):
        """Request without API key should return 401."""
        # Mock settings to disable debug mode for this test
        mock_settings_instance = MagicMock()
        mock_settings_instance.debug = False  # Disable debug mode
        mock_settings_instance.api_key = "test-api-key"
        mock_settings.return_value = mock_settings_instance

        # Use a valid request body to avoid 422 from FastAPI validation
        response = client.post("/api/v1/analyze", json=sample_scam_message)
        assert response.status_code == 401
        assert response.json()["error"] == "Missing API key"

    @patch("src.api.middleware.get_settings")
    def test_invalid_api_key_returns_403(
        self, mock_settings, client: TestClient, sample_scam_message: dict
    ):
        """Request with invalid API key should return 403."""
        # Mock settings for consistent behavior
        mock_settings_instance = MagicMock()
        mock_settings_instance.debug = False
        mock_settings_instance.api_key = "test-api-key"
        mock_settings.return_value = mock_settings_instance

        response = client.post(
            "/api/v1/analyze",
            json=sample_scam_message,
            headers={"x-api-key": "wrong-key"},
        )
        assert response.status_code == 403
        assert response.json()["error"] == "Invalid API key"


class TestAnalyzeEndpoint:
    """Tests for analyze endpoint."""

    @patch("src.api.routes.get_agent")
    @patch("src.api.routes.get_detector")
    def test_scam_detected_returns_engagement(
        self,
        mock_get_detector,
        mock_get_agent,
        client: TestClient,
        auth_headers: dict,
        sample_scam_message: dict,
    ):
        """A scam message reaches the agent and the reply is the agent's reply."""
        mock_get_detector.return_value.analyze = AsyncMock(
            return_value=DetectionResult(is_scam=True, confidence=0.95, scam_type="banking_fraud")
        )
        agent = mock_get_agent.return_value
        agent.engage = AsyncMock(
            return_value=EngagementResult(
                response="Oh no, what should I do?",
                duration_seconds=120,
                notes="Urgency tactics detected",
                conversation_id="test-conv-123",
                turn_number=1,
                engagement_mode=EngagementMode.CAUTIOUS,
                should_continue=True,
            )
        )
        agent._generate_notes = MagicMock(return_value="Test agent notes")

        response = client.post(
            "/api/v1/analyze",
            json=sample_scam_message,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["reply"] == "Oh no, what should I do?"
        agent.engage.assert_awaited_once()
        assert agent.engage.await_args.kwargs["turn_number"] == 1

    @patch("src.api.routes.get_agent")
    @patch("src.api.routes.get_detector")
    def test_legitimate_message_returns_no_scam(
        self,
        mock_get_detector,
        mock_get_agent,
        client: TestClient,
        auth_headers: dict,
        sample_legitimate_message: dict,
    ):
        """A message the detector clears gets a canned greeting and never reaches the agent."""
        mock_get_detector.return_value.analyze = AsyncMock(
            return_value=DetectionResult(is_scam=False, confidence=0.1)
        )

        response = client.post(
            "/api/v1/analyze",
            json=sample_legitimate_message,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["reply"]
        mock_get_agent.assert_not_called()

    def test_invalid_request_body_returns_200_with_fallback(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Invalid request body should return 200 with fallback reply (Fix 8C: never 422)."""
        response = client.post(
            "/api/v1/analyze",
            json={"invalid": "data"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "reply" in data
