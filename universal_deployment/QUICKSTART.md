# BUDDY Universal - Quick Start Guide

## 🚀 Instant Deployment (Windows)

### Prerequisites
1. **Docker Desktop** - Download from https://docker.com/products/docker-desktop
2. **Python 3.8+** - For testing scripts (optional)

### One-Command Deployment

```cmd
cd universal_deployment
deploy.bat deploy
```

That's it! The script will:
- ✅ Check prerequisites
- ✅ Create configuration file
- ✅ Build and start all services
- ✅ Verify health checks
- ✅ Show you access URLs

## 📋 Quick Commands

```cmd
# Deploy the system
deploy.bat deploy

# Check system status
deploy.bat status

# Test connectivity
deploy.bat test

# View logs
deploy.bat logs

# Stop services
deploy.bat stop

# Clean restart
deploy.bat stop
deploy.bat deploy
```

## 🔗 Access Points

After deployment, access these URLs:

- **API Documentation**: http://localhost:8000/docs
- **Health Status**: http://localhost:8000/health
- **ChromaDB**: http://localhost:8001
- **Core API**: http://localhost:8000/api/v1/

## 🔧 Configuration

Edit `.env` file to customize:

```env
# Database
POSTGRES_DB=buddydb
POSTGRES_USER=buddy
POSTGRES_PASSWORD=your-secure-password

# Security
JWT_SECRET=your-jwt-secret-key
ENCRYPTION_KEY=your-32-char-encryption-key

# AI Services
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

## 📱 Client Integration

### Python Client
```python
from client_examples.python_client import BuddyClient
import asyncio

async def main():
    client = BuddyClient("http://localhost:8000")
    
    # Register device
    await client.register_device(
        device_id="my-device",
        device_name="My Computer",
        device_type="desktop"
    )
    
    # Send message
    response = await client.send_message("Hello BUDDY!")
    print(f"BUDDY: {response['response']}")

asyncio.run(main())
```

### JavaScript Client
```javascript
import { BuddyClient } from './client_examples/javascript_client.js';

const client = new BuddyClient('http://localhost:8000');

// Register device
await client.registerDevice({
    deviceId: 'web-app',
    deviceName: 'Web Application',
    deviceType: 'web'
});

// Send message
const response = await client.sendMessage('Hello BUDDY!');
console.log('BUDDY:', response.response);
```

## 🔄 Cross-Device Sync

### Automatic Synchronization
- **Memory**: Conversations, tasks, preferences sync automatically
- **Real-time**: WebSocket connections for instant updates
- **Conflict Resolution**: Last-write-wins with timestamp tracking

### Manual Sync
```python
# Force sync specific device
await client.sync_device("device-id")

# Get sync status
status = await client.get_sync_status()
```

## 🏥 Health Monitoring

### Check System Health
```cmd
deploy.bat test
```

### Manual Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "database": "connected",
    "redis": "connected",
    "services": {
        "chat": "running",
        "sync": "running",
        "tasks": "running"
    }
}
```

## 🐛 Troubleshooting

### Common Issues

**1. Docker not running**
```
❌ Docker is not running. Please start Docker Desktop.
```
**Solution**: Start Docker Desktop application

**2. Port conflicts**
```
ERROR: Port 8000 is already in use
```
**Solution**: 
```cmd
deploy.bat stop
# Wait a moment
deploy.bat deploy
```

**3. Service health check fails**
```
❌ BUDDY Core health check failed
```
**Solution**: Check logs and restart
```cmd
deploy.bat logs buddy-core
deploy.bat restart
```

### Debug Commands

```cmd
# View all logs
deploy.bat logs

# View specific service logs
deploy.bat logs buddy-core
deploy.bat logs postgres
deploy.bat logs redis

# Check service status
deploy.bat status

# Full cleanup and redeploy
deploy.bat cleanup
deploy.bat deploy
```

## 📦 Production Deployment

### Environment Variables
```env
# Production settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security
CORS_ORIGINS=https://yourdomain.com
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem

# Scale settings
BUDDY_CORE_REPLICAS=3
MAX_CONNECTIONS=1000
```

### Production Command
```cmd
deploy.bat deploy production
```

## 🔄 Updates and Maintenance

### Update System
```cmd
# Stop services
deploy.bat stop

# Pull latest changes
git pull origin main

# Redeploy
deploy.bat deploy
```

### Backup Data
```cmd
deploy.bat backup
```

### Restore Data
```cmd
# Stop services
deploy.bat stop

# Restore from backup
docker-compose exec postgres psql -U buddy -d buddydb < backups/buddy_backup_YYYYMMDD_HHMMSS.sql

# Start services
deploy.bat deploy
```

## 🌐 Cloud Deployment

### Railway.app
1. Connect GitHub repository
2. Set environment variables
3. Deploy from `universal_deployment` folder

### Render.com
1. Create new Web Service
2. Connect repository
3. Set build command: `docker-compose up`
4. Configure environment variables

### AWS/GCP/Azure
Use the provided `Dockerfile` and `docker-compose.yml` with your container orchestration platform.

## 🤝 Support

If you encounter issues:

1. **Check logs**: `deploy.bat logs`
2. **Test connectivity**: `deploy.bat test`
3. **Review configuration**: Check `.env` file
4. **Clean restart**: `deploy.bat cleanup && deploy.bat deploy`

## 🎯 Next Steps

1. **Customize AI Models**: Edit `core_server.py` to integrate your preferred AI services
2. **Add Platforms**: Extend client SDKs for smartwatch, car, TV platforms
3. **Scale Up**: Configure load balancing and multiple replicas
4. **Monitor**: Add logging and monitoring dashboards
5. **Security**: Configure SSL certificates and authentication

---

**Ready to make BUDDY truly universal? Start with `deploy.bat deploy`!** 🚀
