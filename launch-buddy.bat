@echo off
REM BUDDY Quick Launcher
echo.
echo  🤖 BUDDY AI Assistant Launcher
echo  ==============================
echo.

REM Set default environment variables if not provided
if "%BUDDY_HOST%"=="" set BUDDY_HOST=localhost
if "%BUDDY_PORT%"=="" set BUDDY_PORT=8082
if "%BUDDY_API_PORT%"=="" set BUDDY_API_PORT=8081

REM Check if BUDDY API is running
curl -s http://%BUDDY_HOST%:%BUDDY_API_PORT%/health >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ BUDDY API is running at http://%BUDDY_HOST%:%BUDDY_API_PORT%
) else (
    echo 🚀 Starting BUDDY API server...
    cd /d "c:\Users\shrim\Documents\WASE_PROJECT\BUDDY_2.0"
    set BUDDY_ENV=atlas
    set PYTHONIOENCODING=utf-8
    start /b "BUDDY API" "C:/Users/shrim/Documents/WASE_PROJECT/BUDDY_2.0/.venv/Scripts/python.exe" -m packages.core.buddy.main --api-only --port %BUDDY_API_PORT%
    echo    Server starting in background...
    timeout /t 5 >nul
)

echo.
echo 🌐 Available interfaces:
echo    • API Endpoint: http://%BUDDY_HOST%:%BUDDY_API_PORT%
echo    • API Documentation: http://%BUDDY_HOST%:%BUDDY_API_PORT%/docs
echo    • Health Check: http://%BUDDY_HOST%:%BUDDY_API_PORT%/health
echo.

REM Check database status
echo 🗄️ Database Status:
cd /d "c:\Users\shrim\Documents\WASE_PROJECT\BUDDY_2.0\packages\core"
set BUDDY_ENV=atlas
"C:/Users/shrim/Documents/WASE_PROJECT/BUDDY_2.0/.venv/Scripts/python.exe" -c "
try:
    from buddy.database import MongoDBClient
    import asyncio
    async def check_db():
        try:
            db = MongoDBClient()
            await db.connect()
            print('    ✅ MongoDB Atlas connected and ready')
            await db.close()
        except Exception:
            print('    ⚠️  MongoDB Atlas not available (check connection)')
            print('    💡 BUDDY will use memory-only mode')
    asyncio.run(check_db())
except ImportError:
    print('    ⚠️  Database module not available')
"
echo.

REM Test BUDDY with a simple message
echo 💬 Testing BUDDY with a greeting...
powershell -Command "try { $response = Invoke-RestMethod -Uri 'http://%BUDDY_HOST%:%BUDDY_API_PORT%/chat' -Method POST -ContentType 'application/json' -Body ('{\"message\": \"Hello BUDDY!\"}' | ConvertTo-Json); Write-Host ('BUDDY Response: ' + $response.response) } catch { Write-Host 'Unable to test chat - API may still be starting' }"

echo.
echo 🎯 Quick Commands:
echo    • curl -X POST http://%BUDDY_HOST%:%BUDDY_API_PORT%/chat -H "Content-Type: application/json" -d "{\"message\": \"your message here\"}"
echo    • Open http://%BUDDY_HOST%:%BUDDY_API_PORT%/docs in browser for full API documentation
echo.
echo ✨ BUDDY is ready to assist you!
echo.
pause
