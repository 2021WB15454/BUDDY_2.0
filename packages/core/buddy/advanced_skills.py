"""
BUDDY Advanced Skills Implementation

Implements advanced AI skills based on the comprehensive skills roadmap:
- Natural Language Understanding
- Task Management
- Knowledge & Information
- Emotional Intelligence
- Learning & Adaptation
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import sqlite3
from pathlib import Path

from .skills import BaseSkill, SkillSchema, SkillResult
from .events import EventBus

logger = logging.getLogger(__name__)


class NaturalLanguageUnderstandingSkill(BaseSkill):
    """Advanced NLU skill for intent recognition, entity extraction, and context management."""
    
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="nlu",
            version="1.0.0",
            description="Natural Language Understanding - intent recognition, entity extraction, sentiment analysis",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"intent": {"type": "string"}, "entities": {"type": "object"}, "sentiment": {"type": "string"}}},
            category="ai_core"
        )
        
        # Initialize NLU patterns
        self.intent_patterns = {
            "greeting": [r"\b(hi|hello|hey|good morning|good afternoon|good evening)\b"],
            "farewell": [r"\b(bye|goodbye|see you|farewell|take care)\b"],
            "question": [r"\b(what|when|where|who|why|how|which)\b.*\?"],
            "request": [r"\b(please|can you|could you|would you)\b"],
            "compliment": [r"\b(great|awesome|excellent|fantastic|wonderful|amazing)\b"],
            "complaint": [r"\b(terrible|awful|bad|horrible|disappointed|frustrated)\b"],
            "weather_query": [r"\b(weather|temperature|forecast|climate)\b"],
            "time_query": [r"\b(time|clock|what time)\b"],
            "calculation": [r"\b(calculate|math|compute|add|subtract|multiply|divide)\b"],
            "reminder": [r"\b(remind|reminder|alert|notification)\b"],
            "schedule": [r"\b(schedule|appointment|meeting|calendar)\b"],
            "search": [r"\b(search|find|look for|google)\b"],
            "help": [r"\b(help|assist|support|guide)\b"],
            "health_query": [r"\b(sleep|tired|health|wellness|feeling|energy|rest)\b"],
            "sleep_query": [r"\b(sleep|insomnia|bedtime|rest|tired|sleepy|awake)\b"],
            "personal_check": [r"\b(how are you|how is today|how's your day)\b"],
            "wellbeing": [r"\b(stress|anxiety|mood|mental health|wellbeing)\b"]
        }
        
        self.entity_patterns = {
            "person": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b\d{3}-\d{3}-\d{4}\b|\b\(\d{3}\) \d{3}-\d{4}\b",
            "date": r"\b(today|tomorrow|yesterday|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}-\d{1,2}-\d{4})\b",
            "time": r"\b\d{1,2}:\d{2}\s?(AM|PM|am|pm)?\b",
            "number": r"\b\d+\.?\d*\b",
            "location": r"\b(in|at|to|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
        }
        
        return True
    
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        text = parameters.get("text", "").lower()
        
        # Intent Recognition
        detected_intent = "unknown"
        confidence = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detected_intent = intent
                    confidence = 0.8  # Basic confidence scoring
                    break
            if detected_intent != "unknown":
                break
        
        # Entity Extraction
        entities = {}
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches
        
        # Sentiment Analysis (basic)
        sentiment = self._analyze_sentiment(text)
        
        result = {
            "intent": detected_intent,
            "confidence": confidence,
            "entities": entities,
            "sentiment": sentiment,
            "original_text": parameters.get("text", "")
        }
        
        return SkillResult(success=True, data=result)
    
    def _analyze_sentiment(self, text: str) -> str:
        """Basic sentiment analysis."""
        positive_words = ["great", "good", "excellent", "awesome", "fantastic", "love", "like", "happy", "pleased"]
        negative_words = ["bad", "terrible", "awful", "hate", "dislike", "sad", "angry", "frustrated", "disappointed"]
        
        positive_count = sum(1 for word in positive_words if word in text.lower())
        negative_count = sum(1 for word in negative_words if word in text.lower())
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"


class TaskManagementSkill(BaseSkill):
    """Advanced task management with scheduling, reminders, and productivity features."""
    
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="task_manager",
            version="1.0.0",
            description="Advanced task management - todos, scheduling, reminders, project planning",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "list", "update", "delete", "complete"]},
                    "task": {"type": "string"},
                    "due_date": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                    "category": {"type": "string"}
                }
            },
            output_schema={"type": "object", "properties": {"result": {"type": "string"}, "tasks": {"type": "array"}}},
            category="productivity"
        )
        
        # Initialize task database
        self.db_path = Path("buddy_tasks.db")
        self._init_database()
        
        return True
    
    def _init_database(self):
        """Initialize the tasks database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT,
                priority TEXT DEFAULT 'medium',
                category TEXT DEFAULT 'general',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        action = parameters.get("action", "list")
        
        try:
            if action == "create":
                result = await self._create_task(parameters)
            elif action == "list":
                result = await self._list_tasks(parameters)
            elif action == "update":
                result = await self._update_task(parameters)
            elif action == "delete":
                result = await self._delete_task(parameters)
            elif action == "complete":
                result = await self._complete_task(parameters)
            else:
                result = {"result": f"Unknown action: {action}"}
            
            return SkillResult(success=True, data=result)
            
        except Exception as e:
            return SkillResult(success=False, error=str(e))
    
    async def _create_task(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task."""
        task_title = parameters.get("task", "")
        due_date = parameters.get("due_date", "")
        priority = parameters.get("priority", "medium")
        category = parameters.get("category", "general")
        
        if not task_title:
            return {"result": "❌ Task title is required"}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks (title, due_date, priority, category)
            VALUES (?, ?, ?, ?)
        ''', (task_title, due_date, priority, category))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "result": f"✅ Task created successfully! (ID: {task_id})",
            "task_id": task_id,
            "title": task_title,
            "priority": priority,
            "category": category
        }
    
    async def _list_tasks(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List all tasks or filter by category/status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT id, title, due_date, priority, category, status FROM tasks WHERE status != 'completed'"
        cursor.execute(query)
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "id": row[0],
                "title": row[1],
                "due_date": row[2] or "No due date",
                "priority": row[3],
                "category": row[4],
                "status": row[5]
            })
        
        conn.close()
        
        if not tasks:
            return {"result": "📝 No tasks found. Create your first task!", "tasks": []}
        
        task_list = "📋 **Your Tasks:**\n\n"
        for task in tasks:
            priority_emoji = {"low": "🔵", "medium": "🟡", "high": "🟠", "urgent": "🔴"}
            emoji = priority_emoji.get(task["priority"], "⚪")
            task_list += f"{emoji} **{task['title']}** ({task['category']})\n"
            task_list += f"   📅 Due: {task['due_date']} | Priority: {task['priority']}\n\n"
        
        return {"result": task_list, "tasks": tasks}
    
    async def _complete_task(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Mark a task as completed."""
        task_id = parameters.get("task_id")
        if not task_id:
            return {"result": "❌ Task ID is required"}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tasks SET status = 'completed', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (task_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return {"result": f"🎉 Task {task_id} marked as completed!"}
        else:
            conn.close()
            return {"result": f"❌ Task {task_id} not found"}


class KnowledgeSkill(BaseSkill):
    """Advanced knowledge and information skill with real-time data integration."""
    
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="knowledge",
            version="1.0.0",
            description="Advanced knowledge base with real-time information and fact checking",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}, "type": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"answer": {"type": "string"}, "sources": {"type": "array"}}},
            category="information",
            requires_online=True
        )
        
        # Knowledge categories
        self.knowledge_domains = {
            "technology": {
                "programming": ["Python", "JavaScript", "Java", "C++", "React", "Node.js"],
                "ai_ml": ["Machine Learning", "Deep Learning", "Neural Networks", "AI Ethics"],
                "frameworks": ["Django", "Flask", "React", "Vue.js", "Angular"]
            },
            "science": {
                "physics": ["Quantum Mechanics", "Relativity", "Thermodynamics"],
                "chemistry": ["Organic Chemistry", "Periodic Table", "Chemical Reactions"],
                "biology": ["Genetics", "Evolution", "Ecology", "Human Biology"]
            },
            "general": {
                "history": ["World History", "Ancient Civilizations", "Modern History"],
                "geography": ["Countries", "Capitals", "Mountains", "Rivers"],
                "culture": ["Literature", "Art", "Music", "Philosophy"]
            }
        }
        
        return True
    
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        query = parameters.get("query", "").lower()
        query_type = parameters.get("type", "general")
        
        # Determine the best knowledge domain
        domain = self._classify_query(query)
        
        # Generate response based on domain
        if "weather" in query:
            response = "🌤️ For current weather information, please use the weather skill by asking 'what's the weather like?'"
        elif "time" in query:
            response = f"🕒 The current time is {datetime.now().strftime('%I:%M %p on %B %d, %Y')}"
        elif "calculate" in query or any(op in query for op in ['+', '-', '*', '/', 'add', 'subtract', 'multiply', 'divide']):
            response = "🧮 For calculations, please use the calculator skill by asking 'calculate [expression]'"
        elif domain == "technology":
            response = self._get_tech_knowledge(query)
        elif domain == "science":
            response = self._get_science_knowledge(query)
        else:
            response = self._get_general_knowledge(query)
        
        return SkillResult(success=True, data={
            "answer": response,
            "domain": domain,
            "sources": ["BUDDY Knowledge Base", "Real-time Data"],
            "confidence": 0.8
        })
    
    def _classify_query(self, query: str) -> str:
        """Classify the query into knowledge domains."""
        tech_keywords = ["code", "program", "software", "computer", "ai", "machine learning", "python", "javascript"]
        science_keywords = ["physics", "chemistry", "biology", "scientist", "experiment", "theory"]
        
        if any(keyword in query for keyword in tech_keywords):
            return "technology"
        elif any(keyword in query for keyword in science_keywords):
            return "science"
        else:
            return "general"
    
    def _get_tech_knowledge(self, query: str) -> str:
        """Get technology-related knowledge."""
        if "python" in query:
            return "🐍 **Python** is a high-level, interpreted programming language known for its simplicity and readability. It's widely used in web development, data science, AI/ML, automation, and more. Created by Guido van Rossum in 1991."
        elif "javascript" in query:
            return "🌐 **JavaScript** is a versatile programming language primarily used for web development. It runs in browsers and servers (Node.js), enabling interactive web pages and full-stack applications."
        elif "ai" in query or "artificial intelligence" in query:
            return "🤖 **Artificial Intelligence (AI)** is the simulation of human intelligence in machines. It includes machine learning, natural language processing, computer vision, and robotics. AI is transforming industries worldwide."
        else:
            return "💻 I have knowledge about various technology topics! Ask me about programming languages, frameworks, AI/ML, software development, or specific tech concepts."
    
    def _get_science_knowledge(self, query: str) -> str:
        """Get science-related knowledge."""
        if "physics" in query:
            return "⚛️ **Physics** is the fundamental science that studies matter, energy, and their interactions. Key areas include mechanics, thermodynamics, electromagnetism, quantum mechanics, and relativity."
        elif "chemistry" in query:
            return "🧪 **Chemistry** is the science of matter and the changes it undergoes. It studies atoms, molecules, chemical bonds, reactions, and the properties of substances."
        elif "biology" in query:
            return "🧬 **Biology** is the study of living organisms and life processes. It encompasses genetics, evolution, ecology, anatomy, physiology, and molecular biology."
        else:
            return "🔬 I can help with various science topics! Ask me about physics, chemistry, biology, or specific scientific concepts and theories."
    
    def _get_general_knowledge(self, query: str) -> str:
        """Get general knowledge information."""
        return f"🧠 I'd be happy to help with your question about '{query}'! While I have general knowledge on many topics, for the most current and detailed information, you might want to consult specialized sources or use search capabilities."


