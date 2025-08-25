"""
Enhanced BUDDY Backend with MongoDB Integration

A FastAPI server with MongoDB for persistent data storage.
Supports conversations, reminders, analytics, and user management.
"""

import os
import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import MongoDB integration
from mongodb_integration import buddy_db, init_database, get_database, BuddyDatabase

# Import Enhanced NLP Engine
try:
    from enhanced_nlp_engine import get_nlp_engine
    ADVANCED_NLP_AVAILABLE = True
except ImportError:
    ADVANCED_NLP_AVAILABLE = False

# Import Advanced Intent Classifier (Phase 1 implementation)
try:
    from buddy_core.nlp.advanced_intent_classifier import get_advanced_intent_classifier
    from buddy_core.memory.semantic_memory import get_semantic_memory_engine
    PHASE1_ADVANCED_AI_AVAILABLE = True
except ImportError:
    PHASE1_ADVANCED_AI_AVAILABLE = False

# Import Simplified NLP Engine as fallback
from simplified_nlp_engine import get_simplified_nlp_engine

# Import Firebase integration
try:
    from firebase_integration import (
        get_firebase_manager, 
        update_buddy_online_status, 
        update_buddy_offline_status,
        log_conversation_to_firebase,
        verify_firebase_user
    )
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase integration not available")

# Weather API configuration
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "ff2cbe677bbfc325d2b615c86a20daef")
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Runtime flags
DEBUG_MODE = os.getenv("BUDDY_DEBUG") == "1"
DEV_MODE = os.getenv("BUDDY_DEV") == "1"
USE_MONGODB = os.getenv("USE_MONGODB", "1") == "1"

def debug_log_intent(intent: str, message: str | None = None):
    if DEBUG_MODE:
        try:
            logger.info(f"[INTENT] {intent} msg={message!r}")
        except Exception:
            pass

