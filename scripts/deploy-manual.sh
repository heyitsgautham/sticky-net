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