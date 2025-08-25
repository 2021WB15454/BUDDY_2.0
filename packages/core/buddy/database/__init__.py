"""
BUDDY Database Integration Module

Provides database connectivity and ORM functionality for BUDDY.
Supports MongoDB for document storage and conversation management.
"""

from .mongodb_client import MongoDBClient
from .models import (
    ConversationModel,
    UserModel,
    SkillExecutionModel,
    DeviceModel,
    MemoryModel
)
from .repository import (
    ConversationRepository,
    UserRepository,
    SkillRepository,
    DeviceRepository,
    MemoryRepository
)

__all__ = [
    'MongoDBClient',
    'ConversationModel',
    'UserModel', 
    'SkillExecutionModel',
    'DeviceModel',
    'MemoryModel',
    'ConversationRepository',
    'UserRepository',
    'SkillRepository',
    'DeviceRepository',
    'MemoryRepository'
]
