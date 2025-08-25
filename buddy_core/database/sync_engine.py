"""
BUDDY Cross-Platform Sync Engine

Provides real-time synchronization of data across all BUDDY devices,
with conflict resolution, offline support, and security features.
"""

import asyncio
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class ConflictResolutionStrategy(Enum):
    LAST_WRITER_WINS = "last_writer_wins"
    MERGE_CONVERSATION = "merge_conversation"
    USER_PREFERENCE = "user_preference"
    DEVICE_PRIORITY = "device_priority"
    MANUAL = "manual"


@dataclass
class SyncRecord:
    id: str
    user_id: str
    device_id: str
    table_name: str
    record_id: str
    operation: str  # CREATE, UPDATE, DELETE
    data: Dict[Any, Any]
    timestamp: datetime
    sync_version: int
    status: SyncStatus = SyncStatus.PENDING
    checksum: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum for data integrity verification."""
        data_str = json.dumps(self.data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['status'] = self.status.value
        return result


@dataclass
class DeviceInfo:
    device_id: str
    user_id: str
    device_type: str  # desktop, mobile, watch, tv, car
    device_name: str
    capabilities: List[str]
    last_sync: Optional[datetime] = None
    sync_version: int = 1
    is_active: bool = True
    connection_state: str = "offline"
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.last_sync:
            result['last_sync'] = self.last_sync.isoformat()
        return result


class BuddySyncEngine:
    """
    Core synchronization engine for cross-platform data consistency.
    
    Features:
    - Real-time bidirectional sync
    - Offline-first operation with queue management
    - Intelligent conflict resolution
    - Device capability awareness
    - Security with end-to-end encryption support
    """
    
    def __init__(self, local_db, cloud_db=None, vector_db=None, encryption_key=None):
        self.local_db = local_db
        self.cloud_db = cloud_db
        self.vector_db = vector_db
        self.encryption_key = encryption_key
        
        # Sync management
        self.sync_queue: List[SyncRecord] = []
        self.sync_running = False
        self.sync_interval = 30  # seconds
        self.max_retry_count = 3
        
        # Device registry
        self.registered_devices: Dict[str, DeviceInfo] = {}
        self.current_device: Optional[DeviceInfo] = None
        
        # Conflict resolution
        self.conflict_resolvers: Dict[str, Callable] = {
            ConflictResolutionStrategy.LAST_WRITER_WINS.value: self._last_writer_wins,
            ConflictResolutionStrategy.MERGE_CONVERSATION.value: self._merge_conversation_data,
            ConflictResolutionStrategy.USER_PREFERENCE.value: self._apply_user_preference,
            ConflictResolutionStrategy.DEVICE_PRIORITY.value: self._device_priority_resolution
        }
        
        # Event handlers for real-time sync
        self.sync_callbacks: Dict[str, List[Callable]] = {
            'sync_started': [],
            'sync_completed': [],
            'sync_failed': [],
            'conflict_detected': [],
            'device_connected': [],
            'device_disconnected': []
        }
        
        logger.info("BUDDY Sync Engine initialized")
    
    async def initialize(self, device_info: DeviceInfo):
        """Initialize sync engine for current device."""
        self.current_device = device_info
        await self.initialize_sync_tables()
        await self.register_device(device_info)
        await self.start_background_sync()
        logger.info(f"Sync engine initialized for device: {device_info.device_name}")
    
    async def initialize_sync_tables(self):
        """Create sync-specific tables in local database."""
        sync_schema = """
        CREATE TABLE IF NOT EXISTS sync_log (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            table_name TEXT NOT NULL,
            record_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            data TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_version INTEGER DEFAULT 1,
            status TEXT DEFAULT 'pending',
            checksum TEXT,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS device_registry (
            device_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            device_type TEXT NOT NULL,
            device_name TEXT,
            capabilities TEXT,
            last_sync TIMESTAMP,
            sync_version INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT TRUE,
            connection_state TEXT DEFAULT 'offline',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS conflict_resolution (
            id TEXT PRIMARY KEY,
            table_name TEXT NOT NULL,
            record_id TEXT NOT NULL,
            local_version TEXT NOT NULL,
            remote_version TEXT NOT NULL,
            resolution_strategy TEXT,
            resolved_data TEXT,
            resolver_device_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS sync_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_sync_log_status ON sync_log(status);
        CREATE INDEX IF NOT EXISTS idx_sync_log_timestamp ON sync_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_device_registry_user ON device_registry(user_id);
        """
        
        if hasattr(self.local_db, 'execute_script'):
            await self.local_db.execute_script(sync_schema)
        else:
            # Handle different database interfaces
            for statement in sync_schema.split(';'):
                if statement.strip():
                    await self.local_db.execute(statement)
    
    async def register_device(self, device_info: DeviceInfo):
        """Register current device in the sync system."""
        self.registered_devices[device_info.device_id] = device_info
        
        # Store in local database
        device_data = device_info.to_dict()
        device_data['capabilities'] = json.dumps(device_info.capabilities)
        
        await self.local_db.execute("""
            INSERT OR REPLACE INTO device_registry 
            (device_id, user_id, device_type, device_name, capabilities, 
             sync_version, is_active, connection_state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            device_info.device_id,
            device_info.user_id,
            device_info.device_type,
            device_info.device_name,
            json.dumps(device_info.capabilities),
            device_info.sync_version,
            device_info.is_active,
            device_info.connection_state
        ])
        
        # Sync to cloud if available
        if self.cloud_db and await self.is_online():
            await self._sync_device_registry()
        
        await self._trigger_callback('device_connected', device_info)
    
    async def track_change(self, table_name: str, record_id: str, 
                          operation: str, data: Dict, context: Optional[Dict] = None):
        """Track a data change for synchronization."""
        if not self.current_device:
            raise ValueError("Sync engine not initialized")
        
        sync_record = SyncRecord(
            id=str(uuid.uuid4()),
            user_id=self.current_device.user_id,
            device_id=self.current_device.device_id,
            table_name=table_name,
            record_id=record_id,
            operation=operation,
            data=data,
            timestamp=datetime.now(timezone.utc),
            sync_version=1
        )
        
        # Add to sync queue
        await self.add_to_sync_queue(sync_record)
        
        # Store in local sync log
        await self._store_sync_record(sync_record)
        
        # Trigger immediate sync if online and high priority
        priority_tables = ['conversations', 'user_preferences', 'ai_context']
        if table_name in priority_tables and await self.is_online():
            asyncio.create_task(self.sync_changes())
        
        logger.debug(f"Change tracked: {table_name}.{record_id} ({operation})")
    
    async def add_to_sync_queue(self, sync_record: SyncRecord):
        """Add a sync record to the queue for processing."""
        self.sync_queue.append(sync_record)
        
        # Limit queue size to prevent memory issues
        max_queue_size = 1000
        if len(self.sync_queue) > max_queue_size:
            # Remove oldest completed/failed records
            self.sync_queue = [
                r for r in self.sync_queue 
                if r.status in [SyncStatus.PENDING, SyncStatus.SYNCING]
            ][-max_queue_size:]
    
    async def sync_changes(self, force: bool = False):
        """Synchronize pending changes with remote systems."""
        if self.sync_running and not force:
            return
        
        if not await self.is_online():
            logger.debug("Sync skipped: offline")
            return
        
        self.sync_running = True
        await self._trigger_callback('sync_started', None)
        
        try:
            # Process sync queue
            pending_records = [r for r in self.sync_queue if r.status == SyncStatus.PENDING]
            
            for record in pending_records:
                try:
                    record.status = SyncStatus.SYNCING
                    await self._sync_record(record)
                    record.status = SyncStatus.COMPLETED
                    
                except Exception as e:
                    record.status = SyncStatus.FAILED
                    record.error_message = str(e)
                    record.retry_count += 1
                    
                    if record.retry_count >= self.max_retry_count:
                        logger.error(f"Sync record failed permanently: {record.id} - {e}")
                    else:
                        record.status = SyncStatus.PENDING  # Retry later
                    
                # Update sync log
                await self._update_sync_record(record)
            
            # Pull changes from cloud
            await self._pull_remote_changes()
            
            # Update device sync timestamp
            if self.current_device:
                self.current_device.last_sync = datetime.now(timezone.utc)
                await self._update_device_sync_time()
            
            await self._trigger_callback('sync_completed', None)
            logger.debug(f"Sync completed: {len(pending_records)} records processed")
            
        except Exception as e:
            await self._trigger_callback('sync_failed', str(e))
            logger.error(f"Sync failed: {e}")
            
        finally:
            self.sync_running = False
    
    async def _sync_record(self, record: SyncRecord):
        """Sync a single record to remote systems."""
        if not self.cloud_db:
            raise ValueError("Cloud database not configured")
        
        # Check for conflicts
        existing_record = await self._get_remote_record(record.table_name, record.record_id)
        if existing_record and existing_record.get('sync_version', 0) > record.sync_version:
            # Conflict detected
            await self._handle_conflict(record, existing_record)
            return
        
        # Apply encryption if configured
        sync_data = record.data.copy()
        if self.encryption_key:
            sync_data = await self._encrypt_data(sync_data)
        
        # Sync to cloud database
        cloud_record = {
            'id': record.record_id,
            'table_name': record.table_name,
            'data': sync_data,
            'sync_version': record.sync_version + 1,
            'last_modified': record.timestamp.isoformat(),
            'modified_by': record.device_id,
            'checksum': record.checksum
        }
        
        if record.operation == "DELETE":
            await self.cloud_db.delete_record(record.table_name, record.record_id)
        else:
            await self.cloud_db.upsert_record(record.table_name, cloud_record)
        
        # Sync vector embeddings if applicable
        if self.vector_db and record.table_name in ['conversations', 'ai_context']:
            await self._sync_vector_data(record)
    
    async def _handle_conflict(self, local_record: SyncRecord, remote_record: Dict):
        """Handle synchronization conflicts using configured strategy."""
        strategy = await self._get_conflict_strategy(local_record.table_name)
        resolver = self.conflict_resolvers.get(strategy)
        
        if not resolver:
            raise ValueError(f"Unknown conflict resolution strategy: {strategy}")
        
        try:
            resolved_data = await resolver(local_record.data, remote_record.get('data', {}))
            
            # Update local record with resolved data
            local_record.data = resolved_data
            local_record.sync_version = remote_record.get('sync_version', 0) + 1
            local_record.status = SyncStatus.COMPLETED
            
            # Store conflict resolution record
            await self._store_conflict_resolution(local_record, remote_record, strategy, resolved_data)
            
            await self._trigger_callback('conflict_detected', {
                'record': local_record,
                'strategy': strategy,
                'resolved': True
            })
            
            logger.info(f"Conflict resolved for {local_record.table_name}.{local_record.record_id} using {strategy}")
            
        except Exception as e:
            local_record.status = SyncStatus.CONFLICT
            local_record.error_message = f"Conflict resolution failed: {e}"
            
            await self._trigger_callback('conflict_detected', {
                'record': local_record,
                'strategy': strategy,
                'resolved': False,
                'error': str(e)
            })
            
            raise
    
    # Conflict resolution strategies
    async def _last_writer_wins(self, local_data: Dict, remote_data: Dict) -> Dict:
        """Simple last-writer-wins conflict resolution."""
        local_timestamp = local_data.get('timestamp', 0)
        remote_timestamp = remote_data.get('timestamp', 0)
        
        return local_data if local_timestamp >= remote_timestamp else remote_data
    
    async def _merge_conversation_data(self, local_data: Dict, remote_data: Dict) -> Dict:
        """Smart merging for conversation data."""
        merged = remote_data.copy()
        
        # Preserve local device-specific metadata
        if 'device_metadata' in local_data:
            merged['device_metadata'] = local_data['device_metadata']
        
        # Merge message arrays if both exist
        if 'messages' in local_data and 'messages' in remote_data:
            local_messages = {msg['id']: msg for msg in local_data.get('messages', [])}
            remote_messages = {msg['id']: msg for msg in remote_data.get('messages', [])}
            
            # Combine unique messages, sorted by timestamp
            all_messages = {**remote_messages, **local_messages}
            merged['messages'] = sorted(
                all_messages.values(),
                key=lambda x: x.get('timestamp', 0)
            )
        
        # Merge context data
        if 'context' in local_data and 'context' in remote_data:
            merged['context'] = {**remote_data.get('context', {}), **local_data.get('context', {})}
        
        # Update merged timestamp
        merged['timestamp'] = max(
            local_data.get('timestamp', 0),
            remote_data.get('timestamp', 0)
        )
        
        return merged
    
    async def _apply_user_preference(self, local_data: Dict, remote_data: Dict) -> Dict:
        """Apply user-defined conflict resolution preferences."""
        # This would query user preferences for conflict resolution
        # For now, fall back to last writer wins
        return await self._last_writer_wins(local_data, remote_data)
    
    async def _device_priority_resolution(self, local_data: Dict, remote_data: Dict) -> Dict:
        """Resolve conflicts based on device priority (desktop > mobile > watch > tv)."""
        device_priorities = {
            'desktop': 4,
            'mobile': 3,
            'watch': 2,
            'tv': 1,
            'car': 1
        }
        
        local_device = local_data.get('device_type', 'unknown')
        remote_device = remote_data.get('device_type', 'unknown')
        
        local_priority = device_priorities.get(local_device, 0)
        remote_priority = device_priorities.get(remote_device, 0)
        
        if local_priority >= remote_priority:
            return local_data
        else:
            return remote_data
    
    # Utility methods
    async def is_online(self) -> bool:
        """Check if the system is online and can sync."""
        if not self.cloud_db:
            return False
        
        try:
            # Simple connectivity check
            return await self.cloud_db.ping()
        except:
            return False
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status."""
        pending_count = len([r for r in self.sync_queue if r.status == SyncStatus.PENDING])
        syncing_count = len([r for r in self.sync_queue if r.status == SyncStatus.SYNCING])
        failed_count = len([r for r in self.sync_queue if r.status == SyncStatus.FAILED])
        
        return {
            'is_online': await self.is_online(),
            'sync_running': self.sync_running,
            'pending_records': pending_count,
            'syncing_records': syncing_count,
            'failed_records': failed_count,
            'last_sync': self.current_device.last_sync.isoformat() if self.current_device and self.current_device.last_sync else None,
            'registered_devices': len(self.registered_devices),
            'current_device': self.current_device.to_dict() if self.current_device else None
        }
    
    async def add_sync_callback(self, event: str, callback: Callable):
        """Add callback for sync events."""
        if event in self.sync_callbacks:
            self.sync_callbacks[event].append(callback)
    
    async def _trigger_callback(self, event: str, data: Any):
        """Trigger registered callbacks for sync events."""
        for callback in self.sync_callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Sync callback error: {e}")
    
    async def start_background_sync(self):
        """Start background sync task."""
        async def sync_loop():
            while True:
                try:
                    await asyncio.sleep(self.sync_interval)
                    if not self.sync_running:
                        await self.sync_changes()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Background sync error: {e}")
        
        asyncio.create_task(sync_loop())
    
    # Private helper methods
    async def _store_sync_record(self, record: SyncRecord):
        """Store sync record in local database."""
        await self.local_db.execute("""
            INSERT INTO sync_log 
            (id, user_id, device_id, table_name, record_id, operation, 
             data, timestamp, sync_version, status, checksum, retry_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            record.id, record.user_id, record.device_id, record.table_name,
            record.record_id, record.operation, json.dumps(record.data),
            record.timestamp, record.sync_version, record.status.value,
            record.checksum, record.retry_count
        ])
    
    async def _update_sync_record(self, record: SyncRecord):
        """Update existing sync record."""
        await self.local_db.execute("""
            UPDATE sync_log 
            SET status = ?, error_message = ?, retry_count = ?
            WHERE id = ?
        """, [record.status.value, record.error_message, record.retry_count, record.id])
    
    async def _get_remote_record(self, table_name: str, record_id: str) -> Optional[Dict]:
        """Get record from remote database."""
        if not self.cloud_db:
            return None
        return await self.cloud_db.get_record(table_name, record_id)
    
    async def _pull_remote_changes(self):
        """Pull changes from remote systems."""
        if not self.cloud_db or not self.current_device:
            return
        
        last_sync = self.current_device.last_sync or datetime.min.replace(tzinfo=timezone.utc)
        remote_changes = await self.cloud_db.get_changes_since(last_sync)
        
        for change in remote_changes:
            await self._apply_remote_change(change)
    
    async def _apply_remote_change(self, change: Dict):
        """Apply a remote change to local database."""
        # Implementation would depend on your local database structure
        pass
    
    async def _get_conflict_strategy(self, table_name: str) -> str:
        """Get conflict resolution strategy for table."""
        strategy_map = {
            'conversations': ConflictResolutionStrategy.MERGE_CONVERSATION.value,
            'user_preferences': ConflictResolutionStrategy.DEVICE_PRIORITY.value,
            'ai_context': ConflictResolutionStrategy.MERGE_CONVERSATION.value,
            'default': ConflictResolutionStrategy.LAST_WRITER_WINS.value
        }
        return strategy_map.get(table_name, strategy_map['default'])
    
    async def _store_conflict_resolution(self, local_record: SyncRecord, remote_record: Dict, 
                                       strategy: str, resolved_data: Dict):
        """Store conflict resolution record for audit."""
        await self.local_db.execute("""
            INSERT INTO conflict_resolution 
            (id, table_name, record_id, local_version, remote_version, 
             resolution_strategy, resolved_data, resolver_device_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(uuid.uuid4()), local_record.table_name, local_record.record_id,
            json.dumps(local_record.data), json.dumps(remote_record),
            strategy, json.dumps(resolved_data), self.current_device.device_id
        ])
    
    async def _sync_device_registry(self):
        """Sync device registry with cloud."""
        if self.cloud_db and self.current_device:
            await self.cloud_db.upsert_record('device_registry', self.current_device.to_dict())
    
    async def _update_device_sync_time(self):
        """Update device last sync time."""
        if self.current_device:
            await self.local_db.execute("""
                UPDATE device_registry 
                SET last_sync = ? 
                WHERE device_id = ?
            """, [self.current_device.last_sync, self.current_device.device_id])
    
    async def _sync_vector_data(self, record: SyncRecord):
        """Sync vector embeddings for AI context."""
        if not self.vector_db:
            return
        
        # Extract text content for embedding
        text_content = self._extract_text_content(record.data)
        if text_content:
            await self.vector_db.upsert_embedding(
                record.record_id,
                text_content,
                metadata={
                    'table_name': record.table_name,
                    'device_id': record.device_id,
                    'timestamp': record.timestamp.isoformat()
                }
            )
    
    def _extract_text_content(self, data: Dict) -> Optional[str]:
        """Extract text content from data for vector embedding."""
        if 'content' in data:
            return data['content']
        elif 'message' in data:
            return data['message']
        elif 'text' in data:
            return data['text']
        return None
    
    async def _encrypt_data(self, data: Dict) -> Dict:
        """Encrypt sensitive data before cloud sync."""
        # Placeholder for encryption implementation
        return data
    
    async def _decrypt_data(self, data: Dict) -> Dict:
        """Decrypt data received from cloud."""
        # Placeholder for decryption implementation
        return data
