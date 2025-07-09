"""
LLM-Powered Intelligent Router - Uses LLM for routing decisions with rule-based fallback
Replaces pattern-matching with comprehensive LLM decision making
"""

import logging
import json
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import google.generativeai as genai
import streamlit as st

# Import existing classes for compatibility
from intelligent_router import RouteType, RoutingDecision

logger = logging.getLogger(__name__)

# Usage tracking for backup function monitoring
class RoutingUsageTracker:
    """Track usage of primary LLM vs backup rule-based routing"""
    
    def __init__(self):
        self.llm_success_count = 0
        self.backup_usage_count = 0
        self.total_requests = 0
        self.last_backup_time = None
        self.backup_reasons = []
        
    def log_llm_success(self, query: str, decision: RoutingDecision):
        """Log successful LLM routing decision"""
        self.llm_success_count += 1
        self.total_requests += 1
        logger.info(f"LLM_ROUTING_SUCCESS: Query='{query[:50]}...' Route={decision.route_type.value} Confidence={decision.confidence:.2f}")
        
    def log_backup_usage(self, query: str, reason: str, decision: RoutingDecision):
        """Log when backup rule-based routing is used"""
        self.backup_usage_count += 1
        self.total_requests += 1
        self.last_backup_time = datetime.now()
        self.backup_reasons.append(reason)
        
        logger.warning(f"BACKUP_ROUTING_USED: Query='{query[:50]}...' Reason='{reason}' Route={decision.route_type.value} Confidence={decision.confidence:.2f}")
        
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        if self.total_requests == 0:
            return {"llm_success_rate": 0, "backup_usage_rate": 0, "total_requests": 0}
            
        return {
            "llm_success_count": self.llm_success_count,
            "backup_usage_count": self.backup_usage_count,
            "total_requests": self.total_requests,
            "llm_success_rate": self.llm_success_count / self.total_requests,
            "backup_usage_rate": self.backup_usage_count / self.total_requests,
            "last_backup_time": self.last_backup_time.isoformat() if self.last_backup_time else None,
            "recent_backup_reasons": self.backup_reasons[-5:] if self.backup_reasons else []
        }
        
    def log_stats_summary(self):
        """Log summary statistics"""
        stats = self.get_usage_stats()
        logger.info(f"ROUTING_STATS: LLM_Success={stats['llm_success_count']} Backup_Used={stats['backup_usage_count']} Success_Rate={stats['llm_success_rate']:.2%} Backup_Rate={stats['backup_usage_rate']:.2%}")

# Global tracker instance
usage_tracker = RoutingUsageTracker()

# Comprehensive system prompt for routing decisions
COMPREHENSIVE_ROUTING_PROMPT = """You are an expert AI Query Router for a multi-modal AI assistant. Your job is to analyze user queries and determine the optimal routing strategy to provide the most accurate, helpful response.

**AVAILABLE TOOLS:**
1. **get_weather_forecast** - Get weather forecast for any worldwide location (1-5 days)
2. **get_home_weather** - Get weather from user's personal weather station at home
3. **get_pws_current_conditions** - Get current conditions from Personal Weather Station (PWS)
4. **brave_search** - General web search using Brave (privacy-focused, diverse results)
5. **serper_search** - Google-powered search via Serper (structured data, local results)

**ROUTING OPTIONS:**
- **tool_direct**: Use a specific tool immediately (high confidence)
- **tool_with_search**: Use tool but verify/supplement with search (medium confidence)
- **search_only**: Use search without tools (for current events, facts, etc.)
- **model_knowledge**: Use AI model's internal knowledge (no tools/search needed)
- **combined**: Use multiple approaches together

**DECISION CRITERIA:**

**Weather Queries → Tools:**
- "weather in [location]" → get_weather_forecast
- "forecast for [location]" → get_weather_forecast  
- "weather at home/my weather" → get_home_weather
- "PWS/weather station" → get_pws_current_conditions
- "temperature outside" → get_home_weather (if ambiguous location)

**Current Events/Facts → Search:**
- Recent news, events, stock prices → brave_search
- Business hours, addresses, phone numbers → serper_search
- "What happened..." → brave_search
- "Store hours for..." → serper_search

**General Knowledge → Model:**
- Historical facts, science concepts → model_knowledge
- Creative tasks (write, explain) → model_knowledge
- Math problems → model_knowledge
- Conversational queries → model_knowledge

**Edge Cases:**
- Fictional locations ("Middle Earth weather") → model_knowledge
- Historical questions ("history of weather") → model_knowledge
- Vague queries ("what's happening") → search_only with brave_search
- Personal but unclear ("check temperature") → get_home_weather

**CONFIDENCE LEVELS:**
- **High (0.9+)**: Clear, unambiguous queries with obvious tool match
- **Medium (0.7-0.8)**: Reasonable match but might need verification
- **Low (0.5-0.6)**: Uncertain, might need fallback options

**RESPONSE FORMAT:**
Respond with a JSON object containing:
- `"routing_decision"`: One of [tool_direct, tool_with_search, search_only, model_knowledge, combined]
- `"primary_tool"`: Tool name (or null if not using tools)
- `"search_provider"`: "brave" or "serper" (or null if not searching)
- `"confidence"`: Float between 0.0 and 1.0
- `"reasoning"`: Clear explanation of your decision
- `"fallback_options"`: Array of alternative approaches if primary fails

**YOUR TASK:** Analyze the user query and respond with the JSON object showing your routing decision."""


