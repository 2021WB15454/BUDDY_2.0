#!/usr/bin/env python3
"""
Firebase PEM Certificate Validator for BUDDY 2.0
Tests and fixes Firebase certificate issues
"""

import json
import os
from pathlib import Path

def validate_pem_format(pem_content: str) -> bool:
    """Validate PEM format"""
    if not pem_content:
        return False
    
    # Check for proper BEGIN/END markers
    if "-----BEGIN PRIVATE KEY-----" not in pem_content:
        return False
    
    if "-----END PRIVATE KEY-----" not in pem_content:
        return False
    
    # Check for proper line structure
    lines = pem_content.split('\n')
    if len(lines) < 3:  # Header, content, footer minimum
        return False
    
    return True

def fix_pem_newlines(pem_content: str) -> str:
    """Fix newline issues in PEM content"""
    # Replace literal \n with actual newlines
    if '\\n' in pem_content:
        pem_content = pem_content.replace('\\n', '\n')
    
    # Ensure proper line endings
    lines = pem_content.strip().split('\n')
    return '\n'.join(line.strip() for line in lines)

def validate_firebase_service_account():
    """Validate Firebase service account configuration"""
    service_account_path = "config/firebase-service-account.json"
    
    print("🔥 Firebase Certificate Validator")
    print("=" * 40)
    
    # Check if file exists
    if not os.path.exists(service_account_path):
        print(f"❌ Service account file not found: {service_account_path}")
        return False
    
    print(f"✅ Service account file found: {service_account_path}")
    
    try:
        # Load JSON file
        with open(service_account_path, 'r') as f:
            service_account_data = json.load(f)
        
        print("✅ JSON file loaded successfully")
        
        # Check required fields
        required_fields = [
            'type', 'project_id', 'private_key_id', 
            'private_key', 'client_email', 'client_id'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in service_account_data:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        print("✅ All required fields present")
        
        # Validate private key
        private_key = service_account_data['private_key']
        print(f"📋 Private key length: {len(private_key)} characters")
        
        # Check for escaped newlines
        if '\\n' in private_key:
            print("⚠️  Private key contains escaped newlines (\\n)")
            fixed_key = fix_pem_newlines(private_key)
            print("🔧 Fixed newlines in private key")
        else:
            fixed_key = private_key
            print("✅ Private key newlines appear correct")
        
        # Validate PEM format
        if validate_pem_format(fixed_key):
            print("✅ Private key PEM format is valid")
        else:
            print("❌ Private key PEM format is invalid")
            return False
        
        # Test cryptography library parsing
        try:
            from cryptography.hazmat.primitives import serialization
            
            # Try to load the private key
            private_key_obj = serialization.load_pem_private_key(
                fixed_key.encode('utf-8'),
                password=None
            )
            print("✅ Private key successfully parsed by cryptography library")
            
        except ImportError:
            print("⚠️  cryptography library not installed - install with: pip install cryptography")
        except Exception as e:
            print(f"❌ Private key parsing failed: {e}")
            print("\n🔧 Attempting to fix the private key...")
            
            # Try different fixes
            fixed_attempts = [
                # Remove extra whitespace
                '\n'.join(line.strip() for line in fixed_key.split('\n')),
                # Ensure proper line breaks
                fixed_key.replace('\r\n', '\n').replace('\r', '\n'),
                # Remove any BOM or special characters
                fixed_key.encode('utf-8').decode('utf-8-sig')
            ]
            
            for i, attempt in enumerate(fixed_attempts):
                try:
                    test_key = serialization.load_pem_private_key(
                        attempt.encode('utf-8'),
                        password=None
                    )
                    print(f"✅ Fix attempt {i+1} successful!")
                    
                    # Create fixed service account file
                    fixed_service_account = service_account_data.copy()
                    fixed_service_account['private_key'] = attempt
                    
                    backup_path = service_account_path + '.backup'
                    fixed_path = service_account_path + '.fixed'
                    
                    # Backup original
                    with open(backup_path, 'w') as f:
                        json.dump(service_account_data, f, indent=2)
                    
                    # Save fixed version
                    with open(fixed_path, 'w') as f:
                        json.dump(fixed_service_account, f, indent=2)
                    
                    print(f"💾 Original backed up to: {backup_path}")
                    print(f"💾 Fixed version saved to: {fixed_path}")
                    print("\n🔧 To use the fixed version:")
                    print(f"   mv {fixed_path} {service_account_path}")
                    
                    return True
                    
                except Exception as fix_error:
                    print(f"❌ Fix attempt {i+1} failed: {fix_error}")
                    continue
            
            return False
        
        # Test Firebase Admin SDK (if available)
        try:
            import firebase_admin
            from firebase_admin import credentials
            
            # Create fixed service account data
            fixed_service_account = service_account_data.copy()
            fixed_service_account['private_key'] = fixed_key
            
            # Test credential creation
            cred = credentials.Certificate(fixed_service_account)
            print("✅ Firebase Admin SDK credential creation successful")
            
        except ImportError:
            print("⚠️  Firebase Admin SDK not installed - install with: pip install firebase-admin")
        except Exception as e:
            print(f"❌ Firebase credential creation failed: {e}")
            return False
        
        print("\n🎉 Firebase service account validation successful!")
        print("\nNext steps:")
        print("1. Install missing dependencies if any:")
        print("   pip install firebase-admin cryptography")
        print("2. Run your Firebase-enabled application")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing required dependencies...")
    try:
        import subprocess
        import sys
        
        packages = ['firebase-admin', 'cryptography']
        for package in packages:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        
        print("✅ All dependencies installed successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

if __name__ == "__main__":
    print("🔥 Firebase Configuration Validator")
    print("=" * 50)
    
    # Option to install dependencies
    install_deps = input("Install required dependencies (firebase-admin, cryptography)? [y/N]: ")
    if install_deps.lower() in ['y', 'yes']:
        if install_dependencies():
            print("\n" + "="*50)
        else:
            print("⚠️  Dependency installation failed. Continuing with validation...")
    
    # Run validation
    success = validate_firebase_service_account()
    
    if success:
        print("\n🎉 All checks passed! Your Firebase configuration should work.")
    else:
        print("\n❌ Firebase configuration has issues. Please fix them before proceeding.")
        
    input("\nPress Enter to exit...")
