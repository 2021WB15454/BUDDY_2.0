"""
BUDDY 2.0 MongoDB Atlas Database Manager
======================================

Production-ready MongoDB Atlas integration with:
- Multi-tenant data isolation
- Cross-device synchronization
- Conflict resolution
- Performance optimization
- Connection pooling and reliability
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
import json

# MongoDB dependencies (install with: pip install motor pymongo)
try:
    import motor.motor_asyncio
    from pymongo import IndexModel, TEXT, ASCENDING, DESCENDING
    from pymongo.errors import DuplicateKeyError, ConnectionFailure
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("⚠️ MongoDB not available. Install with: pip install motor pymongo")

from .mongodb_schemas import (
    UserSchema, DeviceSchema, ConversationSchema, ConversationSessionSchema,
    SyncOperationSchema, Collections, DatabaseIndexes, MONGODB_SCHEMAS,
    MessageType, DeviceType, SyncStatus, SyncOperationType
)

logger = logging.getLogger(__name__)


class BuddyMongoManager:
    """
    BUDDY 2.0 MongoDB Atlas Database Manager
    
    Handles all database operations with multi-tenant isolation,
    cross-device synchronization, and production-grade reliability.
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        database_name: str = "buddy_production",
        max_pool_size: int = 50,
        min_pool_size: int = 10,
        max_idle_time_ms: int = 30000
    ):
        self.connection_string = connection_string or os.getenv("MONGODB_URI")
        self.database_name = database_name
        self.client = None
        self.database = None
        
        # Connection pool settings
        self.connection_options = {
            "maxPoolSize": max_pool_size,
            "minPoolSize": min_pool_size,
            "maxIdleTimeMS": max_idle_time_ms,
            "retryWrites": True,
            "w": "majority",
            "readPreference": "primary",
            "readConcern": {"level": "majority"}
        }
        
        # Collection references
        self.collections = {}
        
    async def initialize(self) -> bool:
        """Initialize MongoDB connection and setup collections"""
        try:
            if not MONGODB_AVAILABLE:
                logger.error("MongoDB client not available")
                return False
            
            if not self.connection_string:
                logger.error("MongoDB connection string not provided")
                return False
            
            # Create MongoDB client
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                self.connection_string,
                **self.connection_options
            )
            
            # Get database reference
            self.database = self.client[self.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB Atlas")
            
            # Initialize collections
            await self._setup_collections()
            
            # Create indexes
            await self._create_indexes()
            
            logger.info("✅ MongoDB database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB: {e}")
            return False
    
    async def _setup_collections(self):
        """Setup collection references and validation"""
        try:
            # Get collection references
            for collection_name in [Collections.USERS, Collections.DEVICES, 
                                  Collections.CONVERSATIONS, Collections.SESSIONS, 
                                  Collections.SYNC_OPERATIONS]:
                self.collections[collection_name] = self.database[collection_name]
            
            # Create collections with schema validation
            for collection_name, schema in MONGODB_SCHEMAS.items():
                try:
                    await self.database.create_collection(
                        collection_name,
                        validator=schema
                    )
                except Exception:
                    # Collection might already exist
                    pass
            
            logger.info("✅ Collections setup complete")
            
        except Exception as e:
            logger.error(f"Error setting up collections: {e}")
            raise
    
    async def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            # Users collection indexes
            users_indexes = [
                IndexModel([("user_id", ASCENDING)], unique=True),
                IndexModel([("email", ASCENDING)], unique=True),
                IndexModel([("last_active", DESCENDING)]),
                IndexModel([("subscription.tier", ASCENDING), ("subscription.expires_at", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)])
            ]
            await self.collections[Collections.USERS].create_indexes(users_indexes)
            
            # Devices collection indexes
            devices_indexes = [
                IndexModel([("user_id", ASCENDING), ("device_id", ASCENDING)], unique=True),
                IndexModel([("user_id", ASCENDING), ("is_active", ASCENDING), ("last_sync", DESCENDING)]),
                IndexModel([("device_type", ASCENDING), ("platform", ASCENDING)]),
                IndexModel([("last_seen", DESCENDING)]),
                IndexModel([("is_primary", ASCENDING), ("user_id", ASCENDING)])
            ]
            await self.collections[Collections.DEVICES].create_indexes(devices_indexes)
            
            # Conversations collection indexes
            conversations_indexes = [
                IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("user_id", ASCENDING), ("session_id", ASCENDING), ("timestamp", ASCENDING)]),
                IndexModel([("sync_version", ASCENDING), ("user_id", ASCENDING)]),
                IndexModel([("device_id", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("vector_id", ASCENDING)], sparse=True),
                IndexModel([("content", TEXT), ("metadata.intent", TEXT)]),
                IndexModel([("user_id", ASCENDING), ("message_type", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("sync_status", ASCENDING), ("last_modified", DESCENDING)])
            ]
            await self.collections[Collections.CONVERSATIONS].create_indexes(conversations_indexes)
            
            # Sessions collection indexes
            sessions_indexes = [
                IndexModel([("user_id", ASCENDING), ("started_at", DESCENDING)]),
                IndexModel([("session_id", ASCENDING)], unique=True),
                IndexModel([("user_id", ASCENDING), ("device_id", ASCENDING), ("last_activity", DESCENDING)]),
                IndexModel([("ended_at", ASCENDING)], sparse=True, expireAfterSeconds=2592000)  # 30 days
            ]
            await self.collections[Collections.SESSIONS].create_indexes(sessions_indexes)
            
            # Sync operations collection indexes
            sync_indexes = [
                IndexModel([("user_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)]),
                IndexModel([("source_device_id", ASCENDING), ("status", ASCENDING)]),
                IndexModel([("target_device_id", ASCENDING), ("status", ASCENDING)]),
                IndexModel([("batch_id", ASCENDING)], sparse=True),
                IndexModel([("scheduled_at", ASCENDING)], sparse=True),
                IndexModel([("completed_at", ASCENDING)], sparse=True, expireAfterSeconds=604800)  # 7 days
            ]
            await self.collections[Collections.SYNC_OPERATIONS].create_indexes(sync_indexes)
            
            logger.info("✅ Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            raise
    
    # User Management
    async def create_user(self, user_data: UserSchema) -> bool:
        """Create a new user"""
        try:
            await self.collections[Collections.USERS].insert_one(
                user_data.dict(by_alias=True)
            )
            logger.info(f"✅ Created user: {user_data.user_id}")
            return True
            
        except DuplicateKeyError:
            logger.warning(f"User already exists: {user_data.user_id}")
            return False
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    async def get_user(self, user_id: str) -> Optional[UserSchema]:
        """Get user by ID"""
        try:
            user_doc = await self.collections[Collections.USERS].find_one(
                {"user_id": user_id}
            )
            
            if user_doc:
                return UserSchema(**user_doc)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user data"""
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)
            
            result = await self.collections[Collections.USERS].update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    # Device Management
    async def register_device(self, device_data: DeviceSchema) -> bool:
        """Register a new device"""
        try:
            # Check user's device limit
            user = await self.get_user(device_data.user_id)
            if not user:
                logger.error(f"User not found: {device_data.user_id}")
                return False
            
            # Count existing devices
            device_count = await self.collections[Collections.DEVICES].count_documents({
                "user_id": device_data.user_id,
                "is_active": True
            })
            
            if device_count >= user.subscription.max_devices:
                logger.warning(f"Device limit reached for user: {device_data.user_id}")
                return False
            
            await self.collections[Collections.DEVICES].insert_one(
                device_data.dict(by_alias=True)
            )
            
            logger.info(f"✅ Registered device: {device_data.device_id}")
            return True
            
        except DuplicateKeyError:
            # Device already exists, update last_seen
            await self.collections[Collections.DEVICES].update_one(
                {"user_id": device_data.user_id, "device_id": device_data.device_id},
                {"$set": {"last_seen": datetime.now(timezone.utc)}}
            )
            return True
        except Exception as e:
            logger.error(f"Error registering device: {e}")
            return False
    
    async def get_user_devices(self, user_id: str, active_only: bool = True) -> List[DeviceSchema]:
        """Get all devices for a user"""
        try:
            filter_query = {"user_id": user_id}
            if active_only:
                filter_query["is_active"] = True
            
            devices = []
            async for device_doc in self.collections[Collections.DEVICES].find(
                filter_query
            ).sort("last_seen", DESCENDING):
                devices.append(DeviceSchema(**device_doc))
            
            return devices
            
        except Exception as e:
            logger.error(f"Error getting devices for user {user_id}: {e}")
            return []
    
    async def update_device_sync(self, user_id: str, device_id: str) -> bool:
        """Update device last sync time"""
        try:
            result = await self.collections[Collections.DEVICES].update_one(
                {"user_id": user_id, "device_id": device_id},
                {
                    "$set": {
                        "last_sync": datetime.now(timezone.utc),
                        "last_seen": datetime.now(timezone.utc)
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating device sync: {e}")
            return False
    
    # Conversation Management
    async def save_conversation(self, conversation: ConversationSchema) -> bool:
        """Save a conversation message"""
        try:
            await self.collections[Collections.CONVERSATIONS].insert_one(
                conversation.dict(by_alias=True)
            )
            
            # Update session last activity
            await self.collections[Collections.SESSIONS].update_one(
                {"session_id": conversation.session_id},
                {
                    "$set": {"last_activity": datetime.now(timezone.utc)},
                    "$inc": {"message_count": 1}
                }
            )
            
            logger.debug(f"Saved conversation: {conversation._id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return False
    
    async def get_conversations(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        device_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ConversationSchema]:
        """Get conversations with filtering"""
        try:
            filter_query = {"user_id": user_id}
            
            if session_id:
                filter_query["session_id"] = session_id
            if device_id:
                filter_query["device_id"] = device_id
            
            conversations = []
            async for conv_doc in self.collections[Collections.CONVERSATIONS].find(
                filter_query
            ).sort("timestamp", DESCENDING).skip(offset).limit(limit):
                conversations.append(ConversationSchema(**conv_doc))
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return []
    
    async def search_conversations(
        self,
        user_id: str,
        search_text: str,
        limit: int = 20
    ) -> List[ConversationSchema]:
        """Full-text search in conversations"""
        try:
            conversations = []
            async for conv_doc in self.collections[Collections.CONVERSATIONS].find({
                "user_id": user_id,
                "$text": {"$search": search_text}
            }).sort("timestamp", DESCENDING).limit(limit):
                conversations.append(ConversationSchema(**conv_doc))
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            return []
    
    # Session Management
    async def create_session(self, session: ConversationSessionSchema) -> bool:
        """Create a new conversation session"""
        try:
            await self.collections[Collections.SESSIONS].insert_one(
                session.dict(by_alias=True)
            )
            
            logger.info(f"✅ Created session: {session.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False
    
    async def get_active_sessions(self, user_id: str) -> List[ConversationSessionSchema]:
        """Get active sessions for a user"""
        try:
            sessions = []
            async for session_doc in self.collections[Collections.SESSIONS].find({
                "user_id": user_id,
                "ended_at": {"$exists": False}
            }).sort("last_activity", DESCENDING):
                sessions.append(ConversationSessionSchema(**session_doc))
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
    
    async def end_session(self, session_id: str) -> bool:
        """End a conversation session"""
        try:
            result = await self.collections[Collections.SESSIONS].update_one(
                {"session_id": session_id},
                {"$set": {"ended_at": datetime.now(timezone.utc)}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False
    
    # Synchronization Management
    async def create_sync_operation(self, sync_op: SyncOperationSchema) -> bool:
        """Create a synchronization operation"""
        try:
            await self.collections[Collections.SYNC_OPERATIONS].insert_one(
                sync_op.dict(by_alias=True)
            )
            
            logger.debug(f"Created sync operation: {sync_op._id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating sync operation: {e}")
            return False
    
    async def get_pending_sync_operations(
        self,
        user_id: str,
        device_id: Optional[str] = None
    ) -> List[SyncOperationSchema]:
        """Get pending sync operations"""
        try:
            filter_query = {
                "user_id": user_id,
                "status": "pending"
            }
            
            if device_id:
                filter_query["target_device_id"] = device_id
            
            operations = []
            async for op_doc in self.collections[Collections.SYNC_OPERATIONS].find(
                filter_query
            ).sort("created_at", ASCENDING):
                operations.append(SyncOperationSchema(**op_doc))
            
            return operations
            
        except Exception as e:
            logger.error(f"Error getting sync operations: {e}")
            return []
    
    async def update_sync_operation_status(
        self,
        operation_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """Update sync operation status"""
        try:
            update_data = {"status": status}
            
            if status == "completed":
                update_data["completed_at"] = datetime.now(timezone.utc)
            elif status == "failed" and error_message:
                update_data["error_message"] = error_message
            
            result = await self.collections[Collections.SYNC_OPERATIONS].update_one(
                {"_id": operation_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating sync operation: {e}")
            return False
    
    # Analytics and Reporting
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            # Count conversations
            total_conversations = await self.collections[Collections.CONVERSATIONS].count_documents({
                "user_id": user_id
            })
            
            # Count active devices
            active_devices = await self.collections[Collections.DEVICES].count_documents({
                "user_id": user_id,
                "is_active": True
            })
            
            # Count active sessions
            active_sessions = await self.collections[Collections.SESSIONS].count_documents({
                "user_id": user_id,
                "ended_at": {"$exists": False}
            })
            
            # Get recent activity
            recent_activity = await self.collections[Collections.CONVERSATIONS].find({
                "user_id": user_id,
                "timestamp": {"$gte": datetime.now(timezone.utc) - timedelta(days=7)}
            }).count()
            
            return {
                "total_conversations": total_conversations,
                "active_devices": active_devices,
                "active_sessions": active_sessions,
                "recent_activity": recent_activity,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
    
    # Database Maintenance
    async def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Clean up old data for performance"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # Clean up old sync operations
            sync_result = await self.collections[Collections.SYNC_OPERATIONS].delete_many({
                "completed_at": {"$lt": cutoff_date},
                "status": "completed"
            })
            
            # Clean up old ended sessions
            session_result = await self.collections[Collections.SESSIONS].delete_many({
                "ended_at": {"$lt": cutoff_date}
            })
            
            logger.info(f"Cleanup complete: {sync_result.deleted_count} sync ops, {session_result.deleted_count} sessions")
            
            return {
                "sync_operations_deleted": sync_result.deleted_count,
                "sessions_deleted": session_result.deleted_count
            }
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            # Check connection
            await self.client.admin.command('ping')
            
            # Check collections
            collections_info = {}
            for name, collection in self.collections.items():
                count = await collection.count_documents({})
                collections_info[name] = count
            
            return {
                "status": "healthy",
                "database": self.database_name,
                "collections": collections_info,
                "mongodb_connected": True
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "mongodb_connected": False
            }
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions"""
        async with await self.client.start_session() as session:
            async with session.start_transaction():
                yield session
    
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("✅ MongoDB connection closed")


# Testing
async def test_mongodb_manager():
    """Test MongoDB manager functionality"""
    print("🧪 Testing BUDDY MongoDB Manager")
    print("=" * 40)
    
    # Initialize manager
    manager = BuddyMongoManager()
    
    if not await manager.initialize():
        print("❌ Failed to initialize MongoDB manager")
        return
    
    print("✅ MongoDB manager initialized")
    
    # Health check
    health = await manager.health_check()
    print(f"📊 Health Status: {health['status']}")
    
    # Test user creation
    from .mongodb_schemas import UserSchema
    
    test_user = UserSchema(
        user_id="test_user_123",
        email="test@buddy.ai",
        display_name="Test User"
    )
    
    user_created = await manager.create_user(test_user)
    print(f"👤 User Creation: {'✅' if user_created else '❌'}")
    
    # Test device registration
    from .mongodb_schemas import DeviceSchema, DeviceType
    
    test_device = DeviceSchema(
        user_id="test_user_123",
        device_id="test_device_001",
        device_type=DeviceType.MOBILE,
        device_name="Test iPhone",
        platform="ios"
    )
    
    device_registered = await manager.register_device(test_device)
    print(f"📱 Device Registration: {'✅' if device_registered else '❌'}")
    
    # Test conversation saving
    from .mongodb_schemas import ConversationSchema, MessageType
    
    test_conversation = ConversationSchema(
        user_id="test_user_123",
        session_id="test_session_001",
        device_id="test_device_001",
        content="Hello BUDDY, how are you?",
        message_type=MessageType.USER
    )
    
    conversation_saved = await manager.save_conversation(test_conversation)
    print(f"💬 Conversation Save: {'✅' if conversation_saved else '❌'}")
    
    # Clean up test data
    await manager.collections[Collections.USERS].delete_one({"user_id": "test_user_123"})
    await manager.collections[Collections.DEVICES].delete_one({"device_id": "test_device_001"})
    await manager.collections[Collections.CONVERSATIONS].delete_one({"_id": test_conversation._id})
    
    await manager.close()
    print("🎉 MongoDB manager test complete!")


if __name__ == "__main__":
    asyncio.run(test_mongodb_manager())
