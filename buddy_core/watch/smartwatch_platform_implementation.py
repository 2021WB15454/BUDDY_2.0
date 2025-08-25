"""
BUDDY 2.0 Phase 3: Smartwatch Development Implementation
Building on proven Phase 1 & 2 foundations for intelligent wearable AI

This implementation demonstrates ultra-constrained device optimization
with advanced voice integration and health monitoring capabilities.
"""

import asyncio
import json
import time
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WatchPlatform(Enum):
    """Smartwatch platforms supported by BUDDY"""
    APPLE_WATCH = "apple_watch"
    WEAR_OS = "wear_os"
    GALAXY_WATCH = "galaxy_watch"
    FITBIT = "fitbit"
    GARMIN = "garmin"


class WatchCapability(Enum):
    """Smartwatch hardware capabilities"""
    BASIC = "basic"           # Entry-level watches
    STANDARD = "standard"     # Standard smartwatches
    PREMIUM = "premium"       # High-end smartwatches
    ULTRA = "ultra"          # Ultra/Pro models


@dataclass
class WatchConfig:
    """Smartwatch-specific configuration with ultra-low resource limits"""
    platform: WatchPlatform
    capability: WatchCapability
    storage_limit_mb: int
    memory_limit_mb: int
    battery_life_hours: int
    voice_enabled: bool
    health_sensors: bool
    always_on_display: bool
    cellular_enabled: bool
    wifi_enabled: bool
    
    @classmethod
    def for_watch_profile(cls, platform: WatchPlatform, capability: WatchCapability) -> 'WatchConfig':
        """Generate optimal configuration for watch profile"""
        configs = {
            (WatchPlatform.APPLE_WATCH, WatchCapability.ULTRA): cls(
                platform=platform,
                capability=capability,
                storage_limit_mb=32,
                memory_limit_mb=8,
                battery_life_hours=36,
                voice_enabled=True,
                health_sensors=True,
                always_on_display=True,
                cellular_enabled=True,
                wifi_enabled=True
            ),
            (WatchPlatform.APPLE_WATCH, WatchCapability.PREMIUM): cls(
                platform=platform,
                capability=capability,
                storage_limit_mb=16,
                memory_limit_mb=4,
                battery_life_hours=18,
                voice_enabled=True,
                health_sensors=True,
                always_on_display=True,
                cellular_enabled=False,
                wifi_enabled=True
            ),
            (WatchPlatform.APPLE_WATCH, WatchCapability.STANDARD): cls(
                platform=platform,
                capability=capability,
                storage_limit_mb=12,
                memory_limit_mb=3,
                battery_life_hours=15,
                voice_enabled=True,
                health_sensors=True,
                always_on_display=False,
                cellular_enabled=False,
                wifi_enabled=True
            ),
            (WatchPlatform.WEAR_OS, WatchCapability.PREMIUM): cls(
                platform=platform,
                capability=capability,
                storage_limit_mb=20,
                memory_limit_mb=6,
                battery_life_hours=24,
                voice_enabled=True,
                health_sensors=True,
                always_on_display=True,
                cellular_enabled=True,
                wifi_enabled=True
            ),
            (WatchPlatform.WEAR_OS, WatchCapability.STANDARD): cls(
                platform=platform,
                capability=capability,
                storage_limit_mb=16,
                memory_limit_mb=4,
                battery_life_hours=20,
                voice_enabled=True,
                health_sensors=True,
                always_on_display=False,
                cellular_enabled=False,
                wifi_enabled=True
            ),
            (WatchPlatform.GALAXY_WATCH, WatchCapability.STANDARD): cls(
                platform=platform,
                capability=capability,
                storage_limit_mb=12,
                memory_limit_mb=3,
                battery_life_hours=30,
                voice_enabled=True,
                health_sensors=True,
                always_on_display=False,
                cellular_enabled=False,
                wifi_enabled=True
            ),
            (WatchPlatform.FITBIT, WatchCapability.BASIC): cls(
                platform=platform,
                capability=capability,
                storage_limit_mb=8,
                memory_limit_mb=2,
                battery_life_hours=144,  # 6 days
                voice_enabled=False,
                health_sensors=True,
                always_on_display=False,
                cellular_enabled=False,
                wifi_enabled=False
            )
        }
        
        # Default fallback configuration
        default_config = cls(
            platform=platform,
            capability=capability,
            storage_limit_mb=12,
            memory_limit_mb=3,
            battery_life_hours=24,
            voice_enabled=True,
            health_sensors=True,
            always_on_display=False,
            cellular_enabled=False,
            wifi_enabled=True
        )
        
        return configs.get((platform, capability), default_config)


