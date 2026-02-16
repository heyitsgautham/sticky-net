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