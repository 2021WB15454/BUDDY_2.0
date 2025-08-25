#!/usr/bin/env python3
"""
Optimized Local Database for BUDDY Cross-Platform AI Assistant

Platform-adaptive SQLite database with device-specific optimizations,
intelligent data partitioning, and performance monitoring.
"""

import sqlite3
import asyncio
import aiosqlite
import hashlib
import json
import time
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone, timedelta
from functools import lru_cache
import psutil
import threading

logger = logging.getLogger(__name__)


class DeviceCapability(Enum):
    HIGH_PERFORMANCE = "high"      # Desktop, high-end mobile
    MEDIUM_PERFORMANCE = "medium"  # Standard mobile, tablets
    LOW_PERFORMANCE = "low"        # Smartwatch, IoT devices
    CONSTRAINED = "constrained"    # Car systems, TV boxes


@dataclass
class DatabaseConfig:
    device_type: str
    capability: DeviceCapability
    max_storage_mb: int
    max_cache_size: int
    sync_batch_size: int
    index_strategy: str
    cleanup_interval_hours: int = 24
    
    @classmethod
    def from_device_type(cls, device_type: str) -> 'DatabaseConfig':
        """Create optimized config based on device type"""
        configs = {
            'desktop': cls(
                device_type='desktop',
                capability=DeviceCapability.HIGH_PERFORMANCE,
                max_storage_mb=500,
                max_cache_size=8000,
                sync_batch_size=100,
                index_strategy='full'
            ),
            'mobile': cls(
                device_type='mobile',
                capability=DeviceCapability.MEDIUM_PERFORMANCE,
                max_storage_mb=200,
                max_cache_size=4000,
                sync_batch_size=50,
                index_strategy='optimized'
            ),
            'watch': cls(
                device_type='watch',
                capability=DeviceCapability.LOW_PERFORMANCE,
                max_storage_mb=50,
                max_cache_size=1000,
                sync_batch_size=10,
                index_strategy='minimal'
            ),
            'tv': cls(
                device_type='tv',
                capability=DeviceCapability.CONSTRAINED,
                max_storage_mb=100,
                max_cache_size=2000,
                sync_batch_size=20,
                index_strategy='minimal'
            ),
            'car': cls(
                device_type='car',
                capability=DeviceCapability.CONSTRAINED,
                max_storage_mb=75,
                max_cache_size=1500,
                sync_batch_size=15,
                index_strategy='minimal'
            )
        }
        return configs.get(device_type, configs['mobile'])


class LRUCache:
    """Simple LRU Cache implementation for query results"""
    
    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self.cache = {}
        self.access_order = []
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Any:
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
            return None
    
    def put(self, key: str, value: Any):
        with self.lock:
            if key in self.cache:
                # Update existing
                self.access_order.remove(key)
            elif len(self.cache) >= self.maxsize:
                # Remove least recently used
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]
            
            self.cache[key] = value
            self.access_order.append(key)
    
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.access_order.clear()


