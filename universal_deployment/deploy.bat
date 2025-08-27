@echo off
REM BUDDY Universal Deployment - Windows Script
REM Easy deployment and management for Windows users

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ========================================
echo   BUDDY Universal Deployment Manager
echo ========================================
echo.

if "%1"=="" (
    goto show_help
)

if "%1"=="deploy" goto deploy
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="status" goto status
if "%1"=="logs" goto logs
if "%1"=="test" goto test
if "%1"=="cleanup" goto cleanup
if "%1"=="backup" goto backup
if "%1"=="help" goto show_help

goto show_help

:deploy
echo 🚀 Deploying BUDDY Core system...
echo.

REM Check if .env file exists
if not exist ".env" (
    if exist ".env.example" (
        echo 📋 Creating .env file from template...
        copy ".env.example" ".env" >nul
        echo ✅ .env file created. Please edit it with your configuration.
        echo    Then run: deploy.bat deploy
        goto end
    ) else (
        echo ❌ No .env.example file found
        goto end
    )
)

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker not found. Please install Docker Desktop.
    goto end
)

REM Check Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose not found. Please install Docker Compose.
    goto end
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop.
    goto end
)

echo ✅ Prerequisites check passed
echo.

echo 🔧 Building and starting services...
docker-compose up -d --build
if errorlevel 1 (
    echo ❌ Deployment failed
    goto end
)

echo.
echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

echo.
echo 🏥 Checking service health...
python -c "
import requests
import time
import sys

services = [
    ('BUDDY Core', 'http://localhost:8000/health'),
    ('ChromaDB', 'http://localhost:8001/api/v1/heartbeat'),
]

for name, url in services:
    print(f'Checking {name}...')
    for i in range(15):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f'✅ {name} is healthy')
                break
        except:
            pass
        time.sleep(2)
    else:
        print(f'❌ {name} health check failed')
        sys.exit(1)
print('✅ All services are healthy')
"

if errorlevel 1 (
    echo.
    echo ❌ Some services failed health checks. Showing logs:
    docker-compose logs
    goto end
)

echo.
echo 🎉 BUDDY Core deployed successfully!
echo.
echo 📋 Quick Start:
echo    API Docs: http://localhost:8000/docs
echo    Health: http://localhost:8000/health
echo    ChromaDB: http://localhost:8001
echo.
echo 🔧 Management Commands:
echo    Status: deploy.bat status
echo    Logs: deploy.bat logs
echo    Test: deploy.bat test
echo    Stop: deploy.bat stop
echo.
goto end

:stop
echo 🛑 Stopping BUDDY Core services...
docker-compose down
echo ✅ Services stopped
goto end

:restart
echo 🔄 Restarting BUDDY Core services...
docker-compose restart
echo ✅ Services restarted
goto end

:status
echo 📊 Service Status:
docker-compose ps
goto end

:logs
if "%2"=="" (
    docker-compose logs
) else (
    docker-compose logs %2
)
goto end

:test
echo 🧪 Testing BUDDY Core connectivity...
python -c "
import requests
import json

try:
    # Test health
    response = requests.get('http://localhost:8000/health', timeout=10)
    if response.status_code == 200:
        print('✅ Health check passed')
        data = response.json()
        print(f'   Database: {data.get(\"database\", \"unknown\")}')
        print(f'   Redis: {data.get(\"redis\", \"unknown\")}')
    
    # Test device registration
    device_data = {
        'device_id': 'test-windows-device',
        'device_name': 'Windows Test Device',
        'device_type': 'desktop',
        'platform': 'windows'
    }
    
    response = requests.post(
        'http://localhost:8000/api/v1/devices/register',
        json=device_data,
        timeout=10
    )
    
    if response.status_code == 200:
        print('✅ Device registration test passed')
    else:
        print(f'❌ Device registration failed: {response.status_code}')
    
    # Test chat
    chat_data = {
        'text': 'Hello BUDDY! Windows deployment test.',
        'device_id': 'test-windows-device'
    }
    
    response = requests.post(
        'http://localhost:8000/api/v1/chat',
        json=chat_data,
        timeout=10
    )
    
    if response.status_code == 200:
        print('✅ Chat endpoint test passed')
        chat_response = response.json()
        print(f'   Response: {chat_response.get(\"response\", \"No response\")}')
    else:
        print(f'❌ Chat test failed: {response.status_code}')
    
    print('')
    print('✅ All tests passed! BUDDY Core is working correctly.')
    
except Exception as e:
    print(f'❌ Test failed: {e}')
    exit(1)
"
goto end

:cleanup
echo 🧹 Cleaning up BUDDY Core deployment...
docker-compose down -v --remove-orphans
echo ✅ Cleanup completed
goto end

:backup
echo 💾 Creating database backup...
if not exist "backups" mkdir backups
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do if not "%%I"=="" set datetime=%%I
set backup_file=backups\buddy_backup_%datetime:~0,8%_%datetime:~8,6%.sql
docker-compose exec -T postgres pg_dump -U buddy buddydb > "%backup_file%"
echo ✅ Backup created: %backup_file%
goto end

:show_help
echo Usage: deploy.bat [command]
echo.
echo Commands:
echo   deploy   - Deploy BUDDY Core system
echo   stop     - Stop all services
echo   restart  - Restart all services
echo   status   - Show service status
echo   logs     - Show service logs
echo   test     - Test system connectivity
echo   cleanup  - Remove all containers and volumes
echo   backup   - Backup database
echo   help     - Show this help
echo.
echo Examples:
echo   deploy.bat deploy     # Deploy the system
echo   deploy.bat status     # Check status
echo   deploy.bat test       # Test connectivity
echo   deploy.bat stop       # Stop services
echo.
goto end

:end
echo.
pause
