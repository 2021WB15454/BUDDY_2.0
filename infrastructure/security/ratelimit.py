"""Simple in-memory rate limiter (Phase 1)."""
from __future__ import annotations
import time
from collections import deque
from typing import Deque, Dict


class RateLimiter:
    """Simple in-memory sliding window counter with optional per-call overrides.

    NOTE: In production replace with Redis + Lua script for atomicity across workers.
    """

    def __init__(self, limit: int, window_seconds: int):
        self.default_limit = limit
        self.default_window = window_seconds
        self.store: Dict[str, Deque[float]] = {}

    def _prune(self, q: Deque[float], now: float, window: int):
        while q and now - q[0] > window:
            q.popleft()

    def check(self, key: str, *, limit: int | None = None, window: int | None = None) -> tuple[bool, int, int]:
        """Check & record a hit.

        Returns (allowed, remaining, applied_limit)
        """
        applied_limit = limit or self.default_limit
        applied_window = window or self.default_window
        now = time.time()
        q = self.store.setdefault(key, deque())
        self._prune(q, now, applied_window)
        if len(q) >= applied_limit:
            return False, 0, applied_limit
        q.append(now)
        remaining = applied_limit - len(q)
        return True, remaining, applied_limit
