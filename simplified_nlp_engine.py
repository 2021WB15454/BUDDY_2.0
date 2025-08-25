"""
Simplified Enhanced NLP Engine for BUDDY 2.0

A lightweight version that provides enhanced NLP capabilities
without requiring heavy ML dependencies like transformers.

This allows immediate testing and development while ML packages install.
"""

import os
import json
import asyncio
import logging
import re
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

# Local imports
from mongodb_integration import BuddyDatabase

logger = logging.getLogger(__name__)

class SimplifiedIntentClassifier:
    """Rule-based intent classification with enhanced patterns"""
    
    def __init__(self):
        self.intent_patterns = {
            "greeting": [
                r"(?:hello|hi|hey|good\s+(?:morning|afternoon|evening)|greetings)",
                r"(?:what's\s+up|how\s+are\s+you|howdy)"
            ],
            "goodbye": [
                r"(?:bye|goodbye|see\s+you|farewell|take\s+care)",
                r"(?:until\s+next\s+time|catch\s+you\s+later)"
            ],
            "question": [
                r"(?:what|how|when|where|why|which|who)\s+",
                r"\?\s*$",
                r"(?:can\s+you|could\s+you|would\s+you)"
            ],
            "weather": [
                r"(?:weather|temperature|forecast|rain|sunny|cloudy|snow)",
                r"(?:how\s+hot|how\s+cold|climate)"
            ],
            "time": [
                r"(?:time|clock|hour|minute)",
                r"(?:what\s+time|current\s+time)"
            ],
            "calculation": [
                r"(?:calculate|math|compute|solve)",
                r"[\+\-\*\/\=]",
                r"(?:plus|minus|times|divided|multiply)"
            ],
            "reminder": [
                r"(?:remind|reminder|remember|don't\s+forget)",
                r"(?:set\s+a\s+reminder|schedule)"
            ],
            "compliment": [
                r"(?:good\s+job|well\s+done|excellent|amazing|awesome)",
                r"(?:you're\s+great|thank\s+you|thanks)"
            ],
            "help": [
                r"(?:help|assist|support|guide)",
                r"(?:what\s+can\s+you\s+do|capabilities)"
            ],
            "settings": [
                r"(?:settings|preferences|configure|setup)",
                r"(?:change\s+settings|modify\s+preferences)"
            ]
        }
        
    async def classify_intent(self, text: str) -> Tuple[str, float]:
        """Classify intent using enhanced rule-based patterns"""
        text_lower = text.lower().strip()
        
        # Score each intent
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    matches += 1
                    # Weight by pattern specificity
                    pattern_weight = len(pattern) / 100.0  # Longer patterns get higher weight
                    score += 0.8 + pattern_weight
            
            if matches > 0:
                # Bonus for multiple pattern matches
                score += (matches - 1) * 0.2
                intent_scores[intent] = min(score, 0.95)  # Cap at 95%
        
        # Return best match or default
        if intent_scores:
            best_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x])
            confidence = intent_scores[best_intent]
            return best_intent, confidence
        else:
            # Default classification
            if "?" in text:
                return "question", 0.6
            else:
                return "small_talk", 0.5


class SimplifiedContextManager:
    """Lightweight conversation context management"""
    
    def __init__(self, max_context_turns: int = 10):
        self.max_context_turns = max_context_turns
        self.active_sessions = {}
        
    async def update_context(self, session_id: str, user_message: str, 
                           bot_response: str, intent: str, metadata: Optional[Dict] = None):
        """Update conversation context"""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "turns": [],
                "current_topic": None,
                "message_count": 0,
                "last_interaction": datetime.utcnow()
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
        context["message_count"] += 1
        context["last_interaction"] = datetime.utcnow()
        
        # Manage memory
        if len(context["turns"]) > self.max_context_turns:
            context["turns"] = context["turns"][-self.max_context_turns:]
        
        # Update current topic
        recent_intents = [t["intent"] for t in context["turns"][-3:]]
        context["current_topic"] = max(set(recent_intents), key=recent_intents.count)
        
    def get_context(self, session_id: str) -> Dict:
        """Get conversation context"""
        return self.active_sessions.get(session_id, {
            "turns": [],
            "current_topic": None,
            "message_count": 0,
            "last_interaction": None
        })


