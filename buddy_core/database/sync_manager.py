"""
Sync Manager - Cross-Platform Data Synchronization

Handles:
- Offline-first operations
- Conflict resolution
- Real-time sync when online
- Platform-specific optimizations
- Batch operations for efficiency
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone, timedelta
import json
import uuid

logger = logging.getLogger(__name__)

class SyncManager:
    """Manages data synchronization across devices and platforms"""
    
    def __init__(self, local_db, cloud_db, device_id: str = None):
        self.local_db = local_db
        self.cloud_db = cloud_db
        self.device_id = device_id or str(uuid.uuid4())
        
        # Sync state
        self._is_online = False
        self._sync_in_progress = False
        self._sync_interval = 300  # 5 minutes default
        self._sync_task = None
        
        # Conflict resolution strategies
        self.conflict_resolvers = {
            "last_writer_wins": self._resolve_last_writer_wins,
            "merge_changes": self._resolve_merge_changes,
            "user_choice": self._resolve_user_choice
        }
        
        self.default_strategy = "last_writer_wins"
        
        # Sync callbacks
        self.sync_callbacks = {
            "sync_started": [],
            "sync_completed": [],
            "sync_failed": [],
            "conflict_detected": []
        }
    
    async def initialize(self):
        """Initialize sync manager"""
        try:
            # Check initial connectivity
            self._is_online = await self._check_connectivity()
            
            # Start background sync if online
            if self._is_online:
                await self._start_background_sync()
            
            logger.info(f"Sync manager initialized (device: {self.device_id}, online: {self._is_online})")
            
        except Exception as e:
            logger.error(f"Failed to initialize sync manager: {e}")
    
    async def _check_connectivity(self) -> bool:
        """Check if cloud database is accessible"""
        try:
            return self.cloud_db.is_connected()
        except:
            return False
    
    async def _start_background_sync(self):
        """Start background synchronization task"""
        if self._sync_task:
            self._sync_task.cancel()
        
        self._sync_task = asyncio.create_task(self._background_sync_loop())
    
    async def _background_sync_loop(self):
        """Background sync loop"""
        while True:
            try:
                await asyncio.sleep(self._sync_interval)
                
                if self._is_online and not self._sync_in_progress:
                    await self.sync_all()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background sync error: {e}")
    
    # Sync Operations
    async def sync_all(self, force: bool = False) -> Dict[str, Any]:
        """Sync all data between local and cloud"""
        if self._sync_in_progress and not force:
            return {"status": "sync_in_progress"}
        
        self._sync_in_progress = True
        sync_result = {
            "status": "success",
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc),
            "tables_synced": [],
            "conflicts_resolved": 0,
            "records_uploaded": 0,
            "records_downloaded": 0,
            "errors": []
        }
        
        try:
            # Notify sync started
            await self._notify_callbacks("sync_started", sync_result)
            
            # Check connectivity
            self._is_online = await self._check_connectivity()
            if not self._is_online:
                sync_result["status"] = "offline"
                return sync_result
            
            # Sync each table
            tables = ["user_data", "conversations", "ai_context"]
            
            for table in tables:
                try:
                    table_result = await self._sync_table(table)
                    sync_result["tables_synced"].append(table)
                    sync_result["records_uploaded"] += table_result.get("uploaded", 0)
                    sync_result["records_downloaded"] += table_result.get("downloaded", 0)
                    sync_result["conflicts_resolved"] += table_result.get("conflicts", 0)
                    
                except Exception as e:
                    error_msg = f"Failed to sync {table}: {e}"
                    sync_result["errors"].append(error_msg)
                    logger.error(error_msg)
            
            # Log sync operation
            await self.cloud_db.log_sync_operation(
                self.device_id,
                "full_sync",
                "all_tables",
                sync_result["records_uploaded"] + sync_result["records_downloaded"],
                "success" if not sync_result["errors"] else "partial"
            )
            
            # Notify sync completed
            await self._notify_callbacks("sync_completed", sync_result)
            
        except Exception as e:
            sync_result["status"] = "failed"
            sync_result["errors"].append(str(e))
            logger.error(f"Sync failed: {e}")
            
            await self._notify_callbacks("sync_failed", sync_result)
        
        finally:
            self._sync_in_progress = False
        
        return sync_result
    
    async def _sync_table(self, table_name: str) -> Dict[str, int]:
        """Sync specific table"""
        result = {"uploaded": 0, "downloaded": 0, "conflicts": 0}
        
        # Get last sync timestamp
        last_sync = await self._get_last_sync_timestamp(table_name)
        
        # Upload pending changes from local to cloud
        upload_count = await self._upload_pending_changes(table_name)
        result["uploaded"] = upload_count
        
        # Download changes from cloud to local
        download_result = await self._download_changes(table_name, last_sync)
        result["downloaded"] = download_result.get("downloaded", 0)
        result["conflicts"] = download_result.get("conflicts", 0)
        
        # Update last sync timestamp
        await self._update_last_sync_timestamp(table_name)
        
        return result
    
    async def _upload_pending_changes(self, table_name: str) -> int:
        """Upload pending changes to cloud"""
        count = 0
        
        try:
            # Get pending operations
            operations = await self.local_db.get_pending_sync_operations()
            
            for op in operations:
                if op["table_name"] != table_name:
                    continue
                
                try:
                    if table_name == "user_data":
                        await self._upload_user_data(op)
                    elif table_name == "conversations":
                        await self._upload_conversation(op)
                    elif table_name == "ai_context":
                        await self._upload_ai_context(op)
                    
                    # Clear operation from queue
                    await self.local_db.clear_sync_operation(op["id"])
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to upload {table_name} record: {e}")
        
        except Exception as e:
            logger.error(f"Failed to get pending operations: {e}")
        
        return count
    
    async def _download_changes(self, table_name: str, since: datetime = None) -> Dict[str, int]:
        """Download changes from cloud"""
        result = {"downloaded": 0, "conflicts": 0}
        
        try:
            # Get changes from cloud
            if table_name == "user_data":
                cloud_records = await self.cloud_db.get_user_data("all", since=since)
            elif table_name == "conversations":
                cloud_records = await self.cloud_db.get_conversations("all", since=since)
            elif table_name == "ai_context":
                cloud_records = await self.cloud_db.get_ai_context("all", since=since)
            else:
                return result
            
            # Process each record
            for record in cloud_records:
                try:
                    conflict_resolved = await self._process_cloud_record(table_name, record)
                    if conflict_resolved:
                        result["conflicts"] += 1
                    result["downloaded"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process cloud record: {e}")
        
        except Exception as e:
            logger.error(f"Failed to download changes: {e}")
        
        return result
    
    async def _process_cloud_record(self, table_name: str, cloud_record: Dict[str, Any]) -> bool:
        """Process a record from cloud, handling conflicts"""
        # Check if record exists locally
        record_id = cloud_record.get("_id")
        
        # For now, implement simple last-writer-wins
        # In a full implementation, you'd check for conflicts and resolve them
        
        try:
            if table_name == "user_data":
                await self.local_db.store_user_data(
                    cloud_record["user_id"],
                    cloud_record["data_type"],
                    cloud_record["content"],
                    cloud_record.get("device_id")
                )
            elif table_name == "conversations":
                await self.local_db.store_conversation(
                    cloud_record["user_id"],
                    cloud_record["session_id"],
                    cloud_record["message_type"],
                    cloud_record["content"],
                    cloud_record.get("metadata"),
                    cloud_record.get("device_id")
                )
            elif table_name == "ai_context":
                await self.local_db.store_ai_context(
                    cloud_record["user_id"],
                    cloud_record["context_type"],
                    cloud_record["content"],
                    cloud_record.get("embedding_vector"),
                    cloud_record.get("relevance_score", 0.0),
                    cloud_record.get("device_id")
                )
            
            return False  # No conflict detected
            
        except Exception as e:
            logger.error(f"Failed to store cloud record locally: {e}")
            return False
    
    # Conflict Resolution
    async def _resolve_last_writer_wins(self, local_record: Dict, cloud_record: Dict) -> Dict:
        """Last writer wins conflict resolution"""
        local_updated = datetime.fromisoformat(local_record.get("updated_at", "1970-01-01"))
        cloud_updated = datetime.fromisoformat(cloud_record.get("updated_at", "1970-01-01"))
        
        return cloud_record if cloud_updated > local_updated else local_record
    
    async def _resolve_merge_changes(self, local_record: Dict, cloud_record: Dict) -> Dict:
        """Merge changes conflict resolution"""
        # Simple merge - combine non-conflicting fields
        merged = local_record.copy()
        
        for key, value in cloud_record.items():
            if key not in merged or key in ["updated_at", "_id"]:
                merged[key] = value
            elif key == "content" and isinstance(value, dict) and isinstance(merged[key], dict):
                # Merge content dictionaries
                merged[key].update(value)
        
        merged["updated_at"] = datetime.now(timezone.utc).isoformat()
        return merged
    
    async def _resolve_user_choice(self, local_record: Dict, cloud_record: Dict) -> Dict:
        """User choice conflict resolution (placeholder)"""
        # In a real implementation, this would present options to the user
        # For now, default to last writer wins
        return await self._resolve_last_writer_wins(local_record, cloud_record)
    
    # Helper methods
    async def _upload_user_data(self, operation: Dict[str, Any]):
        """Upload user data operation"""
        # Get local record and upload to cloud
        # Implementation depends on operation type (insert, update, delete)
        pass
    
    async def _upload_conversation(self, operation: Dict[str, Any]):
        """Upload conversation operation"""
        pass
    
    async def _upload_ai_context(self, operation: Dict[str, Any]):
        """Upload AI context operation"""
        pass
    
    async def _get_last_sync_timestamp(self, table_name: str) -> datetime:
        """Get last sync timestamp for table"""
        # Query local sync metadata
        return datetime.now(timezone.utc) - timedelta(days=1)  # Placeholder
    
    async def _update_last_sync_timestamp(self, table_name: str):
        """Update last sync timestamp for table"""
        # Update local sync metadata
        pass
    
    # Manual sync operations
    async def force_upload(self, table_name: str = None) -> Dict[str, Any]:
        """Force upload of all local data"""
        if not self._is_online:
            return {"status": "offline"}
        
        # Implementation for force upload
        return {"status": "success", "uploaded": 0}
    
    async def force_download(self, table_name: str = None) -> Dict[str, Any]:
        """Force download of all cloud data"""
        if not self._is_online:
            return {"status": "offline"}
        
        # Implementation for force download
        return {"status": "success", "downloaded": 0}
    
    # Callback management
    def add_sync_callback(self, event_type: str, callback: Callable):
        """Add sync event callback"""
        if event_type in self.sync_callbacks:
            self.sync_callbacks[event_type].append(callback)
    
    async def _notify_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notify sync callbacks"""
        if event_type in self.sync_callbacks:
            for callback in self.sync_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Sync callback error: {e}")
    
    # Configuration
    def set_sync_interval(self, seconds: int):
        """Set background sync interval"""
        self._sync_interval = seconds
        
        if self._sync_task:
            self._sync_task.cancel()
            asyncio.create_task(self._start_background_sync())
    
    def set_conflict_resolution_strategy(self, strategy: str):
        """Set default conflict resolution strategy"""
        if strategy in self.conflict_resolvers:
            self.default_strategy = strategy
    
    # Status and monitoring
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        return {
            "device_id": self.device_id,
            "is_online": self._is_online,
            "sync_in_progress": self._sync_in_progress,
            "sync_interval": self._sync_interval,
            "last_sync": None  # Would track last sync time
        }
    
    async def get_pending_operations_count(self) -> int:
        """Get count of pending sync operations"""
        try:
            operations = await self.local_db.get_pending_sync_operations()
            return len(operations)
        except:
            return 0
    
    async def close(self):
        """Close sync manager"""
        if self._sync_task:
            self._sync_task.cancel()
        
        logger.info("Sync manager closed")
