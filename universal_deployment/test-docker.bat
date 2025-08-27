@echo off
echo ========================================
echo   Docker Installation Verification
echo ========================================
echo.

echo Checking Docker installation...
docker --version
if errorlevel 1 (
    echo ❌ Docker not found. Please install Docker Desktop first.
    echo    Download from: https://www.docker.com/products/docker-desktop/
    goto end
)

echo ✅ Docker found!
echo.

echo Checking Docker Compose...
docker-compose --version
if errorlevel 1 (
    echo ❌ Docker Compose not found
    goto end
)

echo ✅ Docker Compose found!
echo.

echo Checking if Docker daemon is running...
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker daemon is not running. Please start Docker Desktop.
    goto end
)

echo ✅ Docker daemon is running!
echo.

echo Testing Docker with hello-world...
docker run --rm hello-world
if errorlevel 1 (
    echo ❌ Docker test failed
    goto end
)

echo.
echo 🎉 Docker installation is complete and working!
echo.
echo Ready to deploy BUDDY:
echo    deploy.bat deploy
echo.

:end
pause
