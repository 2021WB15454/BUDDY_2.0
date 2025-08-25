"""
BUDDY Core Runtime - Central Intelligence Engine

This is the main orchestrator that brings together all BUDDY components:
- API Gateway for device communication
- Event Bus for internal coordination
- Memory Layer for knowledge and state
- Skills Engine for capabilities
- Voice Service for speech processing
- Sync Service for cross-device coordination

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                        BUDDY CORE                               │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐           │
│  │ API Gateway  │◄►│ Event Bus   │◄►│ Memory Layer │           │
│  │ (REST + WS)  │  │ (Pub/Sub)   │  │ (SQLite+Vec) │           │
│  └──────────────┘  └─────────────┘  └──────────────┘           │
│          ▲                  ▲                ▲                  │
│          │                  │                │                  │
│  ┌───────▼──────┐  ┌────────▼────┐  ┌────────▼─────┐           │
│  │ Skills Engine│  │Voice Service│  │ Sync Service │           │
│  │  (50+ intents)│  │ (ASR+TTS)   │  │  (CRDT sync) │           │
│  └──────────────┘  └─────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ WebSocket/REST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DEVICE INTERFACES                           │
│  Desktop  │  Mobile  │  Watch  │  TV  │  Car  │  Smart Home    │
│ (Electron)│(Flutter) │(WearOS) │(ATV) │(Auto) │(Home Assistant)│
└─────────────────────────────────────────────────────────────────┘
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import json

# Import all BUDDY Core components
from .api import APIGateway, get_api_gateway
from .events import EventBus, get_event_bus
from .memory import MemoryLayer, get_memory
from .dialogue import DialogueOrchestrator
from .skills import SkillsEngine
from .voice import VoiceService
from .sync import SyncService

logger = logging.getLogger(__name__)

class BuddyCore:
    """
    Main BUDDY Core Runtime
    
    Orchestrates all components and provides the central intelligence
    for the multi-device BUDDY ecosystem.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._load_default_config()
        
        # Core components
        self.api_gateway: Optional[APIGateway] = None
        self.event_bus: Optional[EventBus] = None
        self.memory: Optional[MemoryLayer] = None
        self.dialogue: Optional[DialogueOrchestrator] = None
        self.skills: Optional[SkillsEngine] = None
        self.voice: Optional[VoiceService] = None
        self.sync: Optional[SyncService] = None
        
        # Runtime state
        self.is_running = False
        self.startup_time = None
        self.shutdown_handlers = []
        
        # Statistics
        self.stats = {
            'startup_time': None,
            'uptime_seconds': 0,
            'total_messages': 0,
            'total_errors': 0,
            'connected_devices': 0,
            'active_users': 0
        }
        
        # Setup logging
        self._setup_logging()
        
        logger.info("BUDDY Core initialized")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            'api': {
                'host': '0.0.0.0',
                'port': 8082,
                'cors_origins': ['*'],
                'max_connections': 1000
            },
            'memory': {
                'database_path': 'buddy_memory.db',
                'cleanup_interval': 3600,  # 1 hour
                'max_facts': 100000,
                'max_conversations': 10000
            },
            'voice': {
                'enabled': True,
                'asr_model': 'whisper-base',
                'tts_model': 'piper',
                'language': 'en-US',
                'sample_rate': 16000
            },
            'skills': {
                'enabled_categories': ['all'],
                'max_concurrent': 10,
                'timeout_seconds': 30
            },
            'sync': {
                'enabled': True,
                'discovery_port': 8083,
                'sync_interval': 60,  # 1 minute
                'encryption': True
            },
            'logging': {
                'level': 'INFO',
                'file': 'buddy_core.log',
                'max_size_mb': 100,
                'backup_count': 5
            },
            'security': {
                'require_auth': False,
                'jwt_secret': 'buddy-dev-secret-change-in-production',
                'session_timeout': 86400  # 24 hours
            }
        }
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config.get('logging', {})
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_config.get('file', 'buddy_core.log'))
            ]
        )
        
        # Set specific logger levels
        logging.getLogger('websockets').setLevel(logging.WARNING)
        logging.getLogger('uvicorn').setLevel(logging.INFO)
    
    async def initialize(self):
        """Initialize all BUDDY components"""
        logger.info("Initializing BUDDY Core components...")
        
        try:
            # 1. Initialize Event Bus (communication backbone)
            logger.info("Initializing Event Bus...")
            self.event_bus = get_event_bus()
            await self.event_bus.start()
            
            # 2. Initialize Memory Layer (knowledge and state)
            logger.info("Initializing Memory Layer...")
            self.memory = get_memory()
            await self.memory.initialize()
            
            # 3. Initialize Skills Engine (capabilities)
            logger.info("Initializing Skills Engine...")
            self.skills = SkillsEngine(
                event_bus=self.event_bus,
                memory=self.memory,
                config=self.config.get('skills', {})
            )
            await self.skills.initialize()
            
            # 4. Initialize Voice Service (speech processing)
            if self.config.get('voice', {}).get('enabled', True):
                logger.info("Initializing Voice Service...")
                self.voice = VoiceService(
                    event_bus=self.event_bus,
                    config=self.config.get('voice', {})
                )
                await self.voice.initialize()
            
            # 5. Initialize Dialogue Orchestrator (conversation management)
            logger.info("Initializing Dialogue Orchestrator...")
            self.dialogue = DialogueOrchestrator(
                event_bus=self.event_bus,
                memory=self.memory,
                skills=self.skills
            )
            await self.dialogue.initialize()
            
            # 6. Initialize Sync Service (cross-device coordination)
            if self.config.get('sync', {}).get('enabled', True):
                logger.info("Initializing Sync Service...")
                self.sync = SyncService(
                    event_bus=self.event_bus,
                    memory=self.memory,
                    config=self.config.get('sync', {})
                )
                await self.sync.initialize()
            
            # 7. Initialize API Gateway (device interfaces)
            logger.info("Initializing API Gateway...")
            self.api_gateway = get_api_gateway()
            # API Gateway will be started separately in start()
            
            # Setup component interactions
            await self._setup_component_interactions()
            
            logger.info("✅ All BUDDY Core components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize BUDDY Core: {e}")
            await self.shutdown()
            raise
    
    async def _setup_component_interactions(self):
        """Setup interactions between components"""
        
        # Memory cleanup task
        async def memory_cleanup():
            while self.is_running:
                await asyncio.sleep(self.config['memory']['cleanup_interval'])
                if self.memory:
                    await self.memory.cleanup_expired()
        
        # Statistics update task
        async def update_stats():
            while self.is_running:
                await asyncio.sleep(60)  # Update every minute
                await self._update_stats()
        
        # Schedule background tasks
        asyncio.create_task(memory_cleanup())
        asyncio.create_task(update_stats())
        
        # Setup component event subscriptions
        if self.dialogue:
            self.event_bus.subscribe('ui.message.in', self.dialogue.handle_user_message)
        
        if self.skills:
            self.event_bus.subscribe('skill.execute.*', self.skills.handle_skill_execution)
        
        if self.voice:
            self.event_bus.subscribe('voice.asr.*', self.voice.handle_asr_request)
            self.event_bus.subscribe('voice.tts.*', self.voice.handle_tts_request)
        
        if self.sync:
            self.event_bus.subscribe('sync.*', self.sync.handle_sync_event)
        
        logger.info("Component interactions configured")
    
    async def start(self):
        """Start the BUDDY Core runtime"""
        if self.is_running:
            logger.warning("BUDDY Core is already running")
            return
        
        logger.info("🚀 Starting BUDDY Core...")
        self.startup_time = time.time()
        self.stats['startup_time'] = self.startup_time
        self.is_running = True
        
        try:
            # Initialize all components
            await self.initialize()
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Start API Gateway (this will block)
            logger.info("🌐 Starting API Gateway...")
            await self.api_gateway.start()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            await self.shutdown()
        except Exception as e:
            logger.error(f"Error starting BUDDY Core: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self):
        """Shutdown BUDDY Core gracefully"""
        if not self.is_running:
            return
        
        logger.info("🛑 Shutting down BUDDY Core...")
        self.is_running = False
        
        # Run custom shutdown handlers
        for handler in self.shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Error in shutdown handler: {e}")
        
        # Shutdown components in reverse order
        components = [
            ('API Gateway', self.api_gateway),
            ('Sync Service', self.sync),
            ('Voice Service', self.voice),
            ('Dialogue Orchestrator', self.dialogue),
            ('Skills Engine', self.skills),
            ('Memory Layer', self.memory),
            ('Event Bus', self.event_bus)
        ]
        
        for name, component in components:
            if component and hasattr(component, 'stop'):
                try:
                    logger.info(f"Stopping {name}...")
                    await component.stop()
                except Exception as e:
                    logger.error(f"Error stopping {name}: {e}")
        
        logger.info("✅ BUDDY Core shutdown complete")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _update_stats(self):
        """Update runtime statistics"""
        if not self.startup_time:
            return
        
        self.stats['uptime_seconds'] = time.time() - self.startup_time
        
        # Get stats from components
        if self.event_bus:
            event_stats = self.event_bus.get_stats()
            self.stats['total_messages'] = event_stats.get('events_processed', 0)
            self.stats['total_errors'] = event_stats.get('events_failed', 0)
        
        if self.api_gateway:
            connection_stats = self.api_gateway.connection_manager.get_stats()
            self.stats['connected_devices'] = connection_stats.get('device_connections', 0)
        
        if self.memory:
            memory_stats = await self.memory.get_memory_stats()
            self.stats['active_users'] = memory_stats.get('users_count', 0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get runtime statistics"""
        return {
            'buddy_core': self.stats.copy(),
            'components': {
                'event_bus': self.event_bus.get_stats() if self.event_bus else {},
                'memory': asyncio.create_task(self.memory.get_memory_stats()).result() if self.memory else {},
                'api_gateway': self.api_gateway.connection_manager.get_stats() if self.api_gateway else {}
            },
            'config': self.config
        }
    
    def add_shutdown_handler(self, handler):
        """Add a custom shutdown handler"""
        self.shutdown_handlers.append(handler)
    
    def get_component(self, name: str):
        """Get a specific component by name"""
        components = {
            'api_gateway': self.api_gateway,
            'event_bus': self.event_bus,
            'memory': self.memory,
            'dialogue': self.dialogue,
            'skills': self.skills,
            'voice': self.voice,
            'sync': self.sync
        }
        return components.get(name)

# Global BUDDY Core instance
_buddy_core = None

def get_buddy_core(config: Dict[str, Any] = None) -> BuddyCore:
    """Get the global BUDDY Core instance"""
    global _buddy_core
    if _buddy_core is None:
        _buddy_core = BuddyCore(config)
    return _buddy_core

# Main entry point
async def main():
    """Main entry point for BUDDY Core"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BUDDY Core - Multi-Device AI Assistant")
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='API host')
    parser.add_argument('--port', type=int, default=8082, help='API port')
    parser.add_argument('--log-level', type=str, default='INFO', help='Log level')
    parser.add_argument('--dev', action='store_true', help='Development mode')
    
    args = parser.parse_args()
    
    # Load configuration
    config = None
    if args.config and Path(args.config).exists():
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Override with command line args
    if not config:
        config = {}
    
    if not config.get('api'):
        config['api'] = {}
    config['api']['host'] = args.host
    config['api']['port'] = args.port
    
    if not config.get('logging'):
        config['logging'] = {}
    config['logging']['level'] = args.log_level
    
    if args.dev:
        config['logging']['level'] = 'DEBUG'
        config['security']['require_auth'] = False
    
    # Create and start BUDDY Core
    buddy = get_buddy_core(config)
    
    try:
        await buddy.start()
    except KeyboardInterrupt:
        pass
    finally:
        await buddy.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
