# BUDDY 2.0 - Encryption Key Management Utility
# Utility for generating and managing encryption keys

import os
import secrets
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class BuddyEncryptionManager:
    """
    BUDDY Encryption Key Management
    Handles AES-256-GCM encryption keys for data protection
    """
    
    def __init__(self, key_path: str = "./keys/encryption.key"):
        """
        Initialize encryption manager
        
        Args:
            key_path: Path to the encryption key file
        """
        self.key_path = Path(key_path)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
    
    def generate_key(self) -> str:
        """
        Generate a new AES-256-GCM encryption key
        
        Returns:
            Base64 encoded encryption key
        """
        # Generate 256-bit (32-byte) key for AES-256-GCM
        key = secrets.token_bytes(32)
        key_b64 = base64.b64encode(key).decode('utf-8')
        
        # Save to file
        with open(self.key_path, 'w') as f:
            f.write(key_b64)
        
        # Set restrictive permissions (read-only for owner)
        if os.name != 'nt':  # Unix/Linux
            os.chmod(self.key_path, 0o600)
        
        return key_b64
    
    def load_key(self) -> str:
        """
        Load encryption key from file
        
        Returns:
            Base64 encoded encryption key
        """
        if not self.key_path.exists():
            raise FileNotFoundError(f"Encryption key not found: {self.key_path}")
        
        with open(self.key_path, 'r') as f:
            return f.read().strip()
    
    def get_raw_key(self) -> bytes:
        """
        Get raw encryption key bytes
        
        Returns:
            Raw encryption key bytes
        """
        key_b64 = self.load_key()
        return base64.b64decode(key_b64)
    
    def rotate_key(self, backup_old: bool = True) -> str:
        """
        Rotate encryption key (generate new one)
        
        Args:
            backup_old: Whether to backup the old key
            
        Returns:
            New base64 encoded encryption key
        """
        if backup_old and self.key_path.exists():
            backup_path = self.key_path.with_suffix('.key.backup')
            import shutil
            shutil.copy2(self.key_path, backup_path)
            print(f"Old key backed up to: {backup_path}")
        
        new_key = self.generate_key()
        print(f"New encryption key generated: {self.key_path}")
        return new_key
    
    def validate_key(self) -> bool:
        """
        Validate that the encryption key is properly formatted
        
        Returns:
            True if key is valid
        """
        try:
            key = self.get_raw_key()
            return len(key) == 32  # 256 bits
        except Exception:
            return False
    
    def get_key_info(self) -> dict:
        """
        Get information about the current encryption key
        
        Returns:
            Dictionary with key information
        """
        try:
            key = self.get_raw_key()
            key_b64 = self.load_key()
            
            return {
                "key_path": str(self.key_path),
                "key_exists": True,
                "key_length_bytes": len(key),
                "key_length_bits": len(key) * 8,
                "algorithm": "AES-256-GCM",
                "key_preview": key_b64[:16] + "...",
                "file_size": self.key_path.stat().st_size,
                "is_valid": len(key) == 32
            }
        except Exception as e:
            return {
                "key_path": str(self.key_path),
                "key_exists": False,
                "error": str(e)
            }

def create_fernet_key() -> str:
    """
    Create a Fernet-compatible encryption key
    
    Returns:
        URL-safe base64 encoded Fernet key
    """
    return Fernet.generate_key().decode('utf-8')

def derive_key_from_password(password: str, salt: bytes = None) -> tuple:
    """
    Derive encryption key from password using PBKDF2
    
    Args:
        password: Master password
        salt: Salt bytes (generated if None)
        
    Returns:
        Tuple of (derived_key, salt)
    """
    if salt is None:
        salt = secrets.token_bytes(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = kdf.derive(password.encode('utf-8'))
    return key, salt

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BUDDY Encryption Key Management")
    parser.add_argument("--generate", action="store_true", help="Generate new encryption key")
    parser.add_argument("--rotate", action="store_true", help="Rotate encryption key")
    parser.add_argument("--info", action="store_true", help="Show key information")
    parser.add_argument("--validate", action="store_true", help="Validate encryption key")
    parser.add_argument("--key-path", default="./keys/encryption.key", help="Path to encryption key file")
    
    args = parser.parse_args()
    
    manager = BuddyEncryptionManager(args.key_path)
    
    if args.generate:
        key = manager.generate_key()
        print(f"✅ New encryption key generated: {args.key_path}")
        print(f"🔑 Key preview: {key[:32]}...")
    
    elif args.rotate:
        key = manager.rotate_key()
        print(f"🔄 Encryption key rotated successfully")
    
    elif args.info:
        info = manager.get_key_info()
        print("🔐 BUDDY Encryption Key Information:")
        for key, value in info.items():
            print(f"   {key}: {value}")
    
    elif args.validate:
        is_valid = manager.validate_key()
        if is_valid:
            print("✅ Encryption key is valid")
        else:
            print("❌ Encryption key is invalid or missing")
    
    else:
        print("🔐 BUDDY Encryption Key Manager")
        print("Available commands:")
        print("  --generate    Generate new encryption key")
        print("  --rotate      Rotate encryption key")
        print("  --info        Show key information")
        print("  --validate    Validate encryption key")
        print("  --key-path    Specify key file path")
