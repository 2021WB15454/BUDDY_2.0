"""Central dynamic configuration utilities for BUDDY.

All services and clients should derive host/port from environment variables
instead of hardcoding literals. This module provides helpers for Python code.

Environment variables:
  BUDDY_HOST  (default: localhost)
  BUDDY_PORT  (default: 8082)
  BUDDY_WS_PROTOCOL (default: ws)
  BUDDY_HTTP_PROTOCOL (default: http)
"""
from __future__ import annotations
import os

def get_host() -> str:
    return os.getenv("BUDDY_HOST", "localhost")

def get_port() -> int:
    try:
        return int(os.getenv("BUDDY_PORT", "8082"))
    except ValueError:
        return 8082

def get_http_base() -> str:
    proto = os.getenv("BUDDY_HTTP_PROTOCOL", "http")
    return f"{proto}://{get_host()}:{get_port()}"

def get_ws_base() -> str:
    proto = os.getenv("BUDDY_WS_PROTOCOL", "ws")
    return f"{proto}://{get_host()}:{get_port()}"
