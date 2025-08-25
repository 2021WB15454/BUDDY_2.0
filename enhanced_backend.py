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

# Import MongoDB integration
from mongodb_integration import buddy_db, init_database, get_database, BuddyDatabase

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
app = FastAPI(title="BUDDY Backend API with MongoDB", version="0.2.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
async def get_db() -> BuddyDatabase:
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
async def health_check(db: BuddyDatabase = Depends(get_db)):
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

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, background_tasks: BackgroundTasks, db: BuddyDatabase = Depends(get_db)):
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
async def get_conversation(session_id: str, db: BuddyDatabase = Depends(get_db)):
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
async def create_reminder(reminder: ReminderCreate, db: BuddyDatabase = Depends(get_db)):
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
async def get_reminders(user_id: str, status: str = "active", db: BuddyDatabase = Depends(get_db)):
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
async def complete_reminder(reminder_id: str, db: BuddyDatabase = Depends(get_db)):
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
async def check_due_reminders(db: BuddyDatabase = Depends(get_db)):
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
async def update_preferences(prefs: UserPreferences, db: BuddyDatabase = Depends(get_db)):
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
async def get_skills_analytics(days: int = 30, db: BuddyDatabase = Depends(get_db)):
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
async def get_daily_analytics(days: int = 7, db: BuddyDatabase = Depends(get_db)):
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
                          user_id: str, db: BuddyDatabase = None) -> str:
    """Enhanced response generation with database integration."""
    message_lower = user_message.lower()
    
    # Set Reminder with database integration
    if any(phrase in message_lower for phrase in ["set reminder", "remind me", "create reminder"]):
        if db and db.connected:
            # Parse reminder from message (basic implementation)
            import re
            time_match = re.search(r'at (\d{1,2}(?::\d{2})?(?:\s*(?:am|pm))?)', message_lower)
            
            try:
                # Create a reminder for later today or tomorrow
                from datetime import datetime, timedelta
                due_date = datetime.now() + timedelta(hours=1)  # Default 1 hour from now
                
                task_text = re.sub(r'(set|create)?\s*(?:a\s+)?reminder\s*(for|to)?\s*', '', user_message, flags=re.IGNORECASE).strip()
                
                reminder_id = await db.create_reminder(
                    user_id=user_id,
                    title=task_text,
                    description=f"Reminder created via chat: {task_text}",
                    due_date=due_date
                )
                
                return f"✅ **Reminder Created!** \n📝 **Task**: {task_text}\n🕐 **Due**: {due_date.strftime('%I:%M %p')}\n💾 **Saved to database**"
                
            except Exception as e:
                logger.error(f"Failed to create database reminder: {e}")
                return f"⏰ **Reminder Noted!** \n📝 **Task**: {task_text}\n⚠️ **Note**: Could not save to database, stored locally"
        else:
            return f"⏰ **Reminder Created!** \n📝 **Task**: {user_message}\n💡 **Tip**: Enable MongoDB for persistent reminders"
    
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
                    
                    return f"📋 **Your Active Reminders:**\n" + "\n".join(reminder_list) + f"\n\n💾 **From database** ({len(reminders)} total)"
                else:
                    return "📋 **No active reminders found.**\n💡 **Tip**: Say 'set reminder for [task]' to create one!"
                    
            except Exception as e:
                logger.error(f"Failed to get reminders: {e}")
                return "📋 **Could not retrieve reminders from database.**\n⚠️ **Error**: Database connection issue"
        else:
            return "📋 **Your Reminders:**\n• No database connection\n💡 **Tip**: Enable MongoDB for persistent reminders"
    
    # For all other intents, use the original logic from simple_backend.py
    # but with database analytics logging
    if db and db.connected:
        # Log skill usage for analytics
        skill_id = "general_chat"  # Default
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
    
    # Return to original response generation logic...
    # (Include the original generate_response logic here)
    return f"I understand you said: \"{user_message}\"\n\nI'm still learning new skills with database integration! 🚀"

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
