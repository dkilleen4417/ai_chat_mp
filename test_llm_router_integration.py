#!/usr/bin/env python3
"""
Test LLM Router Integration
Verify the new LLM-based routing system works correctly
"""

import sys
sys.path.append('src')

from llm_intelligent_router import llm_intelligent_router
import time

def test_llm_router():
    """Test the new LLM router with various queries"""
    
    print("🧪 Testing LLM Intelligent Router Integration")
    print("=" * 50)
    
    test_queries = [
        "What's the weather in London?",
        "How's the weather at home?", 
        "What's my PWS showing?",
        "What happened at the latest Apple event?",
        "What is the capital of France?",
        "What's the weather like in Middle Earth?",
    ]
    
    print(f"🔄 Testing {len(test_queries)} queries...")
    
    for i, query in enumerate(test_queries):
        print(f"\n🧪 Test {i+1}: '{query}'")
        
        try:
            start_time = time.time()
            decision = llm_intelligent_router.make_routing_decision(query)
            response_time = time.time() - start_time
            
            print(f"   ✅ Route: {decision.route_type.value}")
            print(f"   🔧 Tool: {decision.primary_tool}")
            print(f"   📊 Confidence: {decision.confidence:.2f}")
            print(f"   ⏱️  Time: {response_time:.2f}s")
            print(f"   💭 Reasoning: {decision.reasoning[:80]}...")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n🎯 LLM Router Integration Test Complete!")

if __name__ == "__main__":
    test_llm_router()