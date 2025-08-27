from __future__ import annotations
"""Simple TTL + size-limited LRU cache (Phase D enhancement)."""
from collections import OrderedDict
from typing import Generic, TypeVar, Dict, Tuple, Optional
import time

K = TypeVar('K')
V = TypeVar('V')

class TTLCache(Generic[K, V]):
    def __init__(self, maxsize: int = 256, ttl_seconds: int = 1800):
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self._data: "OrderedDict[K, Tuple[float, V]]" = OrderedDict()
        self.hits: int = 0
        self.misses: int = 0

    def get(self, key: K) -> Optional[V]:
        now = time.time()
        item = self._data.get(key)
        if not item:
            self.misses += 1
            return None
        exp, value = item
        if exp < now:
            self._data.pop(key, None)
            self.misses += 1
            return None
        self._data.move_to_end(key)
        self.hits += 1
        return value

    def set(self, key: K, value: V):
        now = time.time()
        exp = now + self.ttl
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = (exp, value)
        if len(self._data) > self.maxsize:
            self._data.popitem(last=False)

    def purge_expired(self):
        now = time.time()
        expired = [k for k, (exp, _) in self._data.items() if exp < now]
        for k in expired:
            self._data.pop(k, None)

    def stats(self) -> Dict[str, float]:  # type: ignore[name-defined]
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total else 0.0
        return {"size": len(self._data), "hits": self.hits, "misses": self.misses, "hit_rate": hit_rate}

    def __len__(self):
        self.purge_expired()
        return len(self._data)