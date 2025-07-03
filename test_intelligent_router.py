#!/usr/bin/env python3
"""
Test the intelligent router with various query types
"""

import sys
sys.path.append('./src')

from intelligent_router import intelligent_router, RouteType

def test_routing_decisions():
    """Test various query types with the intelligent router"""
    
    test_queries = [
        # Weather queries (should use weather tools)
        "What's the weather in London?",
        "Weather forecast for Tokyo, Japan",
        "How hot is it in Phoenix today?",
        
        # Personal weather station queries (should use PWS tools)
        "What's the temperature at my weather station?",
        "Check my home weather",
        "PWS current conditions",
        "Weather at my house",
        
        # Current events (should search first)
        "Latest news about AI",
        "Current stock price of Apple",
        "What happened today in politics?",
        
        # Local business queries (should search)
        "Store hours for Target near me",
        "Phone number for pizza place",
        
        # General knowledge (should use model knowledge)
        "What is the capital of France?",
        "How do you solve a quadratic equation?",
        "What is photosynthesis?",
        
        # Complex queries (might need combination)
        "Weather in Boise, Idaho and latest news about Idaho",
        "My home weather station temperature vs forecast for tomorrow"
    ]
    
    print("=== Intelligent Router Test ===\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}: \"{query}\"")
        
        # Get routing decision
        decision = intelligent_router.make_routing_decision(query)
        
        print(f"  Route: {decision.route_type.value}")
        print(f"  Primary Tool: {decision.primary_tool or 'None'}")
        print(f"  Confidence: {decision.confidence:.2f}")
        print(f"  Reasoning: {decision.reasoning}")
        if decision.fallback_options:
            print(f"  Fallbacks: {', '.join(decision.fallback_options)}")
        
        # Also show tool assessments
        assessments = intelligent_router.assess_all_tools(query)
        top_3 = assessments[:3]
        if top_3:
            print(f"  Top Tools: {', '.join([f'{a.tool_name}({a.confidence:.2f})' for a in top_3 if a.confidence > 0])}")
        
        print()

def test_specific_scenarios():
    """Test specific scenarios we care about"""
    
    print("=== Specific Scenario Tests ===\n")
    
    scenarios = [
        ("Boise weather", "What's the weather in Boise, Idaho?", RouteType.TOOL_DIRECT, "get_weather_forecast"),
        ("Home PWS", "What's the current temperature on my personal weather station?", RouteType.TOOL_DIRECT, "get_pws_current_conditions"),
        ("General weather", "Weather forecast for London, UK", RouteType.TOOL_DIRECT, "get_weather_forecast"),
        ("Current events", "Latest iPhone news", RouteType.SEARCH_FIRST, None),
        ("General knowledge", "What is 2+2?", RouteType.MODEL_KNOWLEDGE, None)
    ]
    
    for name, query, expected_route, expected_tool in scenarios:
        print(f"Scenario: {name}")
        print(f"  Query: \"{query}\"")
        
        decision = intelligent_router.make_routing_decision(query)
        
        print(f"  Expected: {expected_route.value} / {expected_tool or 'None'}")
        print(f"  Actual: {decision.route_type.value} / {decision.primary_tool or 'None'}")
        
        if decision.route_type == expected_route and decision.primary_tool == expected_tool:
            print("  ✅ PASS")
        else:
            print("  ❌ FAIL")
        
        print(f"  Reasoning: {decision.reasoning}")
        print()

if __name__ == "__main__":
    test_routing_decisions()
    test_specific_scenarios()