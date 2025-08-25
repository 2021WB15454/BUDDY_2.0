"""
Minimal Semantic Memory Engine (No Pinecone Dependencies)
For emergency deployment when vector databases aren't available
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MinimalSemanticMemoryEngine:
    """
    Fallback semantic memory engine that works without vector databases
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.initialized = True
        self.conversation_cache = {}
        
    async def initialize(self, conversation_db=None):
        """Initialize without vector databases"""
        logger.info("✅ Minimal Semantic Memory Engine initialized (no vector DB)")
        return True
        
    async def store_conversation_context(self, user_id: str, conversation_id: str, 
                                       messages: List[Dict], metadata: Dict = None):
        """Store conversation in memory cache"""
        key = f"{user_id}:{conversation_id}"
        self.conversation_cache[key] = {
            'messages': messages,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        return True
        
    async def retrieve_relevant_context(self, user_id: str, query: str, 
                                      conversation_id: str = None, limit: int = 5):
        """Retrieve recent conversations (basic keyword matching)"""
        results = []
        query_lower = query.lower()
        
        for key, data in self.conversation_cache.items():
            if user_id in key:
                # Simple keyword matching
                for msg in data['messages'][-10:]:  # Last 10 messages
                    if any(word in msg.get('content', '').lower() for word in query_lower.split()):
                        results.append({
                            'text': msg.get('content', ''),
                            'metadata': data['metadata'],
                            'score': 0.5  # Dummy score
                        })
                        
        return results[:limit]
        
    async def learn_user_preferences(self, user_id: str, interactions: List[Dict]):
        """Basic preference learning"""
        return {'learned': True, 'interactions_count': len(interactions)}

# Global instance
minimal_semantic_memory_engine = MinimalSemanticMemoryEngine()

async def get_semantic_memory_engine(config: Dict = None, 
                                   conversation_db = None):
    """Get the minimal semantic memory engine instance"""
    if config:
        minimal_semantic_memory_engine.config.update(config)
    
    return minimal_semantic_memory_engine
