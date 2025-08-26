"""
BUDDY Web Interface Server
Simple HTTP server to serve the BUDDY web interface with CORS support
"""

import http.server
import socketserver
import os
import webbrowser
import threading
import time
from urllib.parse import urlparse, parse_qs
import json
from dynamic_config import get_host, get_port, get_ws_base

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
    """Start the BUDDY web interface server"""
    try:
        with socketserver.TCPServer(("", port), BuddyWebHandler) as httpd:
            print(f"🌐 BUDDY Web Interface Server")
            print(f"=" * 40)
            print(f"📡 Server running at: http://localhost:{port}")
            print(f"🚀 BUDDY API running at: http://{get_host()}:{get_port()}")
            print(f"🔗 Communication Hub: {get_ws_base()}")
            print(f"=" * 40)
            print(f"✅ Ready! Opening web interface...")
            print(f"🔄 Press Ctrl+C to stop the server")
            print()
            
            # Open browser after a short delay
            def open_browser():
                time.sleep(1)
                webbrowser.open(f'http://localhost:{port}')
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            # Start serving
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print(f"\n🛑 Shutting down BUDDY Web Interface Server...")
    except OSError as e:
        if e.errno == 10048:  # Port already in use
            print(f"❌ Port {port} is already in use. Trying port {port + 1}...")
            start_web_server(port + 1)
        else:
            print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    import sys
    
    # Check if port is specified
    port = 3000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number. Using default port 3000.")
    
    start_web_server(port)
