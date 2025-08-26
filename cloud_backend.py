"""
BUDDY Cloud Backend - Production Ready

A simplified FastAPI server optimized for cloud deployment.
Includes core features with graceful fallbacks for missing dependencies.
"""

import os
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn

# Phase 1 foundational imports
from infrastructure.config.settings import settings
from infrastructure.logging.structured import configure_logging, get_logger
from infrastructure.middleware import CorrelationIdMiddleware, RateLimitMiddleware, MetricsMiddleware
from infrastructure.security.ratelimit import RateLimiter
from infrastructure.metrics import metrics
from plugins.registry import registry, Plugin
from i18n.translator import translate
from vector.semantic_index import semantic_index
from jobs.scheduler import scheduler

# Auth integration
from packages.core.buddy.auth.jwt_manager import BuddyAuthManager
from packages.core.buddy.auth.api import BuddyAuthAPI, create_auth_routes, BuddyAuthMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

# Optional OpenTelemetry (deferred if not installed)
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    OTEL_AVAILABLE = True
except Exception:
    OTEL_AVAILABLE = False

# Set up logging
configure_logging(settings.environment)
logger = get_logger("cloud-backend")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Try to import optional dependencies with fallbacks
try:
    from mongodb_integration import buddy_db, init_database, get_database
    MONGODB_AVAILABLE = True
    logger.info("MongoDB integration available")
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("MongoDB not available - using memory storage")

try:
    import openai
    OPENAI_AVAILABLE = True
    logger.info("OpenAI integration available")
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - using simple responses")

try:
    from firebase_admin import credentials, messaging
    import firebase_admin
    FIREBASE_AVAILABLE = True
    logger.info("Firebase integration available")
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase not available - notifications disabled")

# Initialize FastAPI app
app = FastAPI(
    title="BUDDY AI Assistant - Cloud Backend",
    description="Simplified cloud-compatible BUDDY backend (Phase 1 foundations added)",
    version=settings.version
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured / metrics / rate limit middleware
rate_limiter = RateLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)
app.add_middleware(MetricsMiddleware)

# Pydantic models
class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    user_id: Optional[str] = Field("default", min_length=1, max_length=100)
    conversation_id: Optional[str] = None
    locale: Optional[str] = Field(None, min_length=2, max_length=5)

    @validator("locale")
    def normalize_locale(cls, v):
        if v:
            return v.lower()
        return v

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    conversation_id: str
    confidence: float = 1.0

class ReminderRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=1000)
    due_time: str = Field(..., description="ISO8601 timestamp UTC")  # TODO: move to datetime field

    @validator("due_time")
    def validate_due_time(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except Exception:
            raise ValueError("due_time must be valid ISO8601")
        return v

class ReminderResponse(BaseModel):
    id: str
    title: str
    description: str
    due_time: str
    status: str

# In-memory storage fallback
memory_storage = {
    "conversations": {},
    "reminders": {},  # reminder_id -> data
    "analytics": []
}

# Error taxonomy (simple)
class ErrorCodes:
    INTERNAL_ERROR = "internal_error"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    RATE_LIMIT = "rate_limited"
@app.get("/semantic/search")
async def semantic_search(q: str, top_k: int = 3):
    results = semantic_index.search(q, top_k=top_k)
    return {"query": q, "results": [{"text": t, "score": s} for t, s in results]}

@app.get("/protected/ping")
async def protected_ping(claims: Dict = Depends(lambda cred: auth_api.verify_token(cred))):  # type: ignore
    return {"message": "pong", "user": claims.get("sub")}

# Simple response patterns
RESPONSE_PATTERNS = {
    "greeting": [
        "Hello! How can I help you today?",
        "Hi there! What can I do for you?",
        "Greetings! I'm BUDDY, your AI assistant."
    ],
    "how_are_you": [
        "I'm doing great! Thanks for asking. How are you?",
        "I'm functioning perfectly! How can I assist you?",
        "All systems operational! What would you like to know?"
    ],
    "time": [
        f"The current time is {datetime.now().strftime('%H:%M:%S')}",
        f"It's {datetime.now().strftime('%I:%M %p')} right now"
    ],
    "date": [
        f"Today is {datetime.now().strftime('%A, %B %d, %Y')}",
        f"The date is {datetime.now().strftime('%Y-%m-%d')}"
    ],
    "default": [
        "That's interesting! Tell me more.",
        "I understand. What else would you like to know?",
        "Thanks for sharing that with me!"
    ]
}

async def get_simple_response(message: str) -> tuple[str, float]:
    """Generate simple response without AI dependencies"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
        return RESPONSE_PATTERNS["greeting"][0], 0.9
    elif "how are you" in message_lower:
        return RESPONSE_PATTERNS["how_are_you"][0], 0.9
    elif "time" in message_lower:
        return RESPONSE_PATTERNS["time"][0], 0.8
    elif "date" in message_lower or "today" in message_lower:
        return RESPONSE_PATTERNS["date"][0], 0.8
    else:
        return f"You said: {message}. That's interesting!", 0.6

async def get_ai_response(message: str) -> tuple[str, float]:
    """Get AI response using OpenAI if available"""
    if not OPENAI_AVAILABLE:
        return await get_simple_response(message)
    
    try:
        # Simple OpenAI integration
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are BUDDY, a helpful AI assistant."},
                {"role": "user", "content": message}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content, 0.9
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return await get_simple_response(message)

# API Endpoints
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.version,
        "environment": settings.environment,
        "features": {
            "mongodb": MONGODB_AVAILABLE,
            "openai": OPENAI_AVAILABLE,
            "firebase": FIREBASE_AVAILABLE,
            "metrics": settings.enable_metrics,
        }
    }

@app.get("/ready")
async def readiness():
    # Simple readiness (later: check DB, queue, vector index load)
    return {"ready": True}

@app.post("/chat", response_model=ChatResponse)
async def chat(message_data: ChatMessage):
    """Main chat endpoint"""
    try:
        start_time = time.time()
        
        # Generate response
        response_text, confidence = await get_ai_response(message_data.message)
        # Simple i18n demo: override greeting if user locale provided
        if message_data.locale:
            if any(word in message_data.message.lower() for word in ["hello", "hi", "hey", "hola", "bonjour"]):
                response_text = translate("greeting", locale=message_data.locale)
        
        # Create conversation ID if not provided
        conversation_id = message_data.conversation_id or f"conv_{int(time.time())}"
        
        # Store conversation if MongoDB available
        if MONGODB_AVAILABLE:
            try:
                db = await get_database()
                await db.save_conversation(
                    session_id=conversation_id,
                    user_id=message_data.user_id,
                    role="user",
                    content=message_data.message
                )
                await db.save_conversation(
                    session_id=conversation_id,
                    user_id=message_data.user_id,
                    role="assistant",
                    content=response_text
                )
            except Exception as e:
                logger.error(f"Database error: {e}")
        else:
            # Store in memory
            if conversation_id not in memory_storage["conversations"]:
                memory_storage["conversations"][conversation_id] = []
            memory_storage["conversations"][conversation_id].extend([
                {"role": "user", "content": message_data.message, "timestamp": datetime.now().isoformat()},
                {"role": "assistant", "content": response_text, "timestamp": datetime.now().isoformat()}
            ])
        
        response_time = time.time() - start_time
        logger.info(f"Chat response generated in {response_time:.2f}s")
        
        return ChatResponse(
            response=response_text,
            timestamp=datetime.now().isoformat(),
            conversation_id=conversation_id,
            confidence=confidence
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    try:
        if MONGODB_AVAILABLE:
            db = await get_database()
            history = await db.get_conversation_history(conversation_id)
            return {"conversation_id": conversation_id, "messages": history}
        else:
            # Return from memory
            messages = memory_storage["conversations"].get(conversation_id, [])
            return {"conversation_id": conversation_id, "messages": messages}
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation")

@app.post("/reminders", response_model=ReminderResponse)
async def create_reminder(reminder: ReminderRequest, credentials: HTTPAuthorizationCredentials = Depends()):
    """Create a new reminder"""
    try:
        reminder_id = f"rem_{int(time.time())}"
        due_date = datetime.fromisoformat(reminder.due_time.replace('Z', '+00:00'))
        # schedule execution
        delay = (due_date - datetime.now(due_date.tzinfo)).total_seconds()
        if delay > 0:
            def trigger():
                logger.info("reminder_due", id=reminder_id, title=reminder.title)
            scheduler.schedule_interval(f"reminder_{reminder_id}", int(delay), trigger)  # one-shot simulated via interval
        
        if MONGODB_AVAILABLE:
            db = await get_database()
            await db.create_reminder(
                user_id="default",
                title=reminder.title,
                description=reminder.description,
                due_date=due_date
            )
        else:
            # Store in memory
            memory_storage["reminders"][reminder_id] = {
                "title": reminder.title,
                "description": reminder.description,
                "due_time": reminder.due_time,
                "status": "active"
            }
        
        return ReminderResponse(
            id=reminder_id,
            title=reminder.title,
            description=reminder.description,
            due_time=reminder.due_time,
            status="active"
        )
        
    except Exception as e:
        logger.error(f"Create reminder error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create reminder")

@app.get("/reminders")
async def get_reminders(user_id: str = "default", credentials: HTTPAuthorizationCredentials = Depends()):
    """Get all reminders for a user"""
    try:
        if MONGODB_AVAILABLE:
            db = await get_database()
            reminders = await db.get_user_reminders(user_id)
            return {"reminders": reminders}
        else:
            # Return from memory
            return {"reminders": list(memory_storage["reminders"].values())}
    except Exception as e:
        logger.error(f"Get reminders error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve reminders")

@app.get("/analytics")
async def get_analytics():
    """Get basic analytics"""
    try:
        if MONGODB_AVAILABLE:
            db = await get_database()
            stats = await db.get_daily_stats(days=7)
            return {"analytics": stats}
        else:
            # Return basic memory stats
            return {
                "analytics": {
                    "conversations": len(memory_storage["conversations"]),
                    "reminders": len(memory_storage["reminders"]),
                    "total_messages": sum(len(conv) for conv in memory_storage["conversations"].values())
                }
            }
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting BUDDY Cloud Backend...", env=settings.environment, version=settings.version)
    
    # Initialize MongoDB if available
    if MONGODB_AVAILABLE:
        try:
            mongodb_uri = os.getenv("MONGODB_URI")
            if mongodb_uri:
                await init_database(mongodb_uri)
                logger.info("✅ MongoDB initialized successfully")
            else:
                logger.warning("⚠️  MongoDB URI not found, using memory storage")
        except Exception as e:
            logger.error(f"❌ MongoDB initialization failed: {e}")
    
    # Initialize Firebase if available
    if FIREBASE_AVAILABLE:
        try:
            service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "config/firebase-service-account.json")
            if os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                logger.info("✅ Firebase initialized successfully")
            else:
                logger.warning("⚠️  Firebase service account not found")
        except Exception as e:
            logger.error(f"❌ Firebase initialization failed: {e}")
    
    # Auth setup
    global auth_api
    auth_api = None  # type: ignore
    if settings.mongodb_uri:
        try:
            client = AsyncIOMotorClient(settings.mongodb_uri)
            auth_manager = BuddyAuthManager(jwt_secret=settings.jwt_secret, mongo_client=client, database_name="buddy_auth")
            await auth_manager.initialize_collections()
            auth_api = BuddyAuthAPI(auth_manager=auth_manager)
            create_auth_routes(app, auth_api)
            app.middleware("http")(BuddyAuthMiddleware(auth_api))
            logger.info("✅ Auth system initialized")
        except Exception as e:
            logger.error("Auth init failed", error=str(e))

    # Register core plugins stub
    registry.register(Plugin(name="core_memory"))
    registry.register(Plugin(name="semantic_index"))

    # Seed semantic index with sample (later: load from DB)
    semantic_index.add("BUDDY is your helpful AI assistant.")
    semantic_index.add("You can set reminders and have conversations.")

    # Schedule simple analytics heartbeat
    scheduler.schedule_interval("heartbeat", 300, lambda: logger.info("heartbeat", ts=datetime.utcnow().isoformat()))

    logger.info("🎉 BUDDY Cloud Backend started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🔄 Shutting down BUDDY Cloud Backend...")
    
    if MONGODB_AVAILABLE:
        try:
            from mongodb_integration import close_database
            await close_database()
            logger.info("✅ MongoDB connection closed")
        except Exception as e:
            logger.error(f"❌ MongoDB shutdown error: {e}")
    
    logger.info("👋 BUDDY Cloud Backend shut down complete")

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8081))
    logger.info("🌐 Starting server", host=host, port=port)
    uvicorn.run("cloud_backend:app", host=host, port=port, log_level="info", reload=False)
