#!/usr/bin/env python3
"""Test script for the weather tool."""

import logging
from src.tools import get_weather_forecast, tool_registry

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_weather_tool():
    """Test the weather tool with a sample location."""
    # Test with a well-known location
    location = "New York, NY"
    print(f"Testing weather forecast for: {location}")
    
    # Call the weather function directly
    print("\nDirect function call:")
    result = get_weather_forecast(location, days=2)
    print(result)
    
    # Test through the tool registry
    print("\nThrough tool registry:")
    weather_tool = tool_registry.get_callable("get_weather_forecast")
    if weather_tool:
        result = weather_tool(location=location, days=2)
        print(result)
    else:
        print("Error: Weather tool not found in registry")

if __name__ == "__main__":
    test_weather_tool()
