"""
BUDDY Web Interface Server
Simple HTTP server to serve the BUDDY web interface with CORS support
Universal port management for any deployment environment
"""

import http.server
import socketserver
import os
import webbrowser
import threading
import time
from urllib.parse import urlparse, parse_qs
import json
import sys

# Add buddy_core to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'buddy_core'))

# Universal Port Management
try:
    from buddy_core.utils.universal_port_manager import (
        UniversalPortManager, PortConfig, auto_configure
    )
    UNIVERSAL_PORT_AVAILABLE = True
except ImportError:
    UNIVERSAL_PORT_AVAILABLE = False
    print("⚠️  Universal port manager not available - using basic port logic")

# Legacy dynamic config for fallback
try:
    from dynamic_config import get_host, get_port, get_ws_base
    DYNAMIC_CONFIG_AVAILABLE = True
except ImportError:
    DYNAMIC_CONFIG_AVAILABLE = False
    def get_host(): return "localhost"
    def get_port(): return 8082
    def get_ws_base(): return "ws://localhost:8082"

class BuddyWebHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for BUDDY web interface with CORS support"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        # Serve the main interface
        if self.path == '/' or self.path == '/index.html':
            self.path = '/buddy_web_interface.html'
        super().do_GET()
    
    def log_message(self, format, *args):
        # Custom logging
        print(f"[Web Server] {format % args}")

def start_web_server(port=3000):
    """Start the BUDDY web interface server with universal port management"""
    
    # Use universal port manager if available
    if UNIVERSAL_PORT_AVAILABLE:
        # Configure for web server
        config = PortConfig(
            port=port,
            fallback_ports=[3000, 3001, 3002, 8080, 8081, 8082, 5000]
        )
        port_manager = UniversalPortManager(config)
        server_config = port_manager.get_server_config()
        actual_port = server_config['port']
    else:
        actual_port = port
    
    try:
        with socketserver.TCPServer(("", actual_port), BuddyWebHandler) as httpd:
            print(f"🌐 BUDDY Web Interface Server")
            print(f"=" * 50)
            
            if UNIVERSAL_PORT_AVAILABLE:
                urls = server_config['urls']
                print(f"📡 Local Access: {urls.get('local', f'http://localhost:{actual_port}')}")
                print(f"🌍 Network Access: {urls.get('network', f'http://localhost:{actual_port}')}")
                if 'external' in urls:
                    print(f"🌐 External URL: {urls['external']}")
                print(f"🔗 Environment: {server_config['environment'].upper()}")
            else:
                print(f"📡 Server running at: http://localhost:{actual_port}")
            
            print(f"🚀 BUDDY API running at: http://{get_host()}:{get_port()}")
            print(f"🔗 Communication Hub: {get_ws_base()}")
            print(f"=" * 50)
            print(f"✅ Ready! Opening web interface...")
            print(f"🔄 Press Ctrl+C to stop the server")
            print()
            
            # Open browser after a short delay
            def open_browser():
                time.sleep(1)
                if UNIVERSAL_PORT_AVAILABLE and 'external' in server_config['urls']:
                    webbrowser.open(server_config['urls']['external'])
                else:
                    webbrowser.open(f'http://localhost:{actual_port}')
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            # Start serving
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print(f"\n🛑 Shutting down BUDDY Web Interface Server...")
    except OSError as e:
        if e.errno == 10048:  # Port already in use
            print(f"❌ Port {actual_port} is already in use. Trying port {actual_port + 1}...")
            start_web_server(actual_port + 1)
        else:
            print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    import sys
    
    # Auto-configure for environment
    if UNIVERSAL_PORT_AVAILABLE:
        auto_configure()
    
    # Check if port is specified
    port = 3000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number. Using default port 3000.")
    
    start_web_server(port)
