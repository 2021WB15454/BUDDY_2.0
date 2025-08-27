@echo off
echo BUDDY Deployment Status Check > deployment_status.txt
echo ========================== >> deployment_status.txt
echo. >> deployment_status.txt

echo Checking Docker... >> deployment_status.txt
docker --version >> deployment_status.txt 2>&1
if errorlevel 1 (
    echo ERROR: Docker not found >> deployment_status.txt
    goto end
)

echo. >> deployment_status.txt
echo Checking Docker Compose... >> deployment_status.txt
docker-compose --version >> deployment_status.txt 2>&1

echo. >> deployment_status.txt
echo Starting Docker Compose deployment... >> deployment_status.txt
docker-compose up -d --build >> deployment_status.txt 2>&1

echo. >> deployment_status.txt
echo Waiting 10 seconds for services to start... >> deployment_status.txt
timeout /t 10 /nobreak >nul

echo. >> deployment_status.txt
echo Service Status: >> deployment_status.txt
docker-compose ps >> deployment_status.txt 2>&1

echo. >> deployment_status.txt
echo Testing health endpoint... >> deployment_status.txt
curl -s http://localhost:8000/health >> deployment_status.txt 2>&1

echo. >> deployment_status.txt
echo Deployment check completed! >> deployment_status.txt
echo Check deployment_status.txt for details >> deployment_status.txt

:end
echo Deployment status written to deployment_status.txt
