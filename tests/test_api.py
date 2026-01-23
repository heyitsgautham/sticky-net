"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

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

    def test_missing_api_key_returns_401(self, client: TestClient):
        """Request without API key should return 401."""
        response = client.post("/api/v1/analyze", json={})
        assert response.status_code == 401
        assert response.json()["error"] == "Missing API key"

    def test_invalid_api_key_returns_403(self, client: TestClient):
        """Request with invalid API key should return 403."""
        response = client.post(
            "/api/v1/analyze",
            json={},
            headers={"x-api-key": "wrong-key"},
        )
        assert response.status_code == 403
        assert response.json()["error"] == "Invalid API key"


class TestAnalyzeEndpoint:
    """Tests for analyze endpoint."""

    @patch("src.api.routes.ScamDetector")
    @patch("src.api.routes.HoneypotAgent")
    @patch("src.api.routes.IntelligenceExtractor")
    def test_scam_detected_returns_engagement(
        self,
        mock_extractor,
        mock_agent,
        mock_detector,
        client: TestClient,
        auth_headers: dict,
        sample_scam_message: dict,
    ):
        """Scam message should trigger engagement."""
        # Setup mocks
        mock_detector_instance = mock_detector.return_value
        mock_detector_instance.analyze = AsyncMock(
            return_value=type("Result", (), {"is_scam": True, "confidence": 0.95})()
        )

        mock_agent_instance = mock_agent.return_value
        mock_agent_instance.engage = AsyncMock(
            return_value=type(
                "Result",
                (),
                {
                    "duration_seconds": 120,
                    "notes": "Urgency tactics detected",
                    "response": "Oh no, what should I do?",
                },
            )()
        )

        mock_extractor_instance = mock_extractor.return_value
        mock_extractor_instance.extract = AsyncMock(
            return_value=type(
                "Result",
                (),
                {"bank_accounts": [], "upi_ids": [], "phishing_links": []},
            )()
        )

        response = client.post(
            "/api/v1/analyze",
            json=sample_scam_message,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["scamDetected"] is True
        assert "agentResponse" in data

    @patch("src.api.routes.ScamDetector")
    def test_legitimate_message_returns_no_scam(
        self,
        mock_detector,
        client: TestClient,
        auth_headers: dict,
        sample_legitimate_message: dict,
    ):
        """Legitimate message should not trigger engagement."""
        mock_detector_instance = mock_detector.return_value
        mock_detector_instance.analyze = AsyncMock(
            return_value=type("Result", (), {"is_scam": False, "confidence": 0.1})()
        )

        response = client.post(
            "/api/v1/analyze",
            json=sample_legitimate_message,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["scamDetected"] is False

    def test_invalid_request_body_returns_422(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Invalid request body should return 422."""
        response = client.post(
            "/api/v1/analyze",
            json={"invalid": "data"},
            headers=auth_headers,
        )
        assert response.status_code == 422
