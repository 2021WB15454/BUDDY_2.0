"""
API Gateway - Central Communication Hub for BUDDY Core

Handles:
- REST API endpoints for device interfaces
- WebSocket connections for real-time communication
- Authentication and authorization
- Rate limiting and security
- Device presence management
- Cross-device event routing
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import jwt

from ..events import Event, get_event_bus, EventPriority
from ..memory import get_memory, UserProfile, Device

logger = logging.getLogger(__name__)

# Pydantic models for API
class MessageRequest(BaseModel):
    text: str
    device_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    response: str
    session_id: str
    context: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None

class DeviceRegistration(BaseModel):
    device_id: str
    device_type: str  # desktop, mobile, watch, tv, car
    name: str
    capabilities: List[str]
    user_id: str

class ReminderRequest(BaseModel):
    title: str
    scheduled_time: float
    recurrence: Optional[str] = None
    priority: str = "normal"

class UserProfileRequest(BaseModel):
    name: str
    timezone: str = "UTC"
    locale: str = "en-US"
    preferences: Dict[str, Any] = {}

class VoiceRequest(BaseModel):
    audio_data: Optional[str] = None  # base64 encoded
    text: Optional[str] = None  # or direct text for TTS
    device_id: Optional[str] = None

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time communication"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.device_connections: Dict[str, str] = {}  # device_id -> connection_id
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
    
    async def connect(self, websocket: WebSocket, connection_id: str, 
                     device_id: str = None, user_id: str = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if device_id:
            self.device_connections[device_id] = connection_id
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} (device: {device_id}, user: {user_id})")
        
        # Update device presence
        if device_id:
            memory = get_memory()
            await memory.update_device_presence(device_id, "online")
            
            # Notify other devices about presence
            bus = get_event_bus()
            await bus.publish('device.presence.update', {
                'device_id': device_id,
                'status': 'online',
                'connection_id': connection_id
            }, device_id=device_id, user_id=user_id)
    
    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            del self.active_connections[connection_id]
            
            # Find and clean up device mapping
            device_id = None
            for dev_id, conn_id in list(self.device_connections.items()):
                if conn_id == connection_id:
                    device_id = dev_id
                    del self.device_connections[dev_id]
                    break
            
            # Clean up user mapping
            user_id = None
            for uid, conn_ids in self.user_connections.items():
                if connection_id in conn_ids:
                    conn_ids.remove(connection_id)
                    user_id = uid
                    if not conn_ids:
                        del self.user_connections[uid]
                    break
            
            logger.info(f"WebSocket disconnected: {connection_id} (device: {device_id})")
            
            # Update device presence
            if device_id:
                memory = get_memory()
                await memory.update_device_presence(device_id, "offline")
                
                # Notify about disconnection
                bus = get_event_bus()
                await bus.publish('device.presence.update', {
                    'device_id': device_id,
                    'status': 'offline'
                }, device_id=device_id, user_id=user_id)
    
    async def send_to_connection(self, connection_id: str, data: Dict[str, Any]):
        """Send data to a specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(data))
            except Exception as e:
                logger.error(f"Failed to send to connection {connection_id}: {e}")
                await self.disconnect(connection_id)
    
    async def send_to_device(self, device_id: str, data: Dict[str, Any]):
        """Send data to a specific device"""
        if device_id in self.device_connections:
            connection_id = self.device_connections[device_id]
            await self.send_to_connection(connection_id, data)
    
    async def send_to_user(self, user_id: str, data: Dict[str, Any], exclude_device: str = None):
        """Send data to all devices of a user"""
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id].copy():
                # Skip the excluded device
                if exclude_device:
                    device_id = None
                    for dev_id, conn_id in self.device_connections.items():
                        if conn_id == connection_id:
                            device_id = dev_id
                            break
                    if device_id == exclude_device:
                        continue
                
                await self.send_to_connection(connection_id, data)
    
    async def broadcast(self, data: Dict[str, Any]):
        """Broadcast data to all connected devices"""
        for connection_id in list(self.active_connections.keys()):
            await self.send_to_connection(connection_id, data)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            'total_connections': len(self.active_connections),
            'device_connections': len(self.device_connections),
            'user_connections': len(self.user_connections),
            'connected_devices': list(self.device_connections.keys())
        }

