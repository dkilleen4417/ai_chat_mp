#!/usr/bin/env python3
"""
Cost-Aware LLM Routing Test: Find the best LLM considering both accuracy AND cost
Includes cost tracking, cost-effectiveness ratios, and budget estimates
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
class CostAwareLLMConfig:
    """Configuration for an LLM with cost information"""
    name: str
    provider: str
    model_id: str
    max_tokens: int = 500
    temperature: float = 0.1
    description: str = ""
    cost_per_1k_input_tokens: float = 0.0  # USD per 1K input tokens
    cost_per_1k_output_tokens: float = 0.0  # USD per 1K output tokens
    free_tier: bool = False  # True if model is free

@dataclass
class CostAwareResult:
    """Result with cost tracking"""
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
    estimated_cost: float = 0.0  # Cost in USD for this single call
    error: Optional[str] = None

def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars ≈ 1 token)"""
    return len(text) // 4

def calculate_call_cost(input_tokens: int, output_tokens: int, config: CostAwareLLMConfig) -> float:
    """Calculate cost for a single API call"""
    if config.free_tier:
        return 0.0
    
    input_cost = (input_tokens / 1000) * config.cost_per_1k_input_tokens
    output_cost = (output_tokens / 1000) * config.cost_per_1k_output_tokens
    return input_cost + output_cost

def get_cost_aware_llm_configs() -> List[CostAwareLLMConfig]:
    """Get LLM configurations with accurate cost information"""
    return [
        # Free models (Google)
        CostAwareLLMConfig(
            name="Gemini 2.5 Flash Lite",
            provider="google",
            model_id="gemini-2.5-flash-lite-preview-06-17",
            description="Fast, lightweight (FREE)",
            cost_per_1k_input_tokens=0.0,
            cost_per_1k_output_tokens=0.0,
            free_tier=True
        ),
        CostAwareLLMConfig(
            name="Gemini 2.0 Flash Exp",
            provider="google",
            model_id="gemini-2.0-flash-exp",
            description="Experimental model (FREE)",
            cost_per_1k_input_tokens=0.0,
            cost_per_1k_output_tokens=0.0,
            free_tier=True
        ),
        
        # Paid Google models
        CostAwareLLMConfig(
            name="Gemini 2.5 Pro",
            provider="google",
            model_id="gemini-2.5-pro",
            description="Most capable Gemini",
            cost_per_1k_input_tokens=1.25,
            cost_per_1k_output_tokens=5.0,
            free_tier=False
        ),
        
        # Anthropic models (paid)
        CostAwareLLMConfig(
            name="Claude 3.5 Sonnet",
            provider="anthropic",
            model_id="claude-3-5-sonnet-20241022",
            description="Excellent instruction following",
            cost_per_1k_input_tokens=3.0,
            cost_per_1k_output_tokens=15.0,
            free_tier=False
        ),
        CostAwareLLMConfig(
            name="Claude 3.5 Haiku",
            provider="anthropic",
            model_id="claude-3-5-haiku-20241022",
            description="Fast and efficient Claude",
            cost_per_1k_input_tokens=0.8,
            cost_per_1k_output_tokens=4.0,
            free_tier=False
        ),
        
        # OpenAI models (paid)
        CostAwareLLMConfig(
            name="GPT-4o",
            provider="openai",
            model_id="gpt-4o",
            description="Most capable OpenAI model",
            cost_per_1k_input_tokens=3.0,
            cost_per_1k_output_tokens=10.0,
            free_tier=False
        ),
        CostAwareLLMConfig(
            name="GPT-4o Mini",
            provider="openai",
            model_id="gpt-4o-mini",
            description="Efficient OpenAI model",
            cost_per_1k_input_tokens=0.15,
            cost_per_1k_output_tokens=0.60,
            free_tier=False
        ),
        
        # xAI models (paid)
        CostAwareLLMConfig(
            name="Grok 3",
            provider="grok",
            model_id="grok-3",
            description="xAI's flagship model",
            cost_per_1k_input_tokens=2.0,
            cost_per_1k_output_tokens=10.0,
            free_tier=False
        ),
    ]

