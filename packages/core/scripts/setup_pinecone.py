#!/usr/bin/env python3
"""
Pinecone Setup Script for BUDDY AI Assistant

This script helps you set up Pinecone integration with BUDDY.
It will create the necessary index and test the connection.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from buddy.database.pinecone_client import PineconeClient, create_memory_document, create_knowledge_document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def setup_pinecone():
    """Set up Pinecone for BUDDY AI Assistant"""
    
    print("🤖 BUDDY AI Assistant - Pinecone Setup")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("❌ Error: PINECONE_API_KEY environment variable not set")
        print("\nPlease:")
        print("1. Get your API key from https://app.pinecone.io/")
        print("2. Set the environment variable:")
        print("   export PINECONE_API_KEY='your-api-key-here'")
        print("3. Or add it to your .env file")
        return False
    
    try:
        # Initialize Pinecone client
        print("\n🔧 Initializing Pinecone client...")
        client = PineconeClient(
            api_key=api_key,
            index_name="buddy-memory"
        )
        
        await client.initialize()
        print("✅ Pinecone client initialized successfully")
        
        # Test basic operations
        print("\n🧪 Testing Pinecone operations...")
        
        # Create test documents
        test_memory = await create_memory_document(
            text="This is a test memory for BUDDY setup",
            conversation_id="setup-test",
            user_id="setup",
            additional_metadata={"test": True}
        )
        
        test_knowledge = await create_knowledge_document(
            text="Pinecone is a vector database service that enables semantic search and AI memory.",
            title="About Pinecone",
            category="technology",
            additional_metadata={"test": True}
        )
        
        # Store test documents
        print("  📝 Storing test memory...")
        memory_success = await client.store_document(test_memory)
        
        print("  📚 Storing test knowledge...")
        knowledge_success = await client.store_document(test_knowledge)
        
        if memory_success and knowledge_success:
            print("✅ Document storage test passed")
        else:
            print("❌ Document storage test failed")
            return False
        
        # Test search
        print("  🔍 Testing search functionality...")
        search_results = await client.search("test memory", top_k=2)
        
        if search_results:
            print(f"✅ Search test passed - found {len(search_results)} results")
            for i, result in enumerate(search_results, 1):
                print(f"    {i}. Score: {result.score:.3f} - {result.document.text[:50]}...")
        else:
            print("❌ Search test failed - no results found")
            return False
        
        # Get index statistics
        print("\n📊 Index Statistics:")
        stats = await client.get_index_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Clean up test documents
        print("\n🧹 Cleaning up test documents...")
        await client.delete_documents(filter_dict={"test": True})
        print("✅ Test cleanup completed")
        
        # Close client
        await client.close()
        
        print("\n🎉 Pinecone setup completed successfully!")
        print("\nNext steps:")
        print("1. The memory skill is now ready to use")
        print("2. Try asking BUDDY to 'remember something'")
        print("3. Test memory recall with 'what do you remember?'")
        print("4. Add knowledge with the memory skill")
        
        return True
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        print(f"\n❌ Setup failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your PINECONE_API_KEY is correct")
        print("2. Ensure you have sufficient Pinecone quota")
        print("3. Check network connectivity")
        print("4. Verify the specified region is available")
        return False

async def test_existing_setup():
    """Test an existing Pinecone setup"""
    print("🧪 Testing existing Pinecone setup...")
    
    try:
        client = PineconeClient()
        await client.initialize()
        
        # Get stats
        stats = await client.get_index_stats()
        print(f"✅ Connection successful")
        print(f"   Total vectors: {stats.get('total_vector_count', 0)}")
        print(f"   Dimension: {stats.get('dimension', 0)}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Pinecone for BUDDY AI Assistant")
    parser.add_argument("--test", action="store_true", help="Test existing setup")
    parser.add_argument("--api-key", help="Pinecone API key (or set PINECONE_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Set API key if provided
    if args.api_key:
        os.environ["PINECONE_API_KEY"] = args.api_key
    
    # Run setup or test
    if args.test:
        success = asyncio.run(test_existing_setup())
    else:
        success = asyncio.run(setup_pinecone())
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
