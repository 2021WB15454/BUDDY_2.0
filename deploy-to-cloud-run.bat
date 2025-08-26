@echo off
echo ======================================
echo   BUDDY 2.0 - Firebase Cloud Run Deploy
echo ======================================
echo.

echo [1/6] Checking prerequisites...
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Google Cloud CLI not found. Please install it first.
    echo Download from: https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

where firebase >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Firebase CLI not found. Please install it first.
    echo Run: npm install -g firebase-tools
    pause
    exit /b 1
)

echo [2/6] Setting up Google Cloud project...
gcloud config set project buddyai-42493
if %errorlevel% neq 0 (
    echo ERROR: Failed to set Google Cloud project
    pause
    exit /b 1
)

echo [3/6] Enabling required APIs...
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
if %errorlevel% neq 0 (
    echo ERROR: Failed to enable APIs
    pause
    exit /b 1
)

echo [4/6] Building and deploying to Cloud Run...
gcloud run deploy buddy-2-0 --source . --platform managed --region us-central1 --allow-unauthenticated --port 8080 --memory 1Gi --cpu 1 --timeout 300 --max-instances 10
if %errorlevel% neq 0 (
    echo ERROR: Deployment failed
    pause
    exit /b 1
)

echo [5/6] Setting environment variables...
echo Please set your environment variables in the Cloud Run console:
echo - MONGODB_URI
echo - OPENAI_API_KEY
echo - GOOGLE_APPLICATION_CREDENTIALS=/app/config/firebase-service-account.json
echo.
echo Cloud Run Console: https://console.cloud.google.com/run

echo [6/6] Optional: Deploy frontend to Firebase Hosting...
set /p deploy_frontend="Deploy frontend to Firebase Hosting? (y/n): "
if /i "%deploy_frontend%"=="y" (
    firebase deploy --only hosting
)

echo.
echo ======================================
echo   DEPLOYMENT COMPLETE! 🎉
echo ======================================
echo.
echo Your BUDDY 2.0 is now running on Cloud Run!
echo Check the Cloud Run console for your service URL.
echo.
pause
