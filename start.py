#!/usr/bin/env python3
"""
BUDDY 2.0 Production Startup Script

Handles different deployment scenarios and ensures proper startup.
"""

import os
import sys
import logging
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main startup function"""
    try:
        logger.info("🚀 Starting BUDDY 2.0 Application...")
        
        # Import the FastAPI app
        from enhanced_backend import app
        
        # Get port from environment
        port = int(os.getenv("PORT", 10000))
        host = os.getenv("HOST", "0.0.0.0")
        
        logger.info(f"🌐 Starting server on {host}:{port}")
        
        # Check if we're in production or development
        env = os.getenv("BUDDY_ENV", "development")
        debug = os.getenv("BUDDY_DEBUG", "0") == "1"
        
        if env == "production":
            # Production mode - use gunicorn
            logger.info("🏭 Production mode - using gunicorn")
            import gunicorn.app.wsgiapp
            sys.argv = [
                "gunicorn",
                "app:app",
                f"--bind={host}:{port}",
                "--worker-class=uvicorn.workers.UvicornWorker",
                "--workers=2",
                "--timeout=120",
                "--preload"
            ]
            gunicorn.app.wsgiapp.run()
        else:
            # Development mode - use uvicorn directly
            logger.info("🔧 Development mode - using uvicorn")
            import uvicorn
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info" if not debug else "debug",
                reload=debug
            )
            
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure all dependencies are installed")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
