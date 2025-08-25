#!/usr/bin/env python3
"""
Intelligent Sync Scheduler for BUDDY Cross-Platform AI Assistant

Advanced synchronization scheduler that optimizes sync operations based on:
- Device capabilities and constraints
- Network conditions
- Priority and urgency of data
- Battery and resource availability
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import json
import time

logger = logging.getLogger(__name__)


class SyncPriority(Enum):
    REALTIME = 1      # Immediate sync (user messages, critical preferences)
    HIGH = 2          # Within 5 seconds (user preferences, device status)
    MEDIUM = 3        # Within 30 seconds (context updates, non-critical data)
    LOW = 4           # Within 5 minutes (analytics, usage data)
    BACKGROUND = 5    # Next sync cycle (cleanup operations, optimization)


class NetworkQuality(Enum):
    EXCELLENT = "excellent"  # High-speed, unlimited
    GOOD = "good"           # Standard broadband/LTE
    POOR = "poor"           # Slow connection, limited bandwidth
    MINIMAL = "minimal"     # Very limited connection
    OFFLINE = "offline"     # No connection


class DeviceConstraint(Enum):
    NONE = "none"           # No constraints
    BATTERY = "battery"     # Low battery, reduce sync frequency
    STORAGE = "storage"     # Low storage, prioritize essential data
    MEMORY = "memory"       # Low memory, reduce batch sizes
    PROCESSING = "processing"  # Limited CPU, reduce sync complexity


@dataclass
class SyncOperation:
    """Represents a single sync operation"""
    id: str
    table_name: str
    record_id: str
    operation_type: str  # INSERT, UPDATE, DELETE, UPSERT
    data: Dict[str, Any]
    priority: SyncPriority
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    device_id: str = ""
    user_id: str = ""
    size_bytes: int = 0
    
    def __post_init__(self):
        if self.scheduled_at is None:
            self.scheduled_at = self.created_at
        if self.size_bytes == 0:
            self.size_bytes = len(json.dumps(self.data).encode('utf-8'))


@dataclass
class SyncContext:
    """Current sync environment context"""
    device_type: str
    device_capability: str
    network_quality: NetworkQuality
    constraints: List[DeviceConstraint] = field(default_factory=list)
    battery_level: Optional[float] = None  # 0.0 to 1.0
    storage_free_mb: Optional[int] = None
    memory_available_mb: Optional[int] = None
    is_charging: bool = False
    is_user_active: bool = True
    last_sync: Optional[datetime] = None


class IntelligentSyncScheduler:
    """
    Intelligent sync scheduler that adapts to device capabilities,
    network conditions, and user behavior patterns.
    """
    
    def __init__(self, device_type: str, device_id: str, 
                 sync_callback: Optional[Callable] = None):
        self.device_type = device_type
        self.device_id = device_id
        self.sync_callback = sync_callback
        
        # Sync queues organized by priority
        self.sync_queues: Dict[SyncPriority, List[SyncOperation]] = {
            priority: [] for priority in SyncPriority
        }
        
        # Sync state
        self.is_syncing = False
        self.sync_context = SyncContext(
            device_type=device_type,
            device_capability=self._determine_device_capability(),
            network_quality=NetworkQuality.GOOD
        )
        
        # Sync statistics
        self.sync_stats = {
            'total_operations': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'retry_count': 0,
            'last_sync_time': None,
            'avg_sync_duration': 0.0
        }
        
        # Adaptive sync parameters
        self.sync_intervals = self._get_sync_intervals()
        self.batch_sizes = self._get_batch_sizes()
        
        # Background tasks
        self._sync_task = None
        self._context_monitor_task = None
        
        logger.info(f"Intelligent sync scheduler initialized for {device_type}")
    
    def _determine_device_capability(self) -> str:
        """Determine device capability level"""
        capability_map = {
            'desktop': 'high',
            'mobile': 'medium',
            'tablet': 'medium',
            'watch': 'low',
            'tv': 'low',
            'car': 'low'
        }
        return capability_map.get(self.device_type, 'medium')
    
    def _get_sync_intervals(self) -> Dict[SyncPriority, float]:
        """Get sync intervals based on device capability"""
        if self.sync_context.device_capability == 'high':
            return {
                SyncPriority.REALTIME: 0.1,    # 100ms
                SyncPriority.HIGH: 1.0,        # 1 second
                SyncPriority.MEDIUM: 10.0,     # 10 seconds
                SyncPriority.LOW: 60.0,        # 1 minute
                SyncPriority.BACKGROUND: 300.0 # 5 minutes
            }
        elif self.sync_context.device_capability == 'medium':
            return {
                SyncPriority.REALTIME: 0.5,    # 500ms
                SyncPriority.HIGH: 5.0,        # 5 seconds
                SyncPriority.MEDIUM: 30.0,     # 30 seconds
                SyncPriority.LOW: 300.0,       # 5 minutes
                SyncPriority.BACKGROUND: 1800.0 # 30 minutes
            }
        else:  # low capability
            return {
                SyncPriority.REALTIME: 2.0,    # 2 seconds
                SyncPriority.HIGH: 15.0,       # 15 seconds
                SyncPriority.MEDIUM: 120.0,    # 2 minutes
                SyncPriority.LOW: 600.0,       # 10 minutes
                SyncPriority.BACKGROUND: 3600.0 # 1 hour
            }
    
    def _get_batch_sizes(self) -> Dict[SyncPriority, int]:
        """Get batch sizes based on device capability and network"""
        base_sizes = {
            'high': {
                SyncPriority.REALTIME: 1,    # Immediate, single operations
                SyncPriority.HIGH: 10,       # Small batches
                SyncPriority.MEDIUM: 50,     # Medium batches
                SyncPriority.LOW: 100,       # Large batches
                SyncPriority.BACKGROUND: 200 # Very large batches
            },
            'medium': {
                SyncPriority.REALTIME: 1,
                SyncPriority.HIGH: 5,
                SyncPriority.MEDIUM: 20,
                SyncPriority.LOW: 50,
                SyncPriority.BACKGROUND: 100
            },
            'low': {
                SyncPriority.REALTIME: 1,
                SyncPriority.HIGH: 2,
                SyncPriority.MEDIUM: 5,
                SyncPriority.LOW: 10,
                SyncPriority.BACKGROUND: 20
            }
        }
        
        # Adjust for network quality
        capability_sizes = base_sizes[self.sync_context.device_capability]
        
        if self.sync_context.network_quality == NetworkQuality.POOR:
            return {k: max(1, v // 2) for k, v in capability_sizes.items()}
        elif self.sync_context.network_quality == NetworkQuality.MINIMAL:
            return {k: 1 for k in capability_sizes.keys()}
        else:
            return capability_sizes
    
    async def start(self):
        """Start the intelligent sync scheduler"""
        if self._sync_task is None:
            self._sync_task = asyncio.create_task(self._sync_loop())
            self._context_monitor_task = asyncio.create_task(self._monitor_context())
            logger.info("Intelligent sync scheduler started")
    
    async def stop(self):
        """Stop the sync scheduler"""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            self._sync_task = None
        
        if self._context_monitor_task:
            self._context_monitor_task.cancel()
            try:
                await self._context_monitor_task
            except asyncio.CancelledError:
                pass
            self._context_monitor_task = None
        
        logger.info("Intelligent sync scheduler stopped")
    
    async def schedule_operation(self, operation: SyncOperation):
        """Schedule a sync operation with intelligent prioritization"""
        # Add device and timing information
        operation.device_id = self.device_id
        operation.created_at = datetime.now(timezone.utc)
        
        # Adjust priority based on context
        adjusted_priority = self._adjust_priority_for_context(operation)
        
        # Add to appropriate queue
        self.sync_queues[adjusted_priority].append(operation)
        self.sync_stats['total_operations'] += 1
        
        logger.debug(f"Scheduled {operation.operation_type} operation for {operation.table_name} "
                    f"with priority {adjusted_priority.name}")
        
        # Trigger immediate sync for high-priority operations
        if adjusted_priority in [SyncPriority.REALTIME, SyncPriority.HIGH]:
            if not self.is_syncing:
                asyncio.create_task(self._execute_sync_cycle())
    
    def _adjust_priority_for_context(self, operation: SyncOperation) -> SyncPriority:
        """Adjust operation priority based on current context"""
        original_priority = operation.priority
        
        # Downgrade priority if device is constrained
        if DeviceConstraint.BATTERY in self.sync_context.constraints:
            if original_priority in [SyncPriority.MEDIUM, SyncPriority.LOW]:
                return SyncPriority.BACKGROUND
        
        if DeviceConstraint.STORAGE in self.sync_context.constraints:
            # Prioritize DELETE operations to free space
            if operation.operation_type == 'DELETE':
                return SyncPriority.HIGH
        
        # Upgrade priority if user is active and operation is recent
        if (self.sync_context.is_user_active and 
            operation.table_name == 'conversations' and
            operation.operation_type in ['INSERT', 'UPDATE']):
            if original_priority == SyncPriority.HIGH:
                return SyncPriority.REALTIME
        
        # Network-based adjustments
        if self.sync_context.network_quality in [NetworkQuality.POOR, NetworkQuality.MINIMAL]:
            if original_priority == SyncPriority.MEDIUM:
                return SyncPriority.LOW
            elif original_priority == SyncPriority.LOW:
                return SyncPriority.BACKGROUND
        
        return original_priority
    
    async def _sync_loop(self):
        """Main sync loop that runs continuously"""
        while True:
            try:
                await self._execute_sync_cycle()
                
                # Calculate next sync interval based on pending operations
                next_interval = self._calculate_next_sync_interval()
                await asyncio.sleep(next_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(5)  # Error recovery delay
    
    def _calculate_next_sync_interval(self) -> float:
        """Calculate the next sync interval based on pending operations"""
        # Find the highest priority with pending operations
        for priority in SyncPriority:
            if self.sync_queues[priority]:
                return self.sync_intervals[priority]
        
        # No pending operations, use background interval
        return self.sync_intervals[SyncPriority.BACKGROUND]
    
    async def _execute_sync_cycle(self):
        """Execute a single sync cycle"""
        if self.is_syncing or self.sync_context.network_quality == NetworkQuality.OFFLINE:
            return
        
        self.is_syncing = True
        sync_start_time = time.time()
        
        try:
            # Determine sync strategy based on context
            strategy = self._determine_sync_strategy()
            
            if strategy == "aggressive":
                await self._aggressive_sync()
            elif strategy == "conservative":
                await self._conservative_sync()
            elif strategy == "minimal":
                await self._minimal_sync()
            else:  # background_only
                await self._background_sync()
            
            # Update sync statistics
            sync_duration = time.time() - sync_start_time
            self.sync_stats['successful_syncs'] += 1
            self.sync_stats['last_sync_time'] = datetime.now(timezone.utc)
            
            # Update average sync duration
            if self.sync_stats['avg_sync_duration'] == 0:
                self.sync_stats['avg_sync_duration'] = sync_duration
            else:
                self.sync_stats['avg_sync_duration'] = (
                    self.sync_stats['avg_sync_duration'] * 0.8 + sync_duration * 0.2
                )
            
            logger.debug(f"Sync cycle completed in {sync_duration:.2f}s using {strategy} strategy")
            
        except Exception as e:
            self.sync_stats['failed_syncs'] += 1
            logger.error(f"Sync cycle failed: {e}")
        
        finally:
            self.is_syncing = False
    
    def _determine_sync_strategy(self) -> str:
        """Determine optimal sync strategy based on current context"""
        # Check for constraints
        if DeviceConstraint.BATTERY in self.sync_context.constraints:
            return "background_only"
        
        if self.sync_context.network_quality == NetworkQuality.MINIMAL:
            return "minimal"
        elif self.sync_context.network_quality == NetworkQuality.POOR:
            return "conservative"
        elif (self.sync_context.device_capability == 'high' and 
              self.sync_context.network_quality in [NetworkQuality.GOOD, NetworkQuality.EXCELLENT]):
            return "aggressive"
        else:
            return "conservative"
    
    async def _aggressive_sync(self):
        """Sync all priorities with large batches"""
        for priority in SyncPriority:
            operations = self.sync_queues[priority]
            if operations:
                batch_size = self.batch_sizes[priority]
                await self._sync_batch(operations[:batch_size], priority)
                # Remove synced operations
                self.sync_queues[priority] = operations[batch_size:]
    
    async def _conservative_sync(self):
        """Sync high and medium priorities with medium batches"""
        priorities_to_sync = [SyncPriority.REALTIME, SyncPriority.HIGH, SyncPriority.MEDIUM]
        
        for priority in priorities_to_sync:
            operations = self.sync_queues[priority]
            if operations:
                batch_size = min(self.batch_sizes[priority], 10)  # Limit batch size
                await self._sync_batch(operations[:batch_size], priority)
                self.sync_queues[priority] = operations[batch_size:]
    
    async def _minimal_sync(self):
        """Sync only critical operations with small batches"""
        critical_priorities = [SyncPriority.REALTIME, SyncPriority.HIGH]
        
        for priority in critical_priorities:
            operations = self.sync_queues[priority]
            if operations:
                # Very small batches for minimal sync
                batch_size = 1 if priority == SyncPriority.REALTIME else 2
                await self._sync_batch(operations[:batch_size], priority)
                self.sync_queues[priority] = operations[batch_size:]
    
    async def _background_sync(self):
        """Sync only background operations"""
        operations = self.sync_queues[SyncPriority.BACKGROUND]
        if operations:
            batch_size = min(self.batch_sizes[SyncPriority.BACKGROUND], 5)
            await self._sync_batch(operations[:batch_size], SyncPriority.BACKGROUND)
            self.sync_queues[SyncPriority.BACKGROUND] = operations[batch_size:]
    
    async def _sync_batch(self, operations: List[SyncOperation], priority: SyncPriority):
        """Sync a batch of operations"""
        if not operations or not self.sync_callback:
            return
        
        try:
            # Group operations by type for efficient batch processing
            grouped_ops = self._group_operations_by_type(operations)
            
            # Execute sync for each operation type
            for op_type, ops in grouped_ops.items():
                try:
                    await self.sync_callback(ops, op_type, priority)
                    logger.debug(f"Successfully synced {len(ops)} {op_type} operations")
                except Exception as e:
                    logger.error(f"Failed to sync {op_type} operations: {e}")
                    # Re-queue failed operations with increased retry count
                    await self._handle_sync_failures(ops)
            
        except Exception as e:
            logger.error(f"Failed to sync batch: {e}")
            await self._handle_sync_failures(operations)
    
    def _group_operations_by_type(self, operations: List[SyncOperation]) -> Dict[str, List[SyncOperation]]:
        """Group operations by table name and operation type for batch processing"""
        grouped = {}
        
        for op in operations:
            key = f"{op.table_name}_{op.operation_type}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(op)
        
        return grouped
    
    async def _handle_sync_failures(self, failed_operations: List[SyncOperation]):
        """Handle failed sync operations with intelligent retry logic"""
        for operation in failed_operations:
            operation.retry_count += 1
            self.sync_stats['retry_count'] += 1
            
            if operation.retry_count <= operation.max_retries:
                # Calculate exponential backoff delay
                delay_seconds = min(300, 2 ** operation.retry_count)  # Max 5 minutes
                operation.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                
                # Re-queue with potentially lower priority
                retry_priority = operation.priority
                if operation.retry_count > 1:
                    # Downgrade priority for repeated failures
                    priority_downgrade = {
                        SyncPriority.REALTIME: SyncPriority.HIGH,
                        SyncPriority.HIGH: SyncPriority.MEDIUM,
                        SyncPriority.MEDIUM: SyncPriority.LOW,
                        SyncPriority.LOW: SyncPriority.BACKGROUND,
                        SyncPriority.BACKGROUND: SyncPriority.BACKGROUND
                    }
                    retry_priority = priority_downgrade[operation.priority]
                
                self.sync_queues[retry_priority].append(operation)
                logger.debug(f"Re-queued operation {operation.id} with retry {operation.retry_count}")
            else:
                logger.error(f"Operation {operation.id} exceeded max retries, dropping")
    
    async def _monitor_context(self):
        """Monitor device context and adjust sync behavior accordingly"""
        while True:
            try:
                # Update context (in a real implementation, this would interface with system APIs)
                await self._update_sync_context()
                
                # Adjust sync parameters based on new context
                self.sync_intervals = self._get_sync_intervals()
                self.batch_sizes = self._get_batch_sizes()
                
                # Sleep for context monitoring interval
                await asyncio.sleep(30)  # Check context every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error monitoring context: {e}")
                await asyncio.sleep(60)  # Error recovery delay
    
    async def _update_sync_context(self):
        """Update the current sync context (mock implementation)"""
        # In a real implementation, this would interface with:
        # - Network APIs to check connection quality
        # - Battery APIs to check power level
        # - Storage APIs to check available space
        # - Memory APIs to check available RAM
        # - User activity detection
        
        # Mock updates for demonstration
        self.sync_context.is_user_active = True  # Would be detected from user interaction
        self.sync_context.last_sync = datetime.now(timezone.utc)
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """Get comprehensive sync statistics"""
        return {
            'device_type': self.device_type,
            'device_capability': self.sync_context.device_capability,
            'network_quality': self.sync_context.network_quality.value,
            'constraints': [c.value for c in self.sync_context.constraints],
            'total_operations': self.sync_stats['total_operations'],
            'successful_syncs': self.sync_stats['successful_syncs'],
            'failed_syncs': self.sync_stats['failed_syncs'],
            'retry_count': self.sync_stats['retry_count'],
            'success_rate': (
                self.sync_stats['successful_syncs'] / max(1, self.sync_stats['total_operations']) * 100
            ),
            'avg_sync_duration': self.sync_stats['avg_sync_duration'],
            'last_sync_time': self.sync_stats['last_sync_time'],
            'pending_operations': {
                priority.name: len(self.sync_queues[priority]) 
                for priority in SyncPriority
            },
            'is_syncing': self.is_syncing
        }
    
    def update_network_quality(self, quality: NetworkQuality):
        """Update network quality and adjust sync behavior"""
        old_quality = self.sync_context.network_quality
        self.sync_context.network_quality = quality
        
        if old_quality != quality:
            logger.info(f"Network quality changed from {old_quality.value} to {quality.value}")
            # Immediately recalculate batch sizes
            self.batch_sizes = self._get_batch_sizes()
    
    def add_constraint(self, constraint: DeviceConstraint):
        """Add a device constraint that affects sync behavior"""
        if constraint not in self.sync_context.constraints:
            self.sync_context.constraints.append(constraint)
            logger.info(f"Added device constraint: {constraint.value}")
    
    def remove_constraint(self, constraint: DeviceConstraint):
        """Remove a device constraint"""
        if constraint in self.sync_context.constraints:
            self.sync_context.constraints.remove(constraint)
            logger.info(f"Removed device constraint: {constraint.value}")


# Example usage
async def main():
    """Example usage of IntelligentSyncScheduler"""
    
    async def mock_sync_callback(operations, operation_type, priority):
        """Mock sync callback for testing"""
        print(f"Syncing {len(operations)} {operation_type} operations with priority {priority.name}")
        await asyncio.sleep(0.1)  # Simulate sync time
    
    # Create scheduler for mobile device
    scheduler = IntelligentSyncScheduler('mobile', 'mobile_123', mock_sync_callback)
    await scheduler.start()
    
    try:
        # Schedule some operations
        for i in range(10):
            operation = SyncOperation(
                id=f"op_{i}",
                table_name="conversations",
                record_id=f"conv_{i}",
                operation_type="INSERT",
                data={"content": f"Message {i}"},
                priority=SyncPriority.HIGH,
                created_at=datetime.now(timezone.utc)
            )
            await scheduler.schedule_operation(operation)
        
        # Let it run for a bit
        await asyncio.sleep(10)
        
        # Get statistics
        stats = scheduler.get_sync_statistics()
        print(f"Sync statistics: {stats}")
        
    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
