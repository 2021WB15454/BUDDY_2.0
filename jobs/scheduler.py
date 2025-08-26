"""Background job scheduler stub.

Phase 1: simple asyncio periodic tasks.
Later: integrate APScheduler / Celery for distributed scheduling.
"""
from __future__ import annotations
import asyncio, logging
from typing import Callable, Dict

logger = logging.getLogger(__name__)


class SimpleScheduler:
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}

    def schedule_interval(self, name: str, seconds: int, func: Callable):
        async def runner():
            await asyncio.sleep(1)
            while True:
                try:
                    await asyncio.sleep(seconds)
                    res = func()
                    if asyncio.iscoroutine(res):
                        await res
                except Exception as e:
                    logger.error(f"Scheduled task {name} failed: {e}")
        if name not in self._tasks:
            self._tasks[name] = asyncio.create_task(runner())

    def cancel_all(self):
        for t in self._tasks.values():
            t.cancel()


scheduler = SimpleScheduler()