class LLMIntelligentRouter:
    """LLM-powered intelligent router with rule-based fallback"""
    
    def __init__(self):
        self.model = None
        self.fallback_router = None
        self.initialize_llm_router()
        self.initialize_fallback()
    
    def initialize_llm_router(self):
        """Initialize the LLM for routing decisions"""
        try:
            # Get API key
            api_key = st.secrets.get("GEMINI_API_KEY")
            if not api_key:
                import os
                api_key = os.getenv("GEMINI_API_KEY")
            
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(
                    "gemini-2.5-flash-lite-preview-06-17",  # Proven performer
                    generation_config={
                        "temperature": 0.1,  # Low for consistent routing
                        "max_output_tokens": 200,  # Small for JSON response
                        "response_mime_type": "application/json"
                    }
                )
                logger.info("LLM Router initialized with Gemini 2.5 Flash Lite")
            else:
                logger.warning("No Gemini API key found - using fallback only")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM router: {e}")
            self.model = None
    
    def initialize_fallback(self):
        """Initialize rule-based fallback router"""
        try:
            from intelligent_router import IntelligentRouter
            self.fallback_router = IntelligentRouter()
            logger.info("Rule-based fallback router initialized")
        except Exception as e:
            logger.error(f"Failed to initialize fallback router: {e}")
            self.fallback_router = None
    
    def make_llm_routing_decision(self, query: str) -> Optional[RoutingDecision]:
        """Make routing decision using LLM"""
        if not self.model:
            return None
        
        start_time = time.time()
        
        try:
            # Create prompt
            prompt = f"{COMPREHENSIVE_ROUTING_PROMPT}\n\nUser query: {query}"
            
            # Get LLM response
            response = self.model.generate_content(prompt)
            response_time = time.time() - start_time
            
            # Parse JSON response
            try:
                data = json.loads(response.text)
            except json.JSONDecodeError as e:
                logger.error(f"LLM routing JSON parse error: {e}")
                return None
            
            # Convert LLM response to RoutingDecision
            routing_decision = data.get("routing_decision", "model_knowledge")
            primary_tool = data.get("primary_tool")
            search_provider = data.get("search_provider")
            confidence = data.get("confidence", 0.5)
            reasoning = data.get("reasoning", "LLM routing decision")
            fallback_options = data.get("fallback_options", [])
            
            # Map routing decision to RouteType
            route_type_mapping = {
                "tool_direct": RouteType.TOOL_DIRECT,
                "tool_with_search": RouteType.TOOL_WITH_SEARCH,
                "search_only": RouteType.SEARCH_FIRST,
                "model_knowledge": RouteType.MODEL_KNOWLEDGE,
                "combined": RouteType.COMBINED
            }
            
            route_type = route_type_mapping.get(routing_decision, RouteType.MODEL_KNOWLEDGE)
            
            # Enhance reasoning with performance info
            enhanced_reasoning = f"LLM: {reasoning} (response_time: {response_time:.2f}s)"
            
            logger.debug(f"LLM routing decision: {routing_decision}, tool: {primary_tool}, confidence: {confidence}")
            
            return RoutingDecision(
                route_type=route_type,
                primary_tool=primary_tool,
                confidence=confidence,
                reasoning=enhanced_reasoning,
                fallback_options=fallback_options
            )
            
        except Exception as e:
            logger.error(f"LLM routing decision failed: {e}")
            return None
    
    def make_fallback_routing_decision(self, query: str) -> RoutingDecision:
        """Make routing decision using rule-based fallback"""
        if self.fallback_router:
            try:
                decision = self.fallback_router.make_routing_decision(query)
                # Enhance reasoning to indicate fallback was used
                decision.reasoning = f"FALLBACK: {decision.reasoning}"
                logger.debug(f"Using fallback routing for query: {query}")
                return decision
            except Exception as e:
                logger.error(f"Fallback routing failed: {e}")
        
        # Ultimate fallback - model knowledge
        logger.warning(f"All routing methods failed, using model knowledge for: {query}")
        return RoutingDecision(
            route_type=RouteType.MODEL_KNOWLEDGE,
            primary_tool=None,
            confidence=0.3,
            reasoning="EMERGENCY FALLBACK: All routing methods failed",
            fallback_options=[]
        )
    
    def make_routing_decision(self, query: str) -> RoutingDecision:
        """Make intelligent routing decision with LLM first, fallback second"""
        
        logger.debug(f"Making LLM routing decision for query: '{query}'")
        
        # Try LLM routing first
        llm_decision = self.make_llm_routing_decision(query)
        
        if llm_decision:
            logger.debug(f"LLM routing successful: {llm_decision.route_type.value}")
            # Track successful LLM usage
            usage_tracker.log_llm_success(query, llm_decision)
            return llm_decision
        else:
            logger.warning(f"LLM routing failed, using fallback")
            # Use fallback and track backup usage
            fallback_decision = self.make_fallback_routing_decision(query)
            usage_tracker.log_backup_usage(query, "LLM routing failed", fallback_decision)
            return fallback_decision
    
    def assess_tool_confidence(self, query: str, tool_name: str):
        """Legacy method for compatibility - redirects to fallback"""
        if self.fallback_router:
            return self.fallback_router.assess_tool_confidence(query, tool_name)
        else:
            # Mock response if no fallback available
            from intelligent_router import ToolConfidence
            return ToolConfidence(tool_name, 0.5, "No fallback available", True)
    
    def assess_all_tools(self, query: str):
        """Legacy method for compatibility - redirects to fallback"""
        if self.fallback_router:
            return self.fallback_router.assess_all_tools(query)
        else:
            return []
    
    def needs_external_search(self, query: str):
        """Legacy method for compatibility - redirects to fallback"""
        if self.fallback_router:
            return self.fallback_router.needs_external_search(query)
        else:
            return False, "No fallback available"


# Create global router instance - this replaces the old intelligent_router
llm_intelligent_router = LLMIntelligentRouter()

# For backward compatibility, also expose as intelligent_router
intelligent_router = llm_intelligent_router