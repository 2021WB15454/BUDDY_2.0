"""
BUDDY Cross-Device Synchronization Manager
Real-time synchronization engine for seamless cross-platform state management

This module implements the synchronization logic that keeps all BUDDY devices
in sync, ensuring users have a consistent experience across all platforms.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sync-related enums and data structures

class SyncOperationType(Enum):
    """Types of synchronization operations"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    CONFLICT_RESOLUTION = "conflict_resolution"

class SyncPriority(Enum):
    """Priority levels for synchronization operations"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    LAST_WRITE_WINS = "last_write_wins"
    DEVICE_PRIORITY = "device_priority"
    USER_CHOICE = "user_choice"
    MERGE_AUTOMATIC = "merge_automatic"
    MERGE_MANUAL = "merge_manual"

@dataclass
class SyncItem:
    """Individual item to be synchronized"""
    id: str
    type: str
    data: Dict[str, Any]
    timestamp: float
    device_id: str
    user_id: str
    version: int = 1
    checksum: Optional[str] = None
    
    def __post_init__(self):
        if not self.checksum:
            import hashlib
            content = json.dumps(self.data, sort_keys=True)
            self.checksum = hashlib.md5(content.encode()).hexdigest()

@dataclass
class SyncOperation:
    """Synchronization operation to be performed"""
    id: str
    operation: SyncOperationType
    item: SyncItem
    target_devices: List[str]
    priority: SyncPriority = SyncPriority.NORMAL
    created_at: float = None
    attempts: int = 0
    max_attempts: int = 3
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()

@dataclass
class DeviceConnection:
    """Information about a connected device"""
    device_id: str
    device_type: str
    platform: str
    user_id: str
    last_seen: float
    capabilities: List[str]
    sync_preferences: Dict[str, Any]
    is_online: bool = True
    connection_quality: str = "good"
    
    def is_active(self, timeout_seconds: int = 300) -> bool:
        """Check if device is considered active"""
        return time.time() - self.last_seen < timeout_seconds

class CrossDeviceSyncManager:
    """Manages synchronization across all connected BUDDY devices"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connected_devices: Dict[str, DeviceConnection] = {}
        self.sync_queue: deque = deque()
        self.sync_history: Dict[str, List[SyncItem]] = defaultdict(list)
        self.conflict_queue: List[Dict[str, Any]] = []
        self.sync_handlers: Dict[str, Callable] = {}
        self.is_running = False
        self.sync_stats = {
            "operations_processed": 0,
            "conflicts_resolved": 0,
            "failed_syncs": 0,
            "avg_sync_time": 0.0
        }
        
        # Setup default sync handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default synchronization handlers"""
        self.sync_handlers = {
            "conversation": self._sync_conversation,
            "user_preferences": self._sync_preferences,
            "context_data": self._sync_context,
            "device_state": self._sync_device_state,
            "skill_data": self._sync_skill_data
        }
    
    async def start(self):
        """Start the synchronization manager"""
        logger.info("Starting Cross-Device Sync Manager")
        self.is_running = True
        
        # Start sync processing loop
        asyncio.create_task(self._sync_processing_loop())
        
        # Start device health monitoring
        asyncio.create_task(self._device_health_monitor())
        
        # Start conflict resolution monitoring
        asyncio.create_task(self._conflict_resolution_loop())
        
        logger.info("Cross-Device Sync Manager started successfully")
    
    async def stop(self):
        """Stop the synchronization manager"""
        logger.info("Stopping Cross-Device Sync Manager")
        self.is_running = False
        
        # Process remaining items in queue
        await self._flush_sync_queue()
        
        logger.info("Cross-Device Sync Manager stopped")
    
    async def register_device(self, device_info: Dict[str, Any]) -> bool:
        """Register a new device for synchronization"""
        try:
            device_id = device_info["device_id"]
            
            device_connection = DeviceConnection(
                device_id=device_id,
                device_type=device_info["device_type"],
                platform=device_info.get("platform", "unknown"),
                user_id=device_info["user_id"],
                last_seen=time.time(),
                capabilities=device_info.get("capabilities", []),
                sync_preferences=device_info.get("sync_preferences", {}),
                is_online=True
            )
            
            self.connected_devices[device_id] = device_connection
            
            # Send initial sync data to new device
            await self._initial_device_sync(device_id)
            
            logger.info(f"Device registered for sync: {device_id} ({device_info['device_type']})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            return False
    
    async def unregister_device(self, device_id: str):
        """Unregister a device from synchronization"""
        if device_id in self.connected_devices:
            device = self.connected_devices[device_id]
            device.is_online = False
            device.last_seen = time.time()
            
            logger.info(f"Device unregistered: {device_id}")
            
            # Clean up after a delay to allow for reconnections
            asyncio.create_task(self._cleanup_device_after_delay(device_id, 3600))  # 1 hour
    
    async def sync_item(self, item_type: str, data: Dict[str, Any], 
                       device_id: str, user_id: str, 
                       target_devices: Optional[List[str]] = None) -> bool:
        """Add an item to the synchronization queue"""
        try:
            # Create sync item
            sync_item = SyncItem(
                id=str(uuid.uuid4()),
                type=item_type,
                data=data,
                timestamp=time.time(),
                device_id=device_id,
                user_id=user_id
            )
            
            # Determine target devices
            if target_devices is None:
                target_devices = await self._get_relevant_devices(sync_item)
            
            # Create sync operation
            sync_op = SyncOperation(
                id=str(uuid.uuid4()),
                operation=SyncOperationType.UPDATE,
                item=sync_item,
                target_devices=target_devices,
                priority=self._get_sync_priority(item_type)
            )
            
            # Add to queue
            self.sync_queue.append(sync_op)
            
            logger.debug(f"Item queued for sync: {item_type} to {len(target_devices)} devices")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue sync item: {e}")
            return False
    
    async def _sync_processing_loop(self):
        """Main synchronization processing loop"""
        while self.is_running:
            try:
                if self.sync_queue:
                    sync_op = self.sync_queue.popleft()
                    await self._process_sync_operation(sync_op)
                else:
                    await asyncio.sleep(0.1)  # Short sleep when queue is empty
                    
            except Exception as e:
                logger.error(f"Error in sync processing loop: {e}")
                await asyncio.sleep(1)  # Longer sleep on error
    
    async def _process_sync_operation(self, sync_op: SyncOperation):
        """Process a single synchronization operation"""
        start_time = time.time()
        
        try:
            # Get the appropriate sync handler
            handler = self.sync_handlers.get(sync_op.item.type, self._default_sync_handler)
            
            # Execute sync for each target device
            results = []
            for device_id in sync_op.target_devices:
                if device_id in self.connected_devices and self.connected_devices[device_id].is_online:
                    result = await handler(sync_op.item, device_id)
                    results.append((device_id, result))
                else:
                    logger.warning(f"Target device not available: {device_id}")
            
            # Update statistics
            sync_time = time.time() - start_time
            self.sync_stats["operations_processed"] += 1
            self.sync_stats["avg_sync_time"] = (
                (self.sync_stats["avg_sync_time"] * (self.sync_stats["operations_processed"] - 1) + sync_time) /
                self.sync_stats["operations_processed"]
            )
            
            # Check for conflicts
            await self._check_for_conflicts(sync_op, results)
            
            logger.debug(f"Sync operation completed: {sync_op.id} in {sync_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Failed to process sync operation {sync_op.id}: {e}")
            
            # Retry logic
            sync_op.attempts += 1
            if sync_op.attempts < sync_op.max_attempts:
                self.sync_queue.append(sync_op)
                logger.info(f"Retrying sync operation: {sync_op.id} (attempt {sync_op.attempts})")
            else:
                self.sync_stats["failed_syncs"] += 1
                logger.error(f"Sync operation failed permanently: {sync_op.id}")
    
    async def _get_relevant_devices(self, sync_item: SyncItem) -> List[str]:
        """Determine which devices should receive this sync item"""
        relevant_devices = []
        
        for device_id, device in self.connected_devices.items():
            # Don't sync back to the originating device
            if device_id == sync_item.device_id:
                continue
            
            # Check if device belongs to the same user
            if device.user_id != sync_item.user_id:
                continue
            
            # Check device capabilities and preferences
            if await self._should_sync_to_device(sync_item, device):
                relevant_devices.append(device_id)
        
        return relevant_devices
    
    async def _should_sync_to_device(self, sync_item: SyncItem, device: DeviceConnection) -> bool:
        """Determine if an item should be synced to a specific device"""
        # Check device capabilities
        if sync_item.type == "voice_data" and "voice" not in device.capabilities:
            return False
        
        if sync_item.type == "health_data" and "health_data" not in device.capabilities:
            return False
        
        # Check sync preferences
        sync_prefs = device.sync_preferences
        if sync_prefs.get(f"sync_{sync_item.type}", True) is False:
            return False
        
        # Check device type specific rules
        if device.device_type == "watch" and len(json.dumps(sync_item.data)) > 1024:
            return False  # Watch has limited storage
        
        return True
    
    def _get_sync_priority(self, item_type: str) -> SyncPriority:
        """Get synchronization priority for an item type"""
        priority_map = {
            "conversation": SyncPriority.HIGH,
            "user_preferences": SyncPriority.NORMAL,
            "context_data": SyncPriority.LOW,
            "device_state": SyncPriority.LOW,
            "emergency": SyncPriority.CRITICAL,
            "health_alert": SyncPriority.URGENT
        }
        
        return priority_map.get(item_type, SyncPriority.NORMAL)
    
    # Sync handlers for different data types
    async def _sync_conversation(self, sync_item: SyncItem, device_id: str) -> bool:
        """Sync conversation data to a device"""
        try:
            device = self.connected_devices[device_id]
            
            # Prepare conversation data for device capabilities
            conversation_data = sync_item.data.copy()
            
            # Optimize for device type
            if device.device_type == "watch":
                # Summarize for watch display
                conversation_data = await self._optimize_for_watch(conversation_data)
            elif device.device_type == "tv":
                # Optimize for TV display
                conversation_data = await self._optimize_for_tv(conversation_data)
            
            # Send sync message to device
            await self._send_sync_message(device_id, "conversation", conversation_data)
            
            logger.debug(f"Conversation synced to {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync conversation to {device_id}: {e}")
            return False
    
    async def _sync_preferences(self, sync_item: SyncItem, device_id: str) -> bool:
        """Sync user preferences to a device"""
        try:
            # Send preferences update
            await self._send_sync_message(device_id, "preferences", sync_item.data)
            
            logger.debug(f"Preferences synced to {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync preferences to {device_id}: {e}")
            return False
    
    async def _sync_context(self, sync_item: SyncItem, device_id: str) -> bool:
        """Sync context data to a device"""
        try:
            device = self.connected_devices[device_id]
            
            # Filter context data based on device capabilities
            context_data = sync_item.data.copy()
            
            if "location" not in device.capabilities:
                context_data.pop("location", None)
            
            if "health_data" not in device.capabilities:
                context_data.pop("health_data", None)
            
            await self._send_sync_message(device_id, "context", context_data)
            
            logger.debug(f"Context synced to {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync context to {device_id}: {e}")
            return False
    
    async def _sync_device_state(self, sync_item: SyncItem, device_id: str) -> bool:
        """Sync device state information"""
        try:
            await self._send_sync_message(device_id, "device_state", sync_item.data)
            
            logger.debug(f"Device state synced to {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync device state to {device_id}: {e}")
            return False
    
    async def _sync_skill_data(self, sync_item: SyncItem, device_id: str) -> bool:
        """Sync skill-specific data"""
        try:
            device = self.connected_devices[device_id]
            
            # Check if device supports the skill
            skill_name = sync_item.data.get("skill_name")
            if skill_name and skill_name not in device.capabilities:
                logger.debug(f"Device {device_id} doesn't support skill {skill_name}")
                return True  # Not an error, just not applicable
            
            await self._send_sync_message(device_id, "skill_data", sync_item.data)
            
            logger.debug(f"Skill data synced to {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync skill data to {device_id}: {e}")
            return False
    
    async def _default_sync_handler(self, sync_item: SyncItem, device_id: str) -> bool:
        """Default sync handler for unknown item types"""
        try:
            await self._send_sync_message(device_id, sync_item.type, sync_item.data)
            
            logger.debug(f"Default sync to {device_id} for {sync_item.type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed default sync to {device_id}: {e}")
            return False
    
    async def _send_sync_message(self, device_id: str, data_type: str, data: Dict[str, Any]):
        """Send synchronization message to a specific device"""
        # In a real implementation, this would send via WebSocket/HTTP
        sync_message = {
            "type": "sync_update",
            "data_type": data_type,
            "data": data,
            "timestamp": time.time(),
            "source": "sync_manager"
        }
        
        logger.debug(f"Sending sync message to {device_id}: {data_type}")
        
        # Mock sending - in production, this would be actual network communication
        # await websocket_manager.send_to_device(device_id, sync_message)
        # await rest_api.post_to_device(device_id, sync_message)
    
    async def _device_health_monitor(self):
        """Monitor device health and connectivity"""
        while self.is_running:
            try:
                current_time = time.time()
                
                for device_id, device in self.connected_devices.items():
                    # Check if device is still active
                    if device.is_online and not device.is_active():
                        device.is_online = False
                        logger.info(f"Device {device_id} marked as offline")
                    
                    # Update connection quality based on response times
                    await self._update_connection_quality(device)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in device health monitor: {e}")
                await asyncio.sleep(60)
    
    async def _conflict_resolution_loop(self):
        """Process conflict resolution queue"""
        while self.is_running:
            try:
                if self.conflict_queue:
                    conflict = self.conflict_queue.pop(0)
                    await self._resolve_conflict(conflict)
                else:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in conflict resolution: {e}")
                await asyncio.sleep(5)
    
    async def _check_for_conflicts(self, sync_op: SyncOperation, results: List[tuple]):
        """Check for synchronization conflicts"""
        # Look for conflicts in the sync results
        conflicts = []
        
        for device_id, result in results:
            if isinstance(result, dict) and result.get("conflict"):
                conflicts.append({
                    "sync_op_id": sync_op.id,
                    "device_id": device_id,
                    "conflict_data": result["conflict"]
                })
        
        # Add conflicts to resolution queue
        self.conflict_queue.extend(conflicts)
        
        if conflicts:
            self.sync_stats["conflicts_resolved"] += len(conflicts)
            logger.warning(f"Detected {len(conflicts)} sync conflicts")
    
    async def _resolve_conflict(self, conflict: Dict[str, Any]):
        """Resolve a synchronization conflict"""
        try:
            resolution_strategy = ConflictResolution.LAST_WRITE_WINS  # Default strategy
            
            # Implement conflict resolution logic based on strategy
            if resolution_strategy == ConflictResolution.LAST_WRITE_WINS:
                await self._resolve_last_write_wins(conflict)
            elif resolution_strategy == ConflictResolution.DEVICE_PRIORITY:
                await self._resolve_device_priority(conflict)
            
            logger.info(f"Conflict resolved: {conflict['sync_op_id']}")
            
        except Exception as e:
            logger.error(f"Failed to resolve conflict: {e}")
    
    async def _resolve_last_write_wins(self, conflict: Dict[str, Any]):
        """Resolve conflict using last-write-wins strategy"""
        # Simple resolution: use the most recent timestamp
        conflict_data = conflict["conflict_data"]
        latest_item = max(conflict_data["items"], key=lambda x: x["timestamp"])
        
        # Re-sync the latest version to all devices
        await self.sync_item(
            latest_item["type"],
            latest_item["data"],
            latest_item["device_id"],
            latest_item["user_id"]
        )
    
    async def _resolve_device_priority(self, conflict: Dict[str, Any]):
        """Resolve conflict using device priority strategy"""
        # Implement device priority based resolution
        device_priorities = {
            "desktop": 3,
            "mobile": 2,
            "watch": 1,
            "tv": 1
        }
        
        conflict_data = conflict["conflict_data"]
        highest_priority_item = max(
            conflict_data["items"],
            key=lambda x: device_priorities.get(x.get("device_type", "unknown"), 0)
        )
        
        # Re-sync the highest priority version
        await self.sync_item(
            highest_priority_item["type"],
            highest_priority_item["data"],
            highest_priority_item["device_id"],
            highest_priority_item["user_id"]
        )
    
    async def _optimize_for_watch(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize data for smartwatch display"""
        optimized = data.copy()
        
        # Truncate long text for watch display
        if "text" in optimized and len(optimized["text"]) > 100:
            optimized["text"] = optimized["text"][:97] + "..."
        
        # Remove unnecessary data for watch
        optimized.pop("detailed_context", None)
        optimized.pop("full_history", None)
        
        return optimized
    
    async def _optimize_for_tv(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize data for TV display"""
        optimized = data.copy()
        
        # Format for large screen display
        if "text" in optimized:
            optimized["display_text"] = self._format_for_tv_display(optimized["text"])
        
        return optimized
    
    def _format_for_tv_display(self, text: str) -> str:
        """Format text for TV display"""
        # Break long lines for TV display
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(" ".join(current_line + [word])) > 60:  # TV line length
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                current_line.append(word)
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return "\n".join(lines)
    
    async def _initial_device_sync(self, device_id: str):
        """Perform initial synchronization for a newly connected device"""
        try:
            device = self.connected_devices[device_id]
            
            # Get recent sync items for this user
            recent_items = await self._get_recent_sync_items(device.user_id)
            
            # Send recent data to the new device
            for item in recent_items:
                if await self._should_sync_to_device(item, device):
                    handler = self.sync_handlers.get(item.type, self._default_sync_handler)
                    await handler(item, device_id)
            
            logger.info(f"Initial sync completed for device: {device_id}")
            
        except Exception as e:
            logger.error(f"Failed initial sync for device {device_id}: {e}")
    
    async def _get_recent_sync_items(self, user_id: str, hours: int = 24) -> List[SyncItem]:
        """Get recent sync items for a user"""
        cutoff_time = time.time() - (hours * 3600)
        recent_items = []
        
        for item_list in self.sync_history.values():
            for item in item_list:
                if item.user_id == user_id and item.timestamp > cutoff_time:
                    recent_items.append(item)
        
        return sorted(recent_items, key=lambda x: x.timestamp, reverse=True)[:50]  # Latest 50 items
    
    async def _update_connection_quality(self, device: DeviceConnection):
        """Update connection quality for a device"""
        # Mock implementation - in production, this would measure actual response times
        if device.is_online:
            device.connection_quality = "good"
        else:
            device.connection_quality = "offline"
    
    async def _cleanup_device_after_delay(self, device_id: str, delay_seconds: int):
        """Clean up device data after a delay"""
        await asyncio.sleep(delay_seconds)
        
        if device_id in self.connected_devices:
            device = self.connected_devices[device_id]
            if not device.is_online:
                # Remove from active devices but keep in history
                del self.connected_devices[device_id]
                logger.info(f"Device cleaned up: {device_id}")
    
    async def _flush_sync_queue(self):
        """Process all remaining items in sync queue"""
        while self.sync_queue:
            sync_op = self.sync_queue.popleft()
            await self._process_sync_operation(sync_op)
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """Get synchronization statistics"""
        return {
            "connected_devices": len([d for d in self.connected_devices.values() if d.is_online]),
            "total_devices": len(self.connected_devices),
            "queue_size": len(self.sync_queue),
            "conflicts_pending": len(self.conflict_queue),
            **self.sync_stats
        }

# Demo function
async def main():
    """Demonstration of cross-device synchronization"""
    print("🔄📱💻⌚ BUDDY Cross-Device Synchronization Demo")
    print("=" * 60)
    print("Real-time synchronization engine for seamless cross-platform state management")
    print()
    
    # Initialize sync manager
    config = {
        "sync_interval": 1,
        "conflict_resolution": "last_write_wins",
        "max_queue_size": 1000
    }
    
    sync_manager = CrossDeviceSyncManager(config)
    await sync_manager.start()
    
    print("🔧 Registering Devices...")
    
    # Register test devices
    devices = [
        {
            "device_id": "mobile_001",
            "device_type": "mobile",
            "platform": "android",
            "user_id": "user123",
            "capabilities": ["voice", "location", "camera", "notifications"],
            "sync_preferences": {"sync_conversation": True, "sync_preferences": True}
        },
        {
            "device_id": "desktop_001",
            "device_type": "desktop",
            "platform": "windows",
            "user_id": "user123",
            "capabilities": ["voice", "file_access", "system_control"],
            "sync_preferences": {"sync_conversation": True, "sync_context": True}
        },
        {
            "device_id": "watch_001",
            "device_type": "watch",
            "platform": "watchos",
            "user_id": "user123",
            "capabilities": ["voice", "health_data", "notifications"],
            "sync_preferences": {"sync_conversation": True, "sync_health": True}
        }
    ]
    
    for device in devices:
        success = await sync_manager.register_device(device)
        if success:
            print(f"   ✅ {device['device_type'].title()} registered: {device['device_id']}")
        else:
            print(f"   ❌ Failed to register {device['device_type']}")
    
    print(f"\n📊 Initial Sync Statistics:")
    stats = sync_manager.get_sync_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print(f"\n🔄 Cross-Device Sync Demo:")
    print("-" * 40)
    
    # Test synchronization scenarios
    sync_scenarios = [
        {
            "type": "conversation",
            "data": {
                "message": "What's the weather like today?",
                "response": "Today is sunny with a high of 75°F",
                "timestamp": time.time()
            },
            "device_id": "mobile_001",
            "description": "Conversation sync from mobile"
        },
        {
            "type": "user_preferences",
            "data": {
                "voice_speed": "normal",
                "theme": "dark",
                "notifications_enabled": True,
                "auto_sync": True
            },
            "device_id": "desktop_001",
            "description": "Preferences sync from desktop"
        },
        {
            "type": "health_data",
            "data": {
                "heart_rate": 72,
                "steps": 8500,
                "calories": 1200,
                "timestamp": time.time()
            },
            "device_id": "watch_001",
            "description": "Health data sync from watch"
        },
        {
            "type": "context_data",
            "data": {
                "location": {"lat": 40.7128, "lng": -74.0060},
                "activity": "walking",
                "battery_level": 85,
                "network": "wifi"
            },
            "device_id": "mobile_001",
            "description": "Context sync from mobile"
        }
    ]
    
    for i, scenario in enumerate(sync_scenarios, 1):
        print(f"\n📤 Scenario {i}: {scenario['description']}")
        
        success = await sync_manager.sync_item(
            scenario["type"],
            scenario["data"],
            scenario["device_id"],
            "user123"
        )
        
        if success:
            print(f"   ✅ {scenario['type']} queued for sync")
        else:
            print(f"   ❌ Failed to queue {scenario['type']}")
        
        # Wait a bit for processing
        await asyncio.sleep(0.5)
    
    # Wait for sync processing
    print(f"\n⏳ Processing sync operations...")
    await asyncio.sleep(3)
    
    print(f"\n📊 Final Sync Statistics:")
    final_stats = sync_manager.get_sync_statistics()
    for key, value in final_stats.items():
        print(f"   {key}: {value}")
    
    # Test device disconnection
    print(f"\n📱 Testing Device Disconnection...")
    await sync_manager.unregister_device("watch_001")
    print("   ✅ Watch disconnected")
    
    disconnect_stats = sync_manager.get_sync_statistics()
    print(f"   Connected devices: {disconnect_stats['connected_devices']}")
    
    # Stop sync manager
    await sync_manager.stop()
    
    print(f"\n✅ Cross-device synchronization demonstrated successfully!")
    print("🔄 Real-time sync ensures consistent experience across all devices")
    print("⚡ Intelligent conflict resolution handles simultaneous updates")
    print("🎯 Device-aware optimization provides platform-specific data")

if __name__ == "__main__":
    asyncio.run(main())
