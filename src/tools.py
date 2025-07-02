"""Tool definitions and registry for agentic use.

Each tool is a plain Python function that takes keyword arguments and returns a string.
The ToolRegistry converts these into the JSON-schema format expected by models that
support function / tool calling (e.g., Google Gemini).
"""

from __future__ import annotations

from typing import Callable, Dict, List, Any, Optional
import streamlit as st
import requests
import logging

# Set up logging
logger = logging.getLogger(__name__)

###############################################################################
# Individual tool implementations
###############################################################################

def brave_search(query: str, num_results: int = 3) -> str:
    """Search the web using Brave Search API and return a formatted string."""
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": st.session_state.brave_api_key,
    }
    params = {"q": query, "count": num_results}

    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search", 
            headers=headers, 
            params=params, 
            timeout=30
        )
        if resp.status_code != 200:
            return f"Brave API error {resp.status_code}: {resp.text}"
        data = resp.json()
        results = data.get("web", {}).get("results", [])[:num_results]
        if not results:
            return "No results found."
        lines: List[str] = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            desc = r.get("description", "")
            lines.append(f"[{i}] {title}\nURL: {url}\n{desc}\n")
        return "\n".join(lines)
    except Exception as exc:  # pylint: disable=broad-except
        return f"Brave search failed: {exc}"


def serper_search(query: str, num_results: int = 3) -> str:
    """Search Google via Serper.dev and return a formatted string."""
    headers = {
        "X-API-KEY": st.session_state.serper_api_key, 
        "Content-Type": "application/json"
    }
    params = {"q": query, "num": num_results}
    try:
        resp = requests.get(
            "https://google.serper.dev/search", 
            headers=headers, 
            params=params, 
            timeout=30
        )
        if resp.status_code != 200:
            return f"Serper API error {resp.status_code}: {resp.text}"
        data = resp.json()
        lines: List[str] = []
        # Answer / knowledge boxes
        ab = data.get("answerBox")
        if ab:
            lines.append(
                f"[Featured] {ab.get('title','')}{ab.get('answer','')}{ab.get('snippet','')}\n"
            )
        kg = data.get("knowledgeGraph")
        if kg:
            lines.append(
                f"[Knowledge] {kg.get('title','')}: {kg.get('description','')}\n"
            )
        for i, r in enumerate(data.get("organic", [])[:num_results], 1):
            lines.append(f"[{i}] {r.get('title')}\nURL: {r.get('link')}\n{r.get('snippet')}\n")
        return "\n".join(lines) if lines else "No results found."
    except Exception as exc:  # pylint: disable=broad-except
        return f"Serper search failed: {exc}"


