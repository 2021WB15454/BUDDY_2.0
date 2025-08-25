#!/usr/bin/env python3
"""
BUDDY 2.0 Cross-Platform Basic Demonstration

Demonstrates cross-platform device simulation without complex sync engine.
Shows the foundation for multi-device BUDDY deployment.
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import BUDDY components
try:
    from buddy_core.memory import EnhancedMemoryLayer
    MEMORY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"BUDDY memory components not available: {e}")
    MEMORY_AVAILABLE = False


class BasicDeviceSimulator:
    """Basic device simulator for cross-platform demonstration."""
    
    def __init__(self, device_type: str, user_id: str, device_name: str = None):
        self.device_type = device_type
        self.device_id = f"{device_type}_{uuid.uuid4().hex[:8]}"
        self.user_id = user_id
        self.device_name = device_name or f"{device_type.title()} Device"
        self.memory_layer = None
        self.conversation_count = 0
        self.is_online = True
        self.preferences = {}
        self.conversations = []
        
    async def initialize(self):
        """Initialize the basic device simulator."""
        logger.info(f"🔧 Initializing {self.device_name} ({self.device_id})")
        
        if MEMORY_AVAILABLE:
            # Initialize memory layer
            self.memory_layer = EnhancedMemoryLayer(config={
                'user_id': self.user_id,
                'device_id': self.device_id,
                'device_type': self.device_type
            })
            await self.memory_layer.initialize()
        
        logger.info(f"✅ {self.device_name} initialized successfully")
    
    async def send_message(self, message: str, message_type: str = "user") -> str:
        """Send a message from this device."""
        # Enhanced message with device context
        enhanced_message = f"[{self.device_type.upper()}] {message}"
        
        # Create conversation record
        conversation_record = {
            'id': str(uuid.uuid4()),
            'content': enhanced_message,
            'message_type': message_type,
            'device_id': self.device_id,
            'device_type': self.device_type,
            'device_name': self.device_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'capabilities': self._get_capabilities(),
            'message_number': self.conversation_count
        }
        
        # Store in memory layer if available
        if self.memory_layer and hasattr(self.memory_layer, 'store_conversation'):
            try:
                await self.memory_layer.store_conversation(
                    content=enhanced_message,
                    message_type=message_type,
                    session_id=f"session_{self.device_type}_{self.user_id}",
                    metadata=conversation_record
                )
            except Exception as e:
                logger.warning(f"Failed to store in memory layer: {e}")
        
        # Store locally for demo purposes
        self.conversations.append(conversation_record)
        self.conversation_count += 1
        
        logger.info(f"📱 {self.device_name}: Sent '{message}' (ID: {conversation_record['id'][:8]})")
        return conversation_record['id']
    
    async def set_preference(self, key: str, value: Any, device_specific: bool = True):
        """Set a device preference."""
        self.preferences[key] = {
            'value': value,
            'device_specific': device_specific,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Store in memory layer if available
        if self.memory_layer and hasattr(self.memory_layer, 'set_preference'):
            try:
                await self.memory_layer.set_preference(key, value)
            except Exception as e:
                logger.warning(f"Failed to store preference: {e}")
        
        scope = "device-specific" if device_specific else "global"
        logger.info(f"⚙️  {self.device_name}: Set {scope} preference '{key}' = '{value}'")
    
    async def simulate_offline(self, duration_seconds: int = 3):
        """Simulate device going offline."""
        logger.info(f"📴 {self.device_name}: Going offline for {duration_seconds} seconds")
        self.is_online = False
        await asyncio.sleep(duration_seconds)
        logger.info(f"📶 {self.device_name}: Coming back online")
        self.is_online = True
    
    async def perform_device_action(self):
        """Perform a device-specific action."""
        actions = {
            'desktop': "Opening productivity suite and checking calendar",
            'mobile': "Using GPS to find nearby coffee shops",
            'watch': "Checking heart rate and daily activity goals",
            'tv': "Adjusting smart home lighting and playing music",
            'car': "Starting navigation to next appointment"
        }
        
        action = actions.get(self.device_type, "Performing device-specific task")
        await self.send_message(f"Action: {action}", "system")
        logger.info(f"🎯 {self.device_name}: {action}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get device status."""
        return {
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'is_online': self.is_online,
            'conversation_count': self.conversation_count,
            'preferences_count': len(self.preferences),
            'capabilities': self._get_capabilities(),
            'memory_available': MEMORY_AVAILABLE and self.memory_layer is not None
        }
    
    def _get_capabilities(self) -> List[str]:
        """Get device-specific capabilities."""
        capabilities_map = {
            'desktop': ['voice_input', 'voice_output', 'screen_large', 'keyboard', 'mouse', 'file_system', 'multitasking'],
            'mobile': ['voice_input', 'voice_output', 'screen_medium', 'touch', 'location', 'camera', 'cellular', 'bluetooth'],
            'watch': ['voice_input', 'voice_output', 'screen_small', 'touch', 'health_sensors', 'haptic', 'always_on'],
            'tv': ['voice_input', 'voice_output', 'screen_large', 'remote_control', 'hdmi', 'streaming'],
            'car': ['voice_input', 'voice_output', 'location', 'navigation', 'vehicle_integration', 'hands_free']
        }
        return capabilities_map.get(self.device_type, ['basic'])
    
    async def close(self):
        """Close the device simulator."""
        if self.memory_layer:
            await self.memory_layer.close()
        logger.info(f"🔌 {self.device_name} closed")


