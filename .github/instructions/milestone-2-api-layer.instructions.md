---
#applyTo: "**"
---

# Milestone 2: API Layer

> **Goal**: Implement the FastAPI REST API with proper authentication, request validation, and response formatting.

## Prerequisites

- Milestone 1 completed (project structure exists)
- All `__init__.py` files in place
- `config/settings.py` working

## Tasks

### 2.1 Implement Pydantic Schemas

#### src/api/schemas.py

```python
"""Pydantic models for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class SenderType(str, Enum):
    """Message sender type."""

    SCAMMER = "scammer"
    USER = "user"


class ChannelType(str, Enum):
    """Communication channel type."""

    SMS = "SMS"
    WHATSAPP = "WhatsApp"
    EMAIL = "Email"
    CHAT = "Chat"


class Message(BaseModel):
    """Incoming message model."""

    sender: SenderType
    text: Annotated[str, Field(min_length=1, max_length=5000)]
    timestamp: datetime


class ConversationMessage(BaseModel):
    """Message in conversation history."""

    sender: SenderType
    text: str
    timestamp: datetime


class Metadata(BaseModel):
    """Request metadata."""

    channel: ChannelType = ChannelType.SMS
    language: str = "English"
    locale: str = "IN"


class AnalyzeRequest(BaseModel):
    """Main API request model."""

    message: Message
    conversationHistory: list[ConversationMessage] = Field(default_factory=list)
    metadata: Metadata = Field(default_factory=Metadata)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
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
            ]
        }
    }


class EngagementMetrics(BaseModel):
    """Engagement metrics model."""

    engagementDurationSeconds: int = 0
    totalMessagesExchanged: int = 0


class ExtractedIntelligence(BaseModel):
    """Extracted intelligence model."""

    bankAccounts: list[str] = Field(default_factory=list)
    upiIds: list[str] = Field(default_factory=list)
    phishingLinks: list[str] = Field(default_factory=list)


class StatusType(str, Enum):
    """Response status type."""

    SUCCESS = "success"
    ERROR = "error"


class AnalyzeResponse(BaseModel):
    """Main API response model."""

    status: StatusType = StatusType.SUCCESS
    scamDetected: bool
    engagementMetrics: EngagementMetrics = Field(default_factory=EngagementMetrics)
    extractedIntelligence: ExtractedIntelligence = Field(default_factory=ExtractedIntelligence)
    agentNotes: str = ""
    agentResponse: str | None = None  # The response to send back to the scammer

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "scamDetected": True,
                    "engagementMetrics": {
                        "engagementDurationSeconds": 420,
                        "totalMessagesExchanged": 18,
                    },
                    "extractedIntelligence": {
                        "bankAccounts": ["XXXX-XXXX-XXXX"],
                        "upiIds": ["scammer@upi"],
                        "phishingLinks": ["http://malicious-link.example"],
                    },
                    "agentNotes": "Scammer used urgency tactics and payment redirection",
                    "agentResponse": "Oh no! What do I need to do to verify?",
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Error response model."""

    status: StatusType = StatusType.ERROR
    error: str
    detail: str | None = None
```

### 2.2 Implement Authentication Middleware

#### src/api/middleware.py

```python
"""API middleware for authentication and request processing."""

import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import get_settings


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API key in request headers."""

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate API key for protected endpoints."""
        # Skip auth for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("x-api-key")
        settings = get_settings()

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"status": "error", "error": "Missing API key"},
            )

        if api_key != settings.api_key:
            return JSONResponse(
                status_code=403,
                content={"status": "error", "error": "Invalid API key"},
            )

        return await call_next(request)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add timing information to response headers."""
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        return response


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(APIKeyMiddleware)
```

### 2.3 Implement API Routes

#### src/api/routes.py

