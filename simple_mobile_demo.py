#!/usr/bin/env python3
"""
Simple Mobile Interface Demo for BUDDY Core
"""
import asyncio
import json
import aiohttp
import websockets

class SimpleMobileBuddy:
    def __init__(self):
        self.base_url = "http://localhost:8082"
        self.ws_url = "ws://localhost:8082/ws"
        self.device_id = "mobile_demo_001"
        self.user_id = "shrihari"
        
    async def send_message(self, message):
        """Send message via REST API"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "message": message,
                    "context": {
                        "device_type": "mobile",
                        "device_id": self.device_id,
                        "user_id": self.user_id,
                        "location": "home",
                        "battery_level": 85
                    }
                }
                
                async with session.post(f"{self.base_url}/chat", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        return {"error": f"HTTP {response.status}"}
                        
        except Exception as e:
            return {"error": str(e)}
    
    async def get_status(self):
        """Get BUDDY status"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def run_demo(self):
        """Run the mobile app demo"""
        print("\n" + "="*50)
        print("📱 BUDDY Mobile Interface Demo")
        print("="*50)
        print("Commands:")
        print("  - Type a message to send to BUDDY")
        print("  - Type 'quit' to exit")
        print("  - Type 'status' to get BUDDY status")
        print("="*50 + "\n")
        
        # Test connection first
        print("🔗 Testing connection to BUDDY Core...")
        status = await self.get_status()
        if "error" in status:
            print(f"❌ Cannot connect to BUDDY Core: {status['error']}")
            return
        else:
            print(f"✅ Connected! BUDDY is {status.get('status', 'unknown')}")
            print(f"📊 Active sessions: {status.get('active_sessions', 0)}")
        
        while True:
            try:
                user_input = input("\n📱 You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'status':
                    status = await self.get_status()
                    print(f"🔍 Status: {json.dumps(status, indent=2)}")
                else:
                    print("⏳ Sending message...")
                    response = await self.send_message(user_input)
                    
                    if "error" in response:
                        print(f"❌ Error: {response['error']}")
                    else:
                        print(f"🤖 BUDDY: {response.get('response', 'No response')}")
                        
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

async def main():
    buddy = SimpleMobileBuddy()
    await buddy.run_demo()

if __name__ == "__main__":
    asyncio.run(main())
