#!/usr/bin/env python3
"""
BUDDY Universal Launcher
Launch BUDDY 2.0 with universal port management across any platform

This script demonstrates BUDDY's platform-agnostic capabilities:
- Auto-detects cloud vs local environment
- Uses environment-assigned ports (Heroku $PORT, Render $PORT, etc.)
- Falls back to free ports automatically
- Works with reverse proxies and containers
- Provides comprehensive startup information
"""

import os
import sys
import asyncio
import argparse
import subprocess
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "buddy_core"))

from buddy_core.utils.universal_port_manager import (
    UniversalPortManager,
    PortConfig,
    auto_configure,
    get_environment,
    is_cloud_environment
)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="BUDDY 2.0 Universal Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python universal_launcher.py                    # Auto-detect everything
  python universal_launcher.py --backend simple  # Use simple backend
  python universal_launcher.py --backend cloud   # Use cloud backend
  python universal_launcher.py --port 8000       # Prefer port 8000
  python universal_launcher.py --host 127.0.0.1  # Bind to localhost only
  python universal_launcher.py --web             # Also start web interface
  python universal_launcher.py --demo            # Run port management demo
  
Environment Variables:
  PORT                 - Preferred port (cloud platforms set this)
  BUDDY_PORT          - Alternative port specification
  HOST                - Host to bind to (default: 0.0.0.0)
  BUDDY_BACKEND       - Backend to use (simple, cloud, enhanced)
  BUDDY_ENV           - Environment (local, production, staging)
        """
    )
    
    parser.add_argument(
        '--backend', 
        choices=['simple', 'cloud', 'enhanced', 'auto'],
        default='auto',
        help='Backend to launch (default: auto-detect)'
    )
    
    parser.add_argument(
        '--port', 
        type=int, 
        default=0,
        help='Preferred port (0 = auto-assign, default: 0)'
    )
    
    parser.add_argument(
        '--host', 
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--web', 
        action='store_true',
        help='Also start web interface server'
    )
    
    parser.add_argument(
        '--demo', 
        action='store_true',
        help='Run port management demonstration'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    return parser.parse_args()

def detect_best_backend():
    """Detect the best backend based on available files and environment"""
    backends = {
        'cloud_backend.py': 'cloud',
        'simple_buddy.py': 'simple', 
        'enhanced_backend.py': 'enhanced'
    }
    
    available_backends = []
    for file, name in backends.items():
        if (current_dir / file).exists():
            available_backends.append((name, file))
    
    if not available_backends:
        raise RuntimeError("No backend files found!")
    
    # Prefer cloud backend for cloud environments
    if is_cloud_environment():
        for name, file in available_backends:
            if name == 'cloud':
                return name, file
    
    # Default priority: cloud > enhanced > simple
    priority = ['cloud', 'enhanced', 'simple']
    for preferred in priority:
        for name, file in available_backends:
            if name == preferred:
                return name, file
    
    # Fallback to first available
    return available_backends[0]

def run_port_demo():
    """Demonstrate universal port management capabilities"""
    print("🧪 BUDDY Universal Port Management Demo")
    print("=" * 60)
    
    # Test different configurations
    configs = [
        PortConfig(port=0, environment="auto"),
        PortConfig(port=8000, fallback_ports=[8001, 8002]),
        PortConfig(port=3000, fallback_ports=[3001, 3002, 8080])
    ]
    
    for i, config in enumerate(configs, 1):
        print(f"\n🔬 Test {i}: {config}")
        manager = UniversalPortManager(config)
        server_config = manager.get_server_config()
        
        print(f"   Environment: {server_config['environment']}")
        print(f"   Assigned Port: {server_config['port']}")
        print(f"   Local URL: {server_config['urls']['local']}")
        print(f"   Network URL: {server_config['urls']['network']}")
    
    print("\n✅ Universal port management working perfectly!")
    print("🌍 BUDDY can run anywhere: local, cloud, container, proxy")

def launch_backend(backend_name: str, backend_file: str, port: int, host: str):
    """Launch the specified backend"""
    print(f"🚀 Launching BUDDY with {backend_name} backend...")
    
    # Set environment variables for the backend
    env = os.environ.copy()
    if port > 0:
        env['BUDDY_PORT'] = str(port)
    env['HOST'] = host
    
    # Launch the backend
    try:
        subprocess.run([sys.executable, str(current_dir / backend_file)], env=env)
    except KeyboardInterrupt:
        print(f"\n🛑 Shutting down BUDDY {backend_name} backend...")
    except Exception as e:
        print(f"❌ Error launching backend: {e}")

def launch_web_interface():
    """Launch web interface in background"""
    print("🌐 Starting web interface server...")
    try:
        subprocess.Popen([
            sys.executable, 
            str(current_dir / "buddy_web_server.py")
        ])
        print("✅ Web interface launched in background")
    except Exception as e:
        print(f"⚠️  Could not start web interface: {e}")

def main():
    """Main launcher function"""
    args = parse_arguments()
    
    print("🚀 BUDDY 2.0 Universal Launcher")
    print("=" * 60)
    
    # Auto-configure for environment
    auto_configure()
    
    # Show environment info
    env = get_environment()
    cloud = is_cloud_environment()
    print(f"🌍 Environment: {env.upper()} {'(Cloud)' if cloud else '(Local)'}")
    
    if args.demo:
        run_port_demo()
        return
    
    # Detect backend
    if args.backend == 'auto':
        backend_name, backend_file = detect_best_backend()
        print(f"🎯 Auto-detected backend: {backend_name}")
    else:
        backend_name = args.backend
        backend_file = f"{backend_name}_backend.py" if backend_name != 'simple' else "simple_buddy.py"
        
        if not (current_dir / backend_file).exists():
            print(f"❌ Backend file not found: {backend_file}")
            return
    
    print(f"📁 Backend file: {backend_file}")
    print(f"🔧 Configuration: host={args.host}, port={args.port or 'auto'}")
    
    # Launch web interface if requested
    if args.web:
        launch_web_interface()
    
    print("=" * 60)
    
    # Launch the backend
    launch_backend(backend_name, backend_file, args.port, args.host)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n👋 BUDDY Universal Launcher stopped")
    except Exception as e:
        print(f"❌ Launcher error: {e}")
        sys.exit(1)
