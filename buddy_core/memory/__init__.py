"""
Memory Layer - BUDDY's Cross-Platform Knowledge and State Management

Enhanced for cross-platform support with:
- Local databases (SQLite, Realm) for offline-first storage
- Cloud synchronization (MongoDB Atlas) for cross-device access
- Vector databases (ChromaDB/Pinecone) for AI context memory
- End-to-end encryption for privacy and security
- Real-time sync across all platforms
"""

import asyncio
import json
import logging
import sqlite3
import time
import platform as system_platform
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import uuid

# Import our new cross-platform database components
from ..database import LocalDatabase, CloudDatabase, VectorDatabase, SyncManager, EncryptionManager

logger = logging.getLogger(__name__)

@dataclass
class Fact:
    """Represents a stored fact/knowledge item"""
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    source: str = "user"
    timestamp: float = None
    fact_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.fact_id is None:
            # Generate deterministic ID based on content
            content = f"{self.subject}|{self.predicate}|{self.object}"
            self.fact_id = hashlib.sha256(content.encode()).hexdigest()[:16]

@dataclass
class UserProfile:
    """User profile and preferences"""
    user_id: str
    name: str
    timezone: str = "UTC"
    locale: str = "en-US"
    preferences: Dict[str, Any] = None
    created_at: float = None
    updated_at: float = None
    
    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}
        if self.created_at is None:
            self.created_at = time.time()
        if self.updated_at is None:
            self.updated_at = time.time()

@dataclass
class Device:
    """Device registration and capabilities"""
    device_id: str
    user_id: str
    device_type: str  # desktop, mobile, watch, tv, car
    name: str
    capabilities: List[str]  # voice, camera, location, etc.
    last_seen: float = None
    status: str = "offline"  # online, offline, idle
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = time.time()

@dataclass
class Reminder:
    """Reminder/task item"""
    reminder_id: str
    user_id: str
    title: str
    scheduled_time: float
    recurrence: Optional[str] = None  # daily, weekly, monthly
    priority: str = "normal"  # low, normal, high
    status: str = "pending"  # pending, fired, cancelled
    created_at: float = None
    device_id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

