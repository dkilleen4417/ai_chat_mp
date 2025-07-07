#!/usr/bin/env python3
"""
Test app to analyze LLM vs Rule-based routing decision performance
Compares the intelligent router with LLM-based decision making
"""

import time
import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import google.generativeai as genai
import streamlit as st
from datetime import datetime

# Import our existing systems
from src.intelligent_router import intelligent_router, RouteType
from src.config import SEARCH_GROUNDING_SYSTEM_PROMPT, DECISION_MODEL

@dataclass
class RoutingTestCase:
    """Test case for routing decisions"""
    query: str
    expected_action: str  # "search", "tool", "model_knowledge"
    expected_tool: Optional[str] = None
    description: str = ""
    difficulty: str = "medium"  # easy, medium, hard


@dataclass
class RoutingResult:
    """Result from a routing decision"""
    system: str  # "llm" or "rule"
    query: str
    action: str
    tool: Optional[str]
    confidence: float
    reasoning: str
    response_time: float
    error: Optional[str] = None


class LLMRoutingTester:
    """Test LLM-based routing using the original system prompt"""
    
    def __init__(self):
        self.model = None
        self.initialize_model()
    
    def initialize_model(self):
        """Initialize the decision model"""
        try:
            # Use secrets if available, otherwise try environment
            api_key = st.secrets.get("GEMINI_API_KEY")
            if not api_key:
                import os
                api_key = os.getenv("GEMINI_API_KEY")
            
            if not api_key:
                raise ValueError("No Gemini API key found")
                
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                DECISION_MODEL,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 200,
                    "response_mime_type": "application/json"
                }
            )
            print(f"✅ LLM Model initialized: {DECISION_MODEL}")
        except Exception as e:
            print(f"❌ Failed to initialize LLM model: {e}")
            self.model = None
    
    def make_routing_decision(self, query: str) -> RoutingResult:
        """Make routing decision using LLM"""
        start_time = time.time()
        
        if not self.model:
            return RoutingResult(
                system="llm",
                query=query,
                action="error",
                tool=None,
                confidence=0.0,
                reasoning="Model not initialized",
                response_time=0.0,
                error="Model not initialized"
            )
        
        try:
            # Create the prompt
            messages = [{"role": "user", "parts": [f"{SEARCH_GROUNDING_SYSTEM_PROMPT}\n\nUser query: {query}"]}]
            
            # Get response
            response = self.model.generate_content(contents=messages)
            response_time = time.time() - start_time
            
            # Parse JSON response
            response_data = json.loads(response.text)
            
            # Convert to our format
            needs_search = response_data.get("needs_search", False)
            search_provider = response_data.get("search_provider", "serper")
            reasoning = response_data.get("reasoning", "No reasoning provided")
            
            if needs_search:
                action = "search"
                tool = search_provider
                confidence = 0.8  # High confidence for search decisions
            else:
                action = "model_knowledge"
                tool = None
                confidence = 0.7  # Medium confidence for model knowledge
            
            return RoutingResult(
                system="llm",
                query=query,
                action=action,
                tool=tool,
                confidence=confidence,
                reasoning=reasoning,
                response_time=response_time
            )
            
        except json.JSONDecodeError as e:
            return RoutingResult(
                system="llm",
                query=query,
                action="error",
                tool=None,
                confidence=0.0,
                reasoning=f"JSON parse error: {str(e)}",
                response_time=time.time() - start_time,
                error=f"JSON parse error: {str(e)}"
            )
        except Exception as e:
            return RoutingResult(
                system="llm",
                query=query,
                action="error",
                tool=None,
                confidence=0.0,
                reasoning=f"LLM error: {str(e)}",
                response_time=time.time() - start_time,
                error=str(e)
            )


class RuleBasedRoutingTester:
    """Test rule-based routing using the intelligent router"""
    
    def make_routing_decision(self, query: str) -> RoutingResult:
        """Make routing decision using rule-based system"""
        start_time = time.time()
        
        try:
            decision = intelligent_router.make_routing_decision(query)
            response_time = time.time() - start_time
            
            # Convert RouteType to our action format
            if decision.route_type == RouteType.SEARCH_FIRST:
                action = "search"
            elif decision.route_type in [RouteType.TOOL_DIRECT, RouteType.TOOL_WITH_SEARCH]:
                action = "tool"
            elif decision.route_type == RouteType.MODEL_KNOWLEDGE:
                action = "model_knowledge"
            else:
                action = "combined"
            
            return RoutingResult(
                system="rule",
                query=query,
                action=action,
                tool=decision.primary_tool,
                confidence=decision.confidence,
                reasoning=decision.reasoning,
                response_time=response_time
            )
            
        except Exception as e:
            return RoutingResult(
                system="rule",
                query=query,
                action="error",
                tool=None,
                confidence=0.0,
                reasoning=f"Rule system error: {str(e)}",
                response_time=time.time() - start_time,
                error=str(e)
            )


