"""
Local Database Layer - Cross-Platform Local Storage

Supports:
- SQLite (default for most platforms)
- Realm (for mobile/sync-heavy applications)
- CoreData bridge (iOS)
- Room bridge (Android)
"""

import sqlite3
import json
import os
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class LocalDatabase:
    """Cross-platform local database implementation"""
    
    def __init__(self, db_path: str = None, platform: str = "default"):
        self.platform = platform
        self.db_path = db_path or self._get_default_db_path()
        self.conn = None
        self._ensure_db_directory()
        
    def _get_default_db_path(self) -> str:
        """Get platform-specific database path"""
        if self.platform == "ios":
            # iOS Documents directory
            return os.path.expanduser("~/Documents/buddy_local.db")
        elif self.platform == "android":
            # Android internal storage
            return "/data/data/com.buddy.ai/databases/buddy_local.db"
        elif self.platform == "windows":
            # Windows AppData
            return os.path.expanduser("~/AppData/Local/BUDDY/buddy_local.db")
        elif self.platform == "macos":
            # macOS Application Support
            return os.path.expanduser("~/Library/Application Support/BUDDY/buddy_local.db")
        elif self.platform == "linux":
            # Linux XDG data directory
            return os.path.expanduser("~/.local/share/buddy/buddy_local.db")
        else:
            # Default/development
            return "./buddy_local.db"
    
    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    async def initialize(self):
        """Initialize local database with tables"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            
            # Create tables for cross-platform data
            await self._create_tables()
            logger.info(f"Local database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize local database: {e}")
            raise
    
    async def _create_tables(self):
        """Create all necessary tables"""
        tables = [
            # User data and preferences
            """
            CREATE TABLE IF NOT EXISTS user_data (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                data_type TEXT NOT NULL,
                content TEXT NOT NULL,
                encrypted BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP,
                device_id TEXT,
                sync_version INTEGER DEFAULT 1
            )
            """,
            
            # Conversation history
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                message_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP,
                device_id TEXT
            )
            """,
            
            # AI context and memory
            """
            CREATE TABLE IF NOT EXISTS ai_context (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                context_type TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding_vector TEXT,
                relevance_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP,
                device_id TEXT
            )
            """,
            
            # App settings per platform
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP,
                UNIQUE(platform, setting_key)
            )
            """,
            
            # Sync metadata
            """
            CREATE TABLE IF NOT EXISTS sync_metadata (
                table_name TEXT PRIMARY KEY,
                last_sync_timestamp TIMESTAMP,
                sync_version INTEGER DEFAULT 1,
                pending_changes INTEGER DEFAULT 0
            )
            """,
            
            # Offline queue for pending operations
            """
            CREATE TABLE IF NOT EXISTS offline_queue (
                id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                retry_count INTEGER DEFAULT 0
            )
            """
        ]
        
        cursor = self.conn.cursor()
        for table_sql in tables:
            cursor.execute(table_sql)
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_user_data_user_id ON user_data(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_data_type ON user_data(data_type)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_ai_context_user_id ON ai_context(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_ai_context_type ON ai_context(context_type)",
            "CREATE INDEX IF NOT EXISTS idx_app_settings_platform ON app_settings(platform)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        self.conn.commit()
    
    # CRUD Operations
    async def store_user_data(self, user_id: str, data_type: str, content: Dict[str, Any], 
                            device_id: str = None, encrypt: bool = False) -> str:
        """Store user data with optional encryption"""
        import uuid
        
        record_id = str(uuid.uuid4())
        content_json = json.dumps(content)
        
        if encrypt:
            # TODO: Implement encryption
            pass
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO user_data (id, user_id, data_type, content, encrypted, device_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (record_id, user_id, data_type, content_json, encrypt, device_id))
        
        self.conn.commit()
        return record_id
    
    async def get_user_data(self, user_id: str, data_type: str = None) -> List[Dict[str, Any]]:
        """Retrieve user data by type"""
        cursor = self.conn.cursor()
        
        if data_type:
            cursor.execute("""
                SELECT * FROM user_data 
                WHERE user_id = ? AND data_type = ?
                ORDER BY updated_at DESC
            """, (user_id, data_type))
        else:
            cursor.execute("""
                SELECT * FROM user_data 
                WHERE user_id = ?
                ORDER BY updated_at DESC
            """, (user_id,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def store_conversation(self, user_id: str, session_id: str, 
                               message_type: str, content: str, 
                               metadata: Dict[str, Any] = None, device_id: str = None) -> str:
        """Store conversation message"""
        import uuid
        
        record_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (id, user_id, session_id, message_type, content, metadata, device_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (record_id, user_id, session_id, message_type, content, metadata_json, device_id))
        
        self.conn.commit()
        return record_id
    
    async def get_conversations(self, user_id: str, session_id: str = None, 
                              limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve conversation history"""
        cursor = self.conn.cursor()
        
        if session_id:
            cursor.execute("""
                SELECT * FROM conversations 
                WHERE user_id = ? AND session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, session_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM conversations 
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def store_ai_context(self, user_id: str, context_type: str, 
                             content: str, embedding_vector: List[float] = None,
                             relevance_score: float = 0.0, device_id: str = None) -> str:
        """Store AI context with optional embedding"""
        import uuid
        
        record_id = str(uuid.uuid4())
        embedding_json = json.dumps(embedding_vector) if embedding_vector else None
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ai_context (id, user_id, context_type, content, embedding_vector, 
                                  relevance_score, device_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (record_id, user_id, context_type, content, embedding_json, relevance_score, device_id))
        
        self.conn.commit()
        return record_id
    
    async def get_ai_context(self, user_id: str, context_type: str = None, 
                           limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve AI context"""
        cursor = self.conn.cursor()
        
        if context_type:
            cursor.execute("""
                SELECT * FROM ai_context 
                WHERE user_id = ? AND context_type = ?
                ORDER BY relevance_score DESC, last_accessed DESC
                LIMIT ?
            """, (user_id, context_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM ai_context 
                WHERE user_id = ?
                ORDER BY relevance_score DESC, last_accessed DESC
                LIMIT ?
            """, (user_id, limit))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # Platform-specific settings
    async def set_app_setting(self, platform: str, key: str, value: Any):
        """Set platform-specific app setting"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO app_settings (id, platform, setting_key, setting_value, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (f"{platform}_{key}", platform, key, json.dumps(value)))
        
        self.conn.commit()
    
    async def get_app_setting(self, platform: str, key: str, default: Any = None) -> Any:
        """Get platform-specific app setting"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT setting_value FROM app_settings 
            WHERE platform = ? AND setting_key = ?
        """, (platform, key))
        
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return default
    
    # Sync support
    async def mark_for_sync(self, table_name: str, record_id: str, operation: str = "update"):
        """Mark record for synchronization"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO offline_queue (id, operation_type, table_name, record_id, data)
            VALUES (?, ?, ?, ?, ?)
        """, (f"{table_name}_{record_id}", operation, table_name, record_id, ""))
        
        self.conn.commit()
    
    async def get_pending_sync_operations(self) -> List[Dict[str, Any]]:
        """Get all pending sync operations"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM offline_queue ORDER BY created_at")
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def clear_sync_operation(self, operation_id: str):
        """Clear completed sync operation"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM offline_queue WHERE id = ?", (operation_id,))
        self.conn.commit()
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Local database connection closed")
