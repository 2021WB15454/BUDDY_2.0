"""
Simple Phase 1 Advanced AI Component Test
Quick validation of core JARVIS-level capabilities
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_basic_components():
    """Test basic component loading and functionality"""
    
    print("🚀 BUDDY 2.0 Phase 1 Advanced AI - Quick Component Test")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Advanced Intent Classifier
    print("\n🎯 Testing Advanced Intent Classifier...")
    try:
        from buddy_core.nlp.advanced_intent_classifier import get_advanced_intent_classifier
        
        intent_classifier = await get_advanced_intent_classifier()
        
        # Test a simple classification
        test_result = await intent_classifier.classify_intent(
            user_input="Send an email to john@example.com about the meeting",
            conversation_context=[],
            user_id="test_user"
        )
        
        print(f"✅ Intent Classifier: WORKING")
        print(f"   Predicted Intent: {test_result['primary_intent']['intent']}")
        print(f"   Confidence: {test_result['primary_intent']['confidence']:.2f}")
        print(f"   Entities Found: {len(test_result['entities'])}")
        
        results['intent_classifier'] = 'success'
        
    except Exception as e:
        print(f"❌ Intent Classifier: FAILED - {e}")
        results['intent_classifier'] = f'failed: {e}'
    
    # Test 2: Semantic Memory Engine
    print("\n🧠 Testing Semantic Memory Engine...")
    try:
        from buddy_core.memory.semantic_memory import get_semantic_memory_engine
        
        semantic_memory = await get_semantic_memory_engine()
        
        # Test storing a conversation
        test_conversation = {
            'id': f'test_{datetime.utcnow().timestamp()}',
            'user_id': 'test_user',
            'session_id': 'test_session',
            'content': 'This is a test conversation about scheduling meetings',
            'intent': 'calendar_schedule',
            'timestamp': datetime.utcnow().isoformat(),
            'role': 'user'
        }
        
        conversation_id = await semantic_memory.store_conversation_context(test_conversation)
        
        print(f"✅ Semantic Memory: WORKING")
        print(f"   Storage: {'Success' if conversation_id else 'Failed'}")
        print(f"   Vector DB: {'Connected' if semantic_memory.vector_index else 'Local'}")
        
        results['semantic_memory'] = 'success'
        
    except Exception as e:
        print(f"❌ Semantic Memory: FAILED - {e}")
        results['semantic_memory'] = f'failed: {e}'
    
    # Test 3: Enhanced Backend Integration
    print("\n🔗 Testing Enhanced Backend Integration...")
    try:
        from enhanced_backend import generate_response
        
        test_response = await generate_response(
            user_message="Hello BUDDY, what can you help me with?",
            conversation_history=[],
            user_id="test_user"
        )
        
        print(f"✅ Enhanced Backend: WORKING")
        print(f"   Response Length: {len(test_response)} characters")
        print(f"   Phase 1 Features: {'Yes' if 'Phase 1' in test_response else 'No'}")
        print(f"   Sample Response: {test_response[:100]}...")
        
        results['enhanced_backend'] = 'success'
        
    except Exception as e:
        print(f"❌ Enhanced Backend: FAILED - {e}")
        results['enhanced_backend'] = f'failed: {e}'
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 QUICK TEST SUMMARY")
    print("=" * 60)
    
    successful_components = len([r for r in results.values() if r == 'success'])
    total_components = len(results)
    
    print(f"Components Tested: {total_components}")
    print(f"Working Components: {successful_components}")
    print(f"Success Rate: {successful_components/total_components:.1%}")
    
    if successful_components == total_components:
        print("\n🎉 ALL PHASE 1 COMPONENTS: OPERATIONAL!")
        print("✨ BUDDY 2.0 Advanced AI is ready for comprehensive testing!")
    else:
        print(f"\n⚠️  {total_components - successful_components} COMPONENTS NEED ATTENTION")
        print("💡 Some Phase 1 features may have initialization issues")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_basic_components())
