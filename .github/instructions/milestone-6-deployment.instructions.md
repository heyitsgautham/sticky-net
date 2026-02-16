---
applyTo: "**"
---

# Milestone 6: Deployment

> **Goal**: Containerize the application and deploy to Google Cloud Run with CI/CD pipeline.

## Prerequisites

- Milestones 1-5 completed
- All tests passing
- Google Cloud project with:
  - Cloud Run API enabled
  - Vertex AI API enabled
  - Firestore in Native mode
  - Service account with appropriate permissions

## Tasks

### 6.1 Finalize Dockerfile

#### Dockerfile (production-optimized)

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache .

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 6.2 Configure Docker Compose for Development

#### docker-compose.yml

```yaml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - API_KEY=${API_KEY:-dev-api-key}
      - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
      - VERTEX_AI_LOCATION=${VERTEX_AI_LOCATION:-global}
      - FIRESTORE_COLLECTION=${FIRESTORE_COLLECTION:-conversations}
      - LLM_MODEL=${LLM_MODEL:-gemini-3-flash-preview}
      - LLM_TEMPERATURE=${LLM_TEMPERATURE:-0.7}
      - MAX_ENGAGEMENT_TURNS=${MAX_ENGAGEMENT_TURNS:-50}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - ENVIRONMENT=development
    volumes:
      # Mount code for hot reload in development
      - ./src:/app/src:ro
      - ./config:/app/config:ro
      # Mount service account key
      - ${GOOGLE_APPLICATION_CREDENTIALS:-./secrets/service-account.json}:/app/secrets/service-account.json:ro
    env_file:
      - .env
    command: ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # Optional: Local Firestore emulator for testing
  firestore-emulator:
    image: gcr.io/google.com/cloudsdktool/cloud-sdk:emulators
    ports:
      - "8085:8085"
    environment:
      - FIRESTORE_PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-demo-project}
    command: >
      gcloud emulators firestore start
      --host-port=0.0.0.0:8085
      --project=${GOOGLE_CLOUD_PROJECT:-demo-project}
    profiles:
      - emulator

networks:
  default:
    name: sticky-net
```

### 6.3 Create CI/CD Pipeline

#### .github/workflows/ci.yml

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"
  REGISTRY: gcr.io
  IMAGE_NAME: ${{ secrets.GCP_PROJECT_ID }}/sticky-net

jobs:
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: |
          uv venv
          source .venv/bin/activate
          uv pip install -e ".[dev]"

      - name: Run Ruff linter
        run: |
          source .venv/bin/activate
          ruff check src/ tests/

      - name: Run Ruff formatter check
        run: |
          source .venv/bin/activate
          ruff format --check src/ tests/

      - name: Run type checking
        run: |
          source .venv/bin/activate
          mypy src/ --ignore-missing-imports

  test:
    name: Run Tests
    runs-on: ubuntu-latest
    needs: lint

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: |
          uv venv
          source .venv/bin/activate
          uv pip install -e ".[dev]"

      - name: Run tests with coverage
        run: |
          source .venv/bin/activate
          pytest tests/ -v --cov=src --cov-report=xml --cov-report=term-missing

      - name: Upload coverage report
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false

  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push'

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: ${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    name: Deploy to Cloud Run
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    environment: production

    permissions:
      contents: read
      id-token: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}

      - name: Configure Docker for GCR
        run: gcloud auth configure-docker

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy sticky-net \
            --image ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            --platform managed \
            --region ${{ secrets.GCP_REGION }} \
            --allow-unauthenticated \
            --set-env-vars "GOOGLE_CLOUD_PROJECT=${{ secrets.GCP_PROJECT_ID }}" \
            --set-env-vars "VERTEX_AI_LOCATION=${{ secrets.GCP_REGION }}" \
            --set-env-vars "FIRESTORE_COLLECTION=conversations" \
            --set-env-vars "LLM_MODEL=gemini-3-flash-preview" \
            --set-env-vars "ENVIRONMENT=production" \
            --set-secrets "API_KEY=sticky-net-api-key:latest" \
            --memory 1Gi \
            --cpu 1 \
            --min-instances 0 \
            --max-instances 10 \
            --timeout 300s \
            --concurrency 80

      - name: Get Cloud Run URL
        run: |
          URL=$(gcloud run services describe sticky-net \
            --platform managed \
            --region ${{ secrets.GCP_REGION }} \
            --format 'value(status.url)')
          echo "Deployed to: $URL"
          echo "SERVICE_URL=$URL" >> $GITHUB_ENV
