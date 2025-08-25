"""
BUDDY Automatic Speech Recognition (ASR)

Converts speech audio to text using various models including Whisper,
Vosk, and other offline-capable ASR systems. Optimized for real-time
streaming with partial results and confidence scoring.
"""

import asyncio
import logging
import numpy as np
from typing import Optional, Dict, Any, List
import tempfile
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    """
    Automatic Speech Recognition system for BUDDY.
    
    Supports multiple ASR backends with emphasis on offline capability,
    real-time performance, and multilingual support.
    """
    
    def __init__(self, audio_config, model_name: str = "whisper_base"):
        self.audio_config = audio_config
        self.model_name = model_name
        self.sample_rate = audio_config.sample_rate
        
        # Models
        self.whisper_model = None
        self.vosk_model = None
        self.model_type = None
        self.is_initialized = False
        
        # Configuration
        self.language = "en"
        self.min_confidence = 0.3
        self.max_audio_length = 30.0  # seconds
        
        # State tracking
        self.last_confidence = 0.0
        self.last_transcript = ""
        self.processing_time = 0.0
        
        # Statistics
        self.stats = {
            "total_transcriptions": 0,
            "successful_transcriptions": 0,
            "avg_confidence": 0.0,
            "avg_processing_time": 0.0,
            "total_audio_processed": 0.0
        }
        
    async def initialize(self) -> bool:
        """Initialize ASR model."""
        try:
            # Try Whisper first (preferred for quality)
            if await self._init_whisper():
                logger.info(f"Initialized Whisper ASR: {self.model_name}")
                return True
                
            # Try Vosk (good for real-time)
            if await self._init_vosk():
                logger.info(f"Initialized Vosk ASR: {self.model_name}")
                return True
                
            # Fallback to simple recognition
            if await self._init_simple():
                logger.info(f"Initialized simple ASR fallback")
                return True
                
            logger.error("Failed to initialize any ASR model")
            return False
            
        except Exception as e:
            logger.error(f"ASR initialization error: {e}")
            return False
            
    async def _init_whisper(self) -> bool:
        """Initialize Whisper model."""
        try:
            import whisper
            
            # Map model names
            model_map = {
                "whisper_tiny": "tiny",
                "whisper_base": "base", 
                "whisper_small": "small",
                "whisper_medium": "medium",
                "whisper_large": "large"
            }
            
            whisper_model_name = model_map.get(self.model_name, "base")
            
            # Load model
            self.whisper_model = whisper.load_model(whisper_model_name)
            self.model_type = "whisper"
            self.is_initialized = True
            
            logger.info(f"Loaded Whisper model: {whisper_model_name}")
            return True
            
        except ImportError:
            logger.debug("Whisper not available")
        except Exception as e:
            logger.debug(f"Whisper initialization failed: {e}")
            
        return False
        
    async def _init_vosk(self) -> bool:
        """Initialize Vosk model."""
        try:
            import vosk
            import json
            
            # Try to find Vosk model
            model_path = self._find_vosk_model()
            if not model_path:
                logger.debug("Vosk model not found")
                return False
                
            # Load model
            self.vosk_model = vosk.Model(str(model_path))
            self.model_type = "vosk"
            self.is_initialized = True
            
            logger.info(f"Loaded Vosk model from: {model_path}")
            return True
            
        except ImportError:
            logger.debug("Vosk not available")
        except Exception as e:
            logger.debug(f"Vosk initialization failed: {e}")
            
        return False
        
    async def _init_simple(self) -> bool:
        """Initialize simple ASR fallback."""
        try:
            # Simple recognizer for testing
            self.simple_recognizer = SimpleASR()
            self.model_type = "simple"
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Simple ASR initialization failed: {e}")
            return False
            
    def _find_vosk_model(self) -> Optional[Path]:
        """Find Vosk model in common locations."""
        potential_paths = [
            Path("models/vosk"),
            Path("./vosk-model"),
            Path.home() / ".cache" / "vosk",
            Path("/usr/share/vosk"),
        ]
        
        for path in potential_paths:
            if path.exists() and path.is_dir():
                # Check if it looks like a Vosk model
                if (path / "am" / "final.mdl").exists():
                    return path
                    
        return None
        
    async def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            Transcribed text
        """
        if not self.is_initialized:
            return ""
            
        try:
            import time
            start_time = time.time()
            
            self.stats["total_transcriptions"] += 1
            audio_duration = len(audio_data) / self.sample_rate
            self.stats["total_audio_processed"] += audio_duration
            
            # Limit audio length
            if audio_duration > self.max_audio_length:
                max_samples = int(self.max_audio_length * self.sample_rate)
                audio_data = audio_data[:max_samples]
                logger.warning(f"Audio truncated to {self.max_audio_length}s")
                
            # Transcribe with appropriate model
            transcript = ""
            confidence = 0.0
            
            if self.model_type == "whisper":
                transcript, confidence = await self._transcribe_whisper(audio_data)
            elif self.model_type == "vosk":
                transcript, confidence = await self._transcribe_vosk(audio_data)
            elif self.model_type == "simple":
                transcript, confidence = await self._transcribe_simple(audio_data)
                
            # Update state
            self.last_transcript = transcript
            self.last_confidence = confidence
            self.processing_time = time.time() - start_time
            
            # Update statistics
            if confidence >= self.min_confidence:
                self.stats["successful_transcriptions"] += 1
                
            # Update average confidence
            total_successful = self.stats["successful_transcriptions"]
            if total_successful > 0:
                self.stats["avg_confidence"] = (
                    (self.stats["avg_confidence"] * (total_successful - 1) + confidence)
                    / total_successful
                )
                
            # Update average processing time
            total_transcriptions = self.stats["total_transcriptions"]
            self.stats["avg_processing_time"] = (
                (self.stats["avg_processing_time"] * (total_transcriptions - 1) + self.processing_time)
                / total_transcriptions
            )
            
            logger.debug(f"Transcribed ({self.processing_time:.2f}s): '{transcript}' "
                        f"(confidence: {confidence:.3f})")
            
            return transcript if confidence >= self.min_confidence else ""
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
            
    async def _transcribe_whisper(self, audio_data: np.ndarray) -> tuple[str, float]:
        """Transcribe using Whisper."""
        try:
            # Convert to float32 and normalize
            if audio_data.dtype != np.float32:
                audio_float = audio_data.astype(np.float32) / 32767.0
            else:
                audio_float = audio_data
                
            # Ensure sample rate is 16kHz for Whisper
            if self.sample_rate != 16000:
                # Simple resampling (should use proper resampling in production)
                target_length = int(len(audio_float) * 16000 / self.sample_rate)
                audio_float = np.interp(
                    np.linspace(0, len(audio_float), target_length),
                    np.arange(len(audio_float)),
                    audio_float
                )
                
            # Transcribe
            result = self.whisper_model.transcribe(
                audio_float,
                language=self.language,
                fp16=False  # Use fp32 for better compatibility
            )
            
            text = result.get("text", "").strip()
            
            # Calculate confidence from segment scores
            segments = result.get("segments", [])
            if segments:
                confidences = [seg.get("no_speech_prob", 1.0) for seg in segments]
                # Convert no_speech_prob to speech confidence
                avg_confidence = 1.0 - np.mean(confidences)
            else:
                avg_confidence = 0.5  # Default moderate confidence
                
            return text, avg_confidence
            
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return "", 0.0
            
    async def _transcribe_vosk(self, audio_data: np.ndarray) -> tuple[str, float]:
        """Transcribe using Vosk."""
        try:
            import vosk
            import json
            
            # Create recognizer
            rec = vosk.KaldiRecognizer(self.vosk_model, self.sample_rate)
            
            # Convert to int16 bytes
            if audio_data.dtype != np.int16:
                audio_int16 = (audio_data.clip(-1, 1) * 32767).astype(np.int16)
            else:
                audio_int16 = audio_data
                
            audio_bytes = audio_int16.tobytes()
            
            # Process audio
            rec.AcceptWaveform(audio_bytes)
            result = json.loads(rec.FinalResult())
            
            text = result.get("text", "").strip()
            confidence = result.get("confidence", 0.0)
            
            return text, confidence
            
        except Exception as e:
            logger.error(f"Vosk transcription error: {e}")
            return "", 0.0
            
    async def _transcribe_simple(self, audio_data: np.ndarray) -> tuple[str, float]:
        """Transcribe using simple recognizer."""
        if hasattr(self, 'simple_recognizer'):
            return await self.simple_recognizer.transcribe(audio_data)
        return "", 0.0
        
    async def stream_transcribe(self, audio_stream) -> List[str]:
        """
        Transcribe streaming audio with partial results.
        
        Args:
            audio_stream: Async generator of audio chunks
            
        Returns:
            List of partial transcriptions
        """
        partial_results = []
        audio_buffer = []
        
        try:
            async for audio_chunk in audio_stream:
                audio_buffer.append(audio_chunk)
                
                # Process every few chunks for partial results
                if len(audio_buffer) >= 5:  # Adjust based on chunk size
                    combined_audio = np.concatenate(audio_buffer)
                    partial_transcript = await self.transcribe(combined_audio)
                    
                    if partial_transcript:
                        partial_results.append(partial_transcript)
                        
                    # Keep only recent audio for next partial
                    audio_buffer = audio_buffer[-3:]
                    
        except Exception as e:
            logger.error(f"Stream transcription error: {e}")
            
        return partial_results
        
    async def stop(self):
        """Stop ASR processing."""
        self.whisper_model = None
        self.vosk_model = None
        self.is_initialized = False
        logger.info("ASR stopped")
        
    def set_language(self, language: str):
        """Set recognition language."""
        self.language = language
        logger.info(f"ASR language set to: {language}")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get ASR statistics."""
        success_rate = 0.0
        if self.stats["total_transcriptions"] > 0:
            success_rate = self.stats["successful_transcriptions"] / self.stats["total_transcriptions"]
            
        return {
            "model_type": self.model_type,
            "is_initialized": self.is_initialized,
            "language": self.language,
            "last_confidence": self.last_confidence,
            "last_processing_time": self.processing_time,
            "success_rate": success_rate,
            **self.stats
        }


class SimpleASR:
    """
    Simple ASR implementation for testing and fallback.
    
    Provides basic speech recognition capabilities when
    sophisticated models aren't available.
    """
    
    def __init__(self):
        self.responses = [
            "I heard something",
            "Can you repeat that?",
            "I'm listening",
            "Please speak clearly",
            "I'm processing your request"
        ]
        
    async def transcribe(self, audio_data: np.ndarray) -> tuple[str, float]:
        """Simple transcription that returns a placeholder."""
        # Calculate basic audio features
        energy = np.sqrt(np.mean(audio_data.astype(float) ** 2))
        duration = len(audio_data) / 16000  # Assume 16kHz
        
        # Return different responses based on audio characteristics
        if energy > 0.01 and duration > 0.5:
            import random
            response = random.choice(self.responses)
            confidence = min(energy * 10, 0.8)  # Cap at 0.8 for simple recognizer
            return response, confidence
            
        return "", 0.0