def get_weather_forecast(location: str, days: int = 3) -> str:
    """Get weather forecast for a location using National Weather Service API.
    
    Args:
        location: City name, state (e.g., "Boston, MA") or ZIP code
        days: Number of days to forecast (1-7)
    """
    try:
        logger.info(f"Fetching weather for location: {location}")
        
        # Try to get coordinates using OpenStreetMap Nominatim
        geo_url = "https://nominatim.openstreetmap.org/search"
        geo_params = {
            "q": location,
            "format": "json",
            "limit": 1
        }
        
        logger.debug(f"Geocoding request: {geo_url}?{requests.compat.urlencode(geo_params)}")
        geo_resp = requests.get(
            geo_url, 
            params=geo_params, 
            headers={"User-Agent": "AIWeatherApp/1.0"},
            timeout=10
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        
        if not geo_data:
            logger.warning(f"No location found for: {location}")
            return f"Could not find location: {location}. Please try being more specific (e.g., 'Boston, MA' or a ZIP code)."
            
        lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
        logger.debug(f"Found coordinates: {lat}, {lon}")
        
        # Get weather forecast from National Weather Service
        weather_url = f"https://api.weather.gov/points/{lat},{lon}"
        headers = {
            "User-Agent": "AIWeatherApp/1.0 (your-email@example.com)",
            "Accept": "application/geo+json"
        }
        
        # Get forecast URL for this location
        logger.debug(f"Fetching points data from: {weather_url}")
        points_resp = requests.get(weather_url, headers=headers, timeout=15)
        points_resp.raise_for_status()
        points_data = points_resp.json()
        
        if "properties" not in points_data or "forecast" not in points_data["properties"]:
            logger.error(f"Unexpected points data structure: {points_data}")
            return "Error: Could not get forecast URL from weather service."
            
        forecast_url = points_data["properties"]["forecast"]
        logger.debug(f"Fetching forecast from: {forecast_url}")
        
        # Get the actual forecast
        forecast_resp = requests.get(forecast_url, headers=headers, timeout=15)
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()
        
        if "properties" not in forecast_data or "periods" not in forecast_data["properties"]:
            logger.error(f"Unexpected forecast data structure: {forecast_data}")
            return "Error: Could not parse forecast data from weather service."
        
        # Format the forecast
        periods = forecast_data["properties"]["periods"][:days*2]  # Two periods per day
        
        result = [f"🌦️ Weather for {location}:"]
        for period in periods:
            day = period.get("name", "Unknown")
            temp = f"{period.get('temperature', 'N/A')}°{period.get('temperatureUnit', '')}"
            forecast = period.get("shortForecast", "No forecast available")
            wind = period.get("windSpeed", "N/A")
            
            # Add umbrella recommendation if rain is in the forecast
            umbrella = ""
            if any(term in forecast.lower() for term in ["rain", "shower", "drizzle"]):
                umbrella = " ☔"
            
            result.append(f"{day}: {temp}, {forecast}, Wind: {wind}{umbrella}")
        
        return "\n".join(result)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Weather API request failed: {str(e)}")
        return "Sorry, I couldn't fetch the weather information. The weather service might be unavailable."
    except Exception as e:
        logger.error(f"Unexpected error in get_weather_forecast: {str(e)}", exc_info=True)
        return "Sorry, an unexpected error occurred while fetching the weather. Please try again later."


class ToolRegistry:
    """Stores callable tools and produces JSON schemas for models.
    
    This enhanced version supports custom parameter schemas for each tool.
    """

    def __init__(self) -> None:
        self._fns: Dict[str, Callable[..., str]] = {}
        self._descriptions: Dict[str, str] = {}
        self._param_schemas: Dict[str, Dict[str, Any]] = {}

    def register_tool(
        self, 
        fn: Callable[..., str], 
        name: str, 
        description: str, 
        params_schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a tool with an optional custom parameter schema.
        
        Args:
            fn: The callable function to register
            name: Name of the tool (must be unique)
            description: Description of what the tool does
            params_schema: Optional custom parameter schema. If not provided,
                         defaults to a simple 'query' parameter.
        """
        self._fns[name] = fn
        self._descriptions[name] = description
        if params_schema is not None:
            self._param_schemas[name] = params_schema

    def get_callable(self, name: str) -> Optional[Callable[..., str]]:
        """Get a callable tool by name."""
        return self._fns.get(name)

    def list_tool_configs(self) -> List[Dict[str, Any]]:
        """Return JSON-schema tool definitions compatible with Gemini."""
        defs: List[Dict[str, Any]] = []
        
        for name, desc in self._descriptions.items():
            # Use custom parameter schema if available, otherwise use default
            if name in self._param_schemas:
                params = self._param_schemas[name]
            else:
                # Default parameter schema for backward compatibility
                params = {
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to run",
                        }
                    },
                    "required": ["query"],
                }
            
            defs.append({
                "name": name,
                "description": desc,
                "parameters": params
            })
        
        # Gemini expects each tool wrapper with "function_declarations"
        return [{"function_declarations": [d]} for d in defs]


# Initialize the tool registry
tool_registry = ToolRegistry()

# Register search tools
tool_registry.register_tool(
    brave_search, 
    "brave_search", 
    "Search the web using Brave Search API."
)

tool_registry.register_tool(
    serper_search, 
    "serper_search", 
    "Search Google via Serper.dev."
)

# Register weather tool with custom parameter schema
tool_registry.register_tool(
    get_weather_forecast,
    "get_weather_forecast",
    "Get weather forecast for a location. Input should be a city name and state (e.g., 'Boston, MA') or ZIP code.",
    params_schema={
        "type": "OBJECT",
        "properties": {
            "location": {
                "type": "string",
                "description": "The location to get weather for (e.g., 'Boston, MA' or ZIP code)"
            },
            "days": {
                "type": "integer",
                "description": "Number of days to forecast (1-7)"
            }
        },
        "required": ["location"]
    }
)

__all__ = [
    "brave_search",
    "serper_search",
    "get_weather_forecast",
    "tool_registry",
    "ToolRegistry",
]
