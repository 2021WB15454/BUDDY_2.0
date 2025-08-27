from __future__ import annotations
"""BUDDY Intelligence Engine (Phase D: Contextual + Personality filter skeleton)."""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from buddy_core.personality.buddy_personality import personality_singleton
import datetime

@dataclass
class IntentAnalysis:
    intent: str
    sentiment: str = "neutral"
    urgency: float = 0.0

class BUDDYKnowledgeBase:
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:  # placeholder
        return []

class BUDDYIntelligenceEngine:
    def __init__(self, user_profile: Optional[Dict[str, Any]] = None, conversation_memory: Optional[List[Dict[str, Any]]] = None):
        self.user_profile = user_profile or {}
        self.memory = conversation_memory or []
        self.knowledge_base = BUDDYKnowledgeBase()

    async def generate_buddy_response(self, user_input: str, context: Dict[str, Any]) -> str:
        intent_analysis = await self.analyze_user_intent(user_input, context)
        relevant_context = await self.gather_contextual_intelligence(user_input, context)
        base_response = await self.generate_intelligent_response(user_input, intent_analysis, relevant_context)
        buddy_response = await self.apply_buddy_personality(base_response, intent_analysis, context)
        enhanced_response = await self.add_proactive_intelligence(buddy_response, context)
        return enhanced_response

    async def analyze_user_intent(self, user_input: str, context: Dict[str, Any]) -> IntentAnalysis:
        # Extremely naive heuristic placeholder
        lowered = user_input.lower()
        if any(k in lowered for k in ["weather", "temperature"]):
            intent = "weather_query"
        elif any(k in lowered for k in ["remind", "schedule", "set a reminder"]):
            intent = "task_request"
        elif lowered.endswith("?"):
            intent = "information_query"
        else:
            intent = "general"
        urgency = 0.7 if any(k in lowered for k in ["urgent", "asap", "now"]) else 0.0
        return IntentAnalysis(intent=intent, urgency=urgency)

    async def gather_contextual_intelligence(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder: later integrate memory_service.retrieve
        return {
            "recent_messages": self.memory[-5:],
            "profile": self.user_profile,
            "time_of_day": self._time_of_day(),
        }

    async def generate_intelligent_response(self, user_input: str, intent: IntentAnalysis, ctx: Dict[str, Any]) -> str:
        if intent.intent == "weather_query":
            return "Current atmospheric conditions are moderate; more details available upon request."
        if intent.intent == "task_request":
            return "Acknowledged. I can help structure or schedule this task if you provide specifics."
        if intent.intent == "information_query":
            return "Here's an informed perspective based on available data." \
                   " Feel free to clarify parameters for deeper precision."
        return "Understood. I'm ready to proceed or refine based on your direction."

    async def apply_buddy_personality(self, response: str, intent: IntentAnalysis, context: Dict[str, Any]) -> str:
        addr = personality_singleton.format_address(
            user_name=context.get('user_name'),
            relationship_familiarity=context.get('relationship_familiarity', 'formal'),
            user_gender=context.get('user_gender'),
            is_urgent=intent.urgency > 0.5
        )
        return f"{addr}, {response}" if addr else response

    async def add_proactive_intelligence(self, response: str, context: Dict[str, Any]) -> str:
        additions: List[str] = []
        if context.get('upcoming_meeting'):
            additions.append("You have an upcoming meeting; I can prepare a briefing packet if desired.")
        if context.get('recurring_task_detected'):
            additions.append("I can automate portions of this recurring workflow.")
        if not additions:
            return response
        return response + "\n\n" + " ".join(additions)

    def _time_of_day(self) -> str:
        hour = datetime.datetime.utcnow().hour
        if hour < 12:
            return "morning"
        if hour < 18:
            return "afternoon"
        return "evening"