```

### 6.4 Create Cloud Run Configuration

#### cloudbuild.yaml (Alternative to GitHub Actions)

```yaml
# For Google Cloud Build instead of GitHub Actions
steps:
  # Run tests
  - name: "python:3.11-slim"
    entrypoint: bash
    args:
      - -c
      - |
        pip install uv
        uv venv
        source .venv/bin/activate
        uv pip install -e ".[dev]"
        pytest tests/ -v

  # Build container
  - name: "gcr.io/cloud-builders/docker"
    args: ["build", "-t", "gcr.io/$PROJECT_ID/sticky-net:$COMMIT_SHA", "."]

  # Push container
  - name: "gcr.io/cloud-builders/docker"
    args: ["push", "gcr.io/$PROJECT_ID/sticky-net:$COMMIT_SHA"]

  # Deploy to Cloud Run
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk"
    entrypoint: gcloud
    args:
      - run
      - deploy
      - sticky-net
      - --image=gcr.io/$PROJECT_ID/sticky-net:$COMMIT_SHA
      - --platform=managed
      - --region=$_REGION
      - --allow-unauthenticated
      - --set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT_ID
      - --set-env-vars=VERTEX_AI_LOCATION=$_REGION
      - --set-secrets=API_KEY=sticky-net-api-key:latest

substitutions:
  _REGION: global

images:
  - "gcr.io/$PROJECT_ID/sticky-net:$COMMIT_SHA"

timeout: "1200s"
```

### 6.5 GCP Setup Scripts

#### scripts/setup-gcp.sh

```bash
#!/bin/bash
# Setup script for Google Cloud resources

set -e

# Configuration
PROJECT_ID="${1:-$(gcloud config get-value project)}"
REGION="${2:-global}"
SERVICE_ACCOUNT_NAME="sticky-net-sa"

echo "🚀 Setting up GCP resources for project: $PROJECT_ID"

# Enable required APIs
echo "📦 Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    aiplatform.googleapis.com \
    firestore.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    --project="$PROJECT_ID"

# Create service account
echo "👤 Creating service account..."
gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
    --display-name="Sticky-Net Service Account" \
    --project="$PROJECT_ID" 2>/dev/null || echo "Service account already exists"

SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant permissions
echo "🔐 Granting permissions..."
for ROLE in \
    "roles/aiplatform.user" \
    "roles/datastore.user" \
    "roles/secretmanager.secretAccessor" \
    "roles/logging.logWriter"
do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$ROLE" \
        --quiet
done

# Create API key secret
echo "🔑 Creating API key secret..."
API_KEY=$(openssl rand -hex 32)
echo -n "$API_KEY" | gcloud secrets create sticky-net-api-key \
    --data-file=- \
    --project="$PROJECT_ID" 2>/dev/null || \
    echo -n "$API_KEY" | gcloud secrets versions add sticky-net-api-key \
        --data-file=- \
        --project="$PROJECT_ID"

echo "API Key (save this!): $API_KEY"

# Initialize Firestore
echo "🔥 Setting up Firestore..."
gcloud firestore databases create \
    --location="$REGION" \
    --project="$PROJECT_ID" 2>/dev/null || echo "Firestore already initialized"

# Create service account key for local development
echo "📝 Creating service account key..."
mkdir -p secrets
gcloud iam service-accounts keys create secrets/service-account.json \
    --iam-account="$SA_EMAIL" \
    --project="$PROJECT_ID"

echo ""
echo "✅ GCP setup complete!"
echo ""
echo "Next steps:"
echo "1. Add secrets to GitHub repository:"
echo "   - GCP_PROJECT_ID: $PROJECT_ID"
echo "   - GCP_REGION: $REGION"
echo "   - WIF_PROVIDER: (Set up Workload Identity Federation)"
echo "   - WIF_SERVICE_ACCOUNT: $SA_EMAIL"
echo ""
echo "2. Update .env file with:"
echo "   GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo "   VERTEX_AI_LOCATION=$REGION"
echo "   GOOGLE_APPLICATION_CREDENTIALS=./secrets/service-account.json"
```

#### scripts/deploy-manual.sh

```bash
#!/bin/bash
# Manual deployment script (without CI/CD)

set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}"
REGION="${VERTEX_AI_LOCATION:-global}"
IMAGE_TAG="${1:-latest}"

echo "🚀 Deploying Sticky-Net to Cloud Run..."

# Build and push
echo "📦 Building Docker image..."
docker build -t "gcr.io/$PROJECT_ID/sticky-net:$IMAGE_TAG" .

echo "⬆️ Pushing to GCR..."
docker push "gcr.io/$PROJECT_ID/sticky-net:$IMAGE_TAG"

