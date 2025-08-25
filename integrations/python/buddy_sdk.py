"""
BUDDY AI Assistant - Python SDK

Easy integration library for connecting to BUDDY API
Supports async/await and synchronous operations
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Callable, Any
import aiohttp
import requests
from dataclasses import dataclass, asdict


@dataclass
class BuddyMessage:
    """Represents a message in BUDDY conversation"""
    content: str
    sender: str
    timestamp: str
    message_id: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BuddyResponse:
    """Represents BUDDY's response"""
    response: str
    confidence: float
    skill_used: str
    execution_time: float
    conversation_id: str
    metadata: Dict[str, Any] = None


class BuddyClient:
    """
    BUDDY AI Assistant Python Client
    
    Provides both synchronous and asynchronous methods for interacting
    with BUDDY AI Assistant API.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8081",
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        timeout: int = 30,
        on_message: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.user_id = user_id or self._generate_user_id()
        self.session_id = session_id or self._generate_session_id()
        self.timeout = timeout
        self.on_message = on_message
        self.on_error = on_error
        
        # Session for synchronous requests
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{uuid.uuid4().hex[:8]}"
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session_{uuid.uuid4().hex[:8]}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers
    
    # ===== SYNCHRONOUS METHODS =====
    
    def chat(
        self, 
        message: str, 
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> BuddyResponse:
        """
        Send a message to BUDDY (synchronous)
        
        Args:
            message: The message to send
            user_id: Optional user ID override
            session_id: Optional session ID override
            context: Additional context for the conversation
            metadata: Additional metadata
            
        Returns:
            BuddyResponse: BUDDY's response
        """
        payload = {
            'message': message,
            'user_id': user_id or self.user_id,
            'session_id': session_id or self.session_id,
            'context': context or {},
            'metadata': {
                'timestamp': time.time(),
                'client': 'buddy-python-sdk',
                **(metadata or {})
            }
        }
        
        try:
            response = self.session.post(
                f'{self.base_url}/chat',
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            buddy_response = BuddyResponse(**data)
            
            if self.on_message:
                self.on_message(buddy_response)
                
            return buddy_response
            
        except Exception as error:
            if self.on_error:
                self.on_error(error)
            raise
    
    def get_skills(self) -> List[Dict]:
        """Get available skills (synchronous)"""
        response = self.session.get(f'{self.base_url}/skills', timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def get_health(self) -> Dict:
        """Check BUDDY health status (synchronous)"""
        response = self.session.get(f'{self.base_url}/health', timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def execute_skill(
        self, 
        skill_name: str, 
        parameters: Optional[Dict] = None
    ) -> Dict:
        """Execute a specific skill (synchronous)"""
        payload = {
            'skill': skill_name,
            'parameters': parameters or {},
            'user_id': self.user_id,
            'session_id': self.session_id
        }
        
        response = self.session.post(
            f'{self.base_url}/skills/execute',
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get_conversation_history(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get conversation history (synchronous)"""
        params = {
            'user_id': user_id or self.user_id,
            'session_id': session_id or self.session_id,
            'limit': limit,
            'offset': offset
        }
        
        response = self.session.get(
            f'{self.base_url}/conversations',
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    # ===== ASYNCHRONOUS METHODS =====
    
    async def async_chat(
        self,
        message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> BuddyResponse:
        """Send a message to BUDDY (asynchronous)"""
        payload = {
            'message': message,
            'user_id': user_id or self.user_id,
            'session_id': session_id or self.session_id,
            'context': context or {},
            'metadata': {
                'timestamp': time.time(),
                'client': 'buddy-python-sdk-async',
                **(metadata or {})
            }
        }
        
        async with aiohttp.ClientSession(
            headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            async with session.post(f'{self.base_url}/chat', json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                buddy_response = BuddyResponse(**data)
                
                if self.on_message:
                    self.on_message(buddy_response)
                    
                return buddy_response
    
    async def async_get_skills(self) -> List[Dict]:
        """Get available skills (asynchronous)"""
        async with aiohttp.ClientSession(
            headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            async with session.get(f'{self.base_url}/skills') as response:
                response.raise_for_status()
                return await response.json()
    
    async def async_execute_skill(
        self,
        skill_name: str,
        parameters: Optional[Dict] = None
    ) -> Dict:
        """Execute a specific skill (asynchronous)"""
        payload = {
            'skill': skill_name,
            'parameters': parameters or {},
            'user_id': self.user_id,
            'session_id': self.session_id
        }
        
        async with aiohttp.ClientSession(
            headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            async with session.post(f'{self.base_url}/skills/execute', json=payload) as response:
                response.raise_for_status()
                return await response.json()
    
    async def stream_chat(
        self,
        message: str,
        on_chunk: Callable[[Dict], None],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Start streaming conversation (asynchronous)"""
        payload = {
            'message': message,
            'user_id': user_id or self.user_id,
            'session_id': session_id or self.session_id,
            'stream': True
        }
        
        async with aiohttp.ClientSession(
            headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            async with session.post(f'{self.base_url}/chat/stream', json=payload) as response:
                response.raise_for_status()
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            on_chunk(data)
                        except json.JSONDecodeError:
                            continue
    
    # ===== CONTEXT MANAGERS =====
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.session.close()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass


# ===== UTILITY FUNCTIONS =====

def create_buddy_client(config: Dict[str, Any]) -> BuddyClient:
    """Factory function to create BUDDY client from config"""
    return BuddyClient(**config)


class BuddyConversation:
    """
    High-level conversation manager for BUDDY
    Maintains conversation state and history
    """
    
    def __init__(self, buddy_client: BuddyClient):
        self.buddy = buddy_client
        self.history: List[BuddyMessage] = []
        self.context: Dict[str, Any] = {}
    
    def add_user_message(self, message: str) -> BuddyMessage:
        """Add user message to conversation history"""
        user_msg = BuddyMessage(
            content=message,
            sender='user',
            timestamp=str(time.time())
        )
        self.history.append(user_msg)
        return user_msg
    
    def add_buddy_response(self, response: BuddyResponse) -> BuddyMessage:
        """Add BUDDY response to conversation history"""
        buddy_msg = BuddyMessage(
            content=response.response,
            sender='buddy',
            timestamp=str(time.time()),
            metadata={
                'confidence': response.confidence,
                'skill_used': response.skill_used,
                'execution_time': response.execution_time
            }
        )
        self.history.append(buddy_msg)
        return buddy_msg
    
    def chat(self, message: str) -> BuddyResponse:
        """Send message and maintain conversation history"""
        self.add_user_message(message)
        response = self.buddy.chat(message, context=self.context)
        self.add_buddy_response(response)
        return response
    
    async def async_chat(self, message: str) -> BuddyResponse:
        """Send message asynchronously and maintain conversation history"""
        self.add_user_message(message)
        response = await self.buddy.async_chat(message, context=self.context)
        self.add_buddy_response(response)
        return response
    
    def get_history(self) -> List[BuddyMessage]:
        """Get conversation history"""
        return self.history.copy()
    
    def clear_history(self):
        """Clear conversation history"""
        self.history.clear()
        self.context.clear()
    
    def set_context(self, key: str, value: Any):
        """Set context variable"""
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context variable"""
        return self.context.get(key, default)
