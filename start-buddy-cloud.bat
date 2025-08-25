@echo off
echo ========================================
echo 🤖 BUDDY 2.0 - AI Assistant Startup
echo ========================================
echo.

echo 📡 Starting BUDDY Backend with Cloud Database...
cd /d "C:\Users\shrim\Documents\WASE_PROJECT\BUDDY_2.0"

echo 🔧 Loading environment...
if not exist ".env" (
    echo ❌ Error: .env file not found!
    echo Please ensure .env file exists with MongoDB configuration.
    pause
    exit /b 1
)

echo 🚀 Starting Backend Server...
start "BUDDY Backend" cmd /k "C:\Users\shrim\Documents\WASE_PROJECT\BUDDY_2.0\.venv\Scripts\python.exe enhanced_backend.py"

echo ⏳ Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo 🌐 Starting Web Interface...
start "BUDDY Web" cmd /k "C:\Users\shrim\Documents\WASE_PROJECT\BUDDY_2.0\.venv\Scripts\python.exe buddy_web_server.py"

echo ⏳ Waiting for web server to start...
timeout /t 3 /nobreak >nul

echo.
echo ✅ BUDDY 2.0 is starting up!
echo.
echo 📊 Backend API: http://localhost:8082
echo 🌐 Web Interface: http://localhost:3000
echo 💾 Database: MongoDB Atlas (Cloud)
echo.
echo 🔧 To stop BUDDY: Close all command windows
echo 📝 Logs: Check the opened command windows
echo.
echo 🎉 BUDDY is ready to assist you!
pause
