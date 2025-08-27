"""
BUDDY 2.0 Cross-Device Memory Management System
Handles memory synchronization and user context across all devices
"""

import asyncio
import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class CrossDeviceMemoryManager:
    def __init__(self, db_path="buddy_memory.db", redis_cache=None):
        self.db_path = db_path
        self.cache = redis_cache  # Redis cache (optional)
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for memory storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    preferences TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_interaction TIMESTAMP
                )
            """)
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    device_id TEXT,
                    device_type TEXT,
                    content TEXT,
                    response TEXT,
                    intent TEXT,
                    metadata TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Devices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    device_type TEXT,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    capabilities TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Memory embeddings table (simplified)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    conversation_id INTEGER,
                    embedding_summary TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("Memory database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    async def sync_user_context_across_devices(self, user_id: str, current_device: str) -> dict:
        """Sync and retrieve complete user context for any device"""
        
        try:
            # Get user's complete interaction history
            user_profile = await self.get_comprehensive_user_profile(user_id)
            
            # Get recent conversations from all devices
            recent_conversations = await self.get_recent_conversations(user_id, limit=10)
            
            # Get device-specific preferences
            device_preferences = await self.get_device_preferences(user_id, current_device)
            
            # Get relevant memories (simplified semantic search)
            relevant_memories = await self.search_relevant_memories(user_id)
            
            return {
                'user_profile': user_profile,
                'recent_conversations': recent_conversations,
                'device_preferences': device_preferences,
                'relevant_memories': relevant_memories,
                'last_sync': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Context sync error: {e}")
            return self.get_default_context()
    
    async def get_comprehensive_user_profile(self, user_id: str) -> dict:
        """Get complete user profile from database"""
        
        try:
            # Check cache first (if Redis available)
            if self.cache:
                cached_profile = await self.cache.get(f"user_profile:{user_id}")
                if cached_profile:
                    return json.loads(cached_profile)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user basic info
            cursor.execute("""
                SELECT name, email, preferences, created_at, last_interaction
                FROM users WHERE id = ?
            """, (user_id,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                # Create new user
                cursor.execute("""
                    INSERT INTO users (id, name, preferences)
                    VALUES (?, ?, ?)
                """, (user_id, None, json.dumps({})))
                conn.commit()
                user_data = (None, None, '{}', datetime.now(), datetime.now())
            
            # Get interaction count
            cursor.execute("""
                SELECT COUNT(*) FROM conversations WHERE user_id = ?
            """, (user_id,))
            total_interactions = cursor.fetchone()[0]
            
            # Get devices used with detailed metadata
            cursor.execute("""
                SELECT device_id, device_type, device_name, last_active, capabilities 
                FROM devices WHERE user_id = ?
                ORDER BY last_active DESC
            """, (user_id,))
            
            devices_used = []
            for row in cursor.fetchall():
                device_data = {
                    'id': row[0],
                    'type': row[1],
                    'name': row[2] or row[1],  # Use device_name or fallback to type
                    'last_seen': row[3].isoformat() if row[3] else 'unknown',
                    'capabilities': json.loads(row[4] or '{}')
                }
                devices_used.append(device_data)
            
            # Get recent topics
            cursor.execute("""
                SELECT DISTINCT intent FROM conversations 
                WHERE user_id = ? AND intent IS NOT NULL
                ORDER BY timestamp DESC LIMIT 10
            """, (user_id,))
            recent_topics = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            profile_data = {
                'name': user_data[0],
                'email': user_data[1],
                'preferences': json.loads(user_data[2] or '{}'),
                'created_at': user_data[3],
                'last_interaction': user_data[4],
                'total_interactions': total_interactions,
                'devices_used': devices_used,
                'recent_topics': recent_topics,
                'profile_completeness': self.calculate_profile_completeness(user_data)
            }
            
            # Cache for 1 hour (if Redis available)
            if self.cache:
                await self.cache.setex(
                    f"user_profile:{user_id}", 
                    3600, 
                    json.dumps(profile_data, default=str)
                )
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Profile retrieval error: {e}")
            return self.get_default_profile()
    
    async def get_recent_conversations(self, user_id: str, limit: int = 10) -> list:
        """Get recent conversations from all devices"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT device_type, content, response, intent, timestamp
                FROM conversations 
                WHERE user_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (user_id, limit))
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    'device_type': row[0],
                    'user_message': row[1],
                    'buddy_response': row[2],
                    'intent': row[3],
                    'timestamp': row[4]
                })
            
            conn.close()
            return conversations
            
        except Exception as e:
            logger.error(f"Recent conversations error: {e}")
            return []
    
    async def get_device_preferences(self, user_id: str, device_type: str) -> dict:
        """Get device-specific preferences"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT capabilities FROM devices 
                WHERE user_id = ? AND device_type = ?
            """, (user_id, device_type))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0] or '{}')
            else:
                return self.get_default_device_preferences(device_type)
                
        except Exception as e:
            logger.error(f"Device preferences error: {e}")
            return self.get_default_device_preferences(device_type)
    
    async def search_relevant_memories(self, user_id: str, query: str = None) -> list:
        """Search for relevant memories (simplified semantic search)"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Simple keyword-based search for now
            if query:
                cursor.execute("""
                    SELECT c.content, c.response, c.intent, c.timestamp
                    FROM conversations c
                    WHERE c.user_id = ? AND (
                        c.content LIKE ? OR c.response LIKE ?
                    )
                    ORDER BY c.timestamp DESC LIMIT 5
                """, (user_id, f"%{query}%", f"%{query}%"))
            else:
                # Get most recent relevant conversations
                cursor.execute("""
                    SELECT content, response, intent, timestamp
                    FROM conversations 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC LIMIT 5
                """, (user_id,))
            
            memories = []
            for row in cursor.fetchall():
                memories.append({
                    'content': row[0],
                    'response': row[1],
                    'intent': row[2],
                    'timestamp': row[3],
                    'relevance_score': 0.8  # Simplified scoring
                })
            
            conn.close()
            return memories
            
        except Exception as e:
            logger.error(f"Memory search error: {e}")
            return []
    
    async def update_conversation_memory(self, user_input: str, response: dict, session_context: dict):
        """Update memory with new conversation data"""
        
        try:
            user_id = session_context['user_id']
            device_type = session_context.get('device_type', 'unknown')
            device_id = session_context.get('device_id', f"{device_type}_{user_id}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Store conversation in database
            cursor.execute("""
                INSERT INTO conversations (user_id, device_id, device_type, content, response, intent, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                device_id,
                device_type,
                user_input,
                response['response'],
                response.get('intent', 'unknown'),
                json.dumps({
                    'response_type': response.get('response_type'),
                    'confidence': response.get('confidence', 0.5),
                    'includes_formatting': response.get('includes_formatting', False)
                }),
                datetime.now(timezone.utc)
            ))
            
            conversation_id = cursor.lastrowid
            
            # Update user last interaction
            cursor.execute("""
                UPDATE users SET last_interaction = ? WHERE id = ?
            """, (datetime.now(timezone.utc), user_id))
            
            # Register/update device
            cursor.execute("""
                INSERT OR REPLACE INTO devices (id, user_id, device_type, last_seen, capabilities)
                VALUES (?, ?, ?, ?, ?)
            """, (
                device_id,
                user_id,
                device_type,
                datetime.now(timezone.utc),
                json.dumps(session_context.get('capabilities', {}))
            ))
            
            # Create simplified embedding entry
            embedding_summary = f"{user_input[:50]}..."
            cursor.execute("""
                INSERT INTO memory_embeddings (user_id, conversation_id, embedding_summary)
                VALUES (?, ?, ?)
            """, (user_id, conversation_id, embedding_summary))
            
            conn.commit()
            conn.close()
            
            # Broadcast update to other devices (simplified)
            await self.broadcast_update_to_devices(user_id, {
                'type': 'conversation_update',
                'conversation_id': conversation_id,
                'preview': user_input[:50] + "..." if len(user_input) > 50 else user_input,
                'device_type': device_type
            })
            
            # Invalidate cache
            if self.cache:
                await self.cache.delete(f"user_profile:{user_id}")
            
            logger.info(f"Memory updated: {response.get('intent')} interaction on {device_type}")
            
        except Exception as e:
            logger.error(f"Memory update error: {e}")
    
    async def broadcast_update_to_devices(self, user_id: str, update: dict):
        """Broadcast update to all user's devices (simplified implementation)"""
        
        try:
            if self.cache:
                # Use Redis pub/sub for real-time sync
                await self.cache.publish(f"user_updates:{user_id}", json.dumps(update))
            
            # In a full implementation, this would also use WebSockets
            logger.info(f"Broadcasted update to devices for user {user_id}: {update['type']}")
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
    
    def calculate_profile_completeness(self, user_data) -> float:
        """Calculate how complete the user profile is"""
        
        completeness = 0.0
        if user_data[0]:  # name
            completeness += 0.4
        if user_data[1]:  # email
            completeness += 0.3
        if user_data[2] and user_data[2] != '{}':  # preferences
            completeness += 0.3
        
        return min(completeness, 1.0)
    
    def get_default_context(self) -> dict:
        """Default context when sync fails"""
        return {
            'user_profile': self.get_default_profile(),
            'recent_conversations': [],
            'device_preferences': {},
            'relevant_memories': [],
            'last_sync': datetime.now(timezone.utc).isoformat()
        }
    
    def get_default_profile(self) -> dict:
        """Default user profile"""
        return {
            'name': None,
            'email': None,
            'preferences': {},
            'total_interactions': 0,
            'devices_used': [],
            'recent_topics': [],
            'profile_completeness': 0.0
        }
    
    async def ensure_device_record(self, user_id: str, device_id: str, device_type: str, 
                                   device_name: Optional[str] = None, capabilities: Optional[Dict] = None) -> Dict:
        """Ensure device is properly recorded in the devices table"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if device exists
            cursor.execute("""
                SELECT id FROM devices WHERE user_id = ? AND device_id = ?
            """, (user_id, device_id))
            
            existing = cursor.fetchone()
            now = datetime.now()
            
            if existing:
                # Update existing device
                cursor.execute("""
                    UPDATE devices SET 
                        device_type = ?, 
                        device_name = ?, 
                        last_active = ?,
                        capabilities = ?
                    WHERE user_id = ? AND device_id = ?
                """, (device_type, device_name, now, json.dumps(capabilities or {}), user_id, device_id))
            else:
                # Insert new device
                cursor.execute("""
                    INSERT INTO devices (user_id, device_id, device_type, device_name, last_active, capabilities)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, device_id, device_type, device_name, now, json.dumps(capabilities or {})))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'device_id': device_id,
                'action': 'updated' if existing else 'created'
            }
            
        except Exception as e:
            logger.error(f"Device record error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_default_device_preferences(self, device_type: str) -> dict:
        """Default preferences by device type"""
        
        defaults = {
            'mobile': {'brief_responses': True, 'voice_enabled': True},
            'desktop': {'detailed_responses': True, 'rich_formatting': True},
            'watch': {'ultra_brief': True, 'haptic_feedback': True},
            'car': {'voice_only': True, 'safety_mode': True},
            'tv': {'large_text': True, 'remote_friendly': True}
        }
        
        return defaults.get(device_type, {})
