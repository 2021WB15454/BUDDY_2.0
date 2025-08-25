"""
Vector Database Layer - AI Context Memory & Semantic Search

Supports:
- ChromaDB (local/cloud)
- Pinecone (cloud)
- Embedding storage and retrieval
- Semantic similarity search
- Context memory for AI
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
import json
import numpy as np
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class VectorDatabase:
    """Vector database implementation for AI context memory"""
    
    def __init__(self, provider: str = "chroma", config: Dict[str, Any] = None):
        self.provider = provider.lower()
        self.config = config or {}
        self.client = None
        self.collection = None
        self._connected = False
        
    async def initialize(self):
        """Initialize vector database connection"""
        try:
            if self.provider == "chroma":
                await self._initialize_chroma()
            elif self.provider == "pinecone":
                await self._initialize_pinecone()
            else:
                logger.error(f"Unsupported vector database provider: {self.provider}")
                return
                
            logger.info(f"Vector database ({self.provider}) initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            self._connected = False
    
    async def _initialize_chroma(self):
        """Initialize ChromaDB"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Configure ChromaDB
            chroma_config = Settings(
                persist_directory=self.config.get("persist_directory", "./chroma_db"),
                anonymized_telemetry=False
            )
            
            self.client = chromadb.Client(chroma_config)
            
            # Get or create collection
            collection_name = self.config.get("collection_name", "buddy_context")
            try:
                self.collection = self.client.get_collection(collection_name)
            except:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": "BUDDY AI context memory"}
                )
            
            self._connected = True
            
        except ImportError:
            logger.warning("ChromaDB not installed, using fallback vector storage")
            await self._initialize_fallback()
    
    async def _initialize_pinecone(self):
        """Initialize Pinecone"""
        try:
            import pinecone
            
            api_key = self.config.get("api_key")
            environment = self.config.get("environment", "us-west1-gcp")
            
            if not api_key:
                raise ValueError("Pinecone API key not provided")
            
            pinecone.init(api_key=api_key, environment=environment)
            
            index_name = self.config.get("index_name", "buddy-context")
            
            # Check if index exists, create if not
            if index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    index_name,
                    dimension=self.config.get("dimension", 384),
                    metric="cosine"
                )
            
            self.client = pinecone.Index(index_name)
            self._connected = True
            
        except ImportError:
            logger.warning("Pinecone not installed, using fallback vector storage")
            await self._initialize_fallback()
    
    async def _initialize_fallback(self):
        """Initialize fallback in-memory vector storage"""
        self.client = {
            "vectors": {},
            "metadata": {},
            "embeddings": []
        }
        self._connected = True
        logger.info("Using fallback in-memory vector storage")
    
    def is_connected(self) -> bool:
        """Check if vector database is connected"""
        return self._connected
    
    async def store_embedding(self, id: str, embedding: List[float], 
                            metadata: Dict[str, Any] = None) -> bool:
        """Store embedding with metadata"""
        if not self._connected:
            return False
        
        try:
            if self.provider == "chroma":
                return await self._store_chroma(id, embedding, metadata)
            elif self.provider == "pinecone":
                return await self._store_pinecone(id, embedding, metadata)
            else:
                return await self._store_fallback(id, embedding, metadata)
                
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            return False
    
    async def _store_chroma(self, id: str, embedding: List[float], 
                          metadata: Dict[str, Any] = None) -> bool:
        """Store in ChromaDB"""
        self.collection.add(
            embeddings=[embedding],
            ids=[id],
            metadatas=[metadata or {}]
        )
        return True
    
    async def _store_pinecone(self, id: str, embedding: List[float], 
                            metadata: Dict[str, Any] = None) -> bool:
        """Store in Pinecone"""
        self.client.upsert(
            vectors=[(id, embedding, metadata or {})]
        )
        return True
    
    async def _store_fallback(self, id: str, embedding: List[float], 
                            metadata: Dict[str, Any] = None) -> bool:
        """Store in fallback storage"""
        self.client["vectors"][id] = embedding
        self.client["metadata"][id] = metadata or {}
        return True
    
    async def search_similar(self, query_embedding: List[float], 
                           limit: int = 10, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar embeddings"""
        if not self._connected:
            return []
        
        try:
            if self.provider == "chroma":
                return await self._search_chroma(query_embedding, limit, threshold)
            elif self.provider == "pinecone":
                return await self._search_pinecone(query_embedding, limit, threshold)
            else:
                return await self._search_fallback(query_embedding, limit, threshold)
                
        except Exception as e:
            logger.error(f"Failed to search embeddings: {e}")
            return []
    
    async def _search_chroma(self, query_embedding: List[float], 
                           limit: int, threshold: float) -> List[Dict[str, Any]]:
        """Search in ChromaDB"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        
        search_results = []
        if results["ids"]:
            for i, id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = 1 - distance  # Convert distance to similarity
                
                if similarity >= threshold:
                    search_results.append({
                        "id": id,
                        "similarity": similarity,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                    })
        
        return search_results
    
    async def _search_pinecone(self, query_embedding: List[float], 
                             limit: int, threshold: float) -> List[Dict[str, Any]]:
        """Search in Pinecone"""
        results = self.client.query(
            vector=query_embedding,
            top_k=limit,
            include_metadata=True
        )
        
        search_results = []
        for match in results["matches"]:
            if match["score"] >= threshold:
                search_results.append({
                    "id": match["id"],
                    "similarity": match["score"],
                    "metadata": match.get("metadata", {})
                })
        
        return search_results
    
    async def _search_fallback(self, query_embedding: List[float], 
                             limit: int, threshold: float) -> List[Dict[str, Any]]:
        """Search in fallback storage using cosine similarity"""
        import numpy as np
        
        if not self.client["vectors"]:
            return []
        
        query_vec = np.array(query_embedding)
        similarities = []
        
        for id, embedding in self.client["vectors"].items():
            stored_vec = np.array(embedding)
            
            # Cosine similarity
            dot_product = np.dot(query_vec, stored_vec)
            norm_query = np.linalg.norm(query_vec)
            norm_stored = np.linalg.norm(stored_vec)
            
            if norm_query > 0 and norm_stored > 0:
                similarity = dot_product / (norm_query * norm_stored)
                
                if similarity >= threshold:
                    similarities.append({
                        "id": id,
                        "similarity": float(similarity),
                        "metadata": self.client["metadata"].get(id, {})
                    })
        
        # Sort by similarity and limit results
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:limit]
    
    async def store_context(self, user_id: str, content: str, 
                          context_type: str = "general", 
                          metadata: Dict[str, Any] = None) -> str:
        """Store context with automatic embedding generation"""
        import uuid
        
        # Generate embedding (placeholder - use actual embedding model)
        embedding = await self._generate_embedding(content)
        
        # Create context metadata
        context_metadata = {
            "user_id": user_id,
            "content": content,
            "context_type": context_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {})
        }
        
        # Generate unique ID
        context_id = str(uuid.uuid4())
        
        # Store embedding
        success = await self.store_embedding(context_id, embedding, context_metadata)
        
        if success:
            return context_id
        else:
            raise Exception("Failed to store context")
    
    async def search_context(self, user_id: str, query: str, 
                           context_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for relevant context"""
        # Generate query embedding
        query_embedding = await self._generate_embedding(query)
        
        # Search for similar embeddings
        results = await self.search_similar(query_embedding, limit * 2)  # Get more to filter
        
        # Filter by user and context type
        filtered_results = []
        for result in results:
            metadata = result.get("metadata", {})
            
            if metadata.get("user_id") == user_id:
                if context_type is None or metadata.get("context_type") == context_type:
                    filtered_results.append(result)
                    
                    if len(filtered_results) >= limit:
                        break
        
        return filtered_results
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (placeholder implementation)"""
        # This is a placeholder - replace with actual embedding model
        # For example, using sentence-transformers, OpenAI embeddings, etc.
        
        try:
            # Try to use sentence-transformers if available
            from sentence_transformers import SentenceTransformer
            
            if not hasattr(self, "_embedding_model"):
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            embedding = self._embedding_model.encode(text)
            return embedding.tolist()
            
        except ImportError:
            # Fallback: simple hash-based embedding (for development only)
            import hashlib
            
            hash_obj = hashlib.sha256(text.encode())
            hex_dig = hash_obj.hexdigest()
            
            # Convert hex to list of floats (384 dimensions)
            embedding = []
            for i in range(0, min(len(hex_dig), 96), 2):  # 96 hex chars = 384 bits
                val = int(hex_dig[i:i+2], 16) / 255.0  # Normalize to 0-1
                embedding.extend([val] * 4)  # Expand to 384 dimensions
            
            # Pad to 384 dimensions if needed
            while len(embedding) < 384:
                embedding.append(0.0)
            
            return embedding[:384]
    
    async def delete_context(self, context_id: str) -> bool:
        """Delete context by ID"""
        if not self._connected:
            return False
        
        try:
            if self.provider == "chroma":
                self.collection.delete(ids=[context_id])
                return True
            elif self.provider == "pinecone":
                self.client.delete(ids=[context_id])
                return True
            else:
                # Fallback
                if context_id in self.client["vectors"]:
                    del self.client["vectors"][context_id]
                    del self.client["metadata"][context_id]
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete context: {e}")
            return False
    
    async def get_user_context_stats(self, user_id: str) -> Dict[str, Any]:
        """Get context statistics for user"""
        if not self._connected:
            return {}
        
        # This would need to be implemented per provider
        # For now, return basic stats
        return {
            "total_contexts": 0,  # Would count contexts for user
            "context_types": [],  # Would list context types
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    async def close(self):
        """Close vector database connection"""
        if self.client and self.provider != "fallback":
            # Close connection based on provider
            pass
        
        self._connected = False
        logger.info("Vector database connection closed")
