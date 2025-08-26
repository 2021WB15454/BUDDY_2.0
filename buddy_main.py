"""
BUDDY Core - Multi-Device AI Assistant

Entry point for the new BUDDY Core architecture.
This replaces simple_backend.py with a fully modular, scalable system.

Features:
- Multi-device support (Desktop, Mobile, Watch, TV, Car)
- Real-time WebSocket communication
- Event-driven architecture
- Persistent memory and knowledge base
- Voice processing capabilities
- Cross-device synchronization
- 50+ integrated AI skills and intents

Usage:
    python buddy_main.py [options]
    
Options:
    --host HOST         API host (default: 0.0.0.0)
    --port PORT         API port (default: 8082)
    --config FILE       Configuration file
    --dev               Development mode
    --log-level LEVEL   Log level (DEBUG, INFO, WARNING, ERROR)

Architecture:
    BUDDY Core (this) ←→ Device Interfaces (Electron, Flutter, etc.)
    
Device interfaces connect via:
    - WebSocket: ws://{os.getenv('BUDDY_HOST','localhost')}:{os.getenv('BUDDY_PORT','8082')}/ws
    - REST API: http://{os.getenv('BUDDY_HOST','localhost')}:{os.getenv('BUDDY_PORT','8082')}/api/*
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the buddy_core module to path
sys.path.insert(0, str(Path(__file__).parent))

from buddy_core.runtime import main

if __name__ == "__main__":
    host = os.getenv('BUDDY_HOST', 'localhost')
    port = os.getenv('BUDDY_PORT', '8082')
    print("🤖 BUDDY Core - Multi-Device AI Assistant")
    print("=" * 50)
    print("Starting BUDDY Core with new architecture...")
    print(f"WebSocket: ws://{host}:{port}/ws")
    print(f"REST API: http://{host}:{port}/api/")
    print("=" * 50)
    
    # Run the main BUDDY Core runtime
    asyncio.run(main())
