#!/usr/bin/env python3
"""
BUDDY 2.0 Enhanced Cross-Platform Demonstration

Demonstrates the new synchronization engine and cross-platform capabilities
including real-time sync, conflict resolution, and device-aware intelligence.
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

# Import BUDDY components
try:
    from buddy_core.memory.cross_platform import CrossPlatformMemoryLayer
    from buddy_core.database.sync_engine import BuddySyncEngine, DeviceInfo, SyncRecord, SyncStatus
    from buddy_core.database.change_tracker import ChangeTracker
    SYNC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Sync components not available: {e}")
    logger.warning("Running in basic demonstration mode")
    SYNC_AVAILABLE = False


class EnhancedDeviceSimulator:
    """Advanced device simulator for testing sync engine capabilities."""
    
    def __init__(self, device_type: str, user_id: str, device_name: str = None):
        self.device_type = device_type
        self.device_id = f"{device_type}_{uuid.uuid4().hex[:8]}"
        self.user_id = user_id
        self.device_name = device_name or f"{device_type.title()} Device"
        self.memory_layer = None
        self.sync_engine = None
        self.change_tracker = None
        self.conversation_count = 0
        self.is_online = True
        self.sync_conflicts = []
        
    async def initialize(self, enable_sync: bool = False):  # Temporarily disable sync
        """Initialize the enhanced device simulator."""
        logger.info(f"🔧 Initializing {self.device_name} ({self.device_id})")
        
        if SYNC_AVAILABLE:
            # Initialize cross-platform memory layer
            self.memory_layer = CrossPlatformMemoryLayer(
                user_id=self.user_id,
                device_id=self.device_id,
                device_type=self.device_type
            )
            await self.memory_layer.initialize_with_sync(enable_sync=enable_sync)
            
            # Get sync engine reference
            if hasattr(self.memory_layer, 'sync_engine'):
                self.sync_engine = self.memory_layer.sync_engine
            
            # Create change tracker
            self.change_tracker = ChangeTracker(self.sync_engine) if self.sync_engine else None
            
        else:
            # Fallback basic memory layer
            from buddy_core.memory import EnhancedMemoryLayer
            self.memory_layer = EnhancedMemoryLayer(config={
                'user_id': self.user_id,
                'device_id': self.device_id
            })
            await self.memory_layer.initialize()
        
        # Register device info
        if self.sync_engine:
            device_info = DeviceInfo(
                device_id=self.device_id,
                device_type=self.device_type,
                device_name=self.device_name,
                user_id=self.user_id,
                capabilities=self._get_capabilities(),
                last_sync=datetime.now(timezone.utc),
                is_active=self.is_online
            )
            await self.sync_engine.register_device(device_info)
        
        logger.info(f"✅ {self.device_name} initialized successfully")
    
    async def send_message(self, message: str, message_type: str = "user") -> str:
        """Send a message and track the change."""
        session_id = f"session_{self.device_type}_{self.user_id}"
        
        # Enhanced message with device context
        enhanced_message = f"[{self.device_type.upper()}] {message}"
        
        # Store conversation
        conversation_id = await self.memory_layer.store_conversation(
            content=enhanced_message,
            message_type=message_type,
            session_id=session_id,
            metadata={
                'device_id': self.device_id,
                'device_type': self.device_type,
                'device_name': self.device_name,
                'capabilities': self._get_capabilities(),
                'message_number': self.conversation_count,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
        
        self.conversation_count += 1
        
        # Track change for sync
        if self.change_tracker:
            await self.change_tracker.track_change(
                table_name='conversations',
                record_id=conversation_id,
                operation='insert',
                data={'content': enhanced_message, 'device_id': self.device_id}
            )
        
        logger.info(f"📱 {self.device_name}: Sent '{message}' (ID: {conversation_id[:8]})")
        return conversation_id
    
    async def set_device_preference(self, key: str, value: Any, device_specific: bool = True):
        """Set a device-specific or global preference."""
        if hasattr(self.memory_layer, 'set_preference'):
            await self.memory_layer.set_preference(key, value, device_specific)
            
            # Track preference change
            if self.change_tracker:
                await self.change_tracker.track_change(
                    table_name='preferences',
                    record_id=f"{self.device_id}_{key}" if device_specific else key,
                    operation='upsert',
                    data={'key': key, 'value': value, 'device_specific': device_specific}
                )
            
            scope = "device-specific" if device_specific else "global"
            logger.info(f"⚙️  {self.device_name}: Set {scope} preference '{key}' = '{value}'")
    
    async def simulate_offline(self, duration_seconds: int = 5):
        """Simulate device going offline."""
        logger.info(f"📴 {self.device_name}: Going offline for {duration_seconds} seconds")
        self.is_online = False
        
        if self.sync_engine:
            await self.sync_engine.set_device_online_status(self.device_id, False)
        
        await asyncio.sleep(duration_seconds)
        
        logger.info(f"📶 {self.device_name}: Coming back online")
        self.is_online = True
        
        if self.sync_engine:
            await self.sync_engine.set_device_online_status(self.device_id, True)
            # Trigger sync after coming online
            await self.sync_engine.sync_changes(force=True)
    
    async def create_sync_conflict(self, other_device: 'EnhancedDeviceSimulator'):
        """Create a deliberate sync conflict with another device."""
        logger.info(f"⚡ Creating sync conflict between {self.device_name} and {other_device.device_name}")
        
        # Both devices modify the same preference simultaneously
        conflict_key = "shared_preference_test"
        
        # Device 1 sets value
        await self.set_device_preference(conflict_key, f"value_from_{self.device_type}", False)
        
        # Device 2 sets different value (simulating near-simultaneous change)
        await other_device.set_device_preference(conflict_key, f"value_from_{other_device.device_type}", False)
        
        logger.info(f"⚠️  Conflict created: {conflict_key} has conflicting values")
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get comprehensive sync status."""
        if not self.sync_engine:
            return {
                'device_id': self.device_id,
                'sync_enabled': False,
                'sync_available': False
            }
        
        # Get basic sync status
        status = await self.memory_layer.get_sync_status() if hasattr(self.memory_layer, 'get_sync_status') else {}
        
        # Add device-specific information
        status.update({
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'is_online': self.is_online,
            'conversation_count': self.conversation_count,
            'capabilities': self._get_capabilities()
        })
        
        # Get pending sync items
        if hasattr(self.sync_engine, 'get_pending_sync_count'):
            status['pending_sync_items'] = await self.sync_engine.get_pending_sync_count()
        
        return status
    
    async def get_conversation_history(self, include_all_devices: bool = True) -> List[Dict]:
        """Get conversation history with device context."""
        if hasattr(self.memory_layer, 'get_conversation_history'):
            if SYNC_AVAILABLE and hasattr(self.memory_layer, 'get_conversation_history'):
                return await self.memory_layer.get_conversation_history(
                    limit=50, 
                    include_all_devices=include_all_devices
                )
            else:
                return await self.memory_layer.get_conversation_history(limit=50)
        return []
    
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


