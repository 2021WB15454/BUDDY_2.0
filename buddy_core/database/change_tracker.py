"""
BUDDY Change Tracker

Automatically tracks database changes for cross-platform synchronization.
Integrates with the sync engine to provide real-time data consistency.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
import uuid

from .sync_engine import BuddySyncEngine, SyncRecord

logger = logging.getLogger(__name__)


class ChangeTracker:
    """
    Tracks changes to BUDDY data for synchronization across devices.
    
    Features:
    - Automatic change detection for all database operations
    - Context-aware tracking (user, device, session)
    - Priority-based sync triggering
    - Change deduplication and batching
    """
    
    def __init__(self, sync_engine: BuddySyncEngine):
        self.sync_engine = sync_engine
        self.change_listeners: Dict[str, List[Callable]] = {}
        self.tracked_tables = {
            'conversations', 'user_preferences', 'ai_context', 
            'reminders', 'skill_data', 'device_settings'
        }
        self.priority_tables = {'conversations', 'user_preferences', 'ai_context'}
        self.batch_changes: Dict[str, List[Dict]] = {}
        self.batch_timeout = 5  # seconds
        
        logger.info("Change Tracker initialized")
    
    async def track_change(self, table_name: str, record_id: str, 
                          operation: str, data: Dict, 
                          user_id: str, device_id: str,
                          context: Optional[Dict] = None):
        """
        Track a data change for synchronization.
        
        Args:
            table_name: Name of the table/collection
            record_id: Unique identifier for the record
            operation: CREATE, UPDATE, DELETE
            data: The changed data
            user_id: User who made the change
            device_id: Device where change originated
            context: Additional context (session_id, etc.)
        """
        if table_name not in self.tracked_tables:
            logger.debug(f"Table {table_name} not tracked for sync")
            return
        
        # Enrich data with metadata
        enriched_data = data.copy()
        enriched_data.update({
            'sync_metadata': {
                'table_name': table_name,
                'operation': operation,
                'user_id': user_id,
                'device_id': device_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'context': context or {}
            }
        })
        
        # Create sync record
        try:
            await self.sync_engine.track_change(
                table_name=table_name,
                record_id=record_id,
                operation=operation,
                data=enriched_data,
                context=context
            )
            
            # Trigger change listeners
            await self._notify_change_listeners(table_name, record_id, operation, enriched_data)
            
            # For high-priority tables, trigger immediate sync
            if table_name in self.priority_tables and await self.sync_engine.is_online():
                asyncio.create_task(self.sync_engine.sync_changes())
            
            logger.debug(f"Change tracked: {table_name}.{record_id} ({operation})")
            
        except Exception as e:
            logger.error(f"Failed to track change for {table_name}.{record_id}: {e}")
            raise
    
    async def track_conversation_message(self, conversation_id: str, message_data: Dict,
                                       user_id: str, device_id: str, session_id: str):
        """Track a new conversation message with special handling."""
        # Add conversation-specific metadata
        enriched_message = message_data.copy()
        enriched_message.update({
            'conversation_id': conversation_id,
            'session_id': session_id,
            'device_origin': device_id,
            'sync_priority': 'high'
        })
        
        await self.track_change(
            table_name='conversations',
            record_id=message_data.get('id', str(uuid.uuid4())),
            operation='CREATE',
            data=enriched_message,
            user_id=user_id,
            device_id=device_id,
            context={
                'session_id': session_id,
                'conversation_id': conversation_id,
                'message_type': message_data.get('type', 'unknown')
            }
        )
    
    async def track_preference_change(self, preference_key: str, preference_value: Any,
                                    user_id: str, device_id: str, is_device_specific: bool = False):
        """Track user preference changes."""
        preference_data = {
            'key': preference_key,
            'value': preference_value,
            'is_device_specific': is_device_specific,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        await self.track_change(
            table_name='user_preferences',
            record_id=preference_key,
            operation='UPDATE',
            data=preference_data,
            user_id=user_id,
            device_id=device_id,
            context={
                'preference_type': 'device_specific' if is_device_specific else 'global'
            }
        )
    
    async def track_ai_context_update(self, context_id: str, context_data: Dict,
                                    user_id: str, device_id: str, session_id: str):
        """Track AI context updates for cross-device continuity."""
        enriched_context = context_data.copy()
        enriched_context.update({
            'context_id': context_id,
            'session_id': session_id,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'sync_priority': 'medium'
        })
        
        await self.track_change(
            table_name='ai_context',
            record_id=context_id,
            operation='UPDATE',
            data=enriched_context,
            user_id=user_id,
            device_id=device_id,
            context={
                'session_id': session_id,
                'context_type': context_data.get('type', 'general')
            }
        )
    
    async def add_change_listener(self, table_name: str, callback: Callable):
        """Add a listener for changes to a specific table."""
        if table_name not in self.change_listeners:
            self.change_listeners[table_name] = []
        self.change_listeners[table_name].append(callback)
    
    async def _notify_change_listeners(self, table_name: str, record_id: str, 
                                     operation: str, data: Dict):
        """Notify registered listeners about changes."""
        listeners = self.change_listeners.get(table_name, [])
        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(table_name, record_id, operation, data)
                else:
                    listener(table_name, record_id, operation, data)
            except Exception as e:
                logger.error(f"Change listener error: {e}")


class EnhancedDatabase:
    """
    Enhanced database wrapper that automatically tracks changes for sync.
    
    This wraps your existing database operations to add automatic
    change tracking without requiring code changes throughout the system.
    """
    
    def __init__(self, base_db, change_tracker: ChangeTracker, user_id: str, device_id: str):
        self.base_db = base_db
        self.change_tracker = change_tracker
        self.user_id = user_id
        self.device_id = device_id
        self.session_context: Optional[Dict] = None
    
    def set_session_context(self, session_id: str, conversation_id: Optional[str] = None):
        """Set current session context for tracking."""
        self.session_context = {
            'session_id': session_id,
            'conversation_id': conversation_id
        }
    
    async def insert_conversation(self, conversation_data: Dict) -> Any:
        """Insert conversation with automatic change tracking."""
        # Perform the actual database insert
        result = await self.base_db.execute_insert("conversations", conversation_data)
        
        # Track the change
        await self.change_tracker.track_conversation_message(
            conversation_id=conversation_data.get('conversation_id', 'default'),
            message_data=conversation_data,
            user_id=self.user_id,
            device_id=self.device_id,
            session_id=self.session_context.get('session_id') if self.session_context else 'unknown'
        )
        
        return result
    
    async def update_conversation(self, conversation_id: str, updates: Dict) -> Any:
        """Update conversation with automatic change tracking."""
        result = await self.base_db.execute_update("conversations", conversation_id, updates)
        
        # Track the change
        await self.change_tracker.track_change(
            table_name='conversations',
            record_id=conversation_id,
            operation='UPDATE',
            data=updates,
            user_id=self.user_id,
            device_id=self.device_id,
            context=self.session_context
        )
        
        return result
    
    async def set_user_preference(self, key: str, value: Any, device_specific: bool = False):
        """Set user preference with automatic change tracking."""
        # Store in base database
        preference_record = {
            'key': key,
            'value': json.dumps(value) if isinstance(value, (dict, list)) else str(value),
            'is_device_specific': device_specific,
            'user_id': self.user_id,
            'device_id': self.device_id if device_specific else None
        }
        
        result = await self.base_db.execute_upsert("user_preferences", preference_record)
        
        # Track the change
        await self.change_tracker.track_preference_change(
            preference_key=key,
            preference_value=value,
            user_id=self.user_id,
            device_id=self.device_id,
            is_device_specific=device_specific
        )
        
        return result
    
    async def update_ai_context(self, context_data: Dict) -> Any:
        """Update AI context with automatic change tracking."""
        context_id = context_data.get('id', str(uuid.uuid4()))
        
        # Store in base database
        result = await self.base_db.execute_upsert("ai_context", context_data)
        
        # Track the change
        await self.change_tracker.track_ai_context_update(
            context_id=context_id,
            context_data=context_data,
            user_id=self.user_id,
            device_id=self.device_id,
            session_id=self.session_context.get('session_id') if self.session_context else 'unknown'
        )
        
        return result
    
    async def delete_record(self, table_name: str, record_id: str) -> Any:
        """Delete record with automatic change tracking."""
        result = await self.base_db.execute_delete(table_name, record_id)
        
        # Track the deletion
        await self.change_tracker.track_change(
            table_name=table_name,
            record_id=record_id,
            operation='DELETE',
            data={'deleted': True, 'deleted_at': datetime.now(timezone.utc).isoformat()},
            user_id=self.user_id,
            device_id=self.device_id,
            context=self.session_context
        )
        
        return result
    
    # Delegate other database operations to base database
    async def execute_query(self, query: str, params: Optional[List] = None):
        """Execute raw query (no automatic tracking)."""
        return await self.base_db.execute_query(query, params)
    
    async def get_conversations(self, limit: int = 50, offset: int = 0):
        """Get conversations (read-only, no tracking needed)."""
        return await self.base_db.get_conversations(limit, offset)
    
    async def get_user_preferences(self, device_specific: bool = False):
        """Get user preferences (read-only, no tracking needed)."""
        return await self.base_db.get_user_preferences(device_specific)


# Integration with existing BUDDY memory layer
class SyncAwareMemoryLayer:
    """
    Memory layer that integrates with the sync system for cross-device continuity.
    """
    
    def __init__(self, enhanced_db: EnhancedDatabase, sync_engine: BuddySyncEngine):
        self.db = enhanced_db
        self.sync_engine = sync_engine
        self.context_cache: Dict[str, Dict] = {}
    
    async def store_conversation(self, conversation_data: Dict, session_id: str) -> str:
        """Store conversation with sync awareness."""
        conversation_id = conversation_data.get('id', str(uuid.uuid4()))
        
        # Set session context
        self.db.set_session_context(session_id, conversation_id)
        
        # Store conversation
        await self.db.insert_conversation(conversation_data)
        
        # Cache for quick access
        self.context_cache[conversation_id] = conversation_data
        
        return conversation_id
    
    async def get_conversation_context(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation context with sync status."""
        # Check cache first
        if conversation_id in self.context_cache:
            return self.context_cache[conversation_id]
        
        # Get from database
        context = await self.db.get_conversation_by_id(conversation_id)
        if context:
            self.context_cache[conversation_id] = context
        
        return context
    
    async def update_context(self, context_data: Dict, session_id: str):
        """Update AI context across devices."""
        self.db.set_session_context(session_id)
        await self.db.update_ai_context(context_data)
        
        # Update cache
        context_id = context_data.get('id')
        if context_id:
            self.context_cache[context_id] = context_data
    
    async def sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        return await self.sync_engine.get_sync_status()
