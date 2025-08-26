"""Background job scheduler stub.

Phase 1: simple asyncio periodic tasks.
Later: integrate APScheduler / Celery for distributed scheduling.
"""
from __future__ import annotations
import asyncio, logging
from datetime import datetime
from typing import Callable, Dict

logger = logging.getLogger(__name__)


class SimpleScheduler:
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}

    def schedule_interval(self, name: str, seconds: int, func: Callable, one_shot: bool = False):
        async def runner():
            await asyncio.sleep(1)
            while True:
                try:
                    await asyncio.sleep(seconds)
                    res = func()
                    if asyncio.iscoroutine(res):
                        await res
                    if one_shot:
                        break
                except Exception as e:
                    logger.error(f"Scheduled task {name} failed: {e}")
        if name not in self._tasks:
            self._tasks[name] = asyncio.create_task(runner())

    def schedule_at(self, name: str, run_at, func: Callable):
        """Schedule a one-shot task to run at a specific datetime (UTC)."""
        if name in self._tasks:
            return
        async def runner():
            try:
                delay = (run_at - datetime.utcnow()).total_seconds()
                if delay > 0:
                    await asyncio.sleep(delay)
                res = func()
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.error(f"Scheduled task {name} failed: {e}")
        self._tasks[name] = asyncio.create_task(runner())

    def cancel_all(self):
        for t in self._tasks.values():
            t.cancel()


scheduler = SimpleScheduler()
