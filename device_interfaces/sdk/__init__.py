"""
BUDDY Device Interface SDK

Universal SDK for connecting any device/platform to BUDDY Core.
Provides standardized patterns for:
- WebSocket communication
- Event handling
- Offline capabilities
- State synchronization
- Voice integration

Supported Platforms:
- Desktop (Electron/React)
- Mobile (Flutter)
- Web Browser (JavaScript)
- Smart Watch (WearOS/watchOS)
- Smart TV (Android TV)
- Car Systems (Android Auto/CarPlay)
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
import aiohttp

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    WATCH = "watch"
    TV = "tv"
    CAR = "car"
    BROWSER = "browser"
    IOT = "iot"

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

@dataclass
class DeviceCapabilities:
    """Device capabilities configuration"""
    voice_input: bool = False
    voice_output: bool = False
    camera: bool = False
    location: bool = False
    notifications: bool = True
    file_access: bool = False
    network: bool = True
    sensors: bool = False
    display: bool = True
    touch: bool = False

@dataclass
class Message:
    """Standard message format for device communication"""
    type: str
    data: Dict[str, Any]
    timestamp: float = None
    message_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        data = json.loads(json_str)
        return cls(**data)

class BuddyConnector:
    """
    Universal BUDDY connector for any device platform
    
    Features:
    - Auto-reconnecting WebSocket connection
    - Offline message queuing
    - Event-driven architecture
    - Platform-agnostic interface
    """
    
    def __init__(self, 
                 device_id: str,
                 device_type: DeviceType,
                 device_name: str,
                 capabilities: DeviceCapabilities,
                 user_id: str = None,
                 core_url: str = "ws://localhost:8082",
                 auto_reconnect: bool = True,
                 max_reconnect_attempts: int = 10):
        
        self.device_id = device_id
        self.device_type = device_type
        self.device_name = device_name
        self.capabilities = capabilities
        self.user_id = user_id
        self.core_url = core_url
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # Connection state
        self.connection_state = ConnectionState.DISCONNECTED
        self.websocket = None
        self.session_id = None
        self.reconnect_attempts = 0
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Offline message queue
        self.offline_queue: List[Message] = []
        self.max_offline_messages = 100
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'reconnections': 0,
            'errors': 0,
            'uptime_start': time.time()
        }
    
    async def connect(self) -> bool:
        """Connect to BUDDY Core"""
        if self.connection_state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return True
        
        self.connection_state = ConnectionState.CONNECTING
        logger.info(f"Connecting to BUDDY Core: {self.core_url}")
        
        try:
            # First register the device via REST API
            await self._register_device()
            
            # Then establish WebSocket connection
            ws_url = f"{self.core_url.replace('http', 'ws')}/ws"
            query_params = f"?device_id={self.device_id}&user_id={self.user_id or 'anonymous'}"
            
            self.websocket = await websockets.connect(f"{ws_url}{query_params}")
            self.connection_state = ConnectionState.CONNECTED
            self.reconnect_attempts = 0
            
            logger.info(f"Connected to BUDDY Core")
            
            # Start message handler
            asyncio.create_task(self._message_handler())
            
            # Send any queued offline messages
            await self._flush_offline_queue()
            
            # Notify connection established
            await self._emit_event('connection.established', {
                'device_id': self.device_id,
                'session_id': self.session_id
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.connection_state = ConnectionState.ERROR
            self.stats['errors'] += 1
            
            if self.auto_reconnect:
                await self._schedule_reconnect()
            
            return False
    
    async def disconnect(self):
        """Disconnect from BUDDY Core"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.connection_state = ConnectionState.DISCONNECTED
        logger.info("Disconnected from BUDDY Core")
        
        await self._emit_event('connection.closed', {
            'device_id': self.device_id
        })
    
    async def send_message(self, text: str, context: Dict[str, Any] = None) -> bool:
        """Send a chat message to BUDDY"""
        message = Message(
            type='message',
            data={
                'text': text,
                'context': context or {},
                'session_id': self.session_id
            }
        )
        return await self._send_message(message)
    
    async def send_voice_start(self) -> bool:
        """Notify BUDDY that voice input started"""
        message = Message(
            type='voice_start',
            data={'device_id': self.device_id}
        )
        return await self._send_message(message)
    
    async def send_voice_stop(self) -> bool:
        """Notify BUDDY that voice input stopped"""
        message = Message(
            type='voice_stop',
            data={'device_id': self.device_id}
        )
        return await self._send_message(message)
    
    async def send_voice_data(self, audio_data: str) -> bool:
        """Send voice audio data for ASR"""
        message = Message(
            type='voice_data',
            data={
                'audio_data': audio_data,
                'device_id': self.device_id
            }
        )
        return await self._send_message(message)
    
    async def create_reminder(self, title: str, scheduled_time: float, 
                            priority: str = "normal") -> bool:
        """Create a reminder"""
        if not self.user_id:
            logger.error("Cannot create reminder without user_id")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.core_url.replace('ws', 'http')}/api/reminders"
                params = {
                    'user_id': self.user_id,
                    'device_id': self.device_id
                }
                data = {
                    'title': title,
                    'scheduled_time': scheduled_time,
                    'priority': priority
                }
                
                async with session.post(url, params=params, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        await self._emit_event('reminder.created', result)
                        return True
                    else:
                        logger.error(f"Failed to create reminder: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            return False
    
    async def _send_message(self, message: Message) -> bool:
        """Internal method to send a message"""
        if self.connection_state != ConnectionState.CONNECTED:
            # Queue message for later if offline
            if len(self.offline_queue) < self.max_offline_messages:
                self.offline_queue.append(message)
                logger.debug(f"Queued message for offline delivery: {message.type}")
            return False
        
        try:
            await self.websocket.send(message.to_json())
            self.stats['messages_sent'] += 1
            logger.debug(f"Sent message: {message.type}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.stats['errors'] += 1
            
            # Try to reconnect
            if self.auto_reconnect:
                await self._schedule_reconnect()
            
            return False
    
    async def _message_handler(self):
        """Handle incoming messages from BUDDY Core"""
        try:
            async for raw_message in self.websocket:
                try:
                    message_data = json.loads(raw_message)
                    message = Message(**message_data)
                    
                    self.stats['messages_received'] += 1
                    logger.debug(f"Received message: {message.type}")
                    
                    # Handle specific message types
                    await self._handle_message(message)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.connection_state = ConnectionState.DISCONNECTED
            
            if self.auto_reconnect:
                await self._schedule_reconnect()
                
        except Exception as e:
            logger.error(f"Message handler error: {e}")
            self.connection_state = ConnectionState.ERROR
            self.stats['errors'] += 1
    
    async def _handle_message(self, message: Message):
        """Handle specific incoming message types"""
        message_type = message.type
        
        if message_type == 'welcome':
            self.session_id = message.data.get('connection_id')
            await self._emit_event('welcome', message.data)
        
        elif message_type == 'message':
            # Chat response from BUDDY
            await self._emit_event('message.received', {
                'content': message.data.get('content', ''),
                'session_id': message.data.get('session_id'),
                'timestamp': message.timestamp
            })
        
        elif message_type == 'notification':
            # System notification
            await self._emit_event('notification', {
                'title': message.data.get('title', ''),
                'message': message.data.get('message', ''),
                'priority': message.data.get('priority', 'normal'),
                'timestamp': message.timestamp
            })
        
        elif message_type == 'reminder':
            # Reminder alert
            await self._emit_event('reminder.alert', {
                'title': message.data.get('title', ''),
                'reminder_id': message.data.get('reminder_id', ''),
                'priority': message.data.get('priority', 'normal'),
                'timestamp': message.timestamp
            })
        
        elif message_type == 'asr_result':
            # Speech recognition result
            await self._emit_event('voice.asr.result', {
                'text': message.data.get('text', ''),
                'confidence': message.data.get('confidence', 0.0),
                'timestamp': message.timestamp
            })
        
        elif message_type == 'tts_result':
            # Text-to-speech result
            await self._emit_event('voice.tts.result', {
                'audio_url': message.data.get('audio_url', ''),
                'text': message.data.get('text', ''),
                'timestamp': message.timestamp
            })
        
        elif message_type == 'pong':
            # Heartbeat response
            await self._emit_event('heartbeat', message.data)
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def _register_device(self):
        """Register device with BUDDY Core"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.core_url.replace('ws', 'http')}/api/devices/register"
                data = {
                    'device_id': self.device_id,
                    'device_type': self.device_type.value,
                    'name': self.device_name,
                    'capabilities': [cap for cap, enabled in asdict(self.capabilities).items() if enabled],
                    'user_id': self.user_id or 'anonymous'
                }
                
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info("Device registered successfully")
                    else:
                        logger.warning(f"Device registration failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
    
    async def _schedule_reconnect(self):
        """Schedule automatic reconnection"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            self.connection_state = ConnectionState.ERROR
            return
        
        self.reconnect_attempts += 1
        self.connection_state = ConnectionState.RECONNECTING
        
        # Exponential backoff
        delay = min(2 ** self.reconnect_attempts, 60)
        logger.info(f"Reconnecting in {delay} seconds (attempt {self.reconnect_attempts})")
        
        await asyncio.sleep(delay)
        await self.connect()
        
        if self.connection_state == ConnectionState.CONNECTED:
            self.stats['reconnections'] += 1
    
    async def _flush_offline_queue(self):
        """Send queued messages after reconnection"""
        if not self.offline_queue:
            return
        
        logger.info(f"Sending {len(self.offline_queue)} queued messages")
        
        for message in self.offline_queue.copy():
            success = await self._send_message(message)
            if success:
                self.offline_queue.remove(message)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to registered handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Event handler error for {event_type}: {e}")
    
    def on(self, event_type: str, handler: Callable):
        """Register an event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event: {event_type}")
    
    def off(self, event_type: str, handler: Callable):
        """Unregister an event handler"""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    async def ping(self):
        """Send a heartbeat ping"""
        message = Message(
            type='ping',
            data={'timestamp': time.time()}
        )
        await self._send_message(message)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        uptime = time.time() - self.stats['uptime_start']
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'connection_state': self.connection_state.value,
            'offline_queue_size': len(self.offline_queue),
            'reconnect_attempts': self.reconnect_attempts
        }
    
    def is_connected(self) -> bool:
        """Check if connected to BUDDY Core"""
        return self.connection_state == ConnectionState.CONNECTED

# Convenience factory functions
def create_desktop_connector(device_id: str, user_id: str = None, **kwargs) -> BuddyConnector:
    """Create a connector for desktop applications"""
    capabilities = DeviceCapabilities(
        voice_input=True,
        voice_output=True,
        camera=True,
        file_access=True,
        display=True,
        touch=False
    )
    return BuddyConnector(
        device_id=device_id,
        device_type=DeviceType.DESKTOP,
        device_name=f"Desktop-{device_id[:8]}",
        capabilities=capabilities,
        user_id=user_id,
        **kwargs
    )

def create_mobile_connector(device_id: str, user_id: str = None, **kwargs) -> BuddyConnector:
    """Create a connector for mobile applications"""
    capabilities = DeviceCapabilities(
        voice_input=True,
        voice_output=True,
        camera=True,
        location=True,
        notifications=True,
        display=True,
        touch=True,
        sensors=True
    )
    return BuddyConnector(
        device_id=device_id,
        device_type=DeviceType.MOBILE,
        device_name=f"Mobile-{device_id[:8]}",
        capabilities=capabilities,
        user_id=user_id,
        **kwargs
    )

def create_watch_connector(device_id: str, user_id: str = None, **kwargs) -> BuddyConnector:
    """Create a connector for smartwatch applications"""
    capabilities = DeviceCapabilities(
        voice_input=True,
        voice_output=True,
        notifications=True,
        display=True,
        touch=True,
        sensors=True
    )
    return BuddyConnector(
        device_id=device_id,
        device_type=DeviceType.WATCH,
        device_name=f"Watch-{device_id[:8]}",
        capabilities=capabilities,
        user_id=user_id,
        **kwargs
    )

def create_tv_connector(device_id: str, user_id: str = None, **kwargs) -> BuddyConnector:
    """Create a connector for smart TV applications"""
    capabilities = DeviceCapabilities(
        voice_input=True,
        voice_output=True,
        display=True,
        notifications=True
    )
    return BuddyConnector(
        device_id=device_id,
        device_type=DeviceType.TV,
        device_name=f"TV-{device_id[:8]}",
        capabilities=capabilities,
        user_id=user_id,
        **kwargs
    )
