@echo off
echo 🚀 BUDDY Universal Core - Production Mode
echo ========================================
echo.

echo 🔍 Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker not found. Please install Docker Desktop.
    pause
    exit /b 1
)

echo ✅ Docker found!
echo.

echo 🐳 Building and starting BUDDY Core...
docker-compose -f docker-compose-simple.yml up -d --build

if errorlevel 1 (
    echo ❌ Deployment failed!
    pause
    exit /b 1
)

echo.
echo ⏳ Waiting for services to start...
timeout /t 15 /nobreak >nul

echo.
echo 📊 Service Status:
docker-compose -f docker-compose-simple.yml ps

echo.
echo 🌍 BUDDY Core is running at:
echo   • API: http://localhost:8000
echo   • Postgres: localhost:5433
echo   • ChromaDB: http://localhost:8001
echo.
echo 🧪 Test with:
echo   curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"text\":\"Hello BUDDY!\"}"
echo.
echo 🎉 BUDDY Universal Core deployed successfully!
pause
