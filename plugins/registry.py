"""Plugin registry scaffolding.

Allows registration of pluggable skill modules with enable/disable lifecycle hooks.
Future: persistence of states, version constraints, remote marketplace.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Callable, Optional


@dataclass
class Plugin:
    name: str
    version: str = "0.1.0"
    enabled: bool = True
    on_enable: Optional[Callable] = None
    on_disable: Optional[Callable] = None


class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}

    def register(self, plugin: Plugin):
        self._plugins[plugin.name] = plugin
        if plugin.enabled and plugin.on_enable:
            plugin.on_enable()

    def enable(self, name: str):
        p = self._plugins.get(name)
        if p and not p.enabled:
            p.enabled = True
            if p.on_enable:
                p.on_enable()

    def disable(self, name: str):
        p = self._plugins.get(name)
        if p and p.enabled:
            p.enabled = False
            if p.on_disable:
                p.on_disable()

    def list(self):
        return list(self._plugins.values())


registry = PluginRegistry()
