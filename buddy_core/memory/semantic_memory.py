"""
BUDDY 2.0 Semantic Memory Engine
Advanced context storage and retrieval using vector databases

This implementation provides JARVIS-level memory capabilities:
- Pinecone/ChromaDB vector storage for semantic search
- Conversation context indexing and retrieval
- User preference learning and adaptation
- Cross-session memory persistence
"""

import os
import json
import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

# Vector database imports
try:
    from pinecone import Pinecone, ServerlessSpec
    import chromadb
    from chromadb.config import Settings
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False

# ML imports for embeddings
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False

# Local imports
from mongodb_integration import BuddyDatabase

logger = logging.getLogger(__name__)

class SemanticMemoryEngine:
    """
    Advanced semantic memory engine for BUDDY AI assistant.
    Provides context-aware conversation storage and retrieval.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.initialized = False
        
        # Vector database clients
        self.pinecone_client = None
        self.chroma_client = None
        self.vector_index = None
        
        # Embedding model
        self.sentence_model = None
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 dimension
        
        # Local storage for fallback
        self.local_memory = {}
        self.faiss_index = None
        
        # Database connections
        self.conversation_db = None
        self.analytics_db = None
        
        # Memory configuration
        self.max_context_length = self.config.get('max_context_length', 10)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.7)
        self.max_memories_per_query = self.config.get('max_memories_per_query', 5)
        
    async def initialize(self, conversation_db: Optional[BuddyDatabase] = None) -> bool:
        """Initialize the semantic memory engine with vector databases"""
        logger.info("Initializing Semantic Memory Engine...")
        
        try:
            # Set database connections
            self.conversation_db = conversation_db
            
            # Initialize embedding model
            if EMBEDDING_AVAILABLE:
                self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Sentence transformer model loaded")
            else:
                logger.warning("Embedding dependencies not available, using fallback")
            
            # Initialize vector databases
            await self._initialize_vector_dbs()
            
            # Initialize fallback storage
            await self._initialize_fallback_storage()
            
            self.initialized = True
            logger.info("Semantic Memory Engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Semantic Memory Engine: {e}")
            self.initialized = False
            return False
    
    async def _initialize_vector_dbs(self):
        """Initialize Pinecone and ChromaDB vector databases"""
        
        # Initialize Pinecone if configured
        pinecone_api_key = self.config.get('pinecone_api_key') or os.getenv('PINECONE_API_KEY')
        if pinecone_api_key and VECTOR_DB_AVAILABLE:
            try:
                # Initialize Pinecone client (v3+ API)
                pc = Pinecone(api_key=pinecone_api_key)
                
                index_name = self.config.get('pinecone_index', 'buddy-conversations')
                
                # Create index if it doesn't exist
                existing_indexes = [idx.name for idx in pc.list_indexes()]
                if index_name not in existing_indexes:
                    pc.create_index(
                        name=index_name,
                        dimension=self.embedding_dimension,
                        metric='cosine',
                        spec=ServerlessSpec(
                            cloud='aws',
                            region='us-east-1'
                        )
                    )
                    logger.info(f"Created Pinecone index: {index_name}")
                
                self.vector_index = pc.Index(index_name)
                logger.info("Pinecone vector database connected")
                
            except Exception as e:
                logger.warning(f"Pinecone initialization failed: {e}")
        
        # Initialize ChromaDB as local fallback
        if VECTOR_DB_AVAILABLE:
            try:
                persist_directory = self.config.get('chroma_persist_dir', './buddy_memory')
                
                self.chroma_client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=persist_directory
                ))
                
                # Get or create conversation collection
                self.conversation_collection = self.chroma_client.get_or_create_collection(
                    name="buddy_conversations",
                    metadata={"description": "BUDDY conversation memory and context"}
                )
                
                # Get or create user preference collection
                self.preference_collection = self.chroma_client.get_or_create_collection(
                    name="user_preferences",
                    metadata={"description": "User preferences and behavioral patterns"}
                )
                
                logger.info("ChromaDB vector database connected")
                
            except Exception as e:
                logger.warning(f"ChromaDB initialization failed: {e}")
    
    async def _initialize_fallback_storage(self):
        """Initialize FAISS for local vector storage as ultimate fallback"""
        if EMBEDDING_AVAILABLE:
            try:
                # Create FAISS index for local storage
                self.faiss_index = faiss.IndexFlatIP(self.embedding_dimension)  # Inner product for cosine similarity
                logger.info("FAISS fallback storage initialized")
            except Exception as e:
                logger.warning(f"FAISS initialization failed: {e}")
    
    async def store_conversation_context(self, conversation: Dict[str, Any]) -> str:
        """
        Store conversation with semantic indexing for future retrieval
        
        Args:
            conversation: Dict containing conversation data
            
        Returns:
            Storage ID for the conversation
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            conversation_id = conversation.get('id', str(uuid.uuid4()))
            content = conversation.get('content', '')
            
            # Generate embedding for semantic search
            embedding = await self._generate_embedding(content)
            
            # Prepare metadata
            metadata = {
                'conversation_id': conversation_id,
                'user_id': conversation.get('user_id', ''),
                'session_id': conversation.get('session_id', ''),
                'intent': conversation.get('intent', ''),
                'timestamp': conversation.get('timestamp', datetime.utcnow().isoformat()),
                'device_type': conversation.get('device_type', ''),
                'platform': conversation.get('platform', ''),
                'response_satisfaction': conversation.get('satisfaction_score', 0),
                'content_preview': content[:100],
                'content_length': len(content),
                'entities': json.dumps(conversation.get('entities', {})),
                'context_type': self._determine_context_type(conversation)
            }
            
            # Store in primary vector database (Pinecone)
            if self.vector_index:
                await self._store_in_pinecone(conversation_id, embedding, metadata)
            
            # Store in local vector database (ChromaDB)
            if hasattr(self, 'conversation_collection'):
                await self._store_in_chromadb(conversation_id, content, embedding, metadata)
            
            # Store in relational database for full context
            if self.conversation_db:
                await self._store_in_relational_db(conversation)
            
            # Update FAISS fallback
            if self.faiss_index is not None:
                await self._store_in_faiss(conversation_id, embedding, metadata)
            
            logger.debug(f"Stored conversation context: {conversation_id}")
            return conversation_id
            
        except Exception as e:
            logger.error(f"Failed to store conversation context: {e}")
            return ""
    
    async def recall_relevant_context(self, query: str, user_id: str, 
                                    session_id: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        Retrieve semantically relevant conversation context
        
        Args:
            query: Search query for relevant context
            user_id: User identifier for personalized results
            session_id: Optional session filter
            limit: Maximum number of results to return
            
        Returns:
            List of relevant conversation contexts with similarity scores
        """
        if not self.initialized:
            await self.initialize()
        
        limit = limit or self.max_memories_per_query
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            
            # Search in vector databases
            results = []
            
            # Search Pinecone (primary)
            if self.vector_index:
                pinecone_results = await self._search_pinecone(query_embedding, user_id, session_id, limit)
                results.extend(pinecone_results)
            
            # Search ChromaDB (fallback)
            elif hasattr(self, 'conversation_collection'):
                chroma_results = await self._search_chromadb(query, query_embedding, user_id, session_id, limit)
                results.extend(chroma_results)
            
            # Search FAISS (ultimate fallback)
            elif self.faiss_index is not None:
                faiss_results = await self._search_faiss(query_embedding, user_id, limit)
                results.extend(faiss_results)
            
            # Enrich results with full conversation data
            enriched_results = await self._enrich_search_results(results)
            
            # Filter by relevance threshold and rank
            filtered_results = [
                result for result in enriched_results 
                if result.get('relevance_score', 0) >= self.similarity_threshold
            ]
            
            # Sort by relevance and recency
            sorted_results = sorted(
                filtered_results,
                key=lambda x: (x.get('relevance_score', 0), x.get('time_relevance', 0)),
                reverse=True
            )
            
            return sorted_results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to recall relevant context: {e}")
            return []
    
    async def learn_user_preferences(self, user_id: str, interaction_data: Dict[str, Any]):
        """
        Learn and update user preferences based on interaction patterns
        
        Args:
            user_id: User identifier
            interaction_data: Data about user interaction and feedback
        """
        try:
            # Extract preference signals
            preferences = {
                'response_style': interaction_data.get('response_style_preference'),
                'detail_level': interaction_data.get('preferred_detail_level'),
                'interaction_speed': interaction_data.get('preferred_response_speed'),
                'content_type': interaction_data.get('preferred_content_type'),
                'communication_style': interaction_data.get('communication_style'),
                'topics_of_interest': interaction_data.get('topics_discussed', []),
                'device_preferences': interaction_data.get('device_usage_patterns', {}),
                'time_patterns': interaction_data.get('interaction_time_patterns', {}),
                'satisfaction_feedback': interaction_data.get('satisfaction_scores', [])
            }
            
            # Generate preference embedding
            preference_text = self._create_preference_text(preferences)
            preference_embedding = await self._generate_embedding(preference_text)
            
            # Store in preference collection
            preference_id = f"{user_id}_preferences_{datetime.utcnow().timestamp()}"
            
            if hasattr(self, 'preference_collection'):
                self.preference_collection.upsert(
                    documents=[preference_text],
                    embeddings=[preference_embedding.tolist()],
                    metadatas=[{
                        'user_id': user_id,
                        'timestamp': datetime.utcnow().isoformat(),
                        'preferences': json.dumps(preferences),
                        'learning_session': interaction_data.get('session_id', ''),
                        'confidence': interaction_data.get('confidence', 0.8)
                    }],
                    ids=[preference_id]
                )
            
            logger.debug(f"Updated user preferences for {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to learn user preferences: {e}")
    
    async def get_user_context_summary(self, user_id: str, days_back: int = 7) -> Dict[str, Any]:
        """
        Generate a summary of user's recent interaction context
        
        Args:
            user_id: User identifier
            days_back: Number of days to look back for context
            
        Returns:
            Context summary with patterns and preferences
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Search for recent conversations
            recent_context = await self.recall_relevant_context(
                query="recent interactions and preferences",
                user_id=user_id,
                limit=20
            )
            
            # Filter by date
            recent_conversations = [
                ctx for ctx in recent_context
                if datetime.fromisoformat(ctx.get('timestamp', '1970-01-01')) >= cutoff_date
            ]
            
            # Analyze patterns
            summary = {
                'user_id': user_id,
                'analysis_period': f"{days_back} days",
                'total_interactions': len(recent_conversations),
                'common_intents': self._analyze_intent_patterns(recent_conversations),
                'interaction_times': self._analyze_time_patterns(recent_conversations),
                'device_usage': self._analyze_device_patterns(recent_conversations),
                'satisfaction_trend': self._analyze_satisfaction_trend(recent_conversations),
                'topic_interests': self._analyze_topic_interests(recent_conversations),
                'response_preferences': self._analyze_response_preferences(recent_conversations),
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate user context summary: {e}")
            return {}
    
    async def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate text embedding using sentence transformer"""
        if self.sentence_model and text:
            try:
                embedding = self.sentence_model.encode([text])
                return embedding[0]
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}")
        
        # Fallback: simple hash-based embedding
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        # Convert to float array (simplified)
        embedding = np.array([float(b) / 255.0 for b in hash_bytes[:self.embedding_dimension]])
        return embedding
    
    def _determine_context_type(self, conversation: Dict[str, Any]) -> str:
        """Determine the type of conversation context"""
        intent = conversation.get('intent', '')
        content = conversation.get('content', '').lower()
        
        if intent.startswith('email_'):
            return 'communication'
        elif intent.startswith('calendar_') or intent.startswith('reminder_'):
            return 'scheduling'
        elif intent.startswith('weather_'):
            return 'information'
        elif intent.startswith('music_') or intent.startswith('video_'):
            return 'entertainment'
        elif intent.startswith('smart_home_') or intent.startswith('device_'):
            return 'control'
        elif 'question' in intent or '?' in content:
            return 'inquiry'
        else:
            return 'general'
    
    async def _store_in_pinecone(self, conversation_id: str, embedding: np.ndarray, metadata: Dict):
        """Store conversation in Pinecone vector database"""
        try:
            self.vector_index.upsert(
                vectors=[{
                    'id': conversation_id,
                    'values': embedding.tolist(),
                    'metadata': metadata
                }]
            )
        except Exception as e:
            logger.warning(f"Pinecone storage failed: {e}")
    
    async def _store_in_chromadb(self, conversation_id: str, content: str, 
                               embedding: np.ndarray, metadata: Dict):
        """Store conversation in ChromaDB"""
        try:
            self.conversation_collection.upsert(
                documents=[content],
                embeddings=[embedding.tolist()],
                metadatas=[metadata],
                ids=[conversation_id]
            )
        except Exception as e:
            logger.warning(f"ChromaDB storage failed: {e}")
    
    async def _store_in_relational_db(self, conversation: Dict[str, Any]):
        """Store full conversation in relational database"""
        if self.conversation_db and hasattr(self.conversation_db, 'save_conversation'):
            try:
                await self.conversation_db.save_conversation(
                    session_id=conversation.get('session_id', ''),
                    user_id=conversation.get('user_id', ''),
                    role=conversation.get('role', 'user'),
                    content=conversation.get('content', ''),
                    metadata=conversation.get('metadata', {})
                )
            except Exception as e:
                logger.warning(f"Relational DB storage failed: {e}")
    
    async def _store_in_faiss(self, conversation_id: str, embedding: np.ndarray, metadata: Dict):
        """Store conversation in FAISS index as fallback"""
        try:
            # Normalize embedding for cosine similarity
            norm = np.linalg.norm(embedding)
            if norm > 0:
                normalized_embedding = embedding / norm
                self.faiss_index.add(normalized_embedding.reshape(1, -1))
                
                # Store metadata separately (FAISS doesn't store metadata)
                if conversation_id not in self.local_memory:
                    self.local_memory[conversation_id] = metadata
                    
        except Exception as e:
            logger.warning(f"FAISS storage failed: {e}")
    
    async def _search_pinecone(self, query_embedding: np.ndarray, user_id: str, 
                             session_id: str, limit: int) -> List[Dict]:
        """Search Pinecone for relevant conversations"""
        try:
            filter_dict = {'user_id': {'$eq': user_id}}
            if session_id:
                filter_dict['session_id'] = {'$eq': session_id}
            
            response = self.vector_index.query(
                vector=query_embedding.tolist(),
                top_k=limit,
                filter=filter_dict,
                include_metadata=True
            )
            
            results = []
            for match in response['matches']:
                results.append({
                    'conversation_id': match['id'],
                    'relevance_score': float(match['score']),
                    'metadata': match['metadata'],
                    'source': 'pinecone'
                })
            
            return results
            
        except Exception as e:
            logger.warning(f"Pinecone search failed: {e}")
            return []
    
    async def _search_chromadb(self, query: str, query_embedding: np.ndarray, 
                             user_id: str, session_id: str, limit: int) -> List[Dict]:
        """Search ChromaDB for relevant conversations"""
        try:
            # Build filter
            where_filter = {'user_id': {'$eq': user_id}}
            if session_id:
                where_filter['session_id'] = {'$eq': session_id}
            
            results = self.conversation_collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter,
                include=['metadatas', 'documents', 'distances']
            )
            
            search_results = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    
                    search_results.append({
                        'conversation_id': results['ids'][0][i],
                        'relevance_score': 1.0 - distance,  # Convert distance to similarity
                        'metadata': metadata,
                        'document': doc,
                        'source': 'chromadb'
                    })
            
            return search_results
            
        except Exception as e:
            logger.warning(f"ChromaDB search failed: {e}")
            return []
    
    async def _search_faiss(self, query_embedding: np.ndarray, user_id: str, limit: int) -> List[Dict]:
        """Search FAISS index for relevant conversations"""
        try:
            # Normalize query embedding
            norm = np.linalg.norm(query_embedding)
            if norm > 0:
                normalized_query = (query_embedding / norm).reshape(1, -1)
                
                # Search FAISS index
                scores, indices = self.faiss_index.search(normalized_query, limit)
                
                results = []
                for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                    if idx != -1:  # Valid index
                        # Find conversation ID from local memory (simplified)
                        conversation_id = f"faiss_{idx}"
                        metadata = self.local_memory.get(conversation_id, {})
                        
                        # Filter by user_id
                        if metadata.get('user_id') == user_id:
                            results.append({
                                'conversation_id': conversation_id,
                                'relevance_score': float(score),
                                'metadata': metadata,
                                'source': 'faiss'
                            })
                
                return results
                
        except Exception as e:
            logger.warning(f"FAISS search failed: {e}")
            return []
    
    async def _enrich_search_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """Enrich search results with additional context and scoring"""
        enriched_results = []
        
        for result in results:
            try:
                metadata = result.get('metadata', {})
                timestamp_str = metadata.get('timestamp', '')
                
                # Calculate time relevance
                time_relevance = self._calculate_time_relevance(timestamp_str)
                
                # Calculate context relevance
                context_relevance = self._calculate_context_relevance(metadata)
                
                # Combine scores
                combined_score = (
                    result.get('relevance_score', 0) * 0.6 +
                    time_relevance * 0.2 +
                    context_relevance * 0.2
                )
                
                enriched_result = {
                    **result,
                    'time_relevance': time_relevance,
                    'context_relevance': context_relevance,
                    'combined_score': combined_score,
                    'timestamp': timestamp_str,
                    'intent': metadata.get('intent', ''),
                    'context_type': metadata.get('context_type', ''),
                    'satisfaction_score': metadata.get('response_satisfaction', 0)
                }
                
                enriched_results.append(enriched_result)
                
            except Exception as e:
                logger.warning(f"Failed to enrich result: {e}")
                enriched_results.append(result)
        
        return enriched_results
    
    def _calculate_time_relevance(self, timestamp_str: str) -> float:
        """Calculate time-based relevance score"""
        if not timestamp_str:
            return 0.0
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=timestamp.tzinfo)
            
            # Time difference in days
            time_diff = (now - timestamp).total_seconds() / (24 * 3600)
            
            # Exponential decay: more recent = higher score
            relevance = max(0.0, 1.0 - (time_diff / 30.0))  # 30-day decay
            return relevance
            
        except Exception:
            return 0.0
    
    def _calculate_context_relevance(self, metadata: Dict) -> float:
        """Calculate context-based relevance score"""
        score = 0.0
        
        # Higher score for successful interactions
        satisfaction = metadata.get('response_satisfaction', 0)
        if satisfaction > 0:
            score += satisfaction * 0.3
        
        # Higher score for specific intents vs general chat
        intent = metadata.get('intent', '')
        if intent and intent != 'small_talk':
            score += 0.3
        
        # Higher score for longer, more substantial content
        content_length = metadata.get('content_length', 0)
        if content_length > 50:
            score += min(0.4, content_length / 500.0)
        
        return min(score, 1.0)
    
    def _create_preference_text(self, preferences: Dict) -> str:
        """Create searchable text from user preferences"""
        pref_parts = []
        
        for key, value in preferences.items():
            if value:
                if isinstance(value, list):
                    pref_parts.append(f"{key}: {', '.join(map(str, value))}")
                else:
                    pref_parts.append(f"{key}: {value}")
        
        return "; ".join(pref_parts)
    
    def _analyze_intent_patterns(self, conversations: List[Dict]) -> Dict[str, int]:
        """Analyze common intent patterns in conversations"""
        intent_counts = {}
        for conv in conversations:
            intent = conv.get('metadata', {}).get('intent', 'unknown')
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        return dict(sorted(intent_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _analyze_time_patterns(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Analyze interaction time patterns"""
        times = []
        for conv in conversations:
            timestamp_str = conv.get('timestamp', '')
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                times.append(timestamp.hour)
            except Exception:
                continue
        
        if times:
            return {
                'most_active_hour': max(set(times), key=times.count),
                'hour_distribution': {str(hour): times.count(hour) for hour in set(times)},
                'total_interactions': len(times)
            }
        return {}
    
    def _analyze_device_patterns(self, conversations: List[Dict]) -> Dict[str, int]:
        """Analyze device usage patterns"""
        device_counts = {}
        for conv in conversations:
            device = conv.get('metadata', {}).get('device_type', 'unknown')
            device_counts[device] = device_counts.get(device, 0) + 1
        
        return device_counts
    
    def _analyze_satisfaction_trend(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Analyze satisfaction score trends"""
        scores = []
        for conv in conversations:
            score = conv.get('metadata', {}).get('response_satisfaction', 0)
            if score > 0:
                scores.append(score)
        
        if scores:
            return {
                'average_satisfaction': sum(scores) / len(scores),
                'satisfaction_trend': 'improving' if len(scores) > 1 and scores[-1] > scores[0] else 'stable',
                'total_rated_interactions': len(scores)
            }
        return {}
    
    def _analyze_topic_interests(self, conversations: List[Dict]) -> List[str]:
        """Analyze topics of interest from conversations"""
        topics = set()
        for conv in conversations:
            context_type = conv.get('metadata', {}).get('context_type', '')
            if context_type:
                topics.add(context_type)
        
        return list(topics)
    
    def _analyze_response_preferences(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Analyze response style preferences"""
        # This would analyze response lengths, styles, etc.
        # Simplified for now
        total_conversations = len(conversations)
        detailed_responses = sum(
            1 for conv in conversations 
            if conv.get('metadata', {}).get('content_length', 0) > 100
        )
        
        return {
            'prefers_detailed_responses': detailed_responses / total_conversations > 0.6 if total_conversations > 0 else False,
            'response_detail_ratio': detailed_responses / total_conversations if total_conversations > 0 else 0
        }

# Global instance
semantic_memory_engine = SemanticMemoryEngine()

async def get_semantic_memory_engine(config: Dict = None, 
                                   conversation_db: BuddyDatabase = None) -> SemanticMemoryEngine:
    """Get the global semantic memory engine instance"""
    if config:
        semantic_memory_engine.config.update(config)
    
    if not semantic_memory_engine.initialized:
        await semantic_memory_engine.initialize(conversation_db)
    
    return semantic_memory_engine
