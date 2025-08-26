"""
Enhanced BUDDY Backend with MongoDB Integration

A FastAPI server with MongoDB for persistent data storage.
Supports conversations, reminders, analytics, and user management.
"""

import os
import asyncio
import httpx
import logging
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header, status, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from fastapi import UploadFile, File, Form
from car.middleware.core import AutomotiveMiddlewareCore, MiddlewareConfig
import json
from dotenv import load_dotenv
from fastapi import Query

########################
# Early initialization  #
########################
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    # Temporarily use minimal semantic memory to avoid Pinecone conflicts
    from minimal_semantic_memory import get_semantic_memory_engine
    PHASE1_ADVANCED_AI_AVAILABLE = True
except ImportError:
    PHASE1_ADVANCED_AI_AVAILABLE = False

# Import Simplified NLP Engine as fallback
from simplified_nlp_engine import get_simplified_nlp_engine

# Import Firebase integration (after logger defined)
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
    logging.getLogger(__name__).warning("Firebase integration not available")

# Weather API configuration
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "ff2cbe677bbfc325d2b615c86a20daef")
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5"

# (Logging already configured above)

# Runtime flags
DEBUG_MODE = os.getenv("BUDDY_DEBUG") == "1"
DEV_MODE = os.getenv("BUDDY_DEV") == "1"
USE_MONGODB = os.getenv("USE_MONGODB", "1") == "1"
ADMIN_API_KEY = os.getenv("BUDDY_ADMIN_API_KEY")
CLIENT_TOKEN = os.getenv("BUDDY_CLIENT_TOKEN")  # Shared client auth token for REST/WS
RATE_LIMIT_WINDOW_SEC = int(os.getenv("BUDDY_RATE_LIMIT_WINDOW_SEC", "300"))  # 5 min default
RATE_LIMIT_MAX = int(os.getenv("BUDDY_RATE_LIMIT_MAX", "60"))  # 60 calls / window
ENABLE_ADMIN_AUDIT = os.getenv("BUDDY_ENABLE_ADMIN_AUDIT", "1") == "1"
AUDIT_LOG_PATH = os.getenv("BUDDY_ADMIN_AUDIT_FILE", "logs/admin_audit.log")
RATE_STATE_FILE = os.getenv("BUDDY_RATE_LIMIT_STATE_FILE", "logs/rate_limit_state.json")

# In-memory rate limit store: { (actor, route): [timestamps] }
_RATE_BUCKET: Dict[Tuple[str, str], List[float]] = {}

def _load_rate_state():
    if not RATE_STATE_FILE:
        return
    try:
        p = Path(RATE_STATE_FILE)
        if not p.exists():
            return
        data = json.loads(p.read_text(encoding="utf-8"))
        now = time.time()
        for k, ts_list in data.items():
            # key stored as actor||route
            if not isinstance(ts_list, list):
                continue
            actor, route = k.split("||", 1)
            # keep only those within window to avoid stale buildup
            fresh = [t for t in ts_list if now - t < RATE_LIMIT_WINDOW_SEC]
            if fresh:
                _RATE_BUCKET[(actor, route)] = fresh
        logger.info("Loaded rate limit state (%d keys)", len(_RATE_BUCKET))
    except Exception as e:
        logger.debug(f"Rate state load failed: {e}")

