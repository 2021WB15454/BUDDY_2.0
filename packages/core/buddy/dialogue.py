"""
BUDDY Dialogue Manager

Manages conversation state, context, and dialogue flow. Handles multi-turn
conversations, intent disambiguation, and response planning using both
rule-based and model-based approaches.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from .events import EventBus, Event, get_event_bus
from .skills import SkillRegistry
from .conversation_flow import ConversationFlowManager
from .device_context import DeviceContextManager, DeviceType

logger = logging.getLogger(__name__)


class DialogueState(Enum):
    """Current state of the dialogue."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    WAITING_FOR_CONFIRMATION = "waiting_confirmation"
    WAITING_FOR_CLARIFICATION = "waiting_clarification"
    ERROR = "error"


@dataclass
class DialogueContext:
    """Context information for the current dialogue."""
    
    user_id: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = "unknown"
    location: Optional[str] = None
    time_zone: str = "UTC"
    language: str = "en"
    previous_intents: List[str] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    current_skill: Optional[str] = None
    pending_confirmations: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)


@dataclass
class DialogueTurn:
    """Represents a single turn in the conversation."""
    
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_input: str = ""
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    system_response: str = ""
    skill_invocations: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None


class DialogueManager:
    """
    Core dialogue management system for BUDDY.
    
    Handles conversation flow, context management, and response planning
    with support for multi-turn conversations and error recovery.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None, skill_registry: Optional[SkillRegistry] = None):
        self.event_bus = event_bus or get_event_bus()
        self.active_contexts: Dict[str, DialogueContext] = {}
        self.dialogue_policies: Dict[str, callable] = {}
        self.confirmation_handlers: Dict[str, callable] = {}
        self.session_timeout = timedelta(minutes=30)
        self.skill_registry = skill_registry  # late-bound by runtime
        
        # Initialize conversation flow manager
        self.flow_manager = ConversationFlowManager(skill_registry, self.event_bus)
        
        # Initialize device context manager
        self.device_manager = DeviceContextManager()
        
        # Subscribe to relevant events
        self.event_bus.subscribe("nlu.intent", self._handle_intent)
        self.event_bus.subscribe("audio.speech_end", self._handle_speech_end)
        self.event_bus.subscribe("skill.result", self._handle_skill_result)
        self.event_bus.subscribe("user.confirmation", self._handle_confirmation)
        
        logger.info("Dialogue manager initialized with conversation flow management")
        
    async def start_session(self, user_id: str, device_id: str, 
                           context_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new dialogue session.
        
        Args:
            user_id: User identifier
            device_id: Device identifier
            context_data: Additional context information
            
        Returns:
            Session ID
        """
        context = DialogueContext(
            user_id=user_id,
            device_id=device_id
        )
        
        if context_data:
            context.location = context_data.get("location")
            context.time_zone = context_data.get("time_zone", "UTC")
            context.language = context_data.get("language", "en")
            context.user_preferences = context_data.get("preferences", {})
            
        self.active_contexts[context.session_id] = context
        
        await self.event_bus.publish(
            "dialogue.session_started",
            {
                "session_id": context.session_id,
                "user_id": user_id,
                "device_id": device_id
            },
            source="dialogue_manager"
        )
        
        logger.info(f"Started dialogue session {context.session_id} for user {user_id}")
        return context.session_id
        
    async def end_session(self, session_id: str):
        """End a dialogue session."""
        if session_id in self.active_contexts:
            context = self.active_contexts[session_id]
            del self.active_contexts[session_id]
            
            await self.event_bus.publish(
                "dialogue.session_ended",
                {
                    "session_id": session_id,
                    "duration_minutes": (datetime.now() - context.created_at).total_seconds() / 60,
                    "turns": len(context.conversation_history)
                },
                source="dialogue_manager"
            )
            
            logger.info(f"Ended dialogue session {session_id}")
            
    async def process_turn(self, session_id: str, user_input: str, 
                          intent_data: Optional[Dict[str, Any]] = None) -> DialogueTurn:
        """
        Process a single dialogue turn with advanced flow management.
        
        Args:
            session_id: Session identifier
            user_input: User's input text
            intent_data: Pre-processed intent information
            
        Returns:
            DialogueTurn object with results
        """
        if session_id not in self.active_contexts:
            raise ValueError(f"Session {session_id} not found")
            
        context = self.active_contexts[session_id]
        context.last_activity = datetime.now()
        
        turn = DialogueTurn(user_input=user_input)
        start_time = datetime.now()
        
        try:
            # Prepare message for flow manager
            message = {
                'text': user_input,
                'session_id': session_id,
                'user_id': context.user_id,
                'timestamp': datetime.now().isoformat()
            }

            # Prepare device context with comprehensive information
            device_context = self.device_manager.create_device_context(
                device_id=context.device_id,
                device_type=None,  # Auto-detect
                user_agent="",  # Can be enhanced with actual user agent
                device_info=None,  # Can be enhanced with actual device info
                location=context.location
            )

            # Use conversation flow manager for advanced processing
            flow_response = await self.flow_manager.manage_conversation_flow(message, device_context)

            if flow_response and flow_response.get('success'):
                # Extract response information from flow manager
                turn.intent = flow_response.get('intent', 'unknown')
                turn.entities = flow_response.get('entities', {})
                turn.confidence = 0.8  # Flow manager provides good confidence

                # Adapt response for device
                raw_response = flow_response.get('response', '')
                turn.system_response = self.device_manager.adapt_response_for_device(raw_response, device_context)
                turn.success = True

                # Update context with flow metadata
                if flow_response.get('flow_metadata'):
                    metadata = flow_response['flow_metadata']
                    context.current_skill = flow_response.get('skill_used')

                    # Store conversation topic if available
                    if metadata.get('topic'):
                        context.entities['current_topic'] = metadata['topic']

            else:
                # Fallback to original processing if flow manager fails
                logger.warning("Flow manager failed, falling back to basic processing")

                # Extract or use provided intent data
                if intent_data:
                    turn.intent = intent_data.get("intent")
                    turn.entities = intent_data.get("entities", {})
                    turn.confidence = intent_data.get("confidence", 0.0)
                else:
                    # Use advanced NLU skill for intent detection if available
                    nlu_result = await self._use_nlu_skill(turn.user_input)
                    if nlu_result and nlu_result.get("intent") != "unknown":
                        turn.intent = nlu_result.get("intent")
                        turn.entities = nlu_result.get("entities", {})
                        turn.confidence = nlu_result.get("confidence", 0.0)
                    else:
                        # Fallback to basic intent detection
                        turn.intent, turn.entities = self._detect_intent(turn.user_input)

                # Apply dialogue policy
                response_plan = await self._apply_policy(context, turn)

                # Execute planned actions
                await self._execute_plan(context, turn, response_plan)

            # Update context with new information
            if turn.intent:
                context.previous_intents.append(turn.intent)
                context.entities.update(turn.entities)

            # Calculate duration
            turn.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Add to conversation history
            context.conversation_history.append(turn.__dict__)

            # Publish turn completion
            await self.event_bus.publish(
                "dialogue.turn_completed",
                {
                    "session_id": session_id,
                    "turn_id": turn.turn_id,
                    "intent": turn.intent,
                    "success": turn.success,
                    "duration_ms": turn.duration_ms
                },
                source="dialogue_manager"
            )

        except Exception as e:
            turn.success = False
            turn.error_message = str(e)
            turn.system_response = "I'm sorry, I encountered an error processing your request."
            logger.error(f"Error processing dialogue turn: {e}")

        return turn
        
    async def _apply_policy(self, context: DialogueContext, turn: DialogueTurn) -> Dict[str, Any]:
        """
        Apply dialogue policy to determine response plan.
        
        Args:
            context: Current dialogue context
            turn: Current turn information
            
        Returns:
            Response plan dictionary
        """
        intent = turn.intent
        
        # Check for confirmation or clarification needs
        if self._needs_confirmation(intent, turn.entities):
            return {
                "action": "request_confirmation",
                "message": f"Do you want me to {intent} with {turn.entities}?",
                "pending_action": {
                    "intent": intent,
                    "entities": turn.entities
                }
            }
            
        if self._needs_clarification(intent, turn.entities):
            return {
                "action": "request_clarification",
                "message": "Could you provide more details?",
                "missing_entities": self._get_missing_entities(intent, turn.entities)
            }
            
        # Standard skill execution
        return {
            "action": "execute_skill",
            "skill_name": self._map_intent_to_skill(intent),
            "parameters": turn.entities
        }
        
    async def _execute_plan(self, context: DialogueContext, turn: DialogueTurn, plan: Dict[str, Any]):
        """Execute the planned response actions."""
        action = plan.get("action")
        
        if action == "execute_skill":
            await self._execute_skill(context, turn, plan)
        elif action == "request_confirmation":
            await self._request_confirmation(context, turn, plan)
        elif action == "request_clarification":
            await self._request_clarification(context, turn, plan)
        else:
            turn.system_response = "I'm not sure how to handle that request."
            
    async def _execute_skill(self, context: DialogueContext, turn: DialogueTurn, plan: Dict[str, Any]):
        """Execute a skill based on the plan."""
        skill_name = plan.get("skill_name")
        parameters = plan.get("parameters", {})
        
        # Prefer direct execution when SkillRegistry is available
        if self.skill_registry is not None:
            result = await self.skill_registry.execute_skill(
                skill_name,
                parameters,
                {
                    "session_id": context.session_id,
                    "turn_id": turn.turn_id,
                    "user_id": context.user_id,
                    "device_id": context.device_id
                }
            )
            if result.success:
                # Expect data.text for user-visible message
                data = result.data or {}
                turn.system_response = data.get("text") or str(data)
            else:
                turn.system_response = result.error_message or "Skill failed."
        else:
            # Fallback to event-based execution (legacy path)
            await self.event_bus.publish(
                "skill.execute",
                {
                    "skill_name": skill_name,
                    "parameters": parameters,
                    "session_id": context.session_id,
                    "turn_id": turn.turn_id,
                    "user_id": context.user_id
                },
                source="dialogue_manager"
            )
        
        context.current_skill = skill_name
        turn.skill_invocations.append({
            "skill": skill_name,
            "parameters": parameters,
            "timestamp": datetime.now().isoformat()
        })
        
    async def _request_confirmation(self, context: DialogueContext, turn: DialogueTurn, plan: Dict[str, Any]):
        """Request user confirmation for an action."""
        message = plan.get("message", "Do you want me to proceed?")
        pending_action = plan.get("pending_action")
        
        context.pending_confirmations.append(pending_action)
        turn.system_response = message
        
        await self.event_bus.publish(
            "tts.speak",
            {
                "text": message,
                "session_id": context.session_id,
                "priority": "high"
            },
            source="dialogue_manager"
        )
        
    async def _request_clarification(self, context: DialogueContext, turn: DialogueTurn, plan: Dict[str, Any]):
        """Request clarification from the user."""
        message = plan.get("message", "Could you provide more details?")
        turn.system_response = message
        
        await self.event_bus.publish(
            "tts.speak",
            {
                "text": message,
                "session_id": context.session_id,
                "priority": "high"
            },
            source="dialogue_manager"
        )
        
    def _needs_confirmation(self, intent: str, entities: Dict[str, Any]) -> bool:
        """Check if the intent requires user confirmation."""
        high_risk_intents = [
            "delete_file", "send_email", "make_purchase", 
            "transfer_money", "schedule_meeting", "send_message"
        ]
        return intent in high_risk_intents
        
    def _needs_clarification(self, intent: str, entities: Dict[str, Any]) -> bool:
        """Check if the intent needs clarification."""
        required_entities = self._get_required_entities(intent)
        missing = [e for e in required_entities if e not in entities]
        return len(missing) > 0
        
    def _get_required_entities(self, intent: str) -> List[str]:
        """Get required entities for an intent."""
        entity_requirements = {
            "set_reminder": ["title", "time"],
            "play_music": ["artist", "song"],
            "send_message": ["recipient", "message"],
            "set_timer": ["duration"],
            "weather": ["location"],
        }
        return entity_requirements.get(intent, [])
        
    def _get_missing_entities(self, intent: str, entities: Dict[str, Any]) -> List[str]:
        """Get missing required entities."""
        required = self._get_required_entities(intent)
        return [e for e in required if e not in entities]
        
    def _map_intent_to_skill(self, intent: str) -> str:
        """Enhanced intent to skill mapping with comprehensive advanced skills coverage."""
        intent_skill_mapping = {
            # Core conversational
            "greeting": "greeting",
            "farewell": "greeting",
            "gratitude": "emotional_intelligence",
            "personal_status": "emotional_intelligence",
            "personal_check": "emotional_intelligence",
            
            # Information and knowledge
            "time": "time",
            "date": "time",
            "weather": "weather",
            "weather_query": "weather",
            "question": "knowledge",
            "help": "help",
            
            # Task and productivity
            "calculate": "calculate",
            "calculation": "calculate",
            "set_reminder": "reminders",
            "reminder": "reminders",
            "task": "task_manager",
            "schedule": "task_manager",
            "productivity": "productivity_integration",
            
            # Health and wellness
            "health_query": "health_wellness",
            "sleep_query": "health_wellness",
            "wellbeing": "health_wellness",
            
            # Emotional and social
            "stress": "emotional_intelligence",
            "sadness": "emotional_intelligence",
            "anger": "emotional_intelligence",
            "joy": "emotional_intelligence",
            "complaint": "emotional_intelligence",
            "compliment": "emotional_intelligence",
            
            # Smart home and devices
            "smart_home": "smart_home",
            "device_control": "smart_home",
            "cross_device": "cross_device_coordination",
            
            # Communication
            "communication": "communication_integration",
            "message": "communication_integration",
            "meeting": "communication_integration",
            
            # System and general
            "system_status": "fallback",
            "creative": "knowledge",
            "search": "knowledge",
            "time_query": "time",
            "fallback": "fallback",
            "unknown": "fallback"
        }
        return intent_skill_mapping.get(intent, "fallback")

    def _detect_intent(self, text: str):
        """Enhanced rule-based intent detection with better context understanding."""
        if not text:
            return "fallback", {}
            
        t = text.lower().strip()
        entities = {}
        
        # Greeting intents
        if any(w in t for w in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
            return "greeting", {"message_type": "greeting"}
        
        # Farewell intents
        if any(w in t for w in ["bye", "goodbye", "see you", "farewell", "talk later"]):
            return "farewell", {"message_type": "farewell"}
        
        # Time-related intents
        if any(w in t for w in ["time", "clock", "what time", "current time"]):
            return "time", {"query_type": "current_time"}
        
        # Date-related intents
        if any(w in t for w in ["date", "today", "what day", "current date"]):
            return "date", {"query_type": "current_date"}
        
        # Weather intents with entity extraction
        if "weather" in t:
            # Enhanced city extraction
            city = self._extract_city_from_weather_query(t)
            if city:
                entities["location"] = city
            return "weather", entities
        
        # Calculation intents with enhanced entity extraction
        if any(w in t for w in ["calculate", "math", "compute", "+", "-", "*", "/", "percent", "square root"]):
            expression = self._extract_math_expression(t)
            if expression:
                entities["expression"] = expression
            return "calculate", entities
        
        # Reminder intents with better parsing
        if any(w in t for w in ["remind", "reminder", "set reminder"]):
            reminder_data = self._extract_reminder_details(t)
            entities.update(reminder_data)
            return "set_reminder", entities
        
        # Help intents
        if any(w in t for w in ["help", "what can you do", "capabilities", "features"]):
            return "help", {"help_type": "general"}
        
        # Status/system intents
        if any(w in t for w in ["status", "system", "health", "performance", "metrics"]):
            return "system_status", {"status_type": "general"}
        
        # Question intents
        if any(w in t for w in ["what is", "tell me about", "explain", "define", "how does"]):
            topic = self._extract_question_topic(t)
            if topic:
                entities["topic"] = topic
            return "question", entities
        
        # Personal status inquiry
        if any(w in t for w in ["how are you", "how's it going", "how do you feel"]):
            return "personal_status", {"query_type": "assistant_status"}
        
        # Gratitude
        if any(w in t for w in ["thank", "thanks", "appreciate"]):
            return "gratitude", {"message_type": "thanks"}
        
        # Creative requests
        if any(w in t for w in ["create", "generate", "write", "make", "compose"]):
            creative_type = self._extract_creative_type(t)
            if creative_type:
                entities["creative_type"] = creative_type
            return "creative", entities
        
        # Fallback for unrecognized intents
        return "fallback", {"original_text": text}
    
    def _extract_city_from_weather_query(self, text: str) -> Optional[str]:
        """Extract city name from weather queries."""
        import re
        patterns = [
            r'weather\s+in\s+([a-zA-Z\s]+?)(?:\?|\.|\,|$)',
            r'weather\s+for\s+([a-zA-Z\s]+?)(?:\?|\.|\,|$)',
            r'weather\s+([a-zA-Z\s]+?)(?:\?|\.|\,|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                city = match.group(1).strip()
                # Clean up common words
                exclude_words = {'the', 'is', 'today', 'tomorrow', 'like', 'what', 'how'}
                city_words = [word for word in city.split() if word not in exclude_words]
                if city_words:
                    return ' '.join(city_words).title()
        return None
    
    def _extract_math_expression(self, text: str) -> Optional[str]:
        """Extract mathematical expressions from text."""
        import re
        
        # Look for mathematical expressions
        patterns = [
            r'(\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)',  # Basic operations
            r'(\d+)\s*percent\s*of\s*(\d+)',  # Percentage
            r'square\s*root\s*of\s*(\d+(?:\.\d+)?)',  # Square root
            r'(\d+)\s*\^\s*(\d+)',  # Exponents
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(0)
        
        return None
    
    def _extract_reminder_details(self, text: str) -> Dict[str, Any]:
        """Extract reminder details from text."""
        import re
        details = {}
        
        # Extract title
        if "remind me to" in text.lower():
            parts = text.lower().split("remind me to", 1)
            if len(parts) > 1:
                title_part = parts[1].strip()
                # Remove time information if present
                title = re.sub(r'\s+(at|in|on)\s+.*', '', title_part).strip()
                if title:
                    details["title"] = title
        
        # Extract time information
        time_patterns = [
            r'at\s+(\d{1,2}:\d{2})',
            r'at\s+(\d{1,2}\s*(am|pm))',
            r'in\s+(\d+)\s*(minutes?|hours?|days?)',
            r'on\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'tomorrow',
            r'today'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text.lower())
            if match:
                details["time"] = match.group(0)
                break
        
        return details
    
    def _extract_question_topic(self, text: str) -> Optional[str]:
        """Extract the main topic from a question."""
        import re
        
        # Remove question words and extract the main topic
        question_starters = r'^(what\s+is|tell\s+me\s+about|explain|define|how\s+does)\s+'
        topic_text = re.sub(question_starters, '', text.lower()).strip()
        
        if topic_text and len(topic_text) > 2:
            # Remove trailing punctuation
            topic_text = re.sub(r'[?.!]+$', '', topic_text)
            return topic_text
        
        return None
    
    def _extract_creative_type(self, text: str) -> Optional[str]:
        """Extract the type of creative request."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["joke", "funny", "humor"]):
            return "joke"
        elif any(word in text_lower for word in ["story", "tale", "narrative"]):
            return "story"
        elif any(word in text_lower for word in ["poem", "poetry", "verse"]):
            return "poem"
        elif any(word in text_lower for word in ["idea", "brainstorm"]):
            return "idea"
        
        return "general"
        
    async def _handle_intent(self, event: Event):
        """Handle intent recognition events."""
        payload = event.payload
        session_id = payload.get("session_id")
        turn_id = payload.get("turn_id")
        
        if session_id in self.active_contexts:
            # Update dialogue state based on intent
            context = self.active_contexts[session_id]
            # Implementation would coordinate with ongoing turns
            
    async def _handle_speech_end(self, event: Event):
        """Handle end of speech events."""
        # Trigger processing of completed speech input
        pass
        
    async def _handle_skill_result(self, event: Event):
        """Handle skill execution results."""
        payload = event.payload
        session_id = payload.get("session_id")
        turn_id = payload.get("turn_id")
        result = payload.get("result")
        
        if session_id in self.active_contexts:
            context = self.active_contexts[session_id]
            # Update turn with skill result and generate response
            
    async def _handle_confirmation(self, event: Event):
        """Handle user confirmations."""
        payload = event.payload
        session_id = payload.get("session_id")
        confirmed = payload.get("confirmed", False)
        
        if session_id in self.active_contexts:
            context = self.active_contexts[session_id]
            if context.pending_confirmations and confirmed:
                # Execute pending action
                pending = context.pending_confirmations.pop(0)
                await self._execute_confirmed_action(context, pending)
                
    async def _execute_confirmed_action(self, context: DialogueContext, action: Dict[str, Any]):
        """Execute a previously confirmed action."""
        await self.event_bus.publish(
            "skill.execute",
            {
                "skill_name": self._map_intent_to_skill(action["intent"]),
                "parameters": action["entities"],
                "session_id": context.session_id,
                "user_id": context.user_id,
                "confirmed": True
            },
            source="dialogue_manager"
        )
        
    async def cleanup_expired_sessions(self):
        """Clean up expired dialogue sessions."""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, context in self.active_contexts.items():
            if now - context.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
                
        for session_id in expired_sessions:
            await self.end_session(session_id)
            
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a dialogue session."""
        if session_id not in self.active_contexts:
            return None
            
        context = self.active_contexts[session_id]
        return {
            "session_id": session_id,
            "user_id": context.user_id,
            "device_id": context.device_id,
            "created_at": context.created_at.isoformat(),
            "last_activity": context.last_activity.isoformat(),
            "turns": len(context.conversation_history),
            "current_skill": context.current_skill,
            "pending_confirmations": len(context.pending_confirmations)
        }

    async def _use_nlu_skill(self, text: str) -> Optional[Dict[str, Any]]:
        """Use the advanced NLU skill for intent detection and entity extraction."""
        try:
            if hasattr(self, 'skill_registry') and self.skill_registry:
                nlu_skill = self.skill_registry.get_skill("nlu")
                if nlu_skill:
                    result = await nlu_skill.execute({"text": text}, {})
                    if result.success:
                        return result.data
            return None
        except Exception as e:
            logger.warning(f"Failed to use NLU skill: {e}")
            return None