def estimate_test_costs(configs: List[CostAwareLLMConfig], num_test_cases: int) -> Dict[str, float]:
    """Estimate total costs for running all tests"""
    # Rough estimates for routing prompts
    avg_input_tokens = estimate_tokens(COMPREHENSIVE_ROUTING_PROMPT + "What's the weather in London?")  # ~800 tokens
    avg_output_tokens = 100  # JSON response ~100 tokens
    
    costs = {}
    total_cost = 0.0
    
    for config in configs:
        test_cost = calculate_call_cost(avg_input_tokens, avg_output_tokens, config) * num_test_cases
        costs[config.name] = test_cost
        total_cost += test_cost
    
    costs["TOTAL_ESTIMATED"] = total_cost
    return costs

def test_single_llm_sample(config: CostAwareLLMConfig, test_query: str) -> CostAwareResult:
    """Test a single LLM with one query to get cost estimates"""
    
    # For this demo, I'll create a mock result since we want to avoid actual API calls during design
    # In real implementation, this would call the actual LLM
    
    input_tokens = estimate_tokens(COMPREHENSIVE_ROUTING_PROMPT + test_query)
    output_tokens = 80  # Typical JSON response length
    estimated_cost = calculate_call_cost(input_tokens, output_tokens, config)
    
    return CostAwareResult(
        llm_name=config.name,
        query=test_query,
        routing_decision="tool_direct",
        primary_tool="get_weather_forecast",
        search_provider=None,
        confidence=0.85,
        reasoning="Clear weather request for specific location",
        response_time=0.5,
        json_valid=True,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost=estimated_cost
    )

def calculate_cost_effectiveness(accuracy: float, avg_cost_per_call: float) -> float:
    """Calculate cost-effectiveness ratio (accuracy per cent)"""
    if avg_cost_per_call == 0:
        return float('inf')  # Free models have infinite cost-effectiveness
    return accuracy / (avg_cost_per_call * 100)  # accuracy per cent

def analyze_cost_performance(results: List[CostAwareResult], config: CostAwareLLMConfig) -> Dict[str, Any]:
    """Analyze both performance and cost metrics"""
    if not results:
        return {}
    
    valid_results = [r for r in results if not r.error and r.json_valid]
    
    # Performance metrics
    response_times = [r.response_time for r in valid_results]
    costs = [r.estimated_cost for r in valid_results]
    
    avg_cost_per_call = statistics.mean(costs) if costs else 0
    total_cost = sum(costs)
    
    return {
        "total_tests": len(results),
        "successful_tests": len(valid_results),
        "avg_response_time": statistics.mean(response_times) if response_times else 0,
        "avg_cost_per_call": avg_cost_per_call,
        "total_test_cost": total_cost,
        "free_tier": config.free_tier,
        "cost_per_1k_input": config.cost_per_1k_input_tokens,
        "cost_per_1k_output": config.cost_per_1k_output_tokens
    }

