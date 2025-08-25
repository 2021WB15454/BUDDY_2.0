"""
BUDDY Wake Word Detection

Handles wake word detection using various models including Porcupine,
Precise, or custom models. Supports multiple wake words and confidence
thresholding with false positive mitigation.
"""

import asyncio
import logging
import numpy as np
from typing import Optional, Dict, Any, List
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """
    Wake word detection system for BUDDY.
    
    Supports multiple wake word models and provides confidence scoring
    with false positive mitigation strategies.
    """
    
    def __init__(self, audio_config, model_name: str = "hey_buddy"):
        self.audio_config = audio_config
        self.model_name = model_name
        self.model = None
        self.is_initialized = False
        
        # Configuration
        self.confidence_threshold = 0.7
        self.confirmation_threshold = 0.85  # Higher threshold for confirmation
        self.false_positive_timeout = 2.0  # Seconds to wait before next detection
        
        # State tracking
        self.last_detection_time = 0
        self.last_confidence = 0.0
        self.detection_buffer = []  # For averaging multiple detections
        self.buffer_size = 3
        
        # Statistics
        self.stats = {
            "total_detections": 0,
            "confirmed_detections": 0,
            "false_positives": 0,
            "avg_confidence": 0.0
        }
        
    async def initialize(self) -> bool:
        """Initialize the wake word detection model."""
        try:
            # Try to load Porcupine first (preferred)
            if await self._init_porcupine():
                logger.info(f"Initialized Porcupine wake word detector: {self.model_name}")
                return True
                
            # Fallback to Precise
            if await self._init_precise():
                logger.info(f"Initialized Precise wake word detector: {self.model_name}")
                return True
                
            # Fallback to simple pattern matching
            if await self._init_simple():
                logger.info(f"Initialized simple wake word detector: {self.model_name}")
                return True
                
            logger.error("Failed to initialize any wake word detection model")
            return False
            
        except Exception as e:
            logger.error(f"Wake word detector initialization error: {e}")
            return False
            
    async def _init_porcupine(self) -> bool:
        """Initialize Porcupine wake word detection."""
        try:
            import pvporcupine
            
            # Try to create Porcupine instance
            access_key = None  # Would be loaded from config in real implementation
            keyword_paths = []  # Would be loaded from models directory
            
            if access_key and keyword_paths:
                self.model = pvporcupine.create(
                    access_key=access_key,
                    keyword_paths=keyword_paths
                )
                self.model_type = "porcupine"
                self.is_initialized = True
                return True
                
        except ImportError:
            logger.debug("Porcupine not available")
        except Exception as e:
            logger.debug(f"Porcupine initialization failed: {e}")
            
        return False
        
    async def _init_precise(self) -> bool:
        """Initialize Precise wake word detection."""
        try:
            # Precise would be loaded here
            # For now, this is a placeholder
            logger.debug("Precise wake word detection not implemented yet")
            return False
            
        except Exception as e:
            logger.debug(f"Precise initialization failed: {e}")
            return False
            
    async def _init_simple(self) -> bool:
        """Initialize simple pattern-based wake word detection."""
        try:
            # Simple energy-based detection as fallback
            self.model = SimpleWakeWordDetector(
                target_phrase=self.model_name,
                sample_rate=self.audio_config.sample_rate
            )
            self.model_type = "simple"
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Simple wake word initialization failed: {e}")
            return False
            
    async def process_audio(self, audio_data: np.ndarray) -> bool:
        """
        Process audio data for wake word detection.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            True if wake word detected with sufficient confidence
        """
        if not self.is_initialized:
            return False
            
        try:
            # Check false positive timeout
            current_time = time.time()
            if current_time - self.last_detection_time < self.false_positive_timeout:
                return False
                
            # Process with appropriate model
            confidence = 0.0
            
            if self.model_type == "porcupine":
                confidence = await self._process_porcupine(audio_data)
            elif self.model_type == "precise":
                confidence = await self._process_precise(audio_data)
            elif self.model_type == "simple":
                confidence = await self._process_simple(audio_data)
                
            self.last_confidence = confidence
            
            # Apply confidence thresholding with buffering
            if confidence > self.confidence_threshold:
                self.detection_buffer.append(confidence)
                
                # Keep buffer at fixed size
                if len(self.detection_buffer) > self.buffer_size:
                    self.detection_buffer.pop(0)
                    
                # Check if we have enough confident detections
                if len(self.detection_buffer) >= self.buffer_size:
                    avg_confidence = np.mean(self.detection_buffer)
                    
                    if avg_confidence > self.confirmation_threshold:
                        self.last_detection_time = current_time
                        self.detection_buffer.clear()
                        
                        # Update statistics
                        self.stats["total_detections"] += 1
                        self.stats["confirmed_detections"] += 1
                        self.stats["avg_confidence"] = (
                            (self.stats["avg_confidence"] * (self.stats["confirmed_detections"] - 1) + avg_confidence) 
                            / self.stats["confirmed_detections"]
                        )
                        
                        logger.debug(f"Wake word detected with confidence: {avg_confidence:.3f}")
                        return True
            else:
                # Clear buffer on low confidence
                if self.detection_buffer:
                    self.detection_buffer.clear()
                    
            return False
            
        except Exception as e:
            logger.error(f"Wake word processing error: {e}")
            return False
            
    async def _process_porcupine(self, audio_data: np.ndarray) -> float:
        """Process audio with Porcupine model."""
        try:
            # Convert to int16 if needed
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
                
            # Porcupine expects specific frame length
            frame_length = self.model.frame_length
            
            if len(audio_data) >= frame_length:
                result = self.model.process(audio_data[:frame_length])
                return 1.0 if result >= 0 else 0.0  # Porcupine returns keyword index or -1
            
        except Exception as e:
            logger.error(f"Porcupine processing error: {e}")
            
        return 0.0
        
    async def _process_precise(self, audio_data: np.ndarray) -> float:
        """Process audio with Precise model."""
        # Placeholder for Precise implementation
        return 0.0
        
    async def _process_simple(self, audio_data: np.ndarray) -> float:
        """Process audio with simple detector."""
        if self.model:
            return await self.model.detect(audio_data)
        return 0.0
        
    async def stop(self):
        """Stop the wake word detector."""
        if self.model and self.model_type == "porcupine":
            try:
                self.model.delete()
            except:
                pass
                
        self.is_initialized = False
        logger.info("Wake word detector stopped")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics."""
        return {
            "model_type": getattr(self, "model_type", "none"),
            "is_initialized": self.is_initialized,
            "confidence_threshold": self.confidence_threshold,
            "last_confidence": self.last_confidence,
            **self.stats
        }
        
    def set_sensitivity(self, sensitivity: float):
        """
        Set detection sensitivity.
        
        Args:
            sensitivity: Value between 0.0 (less sensitive) and 1.0 (more sensitive)
        """
        # Adjust thresholds based on sensitivity
        base_threshold = 0.5
        sensitivity_range = 0.4
        
        self.confidence_threshold = base_threshold + (1.0 - sensitivity) * sensitivity_range
        self.confirmation_threshold = self.confidence_threshold + 0.15
        
        logger.info(f"Wake word sensitivity set to {sensitivity:.2f} "
                   f"(threshold: {self.confidence_threshold:.2f})")


class SimpleWakeWordDetector:
    """
    Simple energy and pattern-based wake word detection.
    
    Used as a fallback when sophisticated models aren't available.
    """
    
    def __init__(self, target_phrase: str, sample_rate: int):
        self.target_phrase = target_phrase.lower()
        self.sample_rate = sample_rate
        
        # Simple energy-based detection parameters
        self.energy_threshold = 0.01
        self.pattern_length = int(sample_rate * 2.0)  # 2 seconds
        self.energy_buffer = []
        self.max_buffer_size = 10
        
    async def detect(self, audio_data: np.ndarray) -> float:
        """
        Detect wake word using simple energy patterns.
        
        Args:
            audio_data: Audio data
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        try:
            # Calculate RMS energy
            energy = np.sqrt(np.mean(audio_data.astype(float) ** 2))
            
            # Add to energy buffer
            self.energy_buffer.append(energy)
            if len(self.energy_buffer) > self.max_buffer_size:
                self.energy_buffer.pop(0)
                
            # Check for energy pattern that could indicate speech
            if len(self.energy_buffer) >= 3:
                recent_energy = np.mean(self.energy_buffer[-3:])
                avg_energy = np.mean(self.energy_buffer)
                
                # Simple heuristic: recent energy is significantly higher than average
                if recent_energy > self.energy_threshold and recent_energy > avg_energy * 2.0:
                    # Return a confidence based on energy ratio
                    confidence = min(recent_energy / (avg_energy * 3.0), 1.0)
                    return confidence * 0.8  # Cap at 0.8 since this is a simple detector
                    
            return 0.0
            
        except Exception as e:
            logger.error(f"Simple wake word detection error: {e}")
            return 0.0
