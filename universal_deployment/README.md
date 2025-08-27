# BUDDY Universal Deployment

🚀 **Production-grade BUDDY Core with cross-device memory synchronization**

This deployment provides a complete universal BUDDY system that can serve all devices (mobile, desktop, watch, car, TV) with synchronized memory and real-time communication.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   BUDDY Core    │    │   Databases     │
│                 │    │                 │    │                 │
│ • Mobile Apps   │◄──►│ • FastAPI       │◄──►│ • PostgreSQL    │
│ • Desktop Apps  │    │ • WebSockets    │    │ • ChromaDB      │
│ • Web Apps      │    │ • REST API      │    │ • Redis Cache   │
│ • Watch Apps    │    │ • Background    │    │                 │
│ • Car Systems   │    │   Sync Tasks    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📦 Components

- **BUDDY Core**: FastAPI server with WebSocket support
- **PostgreSQL**: Structured data (conversations, tasks, user profiles)
- **ChromaDB**: Vector embeddings for semantic memory
- **Redis**: Real-time caching and pub/sub
- **Nginx**: Load balancing and SSL termination

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 4GB+ RAM
- Port 8000, 80, 443 available

### 1. Clone and Setup
```bash
cd universal_deployment
cp .env.example .env  # Edit with your settings
```

### 2. Start BUDDY Core
```bash
docker-compose up -d
```

### 3. Verify Installation
```bash
# Check services
docker-compose ps

# Test API
curl http://localhost:8000/health

# View logs
docker-compose logs buddy-core
```

## 🔌 Client Integration

### Python Client
```python
from client_examples.python_client import BuddyClient

client = BuddyClient(
    base_url="http://localhost:8000",
    device_name="My Python App",
    device_type="desktop"
)

await client.connect()
response = await client.send_message("Hello BUDDY!")
```

### JavaScript/Web Client
```javascript
import BuddyClient from './client_examples/javascript_client.js';

const client = new BuddyClient({
    baseUrl: 'http://localhost:8000',
    deviceName: 'My Web App',
    deviceType: 'web'
});

await client.connect();
const response = await client.sendMessage('Hello BUDDY!');
```

### React Hook
```jsx
function MyComponent() {
    const { isConnected, sendMessage, messages } = useBuddy({
        deviceName: 'React App'
    });

    const handleSend = async () => {
        await sendMessage('Hello from React!');
    };

    return (
        <div>
            <p>Status: {isConnected ? 'Connected' : 'Disconnected'}</p>
            <button onClick={handleSend}>Send Message</button>
        </div>
    );
}
```

## 📱 Device Installation Guides

### Desktop (Windows/macOS/Linux)
```bash
# Install Python client
pip install buddy-sdk
buddy-client --connect http://your-server:8000
```

### Mobile (Android)
```kotlin
// Add to build.gradle
implementation 'com.buddy:sdk-android:1.0.0'

// Initialize
val client = BuddyClient.Builder()
    .baseUrl("http://your-server:8000")
    .deviceName("My Android App")
    .build()

client.connect()
```

### Mobile (iOS)
```swift
// Add to Package.swift
.package(url: "https://github.com/buddy/ios-sdk", from: "1.0.0")

// Initialize
let client = BuddyClient(
    baseURL: "http://your-server:8000",
    deviceName: "My iOS App"
)

await client.connect()
```

### Web Applications
```html
<script src="https://cdn.buddy.ai/sdk/1.0/buddy.min.js"></script>
<script>
const client = new BuddyClient({
    baseUrl: 'http://your-server:8000',
    deviceName: 'Web Browser'
});
</script>
```

## 🔄 Memory Synchronization

BUDDY automatically synchronizes data across all devices:

### Real-time Sync
- **WebSocket connections** for instant updates
- **Message broadcasting** to all user devices
- **Conflict resolution** with timestamp-based merging

### Data Types Synced
- **Conversations**: Chat history and context
- **Tasks**: Reminders and to-dos
- **Preferences**: User settings and personalization
- **Context**: Session state and memory

