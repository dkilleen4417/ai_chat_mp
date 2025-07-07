#!/usr/bin/env python3
"""
Practical LLM Routing Test: Smart, cost-aware testing
Focuses on free models first, then tests paid models with small samples
"""

import time
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import google.generativeai as genai
import requests
import streamlit as st
from datetime import datetime
import statistics

# Import our test cases and prompts
from test_comprehensive_routing import create_comprehensive_test_cases, COMPREHENSIVE_ROUTING_PROMPT

@dataclass
class PracticalLLMConfig:
    """Practical LLM configuration with realistic cost estimates"""
    name: str
    provider: str
    model_id: str
    max_tokens: int = 200  # Smaller for routing decisions
    temperature: float = 0.1
    description: str = ""
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0
    free_tier: bool = False
    priority: str = "low"  # "high", "medium", "low" for testing priority

@dataclass
class PracticalResult:
    """Result with practical metrics"""
    llm_name: str
    query: str
    routing_decision: str
    primary_tool: Optional[str]
    search_provider: Optional[str]
    confidence: float
    reasoning: str
    response_time: float
    json_valid: bool
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    error: Optional[str] = None

def estimate_tokens_realistic(text: str) -> int:
    """More realistic token estimation"""
    return max(len(text) // 3, 10)  # More conservative estimate

def get_practical_llm_configs() -> List[PracticalLLMConfig]:
    """Get practical LLM configurations prioritized by testing strategy"""
    return [
        # HIGH PRIORITY - Free models (test all)
        PracticalLLMConfig(
            name="Gemini 2.5 Flash Lite",
            provider="google",
            model_id="gemini-2.5-flash-lite-preview-06-17",
            description="Current baseline (FREE)",
            free_tier=True,
            priority="high"
        ),
        PracticalLLMConfig(
            name="Gemini 2.0 Flash Exp",
            provider="google",
            model_id="gemini-2.0-flash-exp",
            description="Experimental model (FREE)",
            free_tier=True,
            priority="high"
        ),
        
        # MEDIUM PRIORITY - Budget models (small sample test)
        PracticalLLMConfig(
            name="GPT-4o Mini",
            provider="openai",
            model_id="gpt-4o-mini",
            description="Efficient OpenAI ($0.15/$0.60)",
            cost_per_1k_input_tokens=0.15,
            cost_per_1k_output_tokens=0.60,
            priority="medium"
        ),
        PracticalLLMConfig(
            name="Claude 3.5 Haiku",
            provider="anthropic",
            model_id="claude-3-5-haiku-20241022",
            description="Fast Claude ($0.8/$4.0)",
            cost_per_1k_input_tokens=0.8,
            cost_per_1k_output_tokens=4.0,
            priority="medium"
        ),
        
        # LOW PRIORITY - Premium models (tiny sample only)
        PracticalLLMConfig(
            name="GPT-4o",
            provider="openai", 
            model_id="gpt-4o",
            description="Premium OpenAI ($3.0/$10.0)",
            cost_per_1k_input_tokens=3.0,
            cost_per_1k_output_tokens=10.0,
            priority="low"
        ),
        PracticalLLMConfig(
            name="Claude 3.5 Sonnet",
            provider="anthropic",
            model_id="claude-3-5-sonnet-20241022", 
            description="Premium Claude ($3.0/$15.0)",
            cost_per_1k_input_tokens=3.0,
            cost_per_1k_output_tokens=15.0,
            priority="low"
        ),
    ]

def calculate_realistic_cost(input_tokens: int, output_tokens: int, config: PracticalLLMConfig) -> float:
    """Calculate realistic cost for a single API call"""
    if config.free_tier:
        return 0.0
    
    input_cost = (input_tokens / 1000) * config.cost_per_1k_input_tokens
    output_cost = (output_tokens / 1000) * config.cost_per_1k_output_tokens
    return input_cost + output_cost

def calculate_simple_accuracy(results: List[PracticalResult], test_cases) -> float:
    """Calculate accuracy for practical results"""
    if not results:
        return 0.0
    
    correct = 0
    valid_results = [r for r in results if r.json_valid and not r.error]
    
    for i, result in enumerate(valid_results):
        if i < len(test_cases):
            expected = test_cases[i]
            
            # Check routing decision
            decision_match = result.routing_decision == expected.expected_decision
            
            # Check tool (if expected)
            tool_match = True
            if expected.expected_tool:
                tool_match = result.primary_tool == expected.expected_tool
            
            # Check search provider (if expected) 
            search_match = True
            if expected.expected_search_provider:
                search_match = result.search_provider == expected.expected_search_provider
            
            if decision_match and tool_match and search_match:
                correct += 1
    
    return (correct / len(valid_results)) * 100 if valid_results else 0.0

def estimate_test_cost(config: PracticalLLMConfig, num_tests: int) -> float:
    """Estimate cost for testing a specific LLM"""
    if config.free_tier:
        return 0.0
    
    # Realistic estimates for routing JSON responses
    avg_input_tokens = estimate_tokens_realistic(COMPREHENSIVE_ROUTING_PROMPT + "What's the weather in London?")  # ~400 tokens
    avg_output_tokens = 50  # Small JSON response
    
    cost_per_call = calculate_realistic_cost(avg_input_tokens, avg_output_tokens, config)
    return cost_per_call * num_tests

class UniversalLLMTester:
    """Universal LLM tester with practical cost management"""
    
    def __init__(self):
        self.initialize_providers()
    
    def initialize_providers(self):
        """Initialize available providers"""
        try:
            # Google
            gemini_key = st.secrets.get("GEMINI_API_KEY")
            if gemini_key:
                genai.configure(api_key=gemini_key)
                print("✅ Google/Gemini initialized")
            
            # Check other providers
            if st.secrets.get("OPENAI_API_KEY"):
                print("✅ OpenAI key available")
            if st.secrets.get("ANTHROPIC_API_KEY"):
                print("✅ Anthropic key available")
                
        except Exception as e:
            print(f"⚠️ Provider initialization: {e}")
    
    def test_google_model(self, config: PracticalLLMConfig, query: str) -> PracticalResult:
        """Test Google/Gemini model"""
        start_time = time.time()
        
        try:
            model = genai.GenerativeModel(
                config.model_id,
                generation_config={
                    "temperature": config.temperature,
                    "max_output_tokens": config.max_tokens,
                    "response_mime_type": "application/json"
                }
            )
            
            prompt = f"{COMPREHENSIVE_ROUTING_PROMPT}\n\nUser query: {query}"
            response = model.generate_content(prompt)
            response_time = time.time() - start_time
            
            # Estimate tokens
            input_tokens = estimate_tokens_realistic(prompt)
            output_tokens = estimate_tokens_realistic(response.text)
            cost = calculate_realistic_cost(input_tokens, output_tokens, config)
            
            # Parse JSON
            try:
                data = json.loads(response.text)
                return PracticalResult(
                    llm_name=config.name,
                    query=query,
                    routing_decision=data.get("routing_decision", "unknown"),
                    primary_tool=data.get("primary_tool"),
                    search_provider=data.get("search_provider"),
                    confidence=data.get("confidence", 0.0),
                    reasoning=data.get("reasoning", ""),
                    response_time=response_time,
                    json_valid=True,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost=cost
                )
            except json.JSONDecodeError:
                return PracticalResult(
                    llm_name=config.name,
                    query=query,
                    routing_decision="error",
                    primary_tool=None,
                    search_provider=None,
                    confidence=0.0,
                    reasoning="JSON parse error",
                    response_time=response_time,
                    json_valid=False,
                    error="JSON parse error"
                )
                
        except Exception as e:
            return PracticalResult(
                llm_name=config.name,
                query=query,
                routing_decision="error",
                primary_tool=None,
                search_provider=None,
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                response_time=time.time() - start_time,
                json_valid=False,
                error=str(e)
            )
    
    def test_openai_model(self, config: PracticalLLMConfig, query: str) -> PracticalResult:
        """Test OpenAI model"""
        start_time = time.time()
        
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
            if not api_key:
                import os
                api_key = os.getenv("OPENAI_API_KEY")
            
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": config.model_id,
                "messages": [
                    {"role": "system", "content": COMPREHENSIVE_ROUTING_PROMPT},
                    {"role": "user", "content": f"User query: {query}"}
                ],
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Get actual token usage
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                cost = calculate_realistic_cost(input_tokens, output_tokens, config)
                
                try:
                    parsed = json.loads(content)
                    return PracticalResult(
                        llm_name=config.name,
                        query=query,
                        routing_decision=parsed.get("routing_decision", "unknown"),
                        primary_tool=parsed.get("primary_tool"),
                        search_provider=parsed.get("search_provider"),
                        confidence=parsed.get("confidence", 0.0),
                        reasoning=parsed.get("reasoning", ""),
                        response_time=response_time,
                        json_valid=True,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        estimated_cost=cost
                    )
                except json.JSONDecodeError:
                    return PracticalResult(
                        llm_name=config.name,
                        query=query,
                        routing_decision="error",
                        primary_tool=None,
                        search_provider=None,
                        confidence=0.0,
                        reasoning="JSON parse error",
                        response_time=response_time,
                        json_valid=False,
                        error="JSON parse error"
                    )
            else:
                error_msg = f"API error {response.status_code}"
                return PracticalResult(
                    llm_name=config.name,
                    query=query,
                    routing_decision="error",
                    primary_tool=None,
                    search_provider=None,
                    confidence=0.0,
                    reasoning=error_msg,
                    response_time=response_time,
                    json_valid=False,
                    error=error_msg
                )
                
        except Exception as e:
            return PracticalResult(
                llm_name=config.name,
                query=query,
                routing_decision="error",
                primary_tool=None,
                search_provider=None,
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                response_time=time.time() - start_time,
                json_valid=False,
                error=str(e)
            )
    
    def test_llm(self, config: PracticalLLMConfig, query: str) -> PracticalResult:
        """Test any LLM based on provider"""
        if config.provider == "google":
            return self.test_google_model(config, query)
        elif config.provider == "openai":
            return self.test_openai_model(config, query)
        else:
            return PracticalResult(
                llm_name=config.name,
                query=query,
                routing_decision="error",
                primary_tool=None,
                search_provider=None,
                confidence=0.0,
                reasoning=f"Provider {config.provider} not implemented in practical test",
                response_time=0.0,
                json_valid=False,
                error=f"Provider not implemented: {config.provider}"
            )

def run_practical_llm_test():
    """Run practical, cost-conscious LLM routing test"""
    print("💰 PRACTICAL LLM ROUTING TEST")
    print("Smart testing strategy: Free models first, then cost-effective sampling")
    print("=" * 70)
    
    # Initialize
    tester = UniversalLLMTester()
    configs = get_practical_llm_configs()
    test_cases = create_comprehensive_test_cases()
    
    # Separate configs by priority
    free_configs = [c for c in configs if c.priority == "high"]
    budget_configs = [c for c in configs if c.priority == "medium"] 
    premium_configs = [c for c in configs if c.priority == "low"]
    
    print(f"🧪 Test Strategy:")
    print(f"   🆓 Free models: {len(free_configs)} models × {len(test_cases)} tests = {len(free_configs) * len(test_cases)} calls")
    print(f"   💰 Budget models: {len(budget_configs)} models × 5 sample tests = {len(budget_configs) * 5} calls") 
    print(f"   🚀 Premium models: {len(premium_configs)} models × 3 sample tests = {len(premium_configs) * 3} calls")
    
    # Estimate costs
    total_cost = 0.0
    for config in budget_configs:
        total_cost += estimate_test_cost(config, 5)
    for config in premium_configs:
        total_cost += estimate_test_cost(config, 3)
    
    print(f"\n💰 Estimated total cost: ${total_cost:.3f}")
    
    if total_cost > 0.50:
        print(f"⚠️ Cost over $0.50 - proceeding with extra caution")
    
    all_results = {}
    
    # Phase 1: Test free models completely
    print(f"\n🆓 PHASE 1: FREE MODELS (Complete Test)")
    print("-" * 50)
    
    for config in free_configs:
        print(f"\n🧪 Testing {config.name}")
        results = []
        
        for i, test_case in enumerate(test_cases):
            print(f"   Test {i+1}/{len(test_cases)}: {test_case.query[:40]}...")
            result = tester.test_llm(config, test_case.query)
            results.append(result)
            
            if result.error:
                print(f"   ❌ {result.error}")
            else:
                print(f"   ✅ {result.routing_decision} | {result.response_time:.2f}s")
        
        # Calculate accuracy
        accuracy = calculate_simple_accuracy(results, test_cases)
        avg_time = statistics.mean([r.response_time for r in results if not r.error])
        
        all_results[config.name] = {
            "config": config,
            "results": results,
            "accuracy": accuracy,
            "avg_time": avg_time,
            "total_cost": 0.0,
            "test_count": len(results)
        }
        
        print(f"   📊 Accuracy: {accuracy:.1f}%, Avg Time: {avg_time:.2f}s, Cost: FREE")
    
    # Phase 2: Sample test budget models
    print(f"\n💰 PHASE 2: BUDGET MODELS (Sample Test - 5 queries)")
    print("-" * 50)
    
    sample_tests = test_cases[:5]  # First 5 test cases
    
    for config in budget_configs:
        print(f"\n🧪 Testing {config.name} (sample)")
        results = []
        
        for i, test_case in enumerate(sample_tests):
            print(f"   Test {i+1}/5: {test_case.query[:40]}...")
            result = tester.test_llm(config, test_case.query)
            results.append(result)
            
            if result.error:
                print(f"   ❌ {result.error}")
            else:
                print(f"   ✅ {result.routing_decision} | {result.response_time:.2f}s | ${result.estimated_cost:.4f}")
        
        # Calculate metrics
        accuracy = calculate_simple_accuracy(results, sample_tests)
        avg_time = statistics.mean([r.response_time for r in results if not r.error])
        total_cost = sum([r.estimated_cost for r in results])
        
        all_results[config.name] = {
            "config": config,
            "results": results,
            "accuracy": accuracy,
            "avg_time": avg_time,
            "total_cost": total_cost,
            "test_count": len(results)
        }
        
        print(f"   📊 Accuracy: {accuracy:.1f}%, Avg Time: {avg_time:.2f}s, Cost: ${total_cost:.4f}")
    
    # Phase 3: Tiny sample of premium models
    print(f"\n🚀 PHASE 3: PREMIUM MODELS (Tiny Sample - 3 queries)")
    print("-" * 50)
    
    tiny_tests = test_cases[:3]  # First 3 test cases
    
    for config in premium_configs:
        print(f"\n🧪 Testing {config.name} (tiny sample)")
        results = []
        
        for i, test_case in enumerate(tiny_tests):
            print(f"   Test {i+1}/3: {test_case.query[:40]}...")
            result = tester.test_llm(config, test_case.query)
            results.append(result)
            
            if result.error:
                print(f"   ❌ {result.error}")
            else:
                print(f"   ✅ {result.routing_decision} | {result.response_time:.2f}s | ${result.estimated_cost:.4f}")
        
        # Calculate metrics (extrapolated for comparison)
        sample_accuracy = calculate_simple_accuracy(results, tiny_tests)
        avg_time = statistics.mean([r.response_time for r in results if not r.error])
        total_cost = sum([r.estimated_cost for r in results])
        
        all_results[config.name] = {
            "config": config,
            "results": results,
            "accuracy": sample_accuracy,  # Note: small sample!
            "avg_time": avg_time,
            "total_cost": total_cost,
            "test_count": len(results)
        }
        
        print(f"   📊 Accuracy: {sample_accuracy:.1f}% (small sample!), Avg Time: {avg_time:.2f}s, Cost: ${total_cost:.4f}")
    
    # Analysis and recommendations
    print(f"\n📊 PRACTICAL ANALYSIS & RECOMMENDATIONS")
    print("=" * 70)
    
    # Best free model
    free_results = {k: v for k, v in all_results.items() if v["config"].free_tier}
    if free_results:
        best_free = max(free_results.items(), key=lambda x: x[1]["accuracy"])
        print(f"🏆 BEST FREE MODEL: {best_free[0]}")
        print(f"   📊 {best_free[1]['accuracy']:.1f}% accuracy, {best_free[1]['avg_time']:.2f}s avg time")
        print(f"   💰 Cost: FREE (unlimited usage)")
    
    # Cost-effectiveness comparison
    paid_results = {k: v for k, v in all_results.items() if not v["config"].free_tier}
    
    if paid_results:
        print(f"\n💡 COST-EFFECTIVENESS ANALYSIS:")
        print("Model                | Accuracy | Cost/Call | Tests | Sample Size")
        print("-" * 65)
        
        for name, data in paid_results.items():
            accuracy = data["accuracy"]
            avg_cost = data["total_cost"] / data["test_count"] if data["test_count"] > 0 else 0
            test_count = data["test_count"]
            
            sample_note = "(small!)" if test_count <= 5 else ""
            print(f"{name:20s} | {accuracy:7.1f}% | ${avg_cost:.4f}  | {test_count:5d} | {sample_note}")
    
    # Final recommendations
    print(f"\n🎯 PRACTICAL RECOMMENDATIONS:")
    
    if free_results:
        best_free_name, best_free_data = max(free_results.items(), key=lambda x: x[1]["accuracy"])
        print(f"   🆓 For production routing: {best_free_name} ({best_free_data['accuracy']:.1f}% accuracy, FREE)")
    
    if paid_results:
        # Find best budget option
        budget_results = {k: v for k, v in paid_results.items() if v["config"].priority == "medium"}
        if budget_results:
            best_budget = max(budget_results.items(), key=lambda x: x[1]["accuracy"])
            avg_cost = best_budget[1]["total_cost"] / best_budget[1]["test_count"]
            print(f"   💰 Best budget option: {best_budget[0]} ({best_budget[1]['accuracy']:.1f}% accuracy, ${avg_cost:.4f}/call)")
    
    print(f"\n💡 For high-volume routing (1000s of decisions/day): Use free models")
    print(f"💡 For maximum accuracy with budget: Consider sample-tested paid models")
    print(f"💡 Next step: Full test the most promising paid model if accuracy justifies cost")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"practical_llm_results_{timestamp}.json"
    
    # Prepare serializable results
    serializable_results = {}
    for name, data in all_results.items():
        serializable_results[name] = {
            "accuracy": data["accuracy"],
            "avg_time": data["avg_time"],
            "total_cost": data["total_cost"],
            "test_count": data["test_count"],
            "config": {
                "name": data["config"].name,
                "provider": data["config"].provider,
                "free_tier": data["config"].free_tier,
                "priority": data["config"].priority
            }
        }
    
    with open(results_file, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    print(f"🎯 Practical test complete! You now have cost-effective LLM insights.")

if __name__ == "__main__":
    run_practical_llm_test()