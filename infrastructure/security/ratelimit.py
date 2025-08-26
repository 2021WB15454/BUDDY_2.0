"""Simple in-memory rate limiter (Phase 1)."""
from __future__ import annotations
import time
from collections import deque
from typing import Deque, Dict


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self.store: Dict[str, Deque[float]] = {}

    def check(self, key: str) -> tuple[bool, int]:
        now = time.time()
        q = self.store.setdefault(key, deque())
        # purge old
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False, 0
        q.append(now)
        remaining = self.limit - len(q)
        return True, remaining
