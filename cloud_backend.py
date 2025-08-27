"""
BUDDY Cloud Backend - Production Ready

A simplified FastAPI server optimized for cloud deployment.
Includes core features with graceful fallbacks for missing dependencies.
Uses Universal Port Manager for platform-agnostic deployment.
"""

import os
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import contextlib
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn

# Universal Port Management
from buddy_core.utils.universal_port_manager import (
    universal_port_manager, 
    get_buddy_port, 
    get_buddy_host, 
    get_server_config,
    print_startup_banner,
    auto_configure
)

# Phase 1 foundational imports
from infrastructure.config.settings import settings
from infrastructure.logging.structured import configure_logging, get_logger
from infrastructure.middleware import CorrelationIdMiddleware, RateLimitMiddleware, MetricsMiddleware
from infrastructure.security.ratelimit import RateLimiter
try:
    import redis  # type: ignore
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False
from infrastructure.metrics import metrics
from plugins.registry import registry, Plugin
from i18n.translator import translate
from vector.semantic_index import (
    SemanticIndex,
    BowVectorIndex,
    FaissIndex,
    ChromaIndex,
    semantic_index as default_semantic_index,
)
from packages.core.buddy.memory.memory_service import memory_service, MemoryService  # type: ignore
from jobs.scheduler import scheduler

# Auth integration
from packages.core.buddy.auth.jwt_manager import BuddyAuthManager
from packages.core.buddy.auth.api import BuddyAuthAPI, create_auth_routes, BuddyAuthMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

# Optional OpenTelemetry (deferred if not installed)
try:  # Optional OpenTelemetry
    from opentelemetry import trace  # type: ignore
    from opentelemetry.sdk.resources import Resource  # type: ignore
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore
    OTEL_AVAILABLE = True
except Exception:
    OTEL_AVAILABLE = False
    trace = None  # type: ignore
def rbac_required(required_roles: List[str]):
    async def dependency(credentials: HTTPAuthorizationCredentials = Depends()):
        if not auth_api:
            raise HTTPException(status_code=401, detail="Auth not initialized")
        claims = await auth_api.auth_manager.verify_access_token(credentials.credentials)  # type: ignore
        if not claims:
            raise HTTPException(status_code=401, detail="Invalid token")
        roles = claims.get("roles", [])
        if any(r in roles for r in required_roles):
            return claims
        raise HTTPException(status_code=403, detail="Forbidden - missing role")
    return dependency

# Standard error schema helper
def error_response(code: str, message: str, request: Request, details: Dict | None = None, status_code: int = 400):
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        },
        "request_id": getattr(request.state, "correlation_id", None)
    }

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

try:  # Optional OpenAI
    import openai  # type: ignore
    OPENAI_AVAILABLE = True
    logger.info("OpenAI integration available")
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - using simple responses")

try:  # Optional Firebase
    from firebase_admin import credentials, messaging  # type: ignore
    import firebase_admin  # type: ignore
    FIREBASE_AVAILABLE = True
    logger.info("Firebase integration available")
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase not available - notifications disabled")

# Vector backend selection (allows future expansion)
try:
    chosen_backend = getattr(settings, 'vector_backend', 'inmemory')
except Exception:
    chosen_backend = 'inmemory'

backend_key = (chosen_backend or 'inmemory').lower()
if backend_key in ('inmemory', 'memory'):
    semantic_index = default_semantic_index
elif backend_key == 'bow':
    # If Mongo available and configured later in startup, we can rebind with persistence
    semantic_index = BowVectorIndex()
    logger.info("Using BowVectorIndex backend for semantic search (non-persistent until startup rebind if MongoDB)")
elif backend_key == 'faiss':
    semantic_index = FaissIndex()
    logger.info("Attempting to use FaissIndex backend (falls back silently if faiss missing)")
elif backend_key == 'chroma':
    semantic_index = ChromaIndex()
    logger.info("Attempting to use ChromaIndex backend (falls back silently if chromadb missing)")
else:
    logger.warning(f"Vector backend '{chosen_backend}' not implemented; defaulting to in-memory")
    semantic_index = default_semantic_index

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

# Structured / metrics / rate limit middleware (with optional Redis backend)
if getattr(settings, 'redis_url', None) and REDIS_AVAILABLE:
    class RedisRateLimiter(RateLimiter):
        def __init__(self, client, limit, window):
            super().__init__(limit, window)
            self.client = client
            self.script = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[1]) end
