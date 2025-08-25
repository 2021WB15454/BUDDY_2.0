"""
Firebase Integration for BUDDY 2.0 Backend

Manages real-time status updates, authentication, and data synchronization
between the Render backend and Firebase services.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db, auth
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class BuddyFirebaseManager:
    """
    Manages Firebase integration for BUDDY 2.0
    - Real-time status updates
    - User authentication
    - Cross-device synchronization
    """
    
    def __init__(self):
        self.app = None
        self.db_ref = None
        self.status_ref = None
        self.conversations_ref = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if already initialized
            if self.is_initialized:
                logger.info("Firebase already initialized")
                return True
                
            # Load service account from environment or file
            service_account_path = os.getenv(
                'FIREBASE_SERVICE_ACCOUNT_PATH', 
                'config/firebase-service-account.json'
            )
            
            if not os.path.exists(service_account_path):
                logger.warning(f"Firebase service account not found at {service_account_path}")
                return False
                
            # Initialize Firebase Admin SDK
            cred = credentials.Certificate(service_account_path)
            
            # Firebase project configuration
            firebase_config = {
                'databaseURL': f'https://buddyai-42493-default-rtdb.firebaseio.com',
                'projectId': 'buddyai-42493'
            }
            
            self.app = firebase_admin.initialize_app(cred, firebase_config)
            
            # Initialize database references
            self.db_ref = db.reference('/')
            self.status_ref = db.reference('status/buddy')
            self.conversations_ref = db.reference('conversations')
            self.users_ref = db.reference('users')
            
            self.is_initialized = True
            logger.info("Firebase Admin SDK initialized successfully")
            
            # Set initial online status
            await self.set_buddy_status("online")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            return False
    
    async def set_buddy_status(self, status: str, metadata: Optional[Dict] = None):
        """Update BUDDY's online/offline status in real-time"""
        try:
            if not self.is_initialized:
                logger.warning("Firebase not initialized")
                return False
                
            status_data = {
                'status': status,
                'last_updated': datetime.utcnow().isoformat(),
                'backend_url': os.getenv('RENDER_SERVICE_URL', 'https://buddy-2-0.onrender.com'),
                'version': '2.0',
                'capabilities': [
                    'voice_processing',
                    'conversation_ai',
                    'cross_device_sync',
                    'mongodb_storage',
                    'vector_memory'
                ]
            }
            
            if metadata:
                status_data.update(metadata)
                
            # Update Firebase Realtime Database
            self.status_ref.set(status_data)
            logger.info(f"BUDDY status updated to: {status}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update BUDDY status: {e}")
            return False
    
    async def log_conversation(self, user_id: str, conversation_data: Dict):
        """Log conversation to Firebase for cross-device sync"""
        try:
            if not self.is_initialized:
                return False
                
            conversation_entry = {
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'message': conversation_data.get('message', ''),
                'response': conversation_data.get('response', ''),
                'source_device': conversation_data.get('device_type', 'unknown'),
                'session_id': conversation_data.get('session_id', ''),
                'metadata': conversation_data.get('metadata', {})
            }
            
            # Push to conversations
            new_conversation_ref = self.conversations_ref.push(conversation_entry)
            logger.info(f"Conversation logged: {new_conversation_ref.key}")
            
            return new_conversation_ref.key
            
        except Exception as e:
            logger.error(f"Failed to log conversation: {e}")
            return None
    
    async def get_user_conversations(self, user_id: str, limit: int = 50):
        """Retrieve user conversations for context"""
        try:
            if not self.is_initialized:
                return []
                
            # Query conversations by user_id
            conversations_query = self.conversations_ref.order_by_child('user_id').equal_to(user_id).limit_to_last(limit)
            conversations = conversations_query.get()
            
            if not conversations:
                return []
                
            # Convert to list and sort by timestamp
            conversation_list = []
            for key, value in conversations.items():
                value['id'] = key
                conversation_list.append(value)
                
            conversation_list.sort(key=lambda x: x.get('timestamp', ''))
            
            return conversation_list
            
        except Exception as e:
            logger.error(f"Failed to get user conversations: {e}")
            return []
    
    async def verify_user_token(self, id_token: str):
        """Verify Firebase user authentication token"""
        try:
            if not self.is_initialized:
                return None
                
            # Verify the ID token
            decoded_token = auth.verify_id_token(id_token)
            user_id = decoded_token['uid']
            
            logger.info(f"User token verified: {user_id}")
            return decoded_token
            
        except Exception as e:
            logger.error(f"Failed to verify user token: {e}")
            return None
    
    async def update_user_profile(self, user_id: str, profile_data: Dict):
        """Update user profile in Firebase"""
        try:
            if not self.is_initialized:
                return False
                
            user_ref = self.users_ref.child(user_id)
            profile_data['last_updated'] = datetime.utcnow().isoformat()
            
            user_ref.update(profile_data)
            logger.info(f"User profile updated: {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
            return False
    
    async def broadcast_device_sync(self, user_id: str, sync_data: Dict):
        """Broadcast synchronization data to all user devices"""
        try:
            if not self.is_initialized:
                return False
                
            sync_entry = {
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'sync_type': sync_data.get('type', 'conversation'),
                'data': sync_data,
                'source_device': sync_data.get('source_device', 'backend')
            }
            
            # Push to user's sync queue
            sync_ref = db.reference(f'sync/{user_id}')
            new_sync_ref = sync_ref.push(sync_entry)
            
            logger.info(f"Device sync broadcasted: {new_sync_ref.key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to broadcast device sync: {e}")
            return False
    
    async def cleanup_old_data(self, days_old: int = 30):
        """Clean up old conversations and sync data"""
        try:
            if not self.is_initialized:
                return False
                
            cutoff_date = datetime.utcnow().replace(day=datetime.utcnow().day - days_old)
            cutoff_iso = cutoff_date.isoformat()
            
            # Clean old conversations
            old_conversations = self.conversations_ref.order_by_child('timestamp').end_at(cutoff_iso).get()
            
            if old_conversations:
                for key in old_conversations.keys():
                    self.conversations_ref.child(key).delete()
                    
                logger.info(f"Cleaned {len(old_conversations)} old conversations")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return False
    
    async def shutdown(self):
        """Gracefully shutdown Firebase connection"""
        try:
            if self.is_initialized:
                # Set offline status
                await self.set_buddy_status("offline", {
                    'shutdown_time': datetime.utcnow().isoformat()
                })
                
                # Delete the Firebase app
                firebase_admin.delete_app(self.app)
                self.is_initialized = False
                
                logger.info("Firebase connection closed")
                
        except Exception as e:
            logger.error(f"Error during Firebase shutdown: {e}")

# Global Firebase manager instance
firebase_manager = BuddyFirebaseManager()

async def get_firebase_manager():
    """Get the Firebase manager instance"""
    if not firebase_manager.is_initialized:
        await firebase_manager.initialize()
    return firebase_manager

@asynccontextmanager
async def firebase_context():
    """Context manager for Firebase operations"""
    manager = await get_firebase_manager()
    try:
        yield manager
    finally:
        # Manager stays alive for the application lifetime
        pass

# Utility functions for easy integration
async def update_buddy_online_status():
    """Set BUDDY status to online"""
    async with firebase_context() as firebase:
        return await firebase.set_buddy_status("online")

async def update_buddy_offline_status():
    """Set BUDDY status to offline"""
    async with firebase_context() as firebase:
        return await firebase.set_buddy_status("offline")

async def log_conversation_to_firebase(user_id: str, conversation: Dict):
    """Log a conversation to Firebase"""
    async with firebase_context() as firebase:
        return await firebase.log_conversation(user_id, conversation)

async def verify_firebase_user(id_token: str):
    """Verify a Firebase user token"""
    async with firebase_context() as firebase:
        return await firebase.verify_user_token(id_token)

if __name__ == "__main__":
    # Test Firebase integration
    async def test_firebase():
        print("Testing Firebase integration...")
        
        manager = await get_firebase_manager()
        if manager.is_initialized:
            print("✅ Firebase initialized successfully")
            
            # Test status update
            await manager.set_buddy_status("online", {"test": True})
            print("✅ Status update successful")
            
            # Test conversation logging
            test_conversation = {
                "message": "Hello BUDDY!",
                "response": "Hello! How can I help you?",
                "device_type": "web",
                "session_id": "test-session"
            }
            
            conv_id = await manager.log_conversation("test-user", test_conversation)
            print(f"✅ Conversation logged: {conv_id}")
            
        else:
            print("❌ Firebase initialization failed")
    
    asyncio.run(test_firebase())
