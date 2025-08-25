"""
🔗 BUDDY 2.0 Firebase-Render API Bridge

This module automatically connects your Render backend with Firebase
to show real-time "Online/Offline" status in your frontend.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, db

logger = logging.getLogger(__name__)

class BuddyStatusBridge:
    """
    Bridge between Render backend and Firebase frontend
    Automatically updates BUDDY's online/offline status
    """
    
    def __init__(self):
        self.firebase_app = None
        self.status_ref = None
        self.is_connected = False
        
    async def initialize_firebase(self):
        """Initialize Firebase connection for status updates"""
        try:
            # Skip if already initialized
            if self.is_connected:
                return True
                
            # Try to get Firebase service account from file first
            service_account_path = "config/firebase-service-account.json"
            cred = None
            
            if os.path.exists(service_account_path):
                # Use service account file (local development)
                cred = credentials.Certificate(service_account_path)
                logger.info("Using Firebase service account file")
            else:
                # Use environment variables (production deployment)
                logger.info("Firebase service account file not found, trying environment variables...")
                
                # Debug: Check what environment variables we have
                firebase_env_vars = {
                    "FIREBASE_PROJECT_ID": os.getenv("FIREBASE_PROJECT_ID"),
                    "FIREBASE_PRIVATE_KEY_ID": os.getenv("FIREBASE_PRIVATE_KEY_ID"), 
                    "FIREBASE_CLIENT_EMAIL": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "FIREBASE_CLIENT_ID": os.getenv("FIREBASE_CLIENT_ID"),
                    "FIREBASE_PRIVATE_KEY": "***" if os.getenv("FIREBASE_PRIVATE_KEY") else None
                }
                logger.info(f"Available Firebase env vars: {firebase_env_vars}")
                
                firebase_config = {
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID", "buddyai-42493"),
                    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                    "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('FIREBASE_CLIENT_EMAIL', '').replace('@', '%40')}",
                    "universe_domain": "googleapis.com"
                }
                
                # Check if we have the required environment variables
                if firebase_config["private_key_id"] and firebase_config["private_key"] and firebase_config["client_email"]:
                    logger.info("✅ All required Firebase environment variables found")
                    cred = credentials.Certificate(firebase_config)
                    logger.info("Using Firebase credentials from environment variables")
                else:
                    missing_vars = []
                    if not firebase_config["private_key_id"]: missing_vars.append("FIREBASE_PRIVATE_KEY_ID")
                    if not firebase_config["private_key"]: missing_vars.append("FIREBASE_PRIVATE_KEY") 
                    if not firebase_config["client_email"]: missing_vars.append("FIREBASE_CLIENT_EMAIL")
                    logger.warning(f"❌ Missing Firebase environment variables: {missing_vars}")
                    return False
            
            if not cred:
                logger.warning("No Firebase credentials available")
                return False
                
            # Firebase project configuration
            config = {
                'databaseURL': 'https://buddyai-42493-default-rtdb.firebaseio.com'
            }
            
            # Initialize Firebase app
            self.firebase_app = firebase_admin.initialize_app(cred, config, name="buddy-status")
            
            # Get database reference for status
            self.status_ref = db.reference('status/buddy', app=self.firebase_app)
            
            self.is_connected = True
            logger.info("✅ Firebase Status Bridge connected successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Firebase Status Bridge failed: {e}")
            return False
    
    async def set_buddy_online(self, render_url: str = None):
        """Set BUDDY status to ONLINE in Firebase"""
        try:
            if not self.is_connected:
                await self.initialize_firebase()
                
            if not self.is_connected:
                return False
                
            # Get Render URL
            if not render_url:
                render_url = os.getenv("RENDER_EXTERNAL_URL", "https://buddy-backend.onrender.com")
            
            # Status data
            status_data = {
                "status": "online",
                "backend_url": render_url,
                "last_updated": datetime.utcnow().isoformat(),
                "timestamp": datetime.utcnow().timestamp(),
                "version": "2.0",
                "deployment": "render",
                "capabilities": [
                    "chat",
                    "voice_processing", 
                    "mongodb_storage",
                    "vector_memory",
                    "cross_device_sync"
                ],
                "endpoints": {
                    "chat": f"{render_url}/chat",
                    "health": f"{render_url}/health",
                    "status": f"{render_url}/status",
                    "config": f"{render_url}/config"
                }
            }
            
            # Update Firebase Realtime Database
            self.status_ref.set(status_data)
            
            logger.info(f"🟢 BUDDY status set to ONLINE: {render_url}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to set BUDDY online: {e}")
            return False
    
    async def set_buddy_offline(self):
        """Set BUDDY status to OFFLINE in Firebase"""
        try:
            if not self.is_connected:
                return False
                
            status_data = {
                "status": "offline",
                "last_updated": datetime.utcnow().isoformat(),
                "timestamp": datetime.utcnow().timestamp(),
                "version": "2.0",
                "reason": "backend_shutdown"
            }
            
            self.status_ref.set(status_data)
            
            logger.info("🔴 BUDDY status set to OFFLINE")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to set BUDDY offline: {e}")
            return False
    
    async def update_activity(self, activity_type: str, metadata: Dict = None):
        """Update BUDDY's last activity in Firebase"""
        try:
            if not self.is_connected:
                return False
                
            activity_data = {
                "type": activity_type,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            # Update last activity
            activity_ref = db.reference('status/buddy/last_activity', app=self.firebase_app)
            activity_ref.set(activity_data)
            
            # Update heartbeat
            heartbeat_ref = db.reference('status/buddy/heartbeat', app=self.firebase_app)
            heartbeat_ref.set(datetime.utcnow().timestamp())
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update activity: {e}")
            return False

# Global status bridge instance
status_bridge = BuddyStatusBridge()

# FastAPI Integration Functions
async def startup_firebase_bridge():
    """Call this on FastAPI startup"""
    await status_bridge.initialize_firebase()
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    await status_bridge.set_buddy_online(render_url)

async def shutdown_firebase_bridge():
    """Call this on FastAPI shutdown"""
    await status_bridge.set_buddy_offline()

async def log_chat_activity(user_id: str, message_length: int):
    """Log chat activity to Firebase"""
    await status_bridge.update_activity("chat", {
        "user_id": user_id,
        "message_length": message_length
    })

# React Frontend Configuration Generator
def generate_frontend_config(render_url: str) -> Dict[str, Any]:
    """Generate configuration for React frontend"""
    return {
        "api": {
            "base_url": render_url,
            "endpoints": {
                "chat": f"{render_url}/chat",
                "health": f"{render_url}/health", 
                "status": f"{render_url}/status",
                "config": f"{render_url}/config"
            }
        },
        "firebase": {
            "project_id": "buddyai-42493",
            "database_url": "https://buddyai-42493-default-rtdb.firebaseio.com",
            "status_path": "status/buddy"
        },
        "polling": {
            "health_check_interval": 30000,  # 30 seconds
            "status_check_interval": 10000   # 10 seconds
        }
    }

# React Frontend Code (JavaScript)
FRONTEND_INTEGRATION_CODE = '''
// Add this to your React app for automatic BUDDY status monitoring

import { useEffect, useState } from 'react';
import { database, ref, onValue } from 'firebase/database';

// Custom hook for BUDDY status
export const useBuddyStatus = () => {
  const [isOnline, setIsOnline] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [backendUrl, setBackendUrl] = useState(null);
  
  useEffect(() => {
    // Listen to Firebase status changes
    const statusRef = ref(database, 'status/buddy');
    
    const unsubscribe = onValue(statusRef, (snapshot) => {
      const status = snapshot.val();
      
      if (status) {
        setIsOnline(status.status === 'online');
        setLastUpdated(status.last_updated);
        setBackendUrl(status.backend_url);
        
        console.log('🤖 BUDDY Status Update:', status);
      } else {
        setIsOnline(false);
      }
    });
    
    return () => unsubscribe();
  }, []);
  
  return { isOnline, lastUpdated, backendUrl };
};

// Status indicator component
export const BuddyStatusIndicator = () => {
  const { isOnline, lastUpdated, backendUrl } = useBuddyStatus();
  
  return (
    <div className={`buddy-status ${isOnline ? 'online' : 'offline'}`}>
      <div className="status-dot"></div>
      <span>BUDDY is {isOnline ? 'Online' : 'Offline'}</span>
      {lastUpdated && (
        <small>Last seen: {new Date(lastUpdated).toLocaleTimeString()}</small>
      )}
    </div>
  );
};

// CSS for status indicator
const statusStyles = `
.buddy-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
}

.buddy-status.online {
  background: #e8f5e8;
  color: #2e7d2e;
}

.buddy-status.offline {
  background: #ffeaea;
  color: #d32f2f;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.buddy-status.online .status-dot {
  background: #4caf50;
}

.buddy-status.offline .status-dot {
  background: #f44336;
}
`;
'''

if __name__ == "__main__":
    # Test the status bridge
    async def test_bridge():
        print("🧪 Testing Firebase Status Bridge...")
        
        bridge = BuddyStatusBridge()
        success = await bridge.initialize_firebase()
        
        if success:
            print("✅ Firebase connected")
            
            # Test setting online status
            await bridge.set_buddy_online("https://test-backend.onrender.com")
            print("✅ Status set to online")
            
            # Test activity logging
            await bridge.update_activity("test", {"test": True})
            print("✅ Activity logged")
            
        else:
            print("❌ Firebase connection failed")
    
    # Run test
    asyncio.run(test_bridge())
