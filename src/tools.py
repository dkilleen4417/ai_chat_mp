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
    """Get weather forecast for any worldwide location using OpenWeatherMap API.
    
    Args:
        location: City name, country (e.g., "London,UK" or "New York,US") or coordinates
        days: Number of days to forecast (1-5)
    """
    try:
        api_key = st.secrets.get("OPENWEATHER_API_KEY")
        if not api_key:
            return "Error: OpenWeatherMap API key not configured."
        
        logger.info(f"Fetching weather for location: {location}")
        
        # Get current weather and basic info
        current_url = "https://api.openweathermap.org/data/2.5/weather"
        current_params = {
            "q": location,
            "appid": api_key,
            "units": "imperial"  # Fahrenheit, mph
        }
        
        current_resp = requests.get(current_url, params=current_params, timeout=10)
        current_resp.raise_for_status()
        current_data = current_resp.json()
        
        if current_resp.status_code != 200:
            return f"Could not find location: {location}. Please try a different format (e.g., 'City,Country')."
        
        # Extract coordinates for forecast
        lat = current_data["coord"]["lat"]
        lon = current_data["coord"]["lon"]
        city_name = current_data["name"]
        country = current_data["sys"]["country"]
        
        # Get 5-day forecast
        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        forecast_params = {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "imperial"
        }
        
        forecast_resp = requests.get(forecast_url, params=forecast_params, timeout=10)
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()
        
        # Format current weather
        current_temp = round(current_data["main"]["temp"])
        feels_like = round(current_data["main"]["feels_like"])
        humidity = current_data["main"]["humidity"]
        description = current_data["weather"][0]["description"].title()
        wind_speed = round(current_data["wind"]["speed"])
        
        result = [f"🌍 Weather for {city_name}, {country}:"]
        result.append(f"Current: {current_temp}°F (feels like {feels_like}°F)")
        result.append(f"{description}, Humidity: {humidity}%, Wind: {wind_speed} mph")
        result.append("")
        
        # Process forecast by day
        daily_forecasts = {}
        for item in forecast_data["list"][:days*8]:  # 8 forecasts per day (3-hour intervals)
            date_str = item["dt_txt"].split()[0]  # Get date part
            if date_str not in daily_forecasts:
                daily_forecasts[date_str] = {
                    "temps": [],
                    "conditions": [],
                    "date_obj": item["dt_txt"]
                }
            
            daily_forecasts[date_str]["temps"].append(item["main"]["temp"])
            daily_forecasts[date_str]["conditions"].append(item["weather"][0]["description"])
        
        # Format daily forecasts
        result.append("📅 Forecast:")
        for date_str, data in list(daily_forecasts.items())[:days]:
            if not data["temps"]:
                continue
                
            # Calculate high/low temps
            high_temp = round(max(data["temps"]))
            low_temp = round(min(data["temps"]))
            
            # Get most common condition
            conditions = data["conditions"]
            most_common = max(set(conditions), key=conditions.count).title()
            
            # Format date
            from datetime import datetime
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            day_name = date_obj.strftime("%A")
            
            # Add umbrella if rain predicted
            umbrella = ""
            if any(term in most_common.lower() for term in ["rain", "shower", "drizzle"]):
                umbrella = " ☔"
            
            result.append(f"{day_name}: {high_temp}°F/{low_temp}°F, {most_common}{umbrella}")
        
        return "\n".join(result)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenWeatherMap API request failed: {str(e)}")
        return "Sorry, I couldn't fetch the weather information. Please check the location name or try again later."
    except KeyError as e:
        logger.error(f"Unexpected OpenWeatherMap response format: {str(e)}")
        return f"Error parsing weather data. Please try a different location format (e.g., 'City,Country')."
    except Exception as e:
        logger.error(f"Unexpected error in get_weather_forecast: {str(e)}", exc_info=True)
        return "Sorry, an unexpected error occurred while fetching the weather. Please try again later."


