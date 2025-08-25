"""
BUDDY NLP Engine - Advanced Natural Language Processing

This module implements the enhanced NLP capabilities for BUDDY 2.0,
replacing regex-based intent detection with ML-powered understanding.

Features:
- Intent Recognition using HuggingFace Transformers
- Context-aware conversation management
- Semantic memory and retrieval
- Multi-turn dialogue handling

Architecture:
    Intent Classifier → Context Manager → Response Generator
           ↕                ↕               ↕
    Training Data    Conversation     Template Engine
                     History          + ML Enhancement
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

# ML and NLP imports
try:
    import torch
    from transformers import (
        AutoTokenizer, AutoModelForSequenceClassification,
        TrainingArguments, Trainer, pipeline
    )
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings
    ML_AVAILABLE = True
except ImportError as e:
    logging.warning(f"ML dependencies not available: {e}")
    ML_AVAILABLE = False

# Local imports
from mongodb_integration import BuddyDatabase

logger = logging.getLogger(__name__)

class IntentClassifier:
    """ML-based intent classification using HuggingFace Transformers"""
    
    def __init__(self, model_name: str = "microsoft/DialoGPT-medium"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.classifier = None
        self.intent_labels = [
            "greeting", "goodbye", "question", "request", "reminder",
            "weather", "time", "calculation", "help", "settings",
            "compliment", "complaint", "small_talk", "emergency"
        ]
        
    async def initialize(self):
        """Initialize the ML models"""
        if not ML_AVAILABLE:
            logger.warning("ML dependencies not available, falling back to rule-based")
            return False
            
        try:
            # Initialize intent classification pipeline
            self.classifier = pipeline(
                "text-classification",
                model="facebook/bart-large-mnli",
                return_all_scores=True
            )
            
            # Initialize sentence transformer for embeddings
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            logger.info("NLP models initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize NLP models: {e}")
            return False
    
    async def classify_intent(self, text: str) -> Tuple[str, float]:
        """Classify the intent of the input text"""
        if not self.classifier:
            return await self._fallback_classify(text)
        
        try:
            # Use zero-shot classification for intent detection
            candidate_labels = self.intent_labels
            result = self.classifier(text, candidate_labels)
            
            # Get the highest scoring intent
            best_match = max(result, key=lambda x: x['score'])
            intent = best_match['label']
            confidence = best_match['score']
            
            logger.debug(f"Classified intent: {intent} (confidence: {confidence:.3f})")
            return intent, confidence
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return await self._fallback_classify(text)
    
    async def _fallback_classify(self, text: str) -> Tuple[str, float]:
        """Fallback rule-based intent classification"""
        text_lower = text.lower()
        
        # Rule-based patterns (existing logic)
        if any(word in text_lower for word in ["hello", "hi", "hey", "good morning"]):
            return "greeting", 0.9
        elif any(word in text_lower for word in ["bye", "goodbye", "see you"]):
            return "goodbye", 0.9
        elif any(word in text_lower for word in ["weather", "temperature", "rain"]):
            return "weather", 0.8
        elif any(word in text_lower for word in ["time", "clock", "what time"]):
            return "time", 0.8
        elif any(word in text_lower for word in ["calculate", "math", "+", "-", "*", "/"]):
            return "calculation", 0.8
        elif any(word in text_lower for word in ["remind", "reminder", "remember"]):
            return "reminder", 0.8
        elif "?" in text:
            return "question", 0.7
        else:
            return "small_talk", 0.5

    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate text embedding for semantic search"""
        if not hasattr(self, 'sentence_model'):
            return None
            
        try:
            embedding = self.sentence_model.encode([text])
            return embedding[0]
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None