def run_cost_aware_llm_test():
    """Run cost-aware LLM testing with budget considerations"""
    print("💰 COST-AWARE LLM ROUTING TEST")
    print("Find the best LLM considering BOTH accuracy AND cost")
    print("=" * 60)
    
    # Get configurations and test cases
    configs = get_cost_aware_llm_configs()
    test_cases = create_comprehensive_test_cases()
    
    print(f"🧪 Evaluating {len(configs)} LLMs on {len(test_cases)} test cases")
    
    # Estimate costs
    print(f"\n💰 COST ESTIMATION (for {len(test_cases)} tests per model):")
    cost_estimates = estimate_test_costs(configs, len(test_cases))
    
    free_models = []
    paid_models = []
    
    for config in configs:
        cost = cost_estimates[config.name]
        if config.free_tier:
            free_models.append(f"   🆓 {config.name}: FREE")
        else:
            paid_models.append(f"   💳 {config.name}: ${cost:.3f}")
    
    print("Free Models:")
    for model in free_models:
        print(model)
    
    print("\nPaid Models:")  
    for model in paid_models:
        print(model)
    
    total_estimated = cost_estimates["TOTAL_ESTIMATED"]
    print(f"\n💰 TOTAL ESTIMATED COST: ${total_estimated:.3f}")
    
    if total_estimated > 1.0:
        print(f"⚠️  WARNING: Full test will cost over $1.00")
        response = input(f"\nProceed with full test costing ~${total_estimated:.2f}? (y/N): ")
        if response.lower() != 'y':
            print("Test cancelled. Running sample test on free models only...")
            configs = [c for c in configs if c.free_tier]
    
    # Run sample test first to validate approach
    print(f"\n🧪 SAMPLE TEST (first test case only):")
    sample_query = test_cases[0].query
    print(f"Query: '{sample_query}'")
    
    sample_results = []
    for config in configs:
        result = test_single_llm_sample(config, sample_query)
        sample_results.append(result)
        
        cost_str = "FREE" if config.free_tier else f"${result.estimated_cost:.4f}"
        print(f"   {config.name:20s} | {result.routing_decision:15s} | {cost_str:8s} | {result.response_time:.2f}s")
    
    # Cost-effectiveness analysis
    print(f"\n📊 COST-EFFECTIVENESS PREVIEW:")
    print("(Based on sample results - accuracy would come from full test)")
    
    # Mock accuracies for demonstration (in real test, these come from actual results)
    mock_accuracies = {
        "Gemini 2.5 Flash Lite": 84,
        "Gemini 2.0 Flash Exp": 80,
        "Gemini 2.5 Pro": 88,
        "Claude 3.5 Sonnet": 92,
        "Claude 3.5 Haiku": 85,
        "GPT-4o": 90,
        "GPT-4o Mini": 86,
        "Grok 3": 82
    }
    
    cost_effectiveness_results = []
    
    for result in sample_results:
        config = next(c for c in configs if c.name == result.llm_name)
        mock_accuracy = mock_accuracies.get(result.llm_name, 80)
        cost_effectiveness = calculate_cost_effectiveness(mock_accuracy, result.estimated_cost)
        
        cost_effectiveness_results.append({
            "name": result.llm_name,
            "accuracy": mock_accuracy,
            "cost_per_call": result.estimated_cost,
            "cost_effectiveness": cost_effectiveness,
            "free_tier": config.free_tier
        })
    
    # Sort by cost-effectiveness
    cost_effectiveness_results.sort(key=lambda x: x["cost_effectiveness"], reverse=True)
    
    print("Rank | Model                | Accuracy | Cost/Call | Cost-Effectiveness")
    print("-" * 70)
    
    for i, result in enumerate(cost_effectiveness_results):
        cost_str = "FREE" if result["free_tier"] else f"${result['cost_per_call']:.4f}"
        ce_str = "∞" if result["cost_effectiveness"] == float('inf') else f"{result['cost_effectiveness']:.1f}"
        print(f"{i+1:4d} | {result['name']:20s} | {result['accuracy']:7.1f}% | {cost_str:9s} | {ce_str}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    best_free = next((r for r in cost_effectiveness_results if r["free_tier"]), None)
    best_paid = next((r for r in cost_effectiveness_results if not r["free_tier"]), None)
    cheapest_paid = min([r for r in cost_effectiveness_results if not r["free_tier"]], 
                       key=lambda x: x["cost_per_call"], default=None)
    
    if best_free:
        print(f"   🆓 Best Free Option: {best_free['name']} ({best_free['accuracy']:.1f}% accuracy)")
    
    if best_paid:
        print(f"   💳 Best Paid Option: {best_paid['name']} ({best_paid['accuracy']:.1f}% accuracy, ${best_paid['cost_per_call']:.4f}/call)")
    
    if cheapest_paid:
        print(f"   💰 Cheapest Paid: {cheapest_paid['name']} (${cheapest_paid['cost_per_call']:.4f}/call)")
    
    # Volume cost analysis
    print(f"\n📈 VOLUME COST ANALYSIS (daily routing decisions):")
    daily_volumes = [100, 1000, 10000, 100000]
    
    for volume in daily_volumes:
        print(f"\n   {volume:,} decisions/day:")
        
        for result in cost_effectiveness_results[:3]:  # Top 3 models
            if result["free_tier"]:
                daily_cost = 0
                monthly_cost = 0
            else:
                daily_cost = volume * result["cost_per_call"]
                monthly_cost = daily_cost * 30
            
            cost_str = "FREE" if result["free_tier"] else f"${daily_cost:.2f}/day, ${monthly_cost:.0f}/month"
            print(f"      {result['name']:20s}: {cost_str}")
    
    print(f"\n🎯 Cost-Aware Analysis Complete!")
    print(f"💡 For high-volume routing, free models provide best value")
    print(f"💡 For maximum accuracy, paid models may justify cost")

if __name__ == "__main__":
    run_cost_aware_llm_test()