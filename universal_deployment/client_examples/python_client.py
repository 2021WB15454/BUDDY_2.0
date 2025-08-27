"""
BUDDY Python Client SDK
Universal client for connecting any Python-based device to BUDDY Core
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import websockets
import httpx
import logging

logger = logging.getLogger(__name__)

class BuddyClient:
    """Universal BUDDY client for cross-device synchronization"""
    
    def __init__(
        self, 
        base_url: str = "http://localhost:8000",
        device_id: Optional[str] = None,
        device_name: str = "Python Client",
        device_type: str = "desktop",
        platform: str = "python"
    ):
        self.base_url = base_url.rstrip('/')
        self.device_id = device_id or str(uuid.uuid4())
        self.device_name = device_name
        self.device_type = device_type
        self.platform = platform
        self.user_id = None
        self.ws_connection = None
        self.is_connected = False
        self.message_handlers: Dict[str, Callable] = {}
        
        # HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def connect(self) -> bool:
        """Connect to BUDDY Core and register device"""
        try:
            # Register device
            response = await self.http_client.post(
                f"{self.base_url}/api/v1/devices/register",
                json={
                    "device_id": self.device_id,
                    "device_name": self.device_name,
                    "device_type": self.device_type,
                    "platform": self.platform,
                    "metadata": {
                        "sdk_version": "1.0.0",
                        "connected_at": datetime.utcnow().isoformat()
                    }
                }
            )
            response.raise_for_status()
            
            logger.info(f"Device registered successfully: {self.device_id}")
            
            # Connect WebSocket for real-time sync
            await self._connect_websocket()
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to BUDDY Core: {e}")
            return False
    
    async def _connect_websocket(self):
        """Connect to WebSocket for real-time updates"""
        try:
            # For demo using default user ID
            user_id = "550e8400-e29b-41d4-a716-446655440000"
            ws_url = f"{self.base_url.replace('http', 'ws')}/ws/{user_id}"
            
            self.ws_connection = await websockets.connect(ws_url)
            
            # Start listening for messages
            asyncio.create_task(self._listen_websocket())
            
            logger.info("WebSocket connected")
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
    
    async def _listen_websocket(self):
        """Listen for WebSocket messages"""
        try:
            async for message in self.ws_connection:
                data = json.loads(message)
                message_type = data.get("type")
                
                # Handle different message types
                if message_type in self.message_handlers:
                    await self.message_handlers[message_type](data)
                else:
                    await self._handle_default_message(data)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
    
    async def _handle_default_message(self, data: Dict[str, Any]):
        """Default message handler"""
        logger.info(f"Received message: {data}")
    
    def on_message(self, message_type: str, handler: Callable):
        """Register message handler for specific message types"""
        self.message_handlers[message_type] = handler
    
    async def send_message(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send chat message to BUDDY"""
        try:
            response = await self.http_client.post(
                f"{self.base_url}/api/v1/chat",
                json={
                    "text": text,
                    "device_id": self.device_id,
                    "session_id": str(uuid.uuid4()),
                    "context": context or {}
                }
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    async def create_task(
        self, 
        title: str, 
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: str = "medium",
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new task"""
        try:
            task_data = {
                "title": title,
                "device_id": self.device_id,
                "priority": priority
            }
            
            if description:
                task_data["description"] = description
            if due_date:
                task_data["due_date"] = due_date.isoformat()
            if category:
                task_data["category"] = category
            
            response = await self.http_client.post(
                f"{self.base_url}/api/v1/tasks",
                json=task_data
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise
    
    async def sync_data(
        self, 
        sync_types: List[str] = None,
        last_sync: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Sync data from BUDDY Core"""
        try:
            sync_data = {
                "device_id": self.device_id,
                "sync_types": sync_types or ["conversations", "tasks", "preferences"]
            }
            
            if last_sync:
                sync_data["last_sync"] = last_sync.isoformat()
            
            response = await self.http_client.post(
                f"{self.base_url}/api/v1/sync",
                json=sync_data
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to sync data: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from BUDDY Core"""
        if self.ws_connection:
            await self.ws_connection.close()
        
        await self.http_client.aclose()
        self.is_connected = False
        logger.info("Disconnected from BUDDY Core")

# Example usage
async def example_usage():
    """Example of using BUDDY Client SDK"""
    
    # Initialize client
    client = BuddyClient(
        base_url="http://localhost:8000",
        device_name="My Python App",
        device_type="desktop",
        platform="python"
    )
    
    # Set up message handlers
    async def handle_new_message(data):
        print(f"New message from another device: {data}")
    
    async def handle_task_created(data):
        print(f"Task created on another device: {data}")
    
    client.on_message("new_message", handle_new_message)
    client.on_message("task_created", handle_task_created)
    
    try:
        # Connect to BUDDY Core
        if await client.connect():
            print("Connected to BUDDY Core!")
            
            # Send a message
            response = await client.send_message(
                "Hello BUDDY! This is from Python client.",
                context={"app": "example", "version": "1.0"}
            )
            print(f"BUDDY Response: {response}")
            
            # Create a task
            task = await client.create_task(
                title="Test task from Python",
                description="This task was created via Python SDK",
                priority="high"
            )
            print(f"Task created: {task}")
            
            # Sync data
            sync_result = await client.sync_data()
            print(f"Sync completed: {len(sync_result['data']['conversations'])} conversations")
            
            # Keep connection alive for real-time updates
            print("Listening for real-time updates... (Press Ctrl+C to exit)")
            while client.is_connected:
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run example
    asyncio.run(example_usage())
