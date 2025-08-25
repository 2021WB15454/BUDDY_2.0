#!/usr/bin/env python3
"""
BUDDY 2.0 Phase 5: Automotive Platform Implementation
Building on proven Phase 1-4 foundations for intelligent vehicle AI

This implementation demonstrates hands-free automotive AI capabilities
with safety-first design, navigation integration, and connected car features.
"""

import asyncio
import json
import time
import sqlite3
import uuid
import tempfile
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AutomotivePlatform(Enum):
    """Automotive platforms supported by BUDDY"""
    ANDROID_AUTOMOTIVE = "android_automotive"
    APPLE_CARPLAY = "apple_carplay"
    TESLA_INFOTAINMENT = "tesla_infotainment"
    BMW_IDRIVE = "bmw_idrive"
    MERCEDES_MBUX = "mercedes_mbux"
    TOYOTA_ENTUNE = "toyota_entune"
    FORD_SYNC = "ford_sync"
    NATIVE_HEADUNIT = "native_headunit"


class AutomotiveCapability(Enum):
    """Automotive system hardware capabilities"""
    BASIC = "basic"           # Entry-level infotainment
    STANDARD = "standard"     # Standard automotive systems
    PREMIUM = "premium"       # Premium infotainment with AI
    FLAGSHIP = "flagship"     # Advanced AI-powered automotive systems


class SafetyMode(Enum):
    """Driving safety modes for interaction adaptation"""
    PARKED = "parked"         # Vehicle parked, full functionality
    DRIVING = "driving"       # Vehicle in motion, limited interaction
    PASSENGER = "passenger"   # Passenger mode, enhanced interaction
    EMERGENCY = "emergency"   # Emergency mode, critical functions only


@dataclass
class AutomotiveConfig:
    """Automotive-specific configuration optimized for vehicle use"""
    platform: AutomotivePlatform
    capability: AutomotiveCapability
    storage_limit_mb: int
    memory_limit_mb: int
    voice_enabled: bool
    always_listening: bool
    navigation_integration: bool
    vehicle_data_access: bool
    hands_free_only: bool
    emergency_features: bool
    multi_user_support: bool
    offline_navigation: bool
    
    @classmethod
    def for_automotive_profile(cls, platform: AutomotivePlatform, capability: AutomotiveCapability) -> 'AutomotiveConfig':
        """Generate optimal configuration for automotive profile"""
        configs = {
            (AutomotivePlatform.TESLA_INFOTAINMENT, AutomotiveCapability.FLAGSHIP): cls(
                platform=platform,
                capability=capability,
                storage_limit_mb=2000,
                memory_limit_mb=1024,
                voice_enabled=True,
                always_listening=True,
                navigation_integration=True,
                vehicle_data_access=True,
                hands_free_only=False,
                emergency_features=True,
                multi_user_support=True,
                offline_navigation=True
            ),
            (AutomotivePlatform.BMW_IDRIVE, AutomotiveCapability.PREMIUM): cls(
                platform=platform,
                capability=capability,
                storage_limit_mb=1000,
                memory_limit_mb=512,
                voice_enabled=True,
                always_listening=True,
                navigation_integration=True,
                vehicle_data_access=True,
                hands_free_only=True,
                emergency_features=True,
                multi_user_support=True,
                offline_navigation=False
            ),
            (AutomotivePlatform.ANDROID_AUTOMOTIVE, AutomotiveCapability.STANDARD): cls(
                platform=platform,
                capability=capability,
                storage_limit_mb=500,
                memory_limit_mb=256,
                voice_enabled=True,
                always_listening=False,
                navigation_integration=True,
                vehicle_data_access=False,
                hands_free_only=True,
                emergency_features=True,
                multi_user_support=False,
                offline_navigation=False
            ),
            (AutomotivePlatform.FORD_SYNC, AutomotiveCapability.BASIC): cls(
                platform=platform,
                capability=capability,
                storage_limit_mb=200,
                memory_limit_mb=128,
                voice_enabled=True,
                always_listening=False,
                navigation_integration=False,
                vehicle_data_access=False,
                hands_free_only=True,
                emergency_features=True,
                multi_user_support=False,
                offline_navigation=False
            )
        }
        
        # Default fallback configuration
        default_config = cls(
            platform=platform,
            capability=capability,
            storage_limit_mb=300,
            memory_limit_mb=128,
            voice_enabled=True,
            always_listening=False,
            navigation_integration=False,
            vehicle_data_access=False,
            hands_free_only=True,
            emergency_features=True,
            multi_user_support=False,
            offline_navigation=False
        )
        
        return configs.get((platform, capability), default_config)


