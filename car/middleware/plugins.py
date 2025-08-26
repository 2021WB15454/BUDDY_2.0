"""Plugin registry for automotive intents.

Plugins register an intent type and are invoked after safety validation.
Each plugin function signature: async def handler(intent: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]
"""
from __future__ import annotations
from typing import Callable, Awaitable, Dict, Any

Handler = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]

class PluginRegistry:
    def __init__(self):
        self._handlers: Dict[str, Handler] = {}

    def register(self, intent_type: str, handler: Handler, override: bool = False):
        if not override and intent_type in self._handlers:
            raise ValueError(f"Handler already registered for {intent_type}")
        self._handlers[intent_type] = handler

    def get(self, intent_type: str) -> Handler | None:
        return self._handlers.get(intent_type)

    def list_intents(self):
        return list(self._handlers.keys())

registry = PluginRegistry()
