"""
Debug BUDDY Notifications Environment
"""

import os
from dotenv import load_dotenv
load_dotenv()

# Test environment directly
print("=== Environment Debug ===")
push_enabled = os.getenv('PUSH_NOTIFICATIONS_ENABLED', 'false')
print(f"PUSH_NOTIFICATIONS_ENABLED raw: '{push_enabled}'")
print(f"PUSH_NOTIFICATIONS_ENABLED == 'true': {push_enabled == 'true'}")
print(f"PUSH_NOTIFICATIONS_ENABLED.lower() == 'true': {push_enabled.lower() == 'true'}")

# Test the actual class initialization
import sys
sys.path.append('packages/core')

from buddy.notifications import BuddyPushNotifications

print("\n=== Class Debug ===")
notifications = BuddyPushNotifications()
print(f"notifications.enabled: {notifications.enabled}")
print(f"notifications.fcm_service_account_path: {notifications.fcm_service_account_path}")

status = notifications.get_status()
print(f"\n=== Status Debug ===")
for key, value in status.items():
    print(f"{key}: {value}")