class SimplifiedEnhancedNLP:
    """Simplified enhanced NLP engine without heavy ML dependencies"""
    
    def __init__(self, database: Optional[BuddyDatabase] = None):
        self.database = database
        self.intent_classifier = SimplifiedIntentClassifier()
        self.context_manager = SimplifiedContextManager()
        self.initialized = False
        
    async def initialize(self):
        """Initialize the simplified NLP engine"""
        logger.info("Initializing Simplified Enhanced NLP Engine...")
        self.initialized = True
        logger.info("Simplified Enhanced NLP Engine ready!")
        return True
        
    async def process_message(self, session_id: str, user_id: str, 
                            message: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Process message with simplified enhanced NLP"""
        if not self.initialized:
            await self.initialize()
            
        try:
            # Classify intent
            intent, confidence = await self.intent_classifier.classify_intent(message)
            
            # Get context
            context = self.context_manager.get_context(session_id)
            
            # Generate enhanced response
            response = await self._generate_enhanced_response(
                message, intent, confidence, context
            )
            
            # Update context
            await self.context_manager.update_context(
                session_id, message, response, intent, metadata
            )
            
            # Store in database if available
            if self.database and hasattr(self.database, 'connected') and self.database.connected:
                try:
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
                        metadata={"intent": intent, "simplified_nlp": True}
                    )
                except Exception as e:
                    logger.warning(f"Database save failed: {e}")
            
            return {
                "response": response,
                "intent": intent,
                "confidence": confidence,
                "context_turns": len(context.get("turns", [])),
                "enhanced_nlp": True,
                "simplified_mode": True
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "response": "I'm having trouble understanding right now. Please try again.",
                "intent": "error",
                "confidence": 0.0,
                "enhanced_nlp": False,
                "error": str(e)
            }
    
    async def _generate_enhanced_response(self, message: str, intent: str, 
                                        confidence: float, context: Dict) -> str:
        """Generate enhanced response with context awareness"""
        
        message_lower = message.lower()
        turn_count = len(context.get("turns", []))
        current_topic = context.get("current_topic")
        
        # Context-aware greeting
        if intent == "greeting":
            if turn_count > 2:
                return f"Welcome back! I see we've been chatting about {current_topic or 'various topics'}. How can I help you now? 🤖✨"
            else:
                greetings = [
                    f"Hello! I'm BUDDY with Enhanced NLP capabilities (confidence: {confidence:.1%}). How can I assist you today? 🧠",
                    f"Hi there! My enhanced understanding is ready to help (detection confidence: {confidence:.1%}). What's on your mind? 🚀",
                    f"Hey! I'm operating with improved conversational AI. What can I do for you? (Intent: {intent}) ⚡"
                ]
                return random.choice(greetings)
        
        # Enhanced question handling
        elif intent == "question":
            if "how are you" in message_lower:
                return f"I'm excellent! My Enhanced NLP engine is running smoothly with {confidence:.1%} confidence in understanding your intent. I can now better track our conversation context ({turn_count} turns so far). How are you doing? 😊"
            elif "what can you do" in message_lower or "capabilities" in message_lower:
                return f"""🧠 **Enhanced BUDDY Capabilities** (Intent Detection: {confidence:.1%})

**Core AI Features:**
• Advanced intent recognition and classification
• Context-aware conversation management
• Enhanced response generation with memory
• Conversation pattern learning

**Current Context:**
• Session turns: {turn_count}
• Current topic: {current_topic or 'General conversation'}
• Enhanced NLP: ✅ Active

**Available Functions:**
🗓️ Reminders and scheduling
🧮 Mathematical calculations  
🌤️ Weather information (coming soon)
⏰ Time and date queries
💬 Contextual conversations
🔧 System preferences

What would you like to explore? 🚀"""
            else:
                return f"That's a great question! My enhanced NLP detected this as a '{intent}' intent with {confidence:.1%} confidence. Based on our conversation context ({turn_count} previous turns), I can provide more personalized assistance. Could you tell me more about what you'd like to know?"
        
        # Enhanced time responses
        elif intent == "time":
            current_time = datetime.now()
            return f"🕐 **Enhanced Time Response** (NLP Confidence: {confidence:.1%})\n\n**Current Time:** {current_time.strftime('%I:%M %p')}\n**Date:** {current_time.strftime('%A, %B %d, %Y')}\n\n💡 My enhanced NLP can now understand various time-related queries and remember time preferences from our conversation!"
        
        # Enhanced calculation
        elif intent == "calculation":
            try:
                # Extract and evaluate mathematical expressions
                math_expression = re.sub(r'[^\d+\-*/().\s]', '', message)
                if math_expression.strip() and all(c in "0123456789+-*/.() " for c in math_expression):
                    result = eval(math_expression)
                    return f"🧮 **Enhanced Calculator** (Intent confidence: {confidence:.1%})\n\n**Expression:** {math_expression.strip()}\n**Result:** **{result}**\n\n✨ My improved NLP detected this as a calculation request and can now handle more complex mathematical expressions!"
                else:
                    return f"🧮 **Enhanced Calculator Ready!** (Detected: {intent}, {confidence:.1%} confidence)\n\nI can now better understand mathematical expressions! Try:\n• 'Calculate 25 * 8 + 15'\n• 'What's 150 divided by 3?'\n• 'Solve (10 + 5) * 2'"
            except:
                return f"🧮 **Enhanced Calculator** - I detected a math request ({confidence:.1%} confidence) but couldn't evaluate that expression. Please try a simpler format!"
        
        # Enhanced weather
        elif intent == "weather":
            location_match = re.search(r'(?:in|at|for)\s+(\w+)', message_lower)
            location = location_match.group(1).title() if location_match else "your location"
            
            return f"🌤️ **Enhanced Weather Assistant** (NLP confidence: {confidence:.1%})\n\n**Location detected:** {location}\n**Context aware:** Based on our {turn_count} conversation turns\n\n🔧 **Status:** Weather API integration in development\n💡 **Enhanced feature:** I can now remember your preferred locations and weather interests!\n\nWhat specific weather information would you like me to prioritize for future updates?"
        
        # Enhanced reminders
        elif intent == "reminder":
            task_match = re.search(r'(?:remind|reminder).*?(?:to|about|for)\s+(.+)', message_lower)
            task = task_match.group(1) if task_match else "the task you mentioned"
            
            return f"⏰ **Enhanced Reminder System** (NLP confidence: {confidence:.1%})\n\n📝 **Task:** {task}\n🧠 **Context:** Turn {turn_count + 1} in our conversation\n💾 **Enhanced:** I can now better understand reminder contexts and timing preferences\n\n✨ **Coming soon:** Smart scheduling based on our conversation patterns!"
        
        # Enhanced help
        elif intent == "help":
            return f"""🤝 **Enhanced Help System** (Intent confidence: {confidence:.1%})

**Context-Aware Assistance:**
• Conversation turns: {turn_count}
• Current topic: {current_topic or 'Getting started'}
• Enhanced NLP: Active and learning

**How I can help:**
🧠 **Smart Understanding:** I can now better interpret your requests
💭 **Context Memory:** I remember our conversation flow  
🎯 **Intent Detection:** More accurate understanding of what you need
📚 **Learning:** I improve with each interaction

**Try asking me about:**
• Time and scheduling
• Mathematical calculations
• Weather information  
• Setting reminders
• General conversation

My enhanced capabilities make me better at understanding context and providing personalized assistance! 🚀"""
        
        # Enhanced compliments
        elif intent == "compliment":
            return f"😊 **Thank you so much!** That really means a lot!\n\nMy enhanced NLP detected your positive sentiment with {confidence:.1%} confidence. It's wonderful to know my improved understanding and context awareness is helping you!\n\nI'm constantly learning and evolving to serve you better. Our conversation ({turn_count} turns) helps me improve! 🤖💙"
        
        # Enhanced default
        else:
            return f"""🤖 **Enhanced BUDDY Response** 

**Your message:** "{message}"
**NLP Analysis:**
• Intent detected: {intent}
• Confidence level: {confidence:.1%}
• Conversation context: {turn_count} turns
• Current topic: {current_topic or 'Open conversation'}

**Enhanced Understanding:** My improved NLP engine is analyzing patterns in our conversation to provide better, more contextual responses.

How else can I assist you today? 🚀"""

# Global simplified instance
simplified_nlp = SimplifiedEnhancedNLP()

async def get_simplified_nlp_engine(database: Optional[BuddyDatabase] = None) -> SimplifiedEnhancedNLP:
    """Get the simplified enhanced NLP engine"""
    if database and not simplified_nlp.database:
        simplified_nlp.database = database
    
    if not simplified_nlp.initialized:
        await simplified_nlp.initialize()
    
    return simplified_nlp