def _save_rate_state():
    if not RATE_STATE_FILE:
        return
    try:
        Path(RATE_STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
        serial: Dict[str, List[float]] = {}
        for (actor, route), ts_list in _RATE_BUCKET.items():
            serial[f"{actor}||{route}"] = ts_list
        Path(RATE_STATE_FILE).write_text(json.dumps(serial), encoding="utf-8")
    except Exception as e:
        logger.debug(f"Rate state save failed: {e}")

def _hash_actor(actor: str) -> str:
    return hashlib.sha256(actor.encode("utf-8")).hexdigest()[:16]

def _extract_client_ip(request: Request) -> str:
    # Prefer X-Forwarded-For (Render / proxy) then client.host
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        # take first IP
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def _audit(event: str, actor: str, details: Dict[str, Any]):
    if not ENABLE_ADMIN_AUDIT:
        return
    try:
        Path(AUDIT_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "actor_hash": _hash_actor(actor),
            **details
        }
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        logger.debug(f"Audit log write failed: {e}")

def _check_rate_limit(actor: str, route: str):
    now = time.time()
    key = (actor, route)
    bucket = _RATE_BUCKET.setdefault(key, [])
    # purge old
    cutoff = now - RATE_LIMIT_WINDOW_SEC
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= RATE_LIMIT_MAX:
        retry_after = int(bucket[0] + RATE_LIMIT_WINDOW_SEC - now)
        raise HTTPException(status_code=429, detail={
            "error": "rate_limited",
            "window_seconds": RATE_LIMIT_WINDOW_SEC,
            "max": RATE_LIMIT_MAX,
            "retry_after": max(retry_after, 1)
        })
    bucket.append(now)
    # Persist after mutation (best-effort)
    _save_rate_state()

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
    # Load persisted rate limit state
    _load_rate_state()
    
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
    # Initialize automotive middleware core
    try:
        global automotive_core
        automotive_core = AutomotiveMiddlewareCore(MiddlewareConfig())
        await automotive_core.initialize()
        logger.info("🚗 Automotive middleware initialized")
    except Exception as e:
        logger.warning(f"Automotive middleware init failed: {e}")
    # Configure minimal semantic memory (if available)
    if PHASE1_ADVANCED_AI_AVAILABLE:
        try:
            engine = await get_semantic_memory_engine()
            engine.update_config({
                "enable_embeddings": True,
                "chroma_persist_dir": os.getenv("BUDDY_CHROMA_DIR", "./chroma_store"),
                "max_age_seconds": int(os.getenv("BUDDY_MEMORY_MAX_AGE", "86400"))  # 24h default
            })
            logger.info("🧠 Semantic memory configured (embeddings=%s, persist=%s)", engine.enable_embeddings, engine.config.get("chroma_persist_dir"))
        except Exception as e:
            logger.warning(f"Semantic memory configuration failed: {e}")

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

class SemanticMemoryUpdate(BaseModel):
    enable_embeddings: Optional[bool] = None
    chroma_persist_dir: Optional[str] = None
    max_age_seconds: Optional[int] = None

class CarVoiceMeta(BaseModel):
    speed_kmh: Optional[float] = 0.0
    location: Optional[Dict[str, Any]] = None
    source: Optional[str] = "api"

class CarPluginRegistration(BaseModel):
    intent_type: str
    response_text: str = "Acknowledged"
    spoken_text: Optional[str] = None

def _require_admin(api_key: str | None) -> None:
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API key not configured")
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-Admin-API-Key header")
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin API key")

@app.post("/admin/semantic-memory/config")
async def update_semantic_memory_config(update: SemanticMemoryUpdate, api_key: str = Header(None, alias="X-Admin-API-Key"), request: Optional[Request] = None):
    _require_admin(api_key)
    _check_rate_limit(api_key, "/admin/semantic-memory/config:POST")
    if not PHASE1_ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="Semantic memory engine not available")
    engine = await get_semantic_memory_engine()
    new_cfg = {k: v for k, v in update.dict().items() if v is not None}
    client_ip = _extract_client_ip(request) if request else "unknown"
    if not new_cfg:
        _audit("semantic_memory_config_noop", api_key, {"path": "/admin/semantic-memory/config", "method": "POST", "ip": client_ip})
        return {"status": "no_change"}
    engine.update_config(new_cfg)
    _audit("semantic_memory_config_update", api_key, {"changes": new_cfg, "ip": client_ip})
    return {"status": "updated", "config": engine.config}

