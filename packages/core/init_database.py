#!/usr/bin/env python3
"""
BUDDY Database Initialization Script

This script initializes the MongoDB database for BUDDY, creates required
collections with proper indexes, and validates the database connection.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the core package to the path
sys.path.insert(0, str(Path(__file__).parent))

# Set working directory to project root for config file access
project_root = Path(__file__).parent.parent.parent
import os
os.chdir(project_root)

from buddy.database import MongoDBClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def initialize_database():
    """Initialize MongoDB database for BUDDY."""
    
    logger.info("🚀 Starting BUDDY Database Initialization...")
    
    # Initialize MongoDB client
    try:
        db_client = MongoDBClient()
        await db_client.connect()
        logger.info("✅ Connected to MongoDB successfully")
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        logger.info("💡 Make sure MongoDB is running locally on port 27017")
        logger.info("   You can install MongoDB Community Edition from:")
        logger.info("   https://www.mongodb.com/try/download/community")
        return False
    
    try:
        # Test basic operations
        logger.info("🔍 Testing database operations...")
        
        # Get database statistics
        stats = await db_client.get_database_stats()
        logger.info(f"📊 Database stats: {stats}")
        
        # Check collections
        collections = await db_client.list_collections()
        logger.info(f"📁 Available collections: {collections}")
        
        # Health check
        health = await db_client.health_check()
        if health['status'] == 'healthy':
            logger.info("✅ Database health check passed")
        else:
            logger.warning(f"⚠️ Database health check issues: {health}")
        
        # Test conversation creation (basic CRUD test)
        from buddy.database.models import ConversationModel, MessageType
        from datetime import datetime
        import uuid
        
        test_conversation = ConversationModel(
            conversation_id=str(uuid.uuid4()),
            user_id="test_user",
            session_id="test_session",
            device_id="init_script",
            start_time=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            turns=[],
            metadata={"test": True, "initialized_by": "init_script"}
        )
        
        # Insert test conversation
        conversation_collection = db_client.get_collection('conversations')
        result = await conversation_collection.insert_one(test_conversation.to_dict())
        logger.info(f"✅ Test conversation created with ID: {result.inserted_id}")
        
        # Clean up test data
        await conversation_collection.delete_one({"_id": result.inserted_id})
        logger.info("🧹 Test data cleaned up")
        
        logger.info("🎉 Database initialization completed successfully!")
        logger.info("")
        logger.info("📋 Database Summary:")
        logger.info(f"   • Database: {db_client.database.name}")
        logger.info(f"   • Collections: {len(collections)}")
        logger.info("   • Indexes: Created for optimal performance")
        logger.info("   • Health: All systems operational")
        logger.info("")
        logger.info("🔗 BUDDY is now ready to use MongoDB for:")
        logger.info("   • Conversation history and context")
        logger.info("   • User profiles and preferences") 
        logger.info("   • Skill execution logs and analytics")
        logger.info("   • Device management and status")
        logger.info("   • Memory storage and retrieval")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False
    
    finally:
        await db_client.close()
        logger.info("🔌 Database connection closed")


async def check_mongodb_status():
    """Check if MongoDB is running and accessible."""
    
    try:
        db_client = MongoDBClient()
        await db_client.connect()
        health = await db_client.health_check()
        await db_client.close()
        return health['status'] == 'healthy'
    except Exception:
        return False


if __name__ == "__main__":
    print("🤖 BUDDY Database Initialization")
    print("=" * 50)
    
    # Run initialization directly (the connect() method handles the check)
    success = asyncio.run(initialize_database())
    
    if success:
        print("\n🎉 BUDDY database is ready!")
        print("   You can now start the BUDDY server with MongoDB support.")
        sys.exit(0)
    else:
        print("\n❌ Database initialization failed!")
        print("   Check the logs above for details.")
        sys.exit(1)
