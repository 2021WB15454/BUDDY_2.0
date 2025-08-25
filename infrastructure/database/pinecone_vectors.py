"""
BUDDY 2.0 Pinecone Vector Database Implementation
===============================================

Vector database management for semantic search, conversation context,
and intelligent memory retrieval across all platforms.

Features:
- Multi-tenant vector isolation
- Conversation embeddings with metadata
- Semantic search and context retrieval
- Cross-device conversation continuity
- Performance optimization for real-time queries
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import hashlib
import json
from dataclasses import dataclass, asdict

# Import dependencies (install with: pip install pinecone sentence-transformers)
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    print("⚠️ Pinecone not available. Install with: pip install pinecone")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️ SentenceTransformers not available. Install with: pip install sentence-transformers")

from .mongodb_schemas import ConversationSchema, MessageType, DeviceType

logger = logging.getLogger(__name__)


@dataclass
class VectorMetadata:
    """Metadata structure for vector storage"""
    user_id: str
    device_id: str
    conversation_id: str
    session_id: str
    message_type: str
    timestamp: str
    intent: Optional[str] = None
    device_type: Optional[str] = None
    language: str = "en"
    content_hash: Optional[str] = None
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_version: str = "v1"


@dataclass
class VectorSearchResult:
    """Search result from vector database"""
    id: str
    score: float
    metadata: Dict[str, Any]
    content: str
    conversation_id: str
    timestamp: datetime


class BuddyVectorDatabase:
    """
    BUDDY 2.0 Vector Database Manager
    
    Handles conversation embeddings, semantic search, and context retrieval
    with multi-tenant isolation and cross-device synchronization.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: str = "us-west1-gcp",
        embedding_model: str = "all-MiniLM-L6-v2",
        dimension: int = 384
    ):
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.environment = environment
        self.embedding_model_name = embedding_model
        self.dimension = dimension
        self.embedding_model = None
        self.pc = None
        self.indexes = {}
        
        # Index configurations
        self.index_configs = {
            "buddy-conversations": {
                "dimension": 384,
                "metric": "cosine",
                "spec": ServerlessSpec(
                    cloud="aws",
                    region="us-west-2"
                )
            },
            "buddy-contexts": {
                "dimension": 384,
                "metric": "cosine",
                "spec": ServerlessSpec(
                    cloud="aws", 
                    region="us-west-2"
                )
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize Pinecone connection and embedding model"""
        try:
            if not PINECONE_AVAILABLE:
                logger.error("Pinecone client not available")
                return False
            
            if not self.api_key:
                logger.error("Pinecone API key not provided")
                return False
            
            # Initialize Pinecone
            self.pc = Pinecone(api_key=self.api_key)
            
            # Initialize embedding model
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                logger.info(f"Loaded embedding model: {self.embedding_model_name}")
            else:
                logger.warning("SentenceTransformers not available, using fallback")
                return False
            
            # Create indexes if they don't exist
            await self._ensure_indexes_exist()
            
            logger.info("✅ Vector database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            return False
    
    async def _ensure_indexes_exist(self):
        """Create Pinecone indexes if they don't exist"""
        try:
            existing_indexes = [index.name for index in self.pc.list_indexes()]
            
            for index_name, config in self.index_configs.items():
                if index_name not in existing_indexes:
                    logger.info(f"Creating Pinecone index: {index_name}")
                    self.pc.create_index(
                        name=index_name,
                        dimension=config["dimension"],
                        metric=config["metric"],
                        spec=config["spec"]
                    )
                
                # Connect to index
                self.indexes[index_name] = self.pc.Index(index_name)
                logger.info(f"Connected to index: {index_name}")
                
        except Exception as e:
            logger.error(f"Error ensuring indexes exist: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        try:
            if self.embedding_model is None:
                raise ValueError("Embedding model not initialized")
            
            # Clean and prepare text
            cleaned_text = text.strip()[:8000]  # Limit text length
            
            # Generate embedding
            embedding = self.embedding_model.encode(cleaned_text)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def _generate_vector_id(self, user_id: str, conversation_id: str) -> str:
        """Generate unique vector ID"""
        return f"{user_id}_{conversation_id}"
    
    def _create_content_hash(self, content: str) -> str:
        """Create hash of content for deduplication"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def upsert_conversation_vector(
        self,
        conversation: ConversationSchema,
        index_name: str = "buddy-conversations"
    ) -> bool:
        """Store conversation vector in Pinecone"""
        try:
            if index_name not in self.indexes:
                logger.error(f"Index {index_name} not found")
                return False
            
            # Generate embedding
            embedding = self.generate_embedding(conversation.content)
            
            # Create metadata
            metadata = VectorMetadata(
                user_id=conversation.user_id,
                device_id=conversation.device_id,
                conversation_id=conversation._id,
                session_id=conversation.session_id,
                message_type=conversation.message_type.value,
                timestamp=conversation.timestamp.isoformat(),
                intent=conversation.metadata.intent,
                device_type=conversation.device_id.split('_')[1] if '_' in conversation.device_id else "unknown",
                language=conversation.language,
                content_hash=self._create_content_hash(conversation.content),
                embedding_model=self.embedding_model_name
            )
            
            # Generate vector ID
            vector_id = self._generate_vector_id(conversation.user_id, conversation._id)
            
            # Upsert to Pinecone
            index = self.indexes[index_name]
            index.upsert([{
                'id': vector_id,
                'values': embedding,
                'metadata': asdict(metadata)
            }])
            
            logger.debug(f"Upserted vector for conversation {conversation._id}")
            return True
            
        except Exception as e:
            logger.error(f"Error upserting conversation vector: {e}")
            return False
    
    async def batch_upsert_conversations(
        self,
        conversations: List[ConversationSchema],
        index_name: str = "buddy-conversations",
        batch_size: int = 100
    ) -> Dict[str, int]:
        """Batch upsert multiple conversation vectors"""
        try:
            if index_name not in self.indexes:
                logger.error(f"Index {index_name} not found")
                return {"success": 0, "failed": 0}
            
            index = self.indexes[index_name]
            success_count = 0
            failed_count = 0
            
            # Process in batches
            for i in range(0, len(conversations), batch_size):
                batch = conversations[i:i + batch_size]
                vectors = []
                
                for conversation in batch:
                    try:
                        # Generate embedding
                        embedding = self.generate_embedding(conversation.content)
                        
                        # Create metadata
                        metadata = VectorMetadata(
                            user_id=conversation.user_id,
                            device_id=conversation.device_id,
                            conversation_id=conversation._id,
                            session_id=conversation.session_id,
                            message_type=conversation.message_type.value,
                            timestamp=conversation.timestamp.isoformat(),
                            intent=conversation.metadata.intent,
                            content_hash=self._create_content_hash(conversation.content)
                        )
                        
                        # Generate vector ID
                        vector_id = self._generate_vector_id(conversation.user_id, conversation._id)
                        
                        vectors.append({
                            'id': vector_id,
                            'values': embedding,
                            'metadata': asdict(metadata)
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing conversation {conversation._id}: {e}")
                        failed_count += 1
                
                # Upsert batch
                if vectors:
                    index.upsert(vectors)
                    success_count += len(vectors)
                    logger.debug(f"Upserted batch of {len(vectors)} vectors")
            
            logger.info(f"Batch upsert complete: {success_count} success, {failed_count} failed")
            return {"success": success_count, "failed": failed_count}
            
        except Exception as e:
            logger.error(f"Error in batch upsert: {e}")
            return {"success": 0, "failed": len(conversations)}
    
    async def search_conversations(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        index_name: str = "buddy-conversations"
    ) -> List[VectorSearchResult]:
        """Search for relevant conversations using semantic similarity"""
        try:
            if index_name not in self.indexes:
                logger.error(f"Index {index_name} not found")
                return []
            
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            # Build filter for user isolation
            filter_dict = {"user_id": {"$eq": user_id}}
            
            # Add additional filters
            if filter_metadata:
                filter_dict.update(filter_metadata)
            
            # Search in Pinecone
            index = self.indexes[index_name]
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                filter=filter_dict,
                include_metadata=True
            )
            
            # Convert to structured results
            search_results = []
            for match in results.matches:
                result = VectorSearchResult(
                    id=match.id,
                    score=match.score,
                    metadata=match.metadata,
                    content=match.metadata.get('content', ''),
                    conversation_id=match.metadata.get('conversation_id', ''),
                    timestamp=datetime.fromisoformat(match.metadata.get('timestamp', ''))
                )
                search_results.append(result)
            
            logger.debug(f"Found {len(search_results)} relevant conversations")
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            return []
    
    async def get_conversation_context(
        self,
        user_id: str,
        session_id: str,
        query: str,
        context_window: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[VectorSearchResult]:
        """Get relevant conversation context for current session"""
        try:
            # Search recent conversations in the same session
            session_filter = {
                "session_id": {"$eq": session_id}
            }
            
            session_results = await self.search_conversations(
                query=query,
                user_id=user_id,
                top_k=context_window,
                filter_metadata=session_filter
            )
            
            # If not enough context from current session, search across all conversations
            if len(session_results) < context_window // 2:
                global_results = await self.search_conversations(
                    query=query,
                    user_id=user_id,
                    top_k=context_window - len(session_results)
                )
                
                # Combine and deduplicate results
                all_results = session_results + global_results
                seen_ids = set()
                unique_results = []
                
                for result in all_results:
                    if result.id not in seen_ids:
                        seen_ids.add(result.id)
                        unique_results.append(result)
                
                session_results = unique_results
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in session_results 
                if result.score >= similarity_threshold
            ]
            
            logger.debug(f"Retrieved {len(filtered_results)} context conversations")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return []
    
    async def search_by_device_type(
        self,
        user_id: str,
        device_type: str,
        query: str,
        top_k: int = 5
    ) -> List[VectorSearchResult]:
        """Search conversations from specific device type"""
        filter_metadata = {
            "device_type": {"$eq": device_type}
        }
        
        return await self.search_conversations(
            query=query,
            user_id=user_id,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
    
    async def search_by_time_range(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        query: str,
        top_k: int = 5
    ) -> List[VectorSearchResult]:
        """Search conversations within time range"""
        filter_metadata = {
            "timestamp": {
                "$gte": start_time.isoformat(),
                "$lte": end_time.isoformat()
            }
        }
        
        return await self.search_conversations(
            query=query,
            user_id=user_id,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
    
    async def delete_user_vectors(
        self,
        user_id: str,
        index_name: str = "buddy-conversations"
    ) -> bool:
        """Delete all vectors for a user (GDPR compliance)"""
        try:
            if index_name not in self.indexes:
                logger.error(f"Index {index_name} not found")
                return False
            
            # Query all vectors for the user
            index = self.indexes[index_name]
            
            # Note: This is a simplified approach. In production, you might need
            # to implement a more efficient batch deletion strategy
            results = index.query(
                vector=[0.0] * self.dimension,  # Dummy vector
                filter={"user_id": {"$eq": user_id}},
                top_k=10000,  # Large number to get all results
                include_metadata=False
            )
            
            # Extract IDs and delete
            vector_ids = [match.id for match in results.matches]
            
            if vector_ids:
                index.delete(ids=vector_ids)
                logger.info(f"Deleted {len(vector_ids)} vectors for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user vectors: {e}")
            return False
    
    async def get_index_stats(self, index_name: str = "buddy-conversations") -> Dict[str, Any]:
        """Get statistics about the vector index"""
        try:
            if index_name not in self.indexes:
                return {"error": f"Index {index_name} not found"}
            
            index = self.indexes[index_name]
            stats = index.describe_index_stats()
            
            return {
                "index_name": index_name,
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
            
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check vector database health"""
        try:
            if not self.pc:
                return {"status": "error", "message": "Pinecone client not initialized"}
            
            # Check if we can list indexes
            indexes = [index.name for index in self.pc.list_indexes()]
            
            # Check embedding model
            embedding_status = "available" if self.embedding_model else "unavailable"
            
            # Test embedding generation
            try:
                test_embedding = self.generate_embedding("test")
                embedding_test = "passed"
            except Exception:
                embedding_test = "failed"
            
            return {
                "status": "healthy",
                "pinecone_connected": True,
                "available_indexes": indexes,
                "embedding_model": self.embedding_model_name,
                "embedding_status": embedding_status,
                "embedding_test": embedding_test,
                "dimension": self.dimension
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "pinecone_connected": False
            }


class VectorDatabaseManager:
    """High-level manager for vector database operations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.vector_db = BuddyVectorDatabase(
            api_key=config.get("pinecone_api_key"),
            environment=config.get("pinecone_environment", "us-west1-gcp"),
            embedding_model=config.get("embedding_model", "all-MiniLM-L6-v2")
        )
    
    async def initialize(self) -> bool:
        """Initialize vector database"""
        return await self.vector_db.initialize()
    
    async def sync_conversation(self, conversation: ConversationSchema) -> bool:
        """Sync a single conversation to vector database"""
        return await self.vector_db.upsert_conversation_vector(conversation)
    
    async def search_semantic(
        self,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Perform semantic search across conversations"""
        return await self.vector_db.search_conversations(
            query=query,
            user_id=user_id,
            filter_metadata=filters
        )
    
    async def get_smart_context(
        self,
        user_id: str,
        session_id: str,
        current_message: str
    ) -> List[VectorSearchResult]:
        """Get intelligent context for conversation"""
        return await self.vector_db.get_conversation_context(
            user_id=user_id,
            session_id=session_id,
            query=current_message
        )


# Testing and example usage
async def test_vector_database():
    """Test vector database functionality"""
    print("🧪 Testing BUDDY Vector Database")
    print("=" * 40)
    
    # Initialize vector database
    vector_db = BuddyVectorDatabase()
    
    if not await vector_db.initialize():
        print("❌ Failed to initialize vector database")
        return
    
    print("✅ Vector database initialized")
    
    # Health check
    health = await vector_db.health_check()
    print(f"📊 Health Status: {health['status']}")
    
    # Create test conversation
    from .mongodb_schemas import ConversationSchema, MessageType, MessageMetadata
    
    test_conversation = ConversationSchema(
        user_id="test_user",
        session_id="test_session",
        device_id="test_device",
        content="Hello BUDDY, can you help me with my schedule?",
        message_type=MessageType.USER,
        metadata=MessageMetadata(intent="schedule_management")
    )
    
    # Test vector upsert
    success = await vector_db.upsert_conversation_vector(test_conversation)
    print(f"📝 Vector Upsert: {'✅' if success else '❌'}")
    
    # Test search
    results = await vector_db.search_conversations(
        query="help with calendar",
        user_id="test_user"
    )
    print(f"🔍 Search Results: {len(results)} found")
    
    # Test index stats
    stats = await vector_db.get_index_stats()
    print(f"📊 Index Stats: {stats.get('total_vectors', 0)} vectors")
    
    print("🎉 Vector database test complete!")


if __name__ == "__main__":
    asyncio.run(test_vector_database())
