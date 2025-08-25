"""
Minimal VoiceService implementation for development.

Provides placeholder ASR and TTS so other components can exercise
voice flows during local development and demos.
"""

import asyncio
import logging
from typing import Any
from ..events import Event

logger = logging.getLogger(__name__)


class VoiceService:
    """Minimal voice service for demo/test runs.

    - ASR: returns canned transcription when audio present.
    - TTS: attempts to use pyttsx3 on Windows; otherwise publishes completion
      events with played=False.
    """

    def __init__(self, event_bus, config: Any = None):
        self.event_bus = event_bus
        self.config = config or {}
        self._loop = None
        self._tts_engine_available = False
        self._tts = None

    async def initialize(self):
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()

        try:
            import platform
            if platform.system().lower() == "windows":
                import pyttsx3

                try:
                    self._tts = pyttsx3.init()
                    self._tts_engine_available = True
                except Exception:
                    self._tts_engine_available = False
            else:
                self._tts_engine_available = False
        except Exception:
            self._tts_engine_available = False

        # subscribe to event bus topics if available
        try:
            await self.event_bus.subscribe("voice.asr.request", self.handle_asr_request)
            await self.event_bus.subscribe("voice.tts.request", self.handle_tts_request)
        except Exception:
            logger.debug("VoiceService: event bus subscription failed")

        logger.info("VoiceService initialized (tts=%s)", self._tts_engine_available)

    async def handle_asr_request(self, event: Event):
        data = event.data or {}
        audio = data.get("audio_data")

        if audio:
            text = "This is a demo transcription"
            confidence = 0.75
        else:
            text = data.get("text", "simulated voice input")
            confidence = 0.5

        await self.event_bus.publish("voice.asr.complete", {"text": text, "confidence": confidence}, device_id=event.device_id)

    async def handle_tts_request(self, event: Event):
        text = (event.data or {}).get("text", "")
        result = {"text": text, "played": False, "engine": "system" if self._tts_engine_available else "none"}

        if self._tts_engine_available and text.strip():
            def _speak(t: str):
                try:
                    self._tts.say(t)
                    self._tts.runAndWait()
                    return True
                except Exception:
                    return False

            try:
                ok = await self._loop.run_in_executor(None, _speak, text)
                result["played"] = bool(ok)
            except Exception:
                result["played"] = False

        await self.event_bus.publish("voice.tts.complete", result, device_id=event.device_id)

    async def stop(self):
        logger.info("VoiceService stopped")
