"""
BUDDY 2.0 MongoDB Schema Definitions
==================================

Cross-platform database schemas for MongoDB Atlas with multi-tenant
user isolation and device-aware data management.

Architecture:
- User-centric data partitioning
- Device registry for cross-platform sync
- Conversation storage with vector references
- Conflict resolution for multi-device scenarios
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class SubscriptionTier(str, Enum):
    """User subscription tiers"""
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class DeviceType(str, Enum):
    """Supported device types"""
    MOBILE = "mobile"
    DESKTOP = "desktop"
    WEB = "web"
    WATCH = "watch"
    TV = "tv"
    CAR = "car"
    IOT = "iot"


class MessageType(str, Enum):
    """Conversation message types"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"


class SyncStatus(str, Enum):
    """Data synchronization status"""
    PENDING = "pending"
    SYNCED = "synced"
    CONFLICT = "conflict"
    FAILED = "failed"


class UserPreferences(BaseModel):
    """User preferences and settings"""
    language: str = "en"
    timezone: str = "UTC"
    voice_model: str = "default"
    conversation_style: str = "balanced"
    privacy_level: str = "standard"
    notification_settings: Dict[str, bool] = Field(default_factory=dict)
    ui_theme: str = "auto"
    accessibility_options: Dict[str, Any] = Field(default_factory=dict)


class SubscriptionInfo(BaseModel):
    """User subscription information"""
    tier: SubscriptionTier = SubscriptionTier.FREE
    max_devices: int = 3
    features: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    billing_info: Optional[Dict[str, Any]] = None


class UserSchema(BaseModel):
    """Primary user document schema"""
    _id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="Unique user identifier")
    email: str
    display_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Subscription and account info
    subscription: SubscriptionInfo = Field(default_factory=SubscriptionInfo)
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    
    # Security and privacy
    auth_provider: str = "firebase"
    encrypted_data_key: Optional[str] = None
    privacy_consent: Dict[str, bool] = Field(default_factory=dict)
    
    # Analytics and usage
    total_conversations: int = 0
    total_messages: int = 0
    usage_stats: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeviceCapabilities(BaseModel):
    """Device hardware and software capabilities"""
    has_voice: bool = False
    has_camera: bool = False
    has_location: bool = False
    has_biometrics: bool = False
    has_offline_ai: bool = False
    screen_size: str = "unknown"  # small, medium, large, xlarge
    input_methods: List[str] = Field(default_factory=list)  # touch, voice, keyboard, etc.
    network_type: str = "unknown"  # wifi, cellular, ethernet
    storage_capacity: int = 0  # MB available for BUDDY data


class DeviceSchema(BaseModel):
    """Device registration and capabilities"""
    _id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="Reference to user")
    device_id: str = Field(..., description="Unique device identifier")
    device_type: DeviceType
    device_name: str
    platform: str  # ios, android, windows, macos, linux, web
    platform_version: str = "unknown"
    app_version: str = "unknown"
    
    # Device status
    is_active: bool = True
    is_primary: bool = False
    last_sync: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Device capabilities and configuration
    capabilities: DeviceCapabilities = Field(default_factory=DeviceCapabilities)
    
    # Sync configuration
    sync_enabled: bool = True
    auto_sync_interval: int = 300  # seconds
    sync_preferences: Dict[str, bool] = Field(default_factory=dict)
    
    # Device metadata
    hardware_info: Dict[str, Any] = Field(default_factory=dict)
    software_info: Dict[str, Any] = Field(default_factory=dict)
    network_info: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeviceContext(BaseModel):
    """Runtime device context information"""
    location: Optional[Dict[str, float]] = None  # lat, lng, accuracy
    battery_level: Optional[int] = None  # 0-100
    network_quality: str = "unknown"  # excellent, good, fair, poor
    is_charging: Optional[bool] = None
    ambient_light: Optional[str] = None  # bright, normal, dim, dark
    noise_level: Optional[str] = None  # quiet, normal, noisy
    motion_state: Optional[str] = None  # stationary, walking, driving
    time_of_day: str = "unknown"  # morning, afternoon, evening, night


class MessageMetadata(BaseModel):
    """Conversation message metadata"""
    intent: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    response_time: float = 0.0
    processing_engine: str = "unknown"
    
    # Device context at time of message
    device_context: Optional[DeviceContext] = None
    
    # Message processing info
    tokens_used: int = 0
    model_version: str = "unknown"
    language_detected: str = "en"
    
    # Voice-specific metadata
    voice_metadata: Optional[Dict[str, Any]] = None
    
    # Error information if message failed
    error_info: Optional[Dict[str, Any]] = None


