#!/usr/bin/env python3
"""
MongoDB Connection String Fixer

Fix URL encoding issues in MongoDB connection strings.
"""

from urllib.parse import quote_plus

def fix_connection_string():
    """Fix the MongoDB connection string with proper URL encoding."""
    
    print("🔧 Fixing MongoDB Atlas Connection String")
    print("=" * 45)
    
    # Original credentials
    username = "BUDDY_AI"
    password = "Preetty@20"  # Contains @ symbol that needs encoding
    cluster = "cluster0.fbbl9jd.mongodb.net"
    
    # URL encode the password
    encoded_password = quote_plus(password)
    
    print(f"Original password: {password}")
    print(f"Encoded password:  {encoded_password}")
    
    # Create proper connection string
    fixed_connection_string = f"mongodb+srv://{username}:{encoded_password}@{cluster}/"
    
    print(f"\n✅ Fixed Connection String:")
    print(f"{fixed_connection_string}")
    
    return fixed_connection_string

if __name__ == "__main__":
    fixed_uri = fix_connection_string()
    
    print(f"\n📝 Update your configuration with:")
    print(f"connection_string: \"{fixed_uri}\"")