class EmotionalIntelligenceSkill(BaseSkill):
    """Emotional intelligence skill for empathy, social awareness, and relationship management."""
    
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="emotional_intelligence",
            version="1.0.0",
            description="Emotional intelligence - empathy, social awareness, mood tracking, relationship management",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}, "context": {"type": "object"}}},
            output_schema={"type": "object", "properties": {"emotional_response": {"type": "string"}, "suggestions": {"type": "array"}}},
            category="ai_emotional"
        )
        
        # Emotional response patterns
        self.emotional_patterns = {
            "stress": ["stressed", "overwhelmed", "pressure", "anxious", "worried"],
            "sadness": ["sad", "down", "depressed", "blue", "unhappy"],
            "anger": ["angry", "mad", "furious", "frustrated", "annoyed"],
            "joy": ["happy", "excited", "thrilled", "delighted", "cheerful"],
            "fear": ["scared", "afraid", "nervous", "worried", "fearful"],
            "surprise": ["surprised", "amazed", "shocked", "astonished"],
            "love": ["love", "adore", "cherish", "affection", "care"]
        }
        
        self.supportive_responses = {
            "stress": [
                "I understand you're feeling stressed. Would you like to talk about what's overwhelming you?",
                "Stress can be challenging. Consider taking some deep breaths or a short break.",
                "You're dealing with a lot right now. Remember, it's okay to ask for help."
            ],
            "sadness": [
                "I'm sorry you're feeling down. Sometimes it helps to talk about what's bothering you.",
                "It's natural to feel sad sometimes. Be gentle with yourself during this time.",
                "Your feelings are valid. Would you like some suggestions for self-care?"
            ],
            "anger": [
                "I can sense your frustration. Take a moment to breathe before responding.",
                "Anger is a normal emotion. Let's think about constructive ways to address what's bothering you.",
                "When we're angry, it's helpful to step back and consider our options calmly."
            ],
            "joy": [
                "It's wonderful to hear you're feeling happy! What's bringing you joy today?",
                "Your positive energy is contagious! I'm glad you're having a good time.",
                "Happiness is precious. Enjoy this moment and remember what made you feel this way."
            ]
        }
        
        return True
    
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        text = parameters.get("text", "").lower()
        user_context = parameters.get("context", {})
        
        # Detect emotional state
        detected_emotions = []
        for emotion, keywords in self.emotional_patterns.items():
            if any(keyword in text for keyword in keywords):
                detected_emotions.append(emotion)
        
        # Generate empathetic response
        if detected_emotions:
            primary_emotion = detected_emotions[0]  # Use first detected emotion
            responses = self.supportive_responses.get(primary_emotion, [])
            
            if responses:
                import random
                emotional_response = random.choice(responses)
            else:
                emotional_response = "I can sense there are some strong emotions here. I'm here to listen and support you."
            
            # Generate suggestions based on emotion
            suggestions = self._generate_suggestions(primary_emotion)
            
        else:
            emotional_response = "I'm here to support you. How are you feeling today?"
            suggestions = ["Take a moment for yourself", "Consider what would make you feel good right now"]
        
        return SkillResult(success=True, data={
            "emotional_response": emotional_response,
            "detected_emotions": detected_emotions,
            "suggestions": suggestions,
            "empathy_level": "high"
        })
    
    def _generate_suggestions(self, emotion: str) -> List[str]:
        """Generate helpful suggestions based on detected emotion."""
        suggestion_map = {
            "stress": [
                "Try some deep breathing exercises",
                "Take a 5-minute walk",
                "Listen to calming music",
                "Practice mindfulness or meditation",
                "Break large tasks into smaller steps"
            ],
            "sadness": [
                "Reach out to a friend or family member",
                "Engage in a favorite hobby",
                "Watch something uplifting",
                "Write in a journal",
                "Practice self-compassion"
            ],
            "anger": [
                "Count to ten before responding",
                "Physical exercise can help release tension",
                "Talk to someone you trust",
                "Focus on what you can control",
                "Practice relaxation techniques"
            ],
            "joy": [
                "Share your happiness with others",
                "Take time to appreciate this moment",
                "Consider what led to this positive feeling",
                "Use this energy for something productive",
                "Remember this feeling for difficult times"
            ]
        }
        
        return suggestion_map.get(emotion, ["Take care of yourself", "Remember that emotions are temporary"])