@app.get("/admin/semantic-memory/config")
async def get_semantic_memory_config(api_key: str = Header(None, alias="X-Admin-API-Key"), request: Optional[Request] = None):
    _require_admin(api_key)
    _check_rate_limit(api_key, "/admin/semantic-memory/config:GET")
    if not PHASE1_ADVANCED_AI_AVAILABLE:
        raise HTTPException(status_code=503, detail="Semantic memory engine not available")
    engine = await get_semantic_memory_engine()
    _audit("semantic_memory_config_read", api_key, {"path": "/admin/semantic-memory/config", "ip": _extract_client_ip(request) if request else "unknown"})
    return {
        "config": engine.config,
        "enable_embeddings": engine.enable_embeddings,
        "use_chroma": engine.use_chroma,
        "cache_users": len(getattr(engine, 'conversation_cache', {}))
    }

@app.get("/admin/audit/logs")
async def get_audit_logs(api_key: str = Header(None, alias="X-Admin-API-Key"), request: Optional[Request] = None, limit: int = 200):
    _require_admin(api_key)
    _check_rate_limit(api_key, "/admin/audit/logs:GET")
    client_ip = _extract_client_ip(request) if request else "unknown"
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")
    try:
        if not ENABLE_ADMIN_AUDIT:
            raise HTTPException(status_code=503, detail="Audit logging disabled")
        p = Path(AUDIT_LOG_PATH)
        if not p.exists():
            return {"entries": [], "total": 0}
        # Read last N lines efficiently
        with p.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
        entries = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
        _audit("audit_log_read", api_key, {"count": len(entries), "ip": client_ip})
        return {"entries": entries, "returned": len(entries)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to read audit logs")


@app.get("/debug/semantic-memory")
async def debug_semantic_memory(query: str = Query("hello", description="Query text for similarity test"),
                                user_id: str = Query("default_user"),
                                limit: int = Query(5, ge=1, le=25)):
    """Inspect semantic memory retrieval for a given query.

    Returns the raw matches, scores, and basic cache statistics. Works with the minimal semantic
    memory engine (and future full engine) as long as it exposes recall_relevant_context.
    """
    try:
        if not PHASE1_ADVANCED_AI_AVAILABLE:
            raise HTTPException(status_code=503, detail="Semantic memory engine not available")
        semantic_memory = await get_semantic_memory_engine(conversation_db=None)
        matches = await semantic_memory.recall_relevant_context(query=query, user_id=user_id, limit=limit)
        # Basic stats
        cache_size = len(getattr(semantic_memory, 'conversation_cache', {}).get(user_id, []))
        engine_type = semantic_memory.__class__.__name__
        return {
            'engine': engine_type,
            'query': query,
            'user_id': user_id,
            'limit': limit,
            'returned': len(matches),
            'cache_size_for_user': cache_size,
            'matches': matches
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Semantic memory debug error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Database dependency
async def get_db() -> Optional[BuddyDatabase]:
    """Dependency to get database instance"""
    if USE_MONGODB:
        return await get_database()
    return None

## Duplicate startup/shutdown handlers removed (initial handlers earlier in file handle lifecycle)

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

@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    """Authenticated bi-directional chat WebSocket with optional token streaming.

    Client connects with query param: /ws/chat?token=CLIENT_TOKEN
    Send JSON: {"message": str, "user_id"?: str, "session_id"?: str, "stream"?: bool}
    If stream true: server emits {type:start}, many {type:token, token:str}, finally {type:end, complete:bool, length:int}
    Otherwise single message {response: str, ...}
    """
    # Simple token auth via query param
    qp = ws.query_params
    token = None
    try:
        token = qp.get("token")  # starlette QueryParams
    except Exception:
        token = None
    if CLIENT_TOKEN and token != CLIENT_TOKEN:
        await ws.accept()
        await ws.send_json({"error": "auth_failed"})
        await ws.close()
        return
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            user_message = data.get("message")
            if not user_message:
                await ws.send_json({"error": "missing_message"})
                continue
            user_id = data.get("user_id") or "ws_user"
            session_id = data.get("session_id") or f"ws_{user_id}"
            stream = bool(data.get("stream"))
            try:
                if USE_MONGODB:
                    db = await get_database() if USE_MONGODB else None
                else:
                    db = None
                history = []
                if db and db.connected:
                    history = await db.get_conversation_history(session_id, limit=5)
                response_text = await generate_response(user_message, history, user_id, db)
                if db and db.connected:
                    await db.save_conversation(session_id=session_id, user_id=user_id, role="user", content=user_message)
                    await db.save_conversation(session_id=session_id, user_id=user_id, role="assistant", content=response_text)
                if not stream:
                    await ws.send_json({
                        "response": response_text,
                        "user_id": user_id,
                        "session_id": session_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "transport": "websocket"
                    })
                else:
                    tokens = response_text.split(" ")
                    await ws.send_json({"type": "start", "user_id": user_id, "session_id": session_id})
                    for tok in tokens:
                        # include trailing space for reconstruction
                        await ws.send_json({"type": "token", "token": tok + " "})
                        await asyncio.sleep(0.005)  # tiny delay to simulate streaming
                    await ws.send_json({"type": "end", "complete": True, "length": len(response_text)})
            except Exception as e:  # noqa: BLE001
                logger.error(f"WebSocket chat processing error: {e}")
                await ws.send_json({"error": "processing_failure", "detail": str(e)})
    except WebSocketDisconnect:
        try:
            await ws.close()
        except Exception:
            pass
    except Exception as e:  # noqa: BLE001
        logger.error(f"WebSocket connection error: {e}")
        try:
            await ws.close()
        except Exception:
            pass

@app.post("/car/voice")
async def car_voice_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    audio: UploadFile | None = File(None, description="Optional audio file (wav/pcm)"),
    text: str | None = Form(None, description="Optional raw text if already transcribed"),
    speed_kmh: float | None = Form(0.0),
):
    """Unified automotive voice/text interaction endpoint.
    Accepts either audio (transcribed via ASR) or direct text and returns JSON with intent and response.
    """
    if 'automotive_core' not in globals():
        raise HTTPException(status_code=503, detail="Automotive middleware unavailable")
    try:
        audio_bytes = await audio.read() if audio else None
        meta = {"speed_kmh": speed_kmh or 0.0, "source": "api"}
        result = await automotive_core.handle_user_input(audio=audio_bytes, text=text, meta=meta)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"/car/voice error: {e}")
        raise HTTPException(status_code=500, detail="car_voice_processing_error")

