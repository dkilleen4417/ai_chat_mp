"""Weather tool implementation using National Weather Service API."""

import logging
import json
from typing import Dict, Any, Optional
import requests

# Set up logging
logger = logging.getLogger(__name__)

def get_weather_forecast(location: str, days: int = 3) -> str:
    """Get weather forecast for a location using National Weather Service API.
    
    Args:
        location: City name, state (e.g., "Boston, MA") or ZIP code
        days: Number of days to forecast (1-7)
    
    Returns:
        Formatted weather forecast string or error message
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
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse weather data: {str(e)}")
        return "Sorry, I had trouble understanding the weather data. Please try again later."
    except Exception as e:
        logger.error(f"Unexpected error in get_weather_forecast: {str(e)}", exc_info=True)
        return "Sorry, an unexpected error occurred while fetching the weather. Please try again later."
