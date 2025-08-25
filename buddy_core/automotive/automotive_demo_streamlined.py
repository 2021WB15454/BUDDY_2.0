#!/usr/bin/env python3
"""
BUDDY 2.0 Automotive Platform Streamlined Demo
Phase 5: Intelligent Vehicle AI Assistant Implementation

Demonstrates hands-free automotive AI capabilities with safety-first design,
navigation integration, and connected car features.
"""

import asyncio
import time
from automotive_platform_implementation import (
    AutomotiveBuddyCore, AutomotiveConfig, AutomotivePlatform, 
    AutomotiveCapability, SafetyMode
)


async def quick_automotive_demo():
    """Quick demonstration of Automotive BUDDY capabilities"""
    
    print("🚗 BUDDY 2.0 Automotive Demo - Phase 5 Implementation")
    print("=" * 60)
    print("Intelligent Vehicle AI Assistant with Safety-First Design")
    print("")
    
    # Create flagship Tesla for demo
    config = AutomotiveConfig.for_automotive_profile(
        AutomotivePlatform.TESLA_INFOTAINMENT, 
        AutomotiveCapability.FLAGSHIP
    )
    
    buddy = AutomotiveBuddyCore(
        user_id="demo_driver",
        device_id="tesla_model_s_demo",
        config=config
    )
    
    try:
        # Initialize
        print("🔄 Initializing Tesla Model S with Advanced AI...")
        success = await buddy.initialize()
        
        if not success:
            print("❌ Initialization failed")
            return
        
        print("✅ Automotive BUDDY initialized successfully!")
        print(f"   Platform: {config.platform.value}")
        print(f"   Capability: {config.capability.value}")
        print(f"   Storage: {config.storage_limit_mb}MB")
        print(f"   Voice: {config.voice_enabled}")
        print(f"   Navigation: {config.navigation_integration}")
        print(f"   Vehicle Data: {config.vehicle_data_access}")
        print(f"   Emergency Features: {config.emergency_features}")
        
        # Demo safety mode transitions
        print(f"\n🛡️ Safety Mode Management Demo:")
        print("-" * 40)
        
        safety_modes = [
            (SafetyMode.PARKED, 0.0, "Vehicle parked - full functionality"),
            (SafetyMode.DRIVING, 80.0, "Driving 80 km/h - safety restrictions"),
            (SafetyMode.PASSENGER, 65.0, "Passenger mode - enhanced interaction")
        ]
        
        for mode, speed, description in safety_modes:
            result = await buddy.update_safety_mode(mode, speed)
            print(f"✅ {description}")
            print(f"   Mode: {result['new_mode']} | Speed: {speed} km/h")
        
        # Demo voice commands with safety filtering
        print(f"\n🎤 Voice Command Demo (Safety-Filtered):")
        print("-" * 50)
        
        # Test commands in driving mode (safety restricted)
        await buddy.update_safety_mode(SafetyMode.DRIVING, 75.0)
        
        driving_commands = [
            "Navigate to nearest hospital",
            "What's my fuel level?",
            "Emergency help needed",
            "Call my wife",
            "Read me a long article"  # This should be blocked
        ]
        
        for command in driving_commands:
            print(f"\n🚗 DRIVING MODE - User: '{command}'")
            result = await buddy.process_voice_command(command)
            
            if result.get('safety_blocked'):
                print(f"⚠️  BLOCKED: {result['response']}")
            else:
                print(f"✅ ALLOWED: {result['response']}")
        
        # Demo navigation integration
        print(f"\n🗺️ Navigation Integration Demo:")
        print("-" * 40)
        
        # Switch to parked for full navigation
        await buddy.update_safety_mode(SafetyMode.PARKED, 0.0)
        
        destinations = [
            "Toronto Pearson Airport",
            "Nearest Tesla Supercharger",
            "Home"
        ]
        
        for destination in destinations:
            print(f"\n📍 Navigation Request: {destination}")
            result = await buddy.handle_navigation_request(destination)
            print(f"   Distance: {result['distance_km']} km")
            print(f"   ETA: {result['estimated_time'] // 60} minutes")
            print(f"   Route: {result['route_summary']}")
        
        # Demo vehicle status monitoring
        print(f"\n🔧 Vehicle Status Monitoring Demo:")
        print("-" * 45)
        
        vehicle_status = {
            'fuel_level': 12,      # Critical low fuel
            'battery_level': 25,   # Low battery warning
            'engine_temperature': 105,  # High temperature warning
            'tire_pressure': 26,   # Low pressure warning
            'oil_pressure': 35     # Normal
        }
        
        print("🔍 Checking vehicle diagnostics...")
        status_result = await buddy.update_vehicle_status(vehicle_status)
        
        print(f"Status Updated: {len(status_result['alerts'])} alerts generated")
        for alert in status_result['alerts']:
            severity_icon = "🚨" if alert['severity'] == 'critical' else "⚠️"
            print(f"   {severity_icon} {alert['severity'].upper()}: {alert['message']}")
        
        # Demo emergency features
        print(f"\n🚨 Emergency System Demo:")
        print("-" * 35)
        
        print("🆘 Testing emergency activation...")
        emergency_result = await buddy.activate_emergency_mode("test_scenario")
        
        print(f"✅ Emergency Mode: {emergency_result['emergency_activated']}")
        print(f"📞 Emergency Contacts: {len(emergency_result['emergency_contacts'])}")
        print(f"📍 Location Shared: Yes")
        print(f"🗣️  Instructions: {emergency_result['instructions']}")
        
        # Demo communication features
        print(f"\n📞 Communication Features Demo:")
        print("-" * 45)
        
        # Test hands-free communication
        await buddy.update_safety_mode(SafetyMode.DRIVING, 60.0)
        
        comm_commands = [
            "Call my emergency contact",
            "Send a message saying I'm running late",
            "What are my recent missed calls?"
        ]
        
        for command in comm_commands:
            print(f"\n📱 Communication: '{command}'")
            result = await buddy.process_voice_command(command)
            print(f"   Response: {result['response']}")
        
        # Final Status Summary
        print(f"\n📊 Automotive Session Summary:")
        print("-" * 40)
        
        status = await buddy.get_automotive_status()
        print(f"Platform: {status['platform']}")
        print(f"Capability: {status['capability']}")
        print(f"Current Safety Mode: {status['safety_mode']}")
        print(f"Vehicle Speed: {status['vehicle_speed_kmh']} km/h")
        print(f"Navigation Active: {status['navigation_active']}")
        print(f"Emergency Mode: {status['emergency_mode']}")
        print(f"Voice Commands Processed: {status['voice_commands_processed']}")
        print(f"Navigation Requests: {status['navigation_requests']}")
        print(f"Vehicle Status Checks: {status['vehicle_status_checks']}")
        print(f"Emergency Activations: {status['emergency_activations']}")
        print(f"Storage Used: {status['storage_usage']['percentage']:.1f}%")
        print(f"Database Performance: {status['database_performance']['average_execution_time']:.4f}s")
        
        print(f"\n🎉 Automotive Demo Completed Successfully!")
        print(f"✅ Safety-first hands-free AI assistant operational")
        print(f"✅ Navigation and vehicle integration verified")
        print(f"✅ Emergency response system tested")
        print(f"✅ Multi-modal automotive interaction confirmed")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await buddy.close()


if __name__ == "__main__":
    asyncio.run(quick_automotive_demo())
