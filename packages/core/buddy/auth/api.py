# BUDDY 2.0 - Authentication API Endpoints
# FastAPI endpoints for JWT authentication with refresh token strategy

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorClient

from .jwt_manager import BuddyAuthManager, DeviceType, TokenPair, DeviceSession, AuthSecurityUtils

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Request/Response models
class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    device_id: str = Field(..., min_length=5, max_length=100)
    device_type: str = Field(..., pattern="^(ios|android|desktop|smartwatch|tv|car|web)$")
    device_name: str = Field(..., min_length=1, max_length=100)
    roles: Optional[List[str]] = Field(default=None, description="Optional role claims")

class RefreshRequest(BaseModel):
    """Token refresh request model"""
    refresh_token: str = Field(..., min_length=10)
    device_id: str = Field(..., min_length=5, max_length=100)

class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int

class DeviceInfo(BaseModel):
    """Device information model"""
    device_id: str
    device_type: str
    device_name: str
    last_used: datetime
    created_at: datetime
    ip_address: str

class UserDevicesResponse(BaseModel):
    """User devices response model"""
    devices: List[DeviceInfo]
    total_count: int

class AuthStatus(BaseModel):
    """Authentication status model"""
    authenticated: bool
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    expires_at: Optional[datetime] = None

class BuddyAuthAPI:
    """
    BUDDY Authentication API
    Provides FastAPI endpoints for JWT authentication
    """
    
    def __init__(self, 
                 auth_manager: BuddyAuthManager,
                 user_validator=None):
        """
        Initialize the authentication API
        
        Args:
            auth_manager: BuddyAuthManager instance
            user_validator: Function to validate user credentials
        """
        self.auth_manager = auth_manager
        self.user_validator = user_validator or self._default_user_validator
    
    async def _default_user_validator(self, username: str, password: str) -> Optional[str]:
        """
        Default user validator (replace with your user authentication logic)
        
        Args:
            username: Username
            password: Password
            
        Returns:
            User ID if valid, None otherwise
        """
        # TODO: Replace with actual user authentication
        # This is a placeholder for demonstration
        if username == "demo" and password == "password123":
            return "user_demo_001"
        return None
    
    async def login(self, request: Request, login_data: LoginRequest) -> TokenResponse:
        """
        User login endpoint
        
        Args:
            request: FastAPI request object
            login_data: Login request data
            
        Returns:
            Token response with access and refresh tokens
        """
        try:
            # Validate user credentials
            user_id = await self.user_validator(login_data.username, login_data.password)
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )
            
            # Extract request information
            ip_address = AuthSecurityUtils.extract_ip_from_request(request)
            user_agent = request.headers.get("User-Agent", "")
            
            # Convert device type
            try:
                device_type = DeviceType(login_data.device_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid device type"
                )
            
            # Check for suspicious activity (optional)
            user_devices = await self.auth_manager.get_user_devices(user_id)
            previous_ips = [device.ip_address for device in user_devices]
            
            if AuthSecurityUtils.is_suspicious_location(ip_address, previous_ips):
                logger.warning(f"Suspicious login attempt for user {user_id} from IP {ip_address}")
                # Could add additional verification here
            
            # Generate token pair
            token_pair = await self.auth_manager.authenticate_user(
                user_id=user_id,
                device_id=login_data.device_id,
                device_type=device_type,
                device_name=login_data.device_name,
                user_agent=user_agent,
                ip_address=ip_address,
                roles=login_data.roles or ["user"]
            )
            
            logger.info(f"User {user_id} logged in successfully from device {login_data.device_id}")
            
            return TokenResponse(
                access_token=token_pair.access_token,
                refresh_token=token_pair.refresh_token,
                expires_in=token_pair.expires_in,
                refresh_expires_in=token_pair.refresh_expires_in
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    
    async def refresh_token(self, request: Request, refresh_data: RefreshRequest) -> TokenResponse:
        """
        Refresh access token endpoint
        
        Args:
            request: FastAPI request object
            refresh_data: Refresh request data
            
        Returns:
            New token response
        """
        try:
            ip_address = AuthSecurityUtils.extract_ip_from_request(request)
            
            # Refresh the token
            token_pair = await self.auth_manager.refresh_access_token(
                refresh_token=refresh_data.refresh_token,
                device_id=refresh_data.device_id,
                ip_address=ip_address
            )
            
            if not token_pair:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token"
                )
            
            logger.debug(f"Token refreshed for device {refresh_data.device_id}")
            
            return TokenResponse(
                access_token=token_pair.access_token,
                refresh_token=token_pair.refresh_token,
                expires_in=token_pair.expires_in,
                refresh_expires_in=token_pair.refresh_expires_in
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh service unavailable"
            )
    
    async def logout(self, user_id: str, device_id: str, access_token: Optional[str] = None) -> Dict[str, str]:
        """
        Logout from specific device
        
        Args:
            user_id: User identifier
            device_id: Device identifier
            
        Returns:
            Success message
        """
        try:
            success = await self.auth_manager.revoke_device_session(user_id, device_id)
            # Revoke JTI of current access token (best-effort)
            if access_token:
                try:
                    claims = await self.auth_manager.verify_access_token(access_token)
                    if claims and claims.get("jti") and claims.get("exp"):
                        await self.auth_manager.revoke_jti(claims["jti"], claims["exp"])
                except Exception:
                    pass
            
            if success:
                logger.info(f"User {user_id} logged out from device {device_id}")
                return {"message": "Logged out successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Device session not found"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout service unavailable"
            )
    
    async def logout_all_devices(self, user_id: str, access_token: Optional[str] = None) -> Dict[str, str]:
        """
        Logout from all devices
        
        Args:
            user_id: User identifier
            
        Returns:
            Success message
        """
        try:
            success = await self.auth_manager.revoke_all_user_sessions(user_id)
            if access_token:
                try:
                    claims = await self.auth_manager.verify_access_token(access_token)
                    if claims and claims.get("jti") and claims.get("exp"):
                        await self.auth_manager.revoke_jti(claims["jti"], claims["exp"])
                except Exception:
                    pass
            
            if success:
                logger.info(f"User {user_id} logged out from all devices")
                return {"message": "Logged out from all devices successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to logout from all devices"
                )
                
        except Exception as e:
            logger.error(f"Logout all failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout service unavailable"
            )
    
    async def get_user_devices(self, user_id: str) -> UserDevicesResponse:
        """
        Get all user devices
        
        Args:
            user_id: User identifier
            
        Returns:
            List of user devices
        """
        try:
            devices = await self.auth_manager.get_user_devices(user_id)
            
            device_info_list = [
                DeviceInfo(
                    device_id=device.device_id,
                    device_type=device.device_type,
                    device_name=device.device_name,
                    last_used=device.last_used,
                    created_at=device.created_at,
                    ip_address=device.ip_address
                )
                for device in devices
            ]
            
            return UserDevicesResponse(
                devices=device_info_list,
                total_count=len(device_info_list)
            )
            
        except Exception as e:
            logger.error(f"Failed to get user devices: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Device service unavailable"
            )
    
    async def revoke_device(self, user_id: str, device_id: str) -> Dict[str, str]:
        """
        Revoke specific device access
        
        Args:
            user_id: User identifier
            device_id: Device identifier to revoke
            
        Returns:
            Success message
        """
        try:
            success = await self.auth_manager.revoke_device_session(user_id, device_id)
            
            if success:
                logger.info(f"Device {device_id} revoked for user {user_id}")
                return {"message": f"Device {device_id} access revoked successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Device not found"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Device revocation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Device revocation service unavailable"
            )
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
        """
        Verify JWT access token (dependency for protected endpoints)
        
        Args:
            credentials: HTTP Bearer token
            
        Returns:
            Token claims
        """
        try:
            claims = await self.auth_manager.verify_access_token(credentials.credentials)
            
            if not claims:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            return claims
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    async def get_auth_status(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthStatus:
        """
        Get current authentication status
        
        Args:
            credentials: HTTP Bearer token
            
        Returns:
            Authentication status
        """
        try:
            claims = await self.verify_token(credentials)
            
            return AuthStatus(
                authenticated=True,
                user_id=claims.get("sub"),
                device_id=claims.get("device_id"),
                device_type=claims.get("device_type"),
                expires_at=datetime.fromtimestamp(claims.get("exp", 0))
            )
            
        except HTTPException:
            return AuthStatus(authenticated=False)

# Middleware for automatic token verification
class BuddyAuthMiddleware:
    """
    Authentication middleware for BUDDY
    """
    
    def __init__(self, auth_api: BuddyAuthAPI):
        self.auth_api = auth_api
    
    async def __call__(self, request: Request, call_next):
        """
        Process request with authentication
        
        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint
            
        Returns:
            Response
        """
        # Skip authentication for certain paths
        skip_paths = ["/auth/login", "/auth/refresh", "/health", "/docs", "/openapi.json"]
        
        if request.url.path in skip_paths:
            return await call_next(request)
        
        # Check for authorization header
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            claims = await self.auth_api.auth_manager.verify_access_token(token)
            
            if claims:
                # Add user info to request state
                request.state.user_id = claims.get("sub")
                request.state.device_id = claims.get("device_id")
                request.state.device_type = claims.get("device_type")
                request.state.authenticated = True
            else:
                request.state.authenticated = False
        else:
            request.state.authenticated = False
        
        return await call_next(request)

# Helper functions for FastAPI app integration
def create_auth_routes(app: FastAPI, auth_api: BuddyAuthAPI):
    """
    Create authentication routes for FastAPI app
    
    Args:
        app: FastAPI application
        auth_api: BuddyAuthAPI instance
    """
    
    @app.post("/auth/login", response_model=TokenResponse)
    async def login(request: Request, login_data: LoginRequest):
        """User login"""
        return await auth_api.login(request, login_data)
    
    @app.post("/auth/refresh", response_model=TokenResponse)
    async def refresh_token(request: Request, refresh_data: RefreshRequest):
        """Refresh access token"""
        return await auth_api.refresh_token(request, refresh_data)
    
    @app.post("/auth/logout")
    async def logout(device_id: str, request: Request, claims: Dict = Depends(auth_api.verify_token)):
        """Logout from current device"""
        auth_header = request.headers.get("Authorization")
        token = auth_header.split(" ")[1] if auth_header and auth_header.startswith("Bearer ") else None
        return await auth_api.logout(claims["sub"], device_id, access_token=token)
    
    @app.post("/auth/logout-all")
    async def logout_all(request: Request, claims: Dict = Depends(auth_api.verify_token)):
        """Logout from all devices"""
        auth_header = request.headers.get("Authorization")
        token = auth_header.split(" ")[1] if auth_header and auth_header.startswith("Bearer ") else None
        return await auth_api.logout_all_devices(claims["sub"], access_token=token)
    
    @app.get("/auth/devices", response_model=UserDevicesResponse)
    async def get_devices(claims: Dict = Depends(auth_api.verify_token)):
        """Get user devices"""
        return await auth_api.get_user_devices(claims["sub"])
    
    @app.delete("/auth/devices/{device_id}")
    async def revoke_device(device_id: str, claims: Dict = Depends(auth_api.verify_token)):
        """Revoke device access"""
        return await auth_api.revoke_device(claims["sub"], device_id)
    
    @app.get("/auth/status", response_model=AuthStatus)
    async def auth_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Get authentication status"""
        return await auth_api.get_auth_status(credentials)
    
    @app.get("/auth/me")
    async def get_current_user(claims: Dict = Depends(auth_api.verify_token)):
        """Get current user info"""
        return {
            "user_id": claims["sub"],
            "device_id": claims["device_id"],
            "device_type": claims["device_type"],
            "issued_at": datetime.fromtimestamp(claims["iat"]),
            "expires_at": datetime.fromtimestamp(claims["exp"])
        }