def get_home_weather(include_forecast: bool = True) -> str:
    """Get current weather data from your personal WeatherFlow Tempest station.
    
    Args:
        include_forecast: Whether to include 10-day forecast from WeatherFlow
    """
    try:
        # Get credentials from secrets
        api_endpoint = st.secrets.get("WEATHERFLOW_API_ENDPOINT", "https://swd.weatherflow.com/swd/rest")
        access_token = st.secrets.get("WEATHERFLOW_ACCESS_TOKEN")  # Match your existing secrets file
        station_id = st.secrets.get("WEATHERFLOW_STATION_ID")
        
        logger.debug(f"WeatherFlow config - Endpoint: {api_endpoint}")
        logger.debug(f"WeatherFlow config - Token present: {bool(access_token)}")
        logger.debug(f"WeatherFlow config - Station ID: {station_id}")
        
        if not access_token:
            return "Error: WeatherFlow access token not found. Please check WEATHERFLOW_ACCESS_TOKEN in secrets."
        if not station_id:
            return "Error: WeatherFlow station ID not found. Please check WEATHERFLOW_STATION_ID in secrets."
        
        logger.info(f"Fetching home weather from WeatherFlow station: {station_id}")
        
        # Get current station observations
        obs_url = f"{api_endpoint}/observations/station/{station_id}"
        params = {"token": access_token}
        
        logger.debug(f"WeatherFlow request URL: {obs_url}")
        logger.debug(f"WeatherFlow request params: {params}")
        
        obs_resp = requests.get(obs_url, params=params, timeout=15)
        logger.debug(f"WeatherFlow response status: {obs_resp.status_code}")
        logger.debug(f"WeatherFlow response headers: {dict(obs_resp.headers)}")
        
        if obs_resp.status_code != 200:
            logger.error(f"WeatherFlow API error {obs_resp.status_code}: {obs_resp.text}")
            return f"WeatherFlow API error {obs_resp.status_code}: {obs_resp.text[:200]}"
        
        obs_resp.raise_for_status()
        obs_data = obs_resp.json()
        logger.debug(f"WeatherFlow response data keys: {list(obs_data.keys()) if obs_data else 'None'}")
        
        if "obs" not in obs_data or not obs_data["obs"]:
            return "No recent observations available from your home weather station."
        
        # Get the most recent observation
        latest_obs = obs_data["obs"][0]
        
        # Parse observation data (WeatherFlow format)
        # obs format: [timestamp, wind_lull, wind_avg, wind_gust, wind_direction, wind_sample_interval,
        #              station_pressure, air_temperature, relative_humidity, illuminance, uv, solar_radiation,
        #              rain_amount_prev_min, precipitation_type, lightning_strike_avg_distance,
        #              lightning_strike_count, battery, report_interval]
        
        timestamp = latest_obs[0]
        wind_avg = latest_obs[2]
        wind_gust = latest_obs[3]
        wind_direction = latest_obs[4]
        pressure = latest_obs[6]
        temp_c = latest_obs[7]
        humidity = latest_obs[8]
        uv = latest_obs[10]
        rain_prev_min = latest_obs[12]
        
        # Convert Celsius to Fahrenheit
        temp_f = round((temp_c * 9/5) + 32) if temp_c is not None else None
        
        # Convert wind direction to compass
        def wind_dir_to_compass(degrees):
            if degrees is None:
                return "N/A"
            directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                         "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            return directions[round(degrees / 22.5) % 16]
        
        # Format current conditions
        from datetime import datetime
        obs_time = datetime.fromtimestamp(timestamp).strftime("%I:%M %p")
        
        result = [f"🏠 Home Weather Station (as of {obs_time}):"]
        
        if temp_f is not None:
            result.append(f"Temperature: {temp_f}°F ({temp_c:.1f}°C)")
        
        if humidity is not None:
            result.append(f"Humidity: {humidity}%")
        
        if wind_avg is not None:
            wind_dir_str = wind_dir_to_compass(wind_direction)
            result.append(f"Wind: {wind_avg:.1f} mph from {wind_dir_str}")
            if wind_gust is not None and wind_gust > wind_avg:
                result.append(f"Wind Gusts: {wind_gust:.1f} mph")
        
        if pressure is not None:
            # Convert mb to inHg
            pressure_inhg = pressure * 0.02953
            result.append(f"Pressure: {pressure:.1f} mb ({pressure_inhg:.2f} inHg)")
        
        if uv is not None:
            uv_desc = ""
            if uv <= 2:
                uv_desc = " (Low)"
            elif uv <= 5:
                uv_desc = " (Moderate)"
            elif uv <= 7:
                uv_desc = " (High)"
            elif uv <= 10:
                uv_desc = " (Very High)"
            else:
                uv_desc = " (Extreme)"
            result.append(f"UV Index: {uv:.1f}{uv_desc}")
        
        if rain_prev_min is not None and rain_prev_min > 0:
            result.append(f"🌧️ Rain: {rain_prev_min:.2f} inches in last minute")
        
        # Get forecast if requested
        if include_forecast:
            try:
                # Get station details for location
                station_url = f"{api_endpoint}/stations/{station_id}"
                station_resp = requests.get(station_url, params=params, timeout=10)
                station_resp.raise_for_status()
                station_data = station_resp.json()
                
                # WeatherFlow provides forecast data in station details
                if "forecast" in station_data:
                    result.append("")
                    result.append("📅 10-Day Forecast:")
                    
                    forecast = station_data["forecast"]
                    if "daily" in forecast:
                        for day in forecast["daily"][:5]:  # Show 5 days
                            day_name = datetime.fromtimestamp(day["day_start_local"]).strftime("%A")
                            high = round(day["air_temp_high"])
                            low = round(day["air_temp_low"])
                            conditions = day.get("conditions", "Unknown")
                            
                            # Add rain indicator
                            rain_icon = ""
                            if day.get("precip_probability", 0) > 30:
                                rain_icon = " ☔"
                            
                            result.append(f"{day_name}: {high}°F/{low}°F, {conditions}{rain_icon}")
                        
            except Exception as forecast_error:
                logger.warning(f"Could not fetch forecast: {forecast_error}")
                result.append("\n(Forecast unavailable)")
        
        return "\n".join(result)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"WeatherFlow API request failed: {str(e)}")
        return "Sorry, I couldn't connect to your home weather station. Please check your internet connection."
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected WeatherFlow response format: {str(e)}")
        return "Error parsing data from your home weather station. The station may be offline or the data format has changed."
    except Exception as e:
        logger.error(f"Unexpected error in get_home_weather: {str(e)}", exc_info=True)
        return "Sorry, an unexpected error occurred while fetching your home weather data."


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

# Register weather tools with custom parameter schemas
tool_registry.register_tool(
    get_weather_forecast,
    "get_weather_forecast",
    "Get weather forecast for any worldwide location using OpenWeatherMap. Input should be city name, country (e.g., 'London,UK' or 'New York,US').",
    params_schema={
        "type": "OBJECT",
        "properties": {
            "location": {
                "type": "string",
                "description": "The location to get weather for (e.g., 'London,UK' or 'Tokyo,JP')"
            },
            "days": {
                "type": "integer",
                "description": "Number of days to forecast (1-5)"
            }
        },
        "required": ["location"]
    }
)

tool_registry.register_tool(
    get_home_weather,
    "get_home_weather",
    "Get current weather data from the user's personal home weather station. Use this for questions about 'home weather', 'my weather station', 'personal weather station', or 'weather at home'.",
    params_schema={
        "type": "OBJECT",
        "properties": {
            "include_forecast": {
                "type": "boolean",
                "description": "Whether to include 10-day forecast (default: true)"
            }
        },
        "required": []
    }
)

__all__ = [
    "brave_search",
    "serper_search",
    "get_weather_forecast",
    "get_home_weather",
    "tool_registry",
    "ToolRegistry",
]
