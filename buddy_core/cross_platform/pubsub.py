"""Cross-platform Pub/Sub abstraction.

Primary provider order:
1. Redis (if redis-py available and REDIS_URL env var)
2. (Future) NATS (placeholder stub)
3. In-process async fan-out (development fallback)

Publish API is async: await pubsub.publish(topic, payload_dict)
"""
from __future__ import annotations
import os, json, asyncio, threading
from typing import Any, Dict, List, Callable, Awaitable

class BasePubSub:
    async def publish(self, topic: str, payload: Dict[str, Any]):  # pragma: no cover - interface
        raise NotImplementedError
    async def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], Any]):  # pragma: no cover
        raise NotImplementedError

class InProcessPubSub(BasePubSub):
    def __init__(self):
        self._subs: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}
        self._lock = asyncio.Lock()
    async def publish(self, topic: str, payload: Dict[str, Any]):
        async with self._lock:
            subs = list(self._subs.get(topic, []))
        for cb in subs:
            try:
                res = cb(payload)
                if asyncio.iscoroutine(res) or isinstance(res, Awaitable):
                    await res
            except Exception:
                pass
    async def subscribe(self, topic: str, callback):
        async with self._lock:
            self._subs.setdefault(topic, []).append(callback)

class RedisPubSub(BasePubSub):
    def __init__(self, client):
        self._client = client
        self._pubsub = client.pubsub(ignore_subscribe_messages=True)
        self._callbacks: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}
        self._listener_started = False
        self._lock = threading.Lock()
        self._loop = asyncio.get_event_loop()

    async def publish(self, topic: str, payload: Dict[str, Any]):
        data = json.dumps(payload, ensure_ascii=False)
        await asyncio.to_thread(self._client.publish, topic, data)

    async def subscribe(self, topic: str, callback):
        with self._lock:
            self._callbacks.setdefault(topic, []).append(callback)
            # Subscribe underlying pubsub if first time
            if len(self._callbacks[topic]) == 1:
                try:
                    self._pubsub.subscribe(topic)
                except Exception:
                    pass
            if not self._listener_started:
                self._listener_started = True
                threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        for message in self._pubsub.listen():
            if not message or message.get('type') != 'message':
                continue
            channel = message.get('channel')
            if isinstance(channel, bytes):
                channel = channel.decode('utf-8')
            data_raw = message.get('data')
            if isinstance(data_raw, bytes):
                data_raw = data_raw.decode('utf-8')
            try:
                payload = json.loads(data_raw)
            except Exception:
                payload = {"raw": data_raw}
            with self._lock:
                callbacks = list(self._callbacks.get(channel, []))
            for cb in callbacks:
                try:
                    # dispatch onto event loop
                    if asyncio.iscoroutinefunction(cb):
                        asyncio.run_coroutine_threadsafe(cb(payload), self._loop)
                    else:
                        self._loop.call_soon_threadsafe(cb, payload)
                except Exception:
                    pass

class NATSPubSub(BasePubSub):  # placeholder for future NATS integration
    def __init__(self):
        raise NotImplementedError("NATS integration not yet implemented")

def _build_pubsub() -> BasePubSub:
    # Redis
    try:
        import redis  # type: ignore
        redis_url = os.getenv("REDIS_URL") or os.getenv("REDIS_URI")
        if redis_url:
            client = redis.Redis.from_url(redis_url)
            # test connection quickly
            try:
                client.ping()
                return RedisPubSub(client)
            except Exception:
                pass
    except Exception:
        pass
    # Future: NATS (skipped)
    return InProcessPubSub()

pubsub: BasePubSub = _build_pubsub()

__all__ = ["pubsub", "BasePubSub"]
