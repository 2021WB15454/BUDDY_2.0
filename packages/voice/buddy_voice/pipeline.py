"""
BUDDY Voice Pipeline

Complete voice processing pipeline that coordinates wake word detection,
voice activity detection, speech recognition, and text-to-speech.
Handles the full voice interaction flow with error recovery and optimization.
"""

import asyncio
import logging
import numpy as np
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import threading
import queue

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Audio configuration parameters."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    format: str = "int16"


@dataclass 
class VoiceEvent:
    """Voice processing event."""
    event_type: str  # wake_detected, speech_start, speech_end, transcript, etc.
    timestamp: datetime
    data: Dict[str, Any]
    confidence: float = 0.0
    device_id: str = "unknown"


class VoicePipeline:
    """
    Complete voice processing pipeline for BUDDY.
    
    Orchestrates the full voice interaction flow:
    Audio Input → Wake Word → VAD → ASR → Text Output
    Response Text → TTS → Audio Output
    """
    
    def __init__(self, config: AudioConfig, event_callback: Optional[Callable] = None):
        self.config = config
        self.event_callback = event_callback
        
        # Pipeline components (will be initialized lazily)
        self.wake_word_detector = None
        self.vad = None
        self.asr = None
        self.tts = None
        
        # State management
        self.is_running = False
        self.is_listening_for_wake = True
        self.is_recording_speech = False
        self.current_session = None
        
        # Audio streaming
        self.audio_queue = queue.Queue()
        self.audio_thread = None
        
        # Performance tracking
        self.stats = {
            "wake_detections": 0,
            "speech_sessions": 0,
            "transcriptions": 0,
            "tts_requests": 0,
            "errors": 0
        }
        
    async def initialize(self):
        """Initialize all pipeline components."""
        try:
            # Import and initialize components
            from .wake_word import WakeWordDetector
            from .vad import VoiceActivityDetector  
            from .asr import SpeechRecognizer
            from .tts import TextToSpeech
            
            self.wake_word_detector = WakeWordDetector(self.config)
            await self.wake_word_detector.initialize()
            
            self.vad = VoiceActivityDetector(self.config)
            await self.vad.initialize()
            
            self.asr = SpeechRecognizer(self.config)
            await self.asr.initialize()
            
            self.tts = TextToSpeech(self.config)
            await self.tts.initialize()
            
            logger.info("Voice pipeline initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize voice pipeline: {e}")
            return False
            
    async def start(self):
        """Start the voice pipeline."""
        if self.is_running:
            logger.warning("Voice pipeline already running")
            return
            
        if not await self.initialize():
            raise RuntimeError("Failed to initialize voice pipeline")
            
        self.is_running = True
        
        # Start audio processing thread
        self.audio_thread = threading.Thread(target=self._audio_processing_loop, daemon=True)
        self.audio_thread.start()
        
        # Start main processing loop
        asyncio.create_task(self._main_processing_loop())
        
        logger.info("Voice pipeline started")
        
    async def stop(self):
        """Stop the voice pipeline."""
        if not self.is_running:
            return
            
        self.is_running = False
        
        # Stop components
        if self.wake_word_detector:
            await self.wake_word_detector.stop()
        if self.vad:
            await self.vad.stop()
        if self.asr:
            await self.asr.stop()
        if self.tts:
            await self.tts.stop()
            
        # Wait for audio thread to finish
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=5.0)
            
        logger.info("Voice pipeline stopped")
        
    def _audio_processing_loop(self):
        """Audio processing loop running in separate thread."""
        try:
            import sounddevice as sd
            
            def audio_callback(indata, frames, time, status):
                if status:
                    logger.warning(f"Audio input status: {status}")
                
                # Convert to the format expected by our pipeline
                audio_data = (indata[:, 0] * 32767).astype(np.int16)
                self.audio_queue.put(audio_data)
            
            # Start audio stream
            with sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype='float32',
                blocksize=self.config.chunk_size,
                callback=audio_callback
            ):
                logger.info("Audio stream started")
                while self.is_running:
                    threading.Event().wait(0.1)
                    
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            self.stats["errors"] += 1
            
    async def _main_processing_loop(self):
        """Main voice processing loop."""
        audio_buffer = []
        
        while self.is_running:
            try:
                # Get audio data (non-blocking)
                try:
                    audio_chunk = self.audio_queue.get_nowait()
                    audio_buffer.append(audio_chunk)
                    
                    # Keep buffer to reasonable size
                    if len(audio_buffer) > 100:  # ~6 seconds at 16kHz, 1024 chunk
                        audio_buffer.pop(0)
                        
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                
                # Process based on current state
                if self.is_listening_for_wake and not self.is_recording_speech:
                    await self._process_wake_detection(audio_chunk)
                    
                elif self.is_recording_speech:
                    await self._process_speech_recording(audio_chunk, audio_buffer)
                    
            except Exception as e:
                logger.error(f"Processing loop error: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(0.1)
                
    async def _process_wake_detection(self, audio_chunk: np.ndarray):
        """Process audio for wake word detection."""
        try:
            is_wake_detected = await self.wake_word_detector.process_audio(audio_chunk)
            
            if is_wake_detected:
                self.stats["wake_detections"] += 1
                
                await self._emit_event(VoiceEvent(
                    event_type="wake_detected",
                    timestamp=datetime.now(),
                    data={"confidence": self.wake_word_detector.last_confidence},
                    confidence=self.wake_word_detector.last_confidence
                ))
                
                # Start speech recording
                self.is_recording_speech = True
                self.is_listening_for_wake = False
                
                logger.info("Wake word detected, starting speech recording")
                
        except Exception as e:
            logger.error(f"Wake detection error: {e}")
            
    async def _process_speech_recording(self, audio_chunk: np.ndarray, audio_buffer: List[np.ndarray]):
        """Process audio during speech recording."""
        try:
            # Check for voice activity
            is_speech = await self.vad.process_audio(audio_chunk)
            
            if is_speech and not hasattr(self, '_speech_started'):
                self._speech_started = True
                await self._emit_event(VoiceEvent(
                    event_type="speech_start",
                    timestamp=datetime.now(),
                    data={}
                ))
                
            # If no speech for a while, end recording
            if not is_speech and hasattr(self, '_speech_started'):
                silence_duration = getattr(self, '_silence_count', 0) + 1
                setattr(self, '_silence_count', silence_duration)
                
                # End speech after 1 second of silence (assuming 16kHz, 1024 chunks)
                if silence_duration > 15:  
                    await self._end_speech_recording(audio_buffer)
                    
            elif is_speech:
                setattr(self, '_silence_count', 0)
                
        except Exception as e:
            logger.error(f"Speech recording error: {e}")
            
    async def _end_speech_recording(self, audio_buffer: List[np.ndarray]):
        """End speech recording and process transcript."""
        try:
            self.is_recording_speech = False
            delattr(self, '_speech_started')
            delattr(self, '_silence_count')
            
            await self._emit_event(VoiceEvent(
                event_type="speech_end",
                timestamp=datetime.now(),
                data={}
            ))
            
            # Combine audio buffer for transcription
            if audio_buffer:
                full_audio = np.concatenate(audio_buffer)
                
                # Process with ASR
                transcript = await self.asr.transcribe(full_audio)
                
                if transcript and transcript.strip():
                    self.stats["transcriptions"] += 1
                    
                    await self._emit_event(VoiceEvent(
                        event_type="transcript",
                        timestamp=datetime.now(),
                        data={
                            "text": transcript,
                            "confidence": self.asr.last_confidence
                        },
                        confidence=self.asr.last_confidence
                    ))
                    
                    logger.info(f"Transcription: {transcript}")
                    
            # Resume wake word detection
            self.is_listening_for_wake = True
            
        except Exception as e:
            logger.error(f"End speech recording error: {e}")
            # Reset state on error
            self.is_recording_speech = False
            self.is_listening_for_wake = True
            
    async def speak_text(self, text: str, voice: str = "default", 
                        priority: str = "normal") -> bool:
        """
        Convert text to speech and play it.
        
        Args:
            text: Text to speak
            voice: Voice to use
            priority: Priority level (low, normal, high)
            
        Returns:
            True if successful
        """
        try:
            if not self.tts:
                logger.error("TTS not initialized")
                return False
                
            self.stats["tts_requests"] += 1
            
            # Temporarily pause wake word detection during speech
            was_listening = self.is_listening_for_wake
            self.is_listening_for_wake = False
            
            await self._emit_event(VoiceEvent(
                event_type="tts_start",
                timestamp=datetime.now(),
                data={"text": text, "voice": voice}
            ))
            
            # Generate and play speech
            success = await self.tts.speak(text, voice)
            
            await self._emit_event(VoiceEvent(
                event_type="tts_end",
                timestamp=datetime.now(),
                data={"text": text, "success": success}
            ))
            
            # Resume wake word detection
            self.is_listening_for_wake = was_listening
            
            return success
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            self.stats["errors"] += 1
            return False
            
    async def _emit_event(self, event: VoiceEvent):
        """Emit a voice event to the callback."""
        if self.event_callback:
            try:
                if asyncio.iscoroutinefunction(self.event_callback):
                    await self.event_callback(event)
                else:
                    self.event_callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
                
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "is_running": self.is_running,
            "is_listening_for_wake": self.is_listening_for_wake,
            "is_recording_speech": self.is_recording_speech,
            "stats": self.stats.copy(),
            "components": {
                "wake_word": self.wake_word_detector is not None,
                "vad": self.vad is not None,
                "asr": self.asr is not None,
                "tts": self.tts is not None
            }
        }
        
    def set_wake_word_enabled(self, enabled: bool):
        """Enable or disable wake word detection."""
        self.is_listening_for_wake = enabled
        logger.info(f"Wake word detection {'enabled' if enabled else 'disabled'}")
        
    async def force_listen(self):
        """Force start listening for speech (skip wake word)."""
        if not self.is_recording_speech:
            self.is_recording_speech = True
            self.is_listening_for_wake = False
            logger.info("Forced speech listening started")