return current
"""
        def check(self, key: str, *, limit: int | None = None, window: int | None = None):
            applied_limit = limit or self.default_limit
            applied_window = window or self.default_window
            ttl_ms = applied_window * 1000
            try:
                current = self.client.eval(self.script, 1, f"rl:{key}", ttl_ms)
            except Exception:
                # fallback to in-memory if redis fails
                return super().check(key, limit=applied_limit, window=applied_window)
            remaining = applied_limit - current
            if current > applied_limit:
                return False, 0, applied_limit
            return True, max(0, remaining), applied_limit
    try:
        _redis_client = redis.Redis.from_url(str(settings.redis_url))  # type: ignore[arg-type]
        rate_limiter = RedisRateLimiter(_redis_client, settings.rate_limit_requests, settings.rate_limit_window_seconds)
    except Exception:
        rate_limiter = RateLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)
else:
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

@app.get("/admin/echo")
async def admin_echo(claims: Dict = Depends(rbac_required(["admin"]))):
    return {"message": "admin access granted", "user": claims.get("sub"), "roles": claims.get("roles", [])}

@app.get("/protected/ping")
async def protected_ping(claims: Dict = Depends(lambda cred: auth_api.verify_token(cred))):  # type: ignore
    return {"message": "pong", "user": claims.get("sub")}

@app.post("/tracing/enable")
async def enable_tracing():
    if not OTEL_AVAILABLE:
        raise HTTPException(status_code=501, detail="Tracing not available")
    if OTEL_AVAILABLE and trace and getattr(trace, "get_tracer_provider", None) and trace.get_tracer_provider():  # already configured
        return {"status": "already_enabled"}
    if OTEL_AVAILABLE and trace:
        resource = Resource.create({"service.name": "buddy-cloud-backend"})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter())
        provider.add_span_processor(processor)
        if getattr(trace, "set_tracer_provider", None):
            trace.set_tracer_provider(provider)
    return {"status": "enabled"}

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

try:
    import tiktoken  # type: ignore
    TIKTOKEN_AVAILABLE = True
except Exception:
    TIKTOKEN_AVAILABLE = False

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    if TIKTOKEN_AVAILABLE:
        try:
            enc = tiktoken.encoding_for_model(model)
            return len(enc.encode(text))
        except Exception:
            pass
    # fallback word-based estimate
    return max(1, len(text.split()))

def trim_messages_token_budget(messages: List[Dict[str, str]], budget: int, model: str = "gpt-3.5-turbo") -> List[Dict[str, str]]:
    # messages: list of {role, content}
    if not messages:
        return messages
    total = 0
    trimmed: List[Dict[str, str]] = []
    # iterate from end (most recent) backwards
    for msg in reversed(messages):
        tokens = count_tokens(msg.get("content", ""), model=model)
        if total + tokens > budget:
            break
        trimmed.append(msg)
        total += tokens
    return list(reversed(trimmed))

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
async def chat(message_data: ChatMessage, credentials: HTTPAuthorizationCredentials = Depends(), persona: str = Query("buddy", description="Persona mode: 'buddy' or 'neutral'")):
    """Chat endpoint with tracing, role-based rate tiers, context trimming, and token usage analytics."""
    try:
        start_time = time.time()

        tracer = None
        if OTEL_AVAILABLE and trace and getattr(trace, "get_tracer_provider", None) and trace.get_tracer_provider():
            tracer = trace.get_tracer("buddy.chat")

    # Token-aware context trimming
        if message_data.conversation_id and message_data.conversation_id in memory_storage["conversations"]:
            conv = memory_storage["conversations"][message_data.conversation_id]
            trimmed = trim_messages_token_budget(conv, settings.max_context_tokens)
            memory_storage["conversations"][message_data.conversation_id] = trimmed

        span_ctx = tracer.start_as_current_span("chat_handler") if tracer else None
        with span_ctx if span_ctx else contextlib.nullcontext():
            response_text, confidence = await get_ai_response(message_data.message)

        if message_data.locale and any(word in message_data.message.lower() for word in ["hello", "hi", "hey", "hola", "bonjour"]):
            response_text = translate("greeting", locale=message_data.locale)

        conversation_id = message_data.conversation_id or f"conv_{int(time.time())}"

        if MONGODB_AVAILABLE:
            try:
                db = await get_database()
                uid = message_data.user_id or "default"
                await db.save_conversation(session_id=conversation_id, user_id=uid, role="user", content=message_data.message)
                await db.save_conversation(session_id=conversation_id, user_id=uid, role="assistant", content=response_text)
            except Exception as db_err:
                logger.error("conversation_persist_failed", error=str(db_err))
        else:
            if conversation_id not in memory_storage["conversations"]:
                memory_storage["conversations"][conversation_id] = []
            memory_storage["conversations"][conversation_id].extend([
                {"role": "user", "content": message_data.message, "timestamp": datetime.now().isoformat()},
                {"role": "assistant", "content": response_text, "timestamp": datetime.now().isoformat()}
            ])

        # Token usage analytics (rough)
        tokens_in = count_tokens(message_data.message)
        tokens_out = count_tokens(response_text)
        analytics_record = {
            "type": "token_usage",
            "conversation_id": conversation_id,
            "user_id": message_data.user_id,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total": tokens_in + tokens_out,
            "timestamp": datetime.utcnow().isoformat()
        }
        if MONGODB_AVAILABLE:
            try:
                db = await get_database()
                await db.log_analytics_event("token_usage", user_id=(message_data.user_id or "default"), data=analytics_record)
            except Exception as aerr:
                logger.error("token_analytics_log_failed", error=str(aerr))
        else:
            memory_storage["analytics"].append(analytics_record)

        response_time = time.time() - start_time
        logger.info("chat_completed", ms=int(response_time*1000), tokens_in=tokens_in, tokens_out=tokens_out)

        # Persona augmentation (toggle) - executed after base response creation for layering
        if persona == 'buddy' and BUDDY_PERSONA_AVAILABLE:
            try:
                cache_key = f"{message_data.user_id}:{conversation_id}:{hash(message_data.message)}"
                cached = _persona_cache.get(cache_key)
                if cached and cached.get('augmented'):
                    response_text = cached['augmented']
                else:
                    persona_ctx: Dict[str, Any] = {"user_name": message_data.user_id or "User"}
                    if get_user_profile:
                        try:
                            profile = await get_user_profile(message_data.user_id or "default")  # type: ignore
                            if profile:
                                persona_ctx.update(profile)
                        except Exception:
                            pass
                    mem_service: Optional[MemoryService] = globals().get('memory_service')  # type: ignore
                    ranked: List[Dict[str, Any]] = []
                    if mem_service:
                        try:
                            ranked = await mem_service.retrieve(message_data.user_id or "default", message_data.message, top_k=8)
                        except Exception:
                            pass
                    mem_blocks = await _summarize_ranked_memories(ranked)
                    if mem_blocks['snippets']:
                        persona_ctx['memory_snippets'] = mem_blocks['snippets']
                        persona_ctx['memory_summary'] = mem_blocks['summary']
                    proactive: Dict[str, Any] = {}
                    if MONGODB_AVAILABLE:
                        try:
                            db = await get_database()
                            reminders = await db.get_user_reminders(message_data.user_id or "default")
                            now_utc = datetime.utcnow()
                            upcoming: List[Any] = []
                            overdue: List[Any] = []
                            for r in reminders:
                                due = r.get('due_date') or r.get('due_time')
                                if isinstance(due, str):
                                    try:
                                        due_dt = datetime.fromisoformat(due.replace('Z', '+00:00'))
                                    except Exception:
                                        continue
                                else:
                                    due_dt = due
                                if not due_dt:
                                    continue
                                status = r.get('status', 'active')
                                if due_dt < now_utc and status != 'completed':
                                    overdue.append(r)
                                elif 0 <= (due_dt - now_utc).total_seconds() <= 7200:
                                    upcoming.append(r)
                            if upcoming:
                                first = min(upcoming, key=lambda x: x.get('due_date') or x.get('due_time'))
                                proactive['upcoming_reminders_count'] = len(upcoming)
                                proactive['next_reminder_title'] = first.get('title')
                            if overdue:
                                proactive['overdue_reminders_count'] = len(overdue)
                        except Exception:
                            pass
                    if proactive:
                        persona_ctx['proactive'] = proactive
                    engine = BUDDYIntelligenceEngine(user_profile=persona_ctx, conversation_memory=[])
                    styled = await engine.generate_buddy_response(message_data.message, persona_ctx)
                    formality = persona_ctx.get('formality_level', 0.8)
                    humor = persona_ctx.get('humor_subtlety', 0.0)
                    if humor and humor > 0.5:
                        styled += "\n(Quick aside: staying proactive on your schedule.)"
                    if formality < 0.5:
                        styled = styled.replace('Sir', persona_ctx.get('user_name','')).replace('Madam', persona_ctx.get('user_name',''))
                    augmentation_parts: List[str] = [styled]
                    if mem_blocks['summary']:
                        augmentation_parts.append(f"Context Summary: {mem_blocks['summary']}")
                    if proactive:
                        if proactive.get('overdue_reminders_count'):
                            augmentation_parts.append(f"You have {proactive['overdue_reminders_count']} overdue reminder(s).")
                        if proactive.get('upcoming_reminders_count'):
                            augmentation_parts.append(f"{proactive['upcoming_reminders_count']} coming up soon.")
                    augmented_header = '\n\n'.join(augmentation_parts)[:1500]
                    if styled and styled not in response_text:
                        response_text = f"{augmented_header}\n\n{response_text}"[:4000]
                    _persona_cache.set(cache_key, {"augmented": response_text})
            except Exception:
                pass
        elif persona != 'neutral' and persona != 'buddy':
            # Unknown persona -> neutral fallback
            pass

        return ChatResponse(response=response_text, timestamp=datetime.now().isoformat(), conversation_id=conversation_id, confidence=confidence)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("chat_error", error=str(e))
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
    """Create and schedule a reminder"""
    try:
        reminder_id = f"rem_{int(time.time())}"
        due_date = datetime.fromisoformat(reminder.due_time.replace('Z', '+00:00'))
        delay = (due_date - datetime.now(due_date.tzinfo)).total_seconds()
        if delay > 0:
            def trigger():
                logger.info("reminder_due", id=reminder_id, title=reminder.title)
                if reminder_id in memory_storage["reminders"]:
                    memory_storage["reminders"][reminder_id]["status"] = "completed"
                if MONGODB_AVAILABLE:
                    # best-effort completion update
                    async def _complete():
                        try:
                            db = await get_database()
                            await db.complete_reminder(reminder_id)
                        except Exception:
                            pass
                    asyncio.create_task(_complete())
            scheduler.schedule_at(f"reminder_{reminder_id}", due_date, trigger)

        if MONGODB_AVAILABLE:
            db = await get_database()
            await db.create_reminder(user_id="default", title=reminder.title, description=reminder.description, due_date=due_date)
        else:
            memory_storage["reminders"][reminder_id] = {"title": reminder.title, "description": reminder.description, "due_time": reminder.due_time, "status": "active"}

        return ReminderResponse(id=reminder_id, title=reminder.title, description=reminder.description, due_time=reminder.due_time, status="active")
    except Exception as e:
        logger.error("create_reminder_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create reminder")

from fastapi.responses import StreamingResponse
try:
    from buddy_core.intelligence.buddy_intelligence import BUDDYIntelligenceEngine
    from buddy_core.voice.voice_processor import voice_processor_singleton
    from buddy_core.personality.buddy_personality import personality_singleton
    from buddy_core.personality.profile_service import get_user_profile, update_user_profile
    from buddy_core.util.cache import TTLCache
    BUDDY_PERSONA_AVAILABLE = True
except Exception:
    BUDDY_PERSONA_AVAILABLE = False
    get_user_profile = update_user_profile = None  # type: ignore
try:
    from buddy_core.cross_platform.intelligence_core import intelligence_core_singleton, PlatformContext
    CROSS_PLATFORM_AVAILABLE = True
except Exception:
    CROSS_PLATFORM_AVAILABLE = False

# Enhanced endpoint-specific rate limiter for /chat/universal (Redis-based if available)
_universal_rl: Dict[str, List[float]] = {}
_UNIVERSAL_LIMIT = int(os.getenv("UNIVERSAL_CHAT_LIMIT", "30"))
_UNIVERSAL_WINDOW = int(os.getenv("UNIVERSAL_CHAT_WINDOW", "60"))

def _check_universal_rate(user_id: str):
    """Redis-based distributed rate limiter with in-memory fallback"""
    # Try Redis-based rate limiting first
    if REDIS_AVAILABLE and hasattr(rate_limiter, 'client'):
        try:
            # Use Redis INCR with TTL for atomic rate limiting
            redis_client = getattr(rate_limiter, 'client')
            key = f"universal_rate:{user_id}"
            
            # Lua script for atomic INCR + EXPIRE
            script = """
            local current = redis.call('INCR', KEYS[1])
            if current == 1 then 
                redis.call('EXPIRE', KEYS[1], ARGV[1]) 
            end
            return current
            """
            
            current_count = redis_client.eval(
                script, 
                1, 
                key, 
                _UNIVERSAL_WINDOW
            )
            
            remaining = max(0, _UNIVERSAL_LIMIT - current_count)
            allowed = current_count <= _UNIVERSAL_LIMIT
            
            return allowed, remaining
            
        except Exception as e:
            logger.warning("redis_rate_limit_fallback", error=str(e))
            # Fall through to in-memory implementation
    
    # Fallback to in-memory rate limiting
    now = time.time()
    bucket = _universal_rl.setdefault(user_id, [])
    # prune
    cutoff = now - _UNIVERSAL_WINDOW
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= _UNIVERSAL_LIMIT:
        return False, _UNIVERSAL_LIMIT - len(bucket)
    bucket.append(now)
    return True, _UNIVERSAL_LIMIT - len(bucket)

# Caches (TTL + size limited)
_intent_cache = TTLCache[str, Dict[str, Any]](maxsize=500, ttl_seconds=900)
_persona_cache = TTLCache[str, Dict[str, Any]](maxsize=500, ttl_seconds=1800)

# Memory summarization & compression helpers (heuristic; future: LLM or clustering)
async def _compress_memory_snippets(texts: List[str], max_items: int = 6, max_len: int = 500) -> str:
    seen: set[str] = set()
    distilled: List[str] = []
    for t in texts:
        if not t:
            continue
        frag = t.strip().replace('\n', ' ')
        frag = ' '.join(frag.split())  # collapse whitespace
        short = frag[:120]
        key = short.lower()
        if key in seen:
            continue
        seen.add(key)
        distilled.append(short)
        if len(distilled) >= max_items:
            break
    return ' | '.join(distilled)[:max_len]

async def _summarize_ranked_memories(ranked: List[Dict[str, Any]]) -> Dict[str, str]:
    if not ranked:
        return {"snippets": "", "summary": ""}
    ranked_sorted = sorted(ranked, key=lambda r: r.get('score', 0), reverse=True)
    snippet_lines: List[str] = []
    texts: List[str] = []
    for r in ranked_sorted[:10]:
        t = r.get('text') or ''
        ty = r.get('type', 'mem')
        snippet_lines.append(f"[{ty}] {t}"[:180])
        texts.append(t)
    snippets_block = '\n'.join(snippet_lines)[:1400]
    compressed = await _compress_memory_snippets(texts)
    return {"snippets": snippets_block, "summary": compressed}

@app.post("/chat/stream")
async def chat_stream(message_data: ChatMessage, credentials: HTTPAuthorizationCredentials = Depends()):
    """Basic streaming chat endpoint streaming words."""
    try:
        tracer = None
        if OTEL_AVAILABLE and trace and getattr(trace, "get_tracer_provider", None) and trace.get_tracer_provider():
            tracer = trace.get_tracer("buddy.chat.stream")
        span_ctx = tracer.start_as_current_span("chat_stream") if tracer else None
        with span_ctx if span_ctx else contextlib.nullcontext():
            response_text, confidence = await get_ai_response(message_data.message)
            if BUDDY_PERSONA_AVAILABLE:
                try:
                    conv_id = message_data.conversation_id or "default"
                    cache_key = f"{message_data.user_id}:{conv_id}"
                    persona_ctx: Dict[str, Any] = {"user_name": message_data.user_id or "User"}
                    # Load user profile prefs
                    if get_user_profile:
                        profile = await get_user_profile(message_data.user_id or "default")  # type: ignore
                        persona_ctx.update(profile)
                    # Retrieve top memory items for context (facts + episodes)
                    mem_service = globals().get('memory_service')
                    top_memory: str = ""
                    memory_summary: str = ""
                    if mem_service:
                        try:
                            ranked = await mem_service.retrieve(message_data.user_id or "default", message_data.message, top_k=5)
                            if ranked:
                                top_memory = "\n".join([f"[{r['type']}] {r['text']}" for r in ranked])[:1000]
                                # summarization: naive compression (later LLM summarizer)
                                memory_summary = ("; ".join([r['text'] for r in ranked])[:500])
                                persona_ctx['memory_snippets'] = top_memory
                        except Exception:
                            pass
                    # Proactive signals (reminders upcoming)
                    if MONGODB_AVAILABLE:
                        try:
                            db = await get_database()
                            # Assume db.get_due_reminders(buffer_minutes) exists
                            upcoming = await db.get_due_reminders(buffer_minutes=120)  # next 2h
                            if upcoming:
                                persona_ctx['upcoming_meeting'] = True
                                first = upcoming[0]
                                persona_ctx['meeting_time'] = 'soon'
                        except Exception:
                            pass
                    # Intent cache (very simple TTL not implemented yet)
                    cached = _intent_cache.get(cache_key)
                    if cached and 'styled' in cached:
                        styled = cached['styled']
                    else:
                        engine = BUDDYIntelligenceEngine(user_profile=persona_ctx, conversation_memory=[])
                        styled = await engine.generate_buddy_response(message_data.message, persona_ctx)
                        _intent_cache.set(cache_key, {"styled": styled})
                    # persona preference style switches
                    formality = persona_ctx.get('formality_level', 0.8)
                    humor = persona_ctx.get('humor_subtlety', 0.0)
                    if styled:
                        if humor and humor > 0.5:
                            styled += "\n(An aside: Efficiency remains paramount.)"
                        if formality < 0.5:
                            styled = styled.replace('Sir', persona_ctx.get('user_name','')).replace('Madam', persona_ctx.get('user_name',''))
                    if styled and styled not in response_text:
                        # Prepend styled persona layer and memory summary if present
                        if memory_summary:
                            styled = f"{styled}\n\nContext Summary: {memory_summary}"
                        response_text = f"{styled}\n\n{response_text}"[:3500]
                except Exception:
                    pass

        words = response_text.split()

        async def generator():
            for w in words:
                yield w + " "
                await asyncio.sleep(0.02)

        return StreamingResponse(generator(), media_type="text/plain")
    except HTTPException:
        raise

class UniversalChatRequest(ChatMessage):
    device_type: str = Field("web", max_length=30)
    platform: Optional[str] = Field(None, max_length=50)
    capabilities: Optional[Dict[str, Any]] = None
    device_id: Optional[str] = Field(None, max_length=100)

@app.post("/chat/universal")
async def chat_universal(payload: UniversalChatRequest, credentials: HTTPAuthorizationCredentials = Depends()):
    if not CROSS_PLATFORM_AVAILABLE:
        raise HTTPException(status_code=501, detail="Cross-platform intelligence not available")
    try:
        user_id = payload.user_id or "default"
        allowed, remaining = _check_universal_rate(user_id)
        if not allowed:
            raise HTTPException(status_code=429, detail="Universal chat rate limit exceeded")
        ctx = PlatformContext(device_type=payload.device_type, platform=payload.platform or payload.device_type, capabilities=payload.capabilities or {}, user_id=user_id)
        result = await intelligence_core_singleton.process_universal_input(payload.message, ctx)
        return {
            "response": result.response,
            "personality": result.personality,
            "platform_optimized": result.platform_optimized,
            "voice_config": result.voice_config,
            "ui_adaptations": result.ui_adaptations,
            "memory_summary": result.memory_summary,
            "timestamp": result.timestamp,
            "rate_remaining": remaining
        }
    except Exception as e:
        logger.error("universal_chat_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Universal chat failed")

#########################
# Cross-Platform Routes #
#########################

# Device Registration
class DeviceRegistrationRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    device_type: str = Field(..., min_length=1, max_length=30) 
    capabilities: Optional[Dict[str, Any]] = None
    platform_version: Optional[str] = None

@app.post("/devices/register")
async def register_device(payload: DeviceRegistrationRequest, credentials: HTTPAuthorizationCredentials = Depends()):
    """Register a device for cross-platform sync"""
    if not CROSS_PLATFORM_AVAILABLE:
        raise HTTPException(status_code=501, detail="Cross-platform features not available")
    try:
        # Extract user_id from token if available
        user_id = "default"
        if auth_api:
            try:
                claims = await auth_api.auth_manager.verify_access_token(credentials.credentials)
                if claims:
                    user_id = claims.get("sub", "default")
            except Exception:
                pass
        
        # Import sync engine here to avoid circular imports
        from buddy_core.cross_platform.sync_engine import sync_engine_singleton
        
        device_info = {
            "device_id": payload.device_id,
            "device_type": payload.device_type,
            "capabilities": payload.capabilities or {},
            "platform_version": payload.platform_version,
            "registered_at": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat()
        }
        
        await sync_engine_singleton.register_device(
            user_id, 
            payload.device_id, 
            payload.device_type, 
            payload.capabilities or {}
        )
        
        return {
            "status": "registered",
            "device_id": payload.device_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("device_registration_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Device registration failed")

# Intelligence Metrics
@app.get("/system/intel-metrics")
async def get_intelligence_metrics(claims: Dict = Depends(rbac_required(["admin", "user"]))):
    """Get intelligence core performance metrics"""
    if not CROSS_PLATFORM_AVAILABLE:
        raise HTTPException(status_code=501, detail="Cross-platform features not available")
    try:
        metrics = intelligence_core_singleton.metrics_snapshot()
        return {
            "intelligence_metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("intel_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve intelligence metrics")

# WebSocket Sync
import json
from typing import Set

# Store active WebSocket connections per user
_active_connections: Dict[str, Set[WebSocket]] = {}

@app.websocket("/ws/sync/{user_id}")
async def websocket_sync_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time cross-device synchronization"""
    if not CROSS_PLATFORM_AVAILABLE:
        await websocket.close(code=1011, reason="Cross-platform features not available")
        return
    
    await websocket.accept()
    
    # Add connection to user's active connections
    if user_id not in _active_connections:
        _active_connections[user_id] = set()
    _active_connections[user_id].add(websocket)
    
    try:
        # Import pubsub here to avoid circular imports
        from buddy_core.cross_platform.pubsub import pubsub
        
        # Subscribe to user's sync channel
        subscription_task = None
        
        async def handle_pubsub_message(message: Dict[str, Any]):
            """Handle incoming pubsub messages and forward to WebSocket"""
            try:
                # Only forward messages that are sync-related for this user
                await websocket.send_text(json.dumps({
                    "type": "sync_update",
                    "data": message,
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except Exception as e:
                logger.error("websocket_forward_failed", error=str(e))
        
        # Start subscription in background
        subscription_task = asyncio.create_task(pubsub.subscribe(user_id, handle_pubsub_message))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for incoming WebSocket messages (keepalive, commands, etc.)
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                data = json.loads(message)
                
                # Handle different message types
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                elif data.get("type") == "sync_request":
                    # Client requesting sync status - could send back device list, etc.
                    await websocket.send_text(json.dumps({
                        "type": "sync_status",
                        "status": "connected",
                        "user_id": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_text(json.dumps({
                    "type": "keepalive",
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("websocket_message_error", error=str(e))
                break
                
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", user_id=user_id)
    except Exception as e:
        logger.error("websocket_error", user_id=user_id, error=str(e))
    finally:
        # Clean up connection
        if user_id in _active_connections:
            _active_connections[user_id].discard(websocket)
            if not _active_connections[user_id]:
                del _active_connections[user_id]
        
        # Cancel subscription task
        if subscription_task and not subscription_task.done():
            subscription_task.cancel()
        
        try:
            await websocket.close()
        except Exception:
            pass

########################
# Admin Security Routes #
########################

@app.post("/admin/keys/rotate")
async def rotate_key(new_kid: str, new_secret: str, activate: bool = True, claims: Dict = Depends(rbac_required(["admin"]))):
    if not auth_api:
        raise HTTPException(status_code=500, detail="Auth not initialized")
    await auth_api.auth_manager.rotate_key(new_kid, new_secret, activate=activate)
    return {"status": "ok", "active_kid": auth_api.auth_manager.active_kid}

@app.post("/admin/tokens/revoke-jti")
async def revoke_jti(jti: str, exp: int, claims: Dict = Depends(rbac_required(["admin"]))):
    if not auth_api:
        raise HTTPException(status_code=500, detail="Auth not initialized")
    await auth_api.auth_manager.revoke_jti(jti, exp)
    return {"status": "revoked", "jti": jti}

@app.get("/admin/keys")
async def list_keys(claims: Dict = Depends(rbac_required(["admin"]))):
    if not auth_api:
        raise HTTPException(status_code=500, detail="Auth not initialized")
    return {"keys": list(auth_api.auth_manager.jwt_secrets.keys()), "active": auth_api.auth_manager.active_kid}

@app.get("/admin/audit")
async def get_audit_events(
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None),
    from_ts: Optional[str] = Query(None, description="ISO8601 start datetime"),
    to_ts: Optional[str] = Query(None, description="ISO8601 end datetime"),
    claims: Dict = Depends(rbac_required(["admin"]))
):
    if not auth_api:
        raise HTTPException(status_code=500, detail="Auth not initialized")
    coll = getattr(auth_api.auth_manager, 'audit_events_coll', None)
    if not coll:
        raise HTTPException(status_code=501, detail="Audit collection not configured")
    query: Dict[str, Any] = {}
    if event_type:
        query['event_type'] = event_type
    # Parse datetime filters
    from_dt = to_dt = None
    if from_ts:
        try:
            from_dt = datetime.fromisoformat(from_ts.replace('Z', '+00:00'))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid from_ts format")
    if to_ts:
        try:
            to_dt = datetime.fromisoformat(to_ts.replace('Z', '+00:00'))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid to_ts format")
    if from_dt or to_dt:
        range_q: Dict[str, Any] = {}
        if from_dt:
            range_q['$gte'] = from_dt
        if to_dt:
            range_q['$lte'] = to_dt
        query['timestamp'] = range_q
    cursor = coll.find(query).sort('timestamp', -1).skip(skip).limit(limit)
    results: List[Dict[str, Any]] = []
    async for doc in cursor:
        d = {k: v for k, v in doc.items() if k != '_id'}
        d['id'] = str(doc.get('_id'))
        results.append(d)
    total = await coll.count_documents(query)
    return {"total": total, "count": len(results), "results": results, "query": query}

###############
# RAG (Phase) #
###############

class RAGIngestRequest(BaseModel):
    documents: List[str]
    conversation_id: Optional[str] = None

class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 3

class MemoryFactRequest(BaseModel):
    text: str
    importance: float = 0.5
    tags: Optional[List[str]] = None

class MemoryEpisodeRequest(BaseModel):
    event_type: str
    payload: Dict[str, Any]

class MemoryPurgeRequest(BaseModel):
    id: str
    type: str  # 'fact' or 'episode'

class MemoryDecayRequest(BaseModel):
    user_id: Optional[str] = None
    idle_days: int = 30
    decay: float = 0.05

class UserProfileUpdate(BaseModel):
    preferences: Dict[str, Any]

@app.post("/memory/facts")
async def add_memory_fact(payload: MemoryFactRequest, user_id: str = "default"):
    if not globals().get('memory_service'):
        raise HTTPException(status_code=501, detail="Memory service not available")
    fact_id = await globals()['memory_service'].add_fact(user_id, payload.text, payload.importance, payload.tags)
    return {"id": fact_id, "status": "stored"}

@app.get("/memory/facts")
async def list_memory_facts(user_id: str = "default", limit: int = 20):
    if not globals().get('memory_service'):
        raise HTTPException(status_code=501, detail="Memory service not available")
    facts = await globals()['memory_service'].list_facts(user_id, limit)
    return {"facts": facts}

@app.post("/memory/episodes")
async def add_memory_episode(payload: MemoryEpisodeRequest, user_id: str = "default"):
    if not globals().get('memory_service'):
        raise HTTPException(status_code=501, detail="Memory service not available")
    eid = await globals()['memory_service'].add_episode(user_id, payload.event_type, payload.payload)
    return {"id": eid, "status": "stored"}

@app.get("/memory/episodes")
async def list_memory_episodes(user_id: str = "default", limit: int = 50):
    if not globals().get('memory_service'):
        raise HTTPException(status_code=501, detail="Memory service not available")
    eps = await globals()['memory_service'].list_episodes(user_id, limit)
    return {"episodes": eps}

@app.get("/memory/search")
async def search_memory(query: str, user_id: str = "default", top_k: int = 5, include: str = "facts,episodes"):
    if not globals().get('memory_service'):
        raise HTTPException(status_code=501, detail="Memory service not available")
    include_types = [t.strip() for t in include.split(',') if t.strip()]
    svc = globals()['memory_service']
    results = await svc.search(user_id, query, top_k=top_k, include=include_types)
    # mark used for retrieved facts if metadata includes fact_id
    for fact in results.get('facts', []):
        meta = fact.get('metadata') if isinstance(fact, dict) else None
        if meta and meta.get('fact_id'):
            try:
                await svc.mark_used(meta.get('fact_id'))
            except Exception:
                pass
    return {"results": results, "include": include_types}

@app.get("/memory/retrieve")
async def retrieve_memory(query: str, user_id: str = "default", top_k: int = 10):
    svc = globals().get('memory_service')
    if not svc:
        raise HTTPException(status_code=501, detail="Memory service not available")
    ranked = await svc.retrieve(user_id, query, top_k=top_k)
    for item in ranked:
        meta = item.get('metadata') or {}
        if item.get('type') == 'fact' and meta.get('fact_id'):
            await svc.mark_used(meta['fact_id'])
        elif item.get('type') == 'episode' and meta.get('episode_id'):
            await svc.mark_episode_used(meta['episode_id'])
    return {"query": query, "items": ranked}

@app.post("/memory/decay")
async def decay_memory(payload: MemoryDecayRequest):
    svc = globals().get('memory_service')
    if not svc:
        raise HTTPException(status_code=501, detail="Memory service not available")
    updated = await svc.decay_importance(user_id=payload.user_id, idle_days=payload.idle_days, decay=payload.decay)
    return {"updated": updated}

@app.post("/memory/purge")
async def purge_memory(payload: MemoryPurgeRequest):
    svc = globals().get('memory_service')
    if not svc:
        raise HTTPException(status_code=501, detail="Memory service not available")
    ok = await svc.purge(payload.id, payload.type)
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found or not deleted")
    return {"purged": True, "id": payload.id, "type": payload.type}

@app.get("/system/cache-stats")
async def cache_stats():
    return {
        "intent": _intent_cache.stats() if hasattr(_intent_cache, 'stats') else {},
        "persona": _persona_cache.stats() if hasattr(_persona_cache, 'stats') else {},
        "persona_available": BUDDY_PERSONA_AVAILABLE
    }

@app.get("/user/profile")
async def get_profile(user_id: str = "default"):
    if not BUDDY_PERSONA_AVAILABLE or not get_user_profile:
        return {"user_id": user_id, "preferences": {}, "source": "disabled"}
    prof = await get_user_profile(user_id)  # type: ignore
    return prof

@app.post("/user/profile")
async def update_profile(payload: UserProfileUpdate, user_id: str = "default"):
    if not BUDDY_PERSONA_AVAILABLE or not update_user_profile:
        raise HTTPException(status_code=501, detail="Personality profile service unavailable")
    prof = await update_user_profile(user_id, payload.preferences)  # type: ignore
    return prof

@app.post("/rag/ingest")
async def rag_ingest(payload: RAGIngestRequest, claims: Dict = Depends(rbac_required(["admin", "user"]))):
    added = 0
    for doc in payload.documents:
        try:
            semantic_index.add(doc)
            added += 1
        except Exception as e:
            logger.error("rag_ingest_failed", error=str(e))
    return {"ingested": added}

@app.post("/rag/query")
async def rag_query(payload: RAGQueryRequest):
    try:
        results = semantic_index.search(payload.query, top_k=payload.top_k)
        return {"query": payload.query, "results": [{"text": t, "score": s} for t, s in results]}
    except Exception as e:
        logger.error("rag_query_failed", error=str(e))
        raise HTTPException(status_code=500, detail="RAG query failed")

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
                # Rebind bow vector index with persistence if selected
                if backend_key == 'bow':
                    try:
                        from mongodb_integration import _db_client  # type: ignore
                        if _db_client:
                            from vector.semantic_index import BowVectorIndex
                            global semantic_index
                            semantic_index = BowVectorIndex(mongo_client=_db_client)
                            logger.info("BowVectorIndex now using Mongo persistence")
                    except Exception as e:
                        logger.warning("bow_vector_persistence_bind_failed", error=str(e))
                # Initialize memory service
                try:
                    from mongodb_integration import _db_client  # type: ignore
                    if _db_client:
                        from packages.core.buddy.memory.memory_service import MemoryService, memory_service as _ms
                        if _ms is None:
                            from mongodb_integration import get_database as _getdb  # type: ignore
                            db = await _getdb()
                            # Create memory service instance
                            from packages.core.buddy.memory.memory_service import memory_service as ms_ref
                            globals()['memory_service'] = MemoryService(db)
                            logger.info("MemoryService initialized")
                except Exception as e:
                    logger.warning("memory_service_init_failed", error=str(e))
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

    # Restore due reminder scheduling (Mongo)
    if MONGODB_AVAILABLE:
        try:
            db = await get_database()
            # Fire or mark any past-due reminders (missed while offline)
            missed = await db.get_due_reminders(buffer_minutes=0)
            handled_missed = 0
            for r in missed:
                rid = str(r.get('_id'))
                run_at = r.get('due_date')
                if run_at and run_at <= datetime.utcnow():
                    # mark completed (simulating immediate fire)
                    await db.complete_reminder(rid)
                    logger.info("reminder_missed_completed", id=rid, title=r.get('title'))
                    handled_missed += 1
            # Schedule upcoming reminders (next 24h)
            upcoming = await db.get_due_reminders(buffer_minutes=1440)
            scheduled = 0
            for r in upcoming:
                rid = str(r.get('_id'))
                run_at = r.get('due_date')
                if run_at and run_at > datetime.utcnow():
                    def make_trigger(rem_id, title):
                        def trigger():
                            logger.info("reminder_due", id=rem_id, title=title)
                            # update DB status
                            asyncio.create_task(db.complete_reminder(rem_id))
                        return trigger
                    scheduler.schedule_at(f"reminder_{rid}", run_at, make_trigger(rid, r.get('title')))
                    scheduled += 1
            logger.info("reminder_restore_summary", missed_completed=handled_missed, upcoming_scheduled=scheduled)
        except Exception as e:
            logger.error("restore_reminders_failed", error=str(e))

    logger.info("🎉 BUDDY Cloud Backend started successfully!")

if settings.environment != 'production':
    @app.get("/auth/test-token")
    async def get_test_token(user_id: str = "test_user", roles: str = "user"):
        import jwt, time
        now = int(time.time())
        claims = {
            "sub": user_id,
            "device_id": "dev-test",
            "device_type": "web",
            "iat": now,
            "exp": now + 1800,
            "iss": "buddy-ai",
            "aud": "buddy-api",
            "roles": roles.split(",") if roles else ["user"]
        }
        token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
        return {"access_token": token}

# Error handlers
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content=error_response(
        code=ErrorCodes.INTERNAL_ERROR if exc.status_code >=500 else ErrorCodes.VALIDATION_ERROR,
        message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        request=request,
        status_code=exc.status_code
    ))

@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc))
    return JSONResponse(status_code=500, content=error_response(
        code=ErrorCodes.INTERNAL_ERROR,
        message="Internal server error",
        request=request
    ))

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
    # Auto-configure for cloud environment
    auto_configure()
    
    # Get universal server configuration
    server_config = get_server_config()
    host = server_config['host']
    port = server_config['port']
    
    # Print startup banner with all URLs
    print_startup_banner()
    
    # Start server with universal configuration
    logger.info("🌐 Starting BUDDY Cloud Backend", host=host, port=port, environment=server_config['environment'])
    
    with universal_port_manager.managed_server() as config:
        uvicorn.run(
            "cloud_backend:app", 
            host=host, 
            port=port, 
            log_level="info", 
            reload=False,
            access_log=True
        )
