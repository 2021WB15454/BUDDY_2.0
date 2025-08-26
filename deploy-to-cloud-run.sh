#!/bin/bash

echo "======================================"
echo "  BUDDY 2.0 - Firebase Cloud Run Deploy"
echo "======================================"
echo

echo "[1/6] Checking prerequisites..."
if ! command -v gcloud &> /dev/null; then
    echo "ERROR: Google Cloud CLI not found. Please install it first."
    echo "Download from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command -v firebase &> /dev/null; then
    echo "ERROR: Firebase CLI not found. Please install it first."
    echo "Run: npm install -g firebase-tools"
    exit 1
fi

echo "[2/6] Setting up Google Cloud project..."
gcloud config set project buddyai-42493
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to set Google Cloud project"
    exit 1
fi

echo "[3/6] Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to enable APIs"
    exit 1
fi

echo "[4/6] Building and deploying to Cloud Run..."
gcloud run deploy buddy-2-0 \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10

if [ $? -ne 0 ]; then
    echo "ERROR: Deployment failed"
    exit 1
fi

echo "[5/6] Setting environment variables..."
echo "Please set your environment variables in the Cloud Run console:"
echo "- MONGODB_URI"
echo "- OPENAI_API_KEY"
echo "- GOOGLE_APPLICATION_CREDENTIALS=/app/config/firebase-service-account.json"
echo
echo "Cloud Run Console: https://console.cloud.google.com/run"

echo "[6/6] Optional: Deploy frontend to Firebase Hosting..."
read -p "Deploy frontend to Firebase Hosting? (y/n): " deploy_frontend
if [[ $deploy_frontend == "y" || $deploy_frontend == "Y" ]]; then
    firebase deploy --only hosting
fi

echo
echo "======================================"
echo "  DEPLOYMENT COMPLETE! 🎉"
echo "======================================"
echo
echo "Your BUDDY 2.0 is now running on Cloud Run!"
echo "Check the Cloud Run console for your service URL."
echo