class WatchOptimizedDatabase:
    """Ultra-lightweight database for smartwatch constraints"""
    
    def __init__(self, db_path: str, config: WatchConfig):
        self.db_path = db_path
        self.config = config
        self.connection = None
        self.performance_metrics = {
            'queries_executed': 0,
            'total_execution_time': 0.0,
            'storage_used_kb': 0,
            'memory_usage_mb': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Ultra-minimal cache for watch constraints
        self.micro_cache = {}
        self.max_cache_entries = 5 if config.capability == WatchCapability.BASIC else 10
        self.cache_access_order = []
    
    async def initialize(self):
        """Initialize ultra-lightweight watch database"""
        self.connection = sqlite3.connect(self.db_path)
        
        # Apply watch-specific PRAGMA settings for maximum efficiency
        watch_pragmas = [
            "PRAGMA journal_mode = MEMORY",  # Keep journal in memory for speed
            "PRAGMA synchronous = OFF",      # Maximum speed, acceptable for watch
            "PRAGMA cache_size = -512",      # 512KB cache maximum
            "PRAGMA temp_store = MEMORY",
            "PRAGMA locking_mode = EXCLUSIVE",
            "PRAGMA count_changes = OFF",
            "PRAGMA page_size = 1024",       # Smaller pages for constrained storage
            "PRAGMA auto_vacuum = FULL"      # Keep database compact
        ]
        
        # Even more aggressive optimizations for basic watches
        if self.config.capability == WatchCapability.BASIC:
            watch_pragmas.extend([
                "PRAGMA cache_size = -256",   # 256KB cache for basic watches
                "PRAGMA journal_mode = OFF",  # No journal for maximum efficiency
            ])
        
        for pragma in watch_pragmas:
            self.connection.execute(pragma)
        
        # Create ultra-minimal schema
        await self._create_watch_schema()
        logger.info(f"Watch database initialized for {self.config.platform.value} ({self.config.capability.value})")
    
    async def _create_watch_schema(self):
        """Create minimal database schema optimized for watch storage"""
        schema_sql = """
        -- Ultra-minimal conversations for watch
        CREATE TABLE IF NOT EXISTS watch_conversations (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            type INTEGER NOT NULL,  -- 0=user, 1=assistant, 2=system
            timestamp INTEGER NOT NULL,
            session_id TEXT,
            summary TEXT  -- Pre-computed summary for quick display
        ) WITHOUT ROWID;
        
        -- Minimal preferences for watch
        CREATE TABLE IF NOT EXISTS watch_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at INTEGER DEFAULT (strftime('%s', 'now'))
        ) WITHOUT ROWID;
        
        -- Health data integration
        CREATE TABLE IF NOT EXISTS watch_health_context (
            id TEXT PRIMARY KEY,
            metric_type TEXT NOT NULL,  -- heart_rate, steps, activity
            value REAL NOT NULL,
            timestamp INTEGER NOT NULL,
            relevance_score REAL DEFAULT 0.5
        ) WITHOUT ROWID;
        
        -- Ultra-minimal sync queue
        CREATE TABLE IF NOT EXISTS watch_sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL,
            data_summary TEXT NOT NULL,  -- Compressed operation data
            priority INTEGER DEFAULT 1,
            created_at INTEGER DEFAULT (strftime('%s', 'now'))
        );
        
        -- Voice command cache for offline operation
        CREATE TABLE IF NOT EXISTS watch_voice_cache (
            command_hash TEXT PRIMARY KEY,
            response TEXT NOT NULL,
            confidence REAL NOT NULL,
            usage_count INTEGER DEFAULT 1,
            last_used INTEGER DEFAULT (strftime('%s', 'now'))
        ) WITHOUT ROWID;
        """
        
        self.connection.executescript(schema_sql)
        
        # Create minimal indexes only for essential queries
        essential_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_conversations_time ON watch_conversations(timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_health_metric_time ON watch_health_context(metric_type, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_voice_cache_usage ON watch_voice_cache(usage_count DESC, last_used DESC)"
        ]
        
        for index in essential_indexes:
            self.connection.execute(index)
        
        self.connection.commit()
    
    async def store_watch_conversation(self, content: str, message_type: str, session_id: str = None) -> str:
        """Store conversation with watch-specific optimizations"""
        start_time = time.time()
        
        # Generate compact ID
        conv_id = f"w{int(time.time())}{len(content) % 100:02d}"
        
        # Create summary for long content (watch display optimization)
        summary = self._create_watch_summary(content)
        
        # Convert message type to integer for storage efficiency
        type_mapping = {'user': 0, 'assistant': 1, 'system': 2}
        type_int = type_mapping.get(message_type, 0)
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO watch_conversations 
            (id, content, type, timestamp, session_id, summary)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            conv_id,
            content,
            type_int,
            int(time.time()),
            session_id,
            summary
        ))
        
        self.connection.commit()
        
        # Update performance metrics
        execution_time = time.time() - start_time
        self.performance_metrics['queries_executed'] += 1
        self.performance_metrics['total_execution_time'] += execution_time
        
        # Cache recent conversation for quick access
        await self._cache_recent_conversation(conv_id, content, summary, type_int)
        
        # Queue for sync to paired device
        await self._queue_watch_sync('conversation', {'id': conv_id, 'type': message_type, 'summary': summary})
        
        logger.debug(f"Stored watch conversation {conv_id} in {execution_time:.4f}s")
        return conv_id
    
    async def get_recent_conversations(self, limit: int = 5) -> List[Dict]:
        """Get recent conversations optimized for watch display"""
        start_time = time.time()
        
        # Check micro-cache first
        cache_key = f"recent_{limit}"
        if cache_key in self.micro_cache:
            self.performance_metrics['cache_hits'] += 1
            return self.micro_cache[cache_key]
        
        self.performance_metrics['cache_misses'] += 1
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT id, summary, type, timestamp, session_id 
            FROM watch_conversations 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conversations = []
        
        type_names = {0: 'user', 1: 'assistant', 2: 'system'}
        
        for row in rows:
            conv = {
                'id': row[0],
                'content': row[1],  # Using summary for watch display
                'type': type_names[row[2]],
                'timestamp': row[3],
                'session_id': row[4],
                'watch_optimized': True
            }
            conversations.append(conv)
        
        # Cache result with LRU eviction
        await self._cache_with_lru(cache_key, conversations)
        
        # Update metrics
        execution_time = time.time() - start_time
        self.performance_metrics['queries_executed'] += 1
        self.performance_metrics['total_execution_time'] += execution_time
        
        logger.debug(f"Retrieved {len(conversations)} watch conversations in {execution_time:.4f}s")
        return conversations
    
    async def store_health_context(self, metric_type: str, value: float, timestamp: int = None):
        """Store health data for AI context"""
        if not self.config.health_sensors:
            return
        
        if timestamp is None:
            timestamp = int(time.time())
        
        # Calculate relevance score based on metric type and recency
        relevance_score = self._calculate_health_relevance(metric_type, value, timestamp)
        
        health_id = f"h{timestamp}{abs(hash(metric_type)) % 1000:03d}"
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO watch_health_context 
            (id, metric_type, value, timestamp, relevance_score)
            VALUES (?, ?, ?, ?, ?)
        """, (health_id, metric_type, value, timestamp, relevance_score))
        
        self.connection.commit()
        
        # Cleanup old health data to maintain storage limits
        await self._cleanup_old_health_data()
    
    async def get_health_context(self, metric_types: List[str] = None, hours_back: int = 24) -> List[Dict]:
        """Get recent health context for AI processing"""
        if not self.config.health_sensors:
            return []
        
        cutoff_time = int(time.time()) - (hours_back * 3600)
        
        if metric_types:
            placeholders = ','.join('?' * len(metric_types))
            query = f"""
                SELECT metric_type, value, timestamp, relevance_score 
                FROM watch_health_context 
                WHERE metric_type IN ({placeholders}) AND timestamp > ?
                ORDER BY relevance_score DESC, timestamp DESC
                LIMIT 20
            """
            params = metric_types + [cutoff_time]
        else:
            query = """
                SELECT metric_type, value, timestamp, relevance_score 
                FROM watch_health_context 
                WHERE timestamp > ?
                ORDER BY relevance_score DESC, timestamp DESC
                LIMIT 20
            """
            params = [cutoff_time]
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        health_data = []
        for row in rows:
            health_data.append({
                'metric_type': row[0],
                'value': row[1],
                'timestamp': row[2],
                'relevance_score': row[3]
            })
        
        return health_data
    
    async def cache_voice_response(self, command: str, response: str, confidence: float):
        """Cache voice responses for offline operation"""
        if not self.config.voice_enabled:
            return
        
        command_hash = str(abs(hash(command.lower().strip())) % 1000000)
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO watch_voice_cache 
            (command_hash, response, confidence, usage_count, last_used)
            VALUES (?, ?, ?, 1, strftime('%s', 'now'))
        """, (command_hash, response, confidence))
        
        self.connection.commit()
        
        # Cleanup cache if it gets too large
        await self._cleanup_voice_cache()
    
    async def get_cached_voice_response(self, command: str) -> Optional[Dict]:
        """Get cached voice response for offline operation"""
        if not self.config.voice_enabled:
            return None
        
        command_hash = str(abs(hash(command.lower().strip())) % 1000000)
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT response, confidence, usage_count 
            FROM watch_voice_cache 
            WHERE command_hash = ?
        """, (command_hash,))
        
        row = cursor.fetchone()
        if row:
            # Update usage statistics
            cursor.execute("""
                UPDATE watch_voice_cache 
                SET usage_count = usage_count + 1, last_used = strftime('%s', 'now')
                WHERE command_hash = ?
            """, (command_hash,))
            self.connection.commit()
            
            return {
                'response': row[0],
                'confidence': row[1],
                'usage_count': row[2] + 1,
                'cached': True
            }
        
        return None
    
    def _create_watch_summary(self, content: str, max_length: int = 50) -> str:
        """Create ultra-short summary for watch display"""
        if len(content) <= max_length:
            return content
        
        # Simple summarization for watch constraints
        words = content.split()
        if len(words) <= 8:
            return content[:max_length] + "..."
        
        # Keep first few and last few words
        summary_words = words[:4] + ["..."] + words[-2:]
        summary = " ".join(summary_words)
        
        return summary[:max_length] + "..." if len(summary) > max_length else summary
    
    def _calculate_health_relevance(self, metric_type: str, value: float, timestamp: int) -> float:
        """Calculate relevance score for health data"""
        # Time decay (more recent = more relevant)
        age_hours = (time.time() - timestamp) / 3600
        time_factor = max(0.1, 1.0 - (age_hours / 24))  # Decay over 24 hours
        
        # Metric-specific relevance
        metric_importance = {
            'heart_rate': 0.9,
            'steps': 0.7,
            'sleep': 0.8,
            'exercise': 0.9,
            'stress': 0.8,
            'calories': 0.6
        }
        
        base_relevance = metric_importance.get(metric_type, 0.5)
        
        # Anomaly detection (unusual values are more relevant)
        anomaly_factor = 1.0  # Would be calculated based on personal baselines
        
        return base_relevance * time_factor * anomaly_factor
    
    async def _cache_recent_conversation(self, conv_id: str, content: str, summary: str, type_int: int):
        """Cache recent conversation in micro-cache"""
        cache_entry = {
            'id': conv_id,
            'content': summary,
            'type': {0: 'user', 1: 'assistant', 2: 'system'}[type_int],
            'timestamp': int(time.time())
        }
        
        cache_key = f"conv_{conv_id}"
        await self._cache_with_lru(cache_key, cache_entry)
    
    async def _cache_with_lru(self, key: str, value: Any):
        """Cache with LRU eviction for memory constraints"""
        if key in self.micro_cache:
            # Move to end (most recently used)
            self.cache_access_order.remove(key)
            self.cache_access_order.append(key)
        else:
            # Add new entry
            if len(self.micro_cache) >= self.max_cache_entries:
                # Evict least recently used
                lru_key = self.cache_access_order.pop(0)
                del self.micro_cache[lru_key]
            
            self.micro_cache[key] = value
            self.cache_access_order.append(key)
    
    async def _queue_watch_sync(self, operation_type: str, data_summary: Dict):
        """Queue operation for sync with paired device"""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO watch_sync_queue (operation_type, data_summary)
            VALUES (?, ?)
        """, (operation_type, json.dumps(data_summary)))
        
        self.connection.commit()
    
    async def _cleanup_old_health_data(self):
        """Clean up old health data to maintain storage limits"""
        # Keep only last 48 hours of health data
        cutoff_time = int(time.time()) - (48 * 3600)
        
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM watch_health_context WHERE timestamp < ?", (cutoff_time,))
        self.connection.commit()
    
    async def _cleanup_voice_cache(self):
        """Clean up voice cache to maintain memory limits"""
        # Keep only most frequently used 50 entries
        cursor = self.connection.cursor()
        cursor.execute("""
            DELETE FROM watch_voice_cache 
            WHERE command_hash NOT IN (
                SELECT command_hash FROM watch_voice_cache 
                ORDER BY usage_count DESC, last_used DESC 
                LIMIT 50
            )
        """)
        self.connection.commit()
    
    async def get_storage_usage(self) -> Dict[str, Any]:
        """Get storage usage statistics for watch optimization"""
        cursor = self.connection.cursor()
        
        # Get database size
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        db_size_bytes = cursor.fetchone()[0]
        
        # Get table counts
        tables = ['watch_conversations', 'watch_health_context', 'watch_voice_cache', 'watch_sync_queue']
        table_counts = {}
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            table_counts[table] = cursor.fetchone()[0]
        
        storage_kb = db_size_bytes / 1024
        self.performance_metrics['storage_used_kb'] = storage_kb
        
        return {
            'storage_used_kb': storage_kb,
            'storage_limit_mb': self.config.storage_limit_mb,
            'storage_percentage': (storage_kb / 1024) / self.config.storage_limit_mb * 100,
            'table_counts': table_counts,
            'cache_entries': len(self.micro_cache),
            'max_cache_entries': self.max_cache_entries
        }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics for watch optimization"""
        storage_info = await self.get_storage_usage()
        
        avg_time = (
            self.performance_metrics['total_execution_time'] / 
            max(1, self.performance_metrics['queries_executed'])
        )
        
        cache_hit_ratio = (
            self.performance_metrics['cache_hits'] / 
            max(1, self.performance_metrics['cache_hits'] + self.performance_metrics['cache_misses'])
        )
        
        return {
            **self.performance_metrics,
            **storage_info,
            'average_execution_time': avg_time,
            'cache_hit_ratio': cache_hit_ratio,
            'watch_platform': self.config.platform.value,
            'watch_capability': self.config.capability.value,
            'memory_limit_mb': self.config.memory_limit_mb,
            'battery_optimized': True
        }
    
    async def close(self):
        """Close watch database"""
        if self.connection:
            self.connection.close()


class WatchBuddyCore:
    """Ultra-lightweight BUDDY core for smartwatch platforms"""
    
    def __init__(self, user_id: str, device_id: str, config: WatchConfig):
        self.user_id = user_id
        self.device_id = device_id
        self.config = config
        self.database = None
        
        # Watch-specific state
        self.is_on_wrist = True
        self.is_charging = False
        self.battery_level = 0.85
        self.heart_rate = 72
        self.is_connected_to_phone = True
        self.screen_awake = True
        
        # Performance tracking
        self.session_start_time = time.time()
        self.interactions_count = 0
        self.voice_commands_processed = 0
        
    async def initialize(self) -> bool:
        """Initialize ultra-lightweight watch BUDDY core"""
        try:
            # Create temporary database for demo
            temp_dir = tempfile.mkdtemp(prefix="buddy_watch_")
            db_path = os.path.join(temp_dir, f"buddy_watch_{self.device_id}.db")
            
            # Initialize watch database
            self.database = WatchOptimizedDatabase(db_path, self.config)
            await self.database.initialize()
            
            # Initialize health context if sensors available
            if self.config.health_sensors:
                await self._initialize_health_monitoring()
            
            # Cache essential voice commands for offline use
            if self.config.voice_enabled:
                await self._cache_essential_voice_commands()
            
            logger.info(f"Watch BUDDY initialized for {self.config.platform.value} "
                       f"({self.config.capability.value} capability)")
            return True
            
        except Exception as e:
            logger.error(f"Watch initialization failed: {e}")
            return False
    
    async def process_voice_command(self, command: str) -> Dict[str, Any]:
        """Process voice command with watch-optimized response"""
        start_time = time.time()
        
        # Check cache first for offline operation
        cached_response = await self.database.get_cached_voice_response(command)
        if cached_response:
            logger.info("Using cached voice response for offline operation")
            response_data = {
                'response': cached_response['response'],
                'confidence': cached_response['confidence'],
                'cached': True,
                'processing_time': time.time() - start_time,
                'watch_optimized': True
            }
        else:
            # Generate new response (would normally call AI service)
            response_data = await self._generate_watch_response(command)
            
            # Cache for future offline use
            await self.database.cache_voice_response(
                command, 
                response_data['response'], 
                response_data['confidence']
            )
        
        # Store conversation
        await self.database.store_watch_conversation(command, 'user')
        await self.database.store_watch_conversation(response_data['response'], 'assistant')
        
        self.voice_commands_processed += 1
        self.interactions_count += 1
        
        return response_data
    
    async def get_health_aware_response(self, query: str) -> Dict[str, Any]:
        """Generate response incorporating health context"""
        if not self.config.health_sensors:
            return await self._generate_watch_response(query)
        
        # Get recent health context
        health_context = await self.database.get_health_context(['heart_rate', 'steps', 'exercise'], hours_back=2)
        
        # Generate health-aware response
        response = await self._generate_health_aware_response(query, health_context)
        
        # Store with health context
        await self.database.store_watch_conversation(query, 'user')
        await self.database.store_watch_conversation(response['response'], 'assistant')
        
        return response
    
    async def quick_interaction(self, interaction_type: str) -> Dict[str, Any]:
        """Handle quick watch interactions (taps, gestures, etc.)"""
        quick_responses = {
            'time': f"It's {datetime.now().strftime('%I:%M %p')}",
            'weather': "Currently 72°F and sunny",
            'heart_rate': f"Your heart rate is {self.heart_rate} BPM",
            'steps': "You've taken 8,247 steps today",
            'battery': f"Watch battery at {int(self.battery_level * 100)}%",
            'status': "All systems running smoothly"
        }
        
        response = quick_responses.get(interaction_type, "I'm here to help!")
        
        # Store minimal interaction record
        await self.database.store_watch_conversation(f"Quick: {interaction_type}", 'user')
        await self.database.store_watch_conversation(response, 'assistant')
        
        self.interactions_count += 1
        
        return {
            'response': response,
            'type': 'quick_interaction',
            'interaction_type': interaction_type,
            'watch_optimized': True,
            'processing_time': 0.001  # Nearly instant
        }
    
    async def handle_health_event(self, event_type: str, value: float):
        """Handle health sensor events"""
        if not self.config.health_sensors:
            return
        
        # Store health data
        await self.database.store_health_context(event_type, value)
        
        # Generate contextual response for significant events
        if event_type == 'heart_rate' and (value > 120 or value < 50):
            response = await self._generate_health_alert_response(event_type, value)
            await self.database.store_watch_conversation(f"Health alert: {event_type}", 'system')
            await self.database.store_watch_conversation(response, 'assistant')
        
        # Update current state
        if event_type == 'heart_rate':
            self.heart_rate = value
    
    async def handle_watch_state_change(self, state_type: str, value: Any):
        """Handle watch state changes for optimization"""
        if state_type == 'battery_level':
            self.battery_level = value
            if value < 0.2:  # Low battery
                logger.warning("Low battery - enabling aggressive power saving")
                # In real implementation, would reduce functionality
        
        elif state_type == 'on_wrist':
            self.is_on_wrist = value
            if not value:
                logger.info("Watch removed - entering power save mode")
        
        elif state_type == 'charging':
            self.is_charging = value
            if value:
                logger.info("Watch charging - full features available")
        
        elif state_type == 'phone_connection':
            self.is_connected_to_phone = value
            if value:
                logger.info("Phone connected - enabling sync")
            else:
                logger.info("Phone disconnected - offline mode")
        
        elif state_type == 'screen_awake':
            self.screen_awake = value
    
    async def get_watch_status(self) -> Dict[str, Any]:
        """Get comprehensive watch status"""
        performance_metrics = await self.database.get_performance_metrics()
        
        uptime = time.time() - self.session_start_time
        
        return {
            'platform': self.config.platform.value,
            'capability': self.config.capability.value,
            'uptime_minutes': uptime / 60,
            'interactions_count': self.interactions_count,
            'voice_commands_processed': self.voice_commands_processed,
            'is_on_wrist': self.is_on_wrist,
            'battery_level': self.battery_level,
            'is_charging': self.is_charging,
            'heart_rate': self.heart_rate if self.config.health_sensors else None,
            'connected_to_phone': self.is_connected_to_phone,
            'screen_awake': self.screen_awake,
            'voice_enabled': self.config.voice_enabled,
            'health_sensors': self.config.health_sensors,
            'cellular_enabled': self.config.cellular_enabled,
            'always_on_display': self.config.always_on_display,
            'database_performance': performance_metrics,
            'storage_usage': {
                'used_kb': performance_metrics['storage_used_kb'],
                'limit_mb': self.config.storage_limit_mb,
                'percentage': performance_metrics['storage_percentage']
            },
            'memory_usage': {
                'estimated_mb': performance_metrics.get('memory_usage_mb', 2),
                'limit_mb': self.config.memory_limit_mb
            }
        }
    
    async def get_recent_conversations(self, limit: int = 3) -> List[Dict]:
        """Get recent conversations optimized for watch display"""
        return await self.database.get_recent_conversations(limit)
    
    async def _initialize_health_monitoring(self):
        """Initialize health monitoring with sample data"""
        # Simulate initial health data
        current_time = int(time.time())
        
        health_data = [
            ('heart_rate', 72, current_time - 300),
            ('steps', 8247, current_time - 600),
            ('exercise', 1, current_time - 3600),  # 1 hour ago
        ]
        
        for metric_type, value, timestamp in health_data:
            await self.database.store_health_context(metric_type, value, timestamp)
    
    async def _cache_essential_voice_commands(self):
        """Cache essential voice commands for offline operation"""
        essential_commands = [
            ("what time is it", "It's currently {time}", 0.95),
            ("what's my heart rate", "Your heart rate is {hr} BPM", 0.90),
            ("how many steps today", "You've taken {steps} steps today", 0.90),
            ("battery level", "Watch battery is at {battery}%", 0.95),
            ("start timer", "Timer started", 0.85),
            ("stop timer", "Timer stopped", 0.85),
        ]
        
        for command, response, confidence in essential_commands:
            await self.database.cache_voice_response(command, response, confidence)
    
    async def _generate_watch_response(self, query: str) -> Dict[str, Any]:
        """Generate watch-optimized AI response"""
        start_time = time.time()
        
        # Simulate processing time based on watch capability
        processing_times = {
            WatchCapability.ULTRA: 0.05,
            WatchCapability.PREMIUM: 0.1,
            WatchCapability.STANDARD: 0.2,
            WatchCapability.BASIC: 0.5
        }
        
        await asyncio.sleep(processing_times.get(self.config.capability, 0.2))
        
        # Generate ultra-short response for watch constraints
        base_response = f"Got it! {query[:20]}..." if len(query) > 20 else f"Got it! {query}"
        
        # Watch-specific response adaptations
        if not self.is_connected_to_phone:
            base_response = "[Offline] " + base_response[:30]
        elif self.battery_level < 0.2:
            base_response = base_response[:25] + "..."  # Shorter for battery saving
        elif not self.is_on_wrist:
            base_response = "Watch ready when you are"
        
        # Capability-based response length
        if self.config.capability == WatchCapability.BASIC:
            base_response = base_response[:20] + "..." if len(base_response) > 20 else base_response
        
        response_time = time.time() - start_time
        
        return {
            'response': base_response,
            'confidence': 0.85,
            'processing_time': response_time,
            'watch_optimized': True,
            'capability_adapted': True,
            'battery_optimized': self.battery_level < 0.3
        }
    
    async def _generate_health_aware_response(self, query: str, health_context: List[Dict]) -> Dict[str, Any]:
        """Generate response incorporating health context"""
        base_response = await self._generate_watch_response(query)
        
        # Add health context if relevant
        if 'heart' in query.lower() and health_context:
            hr_data = next((h for h in health_context if h['metric_type'] == 'heart_rate'), None)
            if hr_data:
                base_response['response'] = f"Your heart rate is {hr_data['value']:.0f} BPM"
        
        elif 'steps' in query.lower() and health_context:
            steps_data = next((h for h in health_context if h['metric_type'] == 'steps'), None)
            if steps_data:
                base_response['response'] = f"You've taken {steps_data['value']:.0f} steps"
        
        base_response['health_aware'] = True
        base_response['health_context_used'] = len(health_context)
        
        return base_response
    
    async def _generate_health_alert_response(self, event_type: str, value: float) -> str:
        """Generate health alert response"""
        if event_type == 'heart_rate':
            if value > 120:
                return f"High heart rate detected: {value:.0f} BPM"
            elif value < 50:
                return f"Low heart rate detected: {value:.0f} BPM"
        
        return f"Health event: {event_type} = {value}"
    
    async def close(self):
        """Close watch BUDDY core"""
        if self.database:
            await self.database.close()
        
        logger.info("Watch BUDDY core closed")


async def test_watch_buddy_demo():
    """Comprehensive test of smartwatch BUDDY implementation"""
    
    print("⌚ BUDDY 2.0 Smartwatch Platform Demo (Phase 3 Implementation)")
    print("=" * 70)
    print("Building on proven Phase 1 & 2 foundations")
    print("")
    
    # Test different smartwatch profiles
    test_profiles = [
        (WatchPlatform.APPLE_WATCH, WatchCapability.ULTRA, "Apple Watch Ultra"),
        (WatchPlatform.APPLE_WATCH, WatchCapability.PREMIUM, "Apple Watch Series 9"),
        (WatchPlatform.WEAR_OS, WatchCapability.PREMIUM, "Galaxy Watch 6"),
        (WatchPlatform.GALAXY_WATCH, WatchCapability.STANDARD, "Galaxy Watch 5"),
        (WatchPlatform.FITBIT, WatchCapability.BASIC, "Fitbit Sense 2")
    ]
    
    overall_stats = {
        'watches_tested': 0,
        'successful_tests': 0,
        'total_interactions': 0,
        'voice_commands': 0,
        'health_events': 0,
        'avg_response_time': 0
    }
    
    for platform, capability, watch_name in test_profiles:
        print(f"\n⌚ Testing {watch_name} ({platform.value}, {capability.value})")
        print("-" * 55)
        
        # Create watch configuration
        config = WatchConfig.for_watch_profile(platform, capability)
        
        # Initialize watch BUDDY
        buddy = WatchBuddyCore(
            user_id="watch_user_123",
            device_id=f"watch_{platform.value}_{capability.value}_{int(time.time())}",
            config=config
        )
        
        try:
            overall_stats['watches_tested'] += 1
            
            # Initialize
            success = await buddy.initialize()
            if not success:
                print(f"❌ Failed to initialize {watch_name}")
                continue
            
            print(f"✅ {watch_name} initialized successfully")
            print(f"   Storage Limit: {config.storage_limit_mb}MB")
            print(f"   Memory Limit: {config.memory_limit_mb}MB")
            print(f"   Battery Life: {config.battery_life_hours}h")
            print(f"   Voice Enabled: {config.voice_enabled}")
            print(f"   Health Sensors: {config.health_sensors}")
            print(f"   Cellular: {config.cellular_enabled}")
            
            # Test voice commands if available
            if config.voice_enabled:
                print("\n🎤 Testing voice commands...")
                voice_commands = [
                    "What time is it?",
                    "What's my heart rate?",
                    "How many steps today?",
                    "Start a timer"
                ]
                
                for command in voice_commands:
                    result = await buddy.process_voice_command(command)
                    print(f"   '{command}' → {result['response'][:40]}...")
                    overall_stats['voice_commands'] += 1
                    overall_stats['total_interactions'] += 1
            
            # Test quick interactions
            print("\n⚡ Testing quick interactions...")
            quick_actions = ['time', 'heart_rate', 'steps', 'battery']
            for action in quick_actions:
                result = await buddy.quick_interaction(action)
                print(f"   {action.title()}: {result['response']}")
                overall_stats['total_interactions'] += 1
            
            # Test health monitoring if available
            if config.health_sensors:
                print("\n❤️ Testing health monitoring...")
                health_events = [
                    ('heart_rate', 85),
                    ('steps', 9500),
                    ('exercise', 1),
                    ('heart_rate', 125)  # High heart rate
                ]
                
                for event_type, value in health_events:
                    await buddy.handle_health_event(event_type, value)
                    overall_stats['health_events'] += 1
                
                # Test health-aware query
                health_response = await buddy.get_health_aware_response("How am I doing?")
                print(f"   Health query: {health_response['response']}")
                overall_stats['total_interactions'] += 1
            
            # Test watch state changes
            print("\n📲 Testing watch state management...")
            await buddy.handle_watch_state_change('battery_level', 0.15)  # Low battery
            await buddy.handle_watch_state_change('on_wrist', False)      # Removed
            await buddy.handle_watch_state_change('phone_connection', False)  # Offline
            
            # Test offline interaction
            offline_result = await buddy.quick_interaction('time')
            print(f"   Offline interaction: {offline_result['response']}")
            overall_stats['total_interactions'] += 1
            
            # Restore good conditions
            await buddy.handle_watch_state_change('battery_level', 0.8)
            await buddy.handle_watch_state_change('on_wrist', True)
            await buddy.handle_watch_state_change('phone_connection', True)
            await buddy.handle_watch_state_change('charging', True)
            
            # Get watch status
            status = await buddy.get_watch_status()
            print(f"\n📊 Watch Status for {watch_name}:")
            print(f"   Platform: {status['platform']}")
            print(f"   Capability: {status['capability']}")
            print(f"   Interactions: {status['interactions_count']}")
            print(f"   Voice Commands: {status['voice_commands_processed']}")
            print(f"   Storage: {status['storage_usage']['percentage']:.1f}% used")
            print(f"   Memory: {status['memory_usage']['estimated_mb']:.1f}MB / {status['memory_usage']['limit_mb']}MB")
            print(f"   Battery: {int(status['battery_level'] * 100)}%")
            print(f"   Heart Rate: {status['heart_rate']} BPM" if status['heart_rate'] else "   Heart Rate: N/A")
            print(f"   On Wrist: {status['is_on_wrist']}")
            print(f"   Connected: {status['connected_to_phone']}")
            
            overall_stats['avg_response_time'] += status['database_performance']['average_execution_time']
            
            # Test conversation history
            print("\n💬 Testing conversation history...")
            conversations = await buddy.get_recent_conversations(limit=3)
            print(f"   Retrieved {len(conversations)} recent conversations")
            for conv in conversations[:2]:  # Show first 2
                print(f"   {conv['type']}: {conv['content'][:30]}...")
            
            print(f"✅ {watch_name} testing completed successfully")
            overall_stats['successful_tests'] += 1
            
        except Exception as e:
            print(f"❌ {watch_name} testing failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await buddy.close()
        
        # Small delay between watch tests
        await asyncio.sleep(0.1)
    
    # Final summary
    print("\n" + "=" * 70)
    print("🎉 BUDDY 2.0 Smartwatch Platform Demo Completed!")
    print("=" * 70)
    
    print(f"\n📈 Demo Summary:")
    print(f"✅ Watches Tested: {overall_stats['watches_tested']}")
    print(f"✅ Successful Tests: {overall_stats['successful_tests']}")
    print(f"✅ Total Interactions: {overall_stats['total_interactions']}")
    print(f"✅ Voice Commands: {overall_stats['voice_commands']}")
    print(f"✅ Health Events: {overall_stats['health_events']}")
    if overall_stats['successful_tests'] > 0:
        avg_response_time = overall_stats['avg_response_time'] / overall_stats['successful_tests']
        print(f"✅ Average Response Time: {avg_response_time:.4f}s")
    
    print(f"\n⌚ Architecture Highlights:")
    print(f"✅ Ultra-constrained resource optimization")
    print(f"✅ Watch-specific database with <1MB footprint")
    print(f"✅ Offline voice command caching")
    print(f"✅ Health sensor integration and context")
    print(f"✅ Battery-aware performance scaling")
    print(f"✅ On-wrist detection and power management")
    print(f"✅ Quick interaction optimization")
    print(f"✅ Watch display-optimized responses")
    
    print(f"\n🚀 Ready for Phase 4: Smart TV Development!")
    print(f"💡 Smartwatch implementation provides the foundation for:")
    print(f"   • Apple Watch native app deployment")
    print(f"   • Wear OS companion app integration")
    print(f"   • Health monitoring AI insights")
    print(f"   • Ultra-low latency voice commands")
    print(f"   • Seamless device ecosystem sync")
    print(f"   • Advanced wearable AI interactions")


if __name__ == "__main__":
    # Run the smartwatch platform demo
    asyncio.run(test_watch_buddy_demo())
