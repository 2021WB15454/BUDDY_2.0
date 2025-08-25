"""
MongoDB Integration for BUDDY 2.0

This module provides MongoDB database connection and operations for BUDDY.
Supports both local MongoDB and MongoDB Atlas (cloud).
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import logging

logger = logging.getLogger(__name__)

class BuddyDatabase:
    """MongoDB database manager for BUDDY 2.0"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.connected = False
        
        # Database collections
        self.conversations = None
        self.users = None
        self.reminders = None
        self.skills_usage = None
        self.analytics = None
        self.preferences = None
    
    async def connect(self, connection_string: str = None):
        """Connect to MongoDB database"""
        try:
            # Get connection string from environment or parameter
            if not connection_string:
                connection_string = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
            
            # Create MongoDB client
            self.client = AsyncIOMotorClient(connection_string)
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Get database
            db_name = os.getenv('MONGODB_DB_NAME', 'buddy_ai')
            self.db = self.client[db_name]
            
            # Initialize collections
            self.conversations = self.db.conversations
            self.users = self.db.users
            self.reminders = self.db.reminders
            self.skills_usage = self.db.skills_usage
            self.analytics = self.db.analytics
            self.preferences = self.db.preferences
            
            # Create indexes for better performance
            await self._create_indexes()
            
            self.connected = True
            logger.info(f"Connected to MongoDB: {db_name}")
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.connected = False
            raise
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            self.connected = False
            raise
    
    async def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Conversations indexes
            await self.conversations.create_index([("session_id", 1), ("timestamp", -1)])
            await self.conversations.create_index([("user_id", 1), ("timestamp", -1)])
            
            # Users indexes
            await self.users.create_index([("user_id", 1)], unique=True)
            await self.users.create_index([("email", 1)], unique=True, sparse=True)
            
            # Reminders indexes
            await self.reminders.create_index([("user_id", 1), ("due_date", 1)])
            await self.reminders.create_index([("status", 1), ("due_date", 1)])
            
            # Skills usage indexes
            await self.skills_usage.create_index([("skill_id", 1), ("timestamp", -1)])
            await self.skills_usage.create_index([("user_id", 1), ("timestamp", -1)])
            
            # Analytics indexes
            await self.analytics.create_index([("date", -1)])
            await self.analytics.create_index([("event_type", 1), ("timestamp", -1)])
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("Disconnected from MongoDB")
    
    # User Management
    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user"""
        try:
            user_data['created_at'] = datetime.utcnow()
            user_data['updated_at'] = datetime.utcnow()
            
            result = await self.users.insert_one(user_data)
            logger.info(f"Created user: {user_data.get('user_id', 'unknown')}")
            return str(result.inserted_id)
            
        except DuplicateKeyError:
            logger.warning(f"User already exists: {user_data.get('user_id')}")
            raise ValueError("User already exists")
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            user = await self.users.find_one({"user_id": user_id})
            return user
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        try:
            result = await self.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "preferences": preferences,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Failed to update preferences for {user_id}: {e}")
            return False
    
    # Conversation Management
    async def save_conversation(self, session_id: str, user_id: str, 
                              role: str, content: str, metadata: Dict[str, Any] = None) -> str:
        """Save a conversation message"""
        try:
            message_data = {
                "session_id": session_id,
                "user_id": user_id,
                "role": role,  # 'user' or 'assistant'
                "content": content,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {}
            }
            
            result = await self.conversations.insert_one(message_data)
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            raise
    
    async def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        try:
            cursor = self.conversations.find(
                {"session_id": session_id}
            ).sort("timestamp", -1).limit(limit)
            
            messages = await cursor.to_list(length=limit)
            return list(reversed(messages))  # Return in chronological order
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    async def get_user_conversations(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get all conversations for a user within specified days"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            cursor = self.conversations.find({
                "user_id": user_id,
                "timestamp": {"$gte": since_date}
            }).sort("timestamp", -1)
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            logger.error(f"Failed to get user conversations: {e}")
            return []
    
    # Reminder Management
    async def create_reminder(self, user_id: str, title: str, description: str,
                            due_date: datetime, metadata: Dict[str, Any] = None) -> str:
        """Create a new reminder"""
        try:
            reminder_data = {
                "user_id": user_id,
                "title": title,
                "description": description,
                "due_date": due_date,
                "status": "active",  # active, completed, cancelled
                "created_at": datetime.utcnow(),
                "completed_at": None,
                "metadata": metadata or {}
            }
            
            result = await self.reminders.insert_one(reminder_data)
            logger.info(f"Created reminder for {user_id}: {title}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to create reminder: {e}")
            raise
    
    async def get_user_reminders(self, user_id: str, status: str = "active") -> List[Dict[str, Any]]:
        """Get reminders for a user"""
        try:
            query = {"user_id": user_id}
            if status:
                query["status"] = status
            
            cursor = self.reminders.find(query).sort("due_date", 1)
            return await cursor.to_list(length=None)
            
        except Exception as e:
            logger.error(f"Failed to get reminders for {user_id}: {e}")
            return []
    
    async def complete_reminder(self, reminder_id: str) -> bool:
        """Mark a reminder as completed"""
        try:
            from bson import ObjectId
            result = await self.reminders.update_one(
                {"_id": ObjectId(reminder_id)},
                {
                    "$set": {
                        "status": "completed",
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to complete reminder {reminder_id}: {e}")
            return False
    
    async def get_due_reminders(self, buffer_minutes: int = 5) -> List[Dict[str, Any]]:
        """Get reminders that are due (within buffer time)"""
        try:
            due_time = datetime.utcnow() + timedelta(minutes=buffer_minutes)
            
            cursor = self.reminders.find({
                "status": "active",
                "due_date": {"$lte": due_time}
            }).sort("due_date", 1)
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            logger.error(f"Failed to get due reminders: {e}")
            return []
    
    # Skills Usage Tracking
    async def log_skill_usage(self, user_id: str, skill_id: str, 
                            success: bool, response_time: float = None,
                            metadata: Dict[str, Any] = None) -> str:
        """Log skill usage for analytics"""
        try:
            usage_data = {
                "user_id": user_id,
                "skill_id": skill_id,
                "success": success,
                "response_time": response_time,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {}
            }
            
            result = await self.skills_usage.insert_one(usage_data)
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to log skill usage: {e}")
            return None
    
    async def get_skill_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get skill usage analytics"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Aggregate skill usage data
            pipeline = [
                {"$match": {"timestamp": {"$gte": since_date}}},
                {
                    "$group": {
                        "_id": "$skill_id",
                        "total_uses": {"$sum": 1},
                        "successful_uses": {"$sum": {"$cond": ["$success", 1, 0]}},
                        "avg_response_time": {"$avg": "$response_time"},
                        "last_used": {"$max": "$timestamp"}
                    }
                },
                {"$sort": {"total_uses": -1}}
            ]
            
            result = await self.skills_usage.aggregate(pipeline).to_list(length=None)
            
            # Calculate success rates
            for skill in result:
                skill['success_rate'] = (skill['successful_uses'] / skill['total_uses']) * 100
            
            return {
                "period_days": days,
                "skills": result,
                "total_interactions": sum(skill['total_uses'] for skill in result)
            }
            
        except Exception as e:
            logger.error(f"Failed to get skill analytics: {e}")
            return {}
    
    # Analytics and Reporting
    async def log_analytics_event(self, event_type: str, user_id: str = None,
                                data: Dict[str, Any] = None) -> str:
        """Log an analytics event"""
        try:
            event_data = {
                "event_type": event_type,
                "user_id": user_id,
                "timestamp": datetime.utcnow(),
                "date": datetime.utcnow().date(),
                "data": data or {}
            }
            
            result = await self.analytics.insert_one(event_data)
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to log analytics event: {e}")
            return None
    
    async def get_daily_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get daily usage statistics"""
        try:
            since_date = datetime.utcnow().date() - timedelta(days=days)
            
            # Aggregate daily stats
            pipeline = [
                {"$match": {"date": {"$gte": since_date}}},
                {
                    "$group": {
                        "_id": {
                            "date": "$date",
                            "event_type": "$event_type"
                        },
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"_id.date": -1}}
            ]
            
            result = await self.analytics.aggregate(pipeline).to_list(length=None)
            
            # Format results
            daily_stats = {}
            for item in result:
                date_str = item['_id']['date'].isoformat()
                event_type = item['_id']['event_type']
                
                if date_str not in daily_stats:
                    daily_stats[date_str] = {}
                
                daily_stats[date_str][event_type] = item['count']
            
            return daily_stats
            
        except Exception as e:
            logger.error(f"Failed to get daily stats: {e}")
            return {}
    
    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """Check database health and return stats"""
        try:
            if not self.connected:
                return {"status": "disconnected", "error": "Not connected to database"}
            
            # Get collection stats
            stats = {}
            collections = ['conversations', 'users', 'reminders', 'skills_usage', 'analytics']
            
            for collection_name in collections:
                collection = getattr(self, collection_name)
                count = await collection.count_documents({})
                stats[f"{collection_name}_count"] = count
            
            # Test write operation
            test_doc = {"test": True, "timestamp": datetime.utcnow()}
            test_collection = self.db.health_test
            await test_collection.insert_one(test_doc)
            await test_collection.delete_many({"test": True})
            
            return {
                "status": "healthy",
                "connected": True,
                "database": self.db.name,
                "collections": stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "error", "error": str(e)}

# Global database instance
buddy_db = BuddyDatabase()

# Helper functions for easy access
async def init_database(connection_string: str = None):
    """Initialize database connection"""
    await buddy_db.connect(connection_string)
    return buddy_db

async def get_database() -> BuddyDatabase:
    """Get database instance"""
    if not buddy_db.connected:
        await buddy_db.connect()
    return buddy_db

async def close_database():
    """Close database connection"""
    await buddy_db.disconnect()
