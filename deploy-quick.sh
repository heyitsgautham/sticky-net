#!/bin/bash
# Quick deploy to Cloud Run

set -e

echo "🚀 Deploying to Cloud Run..."

gcloud run deploy sticky-net \
  --image gcr.io/sticky-net-485205/sticky-net:latest \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=sticky-net-485205,VERTEX_AI_LOCATION=asia-south1,FIRESTORE_COLLECTION=conversations,LLM_MODEL=gemini-3-flash-preview,ENVIRONMENT=production,DEBUG=false" \
  --set-secrets "API_KEY=sticky-net-api-key:latest" \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 60s \
  --concurrency 80

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Test the /simple endpoint:"
echo "curl -X POST https://sticky-net-140367184766.asia-south1.run.app/api/v1/simple \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'x-api-key: test-api-key' \\"
echo "  -d '{\"message\":{\"sender\":\"scammer\",\"text\":\"test\",\"timestamp\":\"2026-02-04T10:15:30Z\"}}'"
