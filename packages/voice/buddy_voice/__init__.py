"""
BUDDY Voice Processing Package

Handles all voice-related functionality including wake word detection,
voice activity detection, speech recognition, and text-to-speech synthesis.
Designed for offline-first operation with graceful online enhancement.
"""

__version__ = "0.1.0"

from .pipeline import VoicePipeline
from .wake_word import WakeWordDetector
from .vad import VoiceActivityDetector
from .asr import SpeechRecognizer
from .tts import TextToSpeech

__all__ = [
    "VoicePipeline",
    "WakeWordDetector", 
    "VoiceActivityDetector",
    "SpeechRecognizer",
    "TextToSpeech"
]
