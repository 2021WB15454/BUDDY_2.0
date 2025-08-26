"""
BUDDY 2.0 Application Entry Point for Render Deployment

This file serves as the main entry point that Render expects.
It imports the FastAPI app from cloud_backend.py - a simplified, cloud-compatible version.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    logger.info("🚀 Importing BUDDY 2.0 Cloud Backend...")
    from cloud_backend import app
    logger.info("✅ BUDDY 2.0 Cloud Backend imported successfully")
    
    # Import Firebase Status Bridge (if available)
    try:
        from firebase_status_bridge import startup_firebase_bridge, shutdown_firebase_bridge
        
        # Add startup event to set BUDDY online
        @app.on_event("startup")
        async def startup_firebase():
            await startup_firebase_bridge()
        
        # Add shutdown event to set BUDDY offline
        @app.on_event("shutdown")
        async def shutdown_firebase():
            await shutdown_firebase_bridge()
            
        logger.info("✅ Firebase Status Bridge integrated")
        
    except ImportError as e:
        logger.warning(f"⚠️  Firebase Status Bridge not available: {e}")
        
except ImportError as e:
    logger.error(f"❌ Failed to import cloud backend: {e}")
    
    # Fallback to minimal backend
    try:
        logger.info("🔄 Falling back to minimal backend...")
        from minimal_backend import app
        logger.info("✅ Minimal backend loaded successfully")
    except ImportError as e2:
        logger.error(f"❌ Failed to import minimal backend: {e2}")
        
        # Create emergency fallback app
        from fastapi import FastAPI
        
        app = FastAPI(title="BUDDY Emergency Fallback")
        
        @app.get("/health")
        async def emergency_health():
            return {"status": "emergency_fallback", "message": "BUDDY backend not available"}
        
        @app.post("/chat")
        async def emergency_chat(message: dict):
            return {"response": "BUDDY is currently unavailable. Please try again later.", "timestamp": ""}
        
        logger.info("⚠️  Emergency fallback app created")

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 10000))
    
    logger.info(f"🌐 Starting BUDDY on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
