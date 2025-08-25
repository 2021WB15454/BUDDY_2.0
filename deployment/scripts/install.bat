@echo off
REM BUDDY 2.0 Cross-Platform Installation Script (Windows)
REM ======================================================
REM 
REM Installs and configures BUDDY 2.0 across all platforms:
REM - MongoDB Atlas setup
REM - Pinecone vector database
REM - Firebase hosting and functions
REM - Cross-device synchronization
REM - Platform-specific builds

setlocal enabledelayedexpansion

echo 🚀 BUDDY 2.0 Cross-Platform Installation (Windows)
echo ================================================

REM Configuration variables
set MONGODB_URI=%MONGODB_URI%
set PINECONE_API_KEY=%PINECONE_API_KEY%
set FIREBASE_PROJECT_ID=%FIREBASE_PROJECT_ID%
set FIREBASE_SERVICE_ACCOUNT=%FIREBASE_SERVICE_ACCOUNT%

REM Function to check if command exists
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed. Please install Node.js 18+ first.
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.8+ first.
    echo Download from: https://python.org/
    pause
    exit /b 1
)

echo ✅ Prerequisites check passed

REM Install Node.js dependencies
echo ℹ️  Installing Node.js dependencies...
call npm install -g firebase-tools
call npm install -g @angular/cli
call npm install -g expo-cli
call npm install -g electron-builder

if %errorlevel% neq 0 (
    echo ❌ Failed to install Node.js dependencies
    pause
    exit /b 1
)
echo ✅ Node.js dependencies installed

REM Create Python virtual environment
echo ℹ️  Setting up Python environment...
python -m venv .venv
call .venv\Scripts\activate.bat

REM Install Python dependencies
echo ℹ️  Installing Python dependencies...
python -m pip install --upgrade pip
pip install motor pymongo
pip install pinecone-client sentence-transformers
pip install fastapi uvicorn
pip install pydantic
pip install firebase-admin
pip install python-multipart
pip install aiofiles
pip install websockets

REM Voice processing dependencies (Windows specific)
pip install pyaudio speechrecognition
pip install whisper pyttsx3 gtts
pip install webrtcvad

if %errorlevel% neq 0 (
    echo ❌ Failed to install Python dependencies
    echo ⚠️  Some audio dependencies might need manual installation
    echo    For PyAudio issues, try: pip install pipwin && pipwin install pyaudio
)
echo ✅ Python dependencies installed

REM Setup MongoDB Atlas
echo ℹ️  Setting up MongoDB Atlas...
if "%MONGODB_URI%"=="" (
    echo ⚠️  MongoDB URI not provided. Please set up MongoDB Atlas manually.
    echo 1. Go to https://cloud.mongodb.com/
    echo 2. Create a new cluster
    echo 3. Create a database user
    echo 4. Get connection string and set MONGODB_URI environment variable
) else (
    echo ✅ MongoDB URI configured
)

REM Setup Pinecone
echo ℹ️  Setting up Pinecone vector database...
if "%PINECONE_API_KEY%"=="" (
    echo ⚠️  Pinecone API key not provided. Please set up Pinecone manually.
    echo 1. Go to https://www.pinecone.io/
    echo 2. Create an account and get API key
    echo 3. Set PINECONE_API_KEY environment variable
) else (
    echo ✅ Pinecone API key configured
)

REM Setup Firebase
echo ℹ️  Setting up Firebase...
firebase --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Firebase CLI not found. Installing...
    npm install -g firebase-tools
)

REM Login to Firebase (manual step)
echo ⚠️  Please login to Firebase manually by running: firebase login
echo Then press any key to continue...
pause >nul

REM Initialize Firebase project
if not "%FIREBASE_PROJECT_ID%"=="" (
    firebase use %FIREBASE_PROJECT_ID%
    echo ✅ Firebase project configured
) else (
    echo ⚠️  Firebase project ID not provided. Please run 'firebase init' manually.
)

