#!/usr/bin/env python3
"""TV Demo client for BUDDY Core - connects via WebSocket and displays messages"""
import asyncio
import aiohttp
import json

BASE = "http://localhost:8082"

async def tv_client():
    async with aiohttp.ClientSession() as s:
        print("📺 TV demo: requesting forecast via REST /chat")
        payload = {"message": "Show weather forecast for today", "context": {"device_type": "tv", "screen_size": "large"}}
        async with s.post(f"{BASE}/chat", json=payload) as r:
            print('status', r.status)
            print(await r.text())

if __name__ == '__main__':
    asyncio.run(tv_client())
