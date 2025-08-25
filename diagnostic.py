"""
BUDDY Diagnostic Script
Check all components and connections
"""

import requests
import json
import time
from datetime import datetime

def print_separator():
    print("=" * 60)

def check_backend():
    print("🔧 BACKEND SERVER TEST")
    print_separator()
    
    try:
        # Health check
        response = requests.get("http://localhost:8082/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print("✅ Backend is running!")
            print(f"   Status: {health_data.get('status', 'unknown')}")
            print(f"   Uptime: {health_data.get('uptime_seconds', 0):.1f} seconds")
            print(f"   MongoDB: {health_data.get('mongodb_enabled', False)}")
            db_status = health_data.get('database', {}).get('status', 'unknown')
            print(f"   Database: {db_status}")
            return True
        else:
            print(f"❌ Backend responded with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server")
        print("   Please ensure backend is running on port 8082")
        return False
    except Exception as e:
        print(f"❌ Backend check failed: {e}")
        return False

def check_skills():
    print("\n🛠️  SKILLS TEST")
    print_separator()
    
    try:
        response = requests.get("http://localhost:8082/skills", timeout=5)
        if response.status_code == 200:
            skills_data = response.json()
            skills = skills_data.get('skills', [])
            print(f"✅ Skills endpoint working! {len(skills)} skills available:")
            
            for skill in skills:
                status = "🟢" if skill.get('enabled', False) else "🔴"
                print(f"   {status} {skill.get('name', 'Unknown')} - {skill.get('description', 'No description')}")
            return True
        else:
            print(f"❌ Skills check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Skills check failed: {e}")
        return False

def check_chat():
    print("\n💬 CHAT TEST")
    print_separator()
    
    test_messages = [
        "Hello BUDDY!",
        "How are you?", 
        "What time is it?",
        "Calculate 25 * 4"
    ]
    
    for message in test_messages:
        try:
            print(f"Testing: '{message}'")
            
            response = requests.post("http://localhost:8082/chat", 
                json={
                    "message": message,
                    "user_id": "diagnostic_user",
                    "session_id": "diagnostic_session"
                }, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                buddy_response = data.get('response', 'No response')
                print(f"✅ BUDDY: {buddy_response[:100]}{'...' if len(buddy_response) > 100 else ''}")
            else:
                print(f"❌ Chat failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Chat test failed: {e}")
            return False
        
        time.sleep(0.5)  # Small delay between tests
    
    return True

def check_web_server():
    print("\n🌐 WEB SERVER TEST")
    print_separator()
    
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Web server is running!")
            print("   Interface accessible at http://localhost:3000")
            
            # Check if HTML contains the fixed API URL
            if "localhost:8082" in response.text:
                print("✅ Web interface configured for correct API endpoint")
            else:
                print("⚠️  Web interface may have wrong API endpoint")
            
            return True
        else:
            print(f"❌ Web server responded with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to web server")
        print("   Please ensure web server is running on port 3000")
        return False
    except Exception as e:
        print(f"❌ Web server check failed: {e}")
        return False

def main():
    print("🤖 BUDDY 2.0 DIAGNOSTIC REPORT")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator()
    
    results = {
        'backend': check_backend(),
        'skills': check_skills(),
        'chat': check_chat(),
        'web_server': check_web_server()
    }
    
    print("\n📊 SUMMARY")
    print_separator()
    
    all_good = True
    for component, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {component.replace('_', ' ').title()}: {'PASS' if status else 'FAIL'}")
        if not status:
            all_good = False
    
    print_separator()
    
    if all_good:
        print("🎉 ALL SYSTEMS OPERATIONAL!")
        print("   BUDDY 2.0 is ready to use at http://localhost:3000")
    else:
        print("⚠️  SOME ISSUES DETECTED")
        print("   Please check the failed components above")
    
    print("\n🔗 Quick Links:")
    print("   🌐 Web Interface: http://localhost:3000")
    print("   📡 API Backend: http://localhost:8082")
    print("   📊 Health Check: http://localhost:8082/health")
    print("   🧪 Connection Test: http://localhost:3000/test_buddy_connection.html")

if __name__ == "__main__":
    main()