def create_test_cases() -> List[RoutingTestCase]:
    """Create comprehensive test cases"""
    return [
        # Weather queries (should use tools)
        RoutingTestCase("What's the weather in London?", "tool", "get_weather_forecast", "Basic weather query", "easy"),
        RoutingTestCase("Is it going to rain tomorrow in Paris?", "tool", "get_weather_forecast", "Future weather", "medium"),
        RoutingTestCase("How's the weather at home?", "tool", "get_home_weather", "Personal weather", "medium"),
        RoutingTestCase("What's my PWS showing?", "tool", "get_pws_current_conditions", "Personal weather station", "medium"),
        RoutingTestCase("Check the temperature outside", "tool", "get_home_weather", "Ambiguous location", "hard"),
        
        # Search queries (should use search)
        RoutingTestCase("What happened at the latest Apple event?", "search", "brave", "Recent events", "easy"),
        RoutingTestCase("What's Google's stock price today?", "search", "serper", "Current financial data", "easy"),
        RoutingTestCase("Store hours for Walmart near me", "search", "serper", "Local business info", "medium"),
        RoutingTestCase("Latest news about AI developments", "search", "brave", "Current news", "easy"),
        RoutingTestCase("What time does the Apple Store close?", "search", "serper", "Business hours", "medium"),
        
        # Model knowledge queries (should not need search or tools)
        RoutingTestCase("What is the capital of France?", "model_knowledge", None, "General knowledge", "easy"),
        RoutingTestCase("Explain photosynthesis", "model_knowledge", None, "Educational content", "easy"),
        RoutingTestCase("Write a haiku about cats", "model_knowledge", None, "Creative task", "easy"),
        RoutingTestCase("How do you calculate compound interest?", "model_knowledge", None, "Mathematical concept", "medium"),
        RoutingTestCase("What are the principles of good design?", "model_knowledge", None, "Conceptual question", "medium"),
        
        # Edge cases and tricky queries
        RoutingTestCase("Weather forecast for next week", "tool", "get_weather_forecast", "Future weather prediction", "hard"),
        RoutingTestCase("How hot is it on Mars?", "model_knowledge", None, "Space fact vs current weather", "hard"),
        RoutingTestCase("What's the weather like in Middle Earth?", "model_knowledge", None, "Fictional location", "hard"),
        RoutingTestCase("Search for the weather in Tokyo", "search", "serper", "Explicit search request", "medium"),
        RoutingTestCase("Tell me about the history of weather forecasting", "model_knowledge", None, "Historical vs current", "hard"),
        
        # Ambiguous queries
        RoutingTestCase("What's happening?", "search", "brave", "Very vague query", "hard"),
        RoutingTestCase("How are things?", "model_knowledge", None, "Conversational", "hard"),
        RoutingTestCase("Check the latest", "search", "brave", "Incomplete query", "hard"),
        RoutingTestCase("What do you think?", "model_knowledge", None, "Opinion request", "medium"),
        RoutingTestCase("Can you help me?", "model_knowledge", None, "Generic help", "easy"),
    ]


def analyze_results(results: List[RoutingResult], test_cases: List[RoutingTestCase]) -> Dict[str, Any]:
    """Analyze routing results and provide comprehensive metrics"""
    llm_results = [r for r in results if r.system == "llm"]
    rule_results = [r for r in results if r.system == "rule"]
    
    def calculate_accuracy(system_results: List[RoutingResult]) -> float:
        """Calculate accuracy against expected results"""
        correct = 0
        total = len(system_results)
        
        for i, result in enumerate(system_results):
            if i < len(test_cases):
                expected = test_cases[i].expected_action
                actual = result.action
                
                # Allow some flexibility in matching
                if expected == "tool" and actual in ["tool", "search"]:  # Tools might need search verification
                    correct += 1
                elif expected == actual:
                    correct += 1
        
        return (correct / total) * 100 if total > 0 else 0
    
    def calculate_avg_response_time(system_results: List[RoutingResult]) -> float:
        """Calculate average response time"""
        times = [r.response_time for r in system_results if r.error is None]
        return sum(times) / len(times) if times else 0
    
    def calculate_error_rate(system_results: List[RoutingResult]) -> float:
        """Calculate error rate"""
        errors = len([r for r in system_results if r.error is not None])
        return (errors / len(system_results)) * 100 if system_results else 0
    
    analysis = {
        "llm_system": {
            "accuracy": calculate_accuracy(llm_results),
            "avg_response_time": calculate_avg_response_time(llm_results),
            "error_rate": calculate_error_rate(llm_results),
            "total_tests": len(llm_results),
        },
        "rule_system": {
            "accuracy": calculate_accuracy(rule_results),
            "avg_response_time": calculate_avg_response_time(rule_results),
            "error_rate": calculate_error_rate(rule_results),
            "total_tests": len(rule_results),
        },
        "comparison": {
            "llm_faster": calculate_avg_response_time(llm_results) < calculate_avg_response_time(rule_results),
            "llm_more_accurate": calculate_accuracy(llm_results) > calculate_accuracy(rule_results),
            "llm_more_reliable": calculate_error_rate(llm_results) < calculate_error_rate(rule_results),
        }
    }
    
    return analysis


