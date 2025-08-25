# MongoDB Integration Guide for BUDDY

## Overview

BUDDY now includes comprehensive MongoDB integration for persistent conversation storage, user profiles, skill analytics, and more. The database integration is **optional** - BUDDY will work perfectly fine without MongoDB, but enabling it provides enhanced features like conversation history, user preferences, and analytics.

## Features

✅ **Conversation Persistence**: All chat history saved automatically  
✅ **User Profiles**: Personalized settings and preferences  
✅ **Skill Analytics**: Track skill usage and performance  
✅ **Device Management**: Multi-device sync and status tracking  
✅ **Memory System**: Long-term and short-term memory storage  
✅ **Async Operations**: Non-blocking database operations  
✅ **Auto-Reconnection**: Handles connection failures gracefully  

## Quick Start

### Option 1: Local MongoDB (Recommended for Development)

1. **Download MongoDB Community Edition**
   ```
   https://www.mongodb.com/try/download/community
   ```

2. **Install MongoDB**
   - Windows: Run the installer and choose "Complete" installation
   - Include MongoDB Compass (GUI tool) for easy database management

3. **Start MongoDB Service**
   - Windows: Open Services → Start "MongoDB" service
   - Or run: `net start MongoDB`

4. **Test Database Connection**
   ```bash
   cd packages/core
   python init_database.py
   ```

5. **Start BUDDY** (database will be auto-detected)
   ```bash
   ./launch-buddy.bat
   ```

### Option 2: MongoDB Atlas (Cloud Database)

1. **Create Free Account**
   ```
   https://www.mongodb.com/atlas
   ```

2. **Create a Cluster** (M0 Sandbox - Free tier)

3. **Get Connection String**
   - Click "Connect" → "Connect your application"
   - Copy the connection string

4. **Configure BUDDY**
   ```yaml
   # config/database.yml
   production:
     mongodb:
       host: cluster0.xxxxx.mongodb.net
       database: buddy_ai
       username: your_username
       password: your_password
       ssl: true
   ```

## Database Schema

### Collections Created

| Collection | Purpose | Example Documents |
|------------|---------|------------------|
| `conversations` | Chat history and context | User conversations, turns, metadata |
| `users` | User profiles and preferences | Settings, statistics, device list |
| `skill_executions` | Skill usage analytics | Execution logs, performance metrics |
| `devices` | Connected device information | Device status, capabilities, sync data |
| `memories` | Long/short-term memory storage | Facts, preferences, learned information |

### Indexes for Performance

- Conversations: `user_id`, `created_at`, `conversation_id`
- Users: `user_id`, `last_seen`
- Skills: `skill_name`, `executed_at`, `user_id`
- Devices: `device_id`, `user_id`, `last_seen`
- Memories: `user_id`, `memory_type`, `expires_at`

## Configuration

### Database Settings (`config/database.yml`)

```yaml
# Development (default)
development:
  mongodb:
    host: localhost
    port: 27017
    database: buddy_ai_dev

# Production  
production:
  mongodb:
    host: ${MONGODB_HOST}
    port: ${MONGODB_PORT}
    database: ${MONGODB_DATABASE}
    username: ${MONGODB_USERNAME}
    password: ${MONGODB_PASSWORD}
    ssl: true
    connection_pool_size: 20
```

### Environment Variables

```bash
MONGODB_HOST=your-cluster.mongodb.net
MONGODB_PORT=27017
MONGODB_DATABASE=buddy_ai
MONGODB_USERNAME=your_username
MONGODB_PASSWORD=your_password
```

## Usage Examples

### Programmatic Access

```python
from buddy.database import MongoDBClient
from buddy.database.repository import ConversationRepository

# Initialize
db_client = MongoDBClient()
await db_client.connect()

# Use repositories
conv_repo = ConversationRepository(db_client)

# Save conversation
conversation = await conv_repo.create_conversation(
    user_id="user123",
    title="AI Discussion", 
    device_id="desktop"
)

# Add message
await conv_repo.add_turn(
    conversation.conversation_id,
    user_message="Hello BUDDY!",
    assistant_message="Hello! How can I help you today?"
)

# Search conversations
recent = await conv_repo.get_recent_conversations("user123", limit=10)
```

