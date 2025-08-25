#!/usr/bin/env python3
"""
BUDDY 2.0 Cloud Startup Manager
Manages the startup of BUDDY with cloud database integration
"""

import os
import sys
import time
import subprocess
import requests
import threading
from pathlib import Path

class BuddyCloudManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.venv_python = self.base_dir / ".venv" / "Scripts" / "python.exe"
        self.backend_process = None
        self.web_process = None
        
    def check_environment(self):
        """Check if environment is properly configured"""
        print("🔧 Checking Environment...")
        
        # Check .env file
        env_file = self.base_dir / ".env"
        if not env_file.exists():
            print("❌ Error: .env file not found!")
            print("Please ensure .env file exists with MongoDB configuration.")
            return False
        
        # Check virtual environment
        if not self.venv_python.exists():
            print("❌ Error: Python virtual environment not found!")
            print("Please run: python -m venv .venv")
            return False
            
        print("✅ Environment OK")
        return True
    
    def start_backend(self):
        """Start BUDDY backend server"""
        print("🚀 Starting BUDDY Backend...")
        
        try:
            self.backend_process = subprocess.Popen(
                [str(self.venv_python), "enhanced_backend.py"],
                cwd=str(self.base_dir),
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # Wait for backend to start
            for i in range(30):  # 30 second timeout
                try:
                    response = requests.get("http://localhost:8082/health", timeout=2)
                    if response.status_code == 200:
                        print("✅ Backend started successfully!")
                        return True
                except:
                    time.sleep(1)
                    print(f"⏳ Waiting for backend... ({i+1}/30)")
            
            print("❌ Backend failed to start within 30 seconds")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return False
    
    def start_web_interface(self):
        """Start BUDDY web interface"""
        print("🌐 Starting Web Interface...")
        
        try:
            self.web_process = subprocess.Popen(
                [str(self.venv_python), "buddy_web_server.py"],
                cwd=str(self.base_dir),
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            time.sleep(3)  # Give web server time to start
            print("✅ Web interface started!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start web interface: {e}")
            return False
    
    def test_connection(self):
        """Test BUDDY connection and functionality"""
        print("🧪 Testing BUDDY Connection...")
        
        try:
            # Test health endpoint
            response = requests.get("http://localhost:8082/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                db_status = health_data.get('database', {}).get('status', 'unknown')
                print(f"✅ Health Check: OK (Database: {db_status})")
            else:
                print(f"❌ Health Check Failed: {response.status_code}")
                return False
            
            # Test chat
            chat_data = {
                "message": "Hello BUDDY! Test cloud connection.",
                "user_id": "startup_test",
                "session_id": "startup_session"
            }
            
            response = requests.post("http://localhost:8082/chat", json=chat_data, timeout=15)
            if response.status_code == 200:
                print("✅ Chat Test: OK")
            else:
                print(f"❌ Chat Test Failed: {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def start(self):
        """Start BUDDY with cloud database"""
        print("=" * 50)
        print("🤖 BUDDY 2.0 - Cloud Startup Manager")
        print("=" * 50)
        print()
        
        # Check environment
        if not self.check_environment():
            return False
        
        # Start backend
        if not self.start_backend():
            return False
        
        # Start web interface
        if not self.start_web_interface():
            return False
        
        # Test connection
        if not self.test_connection():
            print("⚠️  Warning: Connection test failed, but servers are running")
        
        print()
        print("🎉 BUDDY 2.0 is now running with Cloud Database!")
        print("=" * 50)
        print("📊 Backend API: http://localhost:8082")
        print("🌐 Web Interface: http://localhost:3000")
        print("💾 Database: MongoDB Atlas (Cloud)")
        print("📝 Chat: Available at web interface")
        print("=" * 50)
        print()
        print("Press Ctrl+C to stop all services...")
        
        try:
            # Keep script running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down BUDDY...")
            self.stop()
    
    def stop(self):
        """Stop all BUDDY services"""
        if self.backend_process:
            self.backend_process.terminate()
            print("✅ Backend stopped")
        
        if self.web_process:
            self.web_process.terminate()
            print("✅ Web interface stopped")
        
        print("👋 BUDDY stopped successfully!")

if __name__ == "__main__":
    manager = BuddyCloudManager()
    manager.start()
