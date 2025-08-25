"""
BUDDY Main Entry Point

Main application entry point that starts the BUDDY runtime and handles
command-line arguments, configuration loading, and graceful shutdown.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
import yaml
import json

from .runtime import BuddyRuntime


def setup_logging(level: str = "INFO", log_file: str = None):
    """Setup logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Reduce noise from some libraries
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    

def load_config(config_path: Path = None) -> dict:
    """Load configuration from file."""
    if config_path and config_path.exists():
        with open(config_path, 'r') as f:
            if config_path.suffix.lower() == '.yaml':
                return yaml.safe_load(f)
            else:
                return json.load(f)
    return {}


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BUDDY - Your JARVIS-style Personal AI Assistant"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Path to configuration file (YAML or JSON)"
    )
    
    parser.add_argument(
        "--log-level", "-l",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="Set logging level"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        default="logs/buddy.log",
        help="Path to log file"
    )
    
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Enable development mode"
    )
    
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Start API server only (no voice processing)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="API server port"
    )
    
    parser.add_argument(
        "--host",
        default="localhost",
        help="API server host"
    )
    
    return parser.parse_args()


async def start_api_server(runtime: BuddyRuntime, host: str, port: int):
    """Start the REST API server."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        
        app = FastAPI(
            title="BUDDY API",
            description="REST API for BUDDY Personal AI Assistant",
            version="0.1.0"
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @app.get("/")
        async def root():
            return {"message": "BUDDY API Server", "version": "0.1.0"}
        
        @app.get("/health")
        async def health():
            return {"status": "healthy", "uptime": runtime.get_metrics().get("uptime_seconds", 0)}

        @app.get("/status")
        async def get_status():
            return runtime.get_status()
        
        @app.get("/metrics")
        async def get_metrics():
            return runtime.get_metrics()
        
        @app.post("/chat")
        async def chat(request: dict):
            text = request.get("text") or request.get("message", "")
            user_id = request.get("user_id", "default")
            device_id = request.get("device_id", "api")
            context = request.get("context", {})
            
            if not text:
                raise HTTPException(status_code=400, detail="Text is required")
            
            result = await runtime.process_user_input(text, user_id, device_id, context)
            return result
        
        @app.get("/skills")
        async def get_skills():
            skills = runtime.skill_registry.list_skills()
            return {"skills": skills}
        
        @app.get("/skills/{skill_name}/schema")
        async def get_skill_schema(skill_name: str):
            schema = runtime.skill_registry.get_skill_schema(skill_name)
            if not schema:
                raise HTTPException(status_code=404, detail="Skill not found")
            return schema.to_dict()
        
        # Start server
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        
        logging.info(f"Starting API server on {host}:{port}")
        await server.serve()
        
    except ImportError:
        logging.error("FastAPI and uvicorn are required for API server. Install with: pip install fastapi uvicorn")
        sys.exit(1)


async def main():
    """Main application entry point."""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting BUDDY Personal AI Assistant")
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command line arguments
    if args.dev:
        config.setdefault("privacy", {})["local_only"] = True
        config.setdefault("voice", {})["wake_word_enabled"] = False
        logger.info("Development mode enabled")
    
    # Create runtime
    runtime = BuddyRuntime(config)
    try:
        await runtime.start()
        # Ensure minimal built-in skills are registered for immediate usefulness
        try:
            await runtime.skill_registry.register_builtin_skills()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to register builtin skills: {e}")
        
        # Start API server if requested
        if args.api_only:
            await start_api_server(runtime, args.host, args.port)
        else:
            # Start both runtime and API server
            api_task = asyncio.create_task(
                start_api_server(runtime, args.host, args.port)
            )
            
            # Keep running until stopped
            while runtime.running:
                await asyncio.sleep(1)
                
            api_task.cancel()
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1
    finally:
        await runtime.stop()
        logger.info("BUDDY stopped")
        
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
