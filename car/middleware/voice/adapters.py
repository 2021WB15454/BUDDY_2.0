"""ASR/TTS adapter interfaces and concrete simple implementations.

Provides pluggable architecture so production can swap in Whisper, Vosk,
or cloud services without changing core middleware.
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable, Optional

try:  # pragma: no cover - optional
    import pyttsx3  # type: ignore
except Exception:  # pragma: no cover
    pyttsx3 = None  # type: ignore

try:  # pragma: no cover - optional
    import speech_recognition as sr  # type: ignore
except Exception:  # pragma: no cover
    sr = None  # type: ignore

try:  # pragma: no cover - optional heavy model
    import whisper  # type: ignore
except Exception:  # pragma: no cover
    whisper = None  # type: ignore


@runtime_checkable
class ASRAdapter(Protocol):
    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str: ...


@runtime_checkable
class TTSAdapter(Protocol):
    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes: ...


class FallbackASRAdapter:
    """Very naive ASR placeholder returning static string when real engine absent."""
    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:  # pragma: no cover - trivial
        return "transcribed speech"


class SpeechRecognitionASRAdapter:
    """Adapter wrapping `speech_recognition` library if available.

    NOTE: This is a blocking library; to integrate cleanly we'd normally run this
    in a thread executor. For brevity and because tests use synthetic audio, we
    keep it simple. If library missing, raise to allow fallback.
    """
    def __init__(self):
        if not sr:
            raise RuntimeError("speech_recognition not installed")
        self.recognizer = sr.Recognizer()

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:  # pragma: no cover - integration
        import io, asyncio
        if not sr:  # Fallback if lib vanished
            return ""
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:  # type: ignore[attr-defined]
            audio = self.recognizer.record(source)
        loop = asyncio.get_event_loop()
        # Run potentially blocking recognition in executor
        def _rec():
            try:
                return self.recognizer.recognize_google(audio, language=language)
            except Exception:
                return ""
        return await loop.run_in_executor(None, _rec)


class WhisperASRAdapter:
    """Adapter for OpenAI Whisper local model if installed.
    Loads a small model by default to keep footprint light.
    """
    def __init__(self, model_name: str = "base"):
        if not whisper:
            raise RuntimeError("whisper not installed")
        self.model = whisper.load_model(model_name)  # synchronous load

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:  # pragma: no cover - perf heavy
        import io, tempfile, asyncio
        loop = asyncio.get_event_loop()
        def _run():
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as f:
                f.write(audio_bytes)
                f.flush()
                result = self.model.transcribe(f.name, language=language)
                return result.get('text', '').strip()
        return await loop.run_in_executor(None, _run)


class Pyttsx3TTSAdapter:
    def __init__(self):
        if not pyttsx3:
            raise RuntimeError("pyttsx3 not installed")
        self.engine = pyttsx3.init()

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:  # pragma: no cover - audio output
        # pyttsx3 writes to speakers; for API we just return bytes placeholder.
        # A production impl would stream synthesized audio buffer.
        return text.encode('utf-8')


class FallbackTTSAdapter:
    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:  # pragma: no cover - trivial
        return text.encode('utf-8')


def build_default_asr() -> ASRAdapter:
    # Try Whisper first (higher quality) then speech_recognition then fallback.
    for builder in (lambda: WhisperASRAdapter(), SpeechRecognitionASRAdapter, FallbackASRAdapter):
        try:
            return builder()
        except Exception:
            continue
    return FallbackASRAdapter()


def build_default_tts() -> TTSAdapter:
    try:
        return Pyttsx3TTSAdapter()
    except Exception:
        return FallbackTTSAdapter()
