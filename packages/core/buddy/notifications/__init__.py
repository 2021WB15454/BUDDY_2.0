"""
BUDDY 2.0 - Push Notifications Module
Firebase Cloud Messaging Integration
"""

import os
import json
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
import asyncio

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

logger = logging.getLogger(__name__)

class BuddyPushNotifications:
    """
    Firebase Cloud Messaging integration for BUDDY 2.0
    Supports cross-device push notifications with intelligent routing
    """
    
    def __init__(self):
        self.enabled = os.getenv('PUSH_NOTIFICATIONS_ENABLED', 'false').lower() == 'true'
        self.test_mode = os.getenv('NOTIFICATION_TEST_MODE', 'true').lower() == 'true'
        self.dry_run = os.getenv('NOTIFICATION_DRY_RUN', 'false').lower() == 'true'
        
        # Firebase configuration
        self.fcm_server_key = os.getenv('FCM_SERVER_KEY')
        self.fcm_service_account_path = os.getenv('FCM_SERVICE_ACCOUNT_PATH')
        self.fcm_project_id = os.getenv('FCM_PROJECT_ID', 'buddyai-42493')
        
        # Notification settings
        self.batch_size = int(os.getenv('NOTIFICATION_BATCH_SIZE', '100'))
        self.retry_attempts = int(os.getenv('NOTIFICATION_RETRY_ATTEMPTS', '3'))
        self.retry_delay = int(os.getenv('NOTIFICATION_RETRY_DELAY_SECONDS', '5'))
        
        self.firebase_app = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        if not FIREBASE_AVAILABLE:
            logger.warning("Firebase Admin SDK not available. Install with: pip install firebase-admin")
            return
        
        if not self.enabled:
            logger.info("Push notifications disabled in configuration")
            return
        
        try:
            # Check if Firebase app already exists
            try:
                self.firebase_app = firebase_admin.get_app()
                logger.info("Using existing Firebase app")
                return
            except ValueError:
                # No app exists, create new one
                pass
            
            # Initialize with service account
            if self.fcm_service_account_path and os.path.exists(self.fcm_service_account_path):
                cred = credentials.Certificate(self.fcm_service_account_path)
                self.firebase_app = firebase_admin.initialize_app(cred, {
                    'projectId': self.fcm_project_id
                })
                logger.info(f"Firebase initialized with service account for project: {self.fcm_project_id}")
            else:
                logger.warning("Firebase service account file not found. Using server key method.")
                
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.enabled = False
    
    async def send_notification(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict] = None,
        platform: str = "auto",
        priority: str = "normal"
    ) -> Dict:
        """
        Send push notification to a single device
        
        Args:
            device_token: FCM device token
            title: Notification title
            body: Notification body
            data: Additional data payload
            platform: Target platform (ios, android, web, auto)
            priority: Notification priority (high, normal)
        
        Returns:
            Dict with success status and message ID
        """
        if not self.enabled or not FIREBASE_AVAILABLE:
            logger.info(f"Notification skipped (disabled): {title}")
            return {"success": False, "reason": "notifications_disabled"}
        
        if self.dry_run:
            logger.info(f"DRY RUN - Notification: {title} -> {device_token[:10]}...")
            return {"success": True, "message_id": "dry_run", "dry_run": True}
        
        try:
            # Build notification message
            message = self._build_message(device_token, title, body, data, platform, priority)
            
            # Send notification
            if self.test_mode:
                logger.info(f"TEST MODE - Sending notification: {title}")
            
            response = messaging.send(message, dry_run=self.test_mode)
            
            logger.info(f"Notification sent successfully: {response}")
            return {
                "success": True,
                "message_id": response,
                "test_mode": self.test_mode
            }
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return {
                "success": False,
                "error": str(e),
                "device_token": device_token[:10] + "..."
            }
    
    async def send_multicast(
        self,
        device_tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict] = None,
        platform: str = "auto"
    ) -> Dict:
        """
        Send notification to multiple devices
        
        Args:
            device_tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Additional data payload
            platform: Target platform (ios, android, web, auto)
        
        Returns:
            Dict with batch results
        """
        if not self.enabled or not FIREBASE_AVAILABLE:
            logger.info(f"Multicast notification skipped (disabled): {title}")
            return {"success": False, "reason": "notifications_disabled"}
        
        if self.dry_run:
            logger.info(f"DRY RUN - Multicast notification: {title} -> {len(device_tokens)} devices")
            return {
                "success": True,
                "success_count": len(device_tokens),
                "failure_count": 0,
                "dry_run": True
            }
        
        try:
            # Build multicast message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                tokens=device_tokens
            )
            
            # Send to all devices
            response = messaging.send_multicast(message, dry_run=self.test_mode)
            
            logger.info(f"Multicast notification sent: {response.success_count}/{len(device_tokens)} successful")
            
            return {
                "success": True,
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "responses": [
                    {
                        "success": resp.success,
                        "message_id": resp.message_id if resp.success else None,
                        "error": str(resp.exception) if not resp.success else None
                    }
                    for resp in response.responses
                ],
                "test_mode": self.test_mode
            }
            
        except Exception as e:
            logger.error(f"Failed to send multicast notification: {e}")
            return {
                "success": False,
                "error": str(e),
                "device_count": len(device_tokens)
            }
    
    def _build_message(
        self,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict],
        platform: str,
        priority: str
    ) -> messaging.Message:
        """Build FCM message based on platform and priority"""
        
        # Base notification
        notification = messaging.Notification(title=title, body=body)
        
        # Platform-specific configuration
        android_config = None
        apns_config = None
        webpush_config = None
        
        if platform in ["android", "auto"]:
            android_config = messaging.AndroidConfig(
                priority=priority,
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    icon="buddy_icon",
                    color="#4A90E2",
                    sound="default" if priority == "high" else None,
                    tag="buddy_notification"
                ),
                data=data or {}
            )
        
        if platform in ["ios", "auto"]:
            # APNS configuration for iOS
            apns_config = messaging.APNSConfig(
                headers={
                    "apns-priority": "10" if priority == "high" else "5",
                    "apns-push-type": "alert"
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(title=title, body=body),
                        badge=1,
                        sound="default" if priority == "high" else None,
                        category="BUDDY_NOTIFICATION"
                    ),
                    custom_data=data or {}
                )
            )
        
        if platform in ["web", "auto"]:
            # Web push configuration
            webpush_config = messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=title,
                    body=body,
                    icon="/static/icons/buddy-icon-192.png",
                    badge="/static/icons/buddy-badge.png",
                    tag="buddy_notification",
                    require_interaction=(priority == "high"),
                    silent=(priority == "low")
                ),
                data=data or {}
            )
        
        return messaging.Message(
            token=device_token,
            notification=notification,
            data=data or {},
            android=android_config,
            apns=apns_config,
            webpush=webpush_config
        )
    
    async def send_buddy_sync_notification(
        self,
        device_tokens: Union[str, List[str]],
        source_device: str,
        conversation_id: str,
        update_type: str = "conversation_update"
    ) -> Dict:
        """Send cross-device sync notification"""
        
        title = "BUDDY Sync"
        body = f"Your conversation was updated on {source_device}"
        
        data = {
            "type": "sync_update",
            "conversation_id": conversation_id,
            "source_device": source_device,
            "update_type": update_type,
            "timestamp": datetime.utcnow().isoformat(),
            "click_action": f"buddy://conversation/{conversation_id}"
        }
        
        if isinstance(device_tokens, str):
            return await self.send_notification(device_tokens, title, body, data, priority="normal")
        else:
            return await self.send_multicast(device_tokens, title, body, data)
    
    async def send_reminder_notification(
        self,
        device_token: str,
        reminder_text: str,
        reminder_id: str,
        scheduled_time: datetime
    ) -> Dict:
        """Send reminder notification"""
        
        title = "BUDDY Reminder"
        body = reminder_text
        
        data = {
            "type": "reminder",
            "reminder_id": reminder_id,
            "scheduled_time": scheduled_time.isoformat(),
            "click_action": f"buddy://reminder/{reminder_id}"
        }
        
        return await self.send_notification(device_token, title, body, data, priority="high")
    
    async def send_smart_suggestion(
        self,
        device_token: str,
        suggestion: str,
        suggestion_type: str,
        context: Dict
    ) -> Dict:
        """Send smart suggestion notification"""
        
        title = "BUDDY Suggestion"
        body = suggestion
        
        data = {
            "type": "suggestion",
            "suggestion_type": suggestion_type,
            "context": json.dumps(context),
            "timestamp": datetime.utcnow().isoformat(),
            "click_action": "buddy://suggestions"
        }
        
        return await self.send_notification(device_token, title, body, data, priority="normal")
    
    def get_status(self) -> Dict:
        """Get notification system status"""
        service_account_exists = bool(
            self.fcm_service_account_path and 
            os.path.exists(self.fcm_service_account_path)
        )
        
        return {
            "enabled": self.enabled,
            "firebase_available": FIREBASE_AVAILABLE,
            "firebase_initialized": self.firebase_app is not None,
            "test_mode": self.test_mode,
            "dry_run": self.dry_run,
            "project_id": self.fcm_project_id,
            "service_account_configured": service_account_exists,
            "server_key_configured": bool(self.fcm_server_key),
            "service_account_path": self.fcm_service_account_path,
            "debug_env_enabled": os.getenv('PUSH_NOTIFICATIONS_ENABLED', 'false')
        }

# Global notification instance
push_notifications = BuddyPushNotifications()

# Convenience functions
async def send_push_notification(device_token: str, title: str, body: str, **kwargs):
    """Send a push notification - convenience function"""
    return await push_notifications.send_notification(device_token, title, body, **kwargs)

async def send_sync_notification(device_tokens, source_device: str, conversation_id: str):
    """Send sync notification - convenience function"""
    return await push_notifications.send_buddy_sync_notification(device_tokens, source_device, conversation_id)

def get_notification_status():
    """Get notification status - convenience function"""
    return push_notifications.get_status()
