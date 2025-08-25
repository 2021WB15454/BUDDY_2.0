# BUDDY 2.0 - Authentication Module Initialization
# Main authentication module with configuration and setup

from .jwt_manager import BuddyAuthManager, DeviceType, TokenPair, DeviceSession, AuthSecurityUtils
from .api import BuddyAuthAPI, BuddyAuthMiddleware, create_auth_routes

__all__ = [
    "BuddyAuthManager",
    "BuddyAuthAPI", 
    "BuddyAuthMiddleware",
    "DeviceType",
    "TokenPair",
    "DeviceSession",
    "AuthSecurityUtils",
    "create_auth_routes"
]

# Authentication configuration
AUTH_CONFIG = {
    "access_token_expiry_minutes": 30,
    "refresh_token_expiry_days": 7,
    "device_specific_expiry": {
        "ios": 30,       # 30 days
        "android": 30,   # 30 days
        "desktop": 7,    # 7 days
        "smartwatch": 14, # 14 days
        "tv": 30,        # 30 days
        "car": 90,       # 90 days
        "web": 1         # 1 day
    },
    "max_concurrent_sessions": 10,
    "require_device_verification": False,
    "enable_suspicious_login_detection": True
}

async def initialize_buddy_auth(mongo_client, jwt_secret: str, config: dict = None) -> tuple:
    """
    Initialize BUDDY authentication system
    
    Args:
        mongo_client: MongoDB AsyncIOMotorClient
        jwt_secret: Secret key for JWT signing
        config: Optional configuration override
        
    Returns:
        Tuple of (BuddyAuthManager, BuddyAuthAPI)
    """
    # Use provided config or default
    auth_config = config or AUTH_CONFIG
    
    # Create authentication manager
    auth_manager = BuddyAuthManager(
        jwt_secret=jwt_secret,
        mongo_client=mongo_client
    )
    
    # Override expiry settings if provided
    if "access_token_expiry_minutes" in auth_config:
        from datetime import timedelta
        auth_manager.access_token_expiry = timedelta(
            minutes=auth_config["access_token_expiry_minutes"]
        )
    
    if "refresh_token_expiry_days" in auth_config:
        from datetime import timedelta
        auth_manager.refresh_token_expiry = timedelta(
            days=auth_config["refresh_token_expiry_days"]
        )
    
    # Update device-specific expiry settings
    if "device_specific_expiry" in auth_config:
        from datetime import timedelta
        for device_type, days in auth_config["device_specific_expiry"].items():
            try:
                device_enum = DeviceType(device_type)
                auth_manager.device_refresh_expiry[device_enum] = timedelta(days=days)
            except ValueError:
                pass  # Skip invalid device types
    
    # Initialize database collections
    await auth_manager.initialize_collections()
    
    # Create API wrapper
    auth_api = BuddyAuthAPI(auth_manager)
    
    return auth_manager, auth_api