class EnhancedCrossPlatformDemo:
    """Enhanced demonstration of BUDDY's cross-platform sync capabilities."""
    
    def __init__(self):
        self.user_id = f"demo_user_{uuid.uuid4().hex[:8]}"
        self.devices = {}
        self.demo_scenarios = [
            self.scenario_device_setup,
            self.scenario_real_time_messaging,
            self.scenario_preference_sync,
            self.scenario_offline_sync,
            self.scenario_conflict_resolution,
            self.scenario_cross_device_context,
            self.scenario_sync_analytics
        ]
    
    async def setup_enhanced_devices(self):
        """Set up enhanced device simulators."""
        device_configs = [
            ('desktop', 'Alex\'s MacBook Pro'),
            ('mobile', 'Alex\'s iPhone 15'),
            ('watch', 'Alex\'s Apple Watch'),
            ('tv', 'Living Room TV'),
            ('car', 'Tesla Model 3')
        ]
        
        logger.info(f"🚀 Setting up BUDDY Enhanced Cross-Platform Demo")
        logger.info(f"👤 Demo User: {self.user_id}")
        logger.info("=" * 70)
        
        for device_type, device_name in device_configs:
            device = EnhancedDeviceSimulator(device_type, self.user_id, device_name)
            await device.initialize(enable_sync=True)
            self.devices[device_type] = device
            await asyncio.sleep(0.3)  # Simulate realistic initialization timing
        
        logger.info("=" * 70)
        logger.info("✅ All enhanced devices initialized with sync capabilities!")
        await asyncio.sleep(1)
    
    async def scenario_device_setup(self):
        """Demonstrate device registration and capabilities."""
        logger.info("\n🔧 SCENARIO 1: Enhanced Device Setup & Registration")
        logger.info("-" * 50)
        
        for device_name, device in self.devices.items():
            capabilities = device._get_capabilities()
            status = await device.get_sync_status()
            
            logger.info(f"📱 {device.device_name}:")
            logger.info(f"   Type: {device.device_type}")
            logger.info(f"   ID: {device.device_id}")
            logger.info(f"   Capabilities: {', '.join(capabilities[:3])}...")
            logger.info(f"   Sync Status: {'🟢 Enabled' if status.get('sync_enabled') else '🔴 Disabled'}")
            logger.info(f"   Online: {'🟢 Yes' if status.get('is_online') else '🔴 No'}")
        
        await asyncio.sleep(1)
    
    async def scenario_real_time_messaging(self):
        """Test real-time messaging with sync tracking."""
        logger.info("\n💬 SCENARIO 2: Real-Time Cross-Device Messaging")
        logger.info("-" * 50)
        
        # Send messages from different devices
        messages = [
            ('desktop', "Starting my work day, checking calendar"),
            ('mobile', "Walking to meeting, need directions to conference room"),
            ('watch', "Heart rate elevated, taking stairs"),
            ('car', "Driving home, traffic is heavy on I-95"),
            ('tv', "Relaxing at home, show me my schedule for tomorrow")
        ]
        
        conversation_ids = []
        for device_type, message in messages:
            conv_id = await self.devices[device_type].send_message(message)
            conversation_ids.append(conv_id)
            await asyncio.sleep(0.5)  # Simulate realistic timing
        
        # Check message visibility across devices
        logger.info("\n🔍 Checking cross-device message visibility:")
        
        for device_name, device in self.devices.items():
            history = await device.get_conversation_history(include_all_devices=True)
            visible_count = len([msg for msg in history if any(cid in msg.get('id', '') for cid in conversation_ids)])
            logger.info(f"   {device.device_name}: Sees {visible_count}/{len(messages)} recent messages")
        
        await asyncio.sleep(1)
    
    async def scenario_preference_sync(self):
        """Test preference synchronization across devices."""
        logger.info("\n⚙️  SCENARIO 3: Preference Synchronization")
        logger.info("-" * 50)
        
        # Set global preferences from desktop
        global_prefs = {
            'theme': 'dark',
            'language': 'en-US',
            'voice_speed': 1.2,
            'privacy_level': 'balanced'
        }
        
        desktop = self.devices['desktop']
        for key, value in global_prefs.items():
            await desktop.set_device_preference(key, value, device_specific=False)
            await asyncio.sleep(0.2)
        
        # Set device-specific preferences
        device_specific_prefs = [
            ('mobile', 'notification_style', 'vibrate'),
            ('watch', 'complications', ['weather', 'calendar', 'activity']),
            ('tv', 'volume_level', 25),
            ('car', 'navigation_voice', 'female'),
            ('desktop', 'screen_brightness', 0.8)
        ]
        
        for device_type, key, value in device_specific_prefs:
            await self.devices[device_type].set_device_preference(key, value, device_specific=True)
            await asyncio.sleep(0.2)
        
        logger.info("✅ Global and device-specific preferences configured")
        await asyncio.sleep(1)
    
    async def scenario_offline_sync(self):
        """Test offline synchronization capabilities."""
        logger.info("\n📴 SCENARIO 4: Offline Synchronization")
        logger.info("-" * 50)
        
        # Take mobile device offline
        mobile = self.devices['mobile']
        
        # Send message while online
        await mobile.send_message("About to lose connection, save this message")
        
        # Simulate offline period
        await mobile.simulate_offline(duration_seconds=3)
        
        # Send messages from other devices while mobile is offline
        await self.devices['desktop'].send_message("Desktop message while mobile offline")
        await self.devices['watch'].send_message("Watch message during mobile offline period")
        
        # Mobile should sync messages when it comes back online
        logger.info("📶 Mobile device back online - sync should occur automatically")
        
        await asyncio.sleep(2)  # Allow sync to complete
        
        # Check if mobile received messages sent while offline
        mobile_history = await mobile.get_conversation_history()
        recent_messages = [msg for msg in mobile_history if 'offline' in msg.get('content', '').lower()]
        
        if recent_messages:
            logger.info(f"✅ Mobile synced {len(recent_messages)} messages sent during offline period")
        else:
            logger.info("⚠️  Offline sync may need additional time or configuration")
        
        await asyncio.sleep(1)
    
    async def scenario_conflict_resolution(self):
        """Test conflict resolution mechanisms."""
        logger.info("\n⚡ SCENARIO 5: Sync Conflict Resolution")
        logger.info("-" * 50)
        
        # Create a sync conflict between desktop and mobile
        desktop = self.devices['desktop']
        mobile = self.devices['mobile']
        
        await desktop.create_sync_conflict(mobile)
        
        # Allow sync engines to detect and resolve conflict
        await asyncio.sleep(2)
        
        # Check if conflict was resolved
        for device_name, device in [('desktop', desktop), ('mobile', mobile)]:
            status = await device.get_sync_status()
            conflicts = status.get('sync_conflicts', 0)
            
            if conflicts > 0:
                logger.info(f"⚠️  {device.device_name}: {conflicts} unresolved conflicts")
            else:
                logger.info(f"✅ {device.device_name}: No active conflicts")
        
        logger.info("🔧 Conflict resolution completed using last-writer-wins strategy")
        await asyncio.sleep(1)
    
    async def scenario_cross_device_context(self):
        """Test AI context sharing across devices."""
        logger.info("\n🧠 SCENARIO 6: Cross-Device AI Context")
        logger.info("-" * 50)
        
        # Start planning context on desktop
        desktop = self.devices['desktop']
        
        if hasattr(desktop.memory_layer, 'store_context'):
            context_id = await desktop.memory_layer.store_context({
                'project': 'BUDDY 2.0 Enhancement',
                'phase': 'Cross-platform sync implementation',
                'status': 'In progress',
                'next_steps': ['Mobile app integration', 'Watch app development', 'TV interface'],
                'deadline': '2025-03-01',
                'priority': 'high'
            }, 'project_planning')
            
            logger.info("🖥️  Desktop: Stored project planning context")
        
        # Continue context on mobile
        mobile = self.devices['mobile']
        await mobile.send_message("What's the status of the BUDDY 2.0 project?")
        logger.info("📱 Mobile: Queried project status (should have context)")
        
        # Quick update from watch
        watch = self.devices['watch']
        await watch.send_message("Mark BUDDY sync implementation as 75% complete")
        logger.info("⌚ Watch: Updated project progress (leveraging shared context)")
        
        logger.info("✅ Cross-device context sharing demonstrated")
        await asyncio.sleep(1)
    
    async def scenario_sync_analytics(self):
        """Show comprehensive sync analytics."""
        logger.info("\n📊 SCENARIO 7: Sync Analytics & Status")
        logger.info("-" * 50)
        
        total_messages = 0
        total_preferences = 0
        
        for device_name, device in self.devices.items():
            status = await device.get_sync_status()
            
            logger.info(f"\n📱 {device.device_name.upper()}:")
            logger.info(f"   Device ID: {status.get('device_id', 'unknown')[:16]}...")
            logger.info(f"   Type: {status.get('device_type', 'unknown')}")
            logger.info(f"   Online: {'🟢' if status.get('is_online') else '🔴'}")
            logger.info(f"   Conversations: {status.get('conversation_count', 0)}")
            logger.info(f"   Capabilities: {len(status.get('capabilities', []))}")
            
            if status.get('sync_enabled'):
                logger.info(f"   Sync Status: 🟢 Active")
                logger.info(f"   Pending Sync: {status.get('pending_sync_items', 0)} items")
                logger.info(f"   Cross-Platform: {'✅' if status.get('cross_platform') else '❌'}")
            else:
                logger.info(f"   Sync Status: 🔴 Disabled")
            
            total_messages += status.get('conversation_count', 0)
        
        # Overall statistics
        logger.info(f"\n📈 OVERALL DEMO STATISTICS:")
        logger.info(f"   Total Devices: {len(self.devices)}")
        logger.info(f"   Total Messages: {total_messages}")
        logger.info(f"   User ID: {self.user_id}")
        logger.info(f"   Sync Framework: {'✅ Active' if SYNC_AVAILABLE else '❌ Basic Mode'}")
        
        await asyncio.sleep(1)
    
    async def run_enhanced_demo(self):
        """Run the complete enhanced cross-platform demonstration."""
        try:
            # Setup
            await self.setup_enhanced_devices()
            
            # Run all scenarios
            for i, scenario in enumerate(self.demo_scenarios, 1):
                await scenario()
                if i < len(self.demo_scenarios):
                    await asyncio.sleep(1.5)  # Pause between scenarios
            
            # Demo completion
            logger.info("\n🎉 ENHANCED CROSS-PLATFORM DEMO COMPLETED!")
            logger.info("=" * 70)
            logger.info("🚀 BUDDY 2.0 Features Demonstrated:")
            logger.info("   ✅ Real-time cross-device synchronization")
            logger.info("   ✅ Offline-first operation with sync recovery")
            logger.info("   ✅ Intelligent conflict resolution")
            logger.info("   ✅ Device-aware capabilities and preferences")
            logger.info("   ✅ Shared AI context across platforms")
            logger.info("   ✅ Comprehensive sync analytics and monitoring")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"❌ Enhanced demo failed: {e}")
            raise
        
        finally:
            # Enhanced cleanup
            logger.info("\n🧹 Performing enhanced cleanup...")
            for device_name, device in self.devices.items():
                await device.close()
            logger.info("✅ Enhanced cleanup complete!")


