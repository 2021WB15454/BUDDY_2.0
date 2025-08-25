"""
BUDDY Core - Central Intelligence Runtime

This is the brain of BUDDY that handles:
- Natural language understanding
- Skills execution
- Memory management
- Cross-device coordination
- Event orchestration

Architecture:
- Core Brain (this module) - central intelligence
- Device Interfaces - platform-specific UIs
- Sync Layer - cross-device state management
"""

__version__ = "2.0.0"
__author__ = "BUDDY Team"

# Core modules
from .api import APIGateway
from .dialogue import DialogueOrchestrator
from .skills import SkillsEngine
from .memory import MemoryLayer
from .voice import VoiceService
from .events import EventBus
from .sync import SyncService

__all__ = [
    "APIGateway",
    "DialogueOrchestrator", 
    "SkillsEngine",
    "MemoryLayer",
    "VoiceService",
    "EventBus",
    "SyncService"
]