class ConversationSchema(BaseModel):
    """Individual conversation message"""
    _id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="Partition key for user isolation")
    session_id: str = Field(..., description="Conversation session identifier")
    device_id: str = Field(..., description="Source device")
    
    # Message content
    content: str
    message_type: MessageType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Message metadata and processing info
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)
    
    # Sync and versioning
    sync_version: int = 1
    sync_status: SyncStatus = SyncStatus.PENDING
    last_modified: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Vector database reference
    vector_id: Optional[str] = None
    embedding_version: str = "v1"
    
    # Content analysis
    content_hash: Optional[str] = None
    content_length: int = 0
    language: str = "en"
    
    # Privacy and security
    is_encrypted: bool = False
    encryption_key_id: Optional[str] = None
    
    # Message relationships
    reply_to_message_id: Optional[str] = None
    thread_id: Optional[str] = None
    
    # Analytics and feedback
    user_feedback: Optional[Dict[str, Any]] = None
    analytics_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationSessionSchema(BaseModel):
    """Conversation session management"""
    _id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str
    device_id: str
    
    # Session metadata
    title: str = "New Conversation"
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # Session timing
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    
    # Session statistics
    message_count: int = 0
    total_tokens: int = 0
    average_response_time: float = 0.0
    
    # Session configuration
    ai_personality: str = "default"
    conversation_mode: str = "chat"  # chat, voice, mixed
    language: str = "en"
    
    # Privacy and security
    is_private: bool = True
    sharing_settings: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SyncOperationType(str, Enum):
    """Types of sync operations"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    MERGE = "merge"


class ConflictResolutionStrategy(str, Enum):
    """Conflict resolution strategies"""
    AUTO = "auto"
    MANUAL = "manual"
    LAST_WRITER_WINS = "last_writer_wins"
    FIRST_WRITER_WINS = "first_writer_wins"
    MERGE_CONTENT = "merge_content"
    USER_CHOICE = "user_choice"


class SyncOperationSchema(BaseModel):
    """Cross-device synchronization operations"""
    _id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    source_device_id: str
    target_device_id: Optional[str] = None  # None for broadcast to all devices
    
    # Operation details
    operation_type: SyncOperationType
    document_id: str
    document_type: str  # conversation, session, user_preferences, etc.
    collection_name: str
    
    # Conflict resolution
    conflict_resolution: ConflictResolutionStrategy = ConflictResolutionStrategy.AUTO
    conflict_data: Optional[Dict[str, Any]] = None
    
    # Operation status
    status: str = "pending"  # pending, in_progress, completed, failed, cancelled
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Data payload
    data_payload: Optional[Dict[str, Any]] = None
    data_size: int = 0
    checksum: Optional[str] = None
    
    # Priority and batching
    priority: int = 5  # 1-10, higher is more important
    batch_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DatabaseIndexes:
    """MongoDB index definitions for optimal performance"""
    
    @staticmethod
    def get_user_indexes():
        """Indexes for users collection"""
        return [
            {"key": {"user_id": 1}, "unique": True},
            {"key": {"email": 1}, "unique": True},
            {"key": {"last_active": -1}},
            {"key": {"subscription.tier": 1, "subscription.expires_at": 1}},
            {"key": {"created_at": -1}}
        ]
    
    @staticmethod
    def get_device_indexes():
        """Indexes for devices collection"""
        return [
            {"key": {"user_id": 1, "device_id": 1}, "unique": True},
            {"key": {"user_id": 1, "is_active": 1, "last_sync": -1}},
            {"key": {"device_type": 1, "platform": 1}},
            {"key": {"last_seen": -1}},
            {"key": {"is_primary": 1, "user_id": 1}}
        ]
    
    @staticmethod
    def get_conversation_indexes():
        """Indexes for conversations collection"""
        return [
            {"key": {"user_id": 1, "timestamp": -1}},
            {"key": {"user_id": 1, "session_id": 1, "timestamp": 1}},
            {"key": {"sync_version": 1, "user_id": 1}},
            {"key": {"device_id": 1, "timestamp": -1}},
            {"key": {"vector_id": 1}, "sparse": True},
            {"key": {"content": "text", "metadata.intent": "text"}},
            {"key": {"user_id": 1, "message_type": 1, "timestamp": -1}},
            {"key": {"sync_status": 1, "last_modified": -1}}
        ]
    
    @staticmethod
    def get_session_indexes():
        """Indexes for conversation sessions collection"""
        return [
            {"key": {"user_id": 1, "started_at": -1}},
            {"key": {"session_id": 1}, "unique": True},
            {"key": {"user_id": 1, "device_id": 1, "last_activity": -1}},
            {"key": {"ended_at": 1}, "sparse": True, "expireAfterSeconds": 2592000}  # 30 days
        ]
    
    @staticmethod
    def get_sync_operation_indexes():
        """Indexes for sync operations collection"""
        return [
            {"key": {"user_id": 1, "status": 1, "created_at": -1}},
            {"key": {"source_device_id": 1, "status": 1}},
            {"key": {"target_device_id": 1, "status": 1}},
            {"key": {"batch_id": 1}, "sparse": True},
            {"key": {"scheduled_at": 1}, "sparse": True},
            {"key": {"completed_at": 1}, "sparse": True, "expireAfterSeconds": 604800}  # 7 days
        ]


# Collection name constants
class Collections:
    """MongoDB collection names"""
    USERS = "users"
    DEVICES = "devices"
    CONVERSATIONS = "conversations"
    SESSIONS = "conversation_sessions"
    SYNC_OPERATIONS = "sync_operations"
    ANALYTICS = "analytics"
    FEEDBACK = "user_feedback"
    SYSTEM_LOGS = "system_logs"


# Schema validation for MongoDB
MONGODB_SCHEMAS = {
    Collections.USERS: {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "email", "display_name"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "email": {"bsonType": "string"},
                "display_name": {"bsonType": "string"},
                "subscription": {
                    "bsonType": "object",
                    "properties": {
                        "tier": {"enum": ["free", "premium", "enterprise"]},
                        "max_devices": {"bsonType": "int", "minimum": 1}
                    }
                }
            }
        }
    },
    
    Collections.DEVICES: {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "device_id", "device_type"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "device_id": {"bsonType": "string"},
                "device_type": {"enum": ["mobile", "desktop", "web", "watch", "tv", "car", "iot"]},
                "is_active": {"bsonType": "bool"}
            }
        }
    },
    
    Collections.CONVERSATIONS: {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "session_id", "device_id", "content", "message_type"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "session_id": {"bsonType": "string"},
                "device_id": {"bsonType": "string"},
                "content": {"bsonType": "string"},
                "message_type": {"enum": ["user", "assistant", "system", "error"]},
                "sync_version": {"bsonType": "int", "minimum": 1}
            }
        }
    }
}


def get_schema_for_collection(collection_name: str) -> BaseModel:
    """Get Pydantic schema for a collection"""
    schema_map = {
        Collections.USERS: UserSchema,
        Collections.DEVICES: DeviceSchema,
        Collections.CONVERSATIONS: ConversationSchema,
        Collections.SESSIONS: ConversationSessionSchema,
        Collections.SYNC_OPERATIONS: SyncOperationSchema
    }
    return schema_map.get(collection_name)


if __name__ == "__main__":
    # Example usage and schema validation
    print("🗄️ BUDDY 2.0 MongoDB Schemas")
    print("=" * 40)
    
    # Create example user
    user = UserSchema(
        user_id="user_12345",
        email="test@example.com",
        display_name="Test User"
    )
    print(f"✅ User Schema: {user.user_id}")
    
    # Create example device
    device = DeviceSchema(
        user_id="user_12345",
        device_id="device_mobile_001",
        device_type=DeviceType.MOBILE,
        device_name="iPhone 15",
        platform="ios"
    )
    print(f"✅ Device Schema: {device.device_name}")
    
    # Create example conversation
    conversation = ConversationSchema(
        user_id="user_12345",
        session_id="session_001",
        device_id="device_mobile_001",
        content="Hello BUDDY, how are you today?",
        message_type=MessageType.USER
    )
    print(f"✅ Conversation Schema: {conversation.content[:30]}...")
    
    print("\n📊 Schema Summary:")
    print(f"   👤 Users: {len(UserSchema.__fields__)} fields")
    print(f"   📱 Devices: {len(DeviceSchema.__fields__)} fields")
    print(f"   💬 Conversations: {len(ConversationSchema.__fields__)} fields")
    print(f"   🔄 Sync Operations: {len(SyncOperationSchema.__fields__)} fields")
    
    print("\n🎯 Ready for MongoDB Atlas deployment!")
