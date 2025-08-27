from __future__ import annotations
"""Enhanced BUDDY Conversation Manager.

This file now provides two classes:
 - BUDDYConversationManager (original lightweight skeleton retained for backward compatibility)
 - BUDDYEnhancedConversationManager (advanced, context + personality aware manager)

The enhanced manager introduces:
 - Rich ConversationContext dataclass
 - Intent detection with confidence + alternative intents
 - Personality + proactive suggestions
 - Emotion & task complexity analysis
 - Structured response metadata
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
import re
import random
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Backward compatible original class (unchanged public API)
# ---------------------------------------------------------------------------
class BUDDYConversationManager:
    """Original simple conversation manager retained for existing integrations."""

    def __init__(self):
        self.conversation_state = "attentive"
        self.user_preferences: Dict[str, Any] = {}
        self.interaction_history: List[Dict[str, Any]] = []

    async def maintain_conversation_flow(self, user_input: str, context: Dict[str, Any]) -> str:
        ctype = self.detect_conversation_type(user_input, context)
        if ctype == "casual_chat":
            return await self.handle_casual_interaction(user_input, context)
        if ctype == "task_request":
            return await self.handle_task_request(user_input, context)
        if ctype == "information_query":
            return await self.handle_information_query(user_input, context)
        if ctype == "problem_solving":
            return await self.handle_problem_solving(user_input, context)
        return await self.handle_general_interaction(user_input, context)

    def detect_conversation_type(self, user_input: str, context: Dict[str, Any]) -> str:
        low = user_input.lower()
        if any(k in low for k in ["fix", "error", "issue", "problem"]):
            return "problem_solving"
        if low.endswith("?"):
            return "information_query"
        if any(k in low for k in ["schedule", "remind", "set", "create"]):
            return "task_request"
        if any(k in low for k in ["hey", "hi", "hello"]):
            return "casual_chat"
        return "general"

    async def analyze_task_complexity(self, task_text: str) -> Dict[str, Any]:
        length = len(task_text.split())
        if length < 6:
            return {"complexity": "simple", "task": task_text}
        if length < 20:
            return {"complexity": "moderate", "task": task_text}
        return {"complexity": "complex", "task": task_text}

    async def break_down_complex_task(self, task_text: str) -> List[Dict[str, Any]]:
        segments = task_text.split('.')
        subtasks = []
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            subtasks.append({"description": seg, "estimated_time": "~5-15m"})
        if not subtasks:
            subtasks.append({"description": task_text, "estimated_time": "~15m"})
        return subtasks

    async def present_task_breakdown(self, subtasks: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        addr = context.get('user_name', 'Sir')
        lines = [f"I've analyzed your request, {addr}. To accomplish this efficiently, consider the following steps:\n"]
        for i, st in enumerate(subtasks, 1):
            lines.append(f"{i}. {st['description']}")
            if st.get('estimated_time'):
                lines.append(f"   Estimated time: {st['estimated_time']}")
        lines.append("\nShall I proceed with step one, or would you prefer to review the approach first?")
        return "\n".join(lines)

    async def handle_task_request(self, user_input: str, context: Dict[str, Any]) -> str:
        analysis = await self.analyze_task_complexity(user_input)
        if analysis['complexity'] == 'complex':
            subtasks = await self.break_down_complex_task(analysis['task'])
            return await self.present_task_breakdown(subtasks, context)
        return f"Certainly. I will handle: {analysis['task']}"

    async def handle_casual_interaction(self, user_input: str, context: Dict[str, Any]) -> str:
        return f"Good to hear from you, {context.get('user_name','there')}. How shall we proceed?"

    async def handle_information_query(self, user_input: str, context: Dict[str, Any]) -> str:
        return "I will compile the relevant information and revert promptly."

    async def handle_problem_solving(self, user_input: str, context: Dict[str, Any]) -> str:
        return "Let's isolate variables and iterate toward a resolution. Provide any recent changes if available."

    async def handle_general_interaction(self, user_input: str, context: Dict[str, Any]) -> str:
        return "Acknowledged. Ready to assist further."


# ---------------------------------------------------------------------------
# Enhanced Conversation Manager
# ---------------------------------------------------------------------------
class ConversationState(Enum):
    ATTENTIVE = "attentive"
    PROCESSING = "processing"
    LEARNING = "learning"
    WAITING_FOR_INPUT = "waiting_for_input"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class ConversationContext:
    user_id: str
    user_name: Optional[str]
    device_type: str
    session_id: str
    timestamp: datetime
    location: Optional[str] = None
    mood: Optional[str] = None
    urgency_level: int = 1  # 1-5 scale
    previous_topics: Optional[List[str]] = None

    def __post_init__(self):
        if self.previous_topics is None:
            self.previous_topics = []


@dataclass
class ResponseMetadata:
    confidence: float
    intent_type: str
    requires_followup: bool
    suggested_actions: List[str]
    processing_time_ms: float


class BUDDYEnhancedConversationManager:
    """Advanced conversation manager with personality, memory, and context awareness."""

    def __init__(self, personality_profile: Optional[Dict[str, float]] = None, legacy_string_output: bool = False):
        self.conversation_state = ConversationState.ATTENTIVE
        self.user_preferences: Dict[str, Any] = {}
        self.interaction_history: List[Dict[str, Any]] = []
        self.conversation_memory: Dict[str, List[Dict[str, Any]]] = {}
        self.topic_transitions: List[Tuple[str, str]] = []
        self.legacy_string_output = legacy_string_output  # if True mimic old API returning str only

        # Personality configuration
        self.personality = personality_profile or {
            'formality_level': 0.7,
            'humor_frequency': 0.3,
            'proactivity': 0.8,
            'empathy_level': 0.9,
            'technical_depth': 0.8,
        }

        # Intent patterns
        self.intent_patterns: Dict[str, List[str]] = {
            'greeting': [
                r'\b(hi|hello|hey|good\s+(morning|afternoon|evening)|greetings)\b',
                r'\b(what\'s\s+up|how\s+are\s+you|how\s+do\s+you\s+do)\b',
            ],
            'farewell': [
                r'\b(bye|goodbye|see\s+you|farewell|take\s+care|catch\s+you\s+later)\b',
                r'\b(gotta\s+go|talk\s+to\s+you\s+later|ttyl)\b',
            ],
            'task_request': [
                r'\b(remind|schedule|set|create|add|book|plan|organize)\b',
                r'\b(can\s+you|could\s+you|please|would\s+you)\b.*\b(help|assist|do)\b',
                r'\b(make\s+a|create\s+a|set\s+up|establish)\b',
            ],
            'information_query': [
                r'\b(what|when|where|who|why|how|which)\b',
                r'\b(tell\s+me|show\s+me|explain|describe|define)\b',
                r'\b(information\s+about|details\s+on|facts\s+about)\b',
            ],
            'problem_solving': [
                r'\b(fix|solve|resolve|troubleshoot|debug|repair)\b',
                r'\b(error|issue|problem|bug|trouble|difficulty)\b',
                r'\b(not\s+working|broken|failed|crashed)\b',
            ],
            'personal_question': [
                r'\b(who\s+are\s+you|what\s+are\s+you|tell\s+me\s+about\s+yourself)\b',
                r'\b(your\s+(name|purpose|capabilities|features))\b',
                r'\b(how\s+do\s+you\s+work|how\s+were\s+you\s+made)\b',
            ],
            'emotional_support': [
                r'\b(sad|happy|excited|angry|frustrated|worried|anxious|stressed)\b',
                r'\b(feel|feeling|felt|emotion|mood)\b',
                r'\b(help\s+me\s+with|support|comfort|cheer\s+up)\b',
            ],
            'compliment': [
                r'\b(great|awesome|excellent|amazing|fantastic|wonderful)\b',
                r'\b(good\s+job|well\s+done|impressive|helpful|useful)\b',
                r'\b(thank\s+you|thanks|appreciate|grateful)\b',
            ],
            'complaint': [
                r'\b(terrible|awful|horrible|useless|stupid|annoying)\b',
                r'\b(hate|dislike|don\'t\s+like|frustrated\s+with)\b',
                r'\b(wrong|incorrect|mistake|error)\b',
            ],
        }

        # Response templates
        self.response_templates: Dict[str, Any] = {
            'greeting': {
                'formal': [
                    "Good {time_of_day}, {user_name}. How may I assist you today?",
                    "Hello {user_name}. I trust you're having a pleasant {time_of_day}.",
                    "Welcome back, {user_name}. What shall we accomplish together?",
                ],
                'casual': [
                    "Hey {user_name}! What's up?",
                    "Hi there! Ready to tackle the day?",
                    "Hello {user_name}! How can I help you out?",
                ],
                'warm': [
                    "It's wonderful to see you again, {user_name}! How are you feeling today?",
                    "Hello {user_name}! I hope you're having a great day. What can I do for you?",
                    "Hi {user_name}! I'm here and ready to help with whatever you need.",
                ],
            },
            'farewell': [
                "Goodbye {user_name}. Feel free to call on me anytime.",
                "Take care {user_name}. I'll be here when you return.",
                "See you later {user_name}! Ready whenever you are.",
            ],
            'task_acknowledgment': {
                'efficient': [
                    "Certainly, {user_name}. I'll take care of that immediately.",
                    "Consider it done. Processing your request now.",
                    "Understood. I'm on it.",
                ],
                'detailed': [
                    "I've received your request, {user_name}. Let me break this down and ensure I handle it perfectly.",
                    "Excellent choice. I'll process this systematically to ensure optimal results.",
                    "I understand exactly what you need. Allow me to handle this with precision.",
                ],
            },
            'information_delivery': [
                "Here's what I found for you, {user_name}:",
                "I've gathered the following information:",
                "Based on my analysis, here are the key points:",
                "Let me share what I've discovered:",
            ],
            'empathy_responses': [
                "I understand how you're feeling, {user_name}.",
                "That sounds meaningful, and I'm here to help.",
                "I can sense this matters to you. Let's work through it together.",
            ],
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def maintain_conversation_flow(self, user_input: str, context: ConversationContext) -> Dict[str, Any] | str:
        """Main conversation flow manager.

        Returns a structured dict. If legacy_string_output=True, returns just the response text.
        """
        start_time = datetime.now()
        try:
            self.conversation_state = ConversationState.PROCESSING

            await self._record_interaction(user_input, context)
            intent_result = await self.detect_advanced_intent(user_input, context)
            response_payload = await self._generate_contextual_response(user_input, intent_result, context)
            await self._update_user_preferences(user_input, response_payload, context)

            processing_time = (datetime.now() - start_time).total_seconds() * 1000.0
            metadata = ResponseMetadata(
                confidence=intent_result['confidence'],
                intent_type=intent_result['primary_intent'],
                requires_followup=response_payload.get('requires_followup', False),
                suggested_actions=response_payload.get('suggested_actions', []),
                processing_time_ms=processing_time,
            )

            self.conversation_state = ConversationState.ATTENTIVE

            result = {
                'response': response_payload['text'],
                'metadata': asdict(metadata),
                'context_updated': True,
                'personality_applied': True,
            }
            return result['response'] if self.legacy_string_output else result
        except Exception as e:  # pragma: no cover - defensive
            self.conversation_state = ConversationState.ERROR_RECOVERY
            return await self._handle_conversation_error(e, user_input, context)

    # ------------------------------------------------------------------
    # Intent Detection
    # ------------------------------------------------------------------
    async def detect_advanced_intent(self, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        user_input_lower = user_input.lower()
        intent_scores: Dict[str, float] = {}
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    score += 0.7
                    matches = re.findall(pattern, user_input_lower)
                    score += len(matches) * 0.3
            if score > 0:
                intent_scores[intent] = min(score, 1.0)

        await self._apply_context_boosting(intent_scores, user_input, context)

        if not intent_scores:
            primary_intent = 'general'
            confidence = 0.3
        else:
            primary_intent, confidence = max(intent_scores.items(), key=lambda x: x[1])

        alternative_intents = sorted(
            [(k, v) for k, v in intent_scores.items() if k != primary_intent],
            key=lambda x: x[1],
            reverse=True,
        )[:2]

        return {
            'primary_intent': primary_intent,
            'confidence': confidence,
            'alternative_intents': alternative_intents,
            'context_influenced': bool(context.previous_topics),
        }

    async def _apply_context_boosting(self, intent_scores: Dict[str, float], user_input: str, context: ConversationContext) -> None:
        current_hour = datetime.now().hour
        if 6 <= current_hour <= 10 and 'greeting' in intent_scores:
            intent_scores['greeting'] *= 1.2
        elif (22 <= current_hour or current_hour <= 5) and 'farewell' in intent_scores:
            intent_scores['farewell'] *= 1.2

        if context.device_type == 'mobile' and 'task_request' in intent_scores:
            intent_scores['task_request'] *= 1.1
        elif context.device_type == 'watch' and 'information_query' in intent_scores:
            intent_scores['information_query'] *= 1.3

        if context.previous_topics:
            last_topic = context.previous_topics[-1]
            if last_topic == 'problem_solving' and 'problem_solving' in intent_scores:
                intent_scores['problem_solving'] *= 1.4

    # ------------------------------------------------------------------
    # Response Generation Routing
    # ------------------------------------------------------------------
    async def _generate_contextual_response(self, user_input: str, intent_result: Dict[str, Any], context: ConversationContext) -> Dict[str, Any]:
        intent = intent_result['primary_intent']
        if intent == 'greeting':
            return await self.handle_greeting(user_input, context)
        if intent == 'farewell':
            return await self.handle_farewell(user_input, context)
        if intent == 'task_request':
            return await self.handle_task_request(user_input, context)
        if intent == 'information_query':
            return await self.handle_information_query(user_input, context)
        if intent == 'problem_solving':
            return await self.handle_problem_solving(user_input, context)
        if intent == 'personal_question':
            return await self.handle_personal_question(user_input, context)
        if intent == 'emotional_support':
            return await self.handle_emotional_support(user_input, context)
        if intent == 'compliment':
            return await self.handle_compliment(user_input, context)
        if intent == 'complaint':
            return await self.handle_complaint(user_input, context)
        return await self.handle_general_interaction(user_input, context)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    async def handle_greeting(self, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        user_name = context.user_name or "there"
        time_of_day = self._get_time_of_day()
        if self.personality['formality_level'] > 0.7:
            style = 'formal'
        elif self.personality['empathy_level'] > 0.8:
            style = 'warm'
        else:
            style = 'casual'
        template = random.choice(self.response_templates['greeting'][style])
        response_text = template.format(user_name=user_name, time_of_day=time_of_day)
        suggestions: List[str] = []
        if self.personality['proactivity'] > 0.7:
            suggestions = await self._generate_proactive_suggestions(context)
            if suggestions:
                response_text += f"\n\nI notice you might want to: {', '.join(suggestions[:2])}."
        return {
            'text': response_text,
            'requires_followup': False,
            'suggested_actions': suggestions,
            'emotion_detected': 'positive',
        }

    async def handle_farewell(self, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        user_name = context.user_name or "there"
        template = random.choice(self.response_templates['farewell'])
        return {
            'text': template.format(user_name=user_name),
            'requires_followup': False,
            'suggested_actions': ['resume_later', 'set_reminder'],
        }

    async def handle_task_request(self, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        complexity = await self.analyze_enhanced_task_complexity(user_input)
        user_name = context.user_name or "there"
        if complexity['complexity'] == 'simple':
            style = 'efficient' if self.personality['formality_level'] > 0.6 else 'detailed'
            template = random.choice(self.response_templates['task_acknowledgment'][style])
            return {
                'text': template.format(user_name=user_name),
                'requires_followup': False,
                'task_complexity': 'simple',
                'estimated_time': complexity.get('estimated_time', '5 minutes'),
            }
        if complexity['complexity'] == 'complex':
            subtasks = await self.break_down_complex_task(user_input)
            breakdown = await self.present_enhanced_task_breakdown(subtasks, context)
            return {
                'text': breakdown,
                'requires_followup': True,
                'task_complexity': 'complex',
                'subtasks': subtasks,
                'suggested_actions': ['approve_plan', 'modify_plan', 'start_immediately'],
            }
        # moderate
        return {
            'text': f"I understand your request, {user_name}. This appears moderate; processing now.",
            'requires_followup': False,
            'task_complexity': 'moderate',
            'estimated_time': complexity.get('estimated_time', '15 minutes'),
        }

    async def handle_information_query(self, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        query_type = await self._categorize_information_query(user_input)
        user_name = context.user_name or "there"
        template = random.choice(self.response_templates['information_delivery'])
        if query_type == 'factual':
            text = f"{template.format(user_name=user_name)} I'll gather accurate, up-to-date details."
        elif query_type == 'personal':
            text = f"{template.format(user_name=user_name)} I'll tailor the answer to your situation."
        elif query_type == 'technical':
            depth = "detailed technical" if self.personality['technical_depth'] > 0.7 else "clear, practical"
            text = f"{template.format(user_name=user_name)} I'll provide a {depth} explanation."
        else:
            text = f"{template.format(user_name=user_name)} Analyzing your question for the best response."
        return {
            'text': text,
            'requires_followup': query_type in {'instructional', 'technical'},
            'query_type': query_type,
            'suggested_actions': ['provide_sources', 'explain_further', 'related_topics'],
        }

    async def handle_problem_solving(self, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        analysis = await self._analyze_problem_complexity(user_input)
        user_name = context.user_name or "there"
        if analysis['urgency'] == 'high':
            text = (f"I understand this is urgent, {user_name}. Focusing immediately. "
                    f"Can you provide any error messages or recent changes?")
            return {
                'text': text,
                'requires_followup': True,
                'urgency': 'high',
                'suggested_actions': ['gather_diagnostics', 'immediate_fix', 'escalate'],
            }
        text = (f"I'll help you troubleshoot systematically, {user_name}. "
                f"I'll analyze the problem and guide you through a step-by-step solution.")
        return {
            'text': text,
            'requires_followup': True,
            'urgency': analysis['urgency'],
            'suggested_actions': ['diagnostic_questions', 'step_by_step_guide', 'documentation'],
        }

    async def handle_personal_question(self, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        user_name = context.user_name or "there"
        lower = user_input.lower()
        if 'capabilities' in lower or 'what can you do' in lower:
            text = (
                f"I'm BUDDY, your intelligent AI assistant, {user_name}. I can help with:\n\n"
                "🧠 Intelligent Conversations: I understand context and adapt to you\n"
                "📱 Cross-Platform Sync: Seamless across your devices\n"
                "✅ Task Management: Breakdown, scheduling, proactive suggestions\n"
                "🔍 Information Assistance: Research & explanations\n"
                "🛠 Problem Solving: Structured troubleshooting\n"
                "💬 Emotional Support: Attentive and empathetic responses\n\n"
                "What would you like to explore together?"
            )
        elif 'who are you' in lower:
            text = (f"I'm BUDDY, your personal AI assistant, {user_name}. I learn, remember, "
                    "and adapt to your style to be genuinely helpful.")
        else:
            text = (f"I'm BUDDY, designed to be helpful, intelligent, and adaptive, {user_name}. "
                    "Is there something specific you'd like to know?")
        return {
            'text': text,
            'requires_followup': False,
            'category': 'self_description',
            'suggested_actions': ['explore_features', 'customize_settings', 'start_task'],
        }

    async def handle_emotional_support(self, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        emotion = await self._detect_emotion(user_input)
        user_name = context.user_name or "there"
        if emotion['type'] == 'negative':
            text = (f"I can sense you're feeling {emotion['specific']}, {user_name}. That's understandable, and I'm here. "
                    "Would you like to talk about it or focus on something uplifting?")
        elif emotion['type'] == 'positive':
            text = (f"Great to hear you're feeling {emotion['specific']}, {user_name}! "
                    "How can I help you make the most of this energy?")
        else:
            text = (f"I'm here to listen and support you, {user_name}. What's on your mind?")
        return {
            'text': text,
            'requires_followup': True,
            'emotion_detected': emotion,
            'suggested_actions': ['active_listening', 'mood_boosting_suggestions', 'practical_help'],
        }

    async def handle_compliment(self, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        user_name = context.user_name or "there"
        responses = [
            f"Thank you so much, {user_name}!", 
            f"I appreciate your kind words, {user_name}.",
            f"Glad I'm helping effectively, {user_name}.",
        ]
        text = random.choice(responses)
        if self.personality['humor_frequency'] > 0.5 and random.random() < 0.3:
            text += " I'd blush if I could!"
        return {
            'text': text,
            'requires_followup': False,
            'emotion_detected': 'positive_feedback',
            'suggested_actions': ['continue_conversation', 'new_task', 'explore_features'],
        }

    async def handle_complaint(self, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        user_name = context.user_name or "there"
        text = (f"I'm sorry if I haven't met expectations, {user_name}. "
                "Could you share what went wrong so I can improve?")
        return {
            'text': text,
            'requires_followup': True,
            'emotion_detected': 'negative_feedback',
            'suggested_actions': ['gather_feedback', 'immediate_improvement', 'alternative_approach'],
        }

    async def handle_general_interaction(self, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        user_name = context.user_name or "there"
        if len(user_input.split()) == 1:
            text = (f"I hear '{user_input}', {user_name}. Could you tell me a bit more so I can help accurately?")
        else:
            snippet = user_input[:50]
            text = (f"I see you're asking about '{snippet}...', {user_name}. "
                    "Could you add a little more context?")
        return {
            'text': text,
            'requires_followup': True,
            'category': 'general',
            'suggested_actions': ['clarify_intent', 'provide_examples', 'explore_options'],
        }

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    async def analyze_enhanced_task_complexity(self, task_text: str) -> Dict[str, Any]:
        words = task_text.split()
        word_count = len(words)
        complexity_indicators = {
            'time_references': len(re.findall(r'\b(today|tomorrow|next\s+week|schedule|deadline)\b', task_text.lower())),
            'multiple_steps': len(re.findall(r'\b(then|next|after|before|first|second|finally)\b', task_text.lower())),
            'dependencies': len(re.findall(r'\b(if|when|after|before|depends|requires)\b', task_text.lower())),
            'tools_needed': len(re.findall(r'\b(with|using|through|via)\b', task_text.lower())),
        }
        complexity_score = (
            word_count * 0.1 +
            complexity_indicators['time_references'] * 2 +
            complexity_indicators['multiple_steps'] * 3 +
            complexity_indicators['dependencies'] * 4 +
            complexity_indicators['tools_needed'] * 1.5
        )
        if complexity_score < 5:
            return {'complexity': 'simple', 'estimated_time': '2-5 minutes', 'confidence': 0.8}
        if complexity_score < 15:
            return {'complexity': 'moderate', 'estimated_time': '10-30 minutes', 'confidence': 0.7}
        return {'complexity': 'complex', 'estimated_time': '~45-90 minutes', 'confidence': 0.9}

    async def break_down_complex_task(self, task_text: str) -> List[Dict[str, Any]]:
        sentences = [s.strip() for s in re.split(r'[.!?]+', task_text) if s.strip()]
        if len(sentences) <= 1:
            parts = re.split(r'\b(and|then|next|after|before)\b', task_text)
            sentences = [p.strip() for p in parts if p.strip() and p.lower() not in ['and', 'then', 'next', 'after', 'before']]
        subtasks: List[Dict[str, Any]] = []
        for i, sentence in enumerate(sentences[:5]):
            subtasks.append({
                'id': i + 1,
                'description': sentence,
                'estimated_time': '5-15 minutes',
                'dependencies': [],
                'priority': 'normal',
            })
        return subtasks

    async def present_enhanced_task_breakdown(self, subtasks: List[Dict[str, Any]], context: ConversationContext) -> str:
        user_name = context.user_name or 'Sir'
        lines = [f"I've analyzed your request, {user_name}. Here's my recommended approach:", ""]
        for subtask in subtasks:
            lines.append(f"Step {subtask['id']}: {subtask['description']}")
            lines.append(f"   ⏱️ Estimated time: {subtask['estimated_time']}")
            if subtask.get('dependencies'):
                lines.append(f"   🔗 Dependencies: {', '.join(subtask['dependencies'])}")
            lines.append("")
        lines.append("Would you like me to:\n• Start with Step 1 immediately\n• Modify the plan\n• Break it down further")
        return "\n".join(lines)

    async def _record_interaction(self, user_input: str, context: ConversationContext) -> None:
        interaction = {
            'timestamp': datetime.now(timezone.utc),
            'user_input': user_input,
            'context': asdict(context),
            'session_id': context.session_id,
        }
        self.interaction_history.append(interaction)
        uid = context.user_id
        self.conversation_memory.setdefault(uid, []).append(interaction)
        if len(self.conversation_memory[uid]) > 100:
            self.conversation_memory[uid] = self.conversation_memory[uid][-100:]

    async def _update_user_preferences(self, user_input: str, response: Dict[str, Any], context: ConversationContext) -> None:
        uid = context.user_id
        if uid not in self.user_preferences:
            self.user_preferences[uid] = {
                'communication_style': 'balanced',
                'detail_preference': 0.5,
                'humor_appreciation': 0.5,
                'formality_preference': 0.5,
                'interaction_count': 0,
            }
        prefs = self.user_preferences[uid]
        prefs['interaction_count'] += 1
        wc = len(user_input.split())
        if wc > 20:
            prefs['detail_preference'] = min(prefs['detail_preference'] + 0.1, 1.0)
        elif wc < 5:
            prefs['detail_preference'] = max(prefs['detail_preference'] - 0.05, 0.0)

    def _get_time_of_day(self) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return 'morning'
        if 12 <= hour < 17:
            return 'afternoon'
        if 17 <= hour < 21:
            return 'evening'
        return 'night'

    async def _generate_proactive_suggestions(self, context: ConversationContext) -> List[str]:
        suggestions: List[str] = []
        hour = datetime.now().hour
        if 8 <= hour <= 10:
            suggestions.extend(["review your schedule", "set daily goals", "check important emails"])
        elif 12 <= hour <= 14:
            suggestions.extend(["take a break", "review morning progress", "plan afternoon tasks"])
        elif 17 <= hour <= 19:
            suggestions.extend(["wrap up today's work", "plan tomorrow", "review achievements"])
        if context.device_type == 'mobile':
            suggestions.extend(["quick voice note", "location-based reminder"])
        elif context.device_type == 'desktop':
            suggestions.extend(["organize files", "backup important data"])
        return suggestions[:3]

    async def _categorize_information_query(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ['how to', 'tutorial', 'guide', 'steps']):
            return 'instructional'
        if any(w in q for w in ['what is', 'define', 'meaning', 'explanation']):
            return 'definitional'
        if any(w in q for w in ['when', 'time', 'date', 'schedule']):
            return 'temporal'
        if any(w in q for w in ['where', 'location', 'place']):
            return 'spatial'
        if any(w in q for w in ['technical', 'code', 'programming', 'algorithm']):
            return 'technical'
        if any(w in q for w in ['personal', ' my ', ' me ', ' i ']):
            return 'personal'
        return 'factual'

    async def _analyze_problem_complexity(self, problem_text: str) -> Dict[str, Any]:
        p = problem_text.lower()
        indicators = {
            'urgent': len(re.findall(r'\b(urgent|asap|immediately|critical|emergency)\b', p)),
            'broken': len(re.findall(r'\b(broken|down|crashed|failed|not working)\b', p)),
            'error': len(re.findall(r'\b(error|bug|issue|problem)\b', p)),
        }
        urgency_score = indicators['urgent'] * 3 + indicators['broken'] * 2 + indicators['error']
        if urgency_score >= 3:
            urgency = 'high'
        elif urgency_score >= 1:
            urgency = 'medium'
        else:
            urgency = 'low'
        return {'urgency': urgency, 'complexity': 'moderate', 'indicators': indicators}

    async def _detect_emotion(self, text: str) -> Dict[str, Any]:
        t = text.lower()
        positive = {
            'happy': ['happy', 'joy', 'glad', 'cheerful', 'delighted'],
            'excited': ['excited', 'thrilled', 'enthusiastic', 'eager'],
            'grateful': ['thank', 'grateful', 'appreciate', 'thankful'],
        }
        negative = {
            'sad': ['sad', 'depressed', 'down', 'unhappy', 'melancholy'],
            'angry': ['angry', 'mad', 'furious', 'irritated', 'frustrated'],
            'worried': ['worried', 'anxious', 'concerned', 'stressed', 'nervous'],
        }
        for emo, keys in positive.items():
            if any(k in t for k in keys):
                return {'type': 'positive', 'specific': emo, 'confidence': 0.8}
        for emo, keys in negative.items():
            if any(k in t for k in keys):
                return {'type': 'negative', 'specific': emo, 'confidence': 0.8}
        return {'type': 'neutral', 'specific': 'calm', 'confidence': 0.6}

    async def _handle_conversation_error(self, error: Exception, user_input: str, context: ConversationContext) -> Dict[str, Any]:
        user_name = context.user_name or 'there'
        error_response = (f"I encountered a hiccup processing that, {user_name}. "
                          "Could you rephrase or clarify what you need?")
        return {
            'response': error_response,
            'metadata': {
                'confidence': 0.3,
                'intent_type': 'error_recovery',
                'requires_followup': True,
                'suggested_actions': ['rephrase_request', 'try_different_approach', 'contact_support'],
                'processing_time_ms': 0,
            },
            'error': True,
            'recovery_attempted': True,
        }

    def get_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self.conversation_memory:
            return {'interaction_count': 0, 'topics_discussed': [], 'average_response_time': 0}
        conversations = self.conversation_memory[user_id]
        # Extract previous topics from stored contexts if present
        topics = []
        for item in conversations:
            ctx = item.get('context', {})
            prev = ctx.get('previous_topics') or []
            topics.extend(prev)
        return {
            'interaction_count': len(conversations),
            'topics_discussed': list(sorted(set(topics)))[:10],
            'last_interaction': conversations[-1]['timestamp'] if conversations else None,
            'preferred_style': self.user_preferences.get(user_id, {}).get('communication_style', 'balanced'),
        }

# Convenience alias for external code wanting the enhanced version by default
EnhancedConversationManager = BUDDYEnhancedConversationManager

