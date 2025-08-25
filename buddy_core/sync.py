import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SyncService:
    """Simple Last-Writer-Wins (LWW) sync service for demo purposes."""
    def __init__(self, event_bus=None, memory=None, config=None):
        self.event_bus = event_bus
        self.memory = memory
        self.config = config or {}
        # in-memory store for demo sync objects: {key: {value, ts}}
        self.store = {}
        self._lock = asyncio.Lock()

    async def initialize(self):
        logger.info("Sync Service initialized")

    async def push(self, device_id: str, items: Dict[str, Any]):
        """Push items from a device. Items should be {key: {value, ts}}"""
        async with self._lock:
            for k, v in (items or {}).items():
                existing = self.store.get(k)
                # v expected to be {'value':..., 'ts': epoch_ms}
                if not existing or v.get('ts', 0) >= existing.get('ts', 0):
                    self.store[k] = v
                    # Optionally persist to memory layer
                    if self.memory:
                        await self.memory.kv_set(k, v)
        # Broadcast event
        if self.event_bus:
            await self.event_bus.publish('sync.push', {'device_id': device_id, 'items': items}, device_id=device_id)
        return True

    async def pull(self, device_id: str, keys=None):
        """Pull items for a device. If keys None, return all."""
        async with self._lock:
            if keys is None:
                return dict(self.store)
            else:
                return {k: self.store.get(k) for k in keys}

    async def shutdown(self):
        logger.info("Sync Service stopped")
