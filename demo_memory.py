#!/usr/bin/env python3
"""
Pinecone Memory Demo for BUDDY AI Assistant

This script demonstrates how to use BUDDY's memory capabilities with Pinecone.
"""

import os
import asyncio
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "core"))

async def demo_memory_features():
    """Demonstrate BUDDY's memory features"""
    
    print("🧠 BUDDY AI Assistant - Memory Features Demo")
    print("=" * 45)
    
    # Set up API key (replace with your actual key)
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("❌ Please set PINECONE_API_KEY environment variable")
        return
    
    try:
        from buddy.database.pinecone_client import (
            PineconeClient, create_memory_document, create_knowledge_document
        )
        
        # Initialize Pinecone client
        print("🔧 Initializing memory system...")
        client = PineconeClient(api_key=api_key, index_name="buddy-demo")
        await client.initialize()
        print("✅ Memory system ready!")
        
        print("\n📝 Storing some memories...")
        
        # Store personal preferences
        memories = [
            await create_memory_document(
                text="User prefers coffee over tea and likes it black",
                conversation_id="conversation-1",
                user_id="demo-user",
                additional_metadata={"category": "preferences", "type": "beverage"}
            ),
            await create_memory_document(
                text="User is working on a Python AI project called BUDDY",
                conversation_id="conversation-2", 
                user_id="demo-user",
                additional_metadata={"category": "work", "type": "project"}
            ),
            await create_memory_document(
                text="User mentioned they have a meeting every Tuesday at 3 PM",
                conversation_id="conversation-3",
                user_id="demo-user", 
                additional_metadata={"category": "schedule", "type": "recurring"}
            )
        ]
        
        # Store knowledge
        knowledge = [
            await create_knowledge_document(
                text="Python is a high-level programming language known for its simplicity and readability. It's widely used in AI, web development, and data science.",
                title="Python Programming Language",
                category="technology",
                additional_metadata={"source": "knowledge_base", "confidence": 0.95}
            ),
            await create_knowledge_document(
                text="Pinecone is a vector database that enables fast similarity search and powers AI applications with long-term memory capabilities.",
                title="Pinecone Vector Database", 
                category="technology",
                additional_metadata={"source": "knowledge_base", "confidence": 0.98}
            )
        ]
        
        # Store all documents
        all_docs = memories + knowledge
        stored_count = await client.store_documents(all_docs)
        print(f"✅ Stored {stored_count} memories and knowledge items")
        
        # Wait for indexing
        print("⏳ Waiting for index to update...")
        await asyncio.sleep(5)
        
        print("\n🔍 Testing memory search...")
        
        # Test searches
        search_queries = [
            ("coffee preferences", "Looking for beverage preferences..."),
            ("Python project", "Searching for work-related memories..."),
            ("Tuesday meeting", "Finding schedule information..."),
            ("programming language", "Searching knowledge base..."),
            ("vector database", "Looking up technical knowledge...")
        ]
        
        for query, description in search_queries:
            print(f"\n{description}")
            print(f"Query: '{query}'")
            
            results = await client.search(query, top_k=2, min_score=0.3)
            
            if results:
                for i, result in enumerate(results, 1):
                    score = result.score
                    text = result.document.text
                    doc_type = result.document.metadata.get("type", "unknown")
                    category = result.document.metadata.get("category", "general")
                    
                    print(f"  {i}. [Score: {score:.3f}] [{category}/{doc_type}]")
                    print(f"     {text}")
            else:
                print("  No relevant memories found")
        
        # Get statistics
        print("\n📊 Memory Statistics:")
        stats = await client.get_index_stats()
        print(f"  Total memories: {stats.get('total_vector_count', 0)}")
        print(f"  Index dimension: {stats.get('dimension', 0)}")
        print(f"  Index fullness: {stats.get('index_fullness', 0):.1%}")
        
        print("\n🎯 Demo complete!")
        print("\nWhat this demonstrates:")
        print("✅ Personal memory storage (preferences, work, schedule)")
        print("✅ Knowledge base management (facts, information)")  
        print("✅ Semantic search across all memories")
        print("✅ Context-aware retrieval with relevance scoring")
        print("✅ Metadata filtering and categorization")
        
        print("\n🚀 Next steps:")
        print("1. Integrate with BUDDY's dialogue system")
        print("2. Add automatic memory storage during conversations")
        print("3. Use memory context to enhance responses")
        print("4. Implement user-specific memory isolation")
        
        # Cleanup (optional)
        cleanup = input("\n🧹 Clean up demo data? (y/n): ").lower().strip()
        if cleanup == 'y':
            await client.delete_documents(filter_dict={"user_id": "demo-user"})
            await client.delete_documents(filter_dict={"source": "knowledge_base"})
            print("✅ Demo data cleaned up")
        
        await client.close()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run the memory demo"""
    try:
        asyncio.run(demo_memory_features())
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")

if __name__ == "__main__":
    main()