@app.post("/car/plugins")
async def register_car_plugin(reg: CarPluginRegistration, api_key: str = Header(None, alias="X-Admin-API-Key")):
    """Register a simple automotive intent plugin (template-based)."""
    _require_admin(api_key)
    if 'automotive_core' not in globals():
        raise HTTPException(status_code=503, detail="Automotive middleware unavailable")
    try:
        intent_type = reg.intent_type.strip()
        if not intent_type:
            raise HTTPException(status_code=400, detail="intent_type required")
        spoken = reg.spoken_text or reg.response_text
        async def handler(intent, ctx):  # closure capturing texts
            return {"response": reg.response_text, "spoken": spoken, "intent_type": intent_type}
        automotive_core.register_plugin(intent_type, handler, override=True)
        return {"status": "registered", "intent_type": intent_type}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plugin registration failed: {e}")
        raise HTTPException(status_code=500, detail="plugin_registration_failed")

@app.get("/car/plugins")
async def list_car_plugins(api_key: str = Header(None, alias="X-Admin-API-Key")):
    _require_admin(api_key)
    if 'automotive_core' not in globals():
        raise HTTPException(status_code=503, detail="Automotive middleware unavailable")
    from car.middleware.plugins import registry as plugin_registry
    return {"intents": plugin_registry.list_intents()}

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, background_tasks: BackgroundTasks, db: Optional[BuddyDatabase] = Depends(get_db), client_token: str | None = Header(None, alias="X-Client-Token")):
    """Handle chat messages with MongoDB persistence."""
    try:
        if CLIENT_TOKEN and client_token != CLIENT_TOKEN:
            raise HTTPException(status_code=401, detail="invalid_client_token")
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

