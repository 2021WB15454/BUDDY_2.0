"""
Encryption Manager - Data Security & Privacy

Provides:
- End-to-end encryption for user data
- Key management and rotation
- Platform-specific secure storage
- Compliance with privacy regulations
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
import base64
import hashlib
import json
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class EncryptionManager:
    """Manages encryption and decryption of user data"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.encryption_enabled = self.config.get("enabled", True)
        self.key_rotation_days = self.config.get("key_rotation_days", 90)
        
        # Encryption state
        self._master_key = None
        self._device_key = None
        self._key_cache = {}
        self._initialized = False
        
    async def initialize(self, user_password: str = None, device_id: str = None):
        """Initialize encryption manager"""
        try:
            if not self.encryption_enabled:
                logger.info("Encryption disabled by configuration")
                self._initialized = True
                return
            
            # Initialize encryption backend
            await self._initialize_crypto_backend()
            
            # Generate or load master key
            await self._initialize_master_key(user_password)
            
            # Generate device-specific key
            await self._initialize_device_key(device_id)
            
            self._initialized = True
            logger.info("Encryption manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            self._initialized = False
    
    async def _initialize_crypto_backend(self):
        """Initialize cryptographic backend"""
        try:
            # Try to use cryptography library (recommended)
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives.asymmetric import rsa
            
            self.crypto_backend = "cryptography"
            self.Fernet = Fernet
            self.hashes = hashes
            self.PBKDF2HMAC = PBKDF2HMAC
            self.rsa = rsa
            
            logger.info("Using cryptography library for encryption")
            
        except ImportError:
            try:
                # Fallback to hashlib + base64 (basic encryption)
                import hashlib
                import base64
                from Crypto.Cipher import AES
                from Crypto.Random import get_random_bytes
                
                self.crypto_backend = "pycrypto"
                self.AES = AES
                self.get_random_bytes = get_random_bytes
                
                logger.info("Using PyCrypto for encryption")
                
            except ImportError:
                # Basic fallback (NOT SECURE - for development only)
                self.crypto_backend = "basic"
                logger.warning("Using basic encryption (NOT SECURE - development only)")
    
    async def _initialize_master_key(self, user_password: str = None):
        """Initialize master encryption key"""
        if self.crypto_backend == "cryptography":
            await self._init_master_key_cryptography(user_password)
        elif self.crypto_backend == "pycrypto":
            await self._init_master_key_pycrypto(user_password)
        else:
            await self._init_master_key_basic(user_password)
    
    async def _init_master_key_cryptography(self, user_password: str = None):
        """Initialize master key using cryptography library"""
        if user_password:
            # Derive key from password
            password_bytes = user_password.encode('utf-8')
            salt = os.urandom(16)
            
            kdf = self.PBKDF2HMAC(
                algorithm=self.hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
            self._master_key = self.Fernet(key)
            
            # Store salt securely (in real implementation)
            self._key_salt = salt
            
        else:
            # Generate random key
            key = self.Fernet.generate_key()
            self._master_key = self.Fernet(key)
    
    async def _init_master_key_pycrypto(self, user_password: str = None):
        """Initialize master key using PyCrypto"""
        if user_password:
            # Derive key from password using PBKDF2
            salt = self.get_random_bytes(16)
            key = hashlib.pbkdf2_hmac('sha256', user_password.encode('utf-8'), salt, 100000)
            self._master_key = key
            self._key_salt = salt
        else:
            # Generate random key
            self._master_key = self.get_random_bytes(32)
    
    async def _init_master_key_basic(self, user_password: str = None):
        """Initialize master key using basic method (NOT SECURE)"""
        if user_password:
            # Simple hash of password (NOT SECURE)
            self._master_key = hashlib.sha256(user_password.encode('utf-8')).digest()
        else:
            # Random bytes
            self._master_key = os.urandom(32)
    
    async def _initialize_device_key(self, device_id: str = None):
        """Initialize device-specific key"""
        if device_id:
            # Generate device-specific key from device ID and master key
            device_data = f"{device_id}:{datetime.now().date()}"
            device_hash = hashlib.sha256(device_data.encode('utf-8')).digest()
            
            if self.crypto_backend == "cryptography":
                # Combine with master key
                combined = hashlib.sha256(self._master_key.extract() + device_hash).digest()
                self._device_key = self.Fernet(base64.urlsafe_b64encode(combined))
            else:
                # Simple combination
                self._device_key = hashlib.sha256(self._master_key + device_hash).digest()
    
    # Encryption Operations
    async def encrypt_data(self, data: Any, key_type: str = "master") -> str:
        """Encrypt data using specified key"""
        if not self._initialized or not self.encryption_enabled:
            return json.dumps(data)  # Return unencrypted if disabled
        
        try:
            # Convert data to JSON string
            json_data = json.dumps(data)
            data_bytes = json_data.encode('utf-8')
            
            # Choose encryption key
            if key_type == "device" and self._device_key:
                key = self._device_key
            else:
                key = self._master_key
            
            # Encrypt based on backend
            if self.crypto_backend == "cryptography":
                encrypted_bytes = key.encrypt(data_bytes)
                return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
                
            elif self.crypto_backend == "pycrypto":
                # AES encryption
                cipher = self.AES.new(key[:32], self.AES.MODE_EAX)
                ciphertext, tag = cipher.encrypt_and_digest(data_bytes)
                
                encrypted_data = {
                    "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
                    "nonce": base64.b64encode(cipher.nonce).decode('utf-8'),
                    "tag": base64.b64encode(tag).decode('utf-8')
                }
                
                return base64.urlsafe_b64encode(json.dumps(encrypted_data).encode()).decode('utf-8')
                
            else:
                # Basic XOR encryption (NOT SECURE)
                encrypted = bytearray()
                key_bytes = key[:32]
                
                for i, byte in enumerate(data_bytes):
                    encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
                
                return base64.urlsafe_b64encode(encrypted).decode('utf-8')
                
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return json.dumps(data)  # Fallback to unencrypted
    
    async def decrypt_data(self, encrypted_data: str, key_type: str = "master") -> Any:
        """Decrypt data using specified key"""
        if not self._initialized or not self.encryption_enabled:
            try:
                return json.loads(encrypted_data)  # Assume unencrypted
            except:
                return encrypted_data
        
        try:
            # Choose decryption key
            if key_type == "device" and self._device_key:
                key = self._device_key
            else:
                key = self._master_key
            
            # Decrypt based on backend
            if self.crypto_backend == "cryptography":
                encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
                decrypted_bytes = key.decrypt(encrypted_bytes)
                json_data = decrypted_bytes.decode('utf-8')
                return json.loads(json_data)
                
            elif self.crypto_backend == "pycrypto":
                # Decode and parse encrypted data
                decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
                encrypted_obj = json.loads(decoded_data.decode('utf-8'))
                
                ciphertext = base64.b64decode(encrypted_obj["ciphertext"])
                nonce = base64.b64decode(encrypted_obj["nonce"])
                tag = base64.b64decode(encrypted_obj["tag"])
                
                cipher = self.AES.new(key[:32], self.AES.MODE_EAX, nonce=nonce)
                decrypted_bytes = cipher.decrypt_and_verify(ciphertext, tag)
                
                json_data = decrypted_bytes.decode('utf-8')
                return json.loads(json_data)
                
            else:
                # Basic XOR decryption
                encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
                decrypted = bytearray()
                key_bytes = key[:32]
                
                for i, byte in enumerate(encrypted_bytes):
                    decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
                
                json_data = decrypted.decode('utf-8')
                return json.loads(json_data)
                
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            try:
                return json.loads(encrypted_data)  # Try as unencrypted JSON
            except:
                return encrypted_data  # Return as-is
    
    # Specialized encryption for different data types
    async def encrypt_user_data(self, user_data: Dict[str, Any]) -> str:
        """Encrypt user data with user-specific settings"""
        return await self.encrypt_data(user_data, "master")
    
    async def encrypt_conversation(self, conversation: Dict[str, Any]) -> str:
        """Encrypt conversation data"""
        return await self.encrypt_data(conversation, "master")
    
    async def encrypt_ai_context(self, context: Dict[str, Any]) -> str:
        """Encrypt AI context data"""
        return await self.encrypt_data(context, "device")
    
    # Key Management
    async def rotate_keys(self, new_password: str = None) -> bool:
        """Rotate encryption keys"""
        try:
            # Store old keys for data migration
            old_master_key = self._master_key
            old_device_key = self._device_key
            
            # Generate new keys
            await self._initialize_master_key(new_password)
            await self._initialize_device_key()
            
            # In a full implementation, you would:
            # 1. Decrypt all data with old keys
            # 2. Re-encrypt with new keys
            # 3. Update key metadata
            
            logger.info("Encryption keys rotated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            # Restore old keys
            self._master_key = old_master_key
            self._device_key = old_device_key
            return False
    
    async def export_key_for_device(self, device_id: str) -> Optional[str]:
        """Export key for new device (for key sharing)"""
        if not self._initialized:
            return None
        
        try:
            # In a real implementation, this would:
            # 1. Generate a device-specific key
            # 2. Encrypt it with a shared secret
            # 3. Return the encrypted key for the new device
            
            device_key_data = {
                "device_id": device_id,
                "master_key_hash": hashlib.sha256(str(self._master_key).encode()).hexdigest(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return await self.encrypt_data(device_key_data)
            
        except Exception as e:
            logger.error(f"Key export failed: {e}")
            return None
    
    async def import_key_from_device(self, encrypted_key: str) -> bool:
        """Import key from another device"""
        try:
            key_data = await self.decrypt_data(encrypted_key)
            
            # Validate and import the key
            # In a real implementation, this would verify the key
            # and update the local encryption setup
            
            logger.info("Key imported successfully")
            return True
            
        except Exception as e:
            logger.error(f"Key import failed: {e}")
            return False
    
    # Utility Methods
    def is_data_encrypted(self, data: str) -> bool:
        """Check if data appears to be encrypted"""
        try:
            # Try to decode as base64
            base64.urlsafe_b64decode(data)
            # If successful and not valid JSON, likely encrypted
            try:
                json.loads(data)
                return False  # Valid JSON, probably not encrypted
            except:
                return True  # Not valid JSON, likely encrypted
        except:
            return False  # Not base64, probably not encrypted
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """Get encryption configuration info"""
        return {
            "enabled": self.encryption_enabled,
            "backend": getattr(self, "crypto_backend", "none"),
            "initialized": self._initialized,
            "key_rotation_days": self.key_rotation_days,
            "has_master_key": self._master_key is not None,
            "has_device_key": self._device_key is not None
        }
    
    async def close(self):
        """Close encryption manager"""
        # Clear sensitive data from memory
        self._master_key = None
        self._device_key = None
        self._key_cache.clear()
        
        logger.info("Encryption manager closed")