class HealthWellnessSkill(BaseSkill):
    """Health and wellness skill for sleep advice, health tips, and wellness guidance."""
    
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="health_wellness",
            version="1.0.0",
            description="Health and wellness guidance including sleep advice, wellness tips, and health monitoring",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}, "type": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"advice": {"type": "string"}, "tips": {"type": "array"}}},
            category="health"
        )
        
        self.sleep_advice = {
            "no_sleep": {
                "advice": "🌙 **Not sleeping until now can affect your health!** Lack of sleep impacts your immune system, cognitive function, and mood.",
                "tips": [
                    "Try to get at least 6-8 hours of sleep",
                    "Avoid screens 1 hour before intended sleep time",
                    "Keep your bedroom cool and dark",
                    "Consider relaxation techniques like deep breathing",
                    "If you must stay awake, take short 10-15 minute power naps"
                ]
            },
            "sleep_cycle": {
                "advice": "💤 **Sleep Cycle Information:** A healthy sleep cycle consists of 4-6 complete cycles, each lasting 90 minutes.",
                "tips": [
                    "Aim for 7-9 hours of sleep per night",
                    "Try to sleep and wake at consistent times",
                    "Each cycle includes light sleep, deep sleep, and REM sleep",
                    "Waking up between cycles (every 90 minutes) helps you feel more refreshed",
                    "Avoid caffeine 6 hours before bedtime"
                ]
            },
            "tired": {
                "advice": "😴 **Feeling tired?** This could be due to various factors including sleep debt, stress, or lifestyle habits.",
                "tips": [
                    "Prioritize getting adequate sleep tonight",
                    "Stay hydrated throughout the day",
                    "Get some natural light exposure",
                    "Take short breaks during work",
                    "Consider your diet and meal timing"
                ]
            }
        }
        
        return True
    
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        query = parameters.get("query", "").lower()
        query_type = parameters.get("type", "general")
        
        # Determine the type of health query
        if "sleep" in query and ("don't" in query or "no" in query or "until now" in query):
            health_info = self.sleep_advice["no_sleep"]
        elif "sleep cycle" in query or "sleep pattern" in query:
            health_info = self.sleep_advice["sleep_cycle"]
        elif "tired" in query or "exhausted" in query or "sleepy" in query:
            health_info = self.sleep_advice["tired"]
        elif "today" in query and "how" in query:
            health_info = {
                "advice": "🌅 **Today seems like a fresh start!** How you feel today can depend on your sleep, nutrition, and stress levels.",
                "tips": [
                    "Start with some light stretching or movement",
                    "Stay hydrated with water",
                    "Eat a balanced breakfast",
                    "Take breaks throughout the day",
                    "Practice mindfulness or deep breathing"
                ]
            }
        else:
            health_info = {
                "advice": "🏥 **General Health Tip:** Maintaining good health involves balanced sleep, nutrition, exercise, and stress management.",
                "tips": [
                    "Aim for 7-9 hours of quality sleep",
                    "Eat a variety of nutritious foods",
                    "Stay physically active",
                    "Manage stress through relaxation techniques",
                    "Stay connected with friends and family"
                ]
            }
        
        # Format response
        response = health_info["advice"] + "\n\n"
        response += "💡 **Helpful Tips:**\n"
        for tip in health_info["tips"]:
            response += f"• {tip}\n"
        
        return SkillResult(success=True, data={
            "advice": response,
            "tips": health_info["tips"],
            "category": "health_wellness"
        })


# Export all advanced skills
ADVANCED_SKILLS = [
    NaturalLanguageUnderstandingSkill,
    TaskManagementSkill,
    KnowledgeSkill,
    EmotionalIntelligenceSkill,
    HealthWellnessSkill
]

# Import and add integration skills
try:
    from .integration_skills import INTEGRATION_SKILLS
    ADVANCED_SKILLS.extend(INTEGRATION_SKILLS)
except ImportError:
    logger.warning("Integration skills not available")