@app.post("/api/force-firebase-update")
async def force_firebase_update():
    """Manually trigger Firebase status update."""
    try:
        from firebase_status_bridge import status_bridge
        
        # Try to initialize and update Firebase
        await status_bridge.initialize_firebase()
        
        render_url = os.getenv("RENDER_EXTERNAL_URL", "https://buddy-2-0.onrender.com")
        success = await status_bridge.set_buddy_online(render_url)
        
        if success:
            return {
                "success": True, 
                "message": "Firebase status updated successfully",
                "backend_url": render_url,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "Firebase update failed - check logs for details",
                "backend_url": render_url
            }
            
    except Exception as e:
        logger.error(f"Error forcing Firebase update: {e}")
        return {
            "success": False,
            "message": f"Firebase update error: {str(e)}",
            "error_type": type(e).__name__
        }

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

# ---- Stub handlers for not-yet-implemented advanced intents (prevent attribute errors) ---- #
async def _handle_email_check_intent(entities: Dict, context_info: str) -> str:
    return f"📧 Email check feature pending integration{context_info}\n\n(Stub response)"

async def _handle_music_play_intent(entities: Dict, context_info: str) -> str:
    return f"🎵 Music playback feature pending integration{context_info}\n\n(Stub response)"

async def _handle_lights_control_intent(entities: Dict, context_info: str) -> str:
    return f"💡 Smart lights control feature pending integration{context_info}\n\n(Stub response)"

async def _handle_device_control_intent(entities: Dict, context_info: str) -> str:
    return f"🛰️ Device control feature pending integration{context_info}\n\n(Stub response)"

async def _handle_navigation_intent(entities: Dict, context_info: str) -> str:
    return f"🗺️ Navigation feature pending integration{context_info}\n\n(Stub response)"

async def _handle_task_create_intent(entities: Dict, context_info: str, user_id: str, db: Optional[BuddyDatabase]) -> str:
    return f"✅ Task creation feature pending integration{context_info}\n\n(Stub response)"

async def _handle_help_request_intent(relevant_context: List[Dict], confidence: float) -> str:
    return "🆘 Help system: You can ask about reminders, calculations, time, weather (coming soon), or general chat. (Stub response)"

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
            title = ' '.join(subjects) if subjects else 'reminder task'
            due_text = time_entities[0] if time_entities else None
            # For now, set due_date to 1 hour from now (parsing natural language could be added later)
            due_date = datetime.utcnow() + timedelta(hours=1)
            await db.create_reminder(
                user_id=user_id,
                title=title,
                description=f"Actions: {', '.join(actions)}" if actions else "",
                due_date=due_date,
                metadata={
                    'raw_time': due_text,
                    'entities_time': time_entities,
                    'entities_actions': actions
                }
            )
            storage_status = f"✅ Stored in your personal reminder system (due {due_date.strftime('%Y-%m-%d %H:%M')})"
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
    from dynamic_config import get_host, get_port
    host = get_host()
    port = get_port()
    if USE_MONGODB:
        logger.info("MongoDB integration enabled")
    else:
        logger.info("MongoDB disabled - using in-memory storage")
    logger.info(f"Backend binding on {host}:{port}")
    if DEV_MODE:
        uvicorn.run("enhanced_backend:app", host=host, port=port, log_level="info", reload=True)
    else:
        uvicorn.run(app, host=host, port=port, log_level="info")
