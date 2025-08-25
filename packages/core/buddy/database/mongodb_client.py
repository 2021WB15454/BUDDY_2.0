"""
MongoDB Client for BUDDY

Handles MongoDB connection management, database operations,
and connection pooling for BUDDY's data persistence needs.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    MongoDB client with async support for BUDDY.
    
    Provides connection management, database operations,
    and automatic reconnection with health monitoring.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_default_config()
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.collections: Dict[str, AsyncIOMotorCollection] = {}
        self.is_connected = False
        self._connection_pool_size = self.config.get('connection_pool_size', 10)
        self._timeout = self.config.get('timeout_ms', 10000)  # Increased to 10s for Atlas
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default MongoDB configuration."""
        # Try to load from config file first
        config_path = Path("config/database.yml")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    
                    # Check environment variable for configuration mode
                    env_mode = os.getenv('BUDDY_ENV', 'development')
                    
                    # Try atlas configuration if BUDDY_ENV=atlas or if no local MongoDB
                    if env_mode == 'atlas' or os.getenv('MONGODB_USE_ATLAS', 'false').lower() == 'true':
                        atlas_config = config_data.get('atlas', {}).get('mongodb', {})
                        if atlas_config:
                            logger.info("Using MongoDB Atlas configuration")
                            return atlas_config
                    
                    # Try environment-specific config
                    env_config = config_data.get(env_mode, {}).get('mongodb')
                    if env_config:
                        return env_config
                    
                    # Fall back to default mongodb config
                    return config_data.get('mongodb', {})
                    
            except Exception as e:
                logger.warning(f"Failed to load database config: {e}")
        
        # Default configuration from environment variables
        return {
            'connection_string': os.getenv('MONGODB_CONNECTION_STRING'),
            'host': os.getenv('MONGODB_HOST', 'localhost'),
            'port': int(os.getenv('MONGODB_PORT', 27017)),
            'database': os.getenv('MONGODB_DATABASE', 'buddy_ai'),
            'username': os.getenv('MONGODB_USERNAME'),
            'password': os.getenv('MONGODB_PASSWORD'),
            'auth_source': os.getenv('MONGODB_AUTH_SOURCE', 'admin'),
            'connection_pool_size': 10,
            'timeout_ms': 10000,  # Increased for MongoDB Atlas
            'retry_writes': True,
            'journal': True
        }
    
    async def connect(self) -> bool:
        """
        Establish connection to MongoDB.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Build connection URI
            uri = self._build_connection_uri()
            
            # Create client with connection options
            self.client = AsyncIOMotorClient(
                uri,
                maxPoolSize=self._connection_pool_size,
                serverSelectionTimeoutMS=self._timeout,
                retryWrites=self.config.get('retry_writes', True),
                journal=self.config.get('journal', True)
            )
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Get database
            database_name = self.config.get('database', 'buddy_ai')
            self.database = self.client[database_name]
            
            # Initialize collections
            await self._initialize_collections()
            
            # Create indexes
            await self._create_indexes()
            
            self.is_connected = True
            
            # Log connection info (mask sensitive details for connection strings)
            if self.config.get('connection_string'):
                # For connection strings, just show the database name
                logger.info(f"Connected to MongoDB Atlas: {database_name} database")
            else:
                # For regular connections, show host:port/database
                logger.info(f"Connected to MongoDB: {self.config['host']}:{self.config['port']}/{database_name}")
            
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            return False
    
    def _build_connection_uri(self) -> str:
        """Build MongoDB connection URI from config."""
        # Check if connection string is provided (for Atlas or custom URIs)
        connection_string = self.config.get('connection_string')
        if connection_string:
            logger.info("Using provided connection string for MongoDB")
            return connection_string
        
        # Build URI from individual components
        host = self.config['host']
        port = self.config['port']
        username = self.config.get('username')
        password = self.config.get('password')
        auth_source = self.config.get('auth_source', 'admin')
        
        if username and password:
            auth_string = f"{username}:{password}@"
            auth_params = f"?authSource={auth_source}"
        else:
            auth_string = ""
            auth_params = ""
        
        return f"mongodb://{auth_string}{host}:{port}/{auth_params}"
    
    async def _initialize_collections(self):
        """Initialize database collections."""
        collection_names = [
            'conversations',
            'users', 
            'skill_executions',
            'devices',
            'memories',
            'user_preferences',
            'conversation_summaries',
            'skill_analytics'
        ]
        
        for name in collection_names:
            self.collections[name] = self.database[name]
            
        logger.info(f"Initialized {len(collection_names)} collections")
    
    async def _create_indexes(self):
        """Create database indexes for optimal performance."""
        try:
            # Conversations indexes
            await self.collections['conversations'].create_indexes([
                IndexModel([('session_id', ASCENDING)]),
                IndexModel([('user_id', ASCENDING)]),
                IndexModel([('timestamp', DESCENDING)]),
                IndexModel([('user_id', ASCENDING), ('timestamp', DESCENDING)]),
                IndexModel([('session_id', ASCENDING), ('turn_number', ASCENDING)])
            ])
            
            # Users indexes
            await self.collections['users'].create_indexes([
                IndexModel([('user_id', ASCENDING)], unique=True),
                IndexModel([('email', ASCENDING)], unique=True, sparse=True),
                IndexModel([('created_at', DESCENDING)])
            ])
            
            # Skill executions indexes
            await self.collections['skill_executions'].create_indexes([
                IndexModel([('skill_name', ASCENDING)]),
                IndexModel([('user_id', ASCENDING)]),
                IndexModel([('session_id', ASCENDING)]),
                IndexModel([('timestamp', DESCENDING)]),
                IndexModel([('skill_name', ASCENDING), ('timestamp', DESCENDING)]),
                IndexModel([('success', ASCENDING), ('timestamp', DESCENDING)])
            ])
            
            # Devices indexes
            await self.collections['devices'].create_indexes([
                IndexModel([('device_id', ASCENDING)], unique=True),
                IndexModel([('user_id', ASCENDING)]),
                IndexModel([('last_seen', DESCENDING)])
            ])
            
            # Memories indexes
            await self.collections['memories'].create_indexes([
                IndexModel([('user_id', ASCENDING)]),
                IndexModel([('memory_type', ASCENDING)]),
                IndexModel([('timestamp', DESCENDING)]),
                IndexModel([('user_id', ASCENDING), ('memory_type', ASCENDING)]),
                IndexModel([('tags', ASCENDING)])
            ])
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    async def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.is_connected = False
            logger.info("Disconnected from MongoDB")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check.
        
        Returns:
            Health status information
        """
        try:
            if not self.is_connected or not self.client:
                return {
                    'status': 'disconnected',
                    'error': 'No active connection'
                }
            
            # Ping database
            start_time = datetime.now()
            await self.client.admin.command('ping')
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Get server info
            server_info = await self.client.admin.command('buildInfo')
            
            # Get database stats
            db_stats = await self.database.command('dbStats')
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time,
                'server_version': server_info.get('version'),
                'database_size_mb': db_stats.get('dataSize', 0) / (1024 * 1024),
                'collections_count': len(self.collections),
                'connection_pool_size': self._connection_pool_size
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections."""
        stats = {}
        
        try:
            for name, collection in self.collections.items():
                collection_stats = await self.database.command('collStats', name)
                stats[name] = {
                    'count': collection_stats.get('count', 0),
                    'size_mb': collection_stats.get('size', 0) / (1024 * 1024),
                    'avg_obj_size': collection_stats.get('avgObjSize', 0),
                    'indexes': collection_stats.get('nindexes', 0)
                }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            
        return stats
    
    # Collection access methods
    @property
    def conversations(self) -> AsyncIOMotorCollection:
        """Get conversations collection."""
        return self.collections['conversations']
    
    @property
    def users(self) -> AsyncIOMotorCollection:
        """Get users collection."""
        return self.collections['users']
    
    @property
    def skill_executions(self) -> AsyncIOMotorCollection:
        """Get skill executions collection."""
        return self.collections['skill_executions']
    
    @property
    def devices(self) -> AsyncIOMotorCollection:
        """Get devices collection."""
        return self.collections['devices']
    
    @property
    def memories(self) -> AsyncIOMotorCollection:
        """Get memories collection."""
        return self.collections['memories']
    
    @property
    def user_preferences(self) -> AsyncIOMotorCollection:
        """Get user preferences collection."""
        return self.collections['user_preferences']
    
    @property
    def conversation_summaries(self) -> AsyncIOMotorCollection:
        """Get conversation summaries collection."""
        return self.collections['conversation_summaries']
    
    @property
    def skill_analytics(self) -> AsyncIOMotorCollection:
        """Get skill analytics collection."""
        return self.collections['skill_analytics']
    
    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """
        Get a collection by name.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            AsyncIOMotorCollection: The requested collection
            
        Raises:
            KeyError: If collection doesn't exist
        """
        if collection_name not in self.collections:
            raise KeyError(f"Collection '{collection_name}' not found. Available collections: {list(self.collections.keys())}")
        return self.collections[collection_name]
    
    # Database operations
    async def create_document(self, collection_name: str, document: Dict[str, Any]) -> str:
        """
        Create a new document in the specified collection.
        
        Args:
            collection_name: Name of the collection
            document: Document to insert
            
        Returns:
            Inserted document ID
        """
        try:
            collection = self.collections[collection_name]
            document['created_at'] = datetime.utcnow()
            result = await collection.insert_one(document)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create document in {collection_name}: {e}")
            raise
    
    async def find_documents(self, collection_name: str, filter_query: Dict[str, Any] = None, 
                           limit: int = None, sort: List[tuple] = None) -> List[Dict[str, Any]]:
        """
        Find documents in the specified collection.
        
        Args:
            collection_name: Name of the collection
            filter_query: Query filter
            limit: Maximum number of documents to return
            sort: Sort specification
            
        Returns:
            List of matching documents
        """
        try:
            collection = self.collections[collection_name]
            cursor = collection.find(filter_query or {})
            
            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)
                
            documents = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string for JSON serialization
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                    
            return documents
        except Exception as e:
            logger.error(f"Failed to find documents in {collection_name}: {e}")
            raise
    
    async def update_document(self, collection_name: str, filter_query: Dict[str, Any], 
                            update_data: Dict[str, Any]) -> bool:
        """
        Update a document in the specified collection.
        
        Args:
            collection_name: Name of the collection
            filter_query: Query to find document to update
            update_data: Update operations
            
        Returns:
            True if document was updated
        """
        try:
            collection = self.collections[collection_name]
            update_data['updated_at'] = datetime.utcnow()
            result = await collection.update_one(filter_query, {'$set': update_data})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update document in {collection_name}: {e}")
            raise
    
    async def delete_document(self, collection_name: str, filter_query: Dict[str, Any]) -> bool:
        """
        Delete a document from the specified collection.
        
        Args:
            collection_name: Name of the collection
            filter_query: Query to find document to delete
            
        Returns:
            True if document was deleted
        """
        try:
            collection = self.collections[collection_name]
            result = await collection.delete_one(filter_query)
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete document in {collection_name}: {e}")
            raise
    
    async def aggregate(self, collection_name: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Perform aggregation query on the specified collection.
        
        Args:
            collection_name: Name of the collection
            pipeline: Aggregation pipeline
            
        Returns:
            Aggregation results
        """
        try:
            collection = self.collections[collection_name]
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            # Convert ObjectId to string for JSON serialization
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                    
            return results
        except Exception as e:
            logger.error(f"Failed to perform aggregation in {collection_name}: {e}")
            raise
    
    async def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            self.is_connected = False
            logger.info("MongoDB connection closed")
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            stats = await self.database.command("dbStats")
            return {
                'database': stats.get('db'),
                'collections': stats.get('collections', 0),
                'dataSize': stats.get('dataSize', 0),
                'storageSize': stats.get('storageSize', 0),
                'indexes': stats.get('indexes', 0),
                'indexSize': stats.get('indexSize', 0),
                'objects': stats.get('objects', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    async def list_collections(self) -> List[str]:
        """List all collections in the database."""
        try:
            collections = await self.database.list_collection_names()
            return collections
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
