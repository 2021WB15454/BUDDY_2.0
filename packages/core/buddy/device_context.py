"""
BUDDY Device Context Manager

Manages device-specific information and adapts conversation flow based on device capabilities.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    MOBILE = "mobile"
    DESKTOP = "desktop"
    TABLET = "tablet"
    WATCH = "watch"
    TV = "tv"
    CAR = "car"
    SMART_SPEAKER = "smart_speaker"
    UNKNOWN = "unknown"


@dataclass
class DeviceCapabilities:
    """Device capabilities information"""
    has_screen: bool = True
    has_keyboard: bool = True
    has_microphone: bool = True
    has_speakers: bool = True
    has_camera: bool = False
    has_touch: bool = False
    has_voice_input: bool = True
    has_haptic: bool = False
    screen_size: str = "medium"  # small, medium, large
    input_methods: list = None
    preferred_interaction_mode: str = "text"  # text, voice, mixed
    supports_rich_content: bool = True
    supports_notifications: bool = True
    
    def __post_init__(self):
        if self.input_methods is None:
            self.input_methods = ["text", "voice"] if self.has_keyboard else ["voice"]


class DeviceContextManager:
    """Manages device context and capabilities"""
    
    def __init__(self):
        self.device_profiles = self._initialize_device_profiles()
        self.active_devices = {}
    
    def _initialize_device_profiles(self) -> Dict[DeviceType, DeviceCapabilities]:
        """Initialize standard device capability profiles"""
        return {
            DeviceType.MOBILE: DeviceCapabilities(
                has_screen=True,
                has_keyboard=True,  # Virtual keyboard
                has_microphone=True,
                has_speakers=True,
                has_camera=True,
                has_touch=True,
                has_voice_input=True,
                has_haptic=True,
                screen_size="small",
                input_methods=["text", "voice", "touch"],
                preferred_interaction_mode="mixed",
                supports_rich_content=True,
                supports_notifications=True
            ),
            
            DeviceType.DESKTOP: DeviceCapabilities(
                has_screen=True,
                has_keyboard=True,
                has_microphone=True,
                has_speakers=True,
                has_camera=True,
                has_touch=False,
                has_voice_input=True,
                has_haptic=False,
                screen_size="large",
                input_methods=["text", "voice", "mouse"],
                preferred_interaction_mode="text",
                supports_rich_content=True,
                supports_notifications=True
            ),
            
            DeviceType.WATCH: DeviceCapabilities(
                has_screen=True,
                has_keyboard=False,
                has_microphone=True,
                has_speakers=True,
                has_camera=False,
                has_touch=True,
                has_voice_input=True,
                has_haptic=True,
                screen_size="small",
                input_methods=["voice", "touch"],
                preferred_interaction_mode="voice",
                supports_rich_content=False,
                supports_notifications=True
            ),
            
            DeviceType.TV: DeviceCapabilities(
                has_screen=True,
                has_keyboard=False,
                has_microphone=True,
                has_speakers=True,
                has_camera=False,
                has_touch=False,
                has_voice_input=True,
                has_haptic=False,
                screen_size="large",
                input_methods=["voice", "remote"],
                preferred_interaction_mode="voice",
                supports_rich_content=True,
                supports_notifications=False
            ),
            
            DeviceType.CAR: DeviceCapabilities(
                has_screen=True,
                has_keyboard=False,
                has_microphone=True,
                has_speakers=True,
                has_camera=False,
                has_touch=False,
                has_voice_input=True,
                has_haptic=False,
                screen_size="medium",
                input_methods=["voice"],
                preferred_interaction_mode="voice",
                supports_rich_content=False,
                supports_notifications=True
            ),
            
            DeviceType.SMART_SPEAKER: DeviceCapabilities(
                has_screen=False,
                has_keyboard=False,
                has_microphone=True,
                has_speakers=True,
                has_camera=False,
                has_touch=False,
                has_voice_input=True,
                has_haptic=False,
                screen_size="none",
                input_methods=["voice"],
                preferred_interaction_mode="voice",
                supports_rich_content=False,
                supports_notifications=True
            ),
            
            DeviceType.UNKNOWN: DeviceCapabilities(
                has_screen=True,
                has_keyboard=True,
                has_microphone=True,
                has_speakers=True,
                has_camera=False,
                has_touch=False,
                has_voice_input=True,
                has_haptic=False,
                screen_size="medium",
                input_methods=["text", "voice"],
                preferred_interaction_mode="text",
                supports_rich_content=True,
                supports_notifications=True
            )
        }
    
    def detect_device_type(self, user_agent: str = "", device_info: Dict = None) -> DeviceType:
        """Detect device type from user agent or device info"""
        if device_info:
            device_type = device_info.get('type', '').lower()
            if device_type in ['mobile', 'phone', 'smartphone']:
                return DeviceType.MOBILE
            elif device_type in ['desktop', 'computer', 'pc']:
                return DeviceType.DESKTOP
            elif device_type in ['tablet', 'ipad']:
                return DeviceType.TABLET
            elif device_type in ['watch', 'smartwatch']:
                return DeviceType.WATCH
            elif device_type in ['tv', 'television', 'smart_tv']:
                return DeviceType.TV
            elif device_type in ['car', 'automotive', 'vehicle']:
                return DeviceType.CAR
            elif device_type in ['speaker', 'smart_speaker', 'echo', 'alexa']:
                return DeviceType.SMART_SPEAKER
        
        # Fallback to user agent analysis
        user_agent_lower = user_agent.lower()
        if any(mobile_indicator in user_agent_lower for mobile_indicator in ['mobile', 'iphone', 'android']):
            return DeviceType.MOBILE
        elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
            return DeviceType.TABLET
        elif any(desktop_indicator in user_agent_lower for desktop_indicator in ['windows', 'mac', 'linux']):
            return DeviceType.DESKTOP
        
        return DeviceType.UNKNOWN
    
    def get_device_capabilities(self, device_type: DeviceType) -> DeviceCapabilities:
        """Get capabilities for a specific device type"""
        return self.device_profiles.get(device_type, self.device_profiles[DeviceType.UNKNOWN])
    
    def create_device_context(self, device_id: str, device_type: DeviceType = None, 
                            user_agent: str = "", device_info: Dict = None, 
                            location: str = None) -> Dict[str, Any]:
        """Create comprehensive device context"""
        
        # Auto-detect device type if not provided
        if not device_type:
            device_type = self.detect_device_type(user_agent, device_info)
        
        capabilities = self.get_device_capabilities(device_type)
        
        context = {
            'device_id': device_id,
            'device_type': device_type.value,
            'capabilities': {
                'has_screen': capabilities.has_screen,
                'has_keyboard': capabilities.has_keyboard,
                'has_microphone': capabilities.has_microphone,
                'has_speakers': capabilities.has_speakers,
                'has_camera': capabilities.has_camera,
                'has_touch': capabilities.has_touch,
                'has_voice_input': capabilities.has_voice_input,
                'has_haptic': capabilities.has_haptic,
                'screen_size': capabilities.screen_size,
                'input_methods': capabilities.input_methods,
                'preferred_interaction_mode': capabilities.preferred_interaction_mode,
                'supports_rich_content': capabilities.supports_rich_content,
                'supports_notifications': capabilities.supports_notifications
            },
            'user_agent': user_agent,
            'location': location,
            'optimization_hints': self._get_optimization_hints(device_type, capabilities)
        }
        
        # Store active device
        self.active_devices[device_id] = context
        
        return context
    
    def _get_optimization_hints(self, device_type: DeviceType, capabilities: DeviceCapabilities) -> Dict[str, Any]:
        """Get optimization hints for the device"""
        hints = {
            'response_length': 'medium',
            'formatting': 'standard',
            'interaction_style': 'conversational',
            'content_density': 'medium'
        }
        
        if device_type == DeviceType.WATCH:
            hints.update({
                'response_length': 'very_short',
                'formatting': 'minimal',
                'interaction_style': 'quick',
                'content_density': 'low',
                'prefer_voice': True,
                'use_haptic': True
            })
        elif device_type == DeviceType.SMART_SPEAKER:
            hints.update({
                'response_length': 'short',
                'formatting': 'audio_only',
                'interaction_style': 'voice_focused',
                'content_density': 'low',
                'audio_only': True
            })
        elif device_type == DeviceType.CAR:
            hints.update({
                'response_length': 'short',
                'formatting': 'audio_focused',
                'interaction_style': 'safety_first',
                'content_density': 'low',
                'hands_free': True,
                'safety_filtered': True
            })
        elif device_type == DeviceType.TV:
            hints.update({
                'response_length': 'medium',
                'formatting': 'visual_rich',
                'interaction_style': 'leisurely',
                'content_density': 'medium',
                'large_text': True,
                'visual_elements': True
            })
        elif device_type == DeviceType.DESKTOP:
            hints.update({
                'response_length': 'detailed',
                'formatting': 'rich',
                'interaction_style': 'comprehensive',
                'content_density': 'high',
                'detailed_responses': True,
                'supports_markdown': True
            })
        
        return hints
    
    def adapt_response_for_device(self, response: str, device_context: Dict[str, Any]) -> str:
        """Adapt response text based on device capabilities"""
        hints = device_context.get('optimization_hints', {})
        
        # Adjust response length
        if hints.get('response_length') == 'very_short' and len(response) > 50:
            # Truncate for very small screens
            response = response[:47] + "..."
        elif hints.get('response_length') == 'short' and len(response) > 150:
            # Truncate for voice-only devices
            response = response[:147] + "..."
        
        # Remove formatting for audio-only devices
        if hints.get('audio_only'):
            # Remove markdown and other formatting
            response = response.replace('*', '').replace('_', '').replace('#', '')
        
        # Safety filtering for automotive
        if hints.get('safety_filtered'):
            # Remove any content that might be distracting while driving
            safety_keywords = ['urgent', 'emergency', 'immediately', 'now']
            for keyword in safety_keywords:
                if keyword in response.lower():
                    response = response.replace(keyword, 'when convenient')
        
        return response
    
    def get_device_context(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get stored device context"""
        return self.active_devices.get(device_id)
    
    def update_device_context(self, device_id: str, updates: Dict[str, Any]) -> bool:
        """Update device context with new information"""
        if device_id in self.active_devices:
            self.active_devices[device_id].update(updates)
            return True
        return False