class EnhancedMemoryLayer:
    """
    Enhanced cross-platform memory and knowledge management for BUDDY
    
    Features:
    - Cross-platform local databases (SQLite/Realm)
    - Cloud synchronization (MongoDB Atlas)
    - Vector embeddings for semantic search (ChromaDB/Pinecone)
    - End-to-end encryption for privacy
    - Offline-first with real-time sync
    - Platform-specific optimizations
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Detect current platform
        self.platform = self._detect_platform()
        
        # Generate or load device ID
        self.device_id = self.config.get("device_id") or str(uuid.uuid4())
        
        # Database components
        self.local_db = None
        self.cloud_db = None
        self.vector_db = None
        self.sync_manager = None
        self.encryption = None
        
        # Database manager (for compatibility with demo)
        self.db_manager = None
        
        # Legacy database for backward compatibility
        self.legacy_db = None
        self.legacy_db_path = self.config.get("legacy_db_path", "buddy_memory.db")
        
        # State
        self._initialized = False
        self._online = False
        
    def _detect_platform(self) -> str:
        """Detect the current platform"""
        system = system_platform.system().lower()
        
        if system == "darwin":
            # Check if iOS (simplified detection)
            if hasattr(system_platform, "ios_version"):
                return "ios"
            return "macos"
        elif system == "linux":
            # Check for Android (simplified detection)
            if "android" in system_platform.platform().lower():
                return "android"
            return "linux"
        elif system == "windows":
            return "windows"
        else:
            return "unknown"
    
    async def initialize(self, user_id: str = None, password: str = None):
        """Initialize the enhanced memory layer"""
        try:
            logger.info(f"Initializing enhanced memory layer for platform: {self.platform}")
            
            # Initialize encryption first (if enabled)
            if self.config.get("encryption_enabled", True):
                self.encryption = EncryptionManager(self.config.get("encryption", {}))
                await self.encryption.initialize(password, self.device_id)
            
            # Initialize local database
            local_db_config = self.config.get("local_db", {})
            local_db_path = local_db_config.get("path") or self._get_platform_db_path()
            
            self.local_db = LocalDatabase(local_db_path, self.platform)
            await self.local_db.initialize()
            
            # Initialize cloud database (if configured)
            cloud_config = self.config.get("cloud_db", {})
            if cloud_config.get("enabled", True):
                connection_string = cloud_config.get("connection_string")
                if connection_string:
                    self.cloud_db = CloudDatabase(
                        connection_string, 
                        cloud_config.get("database_name", "buddy_cloud")
                    )
                    await self.cloud_db.initialize()
                    self._online = self.cloud_db.is_connected()
            
            # Initialize vector database
            vector_config = self.config.get("vector_db", {})
            vector_provider = vector_config.get("provider", "chroma")
            
            self.vector_db = VectorDatabase(vector_provider, vector_config)
            await self.vector_db.initialize()
            
            # Initialize sync manager (if cloud is available)
            if self.cloud_db and self._online:
                self.sync_manager = SyncManager(self.local_db, self.cloud_db, self.device_id)
                await self.sync_manager.initialize()
            
            # Initialize legacy database for backward compatibility
            await self._initialize_legacy_db()
            
            # Create database manager for compatibility
            self.db_manager = type('DBManager', (), {
                'local_db': self.local_db,
                'cloud_db': self.cloud_db,
                'vector_db': self.vector_db,
                'sync_manager': self.sync_manager,
                'encryption': self.encryption
            })()
            
            self._initialized = True
            logger.info("Enhanced memory layer initialized successfully")
            
            # Perform initial sync if online
            if self.sync_manager and self._online:
                asyncio.create_task(self._initial_sync())
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced memory layer: {e}")
            self._initialized = False
            raise
    
    def _get_platform_db_path(self) -> str:
        """Get platform-specific database path"""
        if self.platform == "ios":
            return "~/Documents/buddy_local.db"
        elif self.platform == "android":
            return "/data/data/com.buddy.ai/databases/buddy_local.db"
        elif self.platform == "windows":
            return "~/AppData/Local/BUDDY/buddy_local.db"
        elif self.platform == "macos":
            return "~/Library/Application Support/BUDDY/buddy_local.db"
        elif self.platform == "linux":
            return "~/.local/share/buddy/buddy_local.db"
        else:
            return "./buddy_local.db"
    
    async def _initialize_legacy_db(self):
        """Initialize legacy SQLite database for backward compatibility"""
        self.legacy_db = sqlite3.connect(self.legacy_db_path, check_same_thread=False)
        self.legacy_db.row_factory = sqlite3.Row
        
        # Create legacy tables (simplified version of original)
        await self._create_legacy_tables()
    
    async def _create_legacy_tables(self):
        """Create legacy database tables"""
        # Key-value store for backward compatibility
        self.legacy_db.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                scope TEXT DEFAULT 'global',
                expires_at REAL,
                updated_at REAL NOT NULL
            )
        """)
        
        self.legacy_db.commit()
    
    async def _initial_sync(self):
        """Perform initial synchronization"""
        try:
            if self.sync_manager:
                result = await self.sync_manager.sync_all()
                logger.info(f"Initial sync completed: {result}")
        except Exception as e:
            logger.error(f"Initial sync failed: {e}")
    
    # Enhanced User Management
    async def create_user(self, user_profile: UserProfile) -> bool:
        """Create a new user profile with cross-platform sync"""
        if not self._initialized:
            return False
        
        try:
            # Store in local database
            user_data = {
                "name": user_profile.name,
                "timezone": user_profile.timezone,
                "locale": user_profile.locale,
                "preferences": user_profile.preferences,
                "created_at": user_profile.created_at,
                "updated_at": user_profile.updated_at
            }
            
            # Encrypt if enabled
            if self.encryption:
                user_data = await self.encryption.encrypt_user_data(user_data)
            
            await self.local_db.store_user_data(
                user_profile.user_id,
                "profile",
                user_data,
                self.device_id,
                encrypt=bool(self.encryption)
            )
            
            # Store in cloud if available
            if self.cloud_db and self._online:
                await self.cloud_db.store_user_data(
                    user_profile.user_id,
                    "profile", 
                    user_data,
                    self.device_id
                )
            
            # Mark for sync if offline
            elif self.sync_manager:
                await self.local_db.mark_for_sync("user_data", user_profile.user_id)
            
            logger.info(f"Created user profile: {user_profile.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False
    
    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile with cross-platform access"""
        if not self._initialized:
            return None
        
        try:
            # Try local database first
            local_data = await self.local_db.get_user_data(user_id, "profile")
            
            if local_data:
                user_record = local_data[0]
                content = user_record["content"]
                
                # Decrypt if necessary
                if user_record.get("encrypted") and self.encryption:
                    content = await self.encryption.decrypt_data(content)
                elif isinstance(content, str):
                    content = json.loads(content)
                
                return UserProfile(
                    user_id=user_id,
                    name=content["name"],
                    timezone=content.get("timezone", "UTC"),
                    locale=content.get("locale", "en-US"),
                    preferences=content.get("preferences", {}),
                    created_at=content.get("created_at"),
                    updated_at=content.get("updated_at")
                )
            
            # Try cloud database if local not found and online
            elif self.cloud_db and self._online:
                cloud_data = await self.cloud_db.get_user_data(user_id, "profile")
                
                if cloud_data:
                    content = cloud_data[0]["content"]
                    
                    # Store locally for offline access
                    await self.local_db.store_user_data(
                        user_id, "profile", content, self.device_id
                    )
                    
                    return UserProfile(
                        user_id=user_id,
                        name=content["name"],
                        timezone=content.get("timezone", "UTC"),
                        locale=content.get("locale", "en-US"),
                        preferences=content.get("preferences", {}),
                        created_at=content.get("created_at"),
                        updated_at=content.get("updated_at")
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
    
    # Enhanced Device Management
    async def register_device(self, device: Device) -> bool:
        """Register device with cross-platform support"""
        if not self._initialized:
            return False
        
        try:
            # Store device info locally
            device_data = {
                "user_id": device.user_id,
                "device_type": device.device_type,
                "name": device.name,
                "capabilities": device.capabilities,
                "last_seen": device.last_seen,
                "status": device.status,
                "platform": self.platform
            }
            
            await self.local_db.set_app_setting(
                f"device_{device.device_id}",
                "device_info", 
                device_data
            )
            
            # Register in cloud if available
            if self.cloud_db and self._online:
                await self.cloud_db.store_user_data(
                    device.user_id,
                    "device_registration",
                    device_data,
                    device.device_id
                )
            
            logger.info(f"Registered device: {device.device_id} ({device.device_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            return False
    
    # Enhanced Conversation Management
    async def store_conversation(self, user_id: str, session_id: str, 
                               message_type: str, content: str,
                               metadata: Dict[str, Any] = None) -> bool:
        """Store conversation with cross-platform sync"""
        if not self._initialized:
            return False
        
        try:
            # Store locally first
            await self.local_db.store_conversation(
                user_id, session_id, message_type, content, metadata, self.device_id
            )
            
            # Store in cloud if available
            if self.cloud_db and self._online:
                await self.cloud_db.store_conversation(
                    user_id, session_id, message_type, content, metadata, self.device_id
                )
            
            # Store in vector database for semantic search
            if self.vector_db and content.strip():
                await self.vector_db.store_context(
                    user_id, content, "conversation",
                    {
                        "session_id": session_id,
                        "message_type": message_type,
                        "device_id": self.device_id,
                        **(metadata or {})
                    }
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
            return False
    
    async def get_conversation_history(self, user_id: str, session_id: str = None,
                                     limit: int = 100) -> List[Dict[str, Any]]:
        """Get conversation history from all sources"""
        if not self._initialized:
            return []
        
        try:
            # Get from local database
            conversations = await self.local_db.get_conversations(user_id, session_id, limit)
            
            # If online and cloud available, merge with cloud data
            if self.cloud_db and self._online and len(conversations) < limit:
                cloud_conversations = await self.cloud_db.get_conversations(
                    user_id, session_id, limit=limit
                )
                
                # Merge and deduplicate conversations
                all_conversations = conversations + cloud_conversations
                seen_ids = set()
                unique_conversations = []
                
                for conv in all_conversations:
                    conv_id = conv.get("id") or conv.get("_id")
                    if conv_id not in seen_ids:
                        seen_ids.add(conv_id)
                        unique_conversations.append(conv)
                
                # Sort by timestamp
                conversations = sorted(
                    unique_conversations, 
                    key=lambda x: x.get("timestamp", 0), 
                    reverse=True
                )[:limit]
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    # Semantic Search and AI Context
    async def store_ai_context(self, user_id: str, content: str, 
                             context_type: str = "general",
                             metadata: Dict[str, Any] = None) -> bool:
        """Store AI context with semantic search capabilities"""
        if not self._initialized:
            return False
        
        try:
            # Store in vector database for semantic search
            if self.vector_db:
                context_id = await self.vector_db.store_context(
                    user_id, content, context_type,
                    {
                        "device_id": self.device_id,
                        "platform": self.platform,
                        **(metadata or {})
                    }
                )
            
            # Store in local database
            await self.local_db.store_ai_context(
                user_id, context_type, content, 
                device_id=self.device_id
            )
            
            # Store in cloud if available
            if self.cloud_db and self._online:
                await self.cloud_db.store_ai_context(
                    user_id, context_type, content,
                    device_id=self.device_id
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store AI context: {e}")
            return False
    
    async def search_context(self, user_id: str, query: str, 
                           context_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for relevant context using semantic similarity"""
        if not self._initialized:
            return []
        
        try:
            results = []
            
            # Search vector database first (most relevant)
            if self.vector_db:
                vector_results = await self.vector_db.search_context(
                    user_id, query, context_type, limit
                )
                results.extend(vector_results)
            
            # If not enough results, search local database
            if len(results) < limit:
                local_results = await self.local_db.get_ai_context(
                    user_id, context_type, limit - len(results)
                )
                
                # Convert to consistent format
                for result in local_results:
                    results.append({
                        "content": result["content"],
                        "context_type": result["context_type"],
                        "metadata": {"source": "local", "device_id": result.get("device_id")},
                        "similarity": 0.5  # Default similarity for non-vector results
                    })
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search context: {e}")
            return []

    # Facts and Knowledge Store
    async def store_fact(self, fact: str, user_id: str = None) -> bool:
        """Store a fact or piece of knowledge"""
        try:
            # Store as AI context with fact type
            return await self.store_ai_context(
                user_id or "global",
                fact,
                "fact",
                {"type": "knowledge", "source": "user_input"}
            )
        except Exception as e:
            logger.error(f"Failed to store fact: {e}")
            return False
    
    async def get_facts(self, user_id: str = None, limit: int = 10) -> List[str]:
        """Get stored facts"""
        try:
            results = await self.search_context(user_id or "global", "", "fact", limit)
            return [result["content"] for result in results]
        except Exception as e:
            logger.error(f"Failed to get facts: {e}")
            return []

            return []

    # Legacy Key-Value Store (for backward compatibility)
    async def set_kv(self, key: str, value: Any, scope: str = "global", expires_in: int = None) -> bool:
        """Store a key-value pair (legacy compatibility)"""
        if not self._initialized:
            return False
        
        try:
            # Store in enhanced local database
            if self.local_db:
                setting_key = f"{scope}_{key}" if scope != "global" else key
                await self.local_db.set_app_setting(self.platform, setting_key, value)
            
            # Also store in legacy database for backward compatibility
            if self.legacy_db:
                expires_at = None
                if expires_in:
                    expires_at = time.time() + expires_in
                
                self.legacy_db.execute("""
                    INSERT OR REPLACE INTO kv_store (key, value, scope, expires_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (key, json.dumps(value), scope, expires_at, time.time()))
                self.legacy_db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store KV pair: {e}")
            return False
    
    async def get_kv(self, key: str, scope: str = "global", default: Any = None) -> Any:
        """Get a value by key (legacy compatibility)"""
        if not self._initialized:
            return default
        
        try:
            # Try enhanced local database first
            if self.local_db:
                setting_key = f"{scope}_{key}" if scope != "global" else key
                value = await self.local_db.get_app_setting(self.platform, setting_key, default)
                if value != default:
                    return value
            
            # Fallback to legacy database
            if self.legacy_db:
                cursor = self.legacy_db.execute("""
                    SELECT value, expires_at FROM kv_store 
                    WHERE key = ? AND scope = ?
                """, (key, scope))
                
                row = cursor.fetchone()
                if row:
                    # Check expiration
                    if row['expires_at'] and row['expires_at'] < time.time():
                        # Expired, clean up
                        self.legacy_db.execute("DELETE FROM kv_store WHERE key = ? AND scope = ?", (key, scope))
                        self.legacy_db.commit()
                        return default
                    
                    try:
                        return json.loads(row['value'])
                    except json.JSONDecodeError:
                        return row['value']
            
            return default
            
        except Exception as e:
            logger.error(f"Failed to get KV pair: {e}")
            return default
    
    def get_sync_status(self) -> dict:
        """Get synchronization status"""
        try:
            base_status = {
                "platform": self.platform,
                "device_id": self.device_id,
                "online": self._online,
                "encryption": bool(self.encryption),
                "last_sync": "never",
                "pending_operations": 0,
                "sync_enabled": False,
                "cloud_connected": bool(self.cloud_db)
            }
            
            if self.db_manager and self.db_manager.sync_manager:
                sync_status = self.db_manager.sync_manager.get_sync_status()
                base_status.update(sync_status)
            
            return base_status
        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return {
                "platform": getattr(self, 'platform', 'unknown'),
                "device_id": getattr(self, 'device_id', 'unknown'),
                "online": False,
                "encryption": False,
                "error": str(e)
            }
    
    def close(self):
        """Close the memory layer and cleanup resources"""
        try:
            if hasattr(self.db_manager, 'close'):
                self.db_manager.close()
            logger.info("Memory layer closed successfully")
        except Exception as e:
            logger.error(f"Error closing memory layer: {e}")

# Global memory instance
_memory = None

def get_memory() -> EnhancedMemoryLayer:
    """Get the global memory layer instance"""
    global _memory
    if _memory is None:
        _memory = EnhancedMemoryLayer()
    return _memory

# Backward compatibility alias
MemoryLayer = EnhancedMemoryLayer
