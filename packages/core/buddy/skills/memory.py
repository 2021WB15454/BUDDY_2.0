"""
Memory Skill for BUDDY AI Assistant

This skill provides long-term memory capabilities using Pinecone vector database.
It allows BUDDY to remember and recall information from past conversations.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Try different import strategies
MEMORY_SKILL_AVAILABLE = False
BaseSkill = None
SkillResult = None
SkillSchema = None
PineconeClient = None

try:
    # First try relative imports (when run as part of package)
    from ..skills import BaseSkill, SkillResult, SkillSchema
    from ..database.pinecone_client import (
        PineconeClient, VectorDocument, SearchResult,
        create_memory_document, create_knowledge_document
    )
    MEMORY_SKILL_AVAILABLE = True
    logger.info("Memory skill imports loaded via relative imports")
except ImportError:
    try:
        # Try absolute imports (when run directly)
        from packages.core.buddy.skills import BaseSkill, SkillResult, SkillSchema
        from packages.core.buddy.database.pinecone_client import (
            PineconeClient, VectorDocument, SearchResult,
            create_memory_document, create_knowledge_document
        )
        MEMORY_SKILL_AVAILABLE = True
        logger.info("Memory skill imports loaded via absolute imports")
    except ImportError:
        try:
            # Try local imports (fallback)
            sys.path.insert(0, str(Path(__file__).parent))
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from skills import BaseSkill, SkillResult, SkillSchema
            from database.pinecone_client import (
                PineconeClient, VectorDocument, SearchResult,
                create_memory_document, create_knowledge_document
            )
            MEMORY_SKILL_AVAILABLE = True
            logger.info("Memory skill imports loaded via local imports")
        except ImportError as e:
            # Fallback - disable memory skill if dependencies not available
            logger.warning(f"Memory skill dependencies not available: {e}")
            BaseSkill = object  # Fallback base class
            SkillResult = dict
            SkillSchema = dict
            PineconeClient = None
            MEMORY_SKILL_AVAILABLE = False

class MemorySkill(BaseSkill):
    """
    Memory skill that provides long-term memory capabilities using Pinecone
    
    Capabilities:
    - Store conversation memories
    - Recall relevant past conversations
    - Store and retrieve knowledge
    - Semantic search across memories
    """
    
    def __init__(self, event_bus=None):
        if not MEMORY_SKILL_AVAILABLE:
            logger.error("Memory skill cannot be initialized - dependencies missing")
            return
            
        super().__init__(event_bus)
        self.pinecone_client: Optional[PineconeClient] = None
        self.enabled = False
    
    async def initialize(self) -> bool:
        """Initialize the memory skill with Pinecone"""
        try:
            # Set up schema first
            self.schema = SkillSchema(
                name="memory",
                version="1.0.0",
                description="Long-term memory and knowledge storage using vector database",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"text": {"type": "string"}}},
                category="memory",
                permissions=["memory_read", "memory_write"],
                requires_online=True,
                timeout_ms=10000
            )
            
            # Initialize Pinecone client
            self.pinecone_client = PineconeClient(
                index_name="buddy-memory",
                embedding_model="all-MiniLM-L6-v2"
            )
            
            await self.pinecone_client.initialize()
            self.enabled = True
            
            logger.info("✅ Memory skill initialized with Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize memory skill: {e}")
            logger.warning("Memory skill will be disabled")
            self.enabled = False
            return False
    
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        """
        Execute memory-related operations
        
        Handles queries like:
        - "Remember that I like coffee"
        - "What do you remember about me?"
        - "Do you remember when we talked about vacation?"
        - "Store this information: [knowledge]"
        """
        if not self.enabled or not self.pinecone_client:
            return SkillResult(
                success=False,
                error_result_metadata="Memory functionality is not available"
            )
        
        query = parameters.get("query", "")
        query_lower = query.lower().strip()
        
        try:
            # Store memory
            if any(phrase in query_lower for phrase in ["remember", "store", "save"]):
                return await self._store_memory(query, context)
            
            # Recall memories
            elif any(phrase in query_lower for phrase in ["recall", "remember", "what do you remember", "do you remember"]):
                return await self._recall_memories(query, context)
            
            # Search knowledge
            elif any(phrase in query_lower for phrase in ["search", "find", "look up"]):
                return await self._search_knowledge(query, context)
            
            # Default: search for relevant memories
            else:
                return await self._find_relevant_memories(query, context)
                
        except Exception as e:
            logger.error(f"Error in memory skill execution: {e}")
            return SkillResult(
                success=False,
                error_result_metadata="An error occurred while accessing memory"
            )
    
    async def _store_memory(self, query: str, context: Dict[str, Any]) -> SkillResult:
        """Store a memory or piece of information"""
        try:
            # Extract what to remember
            content_to_store = self._extract_memory_content(query)
            
            if not content_to_store:
                return SkillResult(
                    success=False,
                    error_result_metadata="I didn't understand what you want me to remember. Please be more specific."
                )
            
            # Create memory document
            user_id = context.get("user_id", "default")
            conversation_id = context.get("conversation_id", str(uuid.uuid4()))
            
            memory_doc = await create_memory_document(
                text=content_to_store,
                conversation_id=conversation_id,
                user_id=user_id,
                additional_metametadata={
                    "original_query": query,
                    "memory_type": "user_request"
                }
            )
            
            # Store in Pinecone
            success = await self.pinecone_client.store_document(memory_doc)
            
            if success:
                return SkillResult(
                    success=True,
                    result_metadata=f"I'll remember that: {content_to_store}",
                    metadata={
                        "stored_content": content_to_store,
                        "memory_id": memory_doc.id
                    }
                )
            else:
                return SkillResult(
                    success=False,
                    result_metadata="I had trouble storing that memory. Please try again.",
                    metadata={}
                )
                
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return SkillResult(
                success=False,
                result_metadata="An error occurred while storing the memory",
                metadata={"error": str(e)}
            )
    
    async def _recall_memories(self, query: str, context: Dict[str, Any]) -> SkillResult:
        """Recall relevant memories based on the query"""
        try:
            user_id = context.get("user_id", "default")
            
            # Search for relevant memories
            search_results = await self.pinecone_client.search(
                query=query,
                top_k=5,
                filter_dict={"user_id": user_id},
                min_score=0.7
            )
            
            if not search_results:
                return SkillResult(
                    success=True,
                    result_metadata="I don't have any specific memories related to that topic.",
                    metadata={"memories": []}
                )
            
            # Format memories for response
            memories = []
            for result in search_results:
                memory_info = {
                    "content": result.document.text,
                    "timestamp": result.document.timestamp.isoformat(),
                    "relevance_score": result.score,
                    "conversation_id": result.document.metadata.get("conversation_id"),
                    "type": result.document.metadata.get("memory_type", "unknown")
                }
                memories.append(memory_info)
            
            # Create response message
            memory_texts = [mem["content"] for mem in memories[:3]]
            response_message = "Here's what I remember:\n\n" + "\n".join([f"• {text}" for text in memory_texts])
            
            if len(memories) > 3:
                response_message += f"\n\n(I found {len(memories)} total related memories)"
            
            return SkillResult(
                success=True,
                result_metadata=response_message,
                metadata={"memories": memories}
            )
            
        except Exception as e:
            logger.error(f"Error recalling memories: {e}")
            return SkillResult(
                success=False,
                result_metadata="An error occurred while recalling memories",
                metadata={"error": str(e)}
            )
    
    async def _search_knowledge(self, query: str, context: Dict[str, Any]) -> SkillResult:
        """Search the knowledge base"""
        try:
            # Search for knowledge documents
            search_results = await self.pinecone_client.search(
                query=query,
                top_k=3,
                filter_dict={"type": "knowledge"},
                min_score=0.6
            )
            
            if not search_results:
                return SkillResult(
                    success=True,
                    result_metadata="I couldn't find any relevant information in my knowledge base.",
                    metadata={"results": []}
                )
            
            # Format results
            results = []
            for result in search_results:
                result_info = {
                    "title": result.document.metadata.get("title", "Untitled"),
                    "content": result.document.text,
                    "category": result.document.metadata.get("category", "general"),
                    "relevance_score": result.score
                }
                results.append(result_info)
            
            # Create response
            response_parts = []
            for result in results[:2]:  # Show top 2 results
                response_parts.append(f"**{result['title']}**\n{result['content']}")
            
            response_message = "Here's what I found:\n\n" + "\n\n".join(response_parts)
            
            return SkillResult(
                success=True,
                result_metadata=response_message,
                metadata={"results": results}
            )
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            return SkillResult(
                success=False,
                result_metadata="An error occurred while searching the knowledge base",
                metadata={"error": str(e)}
            )
    
    async def _find_relevant_memories(self, query: str, context: Dict[str, Any]) -> SkillResult:
        """Find memories relevant to the current query/context"""
        try:
            user_id = context.get("user_id", "default")
            
            # Search for relevant memories
            search_results = await self.pinecone_client.search(
                query=query,
                top_k=3,
                filter_dict={"user_id": user_id},
                min_score=0.6
            )
            
            if search_results:
                # Return the most relevant memory context
                top_result = search_results[0]
                
                return SkillResult(
                    success=True,
                    result_metadata="",  # This will be used as context for other skills
                    metadata={
                        "relevant_memory": top_result.document.text,
                        "memory_context": {
                            "conversation_id": top_result.document.metadata.get("conversation_id"),
                            "timestamp": top_result.document.timestamp.isoformat(),
                            "relevance_score": top_result.score
                        },
                        "all_results": [
                            {
                                "content": result.document.text,
                                "score": result.score,
                                "timestamp": result.document.timestamp.isoformat()
                            }
                            for result in search_results
                        ]
                    }
                )
            
            return SkillResult(
                success=True,
                result_metadata="",
                metadata={"relevant_memory": None}
            )
            
        except Exception as e:
            logger.error(f"Error finding relevant memories: {e}")
            return SkillResult(
                success=True,
                result_metadata="",
                metadata={"relevant_memory": None, "error": str(e)}
            )
    
    def _extract_memory_content(self, query: str) -> Optional[str]:
        """Extract the content to remember from the query"""
        query_lower = query.lower().strip()
        
        # Common patterns for memory requests
        patterns = [
            "remember that ",
            "remember: ",
            "store this: ",
            "save this: ",
            "don't forget that ",
            "keep in mind that ",
            "note that "
        ]
        
        for pattern in patterns:
            if pattern in query_lower:
                # Extract content after the pattern
                start_idx = query_lower.find(pattern) + len(pattern)
                content = query[start_idx:].strip()
                if content:
                    return content
        
        # If no pattern found, check if entire query is a memory request
        if any(word in query_lower for word in ["remember", "store", "save"]):
            # Remove command words and return the rest
            words = query.split()
            filtered_words = [word for word in words 
                            if word.lower() not in ["remember", "store", "save", "that", "this"]]
            if filtered_words:
                return " ".join(filtered_words)
        
        return None
    
    async def store_conversation_memory(self, 
                                      user_message: str,
                                      assistant_response: str,
                                      context: Dict[str, Any]) -> bool:
        """
        Store a conversation exchange as memory
        
        This method can be called by the conversation manager to automatically
        store important conversation exchanges.
        """
        if not self.enabled or not self.pinecone_client:
            return False
        
        try:
            user_id = context.get("user_id", "default")
            conversation_id = context.get("conversation_id", str(uuid.uuid4()))
            
            # Create memory content
            memory_content = f"User: {user_message}\nAssistant: {assistant_response}"
            
            # Create memory document
            memory_doc = await create_memory_document(
                text=memory_content,
                conversation_id=conversation_id,
                user_id=user_id,
                additional_metametadata={
                    "memory_type": "conversation_exchange",
                    "user_message": user_message,
                    "assistant_response": assistant_response
                }
            )
            
            # Store in Pinecone
            success = await self.pinecone_client.store_document(memory_doc)
            
            if success:
                logger.debug(f"Stored conversation memory for user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing conversation memory: {e}")
            return False
    
    async def add_knowledge(self, 
                           title: str,
                           content: str,
                           category: str = "general",
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add knowledge to the knowledge base
        
        Args:
            title: Title of the knowledge
            content: Knowledge content
            category: Category/topic
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.pinecone_client:
            return False
        
        try:
            # Create knowledge document
            knowledge_doc = await create_knowledge_document(
                text=content,
                title=title,
                category=category,
                additional_metametadata=metadata
            )
            
            # Store in Pinecone
            success = await self.pinecone_client.store_document(knowledge_doc)
            
            if success:
                logger.info(f"Added knowledge: {title}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding knowledge: {e}")
            return False
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memories"""
        if not self.enabled or not self.pinecone_client:
            return {"enabled": False}
        
        try:
            stats = await self.pinecone_client.get_index_stats()
            return {
                "enabled": True,
                "total_memories": stats.get("total_vector_count", 0),
                "index_fullness": stats.get("index_fullness", 0),
                "dimension": stats.get("dimension", 0)
            }
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"enabled": True, "error": str(e)}
    
    async def cleanup(self) -> None:
        """Cleanup the memory skill"""
        if self.pinecone_client:
            await self.pinecone_client.close()
        logger.info("Memory skill cleanup completed")

# Register the skill
def create_skill() -> MemorySkill:
    """Factory function to create the memory skill"""
    return MemorySkill()
