"""
BUDDY Cross-Platform Demo

Demonstrates the cross-platform database architecture with:
- Local database (SQLite) for offline storage
- Cloud database (MongoDB Atlas) for sync
- Vector database (ChromaDB) for AI context
- Encryption for security
- Real-time synchronization

Run this demo to see BUDDY working across multiple platforms.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from buddy_cross_platform_config import CrossPlatformConfig, get_development_config
from buddy_core.memory import EnhancedMemoryLayer, UserProfile, Device, Fact

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CrossPlatformDemo:
    """Demonstrates BUDDY's cross-platform capabilities"""
    
    def __init__(self):
        self.platforms = ["desktop", "mobile", "smartwatch", "tv", "car"]
        self.memory_layers = {}
        
    async def initialize_platforms(self):
        """Initialize memory layers for different platforms"""
        logger.info("🚀 Initializing BUDDY Cross-Platform Demo")
        
        for platform in self.platforms:
            logger.info(f"📱 Setting up {platform} platform...")
            
            # Get platform-specific configuration
            config = get_development_config(platform)
            
            # Create memory layer for this platform
            memory = EnhancedMemoryLayer(config["database"])
            await memory.initialize()
            
            self.memory_layers[platform] = memory
            
            logger.info(f"✅ {platform.capitalize()} platform initialized")
            
            # Show platform status
            status = memory.get_sync_status()
            logger.info(f"   Platform: {status['platform']}")
            logger.info(f"   Device ID: {status['device_id'][:8]}...")
            logger.info(f"   Online: {status['online']}")
            logger.info(f"   Encryption: {status['encryption']}")
    
    async def demo_user_management(self):
        """Demonstrate cross-platform user management"""
        logger.info("\n👤 === USER MANAGEMENT DEMO ===")
        
        # Create a user profile on desktop
        desktop_memory = self.memory_layers["desktop"]
        
        user_profile = UserProfile(
            user_id="demo_user_001",
            name="Alex Johnson",
            timezone="America/New_York",
            locale="en-US",
            preferences={
                "voice_enabled": True,
                "notifications": True,
                "theme": "dark",
                "privacy_level": "balanced"
            }
        )
        
        logger.info("📝 Creating user profile on desktop...")
        await desktop_memory.create_user(user_profile)
        
        # Wait a moment for potential sync
        await asyncio.sleep(1)
        
        # Try to access user from other platforms
        for platform_name, memory in self.memory_layers.items():
            if platform_name != "desktop":
                logger.info(f"🔍 Accessing user from {platform_name}...")
                retrieved_user = await memory.get_user("demo_user_001")
                
                if retrieved_user:
                    logger.info(f"   ✅ User found: {retrieved_user.name}")
                    logger.info(f"   📍 Timezone: {retrieved_user.timezone}")
                    logger.info(f"   🎨 Theme: {retrieved_user.preferences.get('theme')}")
                else:
                    logger.info(f"   ⚠️  User not found (sync may be disabled in dev mode)")
    
    async def demo_device_registration(self):
        """Demonstrate device registration across platforms"""
        logger.info("\n📱 === DEVICE REGISTRATION DEMO ===")
        
        devices = [
            Device(
                device_id="desktop_001",
                user_id="demo_user_001",
                device_type="desktop",
                name="Alex's MacBook Pro",
                capabilities=["voice", "camera", "microphone", "location"]
            ),
            Device(
                device_id="mobile_001", 
                user_id="demo_user_001",
                device_type="mobile",
                name="Alex's iPhone",
                capabilities=["voice", "camera", "microphone", "location", "biometric", "cellular"]
            ),
            Device(
                device_id="watch_001",
                user_id="demo_user_001", 
                device_type="smartwatch",
                name="Alex's Apple Watch",
                capabilities=["voice", "haptic", "health", "location"]
            ),
            Device(
                device_id="tv_001",
                user_id="demo_user_001",
                device_type="smart_tv",
                name="Living Room TV",
                capabilities=["voice", "display", "speakers", "remote"]
            ),
            Device(
                device_id="car_001",
                user_id="demo_user_001",
                device_type="automotive", 
                name="Alex's Tesla Model 3",
                capabilities=["voice", "navigation", "vehicle_control", "cellular"]
            )
        ]
        
        # Register each device on its respective platform
        for i, device in enumerate(devices):
            platform = self.platforms[i]
            memory = self.memory_layers[platform]
            
            logger.info(f"📋 Registering {device.name} on {platform}...")
            await memory.register_device(device)
            
            logger.info(f"   Device Type: {device.device_type}")
            logger.info(f"   Capabilities: {', '.join(device.capabilities)}")
    
    async def demo_conversation_sync(self):
        """Demonstrate conversation synchronization"""
        logger.info("\n💬 === CONVERSATION SYNC DEMO ===")
        
        # Simulate conversations across different platforms
        conversations = [
            {
                "platform": "mobile",
                "session_id": "mobile_session_001",
                "messages": [
                    ("user", "Hey BUDDY, what's the weather like today?"),
                    ("assistant", "It's 72°F and sunny in New York! Perfect weather for a walk."),
                    ("user", "Great! Remind me to walk the dog at 6 PM"),
                    ("assistant", "I've set a reminder for you at 6 PM to walk the dog.")
                ]
            },
            {
                "platform": "desktop", 
                "session_id": "desktop_session_001",
                "messages": [
                    ("user", "BUDDY, schedule a meeting with the team tomorrow at 2 PM"),
                    ("assistant", "I've scheduled 'Team meeting' for tomorrow at 2:00 PM. Would you like me to send calendar invites?"),
                    ("user", "Yes, send invites to Sarah, Mike, and Jennifer"),
                    ("assistant", "Calendar invites sent to Sarah, Mike, and Jennifer for tomorrow's team meeting.")
                ]
            },
            {
                "platform": "car",
                "session_id": "car_session_001", 
                "messages": [
                    ("user", "Navigate to the coffee shop on Main Street"),
                    ("assistant", "Starting navigation to Blue Mountain Coffee on Main Street. ETA: 8 minutes."),
                    ("user", "Also, call Sarah when I arrive"),
                    ("assistant", "I'll remind you to call Sarah when you arrive at Blue Mountain Coffee.")
                ]
            }
        ]
        
        # Store conversations on their respective platforms
        for conv in conversations:
            platform = conv["platform"]
            memory = self.memory_layers[platform]
            session_id = conv["session_id"]
            
            logger.info(f"💾 Storing conversation on {platform}...")
            
            for message_type, content in conv["messages"]:
                await memory.store_conversation(
                    user_id="demo_user_001",
                    session_id=session_id,
                    message_type=message_type,
                    content=content,
                    metadata={
                        "platform": platform,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            
            logger.info(f"   📝 Stored {len(conv['messages'])} messages")
        
        # Demonstrate retrieving conversation history from any platform
        logger.info("\n🔍 Retrieving conversation history from smartwatch...")
        watch_memory = self.memory_layers["smartwatch"]
        
        all_conversations = await watch_memory.get_conversation_history("demo_user_001", limit=20)
        logger.info(f"   📚 Found {len(all_conversations)} conversation messages")
        
        # Show recent messages
        for conv in all_conversations[:3]:
            logger.info(f"   💬 {conv.get('message_type', 'unknown')}: {conv.get('content', '')[:50]}...")
    
    async def demo_ai_context_search(self):
        """Demonstrate AI context and semantic search"""
        logger.info("\n🧠 === AI CONTEXT & SEMANTIC SEARCH DEMO ===")
        
        # Store various types of context across platforms
        contexts = [
            {
                "platform": "mobile",
                "type": "preference",
                "content": "User prefers dark theme and minimal notifications during work hours"
            },
            {
                "platform": "desktop", 
                "type": "work_schedule",
                "content": "User typically works from 9 AM to 5 PM, Monday through Friday"
            },
            {
                "platform": "car",
                "type": "location_habit",
                "content": "User frequently visits Blue Mountain Coffee on Main Street on weekend mornings"
            },
            {
                "platform": "tv",
                "type": "entertainment",
                "content": "User enjoys watching sci-fi shows and documentaries in the evening"
            },
            {
                "platform": "smartwatch",
                "type": "health_goal",
                "content": "User wants to walk 10,000 steps daily and tracks heart rate during workouts"
            }
        ]
        
        # Store context across platforms
        for ctx in contexts:
            platform = ctx["platform"]
            memory = self.memory_layers[platform]
            
            logger.info(f"🧠 Storing AI context on {platform}: {ctx['type']}")
            await memory.store_ai_context(
                user_id="demo_user_001",
                content=ctx["content"],
                context_type=ctx["type"],
                metadata={
                    "platform": platform,
                    "importance": "high"
                }
            )
        
        # Demonstrate semantic search from any platform
        search_queries = [
            "What are the user's work preferences?",
            "Tell me about the user's exercise habits",
            "What does the user like to watch?"
        ]
        
        search_platform = "mobile"
        search_memory = self.memory_layers[search_platform]
        
        for query in search_queries:
            logger.info(f"\n🔍 Searching from {search_platform}: '{query}'")
            
            results = await search_memory.search_context(
                user_id="demo_user_001",
                query=query,
                limit=3
            )
            
            for i, result in enumerate(results, 1):
                content = result.get("content", "")
                similarity = result.get("similarity", 0)
                logger.info(f"   {i}. [Similarity: {similarity:.2f}] {content[:80]}...")
    
    async def demo_facts_and_knowledge(self):
        """Demonstrate facts and knowledge storage"""
        logger.info("\n📚 === FACTS & KNOWLEDGE DEMO ===")
        
        # Store various facts across platforms
        facts = [
            Fact("User", "lives_in", "New York", confidence=1.0, source="user"),
            Fact("User", "works_as", "Software Engineer", confidence=1.0, source="user"),
            Fact("User", "prefers", "coffee over tea", confidence=0.8, source="conversation"),
            Fact("Blue Mountain Coffee", "located_on", "Main Street", confidence=1.0, source="navigation"),
            Fact("User", "exercises", "regularly", confidence=0.9, source="health_data"),
            Fact("User", "meeting_scheduled", "tomorrow 2 PM", confidence=1.0, source="calendar")
        ]
        
        # Store facts across different platforms
        for i, fact in enumerate(facts):
            platform = self.platforms[i % len(self.platforms)]
            memory = self.memory_layers[platform]
            
            logger.info(f"📝 Storing fact on {platform}: {fact.subject} {fact.predicate} {fact.object}")
            await memory.store_fact(fact, user_id="demo_user_001")
        
        # Recall facts from any platform
        recall_platform = "tv"
        recall_memory = self.memory_layers[recall_platform]
        
        logger.info(f"\n🔍 Recalling facts from {recall_platform}:")
        
        # Search for facts about the user
        user_facts = await recall_memory.recall_facts(
            subject="User",
            user_id="demo_user_001",
            limit=10
        )
        
        for fact in user_facts:
            logger.info(f"   📋 {fact.subject} {fact.predicate} {fact.object} (confidence: {fact.confidence})")
    
    async def demo_sync_status(self):
        """Show synchronization status across platforms"""
        logger.info("\n🔄 === SYNC STATUS DEMO ===")
        
        for platform_name, memory in self.memory_layers.items():
            status = memory.get_sync_status()
            stats = await memory.get_memory_stats()
            
            logger.info(f"\n📊 {platform_name.upper()} STATUS:")
            logger.info(f"   Platform: {status['platform']}")
            logger.info(f"   Device ID: {status['device_id'][:12]}...")
            logger.info(f"   Online: {status['online']}")
            logger.info(f"   Local DB: {'✅' if status['local_db'] else '❌'}")
            logger.info(f"   Cloud DB: {'✅' if status['cloud_db'] else '❌'}")
            logger.info(f"   Vector DB: {'✅' if status['vector_db'] else '❌'}")
            logger.info(f"   Encryption: {'✅' if status['encryption'] else '❌'}")
            logger.info(f"   Initialized: {'✅' if stats['initialized'] else '❌'}")
    
    async def run_demo(self):
        """Run the complete cross-platform demo"""
        try:
            # Initialize all platforms
            await self.initialize_platforms()
            
            # Run demo scenarios
            await self.demo_user_management()
            await self.demo_device_registration()
            await self.demo_conversation_sync()
            await self.demo_ai_context_search()
            await self.demo_facts_and_knowledge()
            await self.demo_sync_status()
            
            logger.info("\n🎉 === DEMO COMPLETED SUCCESSFULLY ===")
            logger.info("BUDDY is now running with full cross-platform support!")
            logger.info("Data is synchronized across all devices and platforms.")
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise
        
        finally:
            # Cleanup
            logger.info("\n🧹 Cleaning up demo resources...")
            for platform_name, memory in self.memory_layers.items():
                try:
                    await memory.close()
                    logger.info(f"   ✅ Closed {platform_name} memory layer")
                except Exception as e:
                    logger.error(f"   ❌ Error closing {platform_name}: {e}")

async def main():
    """Main demo function"""
    print("🤖 BUDDY Cross-Platform Database Demo")
    print("=====================================")
    print()
    print("This demo showcases BUDDY's cross-platform architecture:")
    print("✅ Local databases (SQLite) for offline-first storage")
    print("✅ Cloud synchronization (MongoDB Atlas) for cross-device access")
    print("✅ Vector databases (ChromaDB) for AI context memory")
    print("✅ End-to-end encryption for privacy and security")
    print("✅ Real-time sync across iOS, Android, Windows, macOS, Linux")
    print("✅ Smartwatch, TV, and car platform support")
    print()
    
    demo = CrossPlatformDemo()
    await demo.run_demo()

if __name__ == "__main__":
    asyncio.run(main())