# Deploy
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy sticky-net \
    --image "gcr.io/$PROJECT_ID/sticky-net:$IMAGE_TAG" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
    --set-env-vars "VERTEX_AI_LOCATION=$REGION" \
    --set-env-vars "FIRESTORE_COLLECTION=conversations" \
    --set-env-vars "LLM_MODEL=gemini-3-flash-preview" \
    --set-env-vars "ENVIRONMENT=production" \
    --set-secrets "API_KEY=sticky-net-api-key:latest" \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10

# Get URL
URL=$(gcloud run services describe sticky-net \
    --platform managed \
    --region "$REGION" \
    --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "🌐 Service URL: $URL"
echo ""
echo "Test with:"
echo "curl -X POST $URL/api/v1/analyze \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'x-api-key: YOUR_API_KEY' \\"
echo "  -d '{\"message\": {\"sender\": \"scammer\", \"text\": \"Test message\"}}'"
```

### 6.6 Production Configuration Updates

#### config/settings.py (add production settings)

```python
"""Configuration management with production settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # API Configuration
    api_key: str = "dev-api-key"
    port: int = 8080
    environment: str = "development"  # development, staging, production

    # Google Cloud
    google_cloud_project: str = ""
    vertex_ai_location: str = "global"
    google_application_credentials: str = ""

    # Firestore
    firestore_collection: str = "conversations"

    # LLM Configuration
    llm_model: str = "gemini-3-flash-preview"
    llm_temperature: float = 0.7
    max_output_tokens: int = 256

    # Agent Configuration
    max_engagement_turns: int = 50
    engagement_timeout_seconds: int = 300

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or console

    # Rate Limiting (production)
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

## Verification Checklist

- [ ] Dockerfile builds successfully: `docker build -t sticky-net .`
- [ ] Docker Compose runs locally: `docker-compose up`
- [ ] Health endpoint responds: `curl http://localhost:8080/health`
- [ ] CI pipeline passes lint, test, and build stages
- [ ] GCP resources created (APIs, service account, Firestore)
- [ ] API key secret created in Secret Manager
- [ ] Cloud Run deployment succeeds
- [ ] Production endpoint responds with valid API key

## Local Development Workflow

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your values

# 2. Run with Docker Compose
docker-compose up --build

# 3. Test the API
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key" \
  -d '{
    "message": {
      "sender": "scammer",
      "text": "Your account is blocked! Send OTP to 9876543210 or pay Rs 500 to verify@upi"
    }
  }'

# 4. Run tests
docker-compose exec api pytest tests/ -v

# 5. View logs
docker-compose logs -f api
```

## Production Deployment Workflow

```bash
# Option 1: Via GitHub Actions (recommended)
# Push to main branch -> automatic deployment

# Option 2: Manual deployment
./scripts/setup-gcp.sh your-project-id global
./scripts/deploy-manual.sh

# Option 3: Via Cloud Build
gcloud builds submit --config cloudbuild.yaml
```

## Monitoring & Observability

### Cloud Run Metrics

```bash
# View recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sticky-net" \
  --limit 50 \
  --format "table(timestamp, jsonPayload.message)"

# View error logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sticky-net AND severity>=ERROR" \
  --limit 20
```

### Set Up Alerts (optional)

```bash
# Create alert for high error rate
gcloud monitoring channels create \
  --display-name="Email Alerts" \
  --type=email \
  --email-address="alerts@yourdomain.com"

# Create uptime check
gcloud monitoring uptime-check-configs create sticky-net-uptime \
  --display-name="Sticky-Net Health Check" \
  --host="YOUR_CLOUD_RUN_URL" \
  --path="/health" \
  --http-check
```

## Rollback Procedure

```bash
# List revisions
gcloud run revisions list --service sticky-net --region global

# Rollback to previous revision
gcloud run services update-traffic sticky-net \
  --to-revisions=sticky-net-PREVIOUS_REVISION=100 \
  --region global
```

## Cost Optimization

- **Min instances**: Set to 0 for pay-per-use (cold starts ~2-3s)
- **Max instances**: Limit based on budget
- **Memory**: Start with 512MB, increase if needed
- **CPU**: 1 CPU is sufficient for most workloads
- **Firestore**: Use batch operations to reduce costs

## Security Checklist

- [ ] API key stored in Secret Manager (not in code)
- [ ] Service account has minimal required permissions
- [ ] Firestore security rules configured
- [ ] Cloud Run allows only HTTPS
- [ ] No credentials in Docker image or logs
- [ ] Rate limiting enabled in production

## Complete! 🎉

With this milestone complete, you have a fully functional, production-ready AI honeypot system deployed on Google Cloud Run.