class OptimizedLocalDatabase:
    """Platform-adaptive SQLite database with intelligent optimizations"""
    
    def __init__(self, config: DatabaseConfig, db_path: Optional[str] = None):
        self.config = config
        self.db_path = db_path or self._get_optimized_db_path()
        self.connection = None
        self.cache = LRUCache(maxsize=config.max_cache_size)
        self.performance_metrics = []
        self.last_cleanup = datetime.now()
        
    def _get_optimized_db_path(self) -> str:
        """Get optimized database path based on device type"""
        import os
        
        if self.config.device_type == 'mobile':
            # Use app-specific directory for mobile
            base_dir = os.path.expanduser("~/Documents/BUDDY")
        elif self.config.device_type == 'watch':
            # Use minimal storage for watch
            base_dir = os.path.expanduser("~/Library/Application Support/BUDDY")
        elif self.config.device_type in ['tv', 'car']:
            # Use temporary directory for constrained devices
            base_dir = "/tmp/BUDDY" if os.name != 'nt' else os.path.expanduser("~/AppData/Local/Temp/BUDDY")
        else:
            # Default for desktop
            base_dir = os.path.expanduser("~/AppData/Local/BUDDY") if os.name == 'nt' else os.path.expanduser("~/.buddy")
        
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, f"buddy_{self.config.device_type}.db")
    
    async def initialize(self):
        """Initialize database with platform-specific optimizations"""
        logger.info(f"Initializing optimized database for {self.config.device_type}")
        
        self.connection = await aiosqlite.connect(self.db_path)
        
        # Apply platform-specific PRAGMA settings
        optimizations = self._get_platform_optimizations()
        for pragma in optimizations:
            await self.connection.execute(pragma)
        
        # Create optimized schema
        await self._create_optimized_schema()
        
        # Set up indexing strategy
        await self._create_platform_indexes()
        
        # Commit all changes
        await self.connection.commit()
        
        logger.info(f"Database initialized with {len(optimizations)} optimizations")
    
    def _get_platform_optimizations(self) -> List[str]:
        """Get SQLite optimizations based on device capability"""
        base_pragmas = [
            "PRAGMA journal_mode = WAL",
            "PRAGMA synchronous = NORMAL",
            "PRAGMA cache_size = -2000",  # 2MB cache
            "PRAGMA temp_store = MEMORY",
            "PRAGMA foreign_keys = ON"
        ]
        
        if self.config.capability == DeviceCapability.HIGH_PERFORMANCE:
            return base_pragmas + [
                f"PRAGMA cache_size = -{self.config.max_cache_size}",  # Dynamic cache size
                "PRAGMA mmap_size = 268435456",  # 256MB memory mapping
                "PRAGMA optimize",
                "PRAGMA wal_autocheckpoint = 1000",
                "PRAGMA busy_timeout = 5000"
            ]
        elif self.config.capability == DeviceCapability.MEDIUM_PERFORMANCE:
            return base_pragmas + [
                f"PRAGMA cache_size = -{self.config.max_cache_size}",
                "PRAGMA mmap_size = 134217728",  # 128MB memory mapping
                "PRAGMA wal_autocheckpoint = 500",
                "PRAGMA busy_timeout = 3000"
            ]
        elif self.config.capability == DeviceCapability.LOW_PERFORMANCE:
            return [
                "PRAGMA journal_mode = DELETE",  # Less memory usage
                "PRAGMA synchronous = FAST",
                f"PRAGMA cache_size = -{self.config.max_cache_size}",
                "PRAGMA temp_store = FILE",
                "PRAGMA wal_autocheckpoint = 100",
                "PRAGMA busy_timeout = 1000"
            ]
        else:  # CONSTRAINED
            return [
                "PRAGMA journal_mode = TRUNCATE",
                "PRAGMA synchronous = OFF",      # Fastest, less safe
                f"PRAGMA cache_size = -{self.config.max_cache_size}",
                "PRAGMA temp_store = FILE",
                "PRAGMA auto_vacuum = INCREMENTAL",
                "PRAGMA wal_autocheckpoint = 50",
                "PRAGMA busy_timeout = 500"
            ]
    
    async def _create_optimized_schema(self):
        """Create schema optimized for cross-platform sync"""
        schema = f"""
        -- Conversations with platform-specific optimizations
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_id TEXT,
            content TEXT NOT NULL,
            message_type TEXT NOT NULL,
            metadata TEXT,
            timestamp INTEGER NOT NULL,        -- Use INTEGER for better performance
            device_id TEXT,
            sync_version INTEGER DEFAULT 1,
            sync_status INTEGER DEFAULT 0,    -- 0=pending, 1=synced, 2=conflict
            content_hash TEXT,                -- For change detection
            ttl INTEGER,                      -- Time-to-live for cleanup
            priority INTEGER DEFAULT 1,      -- Sync priority
            created_at INTEGER DEFAULT (strftime('%s', 'now'))
        ) {'WITHOUT ROWID' if self.config.capability != DeviceCapability.CONSTRAINED else ''};
        
        -- Lightweight user preferences
        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            device_specific INTEGER DEFAULT 0,
            user_id TEXT NOT NULL,
            updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            sync_hash TEXT,
            sync_version INTEGER DEFAULT 1
        ) {'WITHOUT ROWID' if self.config.capability != DeviceCapability.CONSTRAINED else ''};
        
        -- AI context with vector optimization
        CREATE TABLE IF NOT EXISTS ai_context (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            context_type TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding_preview TEXT,           -- First few dimensions for quick filtering
            relevance_score REAL DEFAULT 0.0,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            last_accessed INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            access_count INTEGER DEFAULT 1,
            sync_version INTEGER DEFAULT 1,
            device_id TEXT
        ) {'WITHOUT ROWID' if self.config.capability != DeviceCapability.CONSTRAINED else ''};
        
        -- Sync queue for offline operations
        CREATE TABLE IF NOT EXISTS sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id TEXT NOT NULL,
            operation TEXT NOT NULL,         -- INSERT, UPDATE, DELETE
            data TEXT,                       -- JSON data
            priority INTEGER DEFAULT 1,
            retry_count INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            scheduled_at INTEGER,            -- For delayed sync
            device_id TEXT
        );
        
        -- Performance metrics table
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_type TEXT NOT NULL,
            execution_time REAL NOT NULL,
            memory_usage REAL,
            timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            device_type TEXT NOT NULL,
            success INTEGER DEFAULT 1
        );
        
        -- Device registry for local tracking
        CREATE TABLE IF NOT EXISTS device_info (
            device_id TEXT PRIMARY KEY,
            device_type TEXT NOT NULL,
            device_name TEXT,
            user_id TEXT NOT NULL,
            capabilities TEXT,              -- JSON array
            last_sync INTEGER,
            sync_version INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            created_at INTEGER DEFAULT (strftime('%s', 'now'))
        ) {'WITHOUT ROWID' if self.config.capability != DeviceCapability.CONSTRAINED else ''};
        """
        
        await self.connection.executescript(schema)
    
    async def _create_platform_indexes(self):
        """Create indexes based on platform capability and usage patterns"""
        if self.config.index_strategy == 'full':
            # Full indexing for high-performance devices
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_conversations_user_time ON conversations(user_id, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_sync ON conversations(sync_status, sync_version)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_content_hash ON conversations(content_hash)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_device ON conversations(device_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_preferences_user ON user_preferences(user_id, device_specific)",
                "CREATE INDEX IF NOT EXISTS idx_context_user_type ON ai_context(user_id, context_type)",
                "CREATE INDEX IF NOT EXISTS idx_context_relevance ON ai_context(relevance_score DESC)",
                "CREATE INDEX IF NOT EXISTS idx_context_accessed ON ai_context(last_accessed DESC)",
                "CREATE INDEX IF NOT EXISTS idx_sync_queue_priority ON sync_queue(priority DESC, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_sync_queue_table ON sync_queue(table_name, operation)"
            ]
        elif self.config.index_strategy == 'optimized':
            # Balanced indexing for medium-performance devices
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_conversations_user_time ON conversations(user_id, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_sync ON conversations(sync_status, sync_version)",
                "CREATE INDEX IF NOT EXISTS idx_preferences_user ON user_preferences(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_context_user_type ON ai_context(user_id, context_type)",
                "CREATE INDEX IF NOT EXISTS idx_context_relevance ON ai_context(relevance_score DESC)",
                "CREATE INDEX IF NOT EXISTS idx_sync_queue_priority ON sync_queue(priority DESC, created_at)"
            ]
        else:  # minimal
            # Minimal indexing for constrained devices
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_sync ON conversations(sync_status)",
                "CREATE INDEX IF NOT EXISTS idx_sync_queue_basic ON sync_queue(priority, created_at)"
            ]
        
        for index in indexes:
            await self.connection.execute(index)
            
        logger.info(f"Created {len(indexes)} indexes with {self.config.index_strategy} strategy")
    
    async def store_conversation_optimized(self, user_id: str, session_id: str, content: str, 
                                         message_type: str, metadata: Optional[Dict] = None,
                                         device_id: Optional[str] = None) -> str:
        """Optimized conversation storage with caching and batching"""
        start_time = time.time()
        
        # Generate unique ID and content hash
        conversation_id = f"conv_{int(time.time() * 1000000)}_{hash(content) & 0x7FFFFFFF}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        # Prepare data
        metadata_json = json.dumps(metadata) if metadata else None
        timestamp = int(time.time())
        
        try:
            # Insert with optimized query
            query = """
            INSERT INTO conversations 
            (id, user_id, session_id, content, message_type, metadata, timestamp, 
             device_id, content_hash, sync_status, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """
            
            # Determine priority based on message type
            priority = 1 if message_type == 'user' else 2
            
            await self.connection.execute(query, (
                conversation_id, user_id, session_id, content, message_type,
                metadata_json, timestamp, device_id, content_hash, priority
            ))
            
            # Add to sync queue
            await self._add_to_sync_queue('conversations', conversation_id, 'INSERT', {
                'user_id': user_id,
                'content': content,
                'message_type': message_type,
                'timestamp': timestamp
            }, priority)
            
            await self.connection.commit()
            
            # Update cache
            cache_key = f"conv_{user_id}_{session_id}"
            self.cache.put(cache_key, None)  # Invalidate cache
            
            # Record performance metrics
            execution_time = time.time() - start_time
            await self._record_performance_metric('conversation_insert', execution_time, True)
            
            logger.debug(f"Stored conversation {conversation_id} in {execution_time:.3f}s")
            return conversation_id
            
        except Exception as e:
            execution_time = time.time() - start_time
            await self._record_performance_metric('conversation_insert', execution_time, False)
            logger.error(f"Failed to store conversation: {e}")
            raise
    
    async def get_conversations_optimized(self, user_id: str, session_id: Optional[str] = None,
                                        limit: int = 50, offset: int = 0) -> List[Dict]:
        """Optimized conversation retrieval with caching"""
        start_time = time.time()
        
        # Check cache first
        cache_key = f"conv_{user_id}_{session_id}_{limit}_{offset}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            # Build optimized query
            if session_id:
                query = """
                SELECT id, content, message_type, metadata, timestamp, device_id, sync_status
                FROM conversations 
                WHERE user_id = ? AND session_id = ?
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
                """
                params = (user_id, session_id, limit, offset)
            else:
                query = """
                SELECT id, content, message_type, metadata, timestamp, device_id, sync_status
                FROM conversations 
                WHERE user_id = ?
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
                """
                params = (user_id, limit, offset)
            
            cursor = await self.connection.execute(query, params)
            rows = await cursor.fetchall()
            
            # Process results
            conversations = []
            for row in rows:
                conversation = {
                    'id': row[0],
                    'content': row[1],
                    'message_type': row[2],
                    'metadata': json.loads(row[3]) if row[3] else {},
                    'timestamp': row[4],
                    'device_id': row[5],
                    'sync_status': row[6]
                }
                conversations.append(conversation)
            
            # Cache result
            self.cache.put(cache_key, conversations)
            
            # Record performance metrics
            execution_time = time.time() - start_time
            await self._record_performance_metric('conversation_select', execution_time, True)
            
            logger.debug(f"Retrieved {len(conversations)} conversations in {execution_time:.3f}s")
            return conversations
            
        except Exception as e:
            execution_time = time.time() - start_time
            await self._record_performance_metric('conversation_select', execution_time, False)
            logger.error(f"Failed to retrieve conversations: {e}")
            raise
    
    async def set_user_preference_optimized(self, user_id: str, key: str, value: Any,
                                          device_specific: bool = False) -> None:
        """Optimized preference storage with conflict detection"""
        start_time = time.time()
        
        try:
            # Serialize value
            value_json = json.dumps(value)
            sync_hash = hashlib.sha256(f"{key}{value_json}".encode()).hexdigest()[:16]
            timestamp = int(time.time())
            
            # Upsert preference
            query = """
            INSERT OR REPLACE INTO user_preferences 
            (key, value, device_specific, user_id, updated_at, sync_hash, sync_version)
            VALUES (?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT sync_version + 1 FROM user_preferences WHERE key = ?), 1))
            """
            
            await self.connection.execute(query, (
                key, value_json, int(device_specific), user_id, timestamp, sync_hash, key
            ))
            
            # Add to sync queue
            await self._add_to_sync_queue('user_preferences', key, 'UPSERT', {
                'key': key,
                'value': value,
                'device_specific': device_specific,
                'user_id': user_id
            }, 2)  # Medium priority
            
            await self.connection.commit()
            
            # Invalidate cache
            cache_key = f"pref_{user_id}_{key}"
            self.cache.put(cache_key, None)
            
            execution_time = time.time() - start_time
            await self._record_performance_metric('preference_upsert', execution_time, True)
            
        except Exception as e:
            execution_time = time.time() - start_time
            await self._record_performance_metric('preference_upsert', execution_time, False)
            logger.error(f"Failed to set preference {key}: {e}")
            raise
    
    async def _add_to_sync_queue(self, table_name: str, record_id: str, operation: str,
                               data: Dict, priority: int = 1) -> None:
        """Add operation to sync queue for offline synchronization"""
        try:
            data_json = json.dumps(data)
            timestamp = int(time.time())
            
            query = """
            INSERT INTO sync_queue (table_name, record_id, operation, data, priority, created_at, device_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            await self.connection.execute(query, (
                table_name, record_id, operation, data_json, priority, timestamp, 
                self.config.device_type
            ))
            
        except Exception as e:
            logger.error(f"Failed to add to sync queue: {e}")
    
    async def _record_performance_metric(self, query_type: str, execution_time: float, 
                                       success: bool) -> None:
        """Record performance metrics for monitoring"""
        try:
            # Get current memory usage
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            query = """
            INSERT INTO performance_metrics (query_type, execution_time, memory_usage, device_type, success)
            VALUES (?, ?, ?, ?, ?)
            """
            
            await self.connection.execute(query, (
                query_type, execution_time, memory_usage, self.config.device_type, int(success)
            ))
            
            # Commit periodically (not every metric)
            if len(self.performance_metrics) % 10 == 0:
                await self.connection.commit()
                
        except Exception as e:
            logger.warning(f"Failed to record performance metric: {e}")
    
    async def get_sync_queue_items(self, limit: int = None) -> List[Dict]:
        """Get pending sync operations"""
        try:
            query = """
            SELECT id, table_name, record_id, operation, data, priority, retry_count, created_at
            FROM sync_queue 
            ORDER BY priority ASC, created_at ASC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = await self.connection.execute(query)
            rows = await cursor.fetchall()
            
            sync_items = []
            for row in rows:
                item = {
                    'id': row[0],
                    'table_name': row[1],
                    'record_id': row[2],
                    'operation': row[3],
                    'data': json.loads(row[4]) if row[4] else {},
                    'priority': row[5],
                    'retry_count': row[6],
                    'created_at': row[7]
                }
                sync_items.append(item)
            
            return sync_items
            
        except Exception as e:
            logger.error(f"Failed to get sync queue items: {e}")
            return []
    
    async def remove_sync_queue_item(self, item_id: int) -> None:
        """Remove item from sync queue after successful sync"""
        try:
            await self.connection.execute("DELETE FROM sync_queue WHERE id = ?", (item_id,))
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to remove sync queue item {item_id}: {e}")
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Cleanup expired data based on retention policies"""
        if datetime.now() - self.last_cleanup < timedelta(hours=self.config.cleanup_interval_hours):
            return {"status": "skipped", "reason": "cleanup interval not reached"}
        
        cleanup_stats = {}
        
        try:
            # Define retention policies based on device capability
            if self.config.capability == DeviceCapability.CONSTRAINED:
                policies = {
                    "conversations": {"max_records": 1000, "max_age_days": 7},
                    "ai_context": {"max_records": 500, "max_age_days": 3},
                    "performance_metrics": {"max_records": 100, "max_age_days": 1}
                }
            elif self.config.capability == DeviceCapability.LOW_PERFORMANCE:
                policies = {
                    "conversations": {"max_records": 5000, "max_age_days": 30},
                    "ai_context": {"max_records": 2000, "max_age_days": 14},
                    "performance_metrics": {"max_records": 500, "max_age_days": 7}
                }
            else:
                policies = {
                    "conversations": {"max_records": 50000, "max_age_days": 365},
                    "ai_context": {"max_records": 20000, "max_age_days": 90},
                    "performance_metrics": {"max_records": 2000, "max_age_days": 30}
                }
            
            # Apply cleanup policies
            for table_name, policy in policies.items():
                deleted_count = await self._cleanup_table(table_name, policy)
                cleanup_stats[table_name] = deleted_count
            
            # Update last cleanup time
            self.last_cleanup = datetime.now()
            
            # Clear cache after cleanup
            self.cache.clear()
            
            logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {"error": str(e)}
    
    async def _cleanup_table(self, table_name: str, policy: Dict) -> int:
        """Cleanup a specific table based on policy"""
        max_records = policy.get("max_records", 10000)
        max_age_days = policy.get("max_age_days", 30)
        
        # Calculate age threshold
        age_threshold = int((datetime.now() - timedelta(days=max_age_days)).timestamp())
        
        # Cleanup by age
        age_query = f"""
        DELETE FROM {table_name} 
        WHERE timestamp < ? OR created_at < ?
        """
        cursor = await self.connection.execute(age_query, (age_threshold, age_threshold))
        age_deleted = cursor.rowcount
        
        # Cleanup by count (keep most recent)
        count_query = f"""
        DELETE FROM {table_name} 
        WHERE id NOT IN (
            SELECT id FROM {table_name} 
            ORDER BY COALESCE(timestamp, created_at) DESC 
            LIMIT ?
        )
        """
        cursor = await self.connection.execute(count_query, (max_records,))
        count_deleted = cursor.rowcount
        
        await self.connection.commit()
        
        total_deleted = age_deleted + count_deleted
        logger.debug(f"Cleaned up {total_deleted} records from {table_name}")
        
        return total_deleted
    
    async def get_performance_report(self) -> Dict:
        """Generate performance report from recorded metrics"""
        try:
            query = """
            SELECT 
                query_type,
                COUNT(*) as count,
                AVG(execution_time) as avg_time,
                MAX(execution_time) as max_time,
                MIN(execution_time) as min_time,
                AVG(memory_usage) as avg_memory,
                SUM(success) * 100.0 / COUNT(*) as success_rate
            FROM performance_metrics 
            WHERE timestamp > strftime('%s', 'now', '-24 hours')
            GROUP BY query_type
            ORDER BY count DESC
            """
            
            cursor = await self.connection.execute(query)
            rows = await cursor.fetchall()
            
            report = {
                "device_type": self.config.device_type,
                "capability": self.config.capability.value,
                "cache_hit_rate": getattr(self.cache, 'hit_rate', 0),
                "query_performance": {}
            }
            
            for row in rows:
                report["query_performance"][row[0]] = {
                    "count": row[1],
                    "avg_time": round(row[2], 4),
                    "max_time": round(row[3], 4),
                    "min_time": round(row[4], 4),
                    "avg_memory_mb": round(row[5], 2),
                    "success_rate": round(row[6], 2)
                }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {"error": str(e)}
    
    async def optimize_database(self) -> Dict[str, Any]:
        """Run database optimization commands"""
        try:
            start_time = time.time()
            
            # Run ANALYZE to update query planner statistics
            await self.connection.execute("ANALYZE")
            
            # Run VACUUM if needed (only for high-performance devices)
            if self.config.capability == DeviceCapability.HIGH_PERFORMANCE:
                await self.connection.execute("VACUUM")
            
            # Optimize WAL checkpoint
            await self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            
            execution_time = time.time() - start_time
            
            logger.info(f"Database optimization completed in {execution_time:.2f}s")
            
            return {
                "status": "completed",
                "execution_time": execution_time,
                "operations": ["ANALYZE", "WAL_CHECKPOINT"]
            }
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def close(self):
        """Close database connection and cleanup"""
        try:
            if self.connection:
                await self.connection.close()
                self.connection = None
            
            # Clear cache
            self.cache.clear()
            
            logger.info(f"Optimized database closed for {self.config.device_type}")
            
        except Exception as e:
            logger.error(f"Error closing database: {e}")


# Factory function for easy database creation
def create_optimized_database(device_type: str, db_path: Optional[str] = None) -> OptimizedLocalDatabase:
    """Create an optimized database for the specified device type"""
    config = DatabaseConfig.from_device_type(device_type)
    return OptimizedLocalDatabase(config, db_path)


# Usage example
async def main():
    """Example usage of OptimizedLocalDatabase"""
    # Create database for mobile device
    mobile_db = create_optimized_database('mobile')
    await mobile_db.initialize()
    
    # Store a conversation
    conv_id = await mobile_db.store_conversation_optimized(
        user_id="test_user",
        session_id="session_1",
        content="Hello BUDDY!",
        message_type="user",
        metadata={"device": "iPhone"},
        device_id="mobile_123"
    )
    
    # Retrieve conversations
    conversations = await mobile_db.get_conversations_optimized("test_user", limit=10)
    print(f"Retrieved {len(conversations)} conversations")
    
    # Set preference
    await mobile_db.set_user_preference_optimized("test_user", "theme", "dark", device_specific=True)
    
    # Get performance report
    report = await mobile_db.get_performance_report()
    print(f"Performance report: {report}")
    
    # Cleanup
    await mobile_db.cleanup_expired_data()
    await mobile_db.close()


if __name__ == "__main__":
    asyncio.run(main())
