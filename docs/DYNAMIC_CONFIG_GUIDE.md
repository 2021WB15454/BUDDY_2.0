# BUDDY 2.0 Dynamic Configuration Guide

## Overview

BUDDY 2.0 now uses dynamic configuration with environment variables to eliminate hardcoded ports and enable flexible deployment across different devices and environments.

## Environment Variables

### Core Backend
- `BUDDY_HOST`: Backend server host (default: localhost)
- `BUDDY_PORT`: Main backend port (default: 8082)
- `BUDDY_SYNC_PORT`: Cross-device sync port (default: 8083)
- `BUDDY_API_PORT`: Legacy API port (default: 8081)

### Frontend/Client
- `REACT_APP_BUDDY_HOST`: Frontend host variable
- `REACT_APP_BUDDY_PORT`: Frontend port variable
- `REACT_APP_BACKEND_URL`: Complete backend URL override

### Security
- `CLIENT_TOKEN`: Shared secret for REST/WebSocket authentication
- `ADMIN_API_KEY`: Admin API access key

## Deployment Scenarios

### 1. Local Development
```bash
# Default localhost setup
BUDDY_HOST=localhost
BUDDY_PORT=8082
BUDDY_SYNC_PORT=8083
```

### 2. LAN Access
```bash
# Enable access from other devices on same network
BUDDY_HOST=0.0.0.0  # Listen on all interfaces
BUDDY_PORT=8082
# Mobile devices connect to: http://192.168.1.100:8082
```

### 3. Production Server
```bash
# Production with domain
BUDDY_HOST=0.0.0.0
BUDDY_PORT=80
REACT_APP_BUDDY_HOST=your-domain.com
REACT_APP_BUDDY_PORT=80
REACT_APP_BACKEND_URL=https://your-domain.com
```

### 4. Docker Deployment
```yaml
# docker-compose.yml
services:
  buddy-backend:
    environment:
      - BUDDY_HOST=0.0.0.0
      - BUDDY_PORT=8082
    ports:
      - "8082:8082"
```

## Platform-Specific Configuration

### Python Backend
Uses `dynamic_config.py` utilities:
```python
from dynamic_config import get_host, get_port, get_http_base
```

### React Native Mobile
Uses `config.ts`:
```typescript
const API_BASE = process.env.REACT_APP_BACKEND_URL || 
  `http://${process.env.REACT_APP_BUDDY_HOST || 'localhost'}:${process.env.REACT_APP_BUDDY_PORT || '8082'}`;
```

### Flutter Mobile
Uses Dart compile-time defines:
```bash
flutter run --dart-define=BUDDY_HOST=192.168.1.100 --dart-define=BUDDY_PORT=8082
```

### Web Interfaces
Uses JavaScript environment detection:
```javascript
function getApiUrl() {
  const host = window.BUDDY_HOST || 'localhost';
  const port = window.BUDDY_PORT || '8082';
  return `http://${host}:${port}`;
}
```

## Setting Environment Variables

### Windows (PowerShell)
```powershell
$env:BUDDY_HOST="192.168.1.100"
$env:BUDDY_PORT="8082"
python enhanced_backend.py
```

### Windows (Command Prompt)
```cmd
set BUDDY_HOST=192.168.1.100
set BUDDY_PORT=8082
python enhanced_backend.py
```

### Linux/macOS
```bash
export BUDDY_HOST=192.168.1.100
export BUDDY_PORT=8082
python enhanced_backend.py
```

### .env File
```bash
# Create .env file in project root
BUDDY_HOST=localhost
BUDDY_PORT=8082
BUDDY_SYNC_PORT=8083
CLIENT_TOKEN=your-secret-token
```

## Mobile Development

### React Native Development
```bash
# Set environment variables for Metro bundler
export REACT_APP_BUDDY_HOST=192.168.1.100
export REACT_APP_BUDDY_PORT=8082
npx react-native start
```

### Flutter Development
```bash
# Pass configuration at runtime
flutter run \
  --dart-define=BUDDY_HOST=192.168.1.100 \
  --dart-define=BUDDY_PORT=8082
```

## Cross-Device Testing

### Same Network Testing
1. Start backend with network access:
   ```bash
   export BUDDY_HOST=0.0.0.0
   export BUDDY_PORT=8082
   python enhanced_backend.py
   ```

2. Find your IP address:
   - Windows: `ipconfig`
   - Linux/macOS: `ifconfig` or `ip addr`

3. Configure mobile apps to use your IP:
   ```bash
   # Example: Your computer IP is 192.168.1.100
   export REACT_APP_BUDDY_HOST=192.168.1.100
   ```

### Remote Testing
1. Use ngrok or similar tunneling service
2. Set REACT_APP_BACKEND_URL to tunnel URL
3. Configure backend for external access

## Troubleshooting

### Connection Issues
1. Check firewall settings
2. Verify environment variables:
   ```bash
   echo $BUDDY_HOST $BUDDY_PORT
   ```
3. Test connectivity:
   ```bash
   curl http://$BUDDY_HOST:$BUDDY_PORT/health
   ```

### Mobile Connection Issues
1. Ensure mobile device on same network
2. Use IP address, not localhost
3. Check that backend binds to 0.0.0.0
4. Verify ports are not blocked

### Environment Variables Not Working
1. Restart application after setting variables
2. Check variable names (case-sensitive)
3. Verify .env file location and format
4. Use absolute paths when necessary

## Files Updated for Dynamic Configuration

- `dynamic_config.py` - Central configuration utilities
- `enhanced_backend.py` - Main backend server
- `minimal_backend.py` - Minimal backend variant
- `buddy_main.py` - Main launcher
- `apps/mobile/src/config.ts` - React Native config
- `apps/mobile_flutter/lib/core/config.dart` - Flutter config
- `buddy_web_interface.html` - Web interface
- `diagnostic.py` - Diagnostic tools
- `quick_test_buddy.py` - Test scripts
- `.env.example` - Environment template

## Security Considerations

- Never commit .env files with real credentials
- Use strong CLIENT_TOKEN values in production
- Consider HTTPS for production deployments
- Implement proper authentication for admin endpoints
- Use environment-specific configurations
