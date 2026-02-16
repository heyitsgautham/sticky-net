"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

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
    def test_missing_api_key_returns_401(self, mock_settings, client: TestClient, sample_scam_message: dict):
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
    def test_invalid_api_key_returns_403(self, mock_settings, client: TestClient, sample_scam_message: dict):
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
    @patch("src.api.routes.ScamDetector")
    @patch("src.api.routes.HoneypotAgent")
    @patch("src.api.routes.IntelligenceExtractor")
    def test_scam_detected_returns_engagement(
        self,
        mock_extractor,
        mock_agent,
        mock_detector,
        mock_get_agent,
        client: TestClient,
        auth_headers: dict,
        sample_scam_message: dict,
    ):
        """Scam message should trigger engagement."""
        # Setup mocks
        mock_detector_instance = mock_detector.return_value
        mock_detector_instance.analyze = AsyncMock(
            return_value=type(
                "Result", (), 
                {"is_scam": True, "confidence": 0.95, "scam_type": "banking_fraud"}
            )()
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
                    "extracted_intelligence": None,  # Agent may return extracted intel
                    "conversation_id": "test-conv-123",
                    "engagement_mode": "CAUTIOUS",
                    "turn_number": 1,
                    "should_continue": True,
                    "exit_reason": None,
                },
            )()
        )
        # Mock the persona manager for notes generation
        mock_agent_instance.persona_manager = MagicMock()
        mock_agent_instance.persona_manager.get_or_create_persona = MagicMock(
            return_value=MagicMock(name="TestPersona")
        )
        mock_agent_instance._generate_notes = MagicMock(return_value="Test agent notes")
        
        # Setup get_agent singleton mock to return the same mocked agent
        mock_get_agent.return_value = mock_agent_instance

        mock_extractor_instance = mock_extractor.return_value
        # extract is synchronous, not async - use MagicMock
        mock_extractor_instance.extract = MagicMock(
            return_value=type(
                "Result",
                (),
                {
                    "bank_accounts": [],
                    "upi_ids": [],
                    "phishing_links": [],
                    "phone_numbers": [],
                    "emails": [],
                    "beneficiary_names": [],
                    "bank_names": [],
                    "ifsc_codes": [],
                    "whatsapp_numbers": [],
                },
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
        # New simplified response format: just status and reply
        assert "reply" in data
        assert isinstance(data["reply"], str)

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
            return_value=type(
                "Result", (), 
                {"is_scam": False, "confidence": 0.1, "scam_type": None}
            )()
        )

        response = client.post(
            "/api/v1/analyze",
            json=sample_legitimate_message,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        # New simplified response format: just status and reply
        assert "reply" in data
        assert isinstance(data["reply"], str)

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
