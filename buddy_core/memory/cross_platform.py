"""
BUDDY Cross-Platform Memory Integration

Integration layer that combines the existing memory system with
the new cross-platform synchronization capabilities and optimized database.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone
import uuid

# Import existing memory layer
from . import EnhancedMemoryLayer as BaseMemoryLayer

# Import optimized database
from ..database.optimized_local_db import OptimizedLocalDatabase, create_optimized_database

# Import sync components
try:
    from ..database.sync_engine import BuddySyncEngine, DeviceInfo
    from ..database.change_tracker import ChangeTracker, EnhancedDatabase, SyncAwareMemoryLayer
    SYNC_AVAILABLE = True
except ImportError:
    SYNC_AVAILABLE = False

logger = logging.getLogger(__name__)


class CrossPlatformMemoryLayer(BaseMemoryLayer):
    """
    Enhanced memory layer with cross-platform sync capabilities and optimized database.
    
    Extends the existing EnhancedMemoryLayer with:
    - Real-time device synchronization
    - Optimized database performance per device type
    - Intelligent conflict resolution
    - Offline-first operation
    - Device-aware context management
    """
    
    def __init__(self, user_id: str, device_id: str, device_type: str = "desktop", **kwargs):
        # Initialize base memory layer with config format it expects
        config = kwargs.get('config', {})
        config.update({
            'user_id': user_id,
            'device_id': device_id,
            'device_type': device_type
        })
        super().__init__(config=config)
        
        self.user_id = user_id
        self.device_id = device_id
        self.device_type = device_type
        
        # Optimized database
        self.optimized_db: Optional[OptimizedLocalDatabase] = None
        
        # Sync components (if available)
        self.sync_engine: Optional[BuddySyncEngine] = None
        self.change_tracker: Optional[ChangeTracker] = None
        self.enhanced_db: Optional[EnhancedDatabase] = None
        self.sync_memory: Optional[SyncAwareMemoryLayer] = None
        
        # Cross-platform state
        self.connected_devices: Dict[str, DeviceInfo] = {}
        self.sync_enabled = False
        
        logger.info(f"Cross-Platform Memory Layer initialized for {device_type}: {device_id}")
    
    async def initialize_with_sync(self, enable_sync: bool = True, cloud_config: Optional[Dict] = None):
        """Initialize with sync capabilities and optimized database."""
        # Initialize optimized database first
        await self._setup_optimized_database()
        
        # Initialize base memory layer
        await super().initialize()
        
        if enable_sync and SYNC_AVAILABLE:
            try:
                await self._setup_sync_system(cloud_config)
                self.sync_enabled = True
            except Exception as e:
                logger.error(f"Failed to setup sync system: {e}")
                self.sync_enabled = False
        
        logger.info(f"Cross-platform memory initialized (sync: {self.sync_enabled}, optimized_db: {self.optimized_db is not None})")
    
    async def _setup_optimized_database(self):
        """Set up the optimized database for this device type."""
        try:
            # Create optimized database instance
            self.optimized_db = create_optimized_database(self.device_type)
            await self.optimized_db.initialize()
            
            logger.info(f"Optimized database initialized for {self.device_type}")
            
        except Exception as e:
            logger.error(f"Failed to setup optimized database: {e}")
            raise
    
    async def store_conversation_optimized(self, content: str, message_type: str = "user", 
                                         session_id: Optional[str] = None, 
                                         metadata: Optional[Dict] = None) -> str:
        """Store conversation using optimized database with cross-platform sync."""
        try:
            # Use session_id if provided, otherwise generate one
            if not session_id:
                session_id = f"session_{self.device_type}_{int(datetime.now().timestamp())}"
            
            # Add device metadata
            if not metadata:
                metadata = {}
            metadata.update({
                'device_id': self.device_id,
                'device_type': self.device_type,
                'cross_platform': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Store using optimized database if available
            if self.optimized_db:
                conversation_id = await self.optimized_db.store_conversation_optimized(
                    user_id=self.user_id,
                    session_id=session_id,
                    content=content,
                    message_type=message_type,
                    metadata=metadata,
                    device_id=self.device_id
                )
                logger.debug(f"Stored conversation {conversation_id} via optimized database")
            else:
                # Fallback to base implementation
                conversation_id = await super().store_conversation(
                    content=content,
                    message_type=message_type,
                    session_id=session_id,
                    metadata=metadata
                )
                logger.debug(f"Stored conversation {conversation_id} via base database")
            
            return conversation_id
            
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
            raise
    
    async def get_conversation_history_optimized(self, limit: int = 50, 
                                               include_all_devices: bool = True,
                                               session_id: Optional[str] = None) -> List[Dict]:
        """Get conversation history using optimized database with cross-platform support."""
        try:
            if self.optimized_db:
                # Use optimized database
                conversations = await self.optimized_db.get_conversations_optimized(
                    user_id=self.user_id,
                    session_id=session_id,
                    limit=limit
                )
                
                # Filter by device if needed
                if not include_all_devices:
                    conversations = [
                        conv for conv in conversations 
                        if conv.get('device_id') == self.device_id
                    ]
                
                logger.debug(f"Retrieved {len(conversations)} conversations via optimized database")
                return conversations
            else:
                # Fallback to base implementation
                conversations = await super().get_conversation_history(limit=limit)
                logger.debug(f"Retrieved {len(conversations)} conversations via base database")
                return conversations
                
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    async def set_preference_optimized(self, key: str, value: Any, device_specific: bool = False):
        """Set preference using optimized database with cross-platform sync."""
        try:
            if self.optimized_db:
                # Use optimized database
                await self.optimized_db.set_user_preference_optimized(
                    user_id=self.user_id,
                    key=key,
                    value=value,
                    device_specific=device_specific
                )
                logger.debug(f"Set preference {key} via optimized database (device_specific: {device_specific})")
            else:
                # Fallback to base implementation
                await super().set_preference(key, value)
                logger.debug(f"Set preference {key} via base database")
                
        except Exception as e:
            logger.error(f"Failed to set preference {key}: {e}")
            raise
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from optimized database."""
        try:
            if self.optimized_db:
                return await self.optimized_db.get_performance_report()
            else:
                return {"error": "Optimized database not available"}
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e)}
    
    async def cleanup_expired_data_optimized(self) -> Dict[str, Any]:
        """Cleanup expired data using optimized database."""
        try:
            if self.optimized_db:
                return await self.optimized_db.cleanup_expired_data()
            else:
                return {"error": "Optimized database not available"}
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return {"error": str(e)}
    
    async def optimize_database_performance(self) -> Dict[str, Any]:
        """Run database optimization routines."""
        try:
            if self.optimized_db:
                return await self.optimized_db.optimize_database()
            else:
                return {"error": "Optimized database not available"}
        except Exception as e:
            logger.error(f"Failed to optimize database: {e}")
            return {"error": str(e)}
    
    async def _setup_sync_system(self, cloud_config: Optional[Dict] = None):
        """Set up the synchronization system."""
        try:
            # Initialize sync engine
            self.sync_engine = BuddySyncEngine(
                local_db=self.db_manager.local_db,
                cloud_db=None,  # Would be configured with cloud_config
                vector_db=self.db_manager.vector_db if hasattr(self.db_manager, 'vector_db') else None
            )
            
            # Initialize change tracker
            self.change_tracker = ChangeTracker(self.sync_engine)
            
            # Wrap database with change tracking
            self.enhanced_db = EnhancedDatabase(
                base_db=self.db_manager,
                change_tracker=self.change_tracker,
                user_id=self.user_id,
                device_id=self.device_id
            )
            
            # Initialize sync-aware memory
            self.sync_memory = SyncAwareMemoryLayer(
                enhanced_db=self.enhanced_db,
                sync_engine=self.sync_engine
            )
            
            # Create device info
            device_info = DeviceInfo(
                device_id=self.device_id,
                user_id=self.user_id,
                device_type=self.device_type,
                device_name=f"BUDDY-{self.device_type}-{self.device_id[:8]}",
                capabilities=self._get_device_capabilities()
            )
            
            # Initialize sync engine
            await self.sync_engine.initialize(device_info)
            
            logger.info("Sync system setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup sync system: {e}")
            self.sync_enabled = False
    
    def _get_device_capabilities(self) -> List[str]:
        """Get capabilities for current device type."""
        base_capabilities = ['messaging', 'context_storage', 'preferences']
        
        device_capabilities = {
            'desktop': base_capabilities + ['voice_input', 'voice_output', 'screen_large', 'keyboard_input'],
            'mobile': base_capabilities + ['voice_input', 'voice_output', 'screen_medium', 'touch_input', 'location'],
            'watch': base_capabilities + ['voice_input', 'voice_output', 'screen_small', 'touch_input', 'health_sensors'],
            'tv': base_capabilities + ['voice_input', 'voice_output', 'screen_large', 'remote_input'],
            'car': base_capabilities + ['voice_input', 'voice_output', 'location', 'automotive_integration']
        }
        
        return device_capabilities.get(self.device_type, base_capabilities)
    
    async def store_conversation(self, content: str, message_type: str = "user", 
                               session_id: Optional[str] = None, metadata: Optional[Dict] = None) -> str:
        """Store conversation with cross-platform sync."""
        # Enhance metadata with device information
        enhanced_metadata = (metadata or {}).copy()
        enhanced_metadata.update({
            'device_id': self.device_id,
            'device_type': self.device_type,
            'sync_enabled': self.sync_enabled
        })
        
        if self.sync_memory and self.sync_enabled:
            # Use sync-aware storage
            conversation_data = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'device_id': self.device_id,
                'session_id': session_id or self.session_id,
                'content': content,
                'message_type': message_type,
                'metadata': enhanced_metadata,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'device_type': self.device_type
            }
            
            conversation_id = await self.sync_memory.store_conversation(
                conversation_data, 
                session_id or self.session_id
            )
            
            # Update cache
            self.conversation_cache[conversation_id] = conversation_data
            
            return conversation_id
        else:
            # Fallback to base implementation
            return await super().store_conversation(content, message_type, metadata)
    
    async def get_conversation_history(self, limit: int = 50, session_id: Optional[str] = None, 
                                     include_all_devices: bool = True) -> List[Dict]:
        """Get conversation history with optional cross-device filtering."""
        conversations = await super().get_conversation_history(limit, session_id)
        
        if self.sync_enabled and self.sync_engine:
            # Add sync metadata
            sync_status = await self.sync_engine.get_sync_status()
            for conv in conversations:
                conv['sync_info'] = {
                    'is_synced': sync_status['is_online'],
                    'last_sync': sync_status['last_sync'],
                    'device_origin': conv.get('device_id', 'unknown'),
                    'from_current_device': conv.get('device_id') == self.device_id
                }
                
                # Filter by device if requested
                if not include_all_devices and conv.get('device_id') != self.device_id:
                    conversations.remove(conv)
        
        return conversations
    
    async def store_context(self, context_data: Dict, context_type: str = "general") -> str:
        """Store AI context with device awareness."""
        # Add device information to context
        enhanced_context = context_data.copy()
        enhanced_context.update({
            'device_id': self.device_id,
            'device_type': self.device_type,
            'capabilities': self._get_device_capabilities()
        })
        
        if self.sync_memory and self.sync_enabled:
            context_id = str(uuid.uuid4())
            full_context = {
                'id': context_id,
                'user_id': self.user_id,
                'device_id': self.device_id,
                'type': context_type,
                'data': enhanced_context,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'device_type': self.device_type
            }
            
            await self.sync_memory.update_context(full_context, self.session_id)
            self.context_cache[context_id] = full_context
            
            return context_id
        else:
            return await super().store_context(enhanced_context, context_type)
    
    async def set_preference(self, key: str, value: Any, device_specific: bool = False):
        """Set user preference with device-specific options."""
        if self.enhanced_db and self.sync_enabled:
            await self.enhanced_db.set_user_preference(key, value, device_specific)
        else:
            # Use base implementation
            await super().set_preference(key, value)
    
    async def get_preference(self, key: str, default: Any = None, device_specific: bool = False) -> Any:
        """Get user preference with device-specific handling."""
        if self.enhanced_db and self.sync_enabled:
            # Build cache key
            cache_key = f"{key}:{self.device_id}" if device_specific else key
            
            # Check cache first
            if hasattr(self, 'preference_cache') and cache_key in self.preference_cache:
                return self.preference_cache[cache_key]
            
            # Get from enhanced database
            try:
                # This would be implemented in the enhanced database
                if device_specific:
                    value = await self.db_manager.get_user_preference(
                        user_id=self.user_id,
                        key=key,
                        device_id=self.device_id
                    )
                else:
                    value = await super().get_preference(key, default)
                
                # Cache the result
                if not hasattr(self, 'preference_cache'):
                    self.preference_cache = {}
                self.preference_cache[cache_key] = value
                
                return value if value is not None else default
                
            except Exception as e:
                logger.error(f"Failed to get preference {key}: {e}")
                return default
        else:
            return await super().get_preference(key, default)
    
    async def get_connected_devices(self) -> List[Dict]:
        """Get list of connected BUDDY devices."""
        if self.sync_engine:
            sync_status = await self.sync_engine.get_sync_status()
            return [{
                'device_id': self.device_id,
                'device_type': self.device_type,
                'is_current': True,
                'last_sync': sync_status.get('last_sync'),
                'status': 'online' if sync_status.get('is_online') else 'offline'
            }]
        else:
            return [{
                'device_id': self.device_id,
                'device_type': self.device_type,
                'is_current': True,
                'status': 'offline'
            }]
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get comprehensive sync status."""
        base_status = await super().get_sync_status()
        
        if self.sync_engine:
            sync_status = await self.sync_engine.get_sync_status()
            return {
                **base_status,
                **sync_status,
                'sync_enabled': self.sync_enabled,
                'device_id': self.device_id,
                'device_type': self.device_type,
                'cross_platform': True
            }
        else:
            return {
                **base_status,
                'sync_enabled': False,
                'device_id': self.device_id,
                'device_type': self.device_type,
                'cross_platform': False
            }
    
    async def force_sync(self) -> bool:
        """Force immediate synchronization across devices."""
        if self.sync_engine and self.sync_enabled:
            try:
                await self.sync_engine.sync_changes(force=True)
                logger.info("Force sync completed successfully")
                return True
            except Exception as e:
                logger.error(f"Force sync failed: {e}")
                return False
        else:
            logger.warning("Sync not available")
            return False
    
    async def add_device_callback(self, event: str, callback: Callable):
        """Add callback for device events (connect, disconnect, sync)."""
        if self.sync_engine:
            await self.sync_engine.add_sync_callback(event, callback)
    
    async def close(self):
        """Close the memory layer with final sync."""
        if self.sync_engine and self.sync_enabled:
            try:
                # Final sync before closing
                await self.sync_engine.sync_changes(force=True)
                logger.info("Final sync completed before shutdown")
            except Exception as e:
                logger.error(f"Final sync failed: {e}")
        
        # Close base memory layer
        await super().close()
        
        logger.info("Cross-platform memory layer closed")


# Update the main export to use the enhanced version
if SYNC_AVAILABLE:
    # Use the cross-platform version if sync is available
    MemoryLayer = CrossPlatformMemoryLayer
    logger.info("Using CrossPlatformMemoryLayer with sync capabilities")
else:
    # Fallback to base version
    from . import MemoryLayer
    logger.warning("Sync not available, using base MemoryLayer")

# Additional compatibility exports
EnhancedMemoryLayer = CrossPlatformMemoryLayer