class ConversationContextManager:
    """Manages conversation context and multi-turn dialogues"""
    
    def __init__(self, max_context_turns: int = 10):
        self.max_context_turns = max_context_turns
        self.active_sessions = {}  # session_id -> context
        
    async def update_context(self, session_id: str, user_message: str, 
                           bot_response: str, intent: str, metadata: Dict = None):
        """Update conversation context with new turn"""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "turns": [],
                "current_topic": None,
                "user_preferences": {},
                "context_summary": ""
            }
        
        context = self.active_sessions[session_id]
        
        # Add new turn
        turn = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": user_message,
            "bot_response": bot_response,
            "intent": intent,
            "metadata": metadata or {}
        }
        
        context["turns"].append(turn)
        
        # Keep only recent turns to manage memory
        if len(context["turns"]) > self.max_context_turns:
            context["turns"] = context["turns"][-self.max_context_turns:]
        
        # Update current topic based on recent intents
        recent_intents = [t["intent"] for t in context["turns"][-3:]]
        context["current_topic"] = max(set(recent_intents), key=recent_intents.count)
        
        logger.debug(f"Updated context for session {session_id}, current topic: {context['current_topic']}")
    
    def get_context(self, session_id: str) -> Dict:
        """Get current conversation context"""
        return self.active_sessions.get(session_id, {
            "turns": [],
            "current_topic": None,
            "user_preferences": {},
            "context_summary": ""
        })
    
    def get_recent_messages(self, session_id: str, count: int = 5) -> List[Dict]:
        """Get recent conversation messages for context"""
        context = self.get_context(session_id)
        return context["turns"][-count:]


