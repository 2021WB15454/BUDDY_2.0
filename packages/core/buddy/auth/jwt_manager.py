# BUDDY 2.0 - JWT Authentication System
# Implements Access Token + Refresh Token strategy for cross-device security

import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    IOS = "ios"
    ANDROID = "android"
    DESKTOP = "desktop"
    SMARTWATCH = "smartwatch"
    TV = "tv"
    CAR = "car"
    WEB = "web"

@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int

@dataclass
class DeviceSession:
    device_id: str
    device_type: str
    device_name: str
    user_agent: str
    ip_address: str
    last_used: datetime
    created_at: datetime

class BuddyAuthManager:
    """Authentication manager supporting JWT rotation, JTI revocation and audit logging."""

    def __init__(self,
                 jwt_secret: str,
                 mongo_client: AsyncIOMotorClient,
                 database_name: str = "buddy_db",
                 rotated_secrets: Optional[Dict[str, str]] = None,
                 active_kid: str = "primary"):
        # Key rotation state
        self.jwt_secrets: Dict[str, str] = rotated_secrets.copy() if rotated_secrets else {active_kid: jwt_secret}
        if active_kid not in self.jwt_secrets:
            self.jwt_secrets[active_kid] = jwt_secret
        self.active_kid = active_kid
        self.jwt_secret = self.jwt_secrets[self.active_kid]
        # DB and collections
        self.mongo_client = mongo_client
        self.db = mongo_client[database_name]
        self.refresh_tokens = self.db.refresh_tokens
        self.device_sessions = self.db.device_sessions
        self.token_blacklist = self.db.token_blacklist
        self.audit = self.db.audit_events
        self.revoked_jti = self.db.revoked_jti
        # Expiry config
        self.access_token_expiry = timedelta(minutes=30)
        self.refresh_token_expiry = timedelta(days=7)
        self.device_refresh_expiry = {
            DeviceType.IOS: timedelta(days=30),
            DeviceType.ANDROID: timedelta(days=30),
            DeviceType.DESKTOP: timedelta(days=7),
            DeviceType.SMARTWATCH: timedelta(days=14),
            DeviceType.TV: timedelta(days=30),
            DeviceType.CAR: timedelta(days=90),
            DeviceType.WEB: timedelta(days=1)
        }
    
    async def initialize_collections(self):
        """Initialize MongoDB collections with proper indexes"""
        try:
            # Create TTL index for refresh tokens
            await self.refresh_tokens.create_index(
                "expires_at", 
                expireAfterSeconds=0,
                name="refresh_token_ttl"
            )
            
            # Create index for device sessions
            await self.device_sessions.create_index([
                ("user_id", 1),
                ("device_id", 1)
            ], unique=True, name="user_device_unique")
            
            # Create TTL index for token blacklist
            await self.token_blacklist.create_index(
                "expires_at",
                expireAfterSeconds=0,
                name="blacklist_ttl"
            )
            
            # Create compound indexes for performance
            await self.refresh_tokens.create_index([
                ("user_id", 1),
                ("device_id", 1),
                ("is_active", 1)
            ], name="refresh_token_lookup")
            
            # Revoked JTI TTL index
            await self.revoked_jti.create_index(
                "exp",
                expireAfterSeconds=0,
                name="revoked_jti_ttl"
            )

            await self.audit.create_index([("ts", -1)])

            logger.info("Authentication collections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize auth collections: {e}")
            raise
    
    def _generate_access_token(self, 
                              user_id: str, 
                              device_id: str, 
                              device_type: DeviceType,
                              roles: Optional[List[str]] = None,
                              additional_claims: Optional[Dict] = None) -> str:
        """
        Generate a short-lived JWT access token
        
        Args:
            user_id: User identifier
            device_id: Unique device identifier
            device_type: Type of device
            additional_claims: Additional JWT claims
            
        Returns:
            JWT access token string
        """
        now = datetime.now(timezone.utc)
        expiry = now + self.access_token_expiry
        
        import uuid
        jti = str(uuid.uuid4())
        claims = {
            "sub": user_id,
            "device_id": device_id,
            "device_type": device_type.value,
            "iat": int(now.timestamp()),
            "exp": int(expiry.timestamp()),
            "iss": "buddy-ai",
            "aud": "buddy-api",
            "jti": jti
        }
        
        if roles:
            claims["roles"] = roles
        if additional_claims:
            claims.update(additional_claims)
        
        headers = {"kid": self.active_kid}
        return jwt.encode(claims, self.jwt_secret, algorithm="HS256", headers=headers)

    async def rotate_key(self, kid: str, new_secret: str, activate: bool = True):
        """Add a new secret (kid) and optionally activate it."""
        self.jwt_secrets[kid] = new_secret
        if activate:
            self.active_kid = kid
            self.jwt_secret = new_secret
        await self.audit.insert_one({"type": "key_rotation", "kid": kid, "active": activate, "ts": datetime.utcnow()})

    async def revoke_jti(self, jti: str, exp: int):
        await self.revoked_jti.update_one({"jti": jti}, {"$set": {"jti": jti, "exp": datetime.fromtimestamp(exp)}}, upsert=True)
        await self.audit.insert_one({"type": "token_revoked", "jti": jti, "ts": datetime.utcnow()})

    async def log_audit(self, event_type: str, data: Dict):
        try:
            await self.audit.insert_one({"type": event_type, "data": data, "ts": datetime.utcnow()})
        except Exception:
            pass
    
    def _generate_refresh_token(self) -> str:
        """Generate a cryptographically secure refresh token"""
        return secrets.token_urlsafe(64)
    
    def _hash_refresh_token(self, token: str) -> str:
        """Hash refresh token for secure storage"""
        return bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_refresh_token(self, token: str, hashed_token: str) -> bool:
        """Verify refresh token against hash"""
        return bcrypt.checkpw(token.encode('utf-8'), hashed_token.encode('utf-8'))
    
    async def authenticate_user(self, 
                               user_id: str,
                               device_id: str,
                               device_type: DeviceType,
                               device_name: str,
                               user_agent: str = "",
                               ip_address: str = "",
                               roles: Optional[List[str]] = None) -> TokenPair:
        """
        Authenticate user and create new token pair
        
        Args:
            user_id: User identifier
            device_id: Unique device identifier
            device_type: Type of device
            device_name: Human-readable device name
            user_agent: User agent string
            ip_address: Client IP address
            
        Returns:
            TokenPair with access and refresh tokens
        """
        try:
            # Generate tokens
            access_token = self._generate_access_token(user_id, device_id, device_type, roles=roles)
            refresh_token = self._generate_refresh_token()
            hashed_refresh_token = self._hash_refresh_token(refresh_token)
            
            # Calculate expiry based on device type
            refresh_expiry = self.device_refresh_expiry.get(
                device_type, 
                self.refresh_token_expiry
            )
            expires_at = datetime.now(timezone.utc) + refresh_expiry
            
            # Store refresh token in database
            refresh_doc = {
                "user_id": user_id,
                "device_id": device_id,
                "refresh_token_hash": hashed_refresh_token,
                "device_type": device_type.value,
                "device_name": device_name,
                "user_agent": user_agent,
                "ip_address": ip_address,
                "created_at": datetime.now(timezone.utc),
                "last_used": datetime.now(timezone.utc),
                "expires_at": expires_at,
                "is_active": True
            }
            
            # Replace existing refresh token for this device
            await self.refresh_tokens.replace_one(
                {"user_id": user_id, "device_id": device_id},
                refresh_doc,
                upsert=True
            )
            
            # Update device session
            session_doc = {
                "user_id": user_id,
                "device_id": device_id,
                "device_type": device_type.value,
                "device_name": device_name,
                "user_agent": user_agent,
                "ip_address": ip_address,
                "last_used": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.device_sessions.replace_one(
                {"user_id": user_id, "device_id": device_id},
                session_doc,
                upsert=True
            )
            
            logger.info(f"User {user_id} authenticated on device {device_id} ({device_type.value})")
            await self.log_audit("login", {"user_id": user_id, "device_id": device_id, "device_type": device_type.value})
            
            return TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=int(self.access_token_expiry.total_seconds()),
                refresh_expires_in=int(refresh_expiry.total_seconds())
            )
            
        except Exception as e:
            logger.error(f"Authentication failed for user {user_id}: {e}")
            raise
    
    async def refresh_access_token(self, 
                                  refresh_token: str,
                                  device_id: str,
                                  ip_address: str = "") -> Optional[TokenPair]:
        """
        Refresh access token using refresh token (with rotation)
        
        Args:
            refresh_token: Current refresh token
            device_id: Device identifier
            ip_address: Client IP address
            
        Returns:
            New TokenPair or None if refresh failed
        """
        try:
            # Find refresh token in database
            token_doc = await self.refresh_tokens.find_one({
                "device_id": device_id,
                "is_active": True,
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            })
            
            if not token_doc:
                logger.warning(f"No valid refresh token found for device {device_id}")
                return None
            
            # Verify refresh token
            if not self._verify_refresh_token(refresh_token, token_doc["refresh_token_hash"]):
                logger.warning(f"Invalid refresh token for device {device_id}")
                # Invalidate the token as it might be compromised
                await self.revoke_device_session(token_doc["user_id"], device_id)
                return None
            
            # Generate new tokens
            device_type = DeviceType(token_doc["device_type"])
            new_access_token = self._generate_access_token(
                token_doc["user_id"], 
                device_id, 
                device_type
            )
            new_refresh_token = self._generate_refresh_token()
            new_hashed_refresh_token = self._hash_refresh_token(new_refresh_token)
            
            # Calculate new expiry
            refresh_expiry = self.device_refresh_expiry.get(
                device_type, 
                self.refresh_token_expiry
            )
            new_expires_at = datetime.now(timezone.utc) + refresh_expiry
            
            # Update refresh token (rotation)
            await self.refresh_tokens.update_one(
                {"_id": token_doc["_id"]},
                {
                    "$set": {
                        "refresh_token_hash": new_hashed_refresh_token,
                        "last_used": datetime.now(timezone.utc),
                        "expires_at": new_expires_at,
                        "ip_address": ip_address
                    }
                }
            )
            
            # Update device session
            await self.device_sessions.update_one(
                {"user_id": token_doc["user_id"], "device_id": device_id},
                {
                    "$set": {
                        "last_used": datetime.now(timezone.utc),
                        "ip_address": ip_address
                    }
                }
            )
            
            logger.info(f"Access token refreshed for user {token_doc['user_id']} on device {device_id}")
            await self.log_audit("refresh", {"user_id": token_doc['user_id'], "device_id": device_id})
            
            return TokenPair(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_in=int(self.access_token_expiry.total_seconds()),
                refresh_expires_in=int(refresh_expiry.total_seconds())
            )
            
        except Exception as e:
            logger.error(f"Token refresh failed for device {device_id}: {e}")
            return None
    
    async def verify_access_token(self, token: str) -> Optional[Dict]:
        """
        Verify JWT access token
        
        Args:
            token: JWT access token
            
        Returns:
            Token claims if valid, None otherwise
        """
        try:
            unverified = jwt.get_unverified_header(token)
            kid = unverified.get("kid", self.active_kid)
            secret = self.jwt_secrets.get(kid)
            if not secret:
                logger.warning(f"Unknown kid {kid}")
                return None
            claims = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="buddy-api",
                issuer="buddy-ai"
            )
            # Revocation check
            jti = claims.get("jti")
            if jti:
                existing = await self.revoked_jti.find_one({"jti": jti})
                if existing:
                    logger.info("token_jti_revoked", extra={"jti": jti})
                    return None
            
            return claims
            
        except jwt.ExpiredSignatureError:
            logger.debug("Access token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid access token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None

    # Synchronous compatibility wrapper (legacy callers)
    def verify_access_token_sync(self, token: str) -> Optional[Dict]:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            # Cannot block; schedule task and return None (caller should migrate to async)
            # For safety, we fallback to creating a task and ignoring result here.
            asyncio.ensure_future(self.verify_access_token(token))
            return None
        return loop.run_until_complete(self.verify_access_token(token))
    
    async def get_user_devices(self, user_id: str) -> List['DeviceSession']:
        """
        Get all active devices for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of active device sessions
        """
        try:
            cursor = self.device_sessions.find({"user_id": user_id})
            devices = []
            
            async for doc in cursor:
                devices.append(DeviceSession(device_id=doc["device_id"], device_type=str(DeviceType(doc["device_type"]).value), device_name=doc.get("device_name", ""), user_agent=doc.get("user_agent", ""), ip_address=doc.get("ip_address", ""), last_used=doc.get("last_used", datetime.utcnow()), created_at=doc.get("created_at", datetime.utcnow())))
            
            return devices
            
        except Exception as e:
            logger.error(f"Failed to get devices for user {user_id}: {e}")
            return []
    
    async def revoke_device_session(self, user_id: str, device_id: str) -> bool:
        """
        Revoke a specific device session
        
        Args:
            user_id: User identifier
            device_id: Device identifier
            
        Returns:
            True if revoked successfully
        """
        try:
            # Deactivate refresh token
            result1 = await self.refresh_tokens.update_one(
                {"user_id": user_id, "device_id": device_id},
                {"$set": {"is_active": False}}
            )
            
            # Remove device session
            result2 = await self.device_sessions.delete_one(
                {"user_id": user_id, "device_id": device_id}
            )
            
            logger.info(f"Device session revoked for user {user_id}, device {device_id}")
            return result1.modified_count > 0 or result2.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to revoke device session: {e}")
            return False
    
    async def revoke_all_user_sessions(self, user_id: str) -> bool:
        """
        Revoke all sessions for a user (e.g., on password change)
        
        Args:
            user_id: User identifier
            
        Returns:
            True if revoked successfully
        """
        try:
            # Deactivate all refresh tokens
            await self.refresh_tokens.update_many(
                {"user_id": user_id},
                {"$set": {"is_active": False}}
            )
            
            # Remove all device sessions
            await self.device_sessions.delete_many({"user_id": user_id})
            
            logger.info(f"All sessions revoked for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke all sessions for user {user_id}: {e}")
            return False
    
    async def cleanup_expired_tokens(self):
        """
        Cleanup expired tokens and sessions (run periodically)
        """
        try:
            now = datetime.now(timezone.utc)
            
            # Remove expired refresh tokens
            result1 = await self.refresh_tokens.delete_many({
                "expires_at": {"$lt": now}
            })
            
            # Remove inactive refresh tokens
            result2 = await self.refresh_tokens.delete_many({
                "is_active": False
            })
            
            # Remove orphaned device sessions
            valid_device_ids = await self.refresh_tokens.distinct(
                "device_id", 
                {"is_active": True}
            )
            
            result3 = await self.device_sessions.delete_many({
                "device_id": {"$nin": valid_device_ids}
            })
            
            logger.info(f"Cleanup completed: {result1.deleted_count} expired tokens, "
                       f"{result2.deleted_count} inactive tokens, "
                       f"{result3.deleted_count} orphaned sessions")
            
        except Exception as e:
            logger.error(f"Token cleanup failed: {e}")

# Security utilities
class AuthSecurityUtils:
    """Security utilities for authentication"""
    
    @staticmethod
    def generate_device_id(device_type: DeviceType, 
                          platform_id: Optional[str] = None) -> str:
        """
        Generate a unique device ID
        
        Args:
            device_type: Type of device
            platform_id: Platform-specific identifier
            
        Returns:
            Unique device identifier
        """
        if platform_id:
            return f"{device_type.value}-{platform_id}"
        else:
            return f"{device_type.value}-{secrets.token_hex(8)}"
    
    @staticmethod
    def is_suspicious_location(current_ip: str, 
                             previous_ips: List[str], 
                             threshold: int = 3) -> bool:
        """
        Simple suspicious location detection
        
        Args:
            current_ip: Current IP address
            previous_ips: List of previous IP addresses
            threshold: Number of recent IPs to check
            
        Returns:
            True if location seems suspicious
        """
        if not previous_ips:
            return False
            
        recent_ips = previous_ips[-threshold:]
        return current_ip not in recent_ips
    
    @staticmethod
    def extract_ip_from_request(request) -> str:
        """
        Extract real IP address from request
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
