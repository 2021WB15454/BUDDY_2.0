"""
Database Repository Classes for BUDDY

Provides high-level database operations and business logic
for different data entities using MongoDB.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from .mongodb_client import MongoDBClient
from .models import (
    ConversationModel, UserModel, SkillExecutionModel, 
    DeviceModel, MemoryModel, ConversationTurn,
    MessageType, DeviceType, MemoryType,
    validate_conversation_data, validate_user_data,
    validate_skill_execution_data, validate_device_data,
    validate_memory_data
)

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class with common database operations."""
    
    def __init__(self, db_client: MongoDBClient):
        self.db = db_client
    
    def _prepare_filter(self, **kwargs) -> Dict[str, Any]:
        """Prepare filter query by removing None values."""
        return {k: v for k, v in kwargs.items() if v is not None}


class ConversationRepository(BaseRepository):
    """Repository for conversation data operations."""
    
    async def create_conversation(self, conversation: ConversationModel) -> str:
        """
        Create a new conversation.
        
        Args:
            conversation: Conversation model to create
            
        Returns:
            Created conversation ID
        """
        try:
            if not validate_conversation_data(conversation.to_dict()):
                raise ValueError("Invalid conversation data")
            
            conversation_id = await self.db.create_document(
                'conversations', 
                conversation.to_dict()
            )
            
            logger.info(f"Created conversation {conversation_id} for user {conversation.user_id}")
            return conversation_id
            
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationModel]:
        """Get conversation by ID."""
        try:
            documents = await self.db.find_documents(
                'conversations',
                {'conversation_id': conversation_id}
            )
            
            if documents:
                return ConversationModel.from_dict(documents[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            raise
    
    async def get_conversations_by_user(self, user_id: str, limit: int = 50) -> List[ConversationModel]:
        """Get conversations for a user."""
        try:
            documents = await self.db.find_documents(
                'conversations',
                {'user_id': user_id},
                limit=limit,
                sort=[('last_activity', -1)]
            )
            
            return [ConversationModel.from_dict(doc) for doc in documents]
            
        except Exception as e:
            logger.error(f"Failed to get conversations for user {user_id}: {e}")
            raise
    
    async def get_conversations_by_session(self, session_id: str) -> List[ConversationModel]:
        """Get conversations for a session."""
        try:
            documents = await self.db.find_documents(
                'conversations',
                {'session_id': session_id},
                sort=[('start_time', 1)]
            )
            
            return [ConversationModel.from_dict(doc) for doc in documents]
            
        except Exception as e:
            logger.error(f"Failed to get conversations for session {session_id}: {e}")
            raise
    
    async def add_turn_to_conversation(self, conversation_id: str, turn: ConversationTurn) -> bool:
        """Add a turn to an existing conversation."""
        try:
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                return False
            
            conversation.add_turn(turn)
            
            success = await self.db.update_document(
                'conversations',
                {'conversation_id': conversation_id},
                {
                    'turns': [turn.to_dict() for turn in conversation.turns],
                    'total_turns': conversation.total_turns,
                    'last_activity': conversation.last_activity.isoformat()
                }
            )
            
            if success:
                logger.debug(f"Added turn to conversation {conversation_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to add turn to conversation {conversation_id}: {e}")
            raise
    
    async def update_conversation_summary(self, conversation_id: str, summary: str) -> bool:
        """Update conversation summary."""
        try:
            return await self.db.update_document(
                'conversations',
                {'conversation_id': conversation_id},
                {'summary': summary}
            )
        except Exception as e:
            logger.error(f"Failed to update conversation summary: {e}")
            raise
    
    async def get_recent_conversations(self, hours: int = 24, limit: int = 100) -> List[ConversationModel]:
        """Get recent conversations within specified hours."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            documents = await self.db.find_documents(
                'conversations',
                {'last_activity': {'$gte': cutoff_time.isoformat()}},
                limit=limit,
                sort=[('last_activity', -1)]
            )
            
            return [ConversationModel.from_dict(doc) for doc in documents]
            
        except Exception as e:
            logger.error(f"Failed to get recent conversations: {e}")
            raise


class UserRepository(BaseRepository):
    """Repository for user data operations."""
    
    async def create_user(self, user: UserModel) -> str:
        """Create a new user."""
        try:
            if not validate_user_data(user.to_dict()):
                raise ValueError("Invalid user data")
            
            user_id = await self.db.create_document('users', user.to_dict())
            logger.info(f"Created user {user.user_id}")
            return user_id
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    async def get_user(self, user_id: str) -> Optional[UserModel]:
        """Get user by ID."""
        try:
            documents = await self.db.find_documents(
                'users',
                {'user_id': user_id}
            )
            
            if documents:
                return UserModel.from_dict(documents[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            raise
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences."""
        try:
            return await self.db.update_document(
                'users',
                {'user_id': user_id},
                {'preferences': preferences}
            )
        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}")
            raise
    
    async def update_last_seen(self, user_id: str) -> bool:
        """Update user's last seen timestamp."""
        try:
            return await self.db.update_document(
                'users',
                {'user_id': user_id},
                {'last_seen': datetime.utcnow().isoformat()}
            )
        except Exception as e:
            logger.error(f"Failed to update last seen for user {user_id}: {e}")
            raise
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            # Get conversation count
            conv_pipeline = [
                {'$match': {'user_id': user_id}},
                {'$count': 'total_conversations'}
            ]
            conv_result = await self.db.aggregate('conversations', conv_pipeline)
            total_conversations = conv_result[0]['total_conversations'] if conv_result else 0
            
            # Get skill usage
            skill_pipeline = [
                {'$match': {'user_id': user_id}},
                {'$group': {
                    '_id': '$skill_name',
                    'count': {'$sum': 1},
                    'success_rate': {'$avg': {'$cond': ['$success', 1, 0]}}
                }},
                {'$sort': {'count': -1}},
                {'$limit': 10}
            ]
            skill_stats = await self.db.aggregate('skill_executions', skill_pipeline)
            
            return {
                'total_conversations': total_conversations,
                'top_skills': skill_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            raise


class SkillRepository(BaseRepository):
    """Repository for skill execution data operations."""
    
    async def log_skill_execution(self, execution: SkillExecutionModel) -> str:
        """Log a skill execution."""
        try:
            if not validate_skill_execution_data(execution.to_dict()):
                raise ValueError("Invalid skill execution data")
            
            execution_id = await self.db.create_document(
                'skill_executions',
                execution.to_dict()
            )
            
            logger.debug(f"Logged skill execution: {execution.skill_name}")
            return execution_id
            
        except Exception as e:
            logger.error(f"Failed to log skill execution: {e}")
            raise
    
    async def get_skill_analytics(self, skill_name: str = None, 
                                 days: int = 30) -> Dict[str, Any]:
        """Get skill analytics."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            match_filter = {'timestamp': {'$gte': cutoff_time.isoformat()}}
            
            if skill_name:
                match_filter['skill_name'] = skill_name
            
            pipeline = [
                {'$match': match_filter},
                {'$group': {
                    '_id': '$skill_name',
                    'total_executions': {'$sum': 1},
                    'success_count': {'$sum': {'$cond': ['$success', 1, 0]}},
                    'avg_execution_time': {'$avg': '$execution_time_ms'},
                    'unique_users': {'$addToSet': '$user_id'}
                }},
                {'$addFields': {
                    'success_rate': {'$divide': ['$success_count', '$total_executions']},
                    'unique_user_count': {'$size': '$unique_users'}
                }},
                {'$sort': {'total_executions': -1}}
            ]
            
            return await self.db.aggregate('skill_executions', pipeline)
            
        except Exception as e:
            logger.error(f"Failed to get skill analytics: {e}")
            raise
    
    async def get_user_skill_history(self, user_id: str, skill_name: str = None, 
                                   limit: int = 50) -> List[SkillExecutionModel]:
        """Get skill execution history for a user."""
        try:
            filter_query = {'user_id': user_id}
            if skill_name:
                filter_query['skill_name'] = skill_name
            
            documents = await self.db.find_documents(
                'skill_executions',
                filter_query,
                limit=limit,
                sort=[('timestamp', -1)]
            )
            
            return [SkillExecutionModel.from_dict(doc) for doc in documents]
            
        except Exception as e:
            logger.error(f"Failed to get skill history for user {user_id}: {e}")
            raise


class DeviceRepository(BaseRepository):
    """Repository for device data operations."""
    
    async def register_device(self, device: DeviceModel) -> str:
        """Register a new device."""
        try:
            if not validate_device_data(device.to_dict()):
                raise ValueError("Invalid device data")
            
            device_id = await self.db.create_document('devices', device.to_dict())
            logger.info(f"Registered device {device.device_id} for user {device.user_id}")
            return device_id
            
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            raise
    
    async def get_device(self, device_id: str) -> Optional[DeviceModel]:
        """Get device by ID."""
        try:
            documents = await self.db.find_documents(
                'devices',
                {'device_id': device_id}
            )
            
            if documents:
                return DeviceModel.from_dict(documents[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get device {device_id}: {e}")
            raise
    
    async def get_user_devices(self, user_id: str) -> List[DeviceModel]:
        """Get all devices for a user."""
        try:
            documents = await self.db.find_documents(
                'devices',
                {'user_id': user_id, 'is_active': True},
                sort=[('last_seen', -1)]
            )
            
            return [DeviceModel.from_dict(doc) for doc in documents]
            
        except Exception as e:
            logger.error(f"Failed to get devices for user {user_id}: {e}")
            raise
    
    async def update_device_activity(self, device_id: str) -> bool:
        """Update device's last seen timestamp."""
        try:
            return await self.db.update_document(
                'devices',
                {'device_id': device_id},
                {'last_seen': datetime.utcnow().isoformat()}
            )
        except Exception as e:
            logger.error(f"Failed to update device activity: {e}")
            raise


class MemoryRepository(BaseRepository):
    """Repository for memory data operations."""
    
    async def store_memory(self, memory: MemoryModel) -> str:
        """Store a new memory."""
        try:
            if not validate_memory_data(memory.to_dict()):
                raise ValueError("Invalid memory data")
            
            memory_id = await self.db.create_document('memories', memory.to_dict())
            logger.debug(f"Stored memory {memory.memory_id} for user {memory.user_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise
    
    async def get_memories(self, user_id: str, memory_type: MemoryType = None,
                          limit: int = 50) -> List[MemoryModel]:
        """Get memories for a user."""
        try:
            filter_query = {'user_id': user_id}
            if memory_type:
                filter_query['memory_type'] = memory_type.value
            
            # Filter out expired memories
            current_time = datetime.utcnow().isoformat()
            filter_query['$or'] = [
                {'expires_at': None},
                {'expires_at': {'$gte': current_time}}
            ]
            
            documents = await self.db.find_documents(
                'memories',
                filter_query,
                limit=limit,
                sort=[('importance', -1), ('last_accessed', -1)]
            )
            
            memories = [MemoryModel.from_dict(doc) for doc in documents]
            
            # Mark memories as accessed
            for memory in memories:
                memory.access()
                await self.update_memory_access(memory.memory_id, memory.access_count)
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to get memories for user {user_id}: {e}")
            raise
    
    async def update_memory_access(self, memory_id: str, access_count: int) -> bool:
        """Update memory access count."""
        try:
            return await self.db.update_document(
                'memories',
                {'memory_id': memory_id},
                {
                    'access_count': access_count,
                    'last_accessed': datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to update memory access: {e}")
            raise
    
    async def cleanup_expired_memories(self) -> int:
        """Clean up expired memories."""
        try:
            current_time = datetime.utcnow().isoformat()
            
            # Count expired memories first
            expired_docs = await self.db.find_documents(
                'memories',
                {
                    'expires_at': {'$ne': None, '$lt': current_time}
                }
            )
            
            count = len(expired_docs)
            
            # Delete expired memories
            if count > 0:
                collection = self.db.collections['memories']
                await collection.delete_many({
                    'expires_at': {'$ne': None, '$lt': current_time}
                })
                
                logger.info(f"Cleaned up {count} expired memories")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
            raise
