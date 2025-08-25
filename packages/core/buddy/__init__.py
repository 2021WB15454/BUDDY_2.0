"""
BUDDY Core Runtime Engine

The central orchestrator for BUDDY's cross-device personal AI assistant.
Handles event routing, dialogue management, skill execution, and coordination
between all subsystems.
"""

__version__ = "0.1.0"
__author__ = "BUDDY Development Team"

from .runtime import BuddyRuntime
from .events import EventBus
from .dialogue import DialogueManager
from .skills import SkillRegistry

__all__ = [
    "BuddyRuntime",
    "EventBus", 
    "DialogueManager",
    "SkillRegistry"
]
