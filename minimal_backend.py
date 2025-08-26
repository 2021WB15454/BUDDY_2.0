"""Minimal backend test to isolate the issue"""

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from datetime import datetime

app = FastAPI()

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    timestamp: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/chat")
async def chat(message: ChatMessage):
    """Minimal chat endpoint"""
    try:
        print(f"Received message: {message.message}")
        
        # Simple response logic
        if "how are you" in message.message.lower():
            response_text = "I'm doing great! This is the new response."
        else:
            response_text = f"You said: {message.message}"
        
        return ChatResponse(
            response=response_text,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        print(f"Error in chat: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    import os
    host = os.getenv("BUDDY_HOST", "localhost")
    port = int(os.getenv("BUDDY_PORT", "8082"))
    uvicorn.run(app, host=host, port=port, log_level="info")