def run_routing_tests():
    """Run comprehensive routing tests"""
    print("🚀 Starting Routing Decision Performance Test")
    print("=" * 60)
    
    # Initialize testers
    llm_tester = LLMRoutingTester()
    rule_tester = RuleBasedRoutingTester()
    
    # Create test cases
    test_cases = create_test_cases()
    print(f"📋 Created {len(test_cases)} test cases")
    
    # Run tests
    results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🧪 Test {i+1}/{len(test_cases)}: {test_case.description}")
        print(f"   Query: '{test_case.query}'")
        print(f"   Expected: {test_case.expected_action} ({test_case.expected_tool or 'N/A'})")
        
        # Test LLM system
        print("   🤖 Testing LLM system...")
        llm_result = llm_tester.make_routing_decision(test_case.query)
        results.append(llm_result)
        
        if llm_result.error:
            print(f"      ❌ Error: {llm_result.error}")
        else:
            print(f"      ✅ Action: {llm_result.action}, Tool: {llm_result.tool}, Confidence: {llm_result.confidence:.2f}")
            print(f"      ⏱️  Time: {llm_result.response_time:.3f}s")
        
        # Test rule system
        print("   ⚙️  Testing Rule system...")
        rule_result = rule_tester.make_routing_decision(test_case.query)
        results.append(rule_result)
        
        if rule_result.error:
            print(f"      ❌ Error: {rule_result.error}")
        else:
            print(f"      ✅ Action: {rule_result.action}, Tool: {rule_result.tool}, Confidence: {rule_result.confidence:.2f}")
            print(f"      ⏱️  Time: {rule_result.response_time:.3f}s")
    
    # Analyze results
    print("\n📊 ANALYSIS RESULTS")
    print("=" * 60)
    
    analysis = analyze_results(results, test_cases)
    
    print(f"🤖 LLM System Performance:")
    print(f"   Accuracy: {analysis['llm_system']['accuracy']:.1f}%")
    print(f"   Avg Response Time: {analysis['llm_system']['avg_response_time']:.3f}s")
    print(f"   Error Rate: {analysis['llm_system']['error_rate']:.1f}%")
    
    print(f"\n⚙️  Rule System Performance:")
    print(f"   Accuracy: {analysis['rule_system']['accuracy']:.1f}%")
    print(f"   Avg Response Time: {analysis['rule_system']['avg_response_time']:.3f}s")
    print(f"   Error Rate: {analysis['rule_system']['error_rate']:.1f}%")
    
    print(f"\n🏆 Winner:")
    comp = analysis['comparison']
    print(f"   Faster: {'🤖 LLM' if comp['llm_faster'] else '⚙️ Rule'}")
    print(f"   More Accurate: {'🤖 LLM' if comp['llm_more_accurate'] else '⚙️ Rule'}")
    print(f"   More Reliable: {'🤖 LLM' if comp['llm_more_reliable'] else '⚙️ Rule'}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"routing_test_results_{timestamp}.json"
    
    detailed_results = {
        "timestamp": timestamp,
        "test_cases": [{"query": tc.query, "expected_action": tc.expected_action, "expected_tool": tc.expected_tool, "description": tc.description} for tc in test_cases],
        "results": [{"system": r.system, "query": r.query, "action": r.action, "tool": r.tool, "confidence": r.confidence, "reasoning": r.reasoning, "response_time": r.response_time, "error": r.error} for r in results],
        "analysis": analysis
    }
    
    with open(results_file, 'w') as f:
        json.dump(detailed_results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    print("\n🎯 Test Complete! Now you can see which system actually performs better.")


if __name__ == "__main__":
    run_routing_tests()