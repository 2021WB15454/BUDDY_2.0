"""
BUDDY Voice Activity Detection (VAD)

Detects speech vs non-speech in audio streams using various algorithms
including WebRTC VAD, energy-based detection, and ML models.
Optimized for real-time processing with low latency.
"""

import asyncio
import logging
import numpy as np
from typing import Optional, Dict, Any
import time

logger = logging.getLogger(__name__)


class VoiceActivityDetector:
    """
    Voice Activity Detection for distinguishing speech from silence/noise.
    
    Uses multiple detection methods with configurable sensitivity and
    temporal smoothing to reduce false positives.
    """
    
    def __init__(self, audio_config):
        self.audio_config = audio_config
        self.sample_rate = audio_config.sample_rate
        
        # Detection models
        self.webrtc_vad = None
        self.energy_detector = None
        self.is_initialized = False
        
        # Configuration
        self.sensitivity = 0.6  # 0.0 = less sensitive, 1.0 = more sensitive
        self.min_speech_duration = 0.3  # Minimum speech duration in seconds
        self.min_silence_duration = 0.8  # Minimum silence to end speech
        
        # State tracking
        self.is_speech_active = False
        self.speech_start_time = 0
        self.silence_start_time = 0
        self.last_detection_time = 0
        
        # Smoothing buffers
        self.detection_buffer = []
        self.buffer_size = 5  # Number of frames to average
        
        # Statistics
        self.stats = {
            "total_frames": 0,
            "speech_frames": 0,
            "silence_frames": 0,
            "speech_segments": 0,
            "avg_speech_duration": 0.0
        }
        
    async def initialize(self) -> bool:
        """Initialize VAD models."""
        try:
            # Try WebRTC VAD first
            if await self._init_webrtc_vad():
                logger.info("Initialized WebRTC VAD")
                
            # Always initialize energy detector as fallback
            self.energy_detector = EnergyVAD(self.sample_rate)
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"VAD initialization error: {e}")
            return False
            
    async def _init_webrtc_vad(self) -> bool:
        """Initialize WebRTC VAD."""
        try:
            import webrtcvad
            
            # Create WebRTC VAD with medium aggressiveness
            vad = webrtcvad.Vad()
            vad.set_mode(2)  # 0-3, where 3 is most aggressive
            
            # Check if sample rate is supported
            if self.sample_rate in [8000, 16000, 32000, 48000]:
                self.webrtc_vad = vad
                return True
            else:
                logger.warning(f"WebRTC VAD doesn't support {self.sample_rate}Hz")
                
        except ImportError:
            logger.debug("WebRTC VAD not available")
        except Exception as e:
            logger.debug(f"WebRTC VAD initialization failed: {e}")
            
        return False
        
    async def process_audio(self, audio_data: np.ndarray) -> bool:
        """
        Process audio frame for voice activity detection.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            True if speech is detected in this frame
        """
        if not self.is_initialized:
            return False
            
        try:
            current_time = time.time()
            self.stats["total_frames"] += 1
            
            # Get detection from available methods
            detections = []
            
            # WebRTC VAD
            if self.webrtc_vad:
                webrtc_result = await self._detect_webrtc(audio_data)
                if webrtc_result is not None:
                    detections.append(webrtc_result)
                    
            # Energy-based detection
            energy_result = await self._detect_energy(audio_data)
            detections.append(energy_result)
            
            # Combine detections (simple voting for now)
            raw_detection = any(detections) if detections else False
            
            # Apply temporal smoothing
            smoothed_detection = self._apply_smoothing(raw_detection)
            
            # Update state and apply minimum duration constraints
            final_detection = self._update_state(smoothed_detection, current_time)
            
            # Update statistics
            if final_detection:
                self.stats["speech_frames"] += 1
            else:
                self.stats["silence_frames"] += 1
                
            self.last_detection_time = current_time
            return final_detection
            
        except Exception as e:
            logger.error(f"VAD processing error: {e}")
            return False
            
    async def _detect_webrtc(self, audio_data: np.ndarray) -> Optional[bool]:
        """Detect speech using WebRTC VAD."""
        try:
            # WebRTC VAD expects 16-bit PCM data
            if audio_data.dtype != np.int16:
                audio_16bit = (audio_data.clip(-1, 1) * 32767).astype(np.int16)
            else:
                audio_16bit = audio_data
                
            # WebRTC VAD expects specific frame sizes (10, 20, or 30ms)
            frame_duration_ms = 20  # 20ms frames
            frame_size = int(self.sample_rate * frame_duration_ms / 1000)
            
            if len(audio_16bit) >= frame_size:
                frame = audio_16bit[:frame_size]
                return self.webrtc_vad.is_speech(frame.tobytes(), self.sample_rate)
                
        except Exception as e:
            logger.debug(f"WebRTC VAD error: {e}")
            
        return None
        
    async def _detect_energy(self, audio_data: np.ndarray) -> bool:
        """Detect speech using energy-based method."""
        if self.energy_detector:
            return await self.energy_detector.detect(audio_data)
        return False
        
    def _apply_smoothing(self, detection: bool) -> bool:
        """Apply temporal smoothing to reduce noise."""
        # Add to buffer
        self.detection_buffer.append(detection)
        
        # Keep buffer at fixed size
        if len(self.detection_buffer) > self.buffer_size:
            self.detection_buffer.pop(0)
            
        # Apply smoothing - require majority vote
        if len(self.detection_buffer) >= self.buffer_size:
            positive_count = sum(self.detection_buffer)
            threshold = self.buffer_size * self.sensitivity
            return positive_count >= threshold
            
        return detection
        
    def _update_state(self, detection: bool, current_time: float) -> bool:
        """Update speech state with minimum duration constraints."""
        if detection and not self.is_speech_active:
            # Potential start of speech
            if self.speech_start_time == 0:
                self.speech_start_time = current_time
                
            # Check if we've had speech long enough
            if current_time - self.speech_start_time >= self.min_speech_duration:
                self.is_speech_active = True
                self.silence_start_time = 0
                self.stats["speech_segments"] += 1
                logger.debug("Speech started")
                
        elif not detection and self.is_speech_active:
            # Potential end of speech
            if self.silence_start_time == 0:
                self.silence_start_time = current_time
                
            # Check if we've had silence long enough
            if current_time - self.silence_start_time >= self.min_silence_duration:
                self.is_speech_active = False
                self.speech_start_time = 0
                
                # Update average speech duration
                speech_duration = self.silence_start_time - (current_time - self.min_silence_duration)
                if self.stats["speech_segments"] > 0:
                    self.stats["avg_speech_duration"] = (
                        (self.stats["avg_speech_duration"] * (self.stats["speech_segments"] - 1) + speech_duration)
                        / self.stats["speech_segments"]
                    )
                
                logger.debug(f"Speech ended (duration: {speech_duration:.2f}s)")
                
        elif detection and self.is_speech_active:
            # Continue speech - reset silence timer
            self.silence_start_time = 0
            
        elif not detection and not self.is_speech_active:
            # Continue silence - reset speech timer
            self.speech_start_time = 0
            
        return self.is_speech_active
        
    async def stop(self):
        """Stop VAD processing."""
        self.is_initialized = False
        self.webrtc_vad = None
        logger.info("VAD stopped")
        
    def set_sensitivity(self, sensitivity: float):
        """
        Set VAD sensitivity.
        
        Args:
            sensitivity: Value between 0.0 (less sensitive) and 1.0 (more sensitive)
        """
        self.sensitivity = max(0.0, min(1.0, sensitivity))
        
        # Adjust WebRTC VAD mode based on sensitivity
        if self.webrtc_vad:
            if sensitivity < 0.3:
                mode = 0  # Least aggressive
            elif sensitivity < 0.6:
                mode = 1
            elif sensitivity < 0.8:
                mode = 2
            else:
                mode = 3  # Most aggressive
                
            self.webrtc_vad.set_mode(mode)
            
        logger.info(f"VAD sensitivity set to {sensitivity:.2f}")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get VAD statistics."""
        total_frames = self.stats["total_frames"]
        speech_ratio = self.stats["speech_frames"] / total_frames if total_frames > 0 else 0
        
        return {
            "is_initialized": self.is_initialized,
            "is_speech_active": self.is_speech_active,
            "sensitivity": self.sensitivity,
            "speech_ratio": speech_ratio,
            "has_webrtc": self.webrtc_vad is not None,
            **self.stats
        }


class EnergyVAD:
    """
    Energy-based Voice Activity Detection.
    
    Simple but effective fallback VAD using audio energy levels
    and spectral characteristics.
    """
    
    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        
        # Energy thresholds (will be adaptive)
        self.energy_threshold = 0.01
        self.spectral_threshold = 0.5
        
        # Adaptive threshold tracking
        self.energy_history = []
        self.history_size = 100
        self.noise_floor = 0.001
        
        # Zero crossing rate for basic spectral analysis
        self.zcr_threshold = 0.1
        
    async def detect(self, audio_data: np.ndarray) -> bool:
        """
        Detect speech using energy and spectral features.
        
        Args:
            audio_data: Audio data
            
        Returns:
            True if speech detected
        """
        try:
            # Calculate RMS energy
            energy = np.sqrt(np.mean(audio_data.astype(float) ** 2))
            
            # Update adaptive threshold
            self._update_adaptive_threshold(energy)
            
            # Energy-based detection
            energy_detection = energy > self.energy_threshold
            
            # Zero crossing rate (simple spectral feature)
            zcr = self._calculate_zcr(audio_data)
            spectral_detection = zcr > self.zcr_threshold
            
            # Combine detections
            return energy_detection and spectral_detection
            
        except Exception as e:
            logger.error(f"Energy VAD error: {e}")
            return False
            
    def _update_adaptive_threshold(self, energy: float):
        """Update adaptive energy threshold based on recent history."""
        self.energy_history.append(energy)
        
        if len(self.energy_history) > self.history_size:
            self.energy_history.pop(0)
            
        if len(self.energy_history) >= 10:
            # Use percentile-based threshold
            sorted_energies = sorted(self.energy_history)
            noise_estimate = sorted_energies[len(sorted_energies) // 4]  # 25th percentile
            self.noise_floor = max(noise_estimate, 0.001)
            self.energy_threshold = self.noise_floor * 3.0  # 3x noise floor
            
    def _calculate_zcr(self, audio_data: np.ndarray) -> float:
        """Calculate zero crossing rate."""
        try:
            if len(audio_data) < 2:
                return 0.0
                
            # Count zero crossings
            crossings = np.sum(np.diff(np.sign(audio_data)) != 0)
            
            # Normalize by frame length
            zcr = crossings / len(audio_data)
            
            return zcr
            
        except Exception:
            return 0.0
