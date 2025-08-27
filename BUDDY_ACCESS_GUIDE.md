# BUDDY 2.0 Access Guide

## Quick Chat Commands (Copy & Paste)

### Standard Chat
```powershell
# PowerShell
$response = Invoke-RestMethod -Uri "http://localhost:8082/chat" -Method POST -ContentType "application/json" -Body '{"message": "Hello BUDDY!", "user_id": "user123"}'
$response.response
```

### Cross-Platform Chat (Enhanced)
```powershell
# Mobile optimized
$response = Invoke-RestMethod -Uri "http://localhost:8082/chat/universal" -Method POST -ContentType "application/json" -Body '{"message": "What are your new capabilities?", "device_type": "mobile", "user_id": "user123"}'
$response.response

# Watch optimized (brief responses)
$response = Invoke-RestMethod -Uri "http://localhost:8082/chat/universal" -Method POST -ContentType "application/json" -Body '{"message": "Hello", "device_type": "watch", "user_id": "user123"}'
$response.response

# Car mode (safety optimized)
$response = Invoke-RestMethod -Uri "http://localhost:8082/chat/universal" -Method POST -ContentType "application/json" -Body '{"message": "How are you?", "device_type": "car", "user_id": "user123"}'
$response.response
```

### System Status
```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8082/health" -Method GET

# Performance metrics
Invoke-RestMethod -Uri "http://localhost:8082/system/intel-metrics" -Method GET
```

### Device Registration
```powershell
# Register a device
$deviceData = @{
    device_id = "my-laptop-001"
    device_type = "desktop"
    capabilities = @{
        screen_size = "large"
        has_camera = $true
    }
    user_id = "user123"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8082/devices/register" -Method POST -ContentType "application/json" -Body $deviceData
```

## cURL Commands (Alternative)

### Basic Chat
```bash
curl -X POST "http://localhost:8082/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello BUDDY!", "user_id": "user123"}'
```

### Universal Chat
```bash
curl -X POST "http://localhost:8082/chat/universal" \
     -H "Content-Type: application/json" \
     -d '{"message": "Test cross-platform", "device_type": "mobile", "user_id": "user123"}'
```

## Python Script Access
```python
import requests
import json

# Chat with BUDDY
def chat_with_buddy(message, device_type="web"):
    url = "http://localhost:8082/chat/universal"
    data = {
        "message": message,
        "device_type": device_type,
        "user_id": "python_user"
    }
    response = requests.post(url, json=data)
    return response.json()

# Example usage
result = chat_with_buddy("What's new in BUDDY 2.0?", "desktop")
print(result['response'])
```

## Available Endpoints
- `GET /` - Welcome page
- `GET /health` - System status
- `POST /chat` - Standard chat
- `POST /chat/universal` - Cross-platform chat
- `GET /system/intel-metrics` - Performance metrics
- `POST /devices/register` - Device registration
- `GET /docs` - API documentation
