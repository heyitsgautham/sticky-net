---
# applyTo: "**"
---

# Milestone 1: Project Setup

> **Goal**: Scaffold the complete project structure, configure dependencies, and set up local development environment with Docker Compose.

## Prerequisites

- Python 3.11+ installed
- Docker & Docker Compose installed
- GCP account with Vertex AI and Firestore enabled
- Service account JSON key for local development

## Tasks

### 1.1 Create Project Configuration Files

#### pyproject.toml
Create `pyproject.toml` with the following dependencies:

```toml
[project]
name = "sticky-net"
version = "0.1.0"
description = "AI Agentic Honey-Pot for Scam Detection"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "google-genai>=1.51.0",
    "google-cloud-firestore>=2.14.0",
    "python-dotenv>=1.0.0",
    "structlog>=24.1.0",
    "httpx>=0.26.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.26.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.11"
strict = true
```

#### .env.example
Create `.env.example`:

```bash
# API Configuration
API_KEY=your-secret-api-key-here
PORT=8080
DEBUG=true

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_APPLICATION_CREDENTIALS=./secrets/service-account.json

# Firestore
FIRESTORE_COLLECTION=conversations
FIRESTORE_EMULATOR_HOST=localhost:8081

# Agent Configuration - Models
FLASH_MODEL=gemini-3-flash-preview
PRO_MODEL=gemini-3-pro-preview
LLM_TEMPERATURE=0.7

# Engagement Policy
MAX_ENGAGEMENT_TURNS_CAUTIOUS=10
MAX_ENGAGEMENT_TURNS_AGGRESSIVE=25
MAX_ENGAGEMENT_DURATION_SECONDS=600
CAUTIOUS_CONFIDENCE_THRESHOLD=0.60
AGGRESSIVE_CONFIDENCE_THRESHOLD=0.85
```

#### .gitignore
Create `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo
.DS_Store

# Environment
.env
.env.local
*.local

# Secrets
secrets/
*.json
!package.json

# Testing
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/

# Docker
*.log

# Firestore emulator
firestore-data/
```

### 1.2 Create Docker Configuration

#### Dockerfile
Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir .

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### docker-compose.yml
Create `docker-compose.yml` for local development:

```yaml
version: "3.9"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - API_KEY=${API_KEY:-dev-api-key}
      - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
      - VERTEX_AI_LOCATION=${VERTEX_AI_LOCATION:-us-central1}
      - GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/service-account.json
      - FIRESTORE_EMULATOR_HOST=firestore:8081
      - LLM_MODEL=${LLM_MODEL:-gemini-3-pro}
      - DEBUG=true
    volumes:
      - ./src:/app/src:ro
      - ./config:/app/config:ro
      - ./secrets:/app/secrets:ro
    depends_on:
      - firestore
    networks:
      - sticky-net

  firestore:
    image: gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators
    command: gcloud emulators firestore start --host-port=0.0.0.0:8081
    ports:
      - "8081:8081"
    networks:
      - sticky-net

networks:
  sticky-net:
    driver: bridge
```

### 1.3 Create Source Directory Structure

Create the following directory structure with `__init__.py` files:

```
src/
├── __init__.py
├── main.py
├── exceptions.py
├── api/
│   ├── __init__.py
│   ├── routes.py
│   ├── middleware.py
│   └── schemas.py
├── detection/
│   ├── __init__.py
│   ├── detector.py
│   └── patterns.py
├── agents/
│   ├── __init__.py
│   ├── honeypot_agent.py
│   ├── persona.py
│   └── prompts.py
└── intelligence/
    ├── __init__.py
    └── extractor.py
```

#### src/__init__.py
```python
"""Sticky-Net: AI Agentic Honey-Pot System."""

__version__ = "0.1.0"
```

#### src/main.py (Minimal skeleton)
```python
"""FastAPI application entry point."""

from fastapi import FastAPI

from src.api.routes import router
from src.api.middleware import setup_middleware

app = FastAPI(
    title="Sticky-Net",
    description="AI Agentic Honey-Pot for Scam Detection",
    version="0.1.0",
)

setup_middleware(app)
app.include_router(router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
```

#### src/exceptions.py
```python
"""Custom exceptions for Sticky-Net."""


class StickyNetError(Exception):
    """Base exception for Sticky-Net."""

    pass


class ScamDetectionError(StickyNetError):
    """Error during scam detection."""

    pass


class AgentEngagementError(StickyNetError):
    """Error during agent engagement."""

    pass


class IntelligenceExtractionError(StickyNetError):
    """Error during intelligence extraction."""

    pass


class ConfigurationError(StickyNetError):
    """Configuration or environment error."""

    pass
```

### 1.4 Create Config Module

#### config/__init__.py
```python
"""Configuration module."""

from config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
```

#### config/settings.py
```python
"""Application settings using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API
    api_key: str
    port: int = 8080
    debug: bool = False

    # Google Cloud
    google_cloud_project: str
    google_cloud_location: str = "global"
    google_genai_use_vertexai: bool = True
    google_application_credentials: str | None = None

    # Firestore
    firestore_collection: str = "conversations"
    firestore_emulator_host: str | None = None

    # AI Models (Gemini 3)
    flash_model: str = "gemini-3-flash-preview"  # Fast classification
    pro_model: str = "gemini-3-pro-preview"      # Engagement responses
    llm_temperature: float = 0.7

    # Engagement Policy
    max_engagement_turns_cautious: int = 10
    max_engagement_turns_aggressive: int = 25
    max_engagement_duration_seconds: int = 600
    cautious_confidence_threshold: float = 0.60
    aggressive_confidence_threshold: float = 0.85


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### 1.5 Create Test Directory Structure

```
tests/
├── __init__.py
├── conftest.py
├── test_api.py
├── test_detection.py
├── test_agent.py
└── test_extractor.py
```

#### tests/conftest.py
```python
"""Pytest fixtures and configuration."""

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
```

### 1.6 Create README.md

```markdown
# Sticky-Net 🕸️

AI-powered honeypot system that detects scam messages and autonomously engages scammers to extract actionable intelligence.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- GCP Service Account (for Vertex AI & Firestore)

### Local Development

1. **Clone and setup environment:**
   ```bash
   git clone <repo-url>
   cd sticky-net
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Place GCP service account key:**
   ```bash
   mkdir -p secrets
   cp /path/to/service-account.json secrets/
   ```

3. **Run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

4. **Or run locally with Python:**
   ```bash
   pip install -e ".[dev]"
   uvicorn src.main:app --reload --port 8080
   ```

### API Usage

```bash
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "message": {
      "sender": "scammer",
      "text": "Your account is blocked. Send OTP now!",
      "timestamp": "2026-01-21T10:15:30Z"
    },
    "conversationHistory": [],
    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
  }'
```

### Running Tests

```bash
pytest --cov=src tests/
```

## Architecture

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for detailed architecture documentation.

## License

MIT
```

## Verification Checklist

- [ ] `pyproject.toml` created with all dependencies
- [ ] `.env.example` created with all required variables
- [ ] `.gitignore` properly configured
- [ ] `Dockerfile` builds successfully
- [ ] `docker-compose.yml` starts all services
- [ ] All `__init__.py` files created
- [ ] `src/main.py` skeleton runs without errors
- [ ] `config/settings.py` loads configuration
- [ ] `tests/conftest.py` fixtures defined
- [ ] `README.md` created with setup instructions
- [ ] Health check endpoint responds at `/health`

## Next Steps

After completing this milestone, proceed to **Milestone 2: API Layer** to implement the full API endpoints and request handling.