class BasicCrossPlatformDemo:
    """Basic cross-platform demonstration."""
    
    def __init__(self):
        self.user_id = f"demo_user_{uuid.uuid4().hex[:8]}"
        self.devices = {}
        self.demo_scenarios = [
            self.scenario_device_setup,
            self.scenario_multi_device_messaging,
            self.scenario_device_preferences,
            self.scenario_device_capabilities,
            self.scenario_offline_simulation,
            self.scenario_status_overview
        ]
    
    async def setup_devices(self):
        """Set up simulated devices."""
        device_configs = [
            ('desktop', 'Alex\'s MacBook Pro'),
            ('mobile', 'Alex\'s iPhone 15'),
            ('watch', 'Alex\'s Apple Watch'),
            ('tv', 'Living Room Smart TV'),
            ('car', 'Tesla Model 3')
        ]
        
        logger.info(f"🚀 Setting up BUDDY Basic Cross-Platform Demo")
        logger.info(f"👤 Demo User: {self.user_id}")
        logger.info("=" * 60)
        
        for device_type, device_name in device_configs:
            device = BasicDeviceSimulator(device_type, self.user_id, device_name)
            await device.initialize()
            self.devices[device_type] = device
            await asyncio.sleep(0.3)  # Simulate realistic setup time
        
        logger.info("=" * 60)
        logger.info("✅ All devices initialized successfully!")
        await asyncio.sleep(1)
    
    async def scenario_device_setup(self):
        """Show device setup and capabilities."""
        logger.info("\n🔧 SCENARIO 1: Device Setup & Capabilities")
        logger.info("-" * 45)
        
        for device_name, device in self.devices.items():
            status = device.get_status()
            capabilities = status['capabilities']
            
            logger.info(f"📱 {device.device_name}:")
            logger.info(f"   Type: {device.device_type}")
            logger.info(f"   ID: {device.device_id}")
            logger.info(f"   Capabilities: {', '.join(capabilities[:3])}...")
            logger.info(f"   Status: {'🟢 Online' if status['is_online'] else '🔴 Offline'}")
            logger.info(f"   Memory Layer: {'✅ Available' if status['memory_available'] else '❌ Basic'}")
        
        await asyncio.sleep(1)
    
    async def scenario_multi_device_messaging(self):
        """Test messaging across devices."""
        logger.info("\n💬 SCENARIO 2: Multi-Device Messaging")
        logger.info("-" * 45)
        
        # Simulate a day's worth of interactions
        interactions = [
            ('desktop', "Good morning BUDDY! Starting my work day."),
            ('mobile', "Walking to first meeting, what's on my calendar?"),
            ('watch', "Heart rate is up, taking the stairs."),
            ('car', "Driving to lunch, need directions to new restaurant."),
            ('tv', "Evening relaxation time, dim the lights please."),
            ('mobile', "Checking tomorrow's weather before bed."),
        ]
        
        for device_type, message in interactions:
            await self.devices[device_type].send_message(message)
            await asyncio.sleep(0.8)  # Simulate realistic timing
        
        # Show message counts
        logger.info("\n📊 Message Summary:")
        total_messages = 0
        for device_name, device in self.devices.items():
            count = device.conversation_count
            total_messages += count
            logger.info(f"   {device.device_name}: {count} messages")
        
        logger.info(f"   Total: {total_messages} messages across all devices")
        await asyncio.sleep(1)
    
    async def scenario_device_preferences(self):
        """Test preference management."""
        logger.info("\n⚙️  SCENARIO 3: Device Preferences")
        logger.info("-" * 45)
        
        # Global preferences
        await self.devices['desktop'].set_preference("theme", "dark", device_specific=False)
        await self.devices['desktop'].set_preference("language", "en-US", device_specific=False)
        
        # Device-specific preferences
        preferences = [
            ('mobile', 'notification_style', 'vibrate_only'),
            ('watch', 'complications', ['weather', 'calendar', 'activity']),
            ('tv', 'volume_default', 25),
            ('car', 'navigation_voice', 'male'),
            ('desktop', 'screen_brightness', 0.75)
        ]
        
        for device_type, key, value in preferences:
            await self.devices[device_type].set_preference(key, value, device_specific=True)
            await asyncio.sleep(0.2)
        
        logger.info("✅ Preferences configured across all devices")
        await asyncio.sleep(1)
    
    async def scenario_device_capabilities(self):
        """Demonstrate device-specific capabilities."""
        logger.info("\n🎯 SCENARIO 4: Device-Specific Capabilities")
        logger.info("-" * 45)
        
        for device_name, device in self.devices.items():
            await device.perform_device_action()
            await asyncio.sleep(0.5)
        
        logger.info("✅ All devices performed their specialized actions")
        await asyncio.sleep(1)
    
    async def scenario_offline_simulation(self):
        """Simulate offline/online behavior."""
        logger.info("\n📴 SCENARIO 5: Offline/Online Simulation")
        logger.info("-" * 45)
        
        # Take mobile offline
        mobile = self.devices['mobile']
        
        # Send message while online
        await mobile.send_message("About to lose signal, save this state")
        
        # Simulate going offline
        await mobile.simulate_offline(duration_seconds=2)
        
        # Other devices continue working
        await self.devices['desktop'].send_message("Working while mobile is offline")
        await self.devices['watch'].send_message("Quick status check")
        
        # Mobile is back online
        await mobile.send_message("Back online, catching up on messages")
        
        logger.info("✅ Offline/online simulation completed")
        await asyncio.sleep(1)
    
    async def scenario_status_overview(self):
        """Show comprehensive status overview."""
        logger.info("\n📊 SCENARIO 6: Status Overview")
        logger.info("-" * 45)
        
        total_messages = 0
        total_preferences = 0
        
        for device_name, device in self.devices.items():
            status = device.get_status()
            
            logger.info(f"\n📱 {device.device_name.upper()}:")
            logger.info(f"   Device ID: {status['device_id'][:16]}...")
            logger.info(f"   Type: {status['device_type']}")
            logger.info(f"   Status: {'🟢 Online' if status['is_online'] else '🔴 Offline'}")
            logger.info(f"   Conversations: {status['conversation_count']}")
            logger.info(f"   Preferences: {status['preferences_count']}")
            logger.info(f"   Capabilities: {len(status['capabilities'])} features")
            logger.info(f"   Memory: {'✅ Enhanced' if status['memory_available'] else '❌ Basic'}")
            
            total_messages += status['conversation_count']
            total_preferences += status['preferences_count']
        
        logger.info(f"\n📈 OVERALL STATISTICS:")
        logger.info(f"   Total Devices: {len(self.devices)}")
        logger.info(f"   Total Messages: {total_messages}")
        logger.info(f"   Total Preferences: {total_preferences}")
        logger.info(f"   User ID: {self.user_id}")
        logger.info(f"   Memory System: {'✅ BUDDY Enhanced' if MEMORY_AVAILABLE else '❌ Basic Simulation'}")
        
        await asyncio.sleep(1)
    
    async def run_demo(self):
        """Run the complete basic cross-platform demonstration."""
        try:
            # Setup
            await self.setup_devices()
            
            # Run all scenarios
            for i, scenario in enumerate(self.demo_scenarios, 1):
                await scenario()
                if i < len(self.demo_scenarios):
                    await asyncio.sleep(1)  # Brief pause between scenarios
            
            # Demo completion
            logger.info("\n🎉 BASIC CROSS-PLATFORM DEMO COMPLETED!")
            logger.info("=" * 60)
            logger.info("🚀 BUDDY Cross-Platform Foundation Demonstrated:")
            logger.info("   ✅ Multi-device simulation and management")
            logger.info("   ✅ Device-aware capabilities and actions")
            logger.info("   ✅ Cross-device preference management")
            logger.info("   ✅ Offline/online state handling")
            logger.info("   ✅ Device-specific feature utilization")
            logger.info("   ✅ Comprehensive status monitoring")
            logger.info("=" * 60)
            logger.info("🔧 Ready for sync engine integration!")
            
        except Exception as e:
            logger.error(f"❌ Basic demo failed: {e}")
            raise
        
        finally:
            # Cleanup
            logger.info("\n🧹 Cleaning up devices...")
            for device in self.devices.values():
                await device.close()
            logger.info("✅ Cleanup complete!")


async def main():
    """Main entry point for basic cross-platform demo."""
    print("🤖 BUDDY 2.0 Basic Cross-Platform Demonstration")
    print("=" * 50)
    print()
    
    if MEMORY_AVAILABLE:
        print("🟢 Running with BUDDY memory system:")
        print("   ✅ Enhanced memory layer")
        print("   ✅ Local database storage")
        print("   ✅ Vector database for AI context")
    else:
        print("🟡 Running in basic simulation mode:")
        print("   ⚠️  BUDDY components not available")
        print("   ⚠️  Using simplified device simulation")
    
    print()
    print("🚀 Cross-Platform Support:")
    print("   📱 Mobile (iOS/Android)")
    print("   🖥️  Desktop (Windows/macOS/Linux)")
    print("   ⌚ Smartwatches (Apple Watch/Wear OS)")
    print("   📺 Smart TVs (universal interface)")
    print("   🚗 Automotive (CarPlay/Android Auto)")
    print()
    
    # Create and run demo
    demo = BasicCrossPlatformDemo()
    await demo.run_demo()
    
    print("\n🎯 Basic demo completed successfully!")
    print("   This demonstrates BUDDY's foundation for cross-platform deployment")
    print("   with device-aware intelligence and seamless multi-device experience.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