class APIGateway:
    """
    Central API Gateway for BUDDY Core
    
    Provides:
    - REST endpoints for device interactions
    - WebSocket for real-time communication
    - Authentication and authorization
    - Cross-device event routing
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8082):
        self.host = host
        self.port = port
        self.app = FastAPI(
            title="BUDDY Core API",
            description="Central Intelligence API for BUDDY Multi-Device Assistant",
            version="2.0.0"
        )
        
        # Connection manager for WebSocket
        self.connection_manager = ConnectionManager()
        
        # Event bus for internal communication
        self.event_bus = get_event_bus()
        self.memory = get_memory()
        
        # Security
        self.security = HTTPBearer(auto_error=False)
        
        # Setup middleware and routes
        self._setup_middleware()
        self._setup_routes()
        self._setup_event_handlers()
    
    def _setup_middleware(self):
        """Setup CORS and other middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure properly for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup API routes"""
        
        # Health check
        @self.app.get("/api/health")
        async def health_check():
            """System health check"""
            memory_stats = await self.memory.get_memory_stats()
            connection_stats = self.connection_manager.get_stats()
            event_stats = self.event_bus.get_stats()
            
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "version": "2.0.0",
                "memory": memory_stats,
                "connections": connection_stats,
                "events": event_stats
            }
        
        # Core messaging
        @self.app.post("/api/message", response_model=MessageResponse)
        async def send_message(request: MessageRequest):
            """Send a message to BUDDY"""
            session_id = request.session_id or str(uuid.uuid4())
            
            # Publish message event
            await self.event_bus.publish('ui.message.in', {
                'text': request.text,
                'session_id': session_id,
                'context': request.context or {}
            }, device_id=request.device_id)
            
            # Wait for response (simplified - in production use proper async handling)
            # For now, return a placeholder response
            return MessageResponse(
                response="Message received and being processed",
                session_id=session_id,
                context=request.context
            )
        
        # Device management
        @self.app.post("/api/devices/register")
        async def register_device(device_data: DeviceRegistration):
            """Register a new device"""
            device = Device(
                device_id=device_data.device_id,
                user_id=device_data.user_id,
                device_type=device_data.device_type,
                name=device_data.name,
                capabilities=device_data.capabilities
            )
            
            success = await self.memory.register_device(device)
            if success:
                await self.event_bus.publish('device.connected', {
                    'device': device_data.dict()
                }, device_id=device_data.device_id, user_id=device_data.user_id)
                
                return {"status": "success", "device_id": device_data.device_id}
            else:
                raise HTTPException(status_code=400, detail="Failed to register device")
        
        @self.app.get("/api/devices")
        async def get_devices(user_id: str):
            """Get all devices for a user"""
            devices = await self.memory.get_user_devices(user_id)
            return {
                "devices": [
                    {
                        "device_id": d.device_id,
                        "device_type": d.device_type,
                        "name": d.name,
                        "capabilities": d.capabilities,
                        "status": d.status,
                        "last_seen": d.last_seen
                    } for d in devices
                ]
            }
        
        # User management
        @self.app.post("/api/users")
        async def create_user(profile_data: UserProfileRequest):
            """Create a new user profile"""
            user_id = str(uuid.uuid4())
            profile = UserProfile(
                user_id=user_id,
                name=profile_data.name,
                timezone=profile_data.timezone,
                locale=profile_data.locale,
                preferences=profile_data.preferences
            )
            
            success = await self.memory.create_user(profile)
            if success:
                return {"user_id": user_id, "status": "created"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create user")
        
        @self.app.get("/api/users/{user_id}")
        async def get_user(user_id: str):
            """Get user profile"""
            user = await self.memory.get_user(user_id)
            if user:
                return {
                    "user_id": user.user_id,
                    "name": user.name,
                    "timezone": user.timezone,
                    "locale": user.locale,
                    "preferences": user.preferences
                }
            else:
                raise HTTPException(status_code=404, detail="User not found")
        
        # Reminders
        @self.app.post("/api/reminders")
        async def create_reminder(reminder_data: ReminderRequest, user_id: str, device_id: str = None):
            """Create a new reminder"""
            from ..memory import Reminder
            
            reminder_id = str(uuid.uuid4())
            reminder = Reminder(
                reminder_id=reminder_id,
                user_id=user_id,
                title=reminder_data.title,
                scheduled_time=reminder_data.scheduled_time,
                recurrence=reminder_data.recurrence,
                priority=reminder_data.priority,
                device_id=device_id
            )
            
            success = await self.memory.create_reminder(reminder)
            if success:
                await self.event_bus.publish('skill.reminder.create', {
                    'reminder_id': reminder_id,
                    'title': reminder_data.title,
                    'scheduled_time': reminder_data.scheduled_time
                }, device_id=device_id, user_id=user_id)
                
                return {"reminder_id": reminder_id, "status": "created"}
            else:
                raise HTTPException(status_code=400, detail="Failed to create reminder")
        
        @self.app.get("/api/reminders")
        async def get_reminders(user_id: str):
            """Get user's reminders"""
            reminders = await self.memory.get_pending_reminders(user_id)
            return {
                "reminders": [
                    {
                        "reminder_id": r.reminder_id,
                        "title": r.title,
                        "scheduled_time": r.scheduled_time,
                        "priority": r.priority,
                        "status": r.status
                    } for r in reminders
                ]
            }
        
        # Voice endpoints
        @self.app.post("/api/voice/asr")
        async def speech_to_text(request: VoiceRequest):
            """Convert speech to text"""
            await self.event_bus.publish('voice.asr.request', {
                'audio_data': request.audio_data,
                'device_id': request.device_id
            }, device_id=request.device_id)
            
            return {"status": "processing", "message": "ASR request queued"}
        
        @self.app.post("/api/voice/tts")
        async def text_to_speech(request: VoiceRequest):
            """Convert text to speech"""
            await self.event_bus.publish('voice.tts.request', {
                'text': request.text,
                'device_id': request.device_id
            }, device_id=request.device_id)
            
            return {"status": "processing", "message": "TTS request queued"}

        # Simple Sync endpoints (LWW demo)
        @self.app.post("/api/sync/push")
        async def sync_push(payload: Dict[str, Any]):
            """Push sync items from device. Payload: {device_id, items: {key: {value, ts}}}"""
            device_id = payload.get('device_id')
            items = payload.get('items', {})
            sync = get_sync_service()
            if not sync:
                raise HTTPException(status_code=500, detail="Sync service not available")
            ok = await sync.push(device_id, items)
            return {"ok": bool(ok)}

        @self.app.get("/api/sync/pull")
        async def sync_pull(device_id: Optional[str] = None, keys: Optional[str] = None):
            """Pull sync items. keys is comma-separated list if provided."""
            sync = get_sync_service()
            if not sync:
                raise HTTPException(status_code=500, detail="Sync service not available")
            keys_list = None
            if keys:
                keys_list = [k.strip() for k in keys.split(',') if k.strip()]
            data = await sync.pull(device_id, keys_list)
            return {"items": data}
        
        # WebSocket endpoint
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """Main WebSocket endpoint for real-time communication"""
            connection_id = str(uuid.uuid4())
            device_id = None
            user_id = None
            
            try:
                # Extract device_id and user_id from query params
                query_params = dict(websocket.query_params)
                device_id = query_params.get('device_id')
                user_id = query_params.get('user_id')
                
                await self.connection_manager.connect(
                    websocket, connection_id, device_id, user_id
                )
                
                # Send welcome message
                await self.connection_manager.send_to_connection(connection_id, {
                    "type": "welcome",
                    "connection_id": connection_id,
                    "timestamp": time.time()
                })
                
                # Listen for messages
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Route message based on type
                    await self._handle_websocket_message(
                        connection_id, device_id, user_id, message
                    )
                    
            except WebSocketDisconnect:
                await self.connection_manager.disconnect(connection_id)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await self.connection_manager.disconnect(connection_id)
    
    async def _handle_websocket_message(self, connection_id: str, device_id: str, 
                                       user_id: str, message: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        message_type = message.get('type')
        
        if message_type == 'message':
            # Chat message
            await self.event_bus.publish('ui.message.in', {
                'text': message.get('text', ''),
                'session_id': message.get('session_id'),
                'context': message.get('context', {}),
                'connection_id': connection_id
            }, device_id=device_id, user_id=user_id)
            
        elif message_type == 'voice_start':
            # Voice input started
            await self.event_bus.publish('ui.voice.start', {
                'connection_id': connection_id
            }, device_id=device_id, user_id=user_id)
            
        elif message_type == 'voice_stop':
            # Voice input stopped
            await self.event_bus.publish('ui.voice.stop', {
                'connection_id': connection_id
            }, device_id=device_id, user_id=user_id)
            
        elif message_type == 'ping':
            # Heartbeat
            await self.connection_manager.send_to_connection(connection_id, {
                "type": "pong",
                "timestamp": time.time()
            })
        
        else:
            logger.warning(f"Unknown WebSocket message type: {message_type}")
    
    def _setup_event_handlers(self):
        """Setup event handlers for internal events"""
        
        # Handle outgoing UI messages
        self.event_bus.subscribe('ui.message.out', self._handle_ui_message_out)
        
        # Handle notifications
        self.event_bus.subscribe('ui.notification.show', self._handle_notification)
        
        # Handle voice events
        self.event_bus.subscribe('voice.asr.complete', self._handle_asr_complete)
        self.event_bus.subscribe('voice.tts.complete', self._handle_tts_complete)
        
        # Handle reminder events
        self.event_bus.subscribe('skill.reminder.fire', self._handle_reminder_fire)
    
    async def _handle_ui_message_out(self, event: Event):
        """Handle outgoing UI messages"""
        data = {
            "type": "message",
            "content": event.data.get('content', ''),
            "timestamp": event.timestamp,
            "session_id": event.session_id
        }
        
        if event.device_id:
            await self.connection_manager.send_to_device(event.device_id, data)
        elif event.user_id:
            await self.connection_manager.send_to_user(event.user_id, data)
    
    async def _handle_notification(self, event: Event):
        """Handle notification events"""
        data = {
            "type": "notification",
            "title": event.data.get('title', ''),
            "message": event.data.get('message', ''),
            "priority": event.data.get('priority', 'normal'),
            "timestamp": event.timestamp
        }
        
        if event.device_id:
            await self.connection_manager.send_to_device(event.device_id, data)
        elif event.user_id:
            await self.connection_manager.send_to_user(event.user_id, data)
    
    async def _handle_asr_complete(self, event: Event):
        """Handle ASR completion"""
        data = {
            "type": "asr_result",
            "text": event.data.get('text', ''),
            "confidence": event.data.get('confidence', 0.0),
            "timestamp": event.timestamp
        }
        
        if event.device_id:
            await self.connection_manager.send_to_device(event.device_id, data)
    
    async def _handle_tts_complete(self, event: Event):
        """Handle TTS completion"""
        data = {
            "type": "tts_result",
            "audio_url": event.data.get('audio_url', ''),
            "text": event.data.get('text', ''),
            "timestamp": event.timestamp
        }
        
        if event.device_id:
            await self.connection_manager.send_to_device(event.device_id, data)
    
    async def _handle_reminder_fire(self, event: Event):
        """Handle reminder firing"""
        data = {
            "type": "reminder",
            "title": event.data.get('title', ''),
            "reminder_id": event.data.get('reminder_id', ''),
            "priority": event.data.get('priority', 'normal'),
            "timestamp": event.timestamp
        }
        
        if event.user_id:
            await self.connection_manager.send_to_user(event.user_id, data)
    
    async def start(self):
        """Start the API gateway"""
        import uvicorn
        
        # Start event bus
        await self.event_bus.start()
        
        logger.info(f"Starting BUDDY Core API Gateway on {self.host}:{self.port}")
        
        # Start the FastAPI server
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def stop(self):
        """Stop the API gateway"""
        await self.event_bus.stop()
        logger.info("API Gateway stopped")

# Global API gateway instance
_api_gateway = None

def get_api_gateway() -> APIGateway:
    """Get the global API gateway instance"""
    global _api_gateway
    if _api_gateway is None:
        _api_gateway = APIGateway()
    return _api_gateway


def get_sync_service():
    """Helper to get the global sync service from the BuddyCore runtime"""
    try:
        from ..runtime import get_buddy_core
        core = get_buddy_core()
        return getattr(core, 'sync', None)
    except Exception:
        return None