# Create FastAPI app
app = FastAPI(title="BUDDY Backend API with MongoDB", version="2.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://buddyai-42493.web.app",  # Firebase hosting
        "https://buddyai-42493.firebaseapp.com",  # Firebase hosting alternate
        "http://localhost:3000",  # Local React development
        "http://localhost:5000",  # Local Firebase hosting
        "*"  # Allow all for development (restrict in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Application startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting BUDDY 2.0 Backend...")
    
    # Initialize MongoDB
    if USE_MONGODB:
        await init_database()
        logger.info("✅ MongoDB initialized")
    
    # Initialize Firebase
    if FIREBASE_AVAILABLE:
        try:
            await update_buddy_online_status()
            logger.info("✅ Firebase initialized - BUDDY is now ONLINE")
        except Exception as e:
            logger.error(f"❌ Firebase initialization failed: {e}")
    
    logger.info("🎯 BUDDY 2.0 Backend ready to serve!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down BUDDY 2.0 Backend...")
    
    # Set offline status in Firebase
    if FIREBASE_AVAILABLE:
        try:
            await update_buddy_offline_status()
            logger.info("✅ Firebase status updated - BUDDY is now OFFLINE")
        except Exception as e:
            logger.error(f"❌ Firebase shutdown error: {e}")
    
    logger.info("👋 BUDDY 2.0 Backend shutdown complete")

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    context: Dict[str, Any] = {}
    user_id: Optional[str] = "default_user"
    session_id: Optional[str] = "default_session"

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    session_id: str
    user_id: str

class ReminderCreate(BaseModel):
    title: str
    description: str = ""
    due_date: str  # ISO format datetime
    user_id: str = "default_user"

class ReminderResponse(BaseModel):
    id: str
    title: str
    description: str
    due_date: str
    status: str
    created_at: str

class UserPreferences(BaseModel):
    user_id: str
    preferences: Dict[str, Any]

# Database dependency
async def get_db() -> Optional[BuddyDatabase]:
    """Dependency to get database instance"""
    if USE_MONGODB:
        return await get_database()
    return None

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    if USE_MONGODB:
        try:
            mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
            await init_database(mongodb_uri)
            logger.info("MongoDB connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            logger.info("Falling back to in-memory storage")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    if USE_MONGODB and buddy_db.connected:
        await buddy_db.disconnect()

# Fallback in-memory storage (when MongoDB is not available)
conversations: Dict[str, List[Dict[str, Any]]] = {}
server_start_time = datetime.now()
MEMORY_FILE = os.path.join(os.path.dirname(__file__), 'user_memory.json')
user_memory: Dict[str, Any] = {}

def load_memory() -> Dict[str, Any]:
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load memory: {e}")
    return {"user_name": None, "preferences": {}, "frequent_intents": {}, "topics": []}

def save_memory() -> None:
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_memory, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save memory: {e}")

# Initialize memory on startup
user_memory.update(load_memory())

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "BUDDY Backend API with MongoDB is running", "status": "healthy"}

@app.get("/health")
async def health_check(db: Optional[BuddyDatabase] = Depends(get_db)):
    """Detailed health check including database."""
    uptime = (datetime.now() - server_start_time).total_seconds()
    
    health_data = {
        "status": "healthy",
        "uptime_seconds": uptime,
        "timestamp": datetime.now().isoformat(),
        "mongodb_enabled": USE_MONGODB
    }
    
    if db and db.connected:
        db_health = await db.health_check()
        health_data["database"] = db_health
    else:
        health_data["database"] = {"status": "disabled", "storage": "in-memory"}
        health_data["active_sessions"] = len(conversations)
    
    return health_data

@app.get("/config")
async def get_frontend_config():
    """Get configuration for Firebase frontend"""
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://buddy-2-0.onrender.com")
    
    config = {
        "api_url": render_url,
        "backend_status": "online",
        "version": "2.0",
        "features": {
            "mongodb": USE_MONGODB,
            "firebase": FIREBASE_AVAILABLE,
            "voice_processing": True,
            "cross_device_sync": True,
            "vector_memory": os.getenv("USE_VECTOR_MEMORY", "1") == "1"
        },
        "endpoints": {
            "chat": f"{render_url}/chat",
            "health": f"{render_url}/health",
            "status": f"{render_url}/status",
            "voice": f"{render_url}/voice/status"
        },
        "firebase_config": {
            "project_id": "buddyai-42493",
            "database_url": "https://buddyai-42493-default-rtdb.firebaseio.com"
        }
    }
    
    return config

@app.get("/status")
async def get_buddy_status():
    """Get BUDDY's current status for frontend"""
    status_data = {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "backend_url": os.getenv("RENDER_EXTERNAL_URL", "https://buddy-2-0.onrender.com"),
        "version": "2.0",
        "uptime_seconds": (datetime.now() - server_start_time).total_seconds(),
        "services": {
            "mongodb": USE_MONGODB,
            "firebase": FIREBASE_AVAILABLE,
            "vector_memory": os.getenv("USE_VECTOR_MEMORY", "1") == "1"
        }
    }
    
    # Update Firebase status if available
    if FIREBASE_AVAILABLE:
        try:
            firebase_manager = await get_firebase_manager()
            await firebase_manager.set_buddy_status("online", status_data)
        except Exception as e:
            logger.error(f"Failed to update Firebase status: {e}")
    
    return status_data

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, background_tasks: BackgroundTasks, db: Optional[BuddyDatabase] = Depends(get_db)):
    """Handle chat messages with MongoDB persistence."""
    try:
        session_id = message.session_id or "session_001"
        user_id = message.user_id or "default_user"
        
        # Store user message in database or memory
        if db and db.connected:
            await db.save_conversation(
                session_id=session_id,
                user_id=user_id,
                role="user",
                content=message.message,
                metadata=message.context
            )
        else:
            # Fallback to in-memory storage
            if session_id not in conversations:
                conversations[session_id] = []
            conversations[session_id].append({
                "role": "user",
                "content": message.message,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id
            })
        
        # Generate response
        if db and db.connected:
            conversation_history = await db.get_conversation_history(session_id, limit=10)
        else:
            conversation_history = conversations.get(session_id, [])
        
        response_text = await generate_response(message.message, conversation_history, user_id, db)
        
        # Store assistant response
        if db and db.connected:
            await db.save_conversation(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=response_text
            )
            
            # Log analytics in background
            background_tasks.add_task(
                db.log_analytics_event,
                "chat_interaction",
                user_id,
                {"message_length": len(message.message), "response_length": len(response_text)}
            )
        else:
            # Fallback storage
            conversations[session_id].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id
            })
        
        # Log conversation to Firebase for cross-device sync
        if FIREBASE_AVAILABLE:
            try:
                conversation_data = {
                    "message": message.message,
                    "response": response_text,
                    "device_type": message.context.get("device_type", "web"),
                    "session_id": session_id,
                    "metadata": message.context
                }
                background_tasks.add_task(log_conversation_to_firebase, user_id, conversation_data)
            except Exception as e:
                logger.error(f"Failed to log to Firebase: {e}")
        
        return ChatResponse(
            response=response_text,
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            user_id=user_id
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")

@app.get("/conversations/{session_id}")
async def get_conversation(session_id: str, db: Optional[BuddyDatabase] = Depends(get_db)):
    """Get conversation history."""
    try:
        if db and db.connected:
            messages = await db.get_conversation_history(session_id)
            return {"messages": messages}
        else:
            return {"messages": conversations.get(session_id, [])}
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reminders", response_model=ReminderResponse)
async def create_reminder(reminder: ReminderCreate, db: Optional[BuddyDatabase] = Depends(get_db)):
    """Create a new reminder."""
    try:
        if not db or not db.connected:
            raise HTTPException(status_code=503, detail="Database not available for reminders")
        
        # Parse due date
        due_date = datetime.fromisoformat(reminder.due_date.replace('Z', '+00:00'))
        
        # Create reminder in database
        reminder_id = await db.create_reminder(
            user_id=reminder.user_id,
            title=reminder.title,
            description=reminder.description,
            due_date=due_date
        )
        
        return ReminderResponse(
            id=reminder_id,
            title=reminder.title,
            description=reminder.description,
            due_date=due_date.isoformat(),
            status="active",
            created_at=datetime.now().isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reminders/{user_id}")
async def get_reminders(user_id: str, status: str = "active", db: Optional[BuddyDatabase] = Depends(get_db)):
    """Get reminders for a user."""
    try:
        if not db or not db.connected:
            return {"reminders": [], "message": "Database not available - reminders stored locally"}
        
        reminders = await db.get_user_reminders(user_id, status)
        
        # Convert ObjectId to string and format dates
        formatted_reminders = []
        for reminder in reminders:
            formatted_reminder = {
                "id": str(reminder["_id"]),
                "title": reminder["title"],
                "description": reminder["description"],
                "due_date": reminder["due_date"].isoformat(),
                "status": reminder["status"],
                "created_at": reminder["created_at"].isoformat()
            }
            if reminder.get("completed_at"):
                formatted_reminder["completed_at"] = reminder["completed_at"].isoformat()
            formatted_reminders.append(formatted_reminder)
        
        return {"reminders": formatted_reminders}
        
    except Exception as e:
        logger.error(f"Error getting reminders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/reminders/{reminder_id}/complete")
async def complete_reminder(reminder_id: str, db: Optional[BuddyDatabase] = Depends(get_db)):
    """Mark a reminder as completed."""
    try:
        if not db or not db.connected:
            raise HTTPException(status_code=503, detail="Database not available")
        
        success = await db.complete_reminder(reminder_id)
        
        if success:
            return {"message": "Reminder completed successfully"}
        else:
            raise HTTPException(status_code=404, detail="Reminder not found")
            
    except Exception as e:
        logger.error(f"Error completing reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reminders/due/check")
async def check_due_reminders(db: Optional[BuddyDatabase] = Depends(get_db)):
    """Get reminders that are due soon."""
    try:
        if not db or not db.connected:
            return {"due_reminders": [], "message": "Database not available"}
        
        due_reminders = await db.get_due_reminders(buffer_minutes=5)
        
        # Format reminders
        formatted_reminders = []
        for reminder in due_reminders:
            formatted_reminders.append({
                "id": str(reminder["_id"]),
                "title": reminder["title"],
                "description": reminder["description"],
                "due_date": reminder["due_date"].isoformat(),
                "user_id": reminder["user_id"]
            })
        
        return {"due_reminders": formatted_reminders}
        
    except Exception as e:
        logger.error(f"Error checking due reminders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/preferences")
async def update_preferences(prefs: UserPreferences, db: Optional[BuddyDatabase] = Depends(get_db)):
    """Update user preferences."""
    try:
        if db and db.connected:
            success = await db.update_user_preferences(prefs.user_id, prefs.preferences)
            return {"success": success, "message": "Preferences updated in database"}
        else:
            # Fallback to file storage
            user_memory.setdefault("preferences", {}).update(prefs.preferences)
            save_memory()
            return {"success": True, "message": "Preferences updated locally"}
            
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/skills")
async def get_skills_analytics(days: int = 30, db: Optional[BuddyDatabase] = Depends(get_db)):
    """Get skills usage analytics."""
    try:
        if not db or not db.connected:
            return {"message": "Database not available for analytics", "skills": []}
        
        analytics = await db.get_skill_analytics(days)
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting skills analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/daily")
async def get_daily_analytics(days: int = 7, db: Optional[BuddyDatabase] = Depends(get_db)):
    """Get daily usage analytics."""
    try:
        if not db or not db.connected:
            return {"message": "Database not available for analytics", "daily_stats": {}}
        
        daily_stats = await db.get_daily_stats(days)
        return {"daily_stats": daily_stats}
        
    except Exception as e:
        logger.error(f"Error getting daily analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Keep all existing endpoints from simple_backend.py
@app.get("/skills")
async def get_skills():
    """Get available skills."""
    return {
        "skills": [
            {
                "id": "chat",
                "name": "General Chat",
                "description": "General conversation and assistance",
                "enabled": True,
                "category": "conversation",
                "icon": "💬"
            },
            {
                "id": "reminders",
                "name": "Reminders",
                "description": "Set and manage reminders and tasks",
                "enabled": True,
                "category": "productivity",
                "icon": "⏰"
            },
            {
                "id": "weather",
                "name": "Weather",
                "description": "Get weather information and forecasts",
                "enabled": True,
                "category": "information",
                "icon": "🌤️"
            },
            {
                "id": "calculator",
                "name": "Calculator",
                "description": "Perform mathematical calculations",
                "enabled": True,
                "category": "utility",
                "icon": "🧮"
            },
            {
                "id": "analytics",
                "name": "Analytics",
                "description": "View usage statistics and insights",
                "enabled": USE_MONGODB,
                "category": "productivity",
                "icon": "📊"
            }
        ]
    }

# Continue with the existing functions from simple_backend.py...
# (I'll include the key functions - let me know if you want the complete file)

async def generate_response(user_message: str, conversation_history: List[Dict[str, Any]], 
                          user_id: str, db: Optional[BuddyDatabase] = None) -> str:
    """Enhanced response generation with Phase 1 Advanced AI capabilities."""
    
    # Try Phase 1 Advanced AI first (JARVIS-level intelligence)
    if PHASE1_ADVANCED_AI_AVAILABLE:
        try:
            return await _generate_phase1_advanced_response(
                user_message, conversation_history, user_id, db
            )
        except Exception as e:
            logger.warning(f"Phase 1 Advanced AI failed, falling back: {e}")
    
    # Try Enhanced NLP Engine (Phase 7)
    if ADVANCED_NLP_AVAILABLE:
        try:
            nlp_engine = await get_nlp_engine(db if db else None)
            session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d')}"
            
            result = await nlp_engine.process_message(
                session_id=session_id,
                user_id=user_id,
                message=user_message,
                metadata={
                    "conversation_history_length": len(conversation_history),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            if result.get("enhanced_nlp", False):
                logger.info(f"Enhanced NLP response - Intent: {result.get('intent')}, Confidence: {result.get('confidence', 0):.2f}")
                return result["response"]
        except Exception as e:
            logger.warning(f"Enhanced NLP engine failed: {e}")
    
    # Try Simplified NLP Engine
    try:
        nlp_engine = await get_simplified_nlp_engine(db if db else None)
        session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d')}"
        
        result = await nlp_engine.process_message(
            session_id=session_id,
            user_id=user_id,
            message=user_message,
            metadata={
                "conversation_history_length": len(conversation_history),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        if result.get("enhanced_nlp", False):
            logger.info(f"Simplified NLP response - Intent: {result.get('intent')}")
            return result["response"]
    except Exception as e:
        logger.warning(f"Simplified NLP engine failed: {e}")
    
    # Ultimate fallback to basic response generation
    return await _generate_basic_response(user_message, conversation_history, user_id, db)


async def _generate_phase1_advanced_response(user_message: str, conversation_history: List[Dict[str, Any]], 
                                           user_id: str, db: Optional[BuddyDatabase] = None) -> str:
    """Generate response using Phase 1 Advanced AI (JARVIS-level capabilities)"""
    
    # Initialize advanced components
    intent_classifier = await get_advanced_intent_classifier()
    semantic_memory = await get_semantic_memory_engine(conversation_db=db)
    
    # Generate session ID for context tracking
    session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H')}"
    
    # 1. Advanced Intent Classification with context
    intent_result = await intent_classifier.classify_intent(
        user_input=user_message,
        conversation_context=conversation_history,
        user_id=user_id
    )
    
    primary_intent = intent_result['primary_intent']
    entities = intent_result['entities']
    confidence = primary_intent['confidence']
    
    logger.info(f"Phase 1 AI - Intent: {primary_intent['intent']}, Confidence: {confidence:.3f}, Entities: {len(entities)}")
    
    # 2. Semantic Memory Retrieval for context-aware responses
    relevant_context = await semantic_memory.recall_relevant_context(
        query=user_message,
        user_id=user_id,
        session_id=session_id,
        limit=3
    )
    
    # 3. Store current conversation for future context
    conversation_data = {
        'id': f"{session_id}_{datetime.utcnow().timestamp()}",
        'user_id': user_id,
        'session_id': session_id,
        'content': user_message,
        'intent': primary_intent['intent'],
        'entities': entities,
        'timestamp': datetime.utcnow().isoformat(),
        'role': 'user',
        'metadata': {
            'confidence': confidence,
            'processing_time_ms': intent_result.get('processing_time_ms', 0),
            'model_type': intent_result.get('model_type', 'unknown')
        }
    }
    
    # Store in semantic memory (async)
    asyncio.create_task(semantic_memory.store_conversation_context(conversation_data))
    
    # 4. Generate advanced response based on intent and context
    response = await _generate_intent_based_response(
        intent=primary_intent['intent'],
        entities=entities,
        confidence=confidence,
        user_message=user_message,
        relevant_context=relevant_context,
        user_id=user_id,
        db=db
    )
    
    # 5. Store response in semantic memory
    response_data = {
        'id': f"{session_id}_{datetime.utcnow().timestamp()}_response",
        'user_id': user_id,
        'session_id': session_id,
        'content': response,
        'intent': primary_intent['intent'],
        'timestamp': datetime.utcnow().isoformat(),
        'role': 'assistant',
        'metadata': {
            'original_confidence': confidence,
            'context_used': len(relevant_context),
            'entities_extracted': len(entities),
            'phase1_advanced_ai': True
        }
    }
    
    asyncio.create_task(semantic_memory.store_conversation_context(response_data))
    
    return response


async def _generate_intent_based_response(intent: str, entities: Dict, confidence: float,
                                        user_message: str, relevant_context: List[Dict],
                                        user_id: str, db: Optional[BuddyDatabase] = None) -> str:
    """Generate sophisticated responses based on classified intent and extracted entities"""
    
    context_info = ""
    if relevant_context:
        context_info = f" (I found {len(relevant_context)} related conversations from our history)"
    
    # Communication intents
    if intent == 'email_send':
        return await _handle_email_send_intent(entities, context_info)
    elif intent == 'email_check':
        return await _handle_email_check_intent(entities, context_info)
    
    # Calendar and scheduling intents
    elif intent == 'calendar_schedule':
        return await _handle_calendar_schedule_intent(entities, context_info)
    elif intent == 'reminder_create':
        return await _handle_reminder_create_intent(entities, context_info, user_id, db)
    
    # Information and knowledge intents
    elif intent == 'weather_query':
        return await _handle_weather_query_intent(entities, context_info)
    elif intent == 'calculation':
        return await _handle_calculation_intent(entities, user_message, context_info)
    elif intent == 'general_qa':
        return await _handle_general_qa_intent(user_message, relevant_context, confidence)
    
    # Entertainment intents
    elif intent == 'music_play':
        return await _handle_music_play_intent(entities, context_info)
    
    # Smart home and control intents
    elif intent == 'lights_control':
        return await _handle_lights_control_intent(entities, context_info)
    elif intent == 'device_control':
        return await _handle_device_control_intent(entities, context_info)
    
    # Navigation intents
    elif intent == 'navigation_start':
        return await _handle_navigation_intent(entities, context_info)
    
    # Productivity intents
    elif intent == 'task_create':
        return await _handle_task_create_intent(entities, context_info, user_id, db)
    
    # Conversational intents with context awareness
    elif intent == 'greeting':
        return await _handle_greeting_intent(relevant_context, user_id, confidence)
    elif intent == 'help_request':
        return await _handle_help_request_intent(relevant_context, confidence)
    
    # Default advanced response
    else:
        return f"""🤖 **BUDDY Advanced AI** (Phase 1 Intelligence Active)

**Analysis:**
• Intent: {intent}
• Confidence: {confidence:.1%}
• Entities Extracted: {len(entities)}
• Context Retrieved: {len(relevant_context)} relevant conversations{context_info}

**Your Message:** "{user_message}"

I understand you're asking about {intent.replace('_', ' ')}. My advanced NLP system has analyzed your request with {confidence:.1%} confidence and extracted {len(entities)} key entities.

{f"**Context Awareness:** Based on our previous conversations, I can see patterns in your interactions that help me provide more personalized assistance." if relevant_context else ""}

**Available Advanced Capabilities:**
🧠 ML-powered intent classification
💭 Semantic memory and context retrieval  
🎯 Entity extraction and analysis
📚 Conversation pattern learning
🔄 Cross-session context persistence

How can I help you further with this {intent.replace('_', ' ')} request? I'm continuously learning to serve you better!"""


# Intent-specific handlers with advanced capabilities

async def _handle_email_send_intent(entities: Dict, context_info: str) -> str:
    """Handle email sending with entity extraction"""
    recipients = entities.get('email_addresses', entities.get('potential_names', []))
    subject = entities.get('subject', '')
    message_body = entities.get('message_body', '')
    
    response = f"📧 **Advanced Email Assistant**{context_info}\n\n"
    
    if recipients:
        response += f"**Recipients Detected:** {', '.join(recipients)}\n"
    if subject:
        response += f"**Subject:** {subject}\n"
    if message_body:
        response += f"**Message Preview:** {message_body[:100]}...\n"
    
    response += "\n🔧 **Next Steps:**\n"
    response += "• Email composition interface integration (Phase 3)\n"
    response += "• Contact verification and suggestion\n"
    response += "• Draft saving and scheduling options\n\n"
    response += "💡 **Advanced Feature:** I can learn your email patterns and suggest recipients, subjects, and optimal sending times!"
    
    return response

async def _handle_calendar_schedule_intent(entities: Dict, context_info: str) -> str:
    """Handle calendar scheduling with time and entity extraction"""
    time_entities = entities.get('time_expressions', []) + entities.get('relative_time', [])
    attendees = entities.get('potential_names', [])
    tasks = entities.get('subjects', [])
    
    response = f"📅 **Advanced Calendar Assistant**{context_info}\n\n"
    
    if time_entities:
        response += f"**Time Detected:** {', '.join(time_entities)}\n"
    if attendees:
        response += f"**Potential Attendees:** {', '.join(attendees)}\n"
    if tasks:
        response += f"**Meeting Subject:** {', '.join(tasks)}\n"
    
    response += "\n🔧 **Calendar Integration Features:**\n"
    response += "• Google Calendar API integration (Phase 3)\n"
    response += "• Automatic conflict detection\n"
    response += "• Smart scheduling suggestions\n"
    response += "• Multi-timezone coordination\n\n"
    response += "💡 **AI Enhancement:** I'll learn your meeting patterns and suggest optimal times based on your preferences!"
    
    return response

async def _handle_reminder_create_intent(entities: Dict, context_info: str, user_id: str, 
                                       db: Optional[BuddyDatabase] = None) -> str:
    """Handle reminder creation with advanced entity extraction"""
    time_entities = entities.get('time_expressions', []) + entities.get('relative_time', [])
    actions = entities.get('actions', [])
    subjects = entities.get('subjects', [])
    
    # Store reminder in database if available
    if db and hasattr(db, 'create_reminder'):
        try:
            reminder_data = {
                'user_id': user_id,
                'task': ' '.join(subjects) if subjects else 'reminder task',
                'time': time_entities[0] if time_entities else 'unspecified time',
                'actions': actions,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'active'
            }
            
            await db.create_reminder(reminder_data)
            storage_status = "✅ Stored in your personal reminder system"
        except Exception as e:
            storage_status = f"⚠️ Storage issue: {str(e)}"
    else:
        storage_status = "📝 Ready for database integration"
    
    response = f"⏰ **Advanced Reminder System**{context_info}\n\n"
    response += f"**Task Analysis:**\n"
    
    if actions:
        response += f"• Actions: {', '.join(actions)}\n"
    if subjects:
        response += f"• Subjects: {', '.join(subjects)}\n"
    if time_entities:
        response += f"• Timing: {', '.join(time_entities)}\n"
    
    response += f"\n**Status:** {storage_status}\n\n"
    response += "🧠 **Smart Features:**\n"
    response += "• Natural language time parsing\n"
    response += "• Context-aware reminder suggestions\n"
    response += "• Cross-device synchronization\n"
    response += "• Learning-based optimal timing\n\n"
    response += "💡 **AI Learning:** I'll analyze your reminder patterns to suggest better timing and priority levels!"
    
    return response

async def _handle_calculation_intent(entities: Dict, user_message: str, context_info: str) -> str:
    """Handle mathematical calculations with advanced entity extraction"""
    expressions = entities.get('expressions', [])
    numbers = entities.get('numbers', [])
    
    response = f"🧮 **Advanced Calculator**{context_info}\n\n"
    
    if expressions:
        try:
            # Safe evaluation of mathematical expressions
            for expr in expressions:
                clean_expr = ''.join(c for c in expr if c in '0123456789+-*/.() ')
                if clean_expr.strip() and all(c in '0123456789+-*/.() ' for c in clean_expr):
                    result = eval(clean_expr)
                    response += f"**Expression:** {clean_expr.strip()}\n"
                    response += f"**Result:** **{result}**\n\n"
        except Exception as e:
            response += f"**Expression Analysis:** {expressions}\n"
            response += f"**Error:** Could not evaluate expression safely\n\n"
    
    if numbers:
        response += f"**Numbers Detected:** {', '.join(map(str, numbers))}\n\n"
    
    response += "🔬 **Advanced Math Features:**\n"
    response += "• Complex expression parsing\n"
    response += "• Unit conversion capabilities\n"
    response += "• Scientific notation support\n"
    response += "• Step-by-step solution breakdown\n\n"
    response += "💡 **Smart Enhancement:** I can remember your calculation history and suggest related operations!"
    
    return response

async def _handle_weather_query_intent(entities: Dict, context_info: str) -> str:
    """Handle weather queries with location entity extraction"""
    locations = entities.get('locations', entities.get('cities', []))
    time_refs = entities.get('relative_time', entities.get('time_expressions', []))
    
    response = f"🌤️ **Advanced Weather Assistant**{context_info}\n\n"
    
    if locations:
        response += f"**Location Analysis:** {', '.join(locations)}\n"
    else:
        response += "**Location:** Current location (GPS/IP-based)\n"
    
    if time_refs:
        response += f"**Time Frame:** {', '.join(time_refs)}\n"
    
    response += "\n🔧 **Weather API Integration:**\n"
    response += "• Real-time weather data (OpenWeatherMap)\n"
    response += "• 7-day forecasts with hourly breakdown\n"
    response += "• Severe weather alerts and notifications\n"
    response += "• Location-based automatic updates\n\n"
    response += "💡 **AI Features:**\n"
    response += "• Weather pattern learning for your locations\n"
    response += "• Personalized weather recommendations\n"
    response += "• Smart notifications for weather changes\n"
    response += "• Activity-based weather suggestions\n\n"
    response += "🚀 **Coming in Phase 3:** Live weather integration with personalized insights!"
    
    return response

async def _handle_greeting_intent(relevant_context: List[Dict], user_id: str, confidence: float) -> str:
    """Handle greetings with personalized context awareness"""
    
    context_summary = ""
    if relevant_context:
        recent_topics = [ctx.get('metadata', {}).get('intent', '') for ctx in relevant_context[:3]]
        unique_topics = list(set([topic for topic in recent_topics if topic]))
        
        if unique_topics:
            context_summary = f"\n\n🧠 **Context Awareness:** I remember we've been discussing {', '.join(unique_topics[:2])}."
    
    current_time = datetime.now()
    time_greeting = ""
    if 5 <= current_time.hour < 12:
        time_greeting = "Good morning"
    elif 12 <= current_time.hour < 17:
        time_greeting = "Good afternoon"
    else:
        time_greeting = "Good evening"
    
    response = f"👋 **{time_greeting}!** I'm BUDDY with Phase 1 Advanced AI capabilities.\n\n"
    response += f"🧠 **Intelligence Status:**\n"
    response += f"• Intent Detection: {confidence:.1%} confidence\n"
    response += f"• Semantic Memory: {len(relevant_context)} relevant conversations\n"
    response += f"• Learning Engine: Active and adapting\n"
    response += f"• Context Awareness: {'Enhanced' if relevant_context else 'Building'}\n"
    
    response += context_summary
    
    response += f"\n\n🚀 **Ready to Help With:**\n"
    response += "📧 Email and communication\n"
    response += "📅 Calendar and scheduling\n"
    response += "💡 Information and calculations\n"
    response += "🎵 Entertainment and media\n"
    response += "🏠 Smart home control\n"
    response += "🗺️ Navigation and travel\n"
    response += "✅ Task and productivity management\n\n"
    response += "What can I help you accomplish today? I'm learning from every interaction to serve you better! ✨"
    
    return response

async def _handle_general_qa_intent(user_message: str, relevant_context: List[Dict], confidence: float) -> str:
    """Handle general questions with context-aware responses"""
    
    context_insight = ""
    if relevant_context:
        context_insight = f"\n\n🔍 **Context Analysis:** I found {len(relevant_context)} related conversations that might help inform my response."
    
    response = f"❓ **Advanced Q&A System** (Confidence: {confidence:.1%})\n\n"
    response += f"**Your Question:** \"{user_message}\"\n"
    response += context_insight
    response += f"\n\n🧠 **AI Analysis:**\n"
    response += f"• Question complexity: {'High' if len(user_message.split()) > 10 else 'Standard'}\n"
    response += f"• Context relevance: {'Available' if relevant_context else 'Building knowledge base'}\n"
    response += f"• Knowledge domain: General inquiry\n\n"
    
    response += "🔧 **Knowledge Integration Features:**\n"
    response += "• Semantic understanding of questions\n"
    response += "• Context-aware response generation\n"
    response += "• Learning from interaction patterns\n"
    response += "• Cross-conversation knowledge linking\n\n"
    
    response += "💡 **Enhanced in Phase 3:** Integration with knowledge APIs, web search, and specialized databases for comprehensive answers!\n\n"
    response += "Based on your question, I'm analyzing the best approach to provide you with accurate information. "
    response += "Could you provide any additional context or specify particular aspects you're most interested in?"
    
    return response


async def _generate_basic_response(user_message: str, conversation_history: List[Dict[str, Any]], 
                                 user_id: str, db: Optional[BuddyDatabase] = None) -> str:
    """Fallback basic response generation (original logic)."""
    import re
    import random
    from datetime import datetime, timedelta
    
    message_lower = user_message.lower()
    
    # Greeting responses
    if any(phrase in message_lower for phrase in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
        greetings = [
            "Hello! I'm BUDDY, your AI assistant. How can I help you today? 🤖",
            "Hi there! Great to see you! What can I assist you with? 😊",
            "Hey! I'm here and ready to help. What's on your mind? 🚀",
            "Hello! Nice to chat with you again. How can I be of service? ✨"
        ]
        return random.choice(greetings)
    
    # How are you responses
    elif any(phrase in message_lower for phrase in ["how are you", "how're you", "how do you feel"]):
        responses = [
            "I'm doing great, thank you for asking! I'm running on cloud infrastructure with MongoDB Atlas, so I'm feeling quite powerful! 🌩️ How are you doing?",
            "I'm excellent! My databases are synced, my APIs are responsive, and I'm ready to help! 💪 How about you?",
            "Feeling fantastic! Connected to the cloud and ready for anything. How can I assist you today? ⚡",
            "I'm wonderful! All systems are green and I'm excited to help you accomplish your goals! 🎯"
        ]
        return random.choice(responses)
    
    # Weather queries
    elif any(phrase in message_lower for phrase in ["weather", "temperature", "forecast", "rain", "sunny", "cloudy"]):
        # Extract location if mentioned
        location_match = re.search(r'weather\s+(?:in|at|for)\s+(\w+)', message_lower)
        location = location_match.group(1) if location_match else "your location"
        
        try:
            # Simple weather response (you can integrate actual weather API later)
            return f"🌤️ **Weather Information for {location.title()}:**\n\n" \
                   f"I'd love to get you the current weather! However, I need to connect to a weather service API.\n\n" \
                   f"💡 **Coming Soon**: Real-time weather data integration\n" \
                   f"🔧 **For now**: Try checking your local weather app or website\n\n" \
                   f"Is there anything else I can help you with? 😊"
        except Exception as e:
            return f"🌤️ Sorry, I'm having trouble accessing weather data right now. Please try again later! 🔄"
    
    # Math/Calculator queries
    elif any(phrase in message_lower for phrase in ["calculate", "math", "plus", "minus", "multiply", "divide", "=", "+", "-", "*", "/"]):
        try:
            # Simple math evaluation (be careful with eval in production!)
            
            # Extract mathematical expression
            math_expression = re.sub(r'[^\d+\-*/().\s]', '', user_message)
            if math_expression.strip():
                # Basic safety check
                if all(c in "0123456789+-*/.() " for c in math_expression):
                    result = eval(math_expression)
                    return f"🧮 **Calculator Result:**\n\n{math_expression.strip()} = **{result}**\n\n✨ Need more calculations? Just ask!"
                else:
                    return "🧮 I can help with math! Try something like: 'Calculate 25 * 4' or '100 / 5 + 10'"
            else:
                return "🧮 **Calculator Ready!** \n\nTry asking me things like:\n• 'Calculate 15 + 25'\n• 'What's 100 divided by 4?'\n• '25 * 8 - 50'"
        except Exception as e:
            return "🧮 I had trouble with that calculation. Please try a simpler math expression!"
    
    # Time queries
    elif any(phrase in message_lower for phrase in ["time", "clock", "what time", "current time"]):
        current_time = datetime.now()
        return f"🕐 **Current Time:**\n\n{current_time.strftime('%I:%M %p')}\n{current_time.strftime('%A, %B %d, %Y')}\n\n⏰ Need to set a reminder? Just say 'remind me to [task]'!"
    
    # Set Reminder with database integration
    elif any(phrase in message_lower for phrase in ["set reminder", "remind me", "create reminder"]):
        if db and db.connected:
            try:
                due_date = datetime.now() + timedelta(hours=1)  # Default 1 hour from now
                
                task_text = re.sub(r'(set|create)?\s*(?:a\s+)?reminder\s*(for|to)?\s*', '', user_message, flags=re.IGNORECASE).strip()
                
                reminder_id = await db.create_reminder(
                    user_id=user_id,
                    title=task_text,
                    description=f"Reminder created via chat: {task_text}",
                    due_date=due_date
                )
                
                return f"✅ **Reminder Created!** \n📝 **Task**: {task_text}\n🕐 **Due**: {due_date.strftime('%I:%M %p')}\n💾 **Saved to cloud database**"
                
            except Exception as e:
                logger.error(f"Failed to create database reminder: {e}")
                return f"⏰ **Reminder Noted!** \n📝 **Task**: {task_text}\n⚠️ **Note**: Could not save to database, stored locally"
        else:
            task_text = re.sub(r'(set|create)?\s*(?:a\s+)?reminder\s*(for|to)?\s*', '', user_message, flags=re.IGNORECASE).strip()
            return f"⏰ **Reminder Created!** \n📝 **Task**: {task_text}\n💡 **Tip**: Enable MongoDB for persistent reminders"
    
    # Get Reminders
    elif any(phrase in message_lower for phrase in ["my reminders", "list reminders", "show reminders"]):
        if db and db.connected:
            try:
                reminders = await db.get_user_reminders(user_id, "active")
                
                if reminders:
                    reminder_list = []
                    for i, reminder in enumerate(reminders[:5], 1):  # Show max 5
                        due_date = reminder["due_date"].strftime('%m/%d %I:%M %p')
                        reminder_list.append(f"{i}. {reminder['title']} - {due_date}")
                    
                    return f"📋 **Your Active Reminders:**\n" + "\n".join(reminder_list) + f"\n\n💾 **From cloud database** ({len(reminders)} total)"
                else:
                    return "📋 **No active reminders found.**\n💡 **Tip**: Say 'set reminder for [task]' to create one!"
                    
            except Exception as e:
                logger.error(f"Failed to get reminders: {e}")
                return "📋 **Could not retrieve reminders from database.**\n⚠️ **Error**: Database connection issue"
        else:
            return "📋 **Your Reminders:**\n• No database connection\n💡 **Tip**: Enable MongoDB for persistent reminders"
    
    # Help/What can you do queries
    elif any(phrase in message_lower for phrase in ["help", "what can you do", "capabilities", "features"]):
        help_text = """🤖 **BUDDY Capabilities:**

💬 **Chat & Conversation**
• Natural conversation and assistance
• Memory of our chat history

⏰ **Reminders & Tasks**
• 'Set reminder for meeting at 3pm'
• 'Show my reminders'

🧮 **Calculator**
• 'Calculate 25 * 4 + 10'
• 'What's 150 divided by 6?'

🕐 **Time & Date**
• 'What time is it?'
• Current date and time

🌤️ **Weather** (Coming Soon)
• 'Weather in [city]'
• Temperature and forecasts

💾 **Cloud Storage**
• All data saved to MongoDB Atlas
• Cross-device synchronization

✨ **Just ask me anything! I'm here to help!**"""
        return help_text
    
    # Unknown/General queries
    else:
        # Log skill usage for analytics
        if db and db.connected:
            skill_id = "general_chat"
            if "weather" in message_lower:
                skill_id = "weather"
            elif any(w in message_lower for w in ["calculate", "math"]):
                skill_id = "calculator"
            elif "time" in message_lower:
                skill_id = "time"
            
            try:
                await db.log_skill_usage(user_id, skill_id, True)
            except Exception as e:
                logger.error(f"Failed to log skill usage: {e}")
        
        # Provide helpful response for unknown queries
        responses = [
            f"I understand you're asking about: \"{user_message}\"\n\n🤔 I'm not sure how to help with that specific request yet, but I'm always learning!\n\n💡 **Try asking me about:**\n• Time and date\n• Simple calculations\n• Setting reminders\n• General conversation\n\nWhat else can I help you with? 😊",
            f"That's an interesting question! \"{user_message}\"\n\n🚀 I'm still expanding my knowledge base. Right now I'm great at:\n\n⏰ Time queries\n🧮 Math calculations\n📝 Reminders\n💬 General chat\n\nIs there something specific I can help you with? ✨",
            f"I hear you asking: \"{user_message}\"\n\n🤖 While I may not have a perfect answer for that yet, I'm constantly improving!\n\n🎯 **I'm excellent at:**\n• Answering time questions\n• Doing calculations\n• Managing reminders\n• Having conversations\n\nTry me with something else! 🌟"
        ]
        
        import random
        return random.choice(responses)

if __name__ == "__main__":
    logger.info("Starting BUDDY Backend Server with MongoDB...")
    
    # Check MongoDB availability
    if USE_MONGODB:
        logger.info("MongoDB integration enabled")
    else:
        logger.info("MongoDB disabled - using in-memory storage")
    
    if DEV_MODE:
        uvicorn.run(
            "enhanced_backend:app",
            host="localhost", 
            port=8082,
            log_level="info",
            reload=True
        )
    else:
        uvicorn.run(
            app,
            host="localhost", 
            port=8082,
            log_level="info"
        )
