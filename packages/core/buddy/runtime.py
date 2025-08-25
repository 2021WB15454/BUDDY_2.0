"""
BUDDY Core Runtime

The main orchestrator for the BUDDY personal AI assistant system.
Coordinates all subsystems including voice processing, dialogue management,
skill execution, and cross-device synchronization.
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml
import json

from .events import EventBus, get_event_bus
from .dialogue import DialogueManager
from .skills import SkillRegistry

# Database imports (optional)
try:
    from .database import MongoDBClient
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    MongoDBClient = None

logger = logging.getLogger(__name__)


class BuddyRuntime:
    """
    Main runtime engine for BUDDY.
    
    Coordinates all subsystems and provides the main event loop
    for processing user interactions across devices.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_default_config()
        # Core components
        self.event_bus = get_event_bus()
        self.skill_registry = SkillRegistry(self.event_bus)
        self.dialogue_manager = DialogueManager(self.event_bus, self.skill_registry)
        
        # Database (optional)
        self.database = None
        if DATABASE_AVAILABLE and self.config.get("database", {}).get("enabled", True):
            try:
                self.database = MongoDBClient()
                logger.info("Database client initialized")
            except Exception as e:
                logger.warning(f"Database initialization failed: {e}")
                self.database = None
        
        # State tracking
        self.active_sessions: Dict[str, str] = {}  # session_id -> user_id
        self.device_connections: Dict[str, Dict[str, Any]] = {}
        self.running = False
        # Performance metrics
        self.metrics = {
            "sessions_started": 0,
            "turns_processed": 0,
            "skills_executed": 0,
            "errors": 0,
            "uptime_start": None
        }
        # Setup event subscriptions
        self._setup_event_handlers()
        logger.info("BUDDY Runtime initialized")
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            "voice": {
                "wake_word_enabled": True,
                "wake_word_model": "hey_buddy",
                "asr_model": "whisper_base",
                "tts_voice": "default",
                "audio_sample_rate": 16000
            },
            "nlu": {
                "model": "lightweight",
                "confidence_threshold": 0.7,
                "max_entities": 10
            },
            "dialogue": {
                "session_timeout_minutes": 30,
                "max_conversation_history": 100,
                "confirmation_required_for": ["delete", "send", "purchase"]
            },
            "skills": {
                "auto_discover": True,
                "skill_directories": ["./skills", "./custom_skills"],
                "default_timeout_ms": 5000
            },
            "sync": {
                "enabled": True,
                "encryption": True,
                "discovery_timeout": 30
            },
            "privacy": {
                "local_only": False,
                "data_retention_days": 90,
                "anonymous_telemetry": True
            },
            "performance": {
                "max_concurrent_sessions": 10,
                "cleanup_interval_minutes": 15
            },
            "database": {
                "enabled": True,
                "type": "mongodb",
                "config_file": "config/database.yml"
            }
        }
        
    def _setup_event_handlers(self):
        """Setup event handlers for runtime coordination."""
        self.event_bus.subscribe("audio.wake_detected", self._handle_wake_detected)
        self.event_bus.subscribe("audio.speech_end", self._handle_speech_end)
        self.event_bus.subscribe("nlu.intent", self._handle_intent_recognized)
        self.event_bus.subscribe("skill.result", self._handle_skill_result)
        self.event_bus.subscribe("device.connected", self._handle_device_connected)
        self.event_bus.subscribe("device.disconnected", self._handle_device_disconnected)
        self.event_bus.subscribe("system.shutdown", self._handle_shutdown_request)
        
    async def start(self):
        """Start the BUDDY runtime."""
        if self.running:
            logger.warning("Runtime already running")
            return
            
        self.running = True
        self.metrics["uptime_start"] = asyncio.get_event_loop().time()
        
        logger.info("Starting BUDDY Runtime...")
        
        try:
            # Initialize database connection if available
            if self.database:
                try:
                    await self.database.connect()
                    logger.info("✅ Database connected successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Database connection failed: {e}")
                    logger.info("🔄 BUDDY will continue without database persistence")
                    self.database = None
            
            # Start core components
            await self.event_bus.start()
            
            # Initialize skill registry and discover skills
            if self.config["skills"]["auto_discover"]:
                skill_paths = [Path(p) for p in self.config["skills"]["skill_directories"]]
                await self.skill_registry.discover_skills(skill_paths)
                
            # Start periodic tasks
            self._start_background_tasks()
            
            # Signal that we're ready
            await self.event_bus.publish(
                "system.ready",
                {
                    "version": "0.1.0",
                    "timestamp": asyncio.get_event_loop().time(),
                    "config": self.config
                },
                source="buddy_runtime"
            )
            
            logger.info("BUDDY Runtime started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start runtime: {e}")
            self.running = False
            raise
            
    async def stop(self):
        """Stop the BUDDY runtime."""
        if not self.running:
            return
            
        logger.info("Stopping BUDDY Runtime...")
        self.running = False
        
        try:
            # Stop background tasks
            self._stop_background_tasks()
            
            # Close database connection if available
            if self.database:
                try:
                    await self.database.close()
                    logger.info("Database connection closed")
                except Exception as e:
                    logger.warning(f"Error closing database: {e}")
            
            # Clean up active sessions
            for session_id in list(self.active_sessions.keys()):
                await self.dialogue_manager.end_session(session_id)
                
            # Stop core components
            await self.event_bus.stop()
            
            logger.info("BUDDY Runtime stopped")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
    async def process_user_input(self, text: str, user_id: str, device_id: str,
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process user input and return response.
        
        Args:
            text: User input text
            user_id: User identifier
            device_id: Device identifier
            context: Additional context information
            
        Returns:
            Response dictionary with result and metadata
        """
        try:
            # Get or create session
            session_id = await self._get_or_create_session(user_id, device_id, context)
            
            # Process the turn
            turn = await self.dialogue_manager.process_turn(session_id, text)
            
            # Update metrics
            self.metrics["turns_processed"] += 1
            
            # Publish turn event
            await self.event_bus.publish(
                "runtime.turn_processed",
                {
                    "session_id": session_id,
                    "turn_id": turn.turn_id,
                    "user_id": user_id,
                    "device_id": device_id,
                    "success": turn.success,
                    "duration_ms": turn.duration_ms
                },
                source="buddy_runtime"
            )
            
            return {
                "success": turn.success,
                "response": turn.system_response,
                "intent": turn.intent,
                "entities": turn.entities,
                "session_id": session_id,
                "turn_id": turn.turn_id,
                "duration_ms": turn.duration_ms,
                "error": turn.error_message
            }
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            self.metrics["errors"] += 1
            
            return {
                "success": False,
                "response": "I'm sorry, I encountered an error processing your request.",
                "error": str(e)
            }
            
    async def _get_or_create_session(self, user_id: str, device_id: str,
                                   context: Optional[Dict[str, Any]] = None) -> str:
        """Get existing session or create a new one."""
        # For now, create a new session each time
        # In a real implementation, we'd check for existing active sessions
        session_id = await self.dialogue_manager.start_session(user_id, device_id, context)
        self.active_sessions[session_id] = user_id
        self.metrics["sessions_started"] += 1
        return session_id
        
    def _start_background_tasks(self):
        """Start background maintenance tasks."""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self._metrics_task = asyncio.create_task(self._periodic_metrics())
        
    def _stop_background_tasks(self):
        """Stop background tasks."""
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()
        if hasattr(self, '_metrics_task'):
            self._metrics_task.cancel()
            
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired sessions and resources."""
        interval = self.config["performance"]["cleanup_interval_minutes"] * 60
        
        while self.running:
            try:
                await asyncio.sleep(interval)
                
                if not self.running:
                    break
                    
                # Clean up expired dialogue sessions
                await self.dialogue_manager.cleanup_expired_sessions()
                
                # Clean up event history
                self.event_bus.clear_history()
                
                logger.debug("Periodic cleanup completed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                
    async def _periodic_metrics(self):
        """Periodic metrics collection and reporting."""
        interval = 300  # 5 minutes
        
        while self.running:
            try:
                await asyncio.sleep(interval)
                
                if not self.running:
                    break
                    
                # Collect and publish metrics
                current_metrics = self.get_metrics()
                
                await self.event_bus.publish(
                    "system.metrics",
                    current_metrics,
                    source="buddy_runtime"
                )
                
                logger.debug(f"Metrics: {current_metrics}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                
    async def _handle_wake_detected(self, event):
        """Handle wake word detection."""
        device_id = event.payload.get("device_id")
        confidence = event.payload.get("confidence", 0.0)
        
        logger.info(f"Wake word detected on device {device_id} (confidence: {confidence})")
        
        # Activate listening mode for this device
        await self.event_bus.publish(
            "audio.start_listening",
            {"device_id": device_id},
            source="buddy_runtime"
        )
        
    async def _handle_speech_end(self, event):
        """Handle end of speech input."""
        device_id = event.payload.get("device_id")
        text = event.payload.get("text", "")
        user_id = event.payload.get("user_id", "default")
        
        if text.strip():
            # Process the speech input
            result = await self.process_user_input(text, user_id, device_id)
            
            # Send response back to device
            if result["success"] and result["response"]:
                await self.event_bus.publish(
                    "tts.speak",
                    {
                        "text": result["response"],
                        "device_id": device_id,
                        "session_id": result.get("session_id")
                    },
                    source="buddy_runtime"
                )
                
    async def _handle_intent_recognized(self, event):
        """Handle intent recognition results."""
        # Intent handling is primarily done in dialogue manager
        # This is for runtime-level coordination if needed
        pass
        
    async def _handle_skill_result(self, event):
        """Handle skill execution results."""
        self.metrics["skills_executed"] += 1
        
        # Forward to appropriate session/device if needed
        session_id = event.payload.get("session_id")
        if session_id and not event.payload.get("success"):
            # Handle skill failures
            await self.event_bus.publish(
                "tts.speak",
                {
                    "text": "I encountered an error while processing that request.",
                    "session_id": session_id,
                    "priority": "high"
                },
                source="buddy_runtime"
            )
            
    async def _handle_device_connected(self, event):
        """Handle device connection."""
        device_id = event.payload.get("device_id")
        device_info = event.payload.get("device_info", {})
        
        self.device_connections[device_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "info": device_info
        }
        
        logger.info(f"Device connected: {device_id}")
        
    async def _handle_device_disconnected(self, event):
        """Handle device disconnection."""
        device_id = event.payload.get("device_id")
        
        if device_id in self.device_connections:
            del self.device_connections[device_id]
            
        # Clean up any sessions for this device
        sessions_to_end = []
        for session_id, context in self.dialogue_manager.active_contexts.items():
            if context.device_id == device_id:
                sessions_to_end.append(session_id)
                
        for session_id in sessions_to_end:
            await self.dialogue_manager.end_session(session_id)
            
        logger.info(f"Device disconnected: {device_id}")
        
    async def _handle_shutdown_request(self, event):
        """Handle system shutdown request."""
        logger.info("Shutdown requested")
        await self.stop()
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get current runtime metrics."""
        uptime = 0
        if self.metrics["uptime_start"]:
            uptime = asyncio.get_event_loop().time() - self.metrics["uptime_start"]
            
        return {
            "uptime_seconds": uptime,
            "sessions_started": self.metrics["sessions_started"],
            "turns_processed": self.metrics["turns_processed"],
            "skills_executed": self.metrics["skills_executed"],
            "errors": self.metrics["errors"],
            "active_sessions": len(self.active_sessions),
            "connected_devices": len(self.device_connections),
            "registered_skills": len(self.skill_registry.skills)
        }
        
    def get_status(self) -> Dict[str, Any]:
        """Get current runtime status."""
        return {
            "running": self.running,
            "version": "0.1.0",
            "metrics": self.get_metrics(),
            "config": self.config,
            "active_sessions": list(self.active_sessions.keys()),
            "connected_devices": list(self.device_connections.keys())
        }


async def main():
    """Main entry point for BUDDY runtime."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start runtime
    runtime = BuddyRuntime()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(runtime.stop())
        
    signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
    
    try:
        await runtime.start()
        
        # Keep running until stopped
        while runtime.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Runtime error: {e}")
    finally:
        await runtime.stop()
        

if __name__ == "__main__":
    asyncio.run(main())
