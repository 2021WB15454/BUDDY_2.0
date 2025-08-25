#!/usr/bin/env python3
"""
Mobile Interface Demo for BUDDY Core
This simulates a mobile app connecting to BUDDY Core using the BuddyConnector SDK
"""
import asyncio
import sys
import os

# Add device_interfaces to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'device_interfaces'))

from sdk import BuddyConnector, create_mobile_connector

class MobileBuddyApp:
    def __init__(self):
        self.buddy = None
        self.running = False
        
    async def initialize(self):
        """Initialize mobile BUDDY connector"""
        print("📱 BUDDY Mobile - Initializing...")
        
        # Create mobile connector with specific configuration
        self.buddy = create_mobile_connector(
            device_id="mobile_demo_001",
            device_name="iPhone Demo",
            user_id="shrihari"
        )
        
        # Set up event handlers
        self.buddy.on_message(self.handle_message)
        self.buddy.on_voice_result(self.handle_voice)
        self.buddy.on_device_event(self.handle_device_event)
        
        # Connect to BUDDY Core
        connected = await self.buddy.connect()
        if connected:
            print("✅ Connected to BUDDY Core!")
            return True
        else:
            print("❌ Failed to connect to BUDDY Core")
            return False
    
    async def handle_message(self, message):
        """Handle incoming messages from BUDDY Core"""
        print(f"🤖 BUDDY: {message.get('content', message)}")
    
    async def handle_voice(self, result):
        """Handle voice recognition results"""
        print(f"🎤 Voice: {result}")
    
    async def handle_device_event(self, event):
        """Handle device-specific events"""
        print(f"📱 Device Event: {event}")
    
    async def send_message(self, message):
        """Send message to BUDDY Core"""
        if self.buddy:
            response = await self.buddy.send_message(message, {
                "device_type": "mobile",
                "location": "home",
                "battery_level": 85
            })
            return response
    
    async def run_demo(self):
        """Run the mobile app demo"""
        self.running = True
        
        print("\n" + "="*50)
        print("📱 BUDDY Mobile Interface Demo")
        print("="*50)
        print("Commands:")
        print("  - Type a message to send to BUDDY")
        print("  - Type 'quit' to exit")
        print("  - Type 'status' to get BUDDY status")
        print("  - Type 'voice' to simulate voice input")
        print("="*50 + "\n")
        
        while self.running:
            try:
                # Get user input
                user_input = input("📱 You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'status':
                    # Get BUDDY status
                    status = await self.buddy.get_device_status()
                    print(f"🔍 Status: {status}")
                elif user_input.lower() == 'voice':
                    # Simulate voice input
                    print("🎤 Simulating voice input: 'What time is it?'")
                    await self.send_message("What time is it?")
                else:
                    # Send regular message
                    await self.send_message(user_input)
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Disconnect
        if self.buddy:
            await self.buddy.disconnect()
            print("📱 Disconnected from BUDDY Core")

async def main():
    """Main mobile app entry point"""
    app = MobileBuddyApp()
    
    # Initialize
    if await app.initialize():
        # Run the demo
        await app.run_demo()
    else:
        print("Failed to start mobile app")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Mobile app stopped")
