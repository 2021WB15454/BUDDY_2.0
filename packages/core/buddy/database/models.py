"""
Database Models for BUDDY

Defines data models and schemas for MongoDB collections.
Provides validation and serialization for database operations.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid


class MessageType(Enum):
    """Types of messages in conversations."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class DeviceType(Enum):
    """Types of devices."""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    SMART_SPEAKER = "smart_speaker"
    SMART_TV = "smart_tv"
    WATCH = "watch"
    AUTOMOTIVE = "automotive"
    UNKNOWN = "unknown"


class MemoryType(Enum):
    """Types of memories."""
    CONVERSATION = "conversation"
    PREFERENCE = "preference"
    SKILL_DATA = "skill_data"
    CONTEXT = "context"
    LEARNING = "learning"


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation."""
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.USER
    content: str = ""
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    skill_used: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    response_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = asdict(self)
        data['message_type'] = self.message_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        """Create from dictionary."""
        data = data.copy()
        data['message_type'] = MessageType(data['message_type'])
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ConversationModel:
    """Model for conversation documents."""
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    user_id: str = ""
    device_id: str = ""
    turns: List[ConversationTurn] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    total_turns: int = 0
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = asdict(self)
        data['turns'] = [turn.to_dict() for turn in self.turns]
        data['start_time'] = self.start_time.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationModel':
        """Create from dictionary."""
        data = data.copy()
        data['turns'] = [ConversationTurn.from_dict(turn) for turn in data.get('turns', [])]
        if isinstance(data['start_time'], str):
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if isinstance(data['last_activity'], str):
            data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        return cls(**data)
    
    def add_turn(self, turn: ConversationTurn):
        """Add a turn to the conversation."""
        self.turns.append(turn)
        self.total_turns = len(self.turns)
        self.last_activity = datetime.utcnow()


@dataclass
class UserModel:
    """Model for user documents."""
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    email: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    total_conversations: int = 0
    favorite_skills: List[str] = field(default_factory=list)
    privacy_settings: Dict[str, bool] = field(default_factory=lambda: {
        'store_conversations': True,
        'personalization': True,
        'analytics': True
    })
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_seen'] = self.last_seen.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserModel':
        """Create from dictionary."""
        data = data.copy()
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data['last_seen'], str):
            data['last_seen'] = datetime.fromisoformat(data['last_seen'])
        return cls(**data)


@dataclass
class SkillExecutionModel:
    """Model for skill execution documents."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    skill_name: str = ""
    user_id: str = ""
    session_id: str = ""
    conversation_id: str = ""
    turn_id: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillExecutionModel':
        """Create from dictionary."""
        data = data.copy()
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class DeviceModel:
    """Model for device documents."""
    device_id: str = ""
    user_id: str = ""
    device_type: DeviceType = DeviceType.UNKNOWN
    device_name: Optional[str] = None
    platform: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    total_sessions: int = 0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = asdict(self)
        data['device_type'] = self.device_type.value
        data['first_seen'] = self.first_seen.isoformat()
        data['last_seen'] = self.last_seen.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceModel':
        """Create from dictionary."""
        data = data.copy()
        data['device_type'] = DeviceType(data['device_type'])
        if isinstance(data['first_seen'], str):
            data['first_seen'] = datetime.fromisoformat(data['first_seen'])
        if isinstance(data['last_seen'], str):
            data['last_seen'] = datetime.fromisoformat(data['last_seen'])
        return cls(**data)


@dataclass
class MemoryModel:
    """Model for memory documents."""
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    memory_type: MemoryType = MemoryType.CONVERSATION
    content: Dict[str, Any] = field(default_factory=dict)
    summary: Optional[str] = None
    importance: float = 0.5  # 0.0 to 1.0
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    related_memories: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = asdict(self)
        data['memory_type'] = self.memory_type.value
        data['last_accessed'] = self.last_accessed.isoformat()
        data['created_at'] = self.created_at.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryModel':
        """Create from dictionary."""
        data = data.copy()
        data['memory_type'] = MemoryType(data['memory_type'])
        if isinstance(data['last_accessed'], str):
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('expires_at') and isinstance(data['expires_at'], str):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)
    
    def access(self):
        """Mark memory as accessed."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if memory has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


# Schema validation functions
def validate_conversation_data(data: Dict[str, Any]) -> bool:
    """Validate conversation data structure."""
    required_fields = ['session_id', 'user_id']
    return all(field in data for field in required_fields)


def validate_user_data(data: Dict[str, Any]) -> bool:
    """Validate user data structure."""
    required_fields = ['user_id']
    return all(field in data for field in required_fields)


def validate_skill_execution_data(data: Dict[str, Any]) -> bool:
    """Validate skill execution data structure."""
    required_fields = ['skill_name', 'user_id', 'session_id']
    return all(field in data for field in required_fields)


def validate_device_data(data: Dict[str, Any]) -> bool:
    """Validate device data structure."""
    required_fields = ['device_id', 'user_id']
    return all(field in data for field in required_fields)


def validate_memory_data(data: Dict[str, Any]) -> bool:
    """Validate memory data structure."""
    required_fields = ['user_id', 'memory_type']
    return all(field in data for field in required_fields)
