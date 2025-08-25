"""
BUDDY Conversation Flow Manager

Implements advanced conversation flow management for maintaining natural dialogue
continuity across devices, topics, and context switches.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

# Import flow persistence manager (would normally be separate)
try:
    from .flow_persistence import FlowPersistenceManager
except ImportError:
    FlowPersistenceManager = None


class ConversationState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    WAITING_FOR_INPUT = "waiting_for_input"
    PROCESSING = "processing"
    COMPLETED = "completed"
    TRANSFERRED = "transferred"


@dataclass
class ConversationContext:
    user_id: str
    session_id: str
    current_topic: Optional[str] = None
    conversation_history: List[Dict] = field(default_factory=list)
    user_intent: Optional[str] = None
    entity_memory: Dict[str, Any] = field(default_factory=dict)
    emotional_state: Optional[str] = None
    device_context: Dict[str, Any] = field(default_factory=dict)
    last_interaction: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    conversation_depth: int = 0
    unresolved_questions: List[str] = field(default_factory=list)
    pending_actions: List[Dict] = field(default_factory=list)
    conversation_state: ConversationState = ConversationState.ACTIVE


class ConversationFlowManager:
    """Main conversation flow management system"""
    
    def __init__(self, skill_registry=None, event_bus=None):
        self.skill_registry = skill_registry
        self.event_bus = event_bus
        self.active_conversations = {}
        self.flow_strategies = {}
        self.memory_engine = ConversationMemoryEngine()
        
        # Initialize flow persistence manager if available
        if FlowPersistenceManager:
            self.persistence_manager = FlowPersistenceManager()
        else:
            self.persistence_manager = None
        
    async def manage_conversation_flow(self, message: Dict, device_context: Dict = None) -> Dict:
        """Main flow management method"""
        session_id = message.get('session_id', str(uuid.uuid4()))
        user_id = message.get('user_id', 'default')
        device_context = device_context or {}
        
        # Get or create conversation context
        context = await self.get_conversation_context(session_id, user_id)
        
        # Update context with new message and device info
        context = await self.update_context(context, message, device_context)
        
        # Analyze conversation flow needs
        flow_decision = await self.analyze_flow_requirements(context, message)
        
        # Generate contextually aware response
        response = await self.generate_contextual_response(context, message, flow_decision)
        
        # Update conversation state
        await self.update_conversation_state(context, response)
        
        return response
    
    async def get_conversation_context(self, session_id: str, user_id: str) -> ConversationContext:
        """Retrieve or create conversation context"""
        context_key = f"{user_id}:{session_id}"
        
        if context_key in self.active_conversations:
            return self.active_conversations[context_key]
        
        # Create new conversation context
        context = ConversationContext(
            user_id=user_id,
            session_id=session_id,
            current_topic=None,
            conversation_history=[],
            user_intent=None,
            entity_memory={},
            emotional_state=None,
            device_context={},
            last_interaction=datetime.now(timezone.utc),
            conversation_depth=0,
            unresolved_questions=[],
            pending_actions=[]
        )
        
        self.active_conversations[context_key] = context
        return context
    
    async def update_context(self, context: ConversationContext, message: Dict, device_context: Dict) -> ConversationContext:
        """Update conversation context with new information"""
        current_text = message.get('text', message.get('content', ''))
        
        # Add message to history
        context.conversation_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'user',
            'content': current_text,
            'device': device_context.get('device_type', 'unknown')
        })
        
        # Update device context
        context.device_context.update(device_context)
        
        # Update last interaction
        context.last_interaction = datetime.now(timezone.utc)
        
        # Increment conversation depth
        context.conversation_depth += 1
        
        # Detect topic from current message
        if await self.is_new_topic(current_text, context.current_topic):
            context.current_topic = await self.extract_topic(current_text)
        
        return context
    
    async def analyze_flow_requirements(self, context: ConversationContext, message: Dict) -> Dict:
        """Analyze what flow management is needed"""
        current_text = message.get('text', message.get('content', ''))
        
        flow_analysis = {
            'topic_shift': await self.detect_topic_shift(context, current_text),
            'intent_change': await self.detect_intent_change(context, current_text),
            'clarification_needed': await self.needs_clarification(context, current_text),
            'context_restoration': await self.should_restore_context(context, current_text),
            'conversation_continuation': await self.is_conversation_continuation(context, current_text),
            'memory_recall': await self.should_recall_memory(context, current_text),
            'emotional_support': await self.needs_emotional_support(current_text),
            'follow_up_required': await self.requires_follow_up(context, current_text)
        }
        
        return flow_analysis
    
    async def generate_contextual_response(self, context: ConversationContext, 
                                         message: Dict, flow_decision: Dict) -> Dict:
        """Generate response based on conversation flow analysis"""
        current_text = message.get('text', message.get('content', ''))
        
        # Prepare context for response generation
        response_context = {
            'conversation_history': context.conversation_history[-5:],  # Last 5 messages
            'current_topic': context.current_topic,
            'user_intent': context.user_intent,
            'entity_memory': context.entity_memory,
            'emotional_state': context.emotional_state,
            'unresolved_questions': context.unresolved_questions,
            'device_context': context.device_context,
            'flow_decisions': flow_decision
        }
        
        # Handle different flow scenarios
        if flow_decision['emotional_support']:
            response = await self.handle_emotional_support(context, current_text, response_context)
        elif flow_decision['topic_shift']:
            response = await self.handle_topic_shift(context, current_text, response_context)
        elif flow_decision['clarification_needed']:
            response = await self.handle_clarification_request(context, current_text, response_context)
        elif flow_decision['context_restoration']:
            response = await self.handle_context_restoration(context, current_text, response_context)
        elif flow_decision['conversation_continuation']:
            response = await self.handle_conversation_continuation(context, current_text, response_context)
        else:
            response = await self.handle_normal_flow(context, current_text, response_context)
        
        # Add flow management metadata
        response['flow_metadata'] = {
            'conversation_state': context.conversation_state.value,
            'topic': context.current_topic,
            'depth': context.conversation_depth,
            'requires_followup': len(context.unresolved_questions) > 0,
            'pending_actions': len(context.pending_actions) > 0
        }
        
        return response
    
    async def handle_emotional_support(self, context: ConversationContext, text: str, response_context: Dict) -> Dict:
        """Handle emotional support scenarios"""
        # Use emotional intelligence skill if available
        if self.skill_registry:
            emotional_skill = self.skill_registry.get_skill("emotional_intelligence")
            if emotional_skill:
                result = await emotional_skill.execute({"text": text}, response_context)
                if result.success:
                    context.emotional_state = result.data.get('detected_emotions', [])
                    return {
                        'success': True,
                        'response': result.data.get('emotional_response', ''),
                        'intent': 'emotional_support',
                        'suggestions': result.data.get('suggestions', [])
                    }
        
        # Fallback emotional response
        return {
            'success': True,
            'response': "I understand you might be going through something. I'm here to listen and support you. How can I help?",
            'intent': 'emotional_support'
        }
    
    async def handle_conversation_continuation(self, context: ConversationContext, text: str, response_context: Dict) -> Dict:
        """Handle conversation continuation with context awareness"""
        # Check if this continues a previous topic
        if context.current_topic and len(context.conversation_history) > 1:
            # Build on previous conversation
            previous_context = f"We were discussing {context.current_topic}. "
            
            # Route to appropriate skill based on topic
            skill_name = await self.determine_skill_for_topic(context.current_topic, text)
            
            if self.skill_registry and skill_name:
                skill = self.skill_registry.get_skill(skill_name)
                if skill:
                    # Add conversation context to parameters
                    parameters = {"text": text, "topic": context.current_topic, "context": previous_context}
                    result = await skill.execute(parameters, response_context)
                    
                    if result.success:
                        response = result.data.get('text') or result.data.get('response', '')
                        return {
                            'success': True,
                            'response': response,
                            'intent': skill_name,
                            'context_aware': True
                        }
        
        # Fallback to normal processing
        return await self.handle_normal_flow(context, text, response_context)
    
    async def handle_normal_flow(self, context: ConversationContext, text: str, response_context: Dict) -> Dict:
        """Handle normal conversation flow"""
        # Use NLU skill for intent detection
        if self.skill_registry:
            nlu_skill = self.skill_registry.get_skill("nlu")
            if nlu_skill:
                nlu_result = await nlu_skill.execute({"text": text}, response_context)
                if nlu_result.success:
                    intent = nlu_result.data.get('intent', 'unknown')
                    
                    # Route to appropriate skill
                    skill_name = await self.map_intent_to_skill(intent)
                    skill = self.skill_registry.get_skill(skill_name)
                    
                    if skill:
                        # Execute skill with context
                        entities = nlu_result.data.get('entities', {})
                        parameters = {"text": text, **entities}
                        
                        result = await skill.execute(parameters, response_context)
                        if result.success:
                            context.user_intent = intent
                            response_text = result.data.get('text') or result.data.get('response') or result.data.get('advice', str(result.data))
                            
                            return {
                                'success': True,
                                'response': response_text,
                                'intent': intent,
                                'entities': entities,
                                'skill_used': skill_name
                            }
        
        # Ultimate fallback
        return {
            'success': True,
            'response': "I understand you're asking about something. While I'm continuously learning, I can help with weather, calculations, tasks, health advice, and general conversation. What would you like to explore?",
            'intent': 'fallback'
        }
    
    async def update_conversation_state(self, context: ConversationContext, response: Dict) -> None:
        """Update conversation state after response"""
        # Add response to history
        context.conversation_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'assistant',
            'content': response.get('response', ''),
            'intent': response.get('intent'),
            'skill_used': response.get('skill_used')
        })
        
        # Update context based on response
        if response.get('intent') and response['intent'] != 'fallback':
            context.user_intent = response['intent']
        
        # Check for follow-up questions
        if response.get('requires_followup'):
            context.unresolved_questions.append(response.get('followup_question', ''))
    
    # Helper methods for flow analysis
    async def detect_topic_shift(self, context: ConversationContext, text: str) -> bool:
        """Detect if there's a topic shift in conversation"""
        if not context.current_topic:
            return False
        
        # Simple keyword-based topic detection
        current_topic_keywords = context.current_topic.lower().split() if context.current_topic else []
        text_words = text.lower().split()
        
        # If no overlap in keywords, might be topic shift
        overlap = set(current_topic_keywords) & set(text_words)
        return len(overlap) == 0 and len(text_words) > 2
    
    async def needs_emotional_support(self, text: str) -> bool:
        """Check if the user needs emotional support"""
        emotional_indicators = [
            'feeling', 'stressed', 'tired', 'sad', 'worried', 'anxious', 
            'depressed', 'overwhelmed', 'frustrated', 'angry', 'upset',
            'sleep', 'sleepy', 'exhausted', 'help me', 'support'
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in emotional_indicators)
    
    async def is_conversation_continuation(self, context: ConversationContext, text: str) -> bool:
        """Check if this is continuing a previous conversation"""
        if len(context.conversation_history) < 2:
            return False
        
        # Look for continuation indicators
        continuation_indicators = ['also', 'and', 'but', 'however', 'what about', 'how about']
        text_lower = text.lower()
        
        return any(indicator in text_lower for indicator in continuation_indicators)
    
    async def extract_topic(self, text: str) -> str:
        """Extract main topic from text"""
        # Simple topic extraction - can be enhanced with NLP
        words = text.lower().split()
        
        # Common topic indicators
        topic_keywords = {
            'weather': ['weather', 'temperature', 'forecast', 'climate', 'rain', 'sunny'],
            'health': ['health', 'sleep', 'tired', 'wellness', 'feeling', 'energy'],
            'technology': ['computer', 'software', 'app', 'technology', 'coding', 'programming'],
            'work': ['work', 'job', 'office', 'meeting', 'project', 'task'],
            'time': ['time', 'clock', 'schedule', 'calendar', 'appointment']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in words for keyword in keywords):
                return topic
        
        # Default to first few significant words
        significant_words = [word for word in words if len(word) > 3]
        return ' '.join(significant_words[:2]) if significant_words else 'general'
    
    async def map_intent_to_skill(self, intent: str) -> str:
        """Map detected intent to appropriate skill"""
        intent_mapping = {
            'greeting': 'greeting',
            'farewell': 'greeting',
            'weather_query': 'weather',
            'health_query': 'health_wellness',
            'sleep_query': 'health_wellness',
            'time_query': 'time',
            'calculation': 'calculate',
            'question': 'knowledge',
            'help': 'help',
            'emotional_support': 'emotional_intelligence',
            'personal_check': 'emotional_intelligence',
            'wellbeing': 'emotional_intelligence'
        }
        
        return intent_mapping.get(intent, 'fallback')
    
    async def is_new_topic(self, text: str, current_topic: str) -> bool:
        """Check if the text introduces a new topic"""
        if not current_topic:
            return True
        
        new_topic = await self.extract_topic(text)
        return new_topic != current_topic
    
    # Placeholder methods for more complex flow analysis
    async def detect_intent_change(self, context: ConversationContext, text: str) -> bool:
        return False
    
    async def needs_clarification(self, context: ConversationContext, text: str) -> bool:
        return len(text.split()) < 2  # Very short messages might need clarification
    
    async def should_restore_context(self, context: ConversationContext, text: str) -> bool:
        return False
    
    async def should_recall_memory(self, context: ConversationContext, text: str) -> bool:
        return False
    
    async def requires_follow_up(self, context: ConversationContext, text: str) -> bool:
        return False
    
    async def handle_topic_shift(self, context: ConversationContext, text: str, response_context: Dict) -> Dict:
        return await self.handle_normal_flow(context, text, response_context)
    
    async def handle_clarification_request(self, context: ConversationContext, text: str, response_context: Dict) -> Dict:
        return {
            'success': True,
            'response': "Could you provide a bit more detail about what you're looking for?",
            'intent': 'clarification'
        }
    
    async def handle_context_restoration(self, context: ConversationContext, text: str, response_context: Dict) -> Dict:
        return await self.handle_normal_flow(context, text, response_context)
    
    async def determine_skill_for_topic(self, topic: str, text: str) -> str:
        """Determine which skill to use based on topic and text"""
        topic_skill_mapping = {
            'weather': 'weather',
            'health': 'health_wellness',
            'technology': 'knowledge',
            'work': 'task_manager',
            'time': 'time'
        }
        
        return topic_skill_mapping.get(topic, 'knowledge')


class ConversationMemoryEngine:
    """Simple in-memory conversation memory engine"""
    
    def __init__(self):
        self.conversation_memory = {}
    
    async def store_conversation(self, session_id: str, context: ConversationContext):
        """Store conversation context"""
        self.conversation_memory[session_id] = context
    
    async def retrieve_conversation(self, session_id: str) -> Optional[ConversationContext]:
        """Retrieve conversation context"""
        return self.conversation_memory.get(session_id)
