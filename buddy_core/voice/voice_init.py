"""
BUDDY 2.0 Voice Module - Advanced Voice Interaction System
=========================================================

This module provides comprehensive voice interaction capabilities for BUDDY 2.0,
integrating speech-to-text, text-to-speech, and natural language processing
for seamless voice conversations.

Components:
- VoiceEngine: Core voice processing engine
- VoiceInterface: High-level voice interaction API
- VoiceWebServer: Web-based voice interface
- Integration with Phase 1 Advanced AI capabilities

Usage:
    from buddy_core.voice import VoiceAssistant, speak, listen_and_respond
    
    # Quick voice interaction
    response = await listen_and_respond()
    await speak("Hello, how can I help you?")
    
    # Full voice assistant
    assistant = VoiceAssistant()
    await assistant.initialize()
    response = await assistant.chat()
"""

# Import main voice components for easy access
from .voice_engine import (
    VoiceEngine,
    VoiceConfig,
    VoiceEngineMode,
    VoiceActivityDetector,
    SpeechToTextEngine,
    TextToSpeechEngine,
    WakeWordDetector,
    get_voice_engine,
    speak,
    listen_and_respond
)

from .voice_interface import (
    VoiceAssistant,
    VoicePersonality,
    VoiceConversationManager,
    quick_voice_test,
    voice_chat,
    start_voice_assistant,
    voice_schedule_meeting,
    voice_weather_check,
    voice_email_send,
    voice_demo
)

# Version info
__version__ = "2.0.0"
__phase__ = "Phase 8: Voice Capabilities"

# Quick access functions
__all__ = [
    # Core engine
    "VoiceEngine",
    "VoiceConfig", 
    "VoiceEngineMode",
    "get_voice_engine",
    
    # High-level interface
    "VoiceAssistant",
    "VoicePersonality",
    "VoiceConversationManager",
    
    # Quick functions
    "speak",
    "listen_and_respond", 
    "voice_chat",
    "quick_voice_test",
    "start_voice_assistant",
    
    # Specialized functions
    "voice_schedule_meeting",
    "voice_weather_check", 
    "voice_email_send",
    "voice_demo"
]
