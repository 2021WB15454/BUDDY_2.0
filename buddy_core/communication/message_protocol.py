"""
BUDDY Cross-Platform Message Protocol
Standardized message format and protocol for seamless device communication

This module defines the unified messaging protocol used across all BUDDY platforms,
ensuring consistent communication regardless of device type or platform.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import base64

# Enums for message classification

class MessageType(Enum):
    """Types of messages in BUDDY protocol"""
    USER_INPUT = "user_input"
    VOICE_INPUT = "voice_input"
    ASSISTANT_RESPONSE = "assistant_response"
    SYNC_UPDATE = "sync_update"
    SYSTEM_EVENT = "system_event"
    HEALTH_DATA = "health_data"
    CONTEXT_UPDATE = "context_update"
    DEVICE_STATUS = "device_status"
    AUTHENTICATION = "authentication"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    CAPABILITY_UPDATE = "capability_update"

class DeviceType(Enum):
    """Supported device types"""
    MOBILE = "mobile"
    DESKTOP = "desktop"
    WATCH = "watch"
    TV = "tv"
    CAR = "car"
    WEB = "web"
    IOT = "iot"
    SPEAKER = "speaker"

class Platform(Enum):
    """Supported platforms"""
    # Mobile
    IOS = "ios"
    ANDROID = "android"
    
    # Desktop
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    
    # Watch
    WATCHOS = "watchos"
    WEAR_OS = "wear_os"
    
    # TV
    TVOS = "tvos"
    ANDROID_TV = "android_tv"
    TIZEN = "tizen"
    WEBOS = "webos"
    
    # Automotive
    ANDROID_AUTOMOTIVE = "android_automotive"
    CARPLAY = "carplay"
    TESLA = "tesla"
    
    # Web
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"
    
    # IoT
    RASPBERRY_PI = "raspberry_pi"
    ARDUINO = "arduino"
    ALEXA = "alexa"
    GOOGLE_HOME = "google_home"

class Priority(Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

class SecurityLevel(Enum):
    """Security classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

# Core message structures

@dataclass
class DeviceInfo:
    """Device information structure"""
    device_id: str
    device_type: DeviceType
    platform: Platform
    model: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    hardware_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type.value,
            "platform": self.platform.value,
            "model": self.model,
            "os_version": self.os_version,
            "app_version": self.app_version,
            "hardware_id": self.hardware_id
        }

@dataclass
class Location:
    """Location information"""
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    altitude: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[float] = None
    timestamp: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class MessageContext:
    """Context information for messages"""
    timestamp: float = field(default_factory=time.time)
    timezone: str = field(default_factory=lambda: str(datetime.now(timezone.utc).astimezone().tzinfo))
    location: Optional[Location] = None
    battery_level: Optional[int] = None
    network_type: Optional[str] = None
    is_charging: Optional[bool] = None
    screen_brightness: Optional[float] = None
    ambient_light: Optional[float] = None
    noise_level: Optional[float] = None
    device_orientation: Optional[str] = None
    app_state: Optional[str] = None
    user_activity: Optional[str] = None
    health_data: Optional[Dict[str, Any]] = None
    custom_context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.location:
            result["location"] = self.location.to_dict()
        return result

@dataclass
class MessageSecurity:
    """Security metadata for messages"""
    security_level: SecurityLevel = SecurityLevel.INTERNAL
    encryption_method: Optional[str] = None
    signature: Optional[str] = None
    checksum: Optional[str] = None
    key_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "security_level": self.security_level.value,
            "encryption_method": self.encryption_method,
            "signature": self.signature,
            "checksum": self.checksum,
            "key_id": self.key_id
        }

