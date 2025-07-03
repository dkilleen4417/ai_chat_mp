"""
Intelligent Router - Confidence-based query routing system
Routes queries to tools, search, or model knowledge based on confidence scores
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class RouteType(Enum):
    """Types of routing decisions"""
    TOOL_DIRECT = "tool_direct"           # High confidence tool usage
    TOOL_WITH_SEARCH = "tool_with_search" # Medium confidence, verify with search
    SEARCH_FIRST = "search_first"         # Search then tools if needed
    MODEL_KNOWLEDGE = "model_knowledge"   # Use pure model knowledge
    COMBINED = "combined"                 # Use multiple sources


@dataclass
class ToolConfidence:
    """Tool confidence assessment"""
    tool_name: str
    confidence: float  # 0.0 to 1.0
    reason: str
    can_handle: bool


@dataclass
class RoutingDecision:
    """Final routing decision with confidence breakdown"""
    route_type: RouteType
    primary_tool: Optional[str]
    confidence: float
    reasoning: str
    fallback_options: List[str]


class IntelligentRouter:
    """Confidence-based query routing system"""
    
    def __init__(self):
        self.tool_patterns = self._initialize_tool_patterns()
        self.confidence_thresholds = {
            'high': 0.8,      # Direct tool usage
            'medium': 0.4,    # Tool + verification
            'low': 0.2        # Search first
        }
    
    def _initialize_tool_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize tool matching patterns and confidence rules"""
        return {
            'get_weather_forecast': {
                'patterns': [
                    r'\bweather\b.*\bin\b',           # "weather in London"
                    r'\bforecast\b.*\bfor\b',         # "forecast for Tokyo"
                    r'\btemperature\b.*\bin\b',       # "temperature in Paris"
                    r'\b(rain|snow|sun)\b.*\bin\b',   # "rain in Seattle"
                    r'\bhow.*hot.*in\b',              # "how hot in Phoenix"
                    r'\bclimate\b.*\bin\b'            # "climate in Miami"
                ],
                'keywords': ['weather', 'forecast', 'temperature', 'rain', 'snow', 'climate'],
                'location_indicators': ['in', 'at', 'for'],
                'confidence_boost': 0.3  # Boost if location detected
            },
            'get_pws_current_conditions': {
                'patterns': [
                    r'\b(home|my|personal)\b.*\b(weather|temperature|station)\b',
                    r'\bPWS\b',
                    r'\bweather station\b.*\b(my|home|personal)\b',
                    r'\bcurrent.*\b(home|my)\b.*\b(weather|temp)\b',
                    r'\bPWS\b.*\b(current|conditions|temperature|weather)\b'
                ],
                'keywords': ['home', 'my', 'personal', 'PWS', 'station', 'conditions'],
                'confidence_boost': 0.5  # High boost for personal queries
            },
            'get_home_weather': {
                'patterns': [
                    r'\b(home|my|personal)\b.*\bweather\b',
                    r'\bweather.*\b(home|house)\b',
                    r'\b(my|our)\b.*\b(station|tempest)\b'
                ],
                'keywords': ['home', 'my', 'personal', 'house', 'tempest'],
                'confidence_boost': 0.4
            },
            'brave_search': {
                'patterns': [
                    r'\b(latest|recent|current|new)\b.*\b(news|events)\b',
                    r'\bwhat.*happened\b',
                    r'\bstock price\b',
                    r'\bcompany.*\b(revenue|earnings)\b'
                ],
                'keywords': ['latest', 'recent', 'current', 'news', 'stock', 'company'],
                'confidence_boost': 0.2
            },
            'serper_search': {
                'patterns': [
                    r'\bwhere.*\bopen\b',
                    r'\bstore hours\b',
                    r'\bphone number\b',
                    r'\baddress.*\bof\b'
                ],
                'keywords': ['hours', 'address', 'phone', 'location', 'store'],
                'confidence_boost': 0.2
            }
        }
    
    def assess_tool_confidence(self, query: str, tool_name: str) -> ToolConfidence:
        """Assess how confident a specific tool is for handling a query"""
        
        if tool_name not in self.tool_patterns:
            return ToolConfidence(tool_name, 0.0, "Tool not recognized", False)
        
        tool_config = self.tool_patterns[tool_name]
        confidence = 0.0
        reasons = []
        
        query_lower = query.lower()
        
        # Pattern matching
        pattern_matches = 0
        for pattern in tool_config['patterns']:
            if re.search(pattern, query_lower):
                pattern_matches += 1
                confidence += 0.3
                reasons.append(f"Pattern match: {pattern}")
        
        # Keyword scoring
        keyword_matches = 0
        for keyword in tool_config['keywords']:
            if keyword in query_lower:
                keyword_matches += 1
                confidence += 0.2
                reasons.append(f"Keyword: {keyword}")
        
        # Special boosts
        if 'location_indicators' in tool_config:
            for indicator in tool_config['location_indicators']:
                if f" {indicator} " in query_lower:
                    confidence += tool_config.get('confidence_boost', 0.1)
                    reasons.append(f"Location indicator: {indicator}")
                    break
        
        if 'confidence_boost' in tool_config and (pattern_matches > 0 or keyword_matches > 0):
            confidence += tool_config['confidence_boost']
        
        # Cap confidence at 1.0
        confidence = min(confidence, 1.0)
        
        # Determine if tool can handle the query
        can_handle = confidence >= self.confidence_thresholds['low']
        
        reason = f"Patterns: {pattern_matches}, Keywords: {keyword_matches}. {'; '.join(reasons[:3])}"
        
        return ToolConfidence(tool_name, confidence, reason, can_handle)
    
    def assess_all_tools(self, query: str) -> List[ToolConfidence]:
        """Assess confidence for all available tools"""
        tool_assessments = []
        
        for tool_name in self.tool_patterns.keys():
            assessment = self.assess_tool_confidence(query, tool_name)
            tool_assessments.append(assessment)
        
        # Sort by confidence (highest first)
        tool_assessments.sort(key=lambda x: x.confidence, reverse=True)
        
        return tool_assessments
    
    def needs_external_search(self, query: str) -> Tuple[bool, str]:
        """Determine if query requires external/current information"""
        
        # Indicators that suggest current/external information needed
        current_indicators = [
            r'\b(latest|recent|current|today|now|this week|this month)\b',
            r'\b(stock price|market|news|events)\b',
            r'\b(what.*happened|breaking|update)\b',
            r'\b(store hours|phone number|address)\b',
            r'\b(open|closed|available)\b.*\b(now|today)\b'
        ]
        
        query_lower = query.lower()
        
        for pattern in current_indicators:
            if re.search(pattern, query_lower):
                return True, f"Detected current information need: {pattern}"
        
        # Check for future/upcoming events
        future_indicators = [
            r'\b(when.*will|upcoming|scheduled|next)\b',
            r'\b(forecast|prediction|estimate)\b.*\b(next|future)\b'
        ]
        
        for pattern in future_indicators:
            if re.search(pattern, query_lower):
                return True, f"Detected future information need: {pattern}"
        
        return False, "No external information indicators found"
    
    def make_routing_decision(self, query: str) -> RoutingDecision:
        """Make intelligent routing decision based on confidence assessment"""
        
        logger.debug(f"Making routing decision for query: '{query}'")
        
        # Assess all tools
        tool_assessments = self.assess_all_tools(query)
        best_tool = tool_assessments[0] if tool_assessments else None
        
        # Check if external search is needed
        needs_search, search_reason = self.needs_external_search(query)
        
        logger.debug(f"Best tool: {best_tool.tool_name if best_tool else 'None'} "
                    f"(confidence: {best_tool.confidence if best_tool else 0:.2f})")
        logger.debug(f"Needs search: {needs_search} - {search_reason}")
        
        # Decision logic
        if best_tool and best_tool.confidence >= self.confidence_thresholds['high']:
            # High confidence - use tool directly
            return RoutingDecision(
                route_type=RouteType.TOOL_DIRECT,
                primary_tool=best_tool.tool_name,
                confidence=best_tool.confidence,
                reasoning=f"High tool confidence ({best_tool.confidence:.2f}): {best_tool.reason}",
                fallback_options=['search'] if needs_search else []
            )
        
        elif best_tool and best_tool.confidence >= self.confidence_thresholds['medium']:
            if needs_search:
                # Medium confidence + search needed - verify with search
                return RoutingDecision(
                    route_type=RouteType.TOOL_WITH_SEARCH,
                    primary_tool=best_tool.tool_name,
                    confidence=best_tool.confidence,
                    reasoning=f"Medium tool confidence + search needed: {best_tool.reason}",
                    fallback_options=['search_verification']
                )
            else:
                # Medium confidence, no search needed - use tool
                return RoutingDecision(
                    route_type=RouteType.TOOL_DIRECT,
                    primary_tool=best_tool.tool_name,
                    confidence=best_tool.confidence,
                    reasoning=f"Medium tool confidence, no search needed: {best_tool.reason}",
                    fallback_options=[]
                )
        
        elif needs_search:
            # Low tool confidence + search needed - search first
            return RoutingDecision(
                route_type=RouteType.SEARCH_FIRST,
                primary_tool=None,
                confidence=0.7,  # Search is generally reliable for current info
                reasoning=f"Search needed for current info: {search_reason}",
                fallback_options=[best_tool.tool_name] if best_tool and best_tool.can_handle else []
            )
        
        elif best_tool and best_tool.confidence >= self.confidence_thresholds['low']:
            # Low-medium tool confidence, no search needed
            return RoutingDecision(
                route_type=RouteType.TOOL_DIRECT,
                primary_tool=best_tool.tool_name,
                confidence=best_tool.confidence,
                reasoning=f"Low-medium tool confidence: {best_tool.reason}",
                fallback_options=['search']
            )
        
        else:
            # No good tools, no search needed - use model knowledge
            return RoutingDecision(
                route_type=RouteType.MODEL_KNOWLEDGE,
                primary_tool=None,
                confidence=0.6,  # Model knowledge is decent for general facts
                reasoning="No suitable tools found, using model knowledge",
                fallback_options=['search'] if len(query.split()) > 3 else []  # Complex queries might need search
            )


# Global router instance
intelligent_router = IntelligentRouter()