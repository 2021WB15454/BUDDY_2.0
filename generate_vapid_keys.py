"""
BUDDY Firebase VAPID Key Generator
Generate VAPID keys for web push notifications
"""

import os
import base64
import json
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend

def generate_vapid_keys():
    """Generate VAPID key pair for web push notifications"""
    
    print("🔑 Generating VAPID Keys for Web Push...")
    
    # Generate ECDSA key pair (P-256 curve)
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Serialize public key in uncompressed format
    public_numbers = public_key.public_numbers()
    x = public_numbers.x.to_bytes(32, 'big')
    y = public_numbers.y.to_bytes(32, 'big')
    uncompressed_public_key = b'\x04' + x + y
    
    # Base64 URL-safe encode the public key
    public_key_b64 = base64.urlsafe_b64encode(uncompressed_public_key).decode('utf-8').rstrip('=')
    
    return {
        'private_key': private_pem.decode('utf-8'),
        'public_key': public_key_b64,
        'public_key_bytes': uncompressed_public_key.hex()
    }

def save_vapid_keys(keys):
    """Save VAPID keys to configuration files"""
    
    # Save to config directory
    config_dir = "./config"
    os.makedirs(config_dir, exist_ok=True)
    
    # VAPID keys file
    vapid_file = os.path.join(config_dir, "vapid-keys.json")
    with open(vapid_file, 'w') as f:
        json.dump(keys, f, indent=2)
    
    print(f"✅ VAPID keys saved to: {vapid_file}")
    
    # Environment variable format
    env_file = os.path.join(config_dir, "vapid-env.txt")
    with open(env_file, 'w') as f:
        f.write("# Add these to your .env file:\n")
        f.write(f"FIREBASE_VAPID_PUBLIC_KEY={keys['public_key']}\n")
        f.write(f"FIREBASE_VAPID_PRIVATE_KEY_PATH=./config/vapid-private-key.pem\n")
    
    # Save private key as PEM file
    pem_file = os.path.join(config_dir, "vapid-private-key.pem")
    with open(pem_file, 'w') as f:
        f.write(keys['private_key'])
    
    print(f"✅ Environment config saved to: {env_file}")
    print(f"✅ Private key saved to: {pem_file}")

def update_firebase_config(public_key):
    """Update Firebase configuration with VAPID key"""
    
    firebase_file = "./apps/desktop/src/firebase.js"
    
    if os.path.exists(firebase_file):
        with open(firebase_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the VAPID key placeholder
        updated_content = content.replace(
            "this.vapidKey = process.env.REACT_APP_FIREBASE_VAPID_KEY || 'your-vapid-key';",
            f"this.vapidKey = process.env.REACT_APP_FIREBASE_VAPID_KEY || '{public_key}';"
        )
        
        with open(firebase_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"✅ Firebase config updated: {firebase_file}")
    
    # Update service worker
    sw_file = "./apps/desktop/public/firebase-messaging-sw.js"
    
    if os.path.exists(sw_file):
        with open(sw_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the VAPID key placeholder
        updated_content = content.replace(
            "applicationServerKey: urlBase64ToUint8Array('your-vapid-key')",
            f"applicationServerKey: urlBase64ToUint8Array('{public_key}')"
        )
        
        with open(sw_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"✅ Service worker updated: {sw_file}")

def main():
    print("🔐 BUDDY Firebase VAPID Key Setup")
    print("=" * 50)
    
    try:
        # Generate VAPID keys
        keys = generate_vapid_keys()
        
        print(f"\n📊 Generated VAPID Keys:")
        print(f"  Public Key: {keys['public_key'][:50]}...")
        print(f"  Public Key Length: {len(keys['public_key'])} characters")
        print(f"  Private Key Length: {len(keys['private_key'])} characters")
        
        # Save keys
        save_vapid_keys(keys)
        
        # Update Firebase configuration
        update_firebase_config(keys['public_key'])
        
        print(f"\n🔧 Next Steps:")
        print(f"1. Add to your .env file:")
        print(f"   REACT_APP_FIREBASE_VAPID_KEY={keys['public_key']}")
        print(f"")
        print(f"2. In Firebase Console:")
        print(f"   - Go to Project Settings → Cloud Messaging")
        print(f"   - Add your VAPID public key")
        print(f"   - Enable Web Push Notifications")
        print(f"")
        print(f"3. Test your web app:")
        print(f"   cd apps/desktop")
        print(f"   npm start")
        print(f"   Navigate to Settings → Enable Notifications")
        
        print(f"\n✅ VAPID key setup complete!")
        return True
        
    except Exception as e:
        print(f"❌ VAPID key generation failed: {e}")
        return False

if __name__ == "__main__":
    main()