@dataclass
class MessageContent:
    """Message content structure"""
    text: Optional[str] = None
    audio_data: Optional[bytes] = None
    image_data: Optional[bytes] = None
    video_data: Optional[bytes] = None
    file_data: Optional[bytes] = None
    structured_data: Optional[Dict[str, Any]] = None
    capabilities: Optional[List[str]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    context: Optional[MessageContext] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "text": self.text,
            "structured_data": self.structured_data,
            "capabilities": self.capabilities,
            "actions": self.actions
        }
        
        # Handle binary data with base64 encoding
        if self.audio_data:
            result["audio_data"] = base64.b64encode(self.audio_data).decode('utf-8')
        if self.image_data:
            result["image_data"] = base64.b64encode(self.image_data).decode('utf-8')
        if self.video_data:
            result["video_data"] = base64.b64encode(self.video_data).decode('utf-8')
        if self.file_data:
            result["file_data"] = base64.b64encode(self.file_data).decode('utf-8')
        
        if self.context:
            result["context"] = self.context.to_dict()
        
        return result

@dataclass
class BuddyMessage:
    """Core BUDDY message structure"""
    # Required fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.USER_INPUT
    timestamp: float = field(default_factory=time.time)
    device_info: DeviceInfo = None
    user_id: str = "default_user"
    session_id: str = ""
    
    # Content
    content: MessageContent = field(default_factory=MessageContent)
    
    # Metadata
    priority: Priority = Priority.NORMAL
    security: MessageSecurity = field(default_factory=MessageSecurity)
    correlation_id: Optional[str] = None
    parent_id: Optional[str] = None
    conversation_id: Optional[str] = None
    
    # Routing
    source_device: Optional[str] = None
    target_devices: Optional[List[str]] = None
    broadcast: bool = False
    
    # Processing
    requires_response: bool = False
    response_timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Quality of Service
    delivery_confirmation: bool = False
    persistence: bool = True
    compression: bool = False
    
    # Custom metadata
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        if not self.session_id:
            self.session_id = f"session_{self.device_info.device_id if self.device_info else 'unknown'}_{int(time.time())}"
        
        if not self.conversation_id:
            self.conversation_id = f"conv_{self.user_id}_{int(time.time())}"
        
        # Generate checksum for integrity
        self.security.checksum = self._generate_checksum()
    
    def _generate_checksum(self) -> str:
        """Generate message checksum for integrity verification"""
        content_str = json.dumps(self.content.to_dict(), sort_keys=True)
        checksum = hashlib.sha256(content_str.encode()).hexdigest()[:16]
        return checksum
    
    def validate_checksum(self) -> bool:
        """Validate message integrity"""
        expected_checksum = self._generate_checksum()
        return self.security.checksum == expected_checksum
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "device_info": self.device_info.to_dict() if self.device_info else None,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "content": self.content.to_dict(),
            "priority": self.priority.value,
            "security": self.security.to_dict(),
            "correlation_id": self.correlation_id,
            "parent_id": self.parent_id,
            "conversation_id": self.conversation_id,
            "source_device": self.source_device,
            "target_devices": self.target_devices,
            "broadcast": self.broadcast,
            "requires_response": self.requires_response,
            "response_timeout": self.response_timeout,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "delivery_confirmation": self.delivery_confirmation,
            "persistence": self.persistence,
            "compression": self.compression,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BuddyMessage':
        """Create message from dictionary"""
        # Extract device info
        device_info = None
        if data.get("device_info"):
            device_data = data["device_info"]
            device_info = DeviceInfo(
                device_id=device_data["device_id"],
                device_type=DeviceType(device_data["device_type"]),
                platform=Platform(device_data["platform"]),
                model=device_data.get("model"),
                os_version=device_data.get("os_version"),
                app_version=device_data.get("app_version"),
                hardware_id=device_data.get("hardware_id")
            )
        
        # Extract content
        content_data = data.get("content", {})
        context_data = content_data.get("context")
        context = None
        if context_data:
            location_data = context_data.get("location")
            location = None
            if location_data:
                location = Location(**location_data)
            
            context = MessageContext(
                timestamp=context_data.get("timestamp", time.time()),
                timezone=context_data.get("timezone", str(datetime.now(timezone.utc).astimezone().tzinfo)),
                location=location,
                battery_level=context_data.get("battery_level"),
                network_type=context_data.get("network_type"),
                is_charging=context_data.get("is_charging"),
                screen_brightness=context_data.get("screen_brightness"),
                ambient_light=context_data.get("ambient_light"),
                noise_level=context_data.get("noise_level"),
                device_orientation=context_data.get("device_orientation"),
                app_state=context_data.get("app_state"),
                user_activity=context_data.get("user_activity"),
                health_data=context_data.get("health_data"),
                custom_context=context_data.get("custom_context")
            )
        
        content = MessageContent(
            text=content_data.get("text"),
            structured_data=content_data.get("structured_data"),
            capabilities=content_data.get("capabilities"),
            actions=content_data.get("actions"),
            context=context
        )
        
        # Handle binary data
        if content_data.get("audio_data"):
            content.audio_data = base64.b64decode(content_data["audio_data"])
        if content_data.get("image_data"):
            content.image_data = base64.b64decode(content_data["image_data"])
        if content_data.get("video_data"):
            content.video_data = base64.b64decode(content_data["video_data"])
        if content_data.get("file_data"):
            content.file_data = base64.b64decode(content_data["file_data"])
        
        # Extract security
        security_data = data.get("security", {})
        security = MessageSecurity(
            security_level=SecurityLevel(security_data.get("security_level", "internal")),
            encryption_method=security_data.get("encryption_method"),
            signature=security_data.get("signature"),
            checksum=security_data.get("checksum"),
            key_id=security_data.get("key_id")
        )
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=MessageType(data.get("type", "user_input")),
            timestamp=data.get("timestamp", time.time()),
            device_info=device_info,
            user_id=data.get("user_id", "default_user"),
            session_id=data.get("session_id", ""),
            content=content,
            priority=Priority(data.get("priority", "normal")),
            security=security,
            correlation_id=data.get("correlation_id"),
            parent_id=data.get("parent_id"),
            conversation_id=data.get("conversation_id"),
            source_device=data.get("source_device"),
            target_devices=data.get("target_devices"),
            broadcast=data.get("broadcast", False),
            requires_response=data.get("requires_response", False),
            response_timeout=data.get("response_timeout"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            delivery_confirmation=data.get("delivery_confirmation", False),
            persistence=data.get("persistence", True),
            compression=data.get("compression", False),
            metadata=data.get("metadata")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BuddyMessage':
        """Create message from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

# Message builders for common scenarios

class MessageBuilder:
    """Builder class for creating BUDDY messages"""
    
    @staticmethod
    def create_user_input(text: str, device_info: DeviceInfo, user_id: str, 
                         context: Optional[MessageContext] = None) -> BuddyMessage:
        """Create a user input message"""
        content = MessageContent(text=text, context=context)
        return BuddyMessage(
            type=MessageType.USER_INPUT,
            device_info=device_info,
            user_id=user_id,
            content=content,
            requires_response=True
        )
    
    @staticmethod
    def create_voice_input(audio_data: bytes, device_info: DeviceInfo, user_id: str,
                          transcription: Optional[str] = None,
                          context: Optional[MessageContext] = None) -> BuddyMessage:
        """Create a voice input message"""
        content = MessageContent(audio_data=audio_data, text=transcription, context=context)
        return BuddyMessage(
            type=MessageType.VOICE_INPUT,
            device_info=device_info,
            user_id=user_id,
            content=content,
            requires_response=True
        )
    
    @staticmethod
    def create_assistant_response(text: str, device_info: DeviceInfo, user_id: str,
                                 correlation_id: str, actions: Optional[List[Dict[str, Any]]] = None,
                                 context: Optional[MessageContext] = None) -> BuddyMessage:
        """Create an assistant response message"""
        content = MessageContent(text=text, actions=actions, context=context)
        return BuddyMessage(
            type=MessageType.ASSISTANT_RESPONSE,
            device_info=device_info,
            user_id=user_id,
            content=content,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_sync_update(data: Dict[str, Any], device_info: DeviceInfo, user_id: str,
                          target_devices: Optional[List[str]] = None) -> BuddyMessage:
        """Create a sync update message"""
        content = MessageContent(structured_data=data)
        return BuddyMessage(
            type=MessageType.SYNC_UPDATE,
            device_info=device_info,
            user_id=user_id,
            content=content,
            target_devices=target_devices,
            broadcast=target_devices is None
        )
    
    @staticmethod
    def create_heartbeat(device_info: DeviceInfo, context: Optional[MessageContext] = None) -> BuddyMessage:
        """Create a heartbeat message"""
        content = MessageContent(context=context)
        return BuddyMessage(
            type=MessageType.HEARTBEAT,
            device_info=device_info,
            content=content,
            priority=Priority.LOW
        )
    
    @staticmethod
    def create_error_message(error_code: str, error_message: str, device_info: DeviceInfo,
                           correlation_id: Optional[str] = None) -> BuddyMessage:
        """Create an error message"""
        content = MessageContent(
            structured_data={
                "error_code": error_code,
                "error_message": error_message,
                "timestamp": time.time()
            }
        )
        return BuddyMessage(
            type=MessageType.ERROR,
            device_info=device_info,
            content=content,
            correlation_id=correlation_id,
            priority=Priority.HIGH
        )

# Protocol utilities

class ProtocolUtils:
    """Utility functions for BUDDY protocol"""
    
    @staticmethod
    def validate_message(message: BuddyMessage) -> List[str]:
        """Validate message structure and return list of errors"""
        errors = []
        
        if not message.id:
            errors.append("Message ID is required")
        
        if not message.device_info:
            errors.append("Device info is required")
        elif not message.device_info.device_id:
            errors.append("Device ID is required")
        
        if not message.user_id:
            errors.append("User ID is required")
        
        if not message.content:
            errors.append("Message content is required")
        
        if not message.validate_checksum():
            errors.append("Message checksum validation failed")
        
        return errors
    
    @staticmethod
    def get_message_size(message: BuddyMessage) -> int:
        """Get message size in bytes"""
        json_str = message.to_json()
        return len(json_str.encode('utf-8'))
    
    @staticmethod
    def compress_message(message: BuddyMessage) -> bytes:
        """Compress message for transmission"""
        import gzip
        json_data = message.to_json()
        return gzip.compress(json_data.encode('utf-8'))
    
    @staticmethod
    def decompress_message(compressed_data: bytes) -> BuddyMessage:
        """Decompress and parse message"""
        import gzip
        json_data = gzip.decompress(compressed_data).decode('utf-8')
        return BuddyMessage.from_json(json_data)
    
    @staticmethod
    def create_response_message(original_message: BuddyMessage, response_text: str,
                              device_info: DeviceInfo) -> BuddyMessage:
        """Create a response message for an incoming message"""
        return MessageBuilder.create_assistant_response(
            text=response_text,
            device_info=device_info,
            user_id=original_message.user_id,
            correlation_id=original_message.id
        )

# Demo function
def main():
    """Demonstration of BUDDY message protocol"""
    print("📬💬 BUDDY Cross-Platform Message Protocol Demo")
    print("=" * 60)
    print("Standardized messaging protocol for seamless device communication")
    print()
    
    # Create sample device info
    mobile_device = DeviceInfo(
        device_id="mobile_001",
        device_type=DeviceType.MOBILE,
        platform=Platform.ANDROID,
        model="Pixel 8",
        os_version="Android 14",
        app_version="2.1.0"
    )
    
    desktop_device = DeviceInfo(
        device_id="desktop_001",
        device_type=DeviceType.DESKTOP,
        platform=Platform.WINDOWS,
        model="Surface Pro",
        os_version="Windows 11",
        app_version="2.1.0"
    )
    
    # Create sample context
    context = MessageContext(
        location=Location(latitude=40.7128, longitude=-74.0060),
        battery_level=85,
        network_type="wifi",
        is_charging=False,
        device_orientation="portrait"
    )
    
    print("🔧 Creating Messages:")
    print("-" * 30)
    
    # Create different types of messages
    messages = [
        MessageBuilder.create_user_input(
            "What's the weather like today?",
            mobile_device,
            "user123",
            context
        ),
        MessageBuilder.create_voice_input(
            b"sample_audio_data",
            mobile_device,
            "user123",
            "What's my schedule for tomorrow?",
            context
        ),
        MessageBuilder.create_assistant_response(
            "Today's weather is sunny with a high of 75°F",
            desktop_device,
            "user123",
            "correlation_123",
            [{"action": "show_weather", "params": {"location": "NYC"}}]
        ),
        MessageBuilder.create_sync_update(
            {"calendar": {"events": [{"title": "Meeting", "time": "2pm"}]}},
            desktop_device,
            "user123",
            ["mobile_001", "watch_001"]
        ),
        MessageBuilder.create_heartbeat(mobile_device, context)
    ]
    
    # Display messages
    for i, message in enumerate(messages, 1):
        print(f"\n📨 Message {i}: {message.type.value}")
        print(f"   ID: {message.id}")
        print(f"   Device: {message.device_info.device_type.value} ({message.device_info.platform.value})")
        print(f"   Size: {ProtocolUtils.get_message_size(message)} bytes")
        
        # Validate message
        errors = ProtocolUtils.validate_message(message)
        if errors:
            print(f"   ❌ Validation errors: {', '.join(errors)}")
        else:
            print(f"   ✅ Message validated successfully")
        
        # Show content preview
        if message.content.text:
            preview = message.content.text[:50] + "..." if len(message.content.text) > 50 else message.content.text
            print(f"   Content: '{preview}'")
    
    print(f"\n🔄 Message Serialization Demo:")
    print("-" * 35)
    
    # Test serialization/deserialization
    test_message = messages[0]
    
    # To JSON
    json_str = test_message.to_json()
    print(f"✅ Serialized to JSON ({len(json_str)} characters)")
    
    # From JSON
    reconstructed = BuddyMessage.from_json(json_str)
    print(f"✅ Deserialized from JSON")
    print(f"   Original ID: {test_message.id}")
    print(f"   Reconstructed ID: {reconstructed.id}")
    print(f"   IDs match: {test_message.id == reconstructed.id}")
    
    # Test compression
    compressed = ProtocolUtils.compress_message(test_message)
    print(f"✅ Compressed to {len(compressed)} bytes (reduction: {((len(json_str) - len(compressed)) / len(json_str) * 100):.1f}%)")
    
    decompressed = ProtocolUtils.decompress_message(compressed)
    print(f"✅ Decompressed successfully")
    
    print(f"\n🔐 Security Features:")
    print("-" * 25)
    
    secure_message = messages[2]
    secure_message.security.security_level = SecurityLevel.CONFIDENTIAL
    secure_message.security.encryption_method = "AES-256"
    secure_message.security.key_id = "key_001"
    
    print(f"🔒 Security level: {secure_message.security.security_level.value}")
    print(f"🔑 Encryption: {secure_message.security.encryption_method}")
    print(f"🛡️  Checksum: {secure_message.security.checksum}")
    print(f"✅ Checksum valid: {secure_message.validate_checksum()}")
    
    print(f"\n📊 Protocol Statistics:")
    print("-" * 25)
    
    total_size = sum(ProtocolUtils.get_message_size(msg) for msg in messages)
    avg_size = total_size / len(messages)
    
    print(f"📨 Total messages: {len(messages)}")
    print(f"📏 Total size: {total_size} bytes")
    print(f"📐 Average size: {avg_size:.1f} bytes")
    print(f"🎯 Message types: {len(set(msg.type for msg in messages))}")
    print(f"📱 Device types: {len(set(msg.device_info.device_type for msg in messages))}")
    
    print(f"\n✅ BUDDY message protocol demonstrated successfully!")
    print("🌐 Unified protocol enables seamless cross-platform communication")
    print("🔒 Built-in security and validation ensure message integrity")
    print("📦 Efficient serialization supports real-time communication")

if __name__ == "__main__":
    main()
