"""
Pinecone Vector Database Client for BUDDY AI Assistant

This module provides vector database capabilities using Pinecone for:
- Semantic search and retrieval
- Long-term memory storage
- Knowledge base management
- Conversation context embedding
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json

try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    Pinecone = None
    ServerlessSpec = None

from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class VectorDocument:
    """Represents a document stored in the vector database"""
    id: str
    text: str
    metadata: Dict[str, Any]
    timestamp: datetime
    source: str = "buddy"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorDocument':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

@dataclass
class SearchResult:
    """Represents a search result from the vector database"""
    document: VectorDocument
    score: float
    
class PineconeClient:
    """
    Pinecone vector database client for BUDDY AI Assistant
    
    Provides semantic search, memory storage, and knowledge retrieval
    capabilities using Pinecone vector database.
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 index_name: str = "buddy-memory",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 cloud: str = "aws",
                 region: str = "us-east-1"):
        """
        Initialize Pinecone client
        
        Args:
            api_key: Pinecone API key (defaults to PINECONE_API_KEY env var)
            index_name: Name of the Pinecone index
            embedding_model: Sentence transformer model for embeddings
            cloud: Cloud provider for Pinecone (aws, gcp, azure)
            region: Region for the index
        """
        if not PINECONE_AVAILABLE:
            raise ImportError("Pinecone not available. Install with: pip install pinecone-client")
        
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            raise ValueError("Pinecone API key required. Set PINECONE_API_KEY environment variable or pass api_key")
        
        self.index_name = index_name
        self.cloud = cloud
        self.region = region
        self.embedding_model_name = embedding_model
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.api_key)
        self.index = None
        self.embedding_model = None
        self.dimension = None
        
        logger.info(f"Pinecone client initialized for index: {self.index_name}")
    
    async def initialize(self) -> None:
        """Initialize the Pinecone index and embedding model"""
        try:
            # Load embedding model
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            self.dimension = self.embedding_model.get_sentence_embedding_dimension()
            
            # Create index if it doesn't exist
            await self._ensure_index_exists()
            
            # Get index reference
            self.index = self.pc.Index(self.index_name)
            
            logger.info("✅ Pinecone client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {e}")
            raise
    
    async def _ensure_index_exists(self) -> None:
        """Ensure the Pinecone index exists, create if necessary"""
        try:
            if not self.pc.has_index(self.index_name):
                logger.info(f"Creating Pinecone index: {self.index_name}")
                
                # Create serverless index
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=self.cloud,
                        region=self.region
                    )
                )
                
                # Wait for index to be ready
                await asyncio.sleep(2)
                logger.info(f"✅ Created Pinecone index: {self.index_name}")
            else:
                logger.info(f"Using existing Pinecone index: {self.index_name}")
                
        except Exception as e:
            logger.error(f"Failed to ensure index exists: {e}")
            raise
    
    def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        if not self.embedding_model:
            raise RuntimeError("Embedding model not initialized")
        
        embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)
        return embeddings
    
    async def store_document(self, document: VectorDocument) -> bool:
        """
        Store a document in the vector database
        
        Args:
            document: Document to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.index:
                raise RuntimeError("Pinecone index not initialized")
            
            # Generate embedding
            embedding = self._generate_embeddings([document.text])[0]
            
            # Prepare metadata
            metadata = {
                "text": document.text,
                "source": document.source,
                "timestamp": document.timestamp.isoformat(),
                **document.metadata
            }
            
            # Store in Pinecone
            self.index.upsert(
                vectors=[(document.id, embedding.tolist(), metadata)]
            )
            
            logger.debug(f"Stored document: {document.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store document {document.id}: {e}")
            return False
    
    async def store_documents(self, documents: List[VectorDocument]) -> int:
        """
        Store multiple documents in batch
        
        Args:
            documents: List of documents to store
            
        Returns:
            Number of successfully stored documents
        """
        try:
            if not self.index:
                raise RuntimeError("Pinecone index not initialized")
            
            # Generate embeddings for all texts
            texts = [doc.text for doc in documents]
            embeddings = self._generate_embeddings(texts)
            
            # Prepare vectors for batch upsert
            vectors = []
            for doc, embedding in zip(documents, embeddings):
                metadata = {
                    "text": doc.text,
                    "source": doc.source,
                    "timestamp": doc.timestamp.isoformat(),
                    **doc.metadata
                }
                vectors.append((doc.id, embedding.tolist(), metadata))
            
            # Batch upsert
            self.index.upsert(vectors=vectors)
            
            logger.info(f"Stored {len(documents)} documents in batch")
            return len(documents)
            
        except Exception as e:
            logger.error(f"Failed to store documents in batch: {e}")
            return 0
    
    async def search(self, 
                    query: str, 
                    top_k: int = 5,
                    filter_dict: Optional[Dict[str, Any]] = None,
                    min_score: float = 0.0) -> List[SearchResult]:
        """
        Search for similar documents
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filter_dict: Metadata filters
            min_score: Minimum similarity score
            
        Returns:
            List of search results
        """
        try:
            if not self.index:
                raise RuntimeError("Pinecone index not initialized")
            
            # Generate query embedding
            query_embedding = self._generate_embeddings([query])[0]
            
            # Search in Pinecone
            search_response = self.index.query(
                vector=query_embedding.tolist(),
                top_k=top_k,
                filter=filter_dict,
                include_metadata=True
            )
            
            # Convert to SearchResult objects
            results = []
            for match in search_response.matches:
                if match.score >= min_score:
                    metadata = match.metadata
                    document = VectorDocument(
                        id=match.id,
                        text=metadata.get("text", ""),
                        metadata={k: v for k, v in metadata.items() 
                                if k not in ["text", "source", "timestamp"]},
                        timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.now().isoformat())),
                        source=metadata.get("source", "unknown")
                    )
                    results.append(SearchResult(document=document, score=match.score))
            
            logger.debug(f"Found {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            return []
    
    async def get_document(self, document_id: str) -> Optional[VectorDocument]:
        """
        Retrieve a specific document by ID
        
        Args:
            document_id: Document ID to retrieve
            
        Returns:
            Document if found, None otherwise
        """
        try:
            if not self.index:
                raise RuntimeError("Pinecone index not initialized")
            
            response = self.index.fetch(ids=[document_id])
            
            if document_id in response.vectors:
                vector_data = response.vectors[document_id]
                metadata = vector_data.metadata
                
                document = VectorDocument(
                    id=document_id,
                    text=metadata.get("text", ""),
                    metadata={k: v for k, v in metadata.items() 
                            if k not in ["text", "source", "timestamp"]},
                    timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.now().isoformat())),
                    source=metadata.get("source", "unknown")
                )
                return document
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector database
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.index:
                raise RuntimeError("Pinecone index not initialized")
            
            self.index.delete(ids=[document_id])
            logger.debug(f"Deleted document: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    async def delete_documents(self, 
                              filter_dict: Optional[Dict[str, Any]] = None,
                              delete_all: bool = False) -> bool:
        """
        Delete multiple documents
        
        Args:
            filter_dict: Metadata filter for documents to delete
            delete_all: If True, delete all documents (use with caution)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.index:
                raise RuntimeError("Pinecone index not initialized")
            
            if delete_all:
                self.index.delete(delete_all=True)
                logger.warning("Deleted all documents from index")
            elif filter_dict:
                self.index.delete(filter=filter_dict)
                logger.info(f"Deleted documents matching filter: {filter_dict}")
            else:
                logger.warning("No deletion criteria specified")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Pinecone index
        
        Returns:
            Dictionary with index statistics
        """
        try:
            if not self.index:
                raise RuntimeError("Pinecone index not initialized")
            
            stats = self.index.describe_index_stats()
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": dict(stats.namespaces) if stats.namespaces else {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}
    
    async def close(self) -> None:
        """Close the Pinecone client connection"""
        try:
            # Pinecone client doesn't require explicit closing
            logger.info("Pinecone client connection closed")
        except Exception as e:
            logger.error(f"Error closing Pinecone client: {e}")

# Utility functions for BUDDY integration

async def create_memory_document(text: str, 
                                conversation_id: str,
                                user_id: str = "default",
                                additional_metadata: Optional[Dict[str, Any]] = None) -> VectorDocument:
    """
    Create a memory document for conversation storage
    
    Args:
        text: Text content to store
        conversation_id: ID of the conversation
        user_id: User ID
        additional_metadata: Additional metadata to store
        
    Returns:
        VectorDocument ready for storage
    """
    import uuid
    
    metadata = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "type": "conversation",
        **(additional_metadata or {})
    }
    
    return VectorDocument(
        id=str(uuid.uuid4()),
        text=text,
        metadata=metadata,
        timestamp=datetime.now(),
        source="buddy_conversation"
    )

async def create_knowledge_document(text: str,
                                   title: str,
                                   category: str = "general",
                                   additional_metadata: Optional[Dict[str, Any]] = None) -> VectorDocument:
    """
    Create a knowledge document for knowledge base storage
    
    Args:
        text: Knowledge content
        title: Title of the knowledge
        category: Category/topic
        additional_metadata: Additional metadata
        
    Returns:
        VectorDocument ready for storage
    """
    import uuid
    
    metadata = {
        "title": title,
        "category": category,
        "type": "knowledge",
        **(additional_metadata or {})
    }
    
    return VectorDocument(
        id=str(uuid.uuid4()),
        text=text,
        metadata=metadata,
        timestamp=datetime.now(),
        source="buddy_knowledge"
    )