### Repository Operations

```python
# User management
user_repo = UserRepository(db_client)
user = await user_repo.create_user("user123", {"name": "John", "timezone": "UTC"})
await user_repo.update_preferences("user123", {"voice": "female", "speed": "normal"})

# Skill analytics
skill_repo = SkillRepository(db_client)
await skill_repo.log_execution("weather", "user123", success=True, duration=1.2)
stats = await skill_repo.get_skill_analytics("weather", days=30)

# Memory system
memory_repo = MemoryRepository(db_client)
await memory_repo.store_memory("user123", "preference", "likes classical music")
memories = await memory_repo.get_memories("user123", memory_type="preference")
```

## Monitoring and Maintenance

### Health Monitoring

```python
# Check database health
health = await db_client.health_check()
print(health)
# {'status': 'healthy', 'response_time_ms': 12, 'collections': 5}

# Get database statistics
stats = await db_client.get_database_stats()
print(f"Database size: {stats.get('dataSize', 0)} bytes")
```

### MongoDB Compass (GUI)

1. Open MongoDB Compass
2. Connect to `mongodb://localhost:27017`
3. Browse the `buddy_ai` database
4. View collections, documents, and indexes
5. Run queries and analyze data

### Backup and Restore

```bash
# Backup
mongodump --db buddy_ai --out backup/

# Restore
mongorestore --db buddy_ai backup/buddy_ai/
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   Error: No connection could be made
   ```
   - Solution: Ensure MongoDB service is running
   - Windows: `net start MongoDB`

2. **Authentication Failed**
   ```
   Error: Authentication failed
   ```
   - Solution: Check username/password in config
   - Verify user has read/write permissions

3. **Database Not Found**
   ```
   Error: Database 'buddy_ai' not found
   ```
   - Solution: Database created automatically on first write
   - Run `init_database.py` to initialize

### Performance Optimization

1. **Index Optimization**
   ```python
   # Indexes are created automatically, but you can add custom ones:
   await db_client.database.conversations.create_index([("custom_field", 1)])
   ```

2. **Connection Pooling**
   ```yaml
   mongodb:
     connection_pool_size: 20  # Adjust based on load
     timeout_ms: 10000        # Connection timeout
   ```

3. **Query Optimization**
   ```python
   # Use projections to limit returned fields
   conversations = await conv_repo.find_conversations(
       {"user_id": "user123"},
       projection={"title": 1, "created_at": 1}  # Only return these fields
   )
   ```

## Advanced Features

### Aggregation Pipelines

```python
# Get conversation statistics
pipeline = [
    {"$match": {"user_id": "user123"}},
    {"$group": {
        "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
        "conversation_count": {"$sum": 1},
        "total_turns": {"$sum": {"$size": "$turns"}}
    }},
    {"$sort": {"_id": 1}}
]

stats = await conv_repo.aggregate(pipeline)
```

### Custom Repositories

```python
from buddy.database.repository import BaseRepository

class CustomRepository(BaseRepository):
    def __init__(self, db_client):
        super().__init__(db_client, "custom_collection")
    
    async def custom_operation(self, user_id: str):
        return await self.collection.find_one({"user_id": user_id})
```

## Migration and Upgrades

The database schema is designed to be backward compatible. Future updates will include migration scripts in `packages/core/migrations/`.

## Security Considerations

1. **Authentication**: Always use username/password for production
2. **SSL/TLS**: Enable SSL for Atlas or production deployments  
3. **Network Security**: Restrict database access to BUDDY servers only
4. **Data Encryption**: MongoDB supports encryption at rest and in transit
5. **Access Control**: Create dedicated database users with minimal permissions

## Support

- **MongoDB Documentation**: https://docs.mongodb.com/
- **BUDDY Issues**: Report database-related issues in the project repository
- **MongoDB Community**: https://community.mongodb.com/
- **Atlas Support**: Available for paid Atlas clusters

---

🎉 **You're all set!** BUDDY now has enterprise-grade database capabilities for persistent conversations, user management, and analytics. The system gracefully handles database unavailability, so you can develop with or without MongoDB as needed.