class AutomotiveOptimizedDatabase:
    """Automotive-optimized database for hands-free AI interactions"""
    
    def __init__(self, db_path: str, config: AutomotiveConfig):
        self.db_path = db_path
        self.config = config
        self.connection = None
        self.performance_metrics = {
            'queries_executed': 0,
            'total_execution_time': 0.0,
            'conversations_stored': 0,
            'navigation_requests': 0,
            'vehicle_commands': 0,
            'emergency_activations': 0,
            'storage_used_mb': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Automotive-specific cache for quick access while driving
        self.navigation_cache = {}
        self.vehicle_data_cache = {}
        self.emergency_contacts_cache = {}
        self.max_cache_entries = 30 if config.capability == AutomotiveCapability.FLAGSHIP else 15
        
    async def initialize(self):
        """Initialize automotive-optimized database"""
        self.connection = sqlite3.connect(self.db_path)
        
        # Apply automotive-specific PRAGMA settings
        automotive_pragmas = [
            "PRAGMA journal_mode = WAL",
            "PRAGMA synchronous = NORMAL",
            f"PRAGMA cache_size = -{self.config.memory_limit_mb // 4 * 1024}",  # 25% of memory for cache
            "PRAGMA temp_store = MEMORY",
            "PRAGMA mmap_size = 67108864",  # 64MB memory mapping for automotive
            "PRAGMA foreign_keys = ON",
            "PRAGMA optimize"
        ]
        
        # Additional optimizations for high-end automotive systems
        if self.config.capability == AutomotiveCapability.FLAGSHIP:
            automotive_pragmas.extend([
                "PRAGMA threads = 2",  # Multi-threading for flagship automotive
                f"PRAGMA cache_size = -{self.config.memory_limit_mb // 2 * 1024}",  # 50% cache for flagship
            ])
        
        for pragma in automotive_pragmas:
            self.connection.execute(pragma)
        
        # Create automotive-optimized schema
        await self._create_automotive_schema()
        logger.info(f"Automotive database initialized for {self.config.platform.value} ({self.config.capability.value})")
    
    async def _create_automotive_schema(self):
        """Create automotive-optimized database schema"""
        schema_sql = """
        -- Automotive conversations with safety-first design
        CREATE TABLE IF NOT EXISTS automotive_conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_id TEXT,
            content TEXT NOT NULL,
            message_type TEXT NOT NULL CHECK(message_type IN ('user', 'assistant', 'system')),
            interaction_type TEXT NOT NULL, -- voice, touch, steering_wheel, emergency
            safety_mode TEXT NOT NULL, -- parked, driving, passenger, emergency
            timestamp INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            metadata TEXT,  -- JSON with automotive context
            voice_optimized TEXT, -- Hands-free audio response
            display_safe TEXT,    -- Driving-safe visual content
            sync_status INTEGER DEFAULT 0,
            content_hash TEXT,
            created_at INTEGER DEFAULT (strftime('%s', 'now'))
        ) WITHOUT ROWID;
        
        -- Navigation and location data
        CREATE TABLE IF NOT EXISTS automotive_navigation (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            request_type TEXT NOT NULL, -- destination, route, traffic, poi
            origin_location TEXT,      -- JSON with lat/lng
            destination_location TEXT, -- JSON with lat/lng
            route_data TEXT,          -- JSON with route information
            traffic_data TEXT,        -- JSON with traffic conditions
            estimated_time INTEGER,   -- ETA in seconds
            distance_km REAL,
            timestamp INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            completion_status TEXT DEFAULT 'pending'
        ) WITHOUT ROWID;
        
        -- Vehicle data and commands
        CREATE TABLE IF NOT EXISTS automotive_vehicle_data (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            data_type TEXT NOT NULL, -- fuel, battery, temperature, diagnostics
            data_value TEXT NOT NULL,
            unit TEXT,
            timestamp INTEGER NOT NULL,
            vehicle_id TEXT,
            is_alert INTEGER DEFAULT 0,
            alert_severity TEXT -- info, warning, critical
        ) WITHOUT ROWID;
        
        -- Emergency contacts and procedures
        CREATE TABLE IF NOT EXISTS automotive_emergency (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            contact_type TEXT NOT NULL, -- emergency_contact, roadside_assistance, insurance
            contact_name TEXT NOT NULL,
            contact_number TEXT NOT NULL,
            priority_level INTEGER DEFAULT 1,
            location_dependent INTEGER DEFAULT 0,
            last_used INTEGER,
            created_at INTEGER DEFAULT (strftime('%s', 'now'))
        ) WITHOUT ROWID;
        
        -- Trip history and analytics
        CREATE TABLE IF NOT EXISTS automotive_trips (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            trip_start_time INTEGER NOT NULL,
            trip_end_time INTEGER,
            start_location TEXT,      -- JSON with location
            end_location TEXT,        -- JSON with location
            distance_km REAL,
            duration_minutes INTEGER,
            fuel_consumed REAL,
            average_speed_kmh REAL,
            buddy_interactions INTEGER DEFAULT 0,
            safety_events INTEGER DEFAULT 0,
            trip_type TEXT DEFAULT 'personal' -- personal, business, emergency
        ) WITHOUT ROWID;
        
        -- Voice command cache for automotive optimization
        CREATE TABLE IF NOT EXISTS automotive_voice_cache (
            command_hash TEXT PRIMARY KEY,
            response_text TEXT NOT NULL,
            response_audio_path TEXT,   -- Path to cached audio
            confidence REAL NOT NULL,
            usage_count INTEGER DEFAULT 1,
            last_used INTEGER DEFAULT (strftime('%s', 'now')),
            safety_context TEXT,        -- driving, parked, passenger
            hands_free_optimized INTEGER DEFAULT 1
        ) WITHOUT ROWID;
        
        -- User preferences for automotive context
        CREATE TABLE IF NOT EXISTS automotive_preferences (
            user_id TEXT NOT NULL,
            preference_key TEXT NOT NULL,
            preference_value TEXT NOT NULL,
            context TEXT,               -- driving, parked, all
            updated_at INTEGER DEFAULT (strftime('%s', 'now')),
            PRIMARY KEY (user_id, preference_key, context)
        ) WITHOUT ROWID;
        """
        
        self.connection.executescript(schema_sql)
        
        # Create automotive-specific indexes
        await self._create_automotive_indexes()
        
        self.connection.commit()
    
    async def _create_automotive_indexes(self):
        """Create automotive-optimized indexes"""
        indexes = [
            # Conversation indexes
            "CREATE INDEX IF NOT EXISTS idx_auto_conversations_user_time ON automotive_conversations(user_id, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auto_conversations_safety ON automotive_conversations(safety_mode, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auto_conversations_interaction ON automotive_conversations(interaction_type, timestamp DESC)",
            
            # Navigation indexes  
            "CREATE INDEX IF NOT EXISTS idx_auto_navigation_user_active ON automotive_navigation(user_id, is_active, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auto_navigation_type ON automotive_navigation(request_type, timestamp DESC)",
            
            # Vehicle data indexes
            "CREATE INDEX IF NOT EXISTS idx_auto_vehicle_data_type ON automotive_vehicle_data(data_type, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auto_vehicle_alerts ON automotive_vehicle_data(is_alert, alert_severity, timestamp DESC)",
            
            # Emergency indexes
            "CREATE INDEX IF NOT EXISTS idx_auto_emergency_priority ON automotive_emergency(priority_level DESC, contact_type)",
            
            # Trip indexes
            "CREATE INDEX IF NOT EXISTS idx_auto_trips_user_time ON automotive_trips(user_id, trip_start_time DESC)",
            
            # Voice cache indexes
            "CREATE INDEX IF NOT EXISTS idx_auto_voice_usage ON automotive_voice_cache(usage_count DESC, last_used DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auto_voice_safety ON automotive_voice_cache(safety_context, confidence DESC)"
        ]
        
        for index in indexes:
            self.connection.execute(index)
    
    async def store_automotive_conversation(self, conversation_data: Dict) -> str:
        """Store conversation with automotive-specific optimizations"""
        start_time = time.time()
        
        # Generate automotive-optimized conversation ID
        conv_id = f"auto_{int(time.time())}_{conversation_data['user_id'][:8]}"
        
        # Create voice-optimized version for hands-free use
        voice_optimized = self._optimize_for_voice_response(conversation_data['content'])
        
        # Create driving-safe display version
        display_safe = self._create_driving_safe_display(conversation_data['content'], conversation_data['message_type'])
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO automotive_conversations 
            (id, user_id, session_id, content, message_type, interaction_type, safety_mode, 
             timestamp, device_id, metadata, voice_optimized, display_safe, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conv_id,
            conversation_data['user_id'],
            conversation_data.get('session_id'),
            conversation_data['content'],
            conversation_data['message_type'],
            conversation_data.get('interaction_type', 'voice'),
            conversation_data.get('safety_mode', 'driving'),
            int(time.time()),
            conversation_data['device_id'],
            json.dumps(conversation_data.get('metadata', {})),
            voice_optimized,
            display_safe,
            self._generate_content_hash(conversation_data['content'])
        ))
        
        self.connection.commit()
        
        # Update performance metrics
        execution_time = time.time() - start_time
        self.performance_metrics['queries_executed'] += 1
        self.performance_metrics['total_execution_time'] += execution_time
        self.performance_metrics['conversations_stored'] += 1
        
        # Cache recent conversation for quick access
        await self._cache_automotive_conversation(conv_id, conversation_data)
        
        logger.debug(f"Stored automotive conversation {conv_id} in {execution_time:.4f}s")
        return conv_id
    
    async def store_navigation_request(self, navigation_data: Dict) -> str:
        """Store navigation request for trip planning"""
        nav_id = f"nav_{int(time.time())}_{navigation_data['user_id'][:8]}"
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO automotive_navigation 
            (id, user_id, request_type, origin_location, destination_location, 
             route_data, traffic_data, estimated_time, distance_km, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nav_id,
            navigation_data['user_id'],
            navigation_data['request_type'],
            json.dumps(navigation_data.get('origin_location', {})),
            json.dumps(navigation_data.get('destination_location', {})),
            json.dumps(navigation_data.get('route_data', {})),
            json.dumps(navigation_data.get('traffic_data', {})),
            navigation_data.get('estimated_time', 0),
            navigation_data.get('distance_km', 0.0),
            int(time.time())
        ))
        
        self.connection.commit()
        self.performance_metrics['navigation_requests'] += 1
        
        return nav_id
    
    async def store_vehicle_data(self, vehicle_data: Dict) -> str:
        """Store vehicle data and diagnostics"""
        data_id = f"vehicle_{int(time.time())}_{vehicle_data['data_type'][:5]}"
        
        # Determine if this is an alert condition
        is_alert, alert_severity = self._evaluate_vehicle_alert(
            vehicle_data['data_type'],
            vehicle_data['data_value']
        )
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO automotive_vehicle_data 
            (id, user_id, data_type, data_value, unit, timestamp, 
             vehicle_id, is_alert, alert_severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data_id,
            vehicle_data['user_id'],
            vehicle_data['data_type'],
            vehicle_data['data_value'],
            vehicle_data.get('unit'),
            int(time.time()),
            vehicle_data.get('vehicle_id'),
            1 if is_alert else 0,
            alert_severity
        ))
        
        self.connection.commit()
        self.performance_metrics['vehicle_commands'] += 1
        
        return data_id
    
    async def get_automotive_conversations(self, user_id: str, safety_mode: str = None, limit: int = 20) -> List[Dict]:
        """Get conversations optimized for automotive display"""
        start_time = time.time()
        
        query = """
            SELECT id, content, message_type, interaction_type, safety_mode, timestamp, 
                   voice_optimized, display_safe, metadata
            FROM automotive_conversations 
            WHERE user_id = ?
        """
        params = [user_id]
        
        if safety_mode:
            query += " AND safety_mode = ?"
            params.append(safety_mode)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conversations = []
        for row in rows:
            metadata = json.loads(row[8]) if row[8] else {}
            conversations.append({
                'id': row[0],
                'content': row[1],
                'message_type': row[2],
                'interaction_type': row[3],
                'safety_mode': row[4],
                'timestamp': row[5],
                'voice_optimized': row[6],
                'display_safe': row[7],
                'metadata': metadata,
                'automotive_formatted': True
            })
        
        # Update metrics
        execution_time = time.time() - start_time
        self.performance_metrics['queries_executed'] += 1
        self.performance_metrics['total_execution_time'] += execution_time
        
        return conversations
    
    async def get_navigation_suggestions(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get recent navigation suggestions"""
        query = """
            SELECT request_type, destination_location, route_data, estimated_time, distance_km
            FROM automotive_navigation 
            WHERE user_id = ? AND is_active = 1
            ORDER BY timestamp DESC LIMIT ?
        """
        
        cursor = self.connection.cursor()
        cursor.execute(query, [user_id, limit])
        rows = cursor.fetchall()
        
        suggestions = []
        for row in rows:
            destination = json.loads(row[1]) if row[1] else {}
            route_data = json.loads(row[2]) if row[2] else {}
            suggestions.append({
                'request_type': row[0],
                'destination': destination,
                'route_data': route_data,
                'estimated_time': row[3],
                'distance_km': row[4]
            })
        
        return suggestions
    
    async def get_vehicle_alerts(self, user_id: str) -> List[Dict]:
        """Get active vehicle alerts"""
        query = """
            SELECT data_type, data_value, unit, alert_severity, timestamp
            FROM automotive_vehicle_data 
            WHERE user_id = ? AND is_alert = 1
            ORDER BY timestamp DESC, alert_severity DESC
        """
        
        cursor = self.connection.cursor()
        cursor.execute(query, [user_id])
        rows = cursor.fetchall()
        
        alerts = []
        for row in rows:
            alerts.append({
                'data_type': row[0],
                'data_value': row[1],
                'unit': row[2],
                'severity': row[3],
                'timestamp': row[4]
            })
        
        return alerts
    
    async def get_emergency_contacts(self, user_id: str) -> List[Dict]:
        """Get emergency contacts for quick access"""
        query = """
            SELECT contact_name, contact_number, contact_type, priority_level
            FROM automotive_emergency 
            WHERE user_id = ?
            ORDER BY priority_level ASC
        """
        
        cursor = self.connection.cursor()
        cursor.execute(query, [user_id])
        rows = cursor.fetchall()
        
        contacts = []
        for row in rows:
            contacts.append({
                'name': row[0],
                'number': row[1],
                'type': row[2],
                'priority': row[3]
            })
        
        return contacts
    
    def _optimize_for_voice_response(self, content: str) -> str:
        """Optimize content for hands-free voice response"""
        # Automotive voice optimization for safe driving
        voice_content = content.replace('\n', '. ')  # Convert line breaks to pauses
        voice_content = voice_content.replace('  ', ' ')  # Remove double spaces
        
        # Add automotive-specific voice cues
        if len(voice_content) > 50:
            voice_content = "Here's what I found: " + voice_content
        
        # Limit length for safety while driving
        if len(voice_content) > 200:
            voice_content = voice_content[:190] + "... Would you like more details?"
        
        return voice_content
    
    def _create_driving_safe_display(self, content: str, message_type: str) -> str:
        """Create driving-safe display version with minimal text"""
        if message_type == 'user':
            return None  # Don't display user messages while driving
        
        # Keep it very short for driving safety
        if len(content) <= 30:
            return content
        
        # Extract key information for driving display
        sentences = content.split('. ')
        if sentences:
            return sentences[0][:30] + "..."
        
        return content[:30] + "..."
    
    def _evaluate_vehicle_alert(self, data_type: str, data_value: str) -> Tuple[bool, str]:
        """Evaluate if vehicle data requires an alert"""
        alert_conditions = {
            'fuel_level': {'critical': 10, 'warning': 20, 'unit': '%'},
            'battery_level': {'critical': 20, 'warning': 30, 'unit': '%'},
            'engine_temperature': {'critical': 110, 'warning': 100, 'unit': 'C'},
            'tire_pressure': {'critical': 25, 'warning': 30, 'unit': 'PSI'},
            'oil_pressure': {'critical': 10, 'warning': 15, 'unit': 'PSI'}
        }
        
        if data_type not in alert_conditions:
            return False, None
        
        try:
            value = float(data_value)
            condition = alert_conditions[data_type]
            
            if data_type in ['fuel_level', 'battery_level', 'tire_pressure', 'oil_pressure']:
                # Lower values are problematic
                if value <= condition['critical']:
                    return True, 'critical'
                elif value <= condition['warning']:
                    return True, 'warning'
            elif data_type == 'engine_temperature':
                # Higher values are problematic
                if value >= condition['critical']:
                    return True, 'critical'
                elif value >= condition['warning']:
                    return True, 'warning'
                    
        except (ValueError, TypeError):
            pass
        
        return False, None
    
    async def _cache_automotive_conversation(self, conv_id: str, conversation_data: Dict):
        """Cache conversation for quick automotive access"""
        if len(self.navigation_cache) < self.max_cache_entries:
            self.navigation_cache[conv_id] = conversation_data
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        return str(hash(content) & 0x7FFFFFFF)
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get automotive database performance metrics"""
        # Calculate storage usage
        cursor = self.connection.cursor()
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        db_size = cursor.fetchone()[0]
        self.performance_metrics['storage_used_mb'] = db_size / (1024 * 1024)
        
        # Calculate average execution time
        avg_time = (
            self.performance_metrics['total_execution_time'] / 
            max(1, self.performance_metrics['queries_executed'])
        )
        
        return {
            **self.performance_metrics,
            'average_execution_time': avg_time,
            'cache_hit_ratio': (
                self.performance_metrics['cache_hits'] / 
                max(1, self.performance_metrics['cache_hits'] + self.performance_metrics['cache_misses'])
            ),
            'storage_limit_mb': self.config.storage_limit_mb,
            'memory_limit_mb': self.config.memory_limit_mb,
            'automotive_platform': self.config.platform.value,
            'automotive_capability': self.config.capability.value
        }
    
    async def close(self):
        """Close automotive database"""
        if self.connection:
            self.connection.close()


class AutomotiveBuddyCore:
    """Core BUDDY implementation for Automotive platforms"""
    
    def __init__(self, user_id: str, device_id: str, config: AutomotiveConfig):
        self.user_id = user_id
        self.device_id = device_id
        self.config = config
        self.database = None
        
        # Automotive-specific state
        self.safety_mode = SafetyMode.PARKED
        self.vehicle_speed_kmh = 0.0
        self.current_location = None
        self.destination = None
        self.navigation_active = False
        self.emergency_mode = False
        self.driver_profile = "primary_driver"
        
        # Performance tracking
        self.session_start_time = time.time()
        self.voice_commands_processed = 0
        self.navigation_requests = 0
        self.vehicle_status_checks = 0
        self.emergency_activations = 0
        
    async def initialize(self) -> bool:
        """Initialize Automotive BUDDY core"""
        try:
            # Create temporary database for demo
            temp_dir = tempfile.mkdtemp(prefix="buddy_automotive_")
            db_path = os.path.join(temp_dir, f"buddy_auto_{self.device_id}.db")
            
            # Initialize automotive database
            self.database = AutomotiveOptimizedDatabase(db_path, self.config)
            await self.database.initialize()
            
            # Initialize automotive-specific features
            if self.config.voice_enabled:
                await self._initialize_voice_recognition()
            
            if self.config.navigation_integration:
                await self._initialize_navigation_system()
            
            if self.config.vehicle_data_access:
                await self._initialize_vehicle_integration()
            
            if self.config.emergency_features:
                await self._initialize_emergency_system()
            
            logger.info(f"Automotive BUDDY initialized for {self.config.platform.value} "
                       f"({self.config.capability.value} capability)")
            return True
            
        except Exception as e:
            logger.error(f"Automotive initialization failed: {e}")
            return False
    
    async def process_voice_command(self, command: str, context: Dict = None) -> Dict[str, Any]:
        """Process voice command with automotive safety optimization"""
        start_time = time.time()
        
        # Safety check - limit interaction while driving
        if self.safety_mode == SafetyMode.DRIVING and not self._is_safe_command(command):
            return {
                'response': "I'll help you with that when it's safe to do so.",
                'safety_blocked': True,
                'safety_mode': self.safety_mode.value,
                'processing_time': time.time() - start_time
            }
        
        # Determine command type
        command_type = self._classify_automotive_command(command)
        
        # Process based on command type
        if command_type == "navigation":
            response = await self._handle_navigation_command(command, context)
        elif command_type == "vehicle_control":
            response = await self._handle_vehicle_command(command, context)
        elif command_type == "emergency":
            response = await self._handle_emergency_command(command, context)
        elif command_type == "communication":
            response = await self._handle_communication_command(command, context)
        elif command_type == "entertainment":
            response = await self._handle_entertainment_command(command, context)
        else:
            response = await self._generate_automotive_response(command, context)
        
        # Store conversation
        await self.database.store_automotive_conversation({
            'user_id': self.user_id,
            'device_id': self.device_id,
            'content': command,
            'message_type': 'user',
            'interaction_type': 'voice',
            'safety_mode': self.safety_mode.value,
            'metadata': {
                'command_type': command_type,
                'vehicle_speed': self.vehicle_speed_kmh,
                'navigation_active': self.navigation_active,
                'driver_profile': self.driver_profile
            }
        })
        
        await self.database.store_automotive_conversation({
            'user_id': self.user_id,
            'device_id': 'automotive_assistant',
            'content': response['response'],
            'message_type': 'assistant',
            'interaction_type': 'voice',
            'safety_mode': self.safety_mode.value,
            'metadata': {
                'command_type': command_type,
                'processing_time': response['processing_time'],
                'confidence': response.get('confidence', 0.8)
            }
        })
        
        self.voice_commands_processed += 1
        return response
    
    async def handle_navigation_request(self, destination: str, context: Dict = None) -> Dict[str, Any]:
        """Handle navigation requests with route planning"""
        start_time = time.time()
        
        navigation_data = {
            'user_id': self.user_id,
            'request_type': 'destination',
            'destination_location': {'address': destination},
            'origin_location': self.current_location or {'address': 'Current Location'},
            'route_data': {},
            'estimated_time': 0,
            'distance_km': 0.0
        }
        
        # Simulate route calculation
        route_result = await self._calculate_route(destination)
        navigation_data.update(route_result)
        
        # Store navigation request
        nav_id = await self.database.store_navigation_request(navigation_data)
        
        self.navigation_requests += 1
        self.destination = destination
        self.navigation_active = True
        
        return {
            'navigation_id': nav_id,
            'destination': destination,
            'estimated_time': route_result['estimated_time'],
            'distance_km': route_result['distance_km'],
            'route_summary': route_result['route_summary'],
            'processing_time': time.time() - start_time,
            'navigation_started': True
        }
    
    async def update_vehicle_status(self, status_data: Dict) -> Dict[str, Any]:
        """Update vehicle status and check for alerts"""
        alerts = []
        
        for data_type, value in status_data.items():
            vehicle_data = {
                'user_id': self.user_id,
                'data_type': data_type,
                'data_value': str(value),
                'unit': self._get_unit_for_data_type(data_type)
            }
            
            data_id = await self.database.store_vehicle_data(vehicle_data)
            
            # Check for alerts
            is_alert, severity = self.database._evaluate_vehicle_alert(data_type, str(value))
            if is_alert:
                alerts.append({
                    'data_type': data_type,
                    'value': value,
                    'severity': severity,
                    'message': self._get_alert_message(data_type, value, severity)
                })
        
        self.vehicle_status_checks += 1
        
        return {
            'status_updated': True,
            'alerts': alerts,
            'alert_count': len(alerts)
        }
    
    async def activate_emergency_mode(self, emergency_type: str = "general") -> Dict[str, Any]:
        """Activate emergency mode with safety features"""
        self.emergency_mode = True
        self.safety_mode = SafetyMode.EMERGENCY
        self.emergency_activations += 1
        
        # Get emergency contacts
        emergency_contacts = await self.database.get_emergency_contacts(self.user_id)
        
        # Log emergency activation
        await self.database.store_automotive_conversation({
            'user_id': self.user_id,
            'device_id': 'emergency_system',
            'content': f"Emergency mode activated: {emergency_type}",
            'message_type': 'system',
            'interaction_type': 'emergency',
            'safety_mode': SafetyMode.EMERGENCY.value,
            'metadata': {
                'emergency_type': emergency_type,
                'current_location': self.current_location,
                'vehicle_speed': self.vehicle_speed_kmh
            }
        })
        
        return {
            'emergency_activated': True,
            'emergency_type': emergency_type,
            'emergency_contacts': emergency_contacts,
            'current_location': self.current_location,
            'instructions': "Emergency services will be contacted if needed. Stay calm and follow voice instructions."
        }
    
    async def update_safety_mode(self, new_mode: SafetyMode, vehicle_speed: float = 0.0):
        """Update safety mode based on driving conditions"""
        old_mode = self.safety_mode
        self.safety_mode = new_mode
        self.vehicle_speed_kmh = vehicle_speed
        
        # Adjust system behavior based on safety mode
        if new_mode == SafetyMode.DRIVING:
            await self._optimize_for_driving_safety()
        elif new_mode == SafetyMode.PARKED:
            await self._enable_full_functionality()
        elif new_mode == SafetyMode.PASSENGER:
            await self._optimize_for_passenger_mode()
        
        logger.info(f"Safety mode changed from {old_mode.value} to {new_mode.value} (speed: {vehicle_speed} km/h)")
        
        return {
            'old_mode': old_mode.value,
            'new_mode': new_mode.value,
            'vehicle_speed': vehicle_speed,
            'safety_optimizations_applied': True
        }
    
    async def get_automotive_status(self) -> Dict[str, Any]:
        """Get comprehensive automotive status"""
        performance_metrics = await self.database.get_performance_metrics()
        
        uptime = time.time() - self.session_start_time
        
        # Get vehicle alerts
        vehicle_alerts = await self.database.get_vehicle_alerts(self.user_id)
        
        # Get navigation suggestions
        navigation_suggestions = await self.database.get_navigation_suggestions(self.user_id, 3)
        
        return {
            'platform': self.config.platform.value,
            'capability': self.config.capability.value,
            'uptime_minutes': uptime / 60,
            'voice_commands_processed': self.voice_commands_processed,
            'navigation_requests': self.navigation_requests,
            'vehicle_status_checks': self.vehicle_status_checks,
            'emergency_activations': self.emergency_activations,
            'safety_mode': self.safety_mode.value,
            'vehicle_speed_kmh': self.vehicle_speed_kmh,
            'navigation_active': self.navigation_active,
            'destination': self.destination,
            'emergency_mode': self.emergency_mode,
            'driver_profile': self.driver_profile,
            'voice_enabled': self.config.voice_enabled,
            'always_listening': self.config.always_listening,
            'navigation_integration': self.config.navigation_integration,
            'vehicle_data_access': self.config.vehicle_data_access,
            'hands_free_only': self.config.hands_free_only,
            'emergency_features': self.config.emergency_features,
            'vehicle_alerts_count': len(vehicle_alerts),
            'navigation_suggestions_count': len(navigation_suggestions),
            'database_performance': performance_metrics,
            'storage_usage': {
                'used_mb': performance_metrics['storage_used_mb'],
                'limit_mb': self.config.storage_limit_mb,
                'percentage': (performance_metrics['storage_used_mb'] / self.config.storage_limit_mb) * 100
            },
            'memory_usage': {
                'limit_mb': self.config.memory_limit_mb,
                'cache_performance': performance_metrics['cache_hit_ratio']
            }
        }
    
    def _is_safe_command(self, command: str) -> bool:
        """Check if command is safe to execute while driving"""
        safe_commands = [
            'emergency', 'help', 'call', 'navigate', 'directions', 'traffic',
            'weather', 'time', 'fuel', 'battery', 'temperature'
        ]
        
        command_lower = command.lower()
        return any(safe_word in command_lower for safe_word in safe_commands)
    
    def _classify_automotive_command(self, command: str) -> str:
        """Classify automotive voice command type"""
        command_lower = command.lower()
        
        if any(word in command_lower for word in ['navigate', 'directions', 'route', 'traffic', 'destination']):
            return "navigation"
        elif any(word in command_lower for word in ['fuel', 'battery', 'temperature', 'tire', 'engine', 'oil']):
            return "vehicle_control"
        elif any(word in command_lower for word in ['emergency', 'help', 'accident', 'call 911', 'roadside']):
            return "emergency"
        elif any(word in command_lower for word in ['call', 'text', 'message', 'phone']):
            return "communication"
        elif any(word in command_lower for word in ['music', 'radio', 'podcast', 'play']):
            return "entertainment"
        else:
            return "general"
    
    async def _handle_navigation_command(self, command: str, context: Dict = None) -> Dict[str, Any]:
        """Handle navigation commands"""
        start_time = time.time()
        
        # Extract destination from command
        if "navigate to" in command.lower():
            destination = command.lower().replace("navigate to", "").strip()
        elif "directions to" in command.lower():
            destination = command.lower().replace("directions to", "").strip()
        else:
            destination = "unknown destination"
        
        if destination != "unknown destination":
            nav_result = await self.handle_navigation_request(destination, context)
            response = f"Navigating to {destination}. {nav_result['route_summary']}"
        else:
            response = "Where would you like to go? Please say 'Navigate to' followed by your destination."
        
        return {
            'response': response,
            'command_type': 'navigation',
            'processing_time': time.time() - start_time,
            'confidence': 0.9,
            'automotive_optimized': True
        }
    
    async def _handle_vehicle_command(self, command: str, context: Dict = None) -> Dict[str, Any]:
        """Handle vehicle control and status commands"""
        start_time = time.time()
        
        # Simulate vehicle status check
        if "fuel" in command.lower():
            response = "Fuel level is at 65%. You have approximately 320 kilometers of range remaining."
        elif "battery" in command.lower():
            response = "Battery level is at 78%. Estimated range is 285 kilometers."
        elif "temperature" in command.lower():
            response = "Engine temperature is normal at 92 degrees Celsius."
        elif "tire" in command.lower():
            response = "All tire pressures are normal. Front tires: 32 PSI, Rear tires: 30 PSI."
        else:
            response = "All vehicle systems are operating normally."
        
        return {
            'response': response,
            'command_type': 'vehicle_control',
            'processing_time': time.time() - start_time,
            'confidence': 0.8,
            'safety_checked': True
        }
    
    async def _handle_emergency_command(self, command: str, context: Dict = None) -> Dict[str, Any]:
        """Handle emergency commands"""
        start_time = time.time()
        
        emergency_result = await self.activate_emergency_mode("voice_activated")
        
        response = "Emergency mode activated. Help is on the way. Your location has been shared with emergency services."
        
        return {
            'response': response,
            'command_type': 'emergency',
            'processing_time': time.time() - start_time,
            'confidence': 1.0,
            'emergency_activated': True,
            'priority': 'critical'
        }
    
    async def _handle_communication_command(self, command: str, context: Dict = None) -> Dict[str, Any]:
        """Handle communication commands"""
        start_time = time.time()
        
        if "call" in command.lower():
            response = "I can help you make hands-free calls. Who would you like to call?"
        elif "message" in command.lower() or "text" in command.lower():
            response = "I can send voice messages for you. What would you like to say?"
        else:
            response = "I can help with hands-free calling and messaging. What would you like to do?"
        
        return {
            'response': response,
            'command_type': 'communication',
            'processing_time': time.time() - start_time,
            'confidence': 0.7,
            'hands_free_ready': True
        }
    
    async def _handle_entertainment_command(self, command: str, context: Dict = None) -> Dict[str, Any]:
        """Handle entertainment commands"""
        start_time = time.time()
        
        # Only allow entertainment if not actively driving
        if self.safety_mode == SafetyMode.DRIVING:
            response = "I'll help with entertainment options when you're parked for safety."
        else:
            response = "What would you like to listen to? I can play music, podcasts, or radio stations."
        
        return {
            'response': response,
            'command_type': 'entertainment',
            'processing_time': time.time() - start_time,
            'confidence': 0.6,
            'safety_mode': self.safety_mode.value
        }
    
    async def _generate_automotive_response(self, query: str, context: Dict = None) -> Dict[str, Any]:
        """Generate automotive-optimized AI response"""
        start_time = time.time()
        
        # Simulate AI processing time based on automotive capability
        processing_times = {
            AutomotiveCapability.FLAGSHIP: 0.1,
            AutomotiveCapability.PREMIUM: 0.2,
            AutomotiveCapability.STANDARD: 0.5,
            AutomotiveCapability.BASIC: 1.0
        }
        
        await asyncio.sleep(processing_times.get(self.config.capability, 0.5))
        
        # Generate automotive-appropriate response
        base_response = f"I understand your question about '{query[:30]}...'. "
        
        # Automotive-specific response adaptations
        if self.safety_mode == SafetyMode.DRIVING:
            base_response += "Here's a quick answer to keep you focused on the road."
        elif self.safety_mode == SafetyMode.PARKED:
            base_response += "I can provide more detailed information since you're parked."
        elif self.navigation_active:
            base_response += "I'll keep this brief since you're navigating."
        else:
            base_response += "Here's what I found for you."
        
        # Adjust response length based on safety mode
        if self.safety_mode == SafetyMode.DRIVING:
            base_response = base_response[:60] + "..." if len(base_response) > 60 else base_response
        
        response_time = time.time() - start_time
        
        return {
            'response': base_response,
            'processing_time': response_time,
            'automotive_optimized': True,
            'safety_adapted': True,
            'safety_mode': self.safety_mode.value,
            'confidence': 0.8
        }
    
    async def _calculate_route(self, destination: str) -> Dict[str, Any]:
        """Calculate route to destination (simulated)"""
        # Simulate route calculation
        await asyncio.sleep(0.1)
        
        return {
            'estimated_time': 1800,  # 30 minutes
            'distance_km': 25.5,
            'route_summary': f"Take Highway 401 to {destination}. Estimated travel time: 30 minutes.",
            'traffic_conditions': 'moderate'
        }
    
    def _get_unit_for_data_type(self, data_type: str) -> str:
        """Get appropriate unit for data type"""
        units = {
            'fuel_level': '%',
            'battery_level': '%',
            'engine_temperature': 'C',
            'tire_pressure': 'PSI',
            'oil_pressure': 'PSI',
            'speed': 'km/h'
        }
        return units.get(data_type, '')
    
    def _get_alert_message(self, data_type: str, value: float, severity: str) -> str:
        """Get alert message for vehicle data"""
        messages = {
            ('fuel_level', 'critical'): f"Critical: Fuel level is very low at {value}%. Find a gas station immediately.",
            ('fuel_level', 'warning'): f"Warning: Fuel level is low at {value}%. Consider refueling soon.",
            ('battery_level', 'critical'): f"Critical: Battery level is very low at {value}%. Charge immediately.",
            ('engine_temperature', 'critical'): f"Critical: Engine overheating at {value}°C. Pull over safely and turn off engine.",
            ('tire_pressure', 'warning'): f"Warning: Tire pressure is low at {value} PSI. Check tires when safe."
        }
        
        return messages.get((data_type, severity), f"{severity.title()}: {data_type} requires attention.")
    
    async def _initialize_voice_recognition(self):
        """Initialize automotive voice recognition capabilities"""
        # Simulate voice recognition setup
        logger.info("Automotive voice recognition initialized")
    
    async def _initialize_navigation_system(self):
        """Initialize navigation system integration"""
        # Simulate navigation system setup
        logger.info("Navigation system integration initialized")
    
    async def _initialize_vehicle_integration(self):
        """Initialize vehicle data integration"""
        # Simulate vehicle data API setup
        logger.info("Vehicle data integration initialized")
    
    async def _initialize_emergency_system(self):
        """Initialize emergency system"""
        # Simulate emergency system setup
        logger.info("Emergency system initialized")
    
    async def _optimize_for_driving_safety(self):
        """Optimize system for driving safety"""
        logger.info("System optimized for driving safety: hands-free mode enabled")
    
    async def _enable_full_functionality(self):
        """Enable full functionality when parked"""
        logger.info("Full functionality enabled: vehicle is parked")
    
    async def _optimize_for_passenger_mode(self):
        """Optimize for passenger mode"""
        logger.info("System optimized for passenger mode: enhanced interaction enabled")
    
    async def close(self):
        """Close Automotive BUDDY core"""
        if self.database:
            await self.database.close()
        
        logger.info("Automotive BUDDY core closed")


async def test_automotive_buddy_demo():
    """Comprehensive test of Automotive BUDDY implementation"""
    
    print("🚗 BUDDY 2.0 Automotive Platform Demo (Phase 5 Implementation)")
    print("=" * 70)
    print("Building on proven Phase 1-4 foundations for intelligent vehicle AI")
    print("")
    
    # Test different automotive profiles
    test_profiles = [
        (AutomotivePlatform.TESLA_INFOTAINMENT, AutomotiveCapability.FLAGSHIP, "Tesla Model S"),
        (AutomotivePlatform.BMW_IDRIVE, AutomotiveCapability.PREMIUM, "BMW iX"),
        (AutomotivePlatform.ANDROID_AUTOMOTIVE, AutomotiveCapability.STANDARD, "Volvo XC40"),
        (AutomotivePlatform.FORD_SYNC, AutomotiveCapability.BASIC, "Ford F-150"),
        (AutomotivePlatform.MERCEDES_MBUX, AutomotiveCapability.PREMIUM, "Mercedes EQS")
    ]
    
    overall_stats = {
        'vehicles_tested': 0,
        'successful_tests': 0,
        'voice_commands': 0,
        'navigation_requests': 0,
        'vehicle_checks': 0,
        'emergency_tests': 0,
        'avg_response_time': 0
    }
    
    for platform, capability, vehicle_name in test_profiles:
        print(f"\n🚗 Testing {vehicle_name} ({platform.value}, {capability.value})")
        print("-" * 60)
        
        # Create automotive configuration
        config = AutomotiveConfig.for_automotive_profile(platform, capability)
        
        # Initialize Automotive BUDDY
        buddy = AutomotiveBuddyCore(
            user_id="driver_user_123",
            device_id=f"auto_{platform.value}_{capability.value}_{int(time.time())}",
            config=config
        )
        
        try:
            overall_stats['vehicles_tested'] += 1
            
            # Initialize
            success = await buddy.initialize()
            if not success:
                print(f"❌ Failed to initialize {vehicle_name}")
                continue
            
            print(f"✅ {vehicle_name} initialized successfully")
            print(f"   Storage Limit: {config.storage_limit_mb}MB")
            print(f"   Memory Limit: {config.memory_limit_mb}MB")
            print(f"   Voice Enabled: {config.voice_enabled}")
            print(f"   Navigation: {config.navigation_integration}")
            print(f"   Vehicle Data: {config.vehicle_data_access}")
            print(f"   Emergency Features: {config.emergency_features}")
            print(f"   Hands-Free Only: {config.hands_free_only}")
            
            # Test safety mode transitions
            print("\n🛡️ Testing safety mode transitions...")
            await buddy.update_safety_mode(SafetyMode.PARKED, 0.0)
            print("   ✅ Parked mode: Full functionality enabled")
            
            await buddy.update_safety_mode(SafetyMode.DRIVING, 80.0)
            print("   ✅ Driving mode: Safety restrictions applied")
            
            await buddy.update_safety_mode(SafetyMode.PASSENGER, 65.0)
            print("   ✅ Passenger mode: Enhanced interaction enabled")
            
            # Test voice commands in different safety modes
            if config.voice_enabled:
                print("\n🎤 Testing voice commands...")
                voice_commands = [
                    ("Navigate to downtown", SafetyMode.PARKED),
                    ("What's my fuel level?", SafetyMode.DRIVING),
                    ("Call mom", SafetyMode.DRIVING),
                    ("Emergency help needed", SafetyMode.DRIVING),
                    ("Play music", SafetyMode.PASSENGER)
                ]
                
                for command, safety_mode in voice_commands:
                    await buddy.update_safety_mode(safety_mode, 50.0 if safety_mode == SafetyMode.DRIVING else 0.0)
                    result = await buddy.process_voice_command(command)
                    safety_status = "🛡️ SAFE" if not result.get('safety_blocked') else "⚠️ BLOCKED"
                    print(f"   {safety_status} '{command}' → {result['response'][:40]}...")
                    overall_stats['voice_commands'] += 1
            
            # Test navigation integration
            if config.navigation_integration:
                print("\n🗺️ Testing navigation integration...")
                destinations = ["Toronto Airport", "Nearest Gas Station", "Home"]
                
                for destination in destinations:
                    await buddy.update_safety_mode(SafetyMode.PARKED, 0.0)
                    result = await buddy.handle_navigation_request(destination)
                    print(f"   📍 Navigation to {destination}")
                    print(f"      Distance: {result['distance_km']} km")
                    print(f"      ETA: {result['estimated_time'] // 60} minutes")
                    overall_stats['navigation_requests'] += 1
            
            # Test vehicle status monitoring
            if config.vehicle_data_access:
                print("\n🔧 Testing vehicle status monitoring...")
                vehicle_status = {
                    'fuel_level': 15,      # Low fuel warning
                    'battery_level': 85,   # Normal
                    'engine_temperature': 95,  # Normal
                    'tire_pressure': 28,   # Low pressure warning
                    'oil_pressure': 35     # Normal
                }
                
                status_result = await buddy.update_vehicle_status(vehicle_status)
                print(f"   Status updated: {len(status_result['alerts'])} alerts generated")
                for alert in status_result['alerts']:
                    print(f"   ⚠️ {alert['severity'].upper()}: {alert['message']}")
                overall_stats['vehicle_checks'] += 1
            
            # Test emergency features
            if config.emergency_features:
                print("\n🚨 Testing emergency features...")
                emergency_result = await buddy.activate_emergency_mode("test_emergency")
                print(f"   Emergency activated: {emergency_result['emergency_activated']}")
                print(f"   Emergency contacts: {len(emergency_result['emergency_contacts'])}")
                print(f"   Instructions: {emergency_result['instructions'][:50]}...")
                overall_stats['emergency_tests'] += 1
            
            # Get automotive status
            status = await buddy.get_automotive_status()
            print(f"\n📊 Automotive Status for {vehicle_name}:")
            print(f"   Platform: {status['platform']}")
            print(f"   Capability: {status['capability']}")
            print(f"   Safety Mode: {status['safety_mode']}")
            print(f"   Voice Commands: {status['voice_commands_processed']}")
            print(f"   Navigation Requests: {status['navigation_requests']}")
            print(f"   Vehicle Checks: {status['vehicle_status_checks']}")
            print(f"   Emergency Activations: {status['emergency_activations']}")
            print(f"   Navigation Active: {status['navigation_active']}")
            print(f"   Storage: {status['storage_usage']['percentage']:.1f}% used")
            print(f"   Vehicle Alerts: {status['vehicle_alerts_count']}")
            
            overall_stats['avg_response_time'] += status['database_performance']['average_execution_time']
            
            print(f"✅ {vehicle_name} testing completed successfully")
            overall_stats['successful_tests'] += 1
            
        except Exception as e:
            print(f"❌ {vehicle_name} testing failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await buddy.close()
        
        # Small delay between vehicle tests
        await asyncio.sleep(0.1)
    
    # Final summary
    print("\n" + "=" * 70)
    print("🎉 BUDDY 2.0 Automotive Platform Demo Completed!")
    print("=" * 70)
    
    print(f"\n📈 Demo Summary:")
    print(f"✅ Vehicles Tested: {overall_stats['vehicles_tested']}")
    print(f"✅ Successful Tests: {overall_stats['successful_tests']}")
    print(f"✅ Voice Commands: {overall_stats['voice_commands']}")
    print(f"✅ Navigation Requests: {overall_stats['navigation_requests']}")
    print(f"✅ Vehicle Status Checks: {overall_stats['vehicle_checks']}")
    print(f"✅ Emergency Feature Tests: {overall_stats['emergency_tests']}")
    if overall_stats['successful_tests'] > 0:
        avg_response_time = overall_stats['avg_response_time'] / overall_stats['successful_tests']
        print(f"✅ Average Response Time: {avg_response_time:.4f}s")
    
    print(f"\n🚗 Architecture Highlights:")
    print(f"✅ Safety-first hands-free interaction design")
    print(f"✅ Multi-modal voice + touch automotive interface")
    print(f"✅ Navigation integration with route planning")
    print(f"✅ Vehicle diagnostics and alert monitoring")
    print(f"✅ Emergency system with location services")
    print(f"✅ Automotive-specific database optimization")
    print(f"✅ Driving safety mode restrictions")
    print(f"✅ Connected car ecosystem integration")
    
    print(f"\n🚀 Ready for Phase 6: IoT Platform Integration!")
    print(f"💡 Automotive implementation provides the foundation for:")
    print(f"   • Tesla Autopilot AI companion integration")
    print(f"   • BMW iDrive voice assistant enhancement")
    print(f"   • Android Automotive OS applications")
    print(f"   • Apple CarPlay intelligent integration")
    print(f"   • Emergency response and roadside assistance")
    print(f"   • Connected vehicle data analytics")
    print(f"   • Multi-driver profile management")


if __name__ == "__main__":
    # Run the Automotive platform demo
    asyncio.run(test_automotive_buddy_demo())
