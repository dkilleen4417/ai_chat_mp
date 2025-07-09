"""
System Prompt Enhancement with User Context
Injects personalized user information into AI system prompts
"""

import streamlit as st
from user_profile import get_user_profile_manager

def enhance_system_prompt(original_prompt: str) -> str:
    """
    Enhance system prompt with user context and personalization
    
    Args:
        original_prompt: The base system prompt from the chat/model
        
    Returns:
        Enhanced system prompt with user context
    """
    try:
        # Get user profile manager
        profile_manager = get_user_profile_manager()
        
        # Generate user context
        user_context = profile_manager.generate_system_context()
        
        # If no user context (privacy settings), return original
        if not user_context or user_context.strip() == "You are User's AI assistant.":
            return original_prompt
        
        # Combine user context with original prompt
        if original_prompt and original_prompt.strip():
            enhanced_prompt = f"""{user_context}

{original_prompt}

Remember to use the user's personal context (location, weather station, preferences) when relevant to their queries.

CRITICAL: When using tool/function call results, you MUST use the EXACT values returned by the tools. Do not approximate, round, or generate similar values. If a tool returns "74°F", you must state "74°F" exactly. This is especially important for weather data, prices, measurements, and other precise information."""
        else:
            # If no original prompt, just use user context
            enhanced_prompt = f"""{user_context}

Be helpful, accurate, and use the user's personal context when relevant to their queries.

CRITICAL: When using tool/function call results, you MUST use the EXACT values returned by the tools. Do not approximate, round, or generate similar values. If a tool returns "74°F", you must state "74°F" exactly. This is especially important for weather data, prices, measurements, and other precise information."""
        
        return enhanced_prompt
        
    except Exception as e:
        # Fallback to original prompt if enhancement fails
        from logger import logger
        logger.warning(f"Failed to enhance system prompt: {e}")
        return original_prompt

def should_use_personal_weather_station(query: str) -> bool:
    """
    Determine if query should use personal weather station data
    
    Args:
        query: User's query string
        
    Returns:
        True if personal weather station should be used
    """
    try:
        profile_manager = get_user_profile_manager()
        
        # Check if user has PWS configured
        if not profile_manager.has_personal_weather_station():
            return False
        
        # Check for home/personal weather keywords
        home_weather_keywords = [
            "home", "my", "personal", "here", "current",
            "pws", "weather station", "tempest"
        ]
        
        weather_keywords = [
            "weather", "temperature", "temp", "conditions",
            "humidity", "wind", "rain", "pressure"
        ]
        
        query_lower = query.lower()
        
        # Must have both home/personal indicators AND weather terms
        has_home_indicator = any(keyword in query_lower for keyword in home_weather_keywords)
        has_weather_term = any(keyword in query_lower for keyword in weather_keywords)
        
        return has_home_indicator and has_weather_term
        
    except Exception:
        return False

def get_user_location_for_search(query: str) -> str:
    """
    Get user's location for search queries when location is referenced
    
    Args:
        query: User's query string
        
    Returns:
        Location string for search, or empty string if not applicable
    """
    try:
        profile_manager = get_user_profile_manager()
        
        # Check for location-related terms
        location_terms = [
            "here", "local", "nearby", "around me", "in my area",
            "home", "my city", "my location"
        ]
        
        query_lower = query.lower()
        has_location_reference = any(term in query_lower for term in location_terms)
        
        if has_location_reference:
            location = profile_manager.get_location_for_weather()
            return location or ""
        
        return ""
        
    except Exception:
        return ""