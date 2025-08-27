# BUDDY Universal Deployment - PowerShell Script
# Reliable deployment for Windows PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   BUDDY Universal Deployment Manager" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "Checking Docker installation..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

# Check Docker Compose
Write-Host "Checking Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker-compose --version
    Write-Host "✅ Docker Compose found: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose not found." -ForegroundColor Red
    exit 1
}

# Check if Docker daemon is running
Write-Host "Checking Docker daemon..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "✅ Docker daemon is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker daemon not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🚀 Starting BUDDY Core deployment..." -ForegroundColor Cyan

# Deploy services
Write-Host "Building and starting services..." -ForegroundColor Yellow
try {
    docker-compose up -d --build
    Write-Host "✅ Services started successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Deployment failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "⏳ Waiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Check service status
Write-Host "📊 Service Status:" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "🏥 Checking service health..." -ForegroundColor Yellow

# Test health endpoint
$maxRetries = 10
$retryCount = 0
$healthOk = $false

while ($retryCount -lt $maxRetries -and -not $healthOk) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ BUDDY Core health check passed!" -ForegroundColor Green
            $healthOk = $true
        }
    } catch {
        $retryCount++
        Write-Host "Attempt $retryCount/$maxRetries - waiting for service..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }
}

if (-not $healthOk) {
    Write-Host "❌ Health check failed. Checking logs..." -ForegroundColor Red
    docker-compose logs buddy-core
    exit 1
}

Write-Host ""
Write-Host "🎉 BUDDY Core deployed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Access Points:" -ForegroundColor Cyan
Write-Host "   🌐 API Documentation: http://localhost:8000/docs" -ForegroundColor White
Write-Host "   💚 Health Status: http://localhost:8000/health" -ForegroundColor White
Write-Host "   📊 Service Status: docker-compose ps" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Management Commands:" -ForegroundColor Cyan
Write-Host "   📊 Status: docker-compose ps" -ForegroundColor White
Write-Host "   📝 Logs: docker-compose logs" -ForegroundColor White
Write-Host "   🛑 Stop: docker-compose down" -ForegroundColor White
Write-Host ""

# Test API endpoint
Write-Host "🧪 Testing API connectivity..." -ForegroundColor Yellow
try {
    $testData = @{
        device_id = "test-powershell-device"
        device_name = "PowerShell Test"
        device_type = "desktop"
        platform = "windows"
    } | ConvertTo-Json
    
    $headers = @{"Content-Type" = "application/json"}
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/devices/register" -Method POST -Body $testData -Headers $headers -UseBasicParsing
    
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Device registration test passed!" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ API test failed: $_" -ForegroundColor Yellow
    Write-Host "   This is normal on first startup - services may still be initializing" -ForegroundColor Gray
}

Write-Host ""
Write-Host "🚀 BUDDY Universal System is ready!" -ForegroundColor Green
Write-Host ""
