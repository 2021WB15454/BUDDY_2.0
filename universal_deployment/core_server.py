"""
BUDDY Universal Core Server
Production-grade FastAPI server with cross-device memory synchronization
"""

import os
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

import redis.asyncio as redis
import chromadb
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, text, select, insert, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic import BaseModel, Field
import structlog
from prometheus_client import Counter, Histogram, generate_latest
import hashlib
import json

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(30),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Metrics
REQUEST_COUNT = Counter('buddy_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('buddy_request_duration_seconds', 'Request duration')
SYNC_OPERATIONS = Counter('buddy_sync_operations_total', 'Sync operations', ['type', 'status'])

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://buddy:buddy_secure_2025@localhost:5432/buddydb")
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8001"))
JWT_SECRET = os.getenv("JWT_SECRET", "buddy_jwt_secret_2025")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "30"))

# Database setup
engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis setup
redis_client = None

# ChromaDB setup
chroma_client = None
memory_collection = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info("WebSocket connected", user_id=user_id)
        
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info("WebSocket disconnected", user_id=user_id)
        
    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Remove stale connections
                    self.active_connections[user_id].remove(connection)

manager = ConnectionManager()

# Pydantic models
class DeviceInfo(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(..., description="Human-readable device name")
    device_type: str = Field(..., description="Device type: mobile, desktop, watch, car, tv")
    platform: str = Field(..., description="Platform: android, ios, windows, macos, linux")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatMessage(BaseModel):
    text: str = Field(..., description="Message text")
    device_id: str = Field(..., description="Originating device ID")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context: Dict[str, Any] = Field(default_factory=dict)

class TaskCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = Field(default="medium", regex="^(low|medium|high|urgent)$")
    category: Optional[str] = None
    device_id: str = Field(..., description="Creating device ID")

class SyncRequest(BaseModel):
    device_id: str
    last_sync: Optional[datetime] = None
    sync_types: List[str] = Field(default=["conversations", "tasks", "preferences"])

class UserPreference(BaseModel):
    key: str
    value: Any
    device_specific: bool = False
    device_id: Optional[str] = None

# Dependency injection
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_redis():
    global redis_client
    if not redis_client:
        redis_client = redis.from_url(REDIS_URL)
    return redis_client

async def get_chroma():
    global chroma_client, memory_collection
    if not chroma_client:
        chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        memory_collection = chroma_client.get_or_create_collection("buddy_memory")
    return memory_collection

# Startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting BUDDY Universal Core")
    
    # Initialize connections
    global redis_client, chroma_client, memory_collection
    redis_client = redis.from_url(REDIS_URL)
    try:
        chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        memory_collection = chroma_client.get_or_create_collection("buddy_memory")
        logger.info("Connected to ChromaDB")
    except Exception as e:
        logger.error("Failed to connect to ChromaDB", error=str(e))
    
    # Start background sync task
    sync_task = asyncio.create_task(background_sync_task())
    
    yield
    
    # Shutdown
    sync_task.cancel()
    if redis_client:
        await redis_client.close()
    logger.info("BUDDY Universal Core shutdown complete")

# FastAPI app
app = FastAPI(
    title="BUDDY Universal Core",
    description="Production-grade AI assistant with cross-device memory synchronization",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
@app.get("/")
async def root():
    return {
        "status": "BUDDY Universal Core Running 🚀",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint for load balancers"""
    try:
        # Check database
        result = await db.execute(text("SELECT 1"))
        db_status = "healthy" if result else "unhealthy"
        
        # Check Redis
        redis_conn = await get_redis()
        await redis_conn.ping()
        redis_status = "healthy"
        
        return {
            "status": "healthy",
            "database": db_status,
            "redis": redis_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.post("/api/v1/devices/register")
async def register_device(device: DeviceInfo, db: AsyncSession = Depends(get_db)):
    """Register a new device for a user"""
    try:
        # For demo, using a default user. In production, get from JWT token
        user_id = "550e8400-e29b-41d4-a716-446655440000"  # Default UUID
        
        query = text("""
            INSERT INTO devices (user_id, device_id, device_name, device_type, platform, metadata)
            VALUES (:user_id, :device_id, :device_name, :device_type, :platform, :metadata)
            ON CONFLICT (device_id) 
            DO UPDATE SET 
                device_name = EXCLUDED.device_name,
                device_type = EXCLUDED.device_type,
                platform = EXCLUDED.platform,
                metadata = EXCLUDED.metadata,
                last_seen = CURRENT_TIMESTAMP
            RETURNING id
        """)
        
        result = await db.execute(query, {
            "user_id": user_id,
            "device_id": device.device_id,
            "device_name": device.device_name,
            "device_type": device.device_type,
            "platform": device.platform,
            "metadata": json.dumps(device.metadata)
        })
        
        await db.commit()
        device_record_id = result.scalar()
        
        logger.info("Device registered", device_id=device.device_id, type=device.device_type)
        
        return {
            "status": "registered",
            "device_id": device.device_id,
            "internal_id": str(device_record_id)
        }
        
    except Exception as e:
        await db.rollback()
        logger.error("Device registration failed", error=str(e))
        raise HTTPException(status_code=500, detail="Device registration failed")

@app.post("/api/v1/chat")
async def chat_endpoint(
    message: ChatMessage, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Process chat message and sync across devices"""
    REQUEST_COUNT.labels(method="POST", endpoint="/chat").inc()
    
    try:
        # For demo, using default user
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Store conversation in database
        conversation_id = str(uuid.uuid4())
        
        # User message
        await db.execute(text("""
            INSERT INTO conversations (id, user_id, session_id, message_text, message_type, context)
            VALUES (:id, :user_id, :session_id, :message_text, :message_type, :context)
        """), {
            "id": conversation_id,
            "user_id": user_id,
            "session_id": message.session_id,
            "message_text": message.text,
            "message_type": "user",
            "context": json.dumps(message.context)
        })
        
        # Generate AI response (simplified for demo)
        ai_response = f"BUDDY received: {message.text}"
        
        # Assistant message
        response_id = str(uuid.uuid4())
        await db.execute(text("""
            INSERT INTO conversations (id, user_id, session_id, message_text, message_type, context)
            VALUES (:id, :user_id, :session_id, :message_text, :message_type, :context)
        """), {
            "id": response_id,
            "user_id": user_id,
            "session_id": message.session_id,
            "message_text": ai_response,
            "message_type": "assistant",
            "context": json.dumps({"device_id": message.device_id})
        })
        
        await db.commit()
        
        # Store embeddings in ChromaDB
        background_tasks.add_task(store_embeddings, message.text, conversation_id)
        
        # Notify other devices via WebSocket
        await manager.send_personal_message(
            json.dumps({
                "type": "new_message",
                "session_id": message.session_id,
                "message": ai_response,
                "device_id": message.device_id
            }),
            user_id
        )
        
        logger.info("Chat processed", session_id=message.session_id, device_id=message.device_id)
        
        return {
            "response": ai_response,
            "session_id": message.session_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        await db.rollback()
        logger.error("Chat processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Chat processing failed")

@app.post("/api/v1/tasks")
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new task"""
    try:
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        task_id = str(uuid.uuid4())
        
        await db.execute(text("""
            INSERT INTO tasks (id, user_id, title, description, due_date, priority, category)
            VALUES (:id, :user_id, :title, :description, :due_date, :priority, :category)
        """), {
            "id": task_id,
            "user_id": user_id,
            "title": task.title,
            "description": task.description,
            "due_date": task.due_date,
            "priority": task.priority,
            "category": task.category
        })
        
        await db.commit()
        
        # Notify devices
        await manager.send_personal_message(
            json.dumps({
                "type": "task_created",
                "task_id": task_id,
                "title": task.title,
                "device_id": task.device_id
            }),
            user_id
        )
        
        return {"task_id": task_id, "status": "created"}
        
    except Exception as e:
        await db.rollback()
        logger.error("Task creation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Task creation failed")

@app.post("/api/v1/sync")
async def sync_data(sync_req: SyncRequest, db: AsyncSession = Depends(get_db)):
    """Sync data for a specific device"""
    try:
        user_id = "550e8400-e29b-41d4-a716-446655440000"
        sync_data = {}
        
        # Sync conversations
        if "conversations" in sync_req.sync_types:
            query = text("""
                SELECT id, session_id, message_text, message_type, created_at, context
                FROM conversations 
                WHERE user_id = :user_id 
                AND (:last_sync IS NULL OR created_at > :last_sync)
                ORDER BY created_at DESC LIMIT 100
            """)
            
            result = await db.execute(query, {
                "user_id": user_id,
                "last_sync": sync_req.last_sync
            })
            
            conversations = []
            for row in result:
                conversations.append({
                    "id": str(row.id),
                    "session_id": row.session_id,
                    "message_text": row.message_text,
                    "message_type": row.message_type,
                    "created_at": row.created_at.isoformat(),
                    "context": row.context
                })
            
            sync_data["conversations"] = conversations
        
        # Sync tasks
        if "tasks" in sync_req.sync_types:
            query = text("""
                SELECT id, title, description, due_date, priority, status, category, created_at
                FROM tasks 
                WHERE user_id = :user_id 
                AND (:last_sync IS NULL OR updated_at > :last_sync)
                ORDER BY created_at DESC
            """)
            
            result = await db.execute(query, {
                "user_id": user_id,
                "last_sync": sync_req.last_sync
            })
            
            tasks = []
            for row in result:
                tasks.append({
                    "id": str(row.id),
                    "title": row.title,
                    "description": row.description,
                    "due_date": row.due_date.isoformat() if row.due_date else None,
                    "priority": row.priority,
                    "status": row.status,
                    "category": row.category,
                    "created_at": row.created_at.isoformat()
                })
            
            sync_data["tasks"] = tasks
        
        # Log sync operation
        await db.execute(text("""
            INSERT INTO sync_logs (user_id, sync_type, status, records_synced, completed_at)
            VALUES (:user_id, :sync_type, :status, :records_synced, CURRENT_TIMESTAMP)
        """), {
            "user_id": user_id,
            "sync_type": ",".join(sync_req.sync_types),
            "status": "success",
            "records_synced": sum(len(data) for data in sync_data.values())
        })
        
        await db.commit()
        
        SYNC_OPERATIONS.labels(type="manual", status="success").inc()
        
        return {
            "status": "success",
            "sync_timestamp": datetime.utcnow().isoformat(),
            "data": sync_data
        }
        
    except Exception as e:
        await db.rollback()
        logger.error("Sync failed", error=str(e))
        SYNC_OPERATIONS.labels(type="manual", status="failed").inc()
        raise HTTPException(status_code=500, detail="Sync failed")

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time sync"""
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages
            message = json.loads(data)
            logger.info("WebSocket message received", user_id=user_id, type=message.get("type"))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

# Background tasks
async def store_embeddings(text: str, conversation_id: str):
    """Store text embeddings in ChromaDB"""
    try:
        collection = await get_chroma()
        # Simple embedding storage (in production, use proper embedding model)
        collection.add(
            documents=[text],
            ids=[conversation_id],
            metadatas=[{"type": "conversation", "timestamp": datetime.utcnow().isoformat()}]
        )
        logger.info("Embedding stored", conversation_id=conversation_id)
    except Exception as e:
        logger.error("Failed to store embedding", error=str(e))

async def background_sync_task():
    """Background task for periodic cross-device sync"""
    while True:
        try:
            await asyncio.sleep(SYNC_INTERVAL)
            # Implement periodic sync logic here
            logger.debug("Background sync task running")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Background sync task error", error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
