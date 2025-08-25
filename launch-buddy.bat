@echo off
REM BUDDY Quick Launcher
echo.
echo  🤖 BUDDY AI Assistant Launcher
echo  ==============================
echo.

REM Check if BUDDY API is running
curl -s http://localhost:8080/health >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ BUDDY API is running at http://localhost:8080
) else (
    echo 🚀 Starting BUDDY API server...
    cd /d "c:\Users\shrim\Documents\WASE_PROJECT\BUDDY_2.0\packages\core"
    start /b "BUDDY API" "C:/Users/shrim/Documents/WASE_PROJECT/BUDDY_2.0/.venv/Scripts/python.exe" -m buddy.main --api-only --port 8080
    echo    Server starting in background...
    timeout /t 3 >nul
)

echo.
echo 🌐 Available interfaces:
echo    • API Endpoint: http://localhost:8080
echo    • API Documentation: http://localhost:8080/docs
echo    • Health Check: http://localhost:8080/health
echo.

REM Check database status
echo 🗄️ Database Status:
cd /d "c:\Users\shrim\Documents\WASE_PROJECT\BUDDY_2.0\packages\core"
"C:/Users/shrim/Documents/WASE_PROJECT/BUDDY_2.0/.venv/Scripts/python.exe" -c "
try:
    from buddy.database import MongoDBClient
    import asyncio
    async def check_db():
        try:
            db = MongoDBClient()
            await db.connect()
            print('    ✅ MongoDB connected and ready')
            await db.close()
        except Exception:
            print('    ⚠️  MongoDB not available (BUDDY will use memory-only mode)')
            print('    💡 To enable persistence, install MongoDB from:')
            print('       https://www.mongodb.com/try/download/community')
    asyncio.run(check_db())
except ImportError:
    print('    ⚠️  Database module not available')
"
echo.

REM Test BUDDY with a simple message
echo 💬 Testing BUDDY with a greeting...
powershell -Command "try { $response = Invoke-RestMethod -Uri 'http://localhost:8080/chat' -Method POST -ContentType 'application/json' -Body ('{\"message\": \"Hello BUDDY!\"}' | ConvertTo-Json); Write-Host ('BUDDY Response: ' + $response.response) } catch { Write-Host 'Unable to test chat - API may still be starting' }"

echo.
echo 🎯 Quick Commands:
echo    • curl -X POST http://localhost:8080/chat -H "Content-Type: application/json" -d "{\"message\": \"your message here\"}"
echo    • Open http://localhost:8080/docs in browser for full API documentation
echo.
echo ✨ BUDDY is ready to assist you!
echo.
pause
