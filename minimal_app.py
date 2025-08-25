"""
Minimal BUDDY 2.0 Backend for Debugging Render Deployment
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="BUDDY 2.0 Backend", version="2.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple models
class ChatMessage(BaseModel):
    message: str
    user_id: str = "default_user"

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    user_id: str

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "BUDDY 2.0 Backend is running",
        "status": "online",
        "version": "2.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0",
        "service": "BUDDY Backend"
    }

@app.get("/status")
async def get_status():
    """Status endpoint for frontend"""
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "backend_url": os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000"),
        "version": "2.0"
    }

@app.get("/config")
async def get_config():
    """Configuration endpoint for frontend"""
    render_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000")
    return {
        "api_url": render_url,
        "backend_status": "online",
        "version": "2.0",
        "endpoints": {
            "chat": f"{render_url}/chat",
            "health": f"{render_url}/health",
            "status": f"{render_url}/status"
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Simple chat endpoint"""
    
    # Simple response logic
    user_message = message.message.lower()
    
    if "hello" in user_message or "hi" in user_message:
        response = "Hello! I'm BUDDY 2.0. How can I help you today?"
    elif "how are you" in user_message:
        response = "I'm doing great! Ready to assist you with anything you need."
    elif "weather" in user_message:
        response = "I can help with weather information! Please tell me your location."
    elif "time" in user_message:
        response = f"The current time is {datetime.now().strftime('%H:%M:%S')}"
    elif "date" in user_message:
        response = f"Today is {datetime.now().strftime('%B %d, %Y')}"
    else:
        response = f"I understand you said: '{message.message}'. I'm BUDDY 2.0, and I'm here to help!"
    
    return ChatResponse(
        response=response,
        timestamp=datetime.now().isoformat(),
        user_id=message.user_id
    )

# Application startup
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 BUDDY 2.0 Minimal Backend starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 BUDDY 2.0 Minimal Backend shutting down...")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
