"""VoiceEngine with pluggable ASR/TTS adapters."""
from typing import Any
from .adapters import build_default_asr, build_default_tts, ASRAdapter, TTSAdapter

class VoiceEngine:
    def __init__(self, config):
        self.config = config
        self._asr: ASRAdapter | None = None
        self._tts: TTSAdapter | None = None

    async def initialize(self):  # pragma: no cover - trivial
        if not self._asr:
            self._asr = build_default_asr()
        if not self._tts:
            self._tts = build_default_tts()
        return True

    async def detect_wake_word(self, audio: bytes) -> bool:
        try:
            return b"hey buddy" in audio.lower()
        except Exception:  # pragma: no cover
            return False

    async def speech_to_text(self, audio: bytes) -> str:
        if not self._asr:
            self._asr = build_default_asr()
        return await self._asr.transcribe(audio)

    async def text_to_speech(self, text: str) -> bytes:
        if not self._tts:
            self._tts = build_default_tts()
        return await self._tts.synthesize(text)