```python
"""API route definitions."""

import structlog
from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    EngagementMetrics,
    ErrorResponse,
    ExtractedIntelligence,
    StatusType,
)
from src.detection.detector import ScamDetector
from src.agents.honeypot_agent import HoneypotAgent
from src.intelligence.extractor import IntelligenceExtractor
from src.exceptions import StickyNetError

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        200: {"model": AnalyzeResponse, "description": "Successful analysis"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def analyze_message(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze incoming message for scam detection and engagement.

    This endpoint:
    1. Analyzes the message for scam indicators
    2. If scam detected, activates AI agent for engagement
    3. Extracts intelligence from conversation
    4. Returns structured response with metrics
    """
    log = logger.bind(
        channel=request.metadata.channel,
        history_length=len(request.conversationHistory),
    )
    log.info("Processing analyze request")

    try:
        # Step 1: Detect scam
        detector = ScamDetector()
        detection_result = await detector.analyze(
            message=request.message.text,
            history=request.conversationHistory,
            metadata=request.metadata,
        )

        if not detection_result.is_scam:
            log.info("Message not detected as scam")
            return AnalyzeResponse(
                status=StatusType.SUCCESS,
                scamDetected=False,
                agentNotes="No scam indicators detected",
            )

        log.info("Scam detected", confidence=detection_result.confidence)

        # Step 2: Engage with AI agent
        agent = HoneypotAgent()
        engagement_result = await agent.engage(
            message=request.message,
            history=request.conversationHistory,
            metadata=request.metadata,
            detection=detection_result,
        )

        # Step 3: Extract intelligence
        extractor = IntelligenceExtractor()
        all_messages = [
            *[m.text for m in request.conversationHistory],
            request.message.text,
        ]
        intelligence = await extractor.extract(all_messages)

        # Step 4: Build response
        return AnalyzeResponse(
            status=StatusType.SUCCESS,
            scamDetected=True,
            engagementMetrics=EngagementMetrics(
                engagementDurationSeconds=engagement_result.duration_seconds,
                totalMessagesExchanged=len(request.conversationHistory) + 1,
            ),
            extractedIntelligence=ExtractedIntelligence(
                bankAccounts=intelligence.bank_accounts,
                upiIds=intelligence.upi_ids,
                phishingLinks=intelligence.phishing_links,
            ),
            agentNotes=engagement_result.notes,
            agentResponse=engagement_result.response,
        )

    except StickyNetError as e:
        log.error("Application error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.exception("Unexpected error")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### 2.4 Update Main Application

#### src/main.py (Updated)

```python
"""FastAPI application entry point."""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.api.middleware import setup_middleware
from config.settings import get_settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Sticky-Net",
        description="AI Agentic Honey-Pot for Scam Detection & Intelligence Extraction",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware (configure for production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom middleware
    setup_middleware(app)

    # Include routers
    app.include_router(router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.on_event("startup")
    async def startup_event() -> None:
        """Application startup tasks."""
        logger.info(
            "Starting Sticky-Net",
            debug=settings.debug,
            llm_model=settings.llm_model,
        )

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Application shutdown tasks."""
        logger.info("Shutting down Sticky-Net")

    return app


app = create_app()
```

### 2.5 Create API Module Init

#### src/api/__init__.py

```python
"""API module for Sticky-Net."""

from src.api.routes import router
from src.api.schemas import AnalyzeRequest, AnalyzeResponse
from src.api.middleware import setup_middleware

__all__ = ["router", "AnalyzeRequest", "AnalyzeResponse", "setup_middleware"]
```

### 2.6 Write API Tests

#### tests/test_api.py

```python
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
```

## Verification Checklist

- [ ] `src/api/schemas.py` implements all request/response models
- [ ] `src/api/middleware.py` validates API key authentication
- [ ] `src/api/routes.py` implements `/api/v1/analyze` endpoint
- [ ] `src/main.py` properly configures FastAPI app
- [ ] API returns 401 for missing API key
- [ ] API returns 403 for invalid API key
- [ ] Health endpoint accessible without auth
- [ ] Request validation works (422 for invalid requests)
- [ ] All tests pass: `pytest tests/test_api.py -v`

## Testing the API

```bash
# Start the server
uvicorn src.main:app --reload --port 8080

# Test health endpoint
curl http://localhost:8080/health

# Test with valid API key (will fail until detection/agent modules implemented)
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "message": {
      "sender": "scammer",
      "text": "Your account is blocked!",
      "timestamp": "2026-01-21T10:15:30Z"
    },
    "conversationHistory": [],
    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
  }'
```

## Next Steps

After completing this milestone, proceed to **Milestone 3: Scam Detection** to implement the fraud indicator analysis.
