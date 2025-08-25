"""
BUDDY 2.0 Application Entry Point for Render Deployment

This file serves as the main entry point that Render expects.
It imports the FastAPI app from enhanced_backend.py.
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
    logger.info("🚀 Importing BUDDY 2.0 Backend...")
    from enhanced_backend import app
    logger.info("✅ BUDDY 2.0 Backend imported successfully")
    
    # Import Firebase Status Bridge
    try:
        from firebase_status_bridge import startup_firebase_bridge, shutdown_firebase_bridge
        
        # Add startup event to set BUDDY online
        @app.on_event("startup")
        async def startup_with_firebase():
            logger.info("🔥 Starting Firebase Status Bridge...")
            await startup_firebase_bridge()
            logger.info("🟢 BUDDY is now ONLINE in Firebase!")
            
        # Add shutdown event to set BUDDY offline  
        @app.on_event("shutdown")
        async def shutdown_with_firebase():
            logger.info("🔴 Setting BUDDY offline in Firebase...")
            await shutdown_firebase_bridge()
            
        logger.info("✅ Firebase Status Bridge integrated")
        
    except ImportError as fb_error:
        logger.warning(f"⚠️ Firebase Status Bridge not available: {fb_error}")
        
except ImportError as e:
    logger.error(f"❌ Failed to import enhanced_backend: {e}")
    logger.info("🔄 Falling back to minimal backend...")
    try:
        from minimal_app import app
        logger.info("✅ Minimal backend imported successfully")
        
        # Add Firebase bridge to minimal app too
        try:
            from firebase_status_bridge import startup_firebase_bridge, shutdown_firebase_bridge
            
            @app.on_event("startup")
            async def minimal_startup():
                await startup_firebase_bridge()
                logger.info("🟢 Minimal BUDDY online in Firebase")
                
            @app.on_event("shutdown") 
            async def minimal_shutdown():
                await shutdown_firebase_bridge()
                
        except ImportError:
            pass
            
    except ImportError as e2:
        logger.error(f"❌ Minimal backend also failed: {e2}")
        # Create absolute minimal FastAPI app
        from fastapi import FastAPI
        app = FastAPI()
        
        @app.get("/")
        async def root():
            return {"message": "BUDDY 2.0 Basic Mode", "status": "online"}
        
        @app.get("/health")
        async def health():
            return {"status": "healthy", "mode": "basic"}
            
        @app.get("/status")
        async def status():
            return {"status": "online", "mode": "basic", "backend_url": os.getenv("RENDER_EXTERNAL_URL", "unknown")}
        
        logger.info("✅ Basic fallback app created")

# Export the app for uvicorn/gunicorn
# Render will automatically detect this and run: uvicorn app:app
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    logger.info(f"🌐 Starting BUDDY 2.0 on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
