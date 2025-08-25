"""
BUDDY 2.0 Voice Module
=====================

Phase 8: Voice Capabilities Integration
- Speech-to-text processing
- Text-to-speech synthesis
- Voice activity detection
- Wake word recognition
- Natural voice conversations
- Web-based voice interface
- Integration with Phase 1 Advanced AI

This module provides comprehensive voice interaction capabilities
for the BUDDY 2.0 assistant.
"""

# Backward compatibility: keep the old VoiceService for existing code
import asyncio
import logging
from typing import Any
from ..events import Event

logger = logging.getLogger(__name__)

class VoiceService:
    """Legacy voice service for backward compatibility"""
    def __init__(self, event_bus, config: Any = None):
        self.event_bus = event_bus
        self.config = config or {}
        
    async def initialize(self):
        logger.info("Legacy VoiceService initialized")
        
    async def stop(self):
        logger.info("Legacy VoiceService stopped")

# Import new Phase 8 voice classes and functions
try:
    from .voice_engine import VoiceEngine, VoiceConfig
    from .voice_interface import (
        VoiceAssistant, 
        VoicePersonality, 
        VoiceConversationManager,
        speak,
        voice_chat,
        start_voice_assistant,
        quick_voice_test
    )
    
    # New Phase 8 voice capabilities available
    _VOICE_AVAILABLE = True
    
except ImportError as e:
    logger.warning(f"Phase 8 voice capabilities not available: {e}")
    
    # Provide fallback implementations
    class VoiceEngine:
        def __init__(self, *args, **kwargs):
            pass
    
    class VoiceConfig:
        def __init__(self, *args, **kwargs):
            pass
    
    class VoiceAssistant:
        def __init__(self, *args, **kwargs):
            pass
    
    class VoicePersonality:
        def __init__(self, *args, **kwargs):
            pass
    
    class VoiceConversationManager:
        def __init__(self, *args, **kwargs):
            pass
    
    async def speak(text):
        print(f"[VOICE FALLBACK] Would speak: {text}")
        
    async def voice_chat(text):
        return f"Voice response to: {text}"
        
    async def start_voice_assistant(*args, **kwargs):
        return VoiceAssistant()
        
    async def quick_voice_test():
        return {"overall_status": "fallback", "mode": "text-only"}
    
    _VOICE_AVAILABLE = False

# Version info
__version__ = "2.0.0"
__phase__ = "Phase 8: Voice Capabilities"

# Export main API
__all__ = [
    'VoiceService',  # Legacy compatibility
    'VoiceEngine',
    'VoiceConfig', 
    'VoiceAssistant',
    'VoicePersonality',
    'VoiceConversationManager',
    'speak',
    'voice_chat',
    'start_voice_assistant',
    'quick_voice_test'
]