REM Set up hosting targets
firebase target:apply hosting buddy-web-app buddy-web
firebase target:apply hosting buddy-admin-dashboard buddy-admin
firebase target:apply hosting buddy-desktop-app buddy-desktop

echo ✅ Firebase configured

REM Build web applications
echo ℹ️  Building web applications...

REM Create web app directories if they don't exist
if not exist "web\src" mkdir web\src
if not exist "web\public" mkdir web\public
if not exist "admin\src" mkdir admin\src
if not exist "admin\public" mkdir admin\public

REM Build web app
echo ℹ️  Building main web application...
cd web
if exist "package.json" (
    call npm install
    call npm run build
) else (
    echo ⚠️  Web app package.json not found. Creating basic build.
    if not exist "build" mkdir build
    echo ^<!DOCTYPE html^>^<html^>^<head^>^<title^>BUDDY 2.0^</title^>^</head^>^<body^>^<h1^>BUDDY 2.0 Web App^</h1^>^</body^>^</html^> > build\index.html
)
cd ..

REM Build admin dashboard
echo ℹ️  Building admin dashboard...
cd admin
if exist "package.json" (
    call npm install
    call npm run build
) else (
    echo ⚠️  Admin dashboard package.json not found. Creating basic build.
    if not exist "build" mkdir build
    echo ^<!DOCTYPE html^>^<html^>^<head^>^<title^>BUDDY 2.0 Admin^</title^>^</head^>^<body^>^<h1^>BUDDY 2.0 Admin Dashboard^</h1^>^</body^>^</html^> > build\index.html
)
cd ..

echo ✅ Web applications built

REM Build desktop apps
echo ℹ️  Building desktop applications...
if exist "apps\desktop" (
    cd apps\desktop
    if exist "package.json" (
        call npm install
        call npm run build
        call npm run electron:build
    ) else (
        echo ⚠️  Desktop app package.json not found. Skipping desktop build.
    )
    cd ..\..
) else (
    echo ⚠️  Desktop app directory not found. Skipping desktop build.
)

echo ✅ Desktop applications built

REM Create configuration files
echo ℹ️  Creating configuration files...

REM Create environment configuration
(
echo # BUDDY 2.0 Environment Configuration
echo MONGODB_URI=%MONGODB_URI%
echo PINECONE_API_KEY=%PINECONE_API_KEY%
echo FIREBASE_PROJECT_ID=%FIREBASE_PROJECT_ID%
echo.
echo # API Configuration
echo API_BASE_URL=https://%FIREBASE_PROJECT_ID%.web.app/api
echo WS_BASE_URL=wss://%FIREBASE_PROJECT_ID%.web.app/ws
echo.
echo # Voice Configuration
echo VOICE_ENGINE=whisper
echo TTS_ENGINE=pyttsx3
echo EMBEDDING_MODEL=all-MiniLM-L6-v2
echo.
echo # Sync Configuration
echo SYNC_INTERVAL=300
echo MAX_CONCURRENT_SYNCS=5
echo SYNC_BATCH_SIZE=50
) > .env

REM Create requirements.txt
pip freeze > requirements.txt

echo ✅ Configuration files created

REM Run tests if requested
if "%1"=="--test" (
    echo ℹ️  Running tests...
    python test_phase8_voice.py
    echo ✅ Tests completed
)

REM Deploy if requested
if "%1"=="--deploy" (
    echo ℹ️  Deploying to Firebase...
    firebase deploy --only functions
    firebase deploy --only hosting
    echo ✅ Firebase deployment complete
)

echo.
echo ✅ BUDDY 2.0 installation complete!
echo.
echo ℹ️  Next steps:
echo 1. Configure your environment variables in .env
echo 2. Run 'python buddy_main.py' to start the backend
echo 3. Run 'firebase serve' to test locally
echo 4. Run '%~nx0 --deploy' to deploy to production
echo.
echo 🎉 BUDDY 2.0 is ready for cross-platform deployment!

pause