### Sync Flow Example
```
1. User sends message on Phone
   ↓
2. Message stored in PostgreSQL
   ↓
3. Embedding created in ChromaDB
   ↓
4. WebSocket notification sent to all devices
   ↓
5. Desktop, Watch, Car receive update instantly
```

## 🛠️ API Endpoints

### Core APIs
```http
# Health check
GET /health

# Register device
POST /api/v1/devices/register

# Send chat message
POST /api/v1/chat

# Create task
POST /api/v1/tasks

# Sync data
POST /api/v1/sync

# WebSocket connection
WS /ws/{user_id}
```

### Example API Usage
```bash
# Register device
curl -X POST http://localhost:8000/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "my-device-123",
    "device_name": "My Device",
    "device_type": "mobile",
    "platform": "android"
  }'

# Send message
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello BUDDY!",
    "device_id": "my-device-123"
  }'
```

## 🏭 Production Deployment

### Environment Variables
```bash
# Core settings
DATABASE_URL=postgresql://user:pass@host:5432/buddydb
REDIS_URL=redis://host:6379/0
JWT_SECRET=your-secure-secret

# External APIs
OPENAI_API_KEY=sk-...

# Scaling
SYNC_INTERVAL=30
WORKERS=4
```

### Docker Compose Production
```yaml
# Use production docker-compose.prod.yml
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment
```bash
# Deploy to Kubernetes
kubectl apply -f k8s/
```

### Cloud Providers

#### Railway
```bash
railway login
railway init
railway up
```

#### Render
```bash
# Connect your GitHub repo
# Set environment variables in dashboard
# Deploy automatically on push
```

#### Heroku
```bash
heroku container:push web
heroku container:release web
```

## 📊 Monitoring & Analytics

### Metrics Endpoint
```bash
curl http://localhost:8000/metrics
```

### Grafana Dashboard
```bash
# Import dashboard from config/grafana-dashboard.json
```

### Logs
```bash
# View structured logs
docker-compose logs -f buddy-core

# Search logs
docker-compose logs buddy-core | grep "ERROR"
```

## 🔐 Security

### Authentication
- JWT tokens for API access
- Device registration and verification
- User session management

### Data Protection
- PostgreSQL encryption at rest
- HTTPS/WSS for all communications
- Input validation and sanitization

### Network Security
- Nginx rate limiting
- CORS configuration
- IP whitelisting for admin endpoints

## 🚀 Scaling

### Horizontal Scaling
```yaml
# Scale BUDDY Core instances
docker-compose up -d --scale buddy-core=3
```

### Database Scaling
```yaml
# Add read replicas
postgres-read-replica:
  image: postgres:15-alpine
  environment:
    POSTGRES_MASTER_SERVICE: postgres
```

### Caching Strategy
- Redis for session storage
- HTTP caching with Nginx
- Application-level caching

## 🔧 Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn core_server:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run tests
pytest tests/

# Load testing
hey -n 1000 -c 10 http://localhost:8000/api/v1/chat
```

### Contributing
1. Fork the repository
2. Create feature branch
3. Add tests
4. Submit pull request

## 📚 Documentation

- **API Docs**: http://localhost:8000/docs
- **WebSocket Protocol**: [ws-protocol.md](docs/ws-protocol.md)
- **Client SDKs**: [client-sdks.md](docs/client-sdks.md)
- **Deployment Guide**: [deployment.md](docs/deployment.md)

## 🆘 Support

### Common Issues

**Connection refused**
```bash
# Check if services are running
docker-compose ps

# Check logs
docker-compose logs
```

**Database connection error**
```bash
# Reset database
docker-compose down -v
docker-compose up -d
```

**WebSocket connection failed**
```bash
# Check nginx configuration
docker-compose logs nginx
```

### Getting Help
- GitHub Issues: [Report bugs](https://github.com/buddy/core/issues)
- Discord: [Join community](https://discord.gg/buddy)
- Email: support@buddy.ai

---

🎉 **Congratulations!** You now have a production-grade universal BUDDY system that synchronizes seamlessly across all devices. Users can start conversations on their phone, continue on desktop, get notifications on their watch, and have BUDDY respond in their car - all with perfect memory synchronization.
