"""
BUDDY Text-to-Speech (TTS)

Converts text to natural-sounding speech using various TTS engines
including Piper, Coqui-TTS, and system TTS. Supports multiple voices,
emotional expression, and real-time streaming synthesis.
"""

import asyncio
import logging
import numpy as np
from typing import Optional, Dict, Any, List
import tempfile
import os
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)


class TextToSpeech:
    """
    Text-to-Speech system for BUDDY.
    
    Supports multiple TTS backends with emphasis on offline capability,
    natural voice quality, and low latency for real-time interaction.
    """
    
    def __init__(self, audio_config, voice_name: str = "default"):
        self.audio_config = audio_config
        self.voice_name = voice_name
        self.sample_rate = audio_config.sample_rate
        
        # TTS engines
        self.piper_model = None
        self.coqui_model = None
        self.system_tts = None
        self.engine_type = None
        self.is_initialized = False
        
        # Configuration
        self.speed = 1.0
        self.pitch = 1.0
        self.volume = 1.0
        self.emotion = "neutral"
        
        # Voice management
        self.available_voices = {}
        self.current_voice = voice_name
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_syntheses": 0,
            "total_characters": 0,
            "avg_synthesis_time": 0.0,
            "total_audio_generated": 0.0
        }
        
    async def initialize(self) -> bool:
        """Initialize TTS engine."""
        try:
            # Try Piper first (preferred for quality and offline)
            if await self._init_piper():
                logger.info(f"Initialized Piper TTS: {self.voice_name}")
                return True
                
            # Try Coqui TTS
            if await self._init_coqui():
                logger.info(f"Initialized Coqui TTS: {self.voice_name}")
                return True
                
            # Fallback to system TTS
            if await self._init_system():
                logger.info(f"Initialized system TTS: {self.voice_name}")
                return True
                
            logger.error("Failed to initialize any TTS engine")
            return False
            
        except Exception as e:
            logger.error(f"TTS initialization error: {e}")
            return False
            
    async def _init_piper(self) -> bool:
        """Initialize Piper TTS."""
        try:
            # Check if Piper binary exists
            piper_path = self._find_piper_binary()
            if not piper_path:
                logger.debug("Piper binary not found")
                return False
                
            # Find voice model
            voice_model = self._find_piper_voice(self.voice_name)
            if not voice_model:
                logger.debug(f"Piper voice model not found: {self.voice_name}")
                return False
                
            self.piper_model = {
                "binary": piper_path,
                "model": voice_model,
                "config": voice_model.with_suffix(".json")
            }
            self.engine_type = "piper"
            self.is_initialized = True
            
            # Load available voices
            await self._load_piper_voices()
            
            return True
            
        except Exception as e:
            logger.debug(f"Piper initialization failed: {e}")
            return False
            
    async def _init_coqui(self) -> bool:
        """Initialize Coqui TTS."""
        try:
            import TTS
            from TTS.api import TTS as CoquiTTS
            
            # Initialize with a basic model
            model_name = "tts_models/en/ljspeech/tacotron2-DDC"
            self.coqui_model = CoquiTTS(model_name=model_name)
            self.engine_type = "coqui"
            self.is_initialized = True
            
            # Load available models
            await self._load_coqui_voices()
            
            return True
            
        except ImportError:
            logger.debug("Coqui TTS not available")
        except Exception as e:
            logger.debug(f"Coqui initialization failed: {e}")
            
        return False
        
    async def _init_system(self) -> bool:
        """Initialize system TTS."""
        try:
            import platform
            
            system = platform.system().lower()
            
            if system == "windows":
                # Use Windows SAPI
                self.system_tts = WindowsTTS()
            elif system == "darwin":
                # Use macOS say command
                self.system_tts = MacOSTTS()
            elif system == "linux":
                # Use espeak or festival
                self.system_tts = LinuxTTS()
            else:
                return False
                
            self.engine_type = "system"
            self.is_initialized = True
            
            # Load available voices
            await self._load_system_voices()
            
            return True
            
        except Exception as e:
            logger.debug(f"System TTS initialization failed: {e}")
            return False
            
    def _find_piper_binary(self) -> Optional[Path]:
        """Find Piper binary in common locations."""
        potential_paths = [
            Path("./piper"),
            Path("./bin/piper"),
            Path("models/piper/piper"),
            Path.home() / ".local" / "bin" / "piper",
            Path("/usr/local/bin/piper"),
            Path("/usr/bin/piper"),
        ]
        
        # Add Windows executable extension
        import platform
        if platform.system().lower() == "windows":
            potential_paths.extend([
                Path("./piper.exe"),
                Path("./bin/piper.exe"),
                Path("models/piper/piper.exe"),
            ])
            
        for path in potential_paths:
            if path.exists() and path.is_file():
                return path
                
        return None
        
    def _find_piper_voice(self, voice_name: str) -> Optional[Path]:
        """Find Piper voice model."""
        voice_dirs = [
            Path("models/piper/voices"),
            Path("./voices"),
            Path.home() / ".local" / "share" / "piper" / "voices",
        ]
        
        for voice_dir in voice_dirs:
            if not voice_dir.exists():
                continue
                
            # Look for .onnx model files
            for model_file in voice_dir.glob("**/*.onnx"):
                if voice_name.lower() in model_file.stem.lower():
                    return model_file
                    
        return None
        
    async def speak(self, text: str, voice: Optional[str] = None) -> bool:
        """
        Convert text to speech and play it.
        
        Args:
            text: Text to synthesize
            voice: Voice to use (optional)
            
        Returns:
            True if successful
        """
        if not self.is_initialized:
            logger.error("TTS not initialized")
            return False
            
        if not text.strip():
            return True
            
        try:
            import time
            start_time = time.time()
            
            self.stats["total_requests"] += 1
            self.stats["total_characters"] += len(text)
            
            voice_to_use = voice or self.current_voice
            
            # Synthesize audio
            audio_data = None
            
            if self.engine_type == "piper":
                audio_data = await self._synthesize_piper(text, voice_to_use)
            elif self.engine_type == "coqui":
                audio_data = await self._synthesize_coqui(text, voice_to_use)
            elif self.engine_type == "system":
                audio_data = await self._synthesize_system(text, voice_to_use)
                
            if audio_data is not None:
                # Play the audio
                success = await self._play_audio(audio_data)
                
                if success:
                    self.stats["successful_syntheses"] += 1
                    
                # Update statistics
                synthesis_time = time.time() - start_time
                self.stats["avg_synthesis_time"] = (
                    (self.stats["avg_synthesis_time"] * (self.stats["total_requests"] - 1) + synthesis_time)
                    / self.stats["total_requests"]
                )
                
                if isinstance(audio_data, np.ndarray):
                    audio_duration = len(audio_data) / self.sample_rate
                    self.stats["total_audio_generated"] += audio_duration
                    
                logger.debug(f"TTS completed ({synthesis_time:.2f}s): '{text[:50]}...'")
                return success
                
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            
        return False
        
    async def _synthesize_piper(self, text: str, voice: str) -> Optional[np.ndarray]:
        """Synthesize using Piper."""
        try:
            if not self.piper_model:
                return None
                
            # Create temporary files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as text_file:
                text_file.write(text)
                text_file_path = text_file.name
                
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as audio_file:
                audio_file_path = audio_file.name
                
            try:
                # Run Piper
                cmd = [
                    str(self.piper_model["binary"]),
                    "--model", str(self.piper_model["model"]),
                    "--config", str(self.piper_model["config"]),
                    "--output_file", audio_file_path
                ]
                
                # Add text via stdin
                process = subprocess.run(
                    cmd,
                    input=text,
                    text=True,
                    capture_output=True,
                    timeout=30
                )
                
                if process.returncode == 0:
                    # Load generated audio
                    import soundfile as sf
                    audio_data, sr = sf.read(audio_file_path)
                    
                    # Convert to numpy array if needed
                    if not isinstance(audio_data, np.ndarray):
                        audio_data = np.array(audio_data)
                        
                    return audio_data
                else:
                    logger.error(f"Piper process failed: {process.stderr}")
                    
            finally:
                # Clean up temporary files
                try:
                    os.unlink(text_file_path)
                    os.unlink(audio_file_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Piper synthesis error: {e}")
            
        return None
        
    async def _synthesize_coqui(self, text: str, voice: str) -> Optional[np.ndarray]:
        """Synthesize using Coqui TTS."""
        try:
            if not self.coqui_model:
                return None
                
            # Synthesize
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                
            try:
                self.coqui_model.tts_to_file(text=text, file_path=temp_path)
                
                # Load audio
                import soundfile as sf
                audio_data, sr = sf.read(temp_path)
                
                return audio_data
                
            finally:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Coqui synthesis error: {e}")
            
        return None
        
    async def _synthesize_system(self, text: str, voice: str) -> Optional[bool]:
        """Synthesize using system TTS."""
        try:
            if self.system_tts:
                return await self.system_tts.speak(text, voice)
                
        except Exception as e:
            logger.error(f"System TTS synthesis error: {e}")
            
        return None
        
    async def _play_audio(self, audio_data) -> bool:
        """Play audio data."""
        try:
            if isinstance(audio_data, bool):
                return audio_data  # System TTS already played
                
            if not isinstance(audio_data, np.ndarray):
                return False
                
            # Play using sounddevice
            import sounddevice as sd
            
            # Ensure audio is in correct format
            if audio_data.dtype != np.float32:
                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32767.0
                else:
                    audio_data = audio_data.astype(np.float32)
                    
            # Play audio
            sd.play(audio_data, self.sample_rate)
            sd.wait()  # Wait until audio finishes
            
            return True
            
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            return False
            
    async def _load_piper_voices(self):
        """Load available Piper voices."""
        # Implementation would scan voice directories
        self.available_voices["piper"] = ["default", "female", "male"]
        
    async def _load_coqui_voices(self):
        """Load available Coqui voices."""
        # Implementation would scan available models
        self.available_voices["coqui"] = ["ljspeech", "female", "male"]
        
    async def _load_system_voices(self):
        """Load available system voices."""
        if self.system_tts:
            voices = await self.system_tts.get_voices()
            self.available_voices["system"] = voices
            
    async def stop(self):
        """Stop TTS processing."""
        self.piper_model = None
        self.coqui_model = None
        self.system_tts = None
        self.is_initialized = False
        logger.info("TTS stopped")
        
    def get_available_voices(self) -> List[str]:
        """Get list of available voices."""
        if self.engine_type in self.available_voices:
            return self.available_voices[self.engine_type]
        return []
        
    def set_voice(self, voice_name: str) -> bool:
        """Set current voice."""
        available = self.get_available_voices()
        if voice_name in available:
            self.current_voice = voice_name
            logger.info(f"TTS voice set to: {voice_name}")
            return True
        return False
        
    def get_stats(self) -> Dict[str, Any]:
        """Get TTS statistics."""
        success_rate = 0.0
        if self.stats["total_requests"] > 0:
            success_rate = self.stats["successful_syntheses"] / self.stats["total_requests"]
            
        return {
            "engine_type": self.engine_type,
            "is_initialized": self.is_initialized,
            "current_voice": self.current_voice,
            "available_voices": len(self.get_available_voices()),
            "success_rate": success_rate,
            **self.stats
        }


class WindowsTTS:
    """Windows SAPI TTS implementation."""
    
    def __init__(self):
        self.voices = []
        
    async def speak(self, text: str, voice: str) -> bool:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            return True
        except:
            return False
            
    async def get_voices(self) -> List[str]:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            return [voice.id for voice in voices]
        except:
            return ["default"]


class MacOSTTS:
    """macOS say command TTS implementation."""
    
    async def speak(self, text: str, voice: str) -> bool:
        try:
            cmd = ["say", text]
            if voice != "default":
                cmd.extend(["-v", voice])
            subprocess.run(cmd, check=True)
            return True
        except:
            return False
            
    async def get_voices(self) -> List[str]:
        try:
            result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
            voices = [line.split()[0] for line in result.stdout.split('\n') if line.strip()]
            return voices
        except:
            return ["default"]


class LinuxTTS:
    """Linux espeak/festival TTS implementation."""
    
    async def speak(self, text: str, voice: str) -> bool:
        try:
            # Try espeak first
            cmd = ["espeak", text]
            subprocess.run(cmd, check=True)
            return True
        except:
            try:
                # Try festival
                cmd = ["festival", "--tts"]
                subprocess.run(cmd, input=text, text=True, check=True)
                return True
            except:
                return False
                
    async def get_voices(self) -> List[str]:
        return ["default"]
