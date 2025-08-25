#!/usr/bin/env python3
"""Watch Demo client - lightweight REST-based client that pulls sync and posts simple messages"""
import asyncio
import aiohttp
import time

BASE = "http://localhost:8082"

async def watch_demo():
    async with aiohttp.ClientSession() as s:
        # Post a status update to sync
        ts = int(time.time() * 1000)
        payload = {
            "device_id": "watch_001",
            "items": {
                "health.heart_rate": {"value": 68, "ts": ts},
                "health.steps": {"value": 1234, "ts": ts}
            }
        }
        print("📡 Pushing health to sync...")
        async with s.post(f"{BASE}/sync/push", json=payload) as r:
            print("push status:", r.status, await r.text())

        # Pull sync
        async with s.get(f"{BASE}/sync/pull?device_id=watch_001") as r:
            print("pull status:", r.status, await r.text())

        # Send a quick chat message via REST
        chat_payload = {"message": "What's my next calendar event?", "context": {"device_type": "watch"}}
        async with s.post(f"{BASE}/chat", json=chat_payload) as r:
            print("chat status:", r.status, await r.text())

if __name__ == '__main__':
    asyncio.run(watch_demo())
