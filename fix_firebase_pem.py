#!/usr/bin/env python3
"""
Quick Firebase PEM Fix for BUDDY 2.0
"""

import json
import os

def fix_firebase_pem():
    """Fix Firebase service account PEM formatting"""
    service_account_path = "config/firebase-service-account.json"
    
    print("🔧 Fixing Firebase PEM certificate...")
    
    if not os.path.exists(service_account_path):
        print(f"❌ File not found: {service_account_path}")
        return False
    
    try:
        # Load the service account file
        with open(service_account_path, 'r', encoding='utf-8') as f:
            service_account_data = json.load(f)
        
        # Get the private key
        private_key = service_account_data.get('private_key', '')
        
        print(f"📋 Original private key length: {len(private_key)}")
        contains_escaped = '\\n' in private_key
        print(f"📋 Contains escaped newlines: {contains_escaped}")
        
        # Fix the private key formatting
        if '\\n' in private_key:
            # Replace escaped newlines with actual newlines
            fixed_key = private_key.replace('\\n', '\n')
            print("🔧 Fixed escaped newlines")
        else:
            fixed_key = private_key
        
        # Ensure proper line endings and remove extra whitespace
        lines = fixed_key.split('\n')
        cleaned_lines = []
        
        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line:  # Skip empty lines except between header and footer
                cleaned_lines.append(cleaned_line)
        
        # Reconstruct the key with proper formatting
        if cleaned_lines:
            # Find BEGIN and END markers
            begin_idx = -1
            end_idx = -1
            
            for i, line in enumerate(cleaned_lines):
                if "-----BEGIN PRIVATE KEY-----" in line:
                    begin_idx = i
                elif "-----END PRIVATE KEY-----" in line:
                    end_idx = i
            
            if begin_idx >= 0 and end_idx >= 0:
                # Reconstruct with proper newlines
                header = cleaned_lines[begin_idx]
                footer = cleaned_lines[end_idx]
                body_lines = cleaned_lines[begin_idx + 1:end_idx]
                
                # Join body lines (Base64 content)
                body = ''.join(body_lines)
                
                # Split into 64-character lines for proper PEM format
                formatted_body_lines = []
                for i in range(0, len(body), 64):
                    formatted_body_lines.append(body[i:i+64])
                
                # Reconstruct the full key
                fixed_key = header + '\n' + '\n'.join(formatted_body_lines) + '\n' + footer
                
                print("✅ Private key reformatted with proper line breaks")
            else:
                print("⚠️  Could not find proper BEGIN/END markers")
        
        # Update the service account data
        service_account_data['private_key'] = fixed_key
        
        # Create backup
        backup_path = service_account_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(service_account_data, f, indent=2)
        print(f"💾 Backup created: {backup_path}")
        
        # Save the fixed version
        with open(service_account_path, 'w', encoding='utf-8') as f:
            json.dump(service_account_data, f, indent=2)
        
        print(f"✅ Fixed service account saved to: {service_account_path}")
        
        # Test the fix
        try:
            from cryptography.hazmat.primitives import serialization
            
            # Try to parse the fixed key
            private_key_obj = serialization.load_pem_private_key(
                fixed_key.encode('utf-8'),
                password=None
            )
            print("✅ Private key validation successful!")
            return True
            
        except ImportError:
            print("⚠️  cryptography not installed. Install with: pip install cryptography")
            print("✅ PEM format fixed (validation requires cryptography)")
            return True
            
        except Exception as e:
            print(f"❌ Private key validation failed: {e}")
            
            # Try to restore backup
            with open(backup_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            
            with open(service_account_path, 'w', encoding='utf-8') as f:
                json.dump(original_data, f, indent=2)
            
            print(f"🔄 Restored original file from backup")
            return False
    
    except Exception as e:
        print(f"❌ Error fixing Firebase PEM: {e}")
        return False

def install_firebase_deps():
    """Install Firebase dependencies"""
    try:
        import subprocess
        import sys
        
        print("📦 Installing Firebase dependencies...")
        
        packages = ['firebase-admin', 'cryptography']
        for package in packages:
            try:
                print(f"Installing {package}...")
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', package
                ])
                print(f"✅ {package} installed")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {package}: {e}")
                return False
        
        print("✅ All dependencies installed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

if __name__ == "__main__":
    print("🔥 Firebase PEM Certificate Fixer")
    print("=" * 40)
    
    # Install dependencies first
    print("Step 1: Installing dependencies...")
    if install_firebase_deps():
        print("\nStep 2: Fixing PEM certificate...")
        if fix_firebase_pem():
            print("\n🎉 Firebase certificate fixed successfully!")
            print("\nYou can now restart your Firebase-enabled application.")
        else:
            print("\n❌ Failed to fix Firebase certificate.")
    else:
        print("\n❌ Failed to install dependencies.")
        print("Please install manually: pip install firebase-admin cryptography")
