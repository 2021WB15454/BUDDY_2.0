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
except ImportError as e:
    logger.error(f"❌ Failed to import enhanced_backend: {e}")
    logger.info("🔄 Falling back to minimal backend...")
    try:
        from minimal_app import app
        logger.info("✅ Minimal backend imported successfully")
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
        
        logger.info("✅ Basic fallback app created")

# Export the app for uvicorn/gunicorn
# Render will automatically detect this and run: uvicorn app:app
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    logger.info(f"🌐 Starting BUDDY 2.0 on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