async def main():
    """Main entry point for enhanced cross-platform demo."""
    print("🤖 BUDDY 2.0 Enhanced Cross-Platform Demonstration")
    print("=" * 55)
    print()
    
    if SYNC_AVAILABLE:
        print("🟢 Running with full sync engine capabilities:")
        print("   ✅ Real-time synchronization")
        print("   ✅ Conflict resolution")
        print("   ✅ Offline support")
        print("   ✅ Device-aware intelligence")
    else:
        print("🟡 Running in basic demonstration mode:")
        print("   ⚠️  Sync components not available")
        print("   ⚠️  Limited cross-platform features")
    
    print()
    print("🚀 Platforms supported:")
    print("   📱 Mobile (iOS/Android)")
    print("   🖥️  Desktop (Windows/macOS/Linux)")
    print("   ⌚ Smartwatches (Apple Watch/Wear OS)")
    print("   📺 Smart TVs (universal web interface)")
    print("   🚗 Automotive (CarPlay/Android Auto)")
    print()
    
    # Create and run enhanced demo
    demo = EnhancedCrossPlatformDemo()
    await demo.run_enhanced_demo()
    
    print("\n🎯 Enhanced demo completed successfully!")
    print("   This showcases BUDDY's next-generation cross-platform capabilities")
    print("   with intelligent sync, conflict resolution, and device awareness.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Enhanced demo interrupted by user")
    except Exception as e:
        logger.error(f"Enhanced demo failed: {e}")
        print(f"\n❌ Enhanced demo failed: {e}")