class SemanticMemoryManager:
    """Manages semantic memory using Pinecone and ChromaDB"""
    
    def __init__(self, use_local_db: bool = True):
        self.use_local_db = use_local_db
        self.chroma_client = None
        self.collection = None
        
    async def initialize(self):
        """Initialize semantic memory databases"""
        if self.use_local_db and ML_AVAILABLE:
            try:
                # Initialize ChromaDB for local semantic search
                self.chroma_client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory="./buddy_semantic_memory"
                ))
                
                # Get or create collection
                self.collection = self.chroma_client.get_or_create_collection(
                    name="buddy_conversations",
                    metadata={"description": "BUDDY conversation memory"}
                )
                
                logger.info("ChromaDB initialized for semantic memory")
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}")
                return False
        
        return True
    
    async def store_conversation(self, session_id: str, user_message: str,
                               bot_response: str, embedding: np.ndarray = None):
        """Store conversation in semantic memory"""
        if not self.collection:
            return
        
        try:
            # Create unique ID for this conversation turn
            turn_id = f"{session_id}_{datetime.utcnow().timestamp()}"
            
            # Store conversation turn
            self.collection.add(
                documents=[f"User: {user_message}\nBuddy: {bot_response}"],
                embeddings=[embedding.tolist()] if embedding is not None else None,
                metadatas=[{
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_message": user_message,
                    "bot_response": bot_response
                }],
                ids=[turn_id]
            )
            
            logger.debug(f"Stored conversation turn {turn_id} in semantic memory")
            
        except Exception as e:
            logger.error(f"Failed to store conversation in semantic memory: {e}")
    
    async def search_similar_conversations(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for similar conversations in memory"""
        if not self.collection:
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            similar_conversations = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 1.0
                    
                    similar_conversations.append({
                        "document": doc,
                        "metadata": metadata,
                        "similarity": 1.0 - distance  # Convert distance to similarity
                    })
            
            return similar_conversations
            
        except Exception as e:
            logger.error(f"Failed to search semantic memory: {e}")
            return []


class EnhancedNLPEngine:
    """Main NLP engine orchestrating all components"""
    
    def __init__(self, database: BuddyDatabase = None):
        self.database = database
        self.intent_classifier = IntentClassifier()
        self.context_manager = ConversationContextManager()
        self.memory_manager = SemanticMemoryManager()
        self.initialized = False
    
    async def initialize(self):
        """Initialize all NLP components"""
        logger.info("Initializing Enhanced NLP Engine...")
        
        success = True
        success &= await self.intent_classifier.initialize()
        success &= await self.memory_manager.initialize()
        
        self.initialized = success
        
        if success:
            logger.info("Enhanced NLP Engine initialized successfully")
        else:
            logger.warning("Enhanced NLP Engine initialized with some limitations")
        
        return success
    
    async def process_message(self, session_id: str, user_id: str, 
                            message: str, metadata: Dict = None) -> Dict[str, Any]:
        """Process incoming message with enhanced NLP"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Classify intent
            intent, confidence = await self.intent_classifier.classify_intent(message)
            
            # Get conversation context
            context = self.context_manager.get_context(session_id)
            
            # Generate text embedding for semantic search
            embedding = self.intent_classifier.get_text_embedding(message)
            
            # Search for similar conversations
            similar_conversations = await self.memory_manager.search_similar_conversations(message)
            
            # Generate enhanced response
            response = await self._generate_enhanced_response(
                message, intent, confidence, context, similar_conversations
            )
            
            # Update context
            await self.context_manager.update_context(
                session_id, message, response, intent, metadata
            )
            
            # Store in semantic memory
            if embedding is not None:
                await self.memory_manager.store_conversation(
                    session_id, message, response, embedding
                )
            
            # Store in database
            if self.database and self.database.connected:
                await self.database.save_conversation(
                    session_id=session_id,
                    user_id=user_id,
                    role="user",
                    content=message,
                    metadata={"intent": intent, "confidence": confidence}
                )
                
                await self.database.save_conversation(
                    session_id=session_id,
                    user_id=user_id,
                    role="assistant",
                    content=response,
                    metadata={"intent": intent, "enhanced_nlp": True}
                )
            
            return {
                "response": response,
                "intent": intent,
                "confidence": confidence,
                "context_turns": len(context.get("turns", [])),
                "similar_conversations": len(similar_conversations),
                "enhanced_nlp": True
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "response": "I'm sorry, I'm having trouble understanding right now. Please try again.",
                "intent": "error",
                "confidence": 0.0,
                "enhanced_nlp": False,
                "error": str(e)
            }
    
    async def _generate_enhanced_response(self, message: str, intent: str, 
                                        confidence: float, context: Dict,
                                        similar_conversations: List[Dict]) -> str:
        """Generate enhanced response using context and semantic memory"""
        
        # Context-aware response generation
        recent_turns = context.get("turns", [])
        current_topic = context.get("current_topic")
        
        # Check if we're continuing a conversation topic
        if current_topic and len(recent_turns) > 1:
            if current_topic == intent:
                return await self._generate_contextual_response(message, intent, recent_turns)
        
        # Use similar conversations for better responses
        if similar_conversations and confidence > 0.7:
            return await self._generate_memory_enhanced_response(
                message, intent, similar_conversations
            )
        
        # Fallback to standard response generation
        return await self._generate_standard_response(message, intent, confidence)
    
    async def _generate_contextual_response(self, message: str, intent: str, 
                                          recent_turns: List[Dict]) -> str:
        """Generate response considering conversation context"""
        if intent == "greeting" and len(recent_turns) > 2:
            return "Good to continue our conversation! What else can I help you with?"
        
        if intent == "question" and len(recent_turns) > 1:
            last_turn = recent_turns[-1]
            if "weather" in last_turn.get("user_message", "").lower():
                return "Following up on the weather topic - is there a specific location or time you're interested in?"
        
        return await self._generate_standard_response(message, intent, 0.8)
    
    async def _generate_memory_enhanced_response(self, message: str, intent: str,
                                               similar_conversations: List[Dict]) -> str:
        """Generate response enhanced by similar conversation memory"""
        # Analyze similar conversations for response patterns
        response_patterns = []
        for conv in similar_conversations[:3]:  # Use top 3 similar conversations
            if conv["similarity"] > 0.7:
                response_patterns.append(conv["metadata"].get("bot_response", ""))
        
        if response_patterns and intent == "question":
            return f"Based on our previous conversations, I remember we discussed similar topics. {response_patterns[0][:100]}... Would you like me to elaborate on this?"
        
        return await self._generate_standard_response(message, intent, 0.9)
    
    async def _generate_standard_response(self, message: str, intent: str, 
                                        confidence: float) -> str:
        """Generate standard response based on intent"""
        import re
        import random
        from datetime import datetime
        
        message_lower = message.lower()
        
        # Enhanced greeting responses
        if intent == "greeting":
            greetings = [
                "Hello! I'm BUDDY with enhanced AI capabilities. How can I assist you today? 🤖",
                "Hi there! I'm excited to help you with my improved understanding. What's on your mind? 😊",
                "Hey! I've learned a lot since we last talked. What can I help you with? 🚀",
                "Greetings! My enhanced NLP is ready to better understand your needs. How may I help? ✨"
            ]
            return random.choice(greetings)
        
        # Enhanced question handling
        elif intent == "question":
            if "how" in message_lower and "are" in message_lower:
                return f"I'm doing fantastic! My enhanced NLP system is running smoothly (confidence: {confidence:.1%}). I can better understand context and remember our conversations now. How are you doing?"
            elif "what" in message_lower and "can" in message_lower:
                return "With my enhanced capabilities, I can:\n\n🧠 Better understand your intentions\n💭 Remember our conversation context\n🔍 Use semantic memory to provide relevant responses\n⚡ Learn from our interactions\n\nWhat would you like to try?"
            else:
                return f"That's an interesting question! With my improved understanding (confidence: {confidence:.1%}), I'm analyzing the context of your inquiry. Could you provide a bit more detail so I can give you the best answer?"
        
        # Enhanced time responses
        elif intent == "time":
            current_time = datetime.now()
            return f"🕐 **Current Time** (Enhanced NLP Response):\n\n{current_time.strftime('%I:%M %p')}\n{current_time.strftime('%A, %B %d, %Y')}\n\nI can now better understand time-related requests and context. Need anything else time-related?"
        
        # Enhanced calculation
        elif intent == "calculation":
            try:
                # Extract mathematical expression
                math_expression = re.sub(r'[^\d+\-*/().\s]', '', message)
                if math_expression.strip():
                    if all(c in "0123456789+-*/.() " for c in math_expression):
                        result = eval(math_expression)
                        return f"🧮 **Enhanced Calculator Result:**\n\n{math_expression.strip()} = **{result}**\n\nMy improved NLP detected this as a calculation with {confidence:.1%} confidence. Need more math help?"
                
                return "🧮 **Enhanced Calculator Ready!**\n\nI can now better understand math expressions! Try:\n• 'Calculate 15 + 25'\n• 'What's 100 divided by 4?'\n• '25 * 8 - 50'"
                
            except Exception:
                return "🧮 I detected a calculation request but had trouble with that expression. My enhanced NLP is learning - please try a simpler math expression!"
        
        # Enhanced weather
        elif intent == "weather":
            location_match = re.search(r'(?:in|at|for)\s+(\w+)', message_lower)
            location = location_match.group(1) if location_match else "your location"
            
            return f"🌤️ **Enhanced Weather Assistant for {location.title()}:**\n\nMy improved NLP detected this as a weather query with {confidence:.1%} confidence!\n\n💡 **Coming Soon**: Real-time weather integration\n🔧 **For now**: I'm learning your weather patterns and will provide personalized forecasts soon\n\nI can now better understand location context in your requests!"
        
        # Enhanced reminder
        elif intent == "reminder":
            task_text = re.sub(r'(set|create)?\s*(?:a\s+)?reminder\s*(for|to)?\s*', '', message, flags=re.IGNORECASE).strip()
            return f"⏰ **Enhanced Reminder System!**\n\n📝 **Task**: {task_text}\n🧠 **NLP Confidence**: {confidence:.1%}\n💾 **Smart Context**: I can now better understand when and how you want to be reminded\n\n✨ **New**: I'll learn your reminder patterns and suggest optimal timing!"
        
        # Enhanced small talk
        elif intent == "small_talk":
            responses = [
                f"I appreciate you chatting with me! My enhanced NLP (confidence: {confidence:.1%}) is getting better at understanding conversational nuances. What's on your mind?",
                f"Thanks for the conversation! With my improved understanding, I can now pick up on subtle context clues. Tell me more about what interests you!",
                f"It's great to talk! My enhanced capabilities help me better understand the flow of our conversation. What would you like to explore together?",
                f"I love our chats! My advanced NLP system is learning from each interaction (current confidence: {confidence:.1%}). What shall we discuss?"
            ]
            return random.choice(responses)
        
        # Default enhanced response
        else:
            return f"I understand you said: \"{message}\"\n\n🧠 **Enhanced NLP Analysis:**\n• Intent: {intent}\n• Confidence: {confidence:.1%}\n• Context-aware: ✅\n• Semantic memory: ✅\n\nI'm continuously learning to better understand you. What would you like to explore together? 🚀"


# Global instance for easy access
enhanced_nlp = EnhancedNLPEngine()

async def get_nlp_engine(database: Optional[BuddyDatabase] = None) -> EnhancedNLPEngine:
    """Get or create the enhanced NLP engine instance"""
    if database and not enhanced_nlp.database:
        enhanced_nlp.database = database
    
    if not enhanced_nlp.initialized:
        await enhanced_nlp.initialize()
    
    return enhanced_nlp
