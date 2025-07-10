#!/usr/bin/env python3
"""
Test W3W tool routing integration
Verify that the LLM router can route W3W queries to the W3W tool
"""

import sys
sys.path.append('src')

from llm_intelligent_router import llm_intelligent_router
import time

def test_w3w_routing():
    """Test W3W tool routing"""
    
    print("🧪 Testing W3W Tool Routing Integration")
    print("=" * 50)
    
    w3w_test_queries = [
        "What's the What3Words address for Times Square, New York?",
        "Get me the W3W for 1600 Pennsylvania Avenue, Washington DC",
        "Convert my home address to What3Words",
        "What3Words for the White House?",
        "Get the three word address for Central Park",
    ]
    
    print(f"🔄 Testing {len(w3w_test_queries)} W3W queries...")
    
    for i, query in enumerate(w3w_test_queries):
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
            
            # Check if it correctly routed to W3W tool
            if decision.primary_tool == "get_what3words_address":
                print(f"   🎯 SUCCESS: Correctly routed to W3W tool!")
            else:
                print(f"   ⚠️  WARNING: Expected 'get_what3words_address', got '{decision.primary_tool}'")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n🎯 W3W Routing Test Complete!")
    print(f"💡 If successful, the W3W tool should now work in the main app")

if __name__ == "__main__":
    test_w3w_routing()