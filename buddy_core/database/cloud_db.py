"""
Cloud Database Layer - MongoDB Atlas Integration

Handles:
- Central cloud storage
- Cross-device synchronization
- Scalable document storage
- Aggregation and analytics
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

class CloudDatabase:
    """MongoDB Atlas cloud database implementation"""
    
    def __init__(self, connection_string: str = None, database_name: str = "buddy_cloud"):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client = None
        self.db = None
        self._connected = False
        
    async def initialize(self):
        """Initialize MongoDB connection"""
        try:
            # Try to import motor (async MongoDB driver)
            try:
                from motor.motor_asyncio import AsyncIOMotorClient
                self.client = AsyncIOMotorClient(self.connection_string)
                self.db = self.client[self.database_name]
                
                # Test connection
                await self.client.admin.command('ping')
                self._connected = True
                
                # Create indexes
                await self._create_indexes()
                
                logger.info("Cloud database (MongoDB) connected successfully")
                
            except ImportError:
                logger.warning("Motor not installed, using sync MongoDB client")
                import pymongo
                self.client = pymongo.MongoClient(self.connection_string)
                self.db = self.client[self.database_name]
                self._connected = True
                
                logger.info("Cloud database (MongoDB sync) connected successfully")
                
        except Exception as e:
            logger.error(f"Failed to connect to cloud database: {e}")
            self._connected = False
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        if not self._connected:
            return
            
        try:
            # User data indexes
            await self.db.user_data.create_index([("user_id", 1), ("data_type", 1)])
            await self.db.user_data.create_index([("updated_at", -1)])
            await self.db.user_data.create_index([("device_id", 1)])
            
            # Conversations indexes
            await self.db.conversations.create_index([("user_id", 1), ("session_id", 1)])
            await self.db.conversations.create_index([("timestamp", -1)])
            
            # AI context indexes
            await self.db.ai_context.create_index([("user_id", 1), ("context_type", 1)])
            await self.db.ai_context.create_index([("relevance_score", -1)])
            
            # Sync metadata indexes
            await self.db.sync_logs.create_index([("device_id", 1), ("timestamp", -1)])
            
            logger.info("Cloud database indexes created")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._connected
    
    # User Data Operations
    async def store_user_data(self, user_id: str, data_type: str, content: Dict[str, Any], 
                            device_id: str = None, sync_version: int = 1) -> str:
        """Store user data in cloud"""
        if not self._connected:
            raise ConnectionError("Cloud database not connected")
        
        document = {
            "user_id": user_id,
            "data_type": data_type,
            "content": content,
            "device_id": device_id,
            "sync_version": sync_version,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = await self.db.user_data.insert_one(document)
        return str(result.inserted_id)
    
    async def get_user_data(self, user_id: str, data_type: str = None, 
                          since: datetime = None) -> List[Dict[str, Any]]:
        """Retrieve user data from cloud"""
        if not self._connected:
            return []
        
        query = {"user_id": user_id}
        if data_type:
            query["data_type"] = data_type
        if since:
            query["updated_at"] = {"$gte": since}
        
        cursor = self.db.user_data.find(query).sort("updated_at", -1)
        documents = await cursor.to_list(length=1000)
        
        # Convert ObjectId to string
        for doc in documents:
            doc["_id"] = str(doc["_id"])
        
        return documents
    
    async def update_user_data(self, record_id: str, content: Dict[str, Any], 
                             sync_version: int = None) -> bool:
        """Update user data in cloud"""
        if not self._connected:
            return False
        
        from bson import ObjectId
        
        update_data = {
            "content": content,
            "updated_at": datetime.now(timezone.utc)
        }
        
        if sync_version:
            update_data["sync_version"] = sync_version
        
        result = await self.db.user_data.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    
    # Conversation Operations
    async def store_conversation(self, user_id: str, session_id: str, 
                               message_type: str, content: str, 
                               metadata: Dict[str, Any] = None, 
                               device_id: str = None) -> str:
        """Store conversation in cloud"""
        if not self._connected:
            raise ConnectionError("Cloud database not connected")
        
        document = {
            "user_id": user_id,
            "session_id": session_id,
            "message_type": message_type,
            "content": content,
            "metadata": metadata or {},
            "device_id": device_id,
            "timestamp": datetime.now(timezone.utc)
        }
        
        result = await self.db.conversations.insert_one(document)
        return str(result.inserted_id)
    
    async def get_conversations(self, user_id: str, session_id: str = None, 
                              since: datetime = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve conversations from cloud"""
        if not self._connected:
            return []
        
        query = {"user_id": user_id}
        if session_id:
            query["session_id"] = session_id
        if since:
            query["timestamp"] = {"$gte": since}
        
        cursor = self.db.conversations.find(query).sort("timestamp", -1).limit(limit)
        documents = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for doc in documents:
            doc["_id"] = str(doc["_id"])
        
        return documents
    
    # AI Context Operations
    async def store_ai_context(self, user_id: str, context_type: str, 
                             content: str, embedding_vector: List[float] = None,
                             relevance_score: float = 0.0, 
                             device_id: str = None) -> str:
        """Store AI context in cloud"""
        if not self._connected:
            raise ConnectionError("Cloud database not connected")
        
        document = {
            "user_id": user_id,
            "context_type": context_type,
            "content": content,
            "embedding_vector": embedding_vector,
            "relevance_score": relevance_score,
            "device_id": device_id,
            "created_at": datetime.now(timezone.utc),
            "last_accessed": datetime.now(timezone.utc)
        }
        
        result = await self.db.ai_context.insert_one(document)
        return str(result.inserted_id)
    
    async def get_ai_context(self, user_id: str, context_type: str = None, 
                           min_relevance: float = 0.0, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve AI context from cloud"""
        if not self._connected:
            return []
        
        query = {
            "user_id": user_id,
            "relevance_score": {"$gte": min_relevance}
        }
        if context_type:
            query["context_type"] = context_type
        
        cursor = self.db.ai_context.find(query).sort([
            ("relevance_score", -1),
            ("last_accessed", -1)
        ]).limit(limit)
        
        documents = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for doc in documents:
            doc["_id"] = str(doc["_id"])
        
        return documents
    
    async def update_context_relevance(self, context_id: str, relevance_score: float):
        """Update context relevance score"""
        if not self._connected:
            return False
        
        from bson import ObjectId
        
        result = await self.db.ai_context.update_one(
            {"_id": ObjectId(context_id)},
            {
                "$set": {
                    "relevance_score": relevance_score,
                    "last_accessed": datetime.now(timezone.utc)
                }
            }
        )
        
        return result.modified_count > 0
    
    # Sync Operations
    async def log_sync_operation(self, device_id: str, operation: str, 
                               table_name: str, record_count: int, 
                               status: str = "success"):
        """Log synchronization operation"""
        if not self._connected:
            return
        
        document = {
            "device_id": device_id,
            "operation": operation,
            "table_name": table_name,
            "record_count": record_count,
            "status": status,
            "timestamp": datetime.now(timezone.utc)
        }
        
        await self.db.sync_logs.insert_one(document)
    
    async def get_device_sync_status(self, device_id: str) -> Dict[str, Any]:
        """Get last sync status for device"""
        if not self._connected:
            return {}
        
        pipeline = [
            {"$match": {"device_id": device_id}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$table_name",
                "last_sync": {"$first": "$timestamp"},
                "status": {"$first": "$status"},
                "record_count": {"$first": "$record_count"}
            }}
        ]
        
        cursor = self.db.sync_logs.aggregate(pipeline)
        results = await cursor.to_list(length=100)
        
        return {doc["_id"]: {
            "last_sync": doc["last_sync"],
            "status": doc["status"],
            "record_count": doc["record_count"]
        } for doc in results}
    
    # Analytics and Insights
    async def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get user analytics from cloud data"""
        if not self._connected:
            return {}
        
        # Conversation analytics
        conv_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$message_type",
                "count": {"$sum": 1},
                "last_message": {"$max": "$timestamp"}
            }}
        ]
        
        conv_cursor = self.db.conversations.aggregate(conv_pipeline)
        conv_stats = await conv_cursor.to_list(length=100)
        
        # Context analytics
        context_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$context_type",
                "count": {"$sum": 1},
                "avg_relevance": {"$avg": "$relevance_score"}
            }}
        ]
        
        context_cursor = self.db.ai_context.aggregate(context_pipeline)
        context_stats = await context_cursor.to_list(length=100)
        
        return {
            "conversations": conv_stats,
            "context": context_stats,
            "generated_at": datetime.now(timezone.utc)
        }
    
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("Cloud database connection closed")
