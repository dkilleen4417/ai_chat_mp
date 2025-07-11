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

# Session state alias for consistency
ss = st.session_state

# Set up logging
logger = logging.getLogger(__name__)

###############################################################################
# Individual tool implementations
###############################################################################

def brave_search(query: str, num_results: int = 3) -> str:
    """Search the web using Brave Search API and return a formatted string."""
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": ss.brave_api_key,
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
        "X-API-KEY": ss.serper_api_key, 
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
        
        # Try different location formats if first one fails
        location_formats = [
            location,
            f"{location},US" if ",US" not in location else location,
            location.replace(",MD", ",MD,US"),
            location.replace(",CA", ",CA,US"),
            location.replace(",TX", ",TX,US"),
            location.replace(",FL", ",FL,US"),
            location.replace(",NY", ",NY,US"),
        ]
        
        current_data = None
        last_error = None
        
        for loc_format in location_formats:
            try:
                logger.debug(f"Trying location format: {loc_format}")
                current_url = "https://api.openweathermap.org/data/2.5/weather"
                current_params = {
                    "q": loc_format,
                    "appid": api_key,
                    "units": "imperial"  # Fahrenheit, mph
                }
                
                current_resp = requests.get(current_url, params=current_params, timeout=10)
                
                if current_resp.status_code == 200:
                    current_data = current_resp.json()
                    logger.info(f"Successfully found location with format: {loc_format}")
                    break
                else:
                    last_error = f"Status {current_resp.status_code} for {loc_format}"
                    logger.debug(f"Failed with format {loc_format}: {current_resp.status_code}")
                    
            except Exception as e:
                last_error = str(e)
                logger.debug(f"Error with format {loc_format}: {e}")
                continue
        
        if not current_data:
            return f"Could not find location: {location}. Tried multiple formats. Last error: {last_error}"
        
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
        
        # Format current weather with timestamp
        current_temp = round(current_data["main"]["temp"])
        feels_like = round(current_data["main"]["feels_like"])
        humidity = current_data["main"]["humidity"]
        description = current_data["weather"][0]["description"].title()
        wind_speed = round(current_data["wind"]["speed"])
        
        # Add timestamp information
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        data_time = datetime.fromtimestamp(current_data["dt"]).strftime("%Y-%m-%d %I:%M %p")
        
        result = [f"🌍 Weather for {city_name}, {country}:"]
        result.append(f"📅 Retrieved: {current_time}")
        result.append(f"📊 Data Time: {data_time}")
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


def enhance_user_query(original_query: str) -> str:
    """Enhance user query to better match available tools and capabilities.
    
    Args:
        original_query: The user's original question/request
    """
    try:
        # Get the decision model from session state
        if not hasattr(ss, 'decision_model'):
            return original_query  # Fallback to original if no decision model
        
        enhancement_prompt = f"""You are a query enhancement specialist. Your job is to rewrite user queries to better utilize available tools while preserving the user's intent.

Available tools:
1. get_weather_forecast(location, days) - Worldwide weather for any location
2. get_home_weather(include_forecast) - Personal weather station data (use for "home", "my station", "personal weather")
3. brave_search(query) - Web search using Brave
4. serper_search(query) - Google search via Serper

Enhancement rules:
- If user asks about "home weather", "my weather", "personal station" → ensure it's phrased to trigger get_home_weather
- If user asks about weather in a location → ensure proper format for get_weather_forecast
- If user needs current information → ensure it triggers search tools
- Preserve the user's original intent and tone
- Don't mention the enhancement process

Original query: "{original_query}"

Enhanced query (or return original if no enhancement needed):"""

        messages = [{"role": "user", "parts": [enhancement_prompt]}]
        
        response = ss.decision_model.generate_content(contents=messages)
        enhanced_query = response.text.strip()
        
        # Basic validation - if enhancement seems off, use original
        if len(enhanced_query) > len(original_query) * 3 or not enhanced_query:
            logger.debug(f"Query enhancement rejected - using original: {original_query}")
            return original_query
        
        logger.debug(f"Query enhanced: '{original_query}' → '{enhanced_query}'")
        return enhanced_query
        
    except Exception as e:
        logger.warning(f"Query enhancement failed: {e}")
        return original_query  # Always fallback to original


def get_pws_current_conditions() -> str:
    """Get CURRENT temperature, humidity, wind, and conditions from your personal WeatherFlow Tempest weather station.
    Use this tool specifically for personal weather station data, home weather, or PWS readings.
    """
    return get_home_weather(include_forecast=False)


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
        
        # Get current station observations (correct WeatherFlow API format)
        obs_url = f"https://swd.weatherflow.com/swd/rest/observations/station/{station_id}"
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
        
        # Parse observation data (WeatherFlow dictionary format)
        logger.debug(f"Observation data type: {type(latest_obs)}")
        logger.debug(f"Observation data keys: {list(latest_obs.keys()) if isinstance(latest_obs, dict) else 'Not a dict'}")
        
        # WeatherFlow returns a dictionary, not an array
        if not isinstance(latest_obs, dict):
            return "Error: WeatherFlow observation data format unexpected (not a dictionary)."
        
        # Extract values from dictionary keys
        timestamp = latest_obs.get('timestamp', 0)
        wind_avg = latest_obs.get('wind_avg')
        wind_gust = latest_obs.get('wind_gust')
        wind_direction = latest_obs.get('wind_direction')
        pressure = latest_obs.get('barometric_pressure') or latest_obs.get('station_pressure')
        temp_c = latest_obs.get('air_temperature')
        humidity = latest_obs.get('relative_humidity')
        uv = latest_obs.get('uv')
        rain_current = latest_obs.get('precip', 0)
        
        # Debug logging for key values
        logger.debug(f"Parsed values - timestamp: {timestamp}, temp_c: {temp_c}, humidity: {humidity}, wind_avg: {wind_avg}")
        logger.debug(f"All observation keys: {list(latest_obs.keys())}")
        logger.debug(f"Full observation data: {latest_obs}")
        
        # Convert Celsius to Fahrenheit
        temp_f = round((temp_c * 9/5) + 32) if temp_c is not None else None
        
        # Convert wind direction to compass
        def wind_dir_to_compass(degrees):
            if degrees is None or degrees == 0:
                return "N/A"
            directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                         "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            return directions[round(degrees / 22.5) % 16]
        
        # Format current conditions
        from datetime import datetime
        try:
            if timestamp and timestamp > 0:
                obs_time = datetime.fromtimestamp(timestamp).strftime("%I:%M %p")
            else:
                obs_time = "Unknown"
        except (ValueError, OSError):
            obs_time = "Invalid timestamp"
        
        # Add retrieval timestamp  
        retrieval_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        
        result = [f"🏠 Home Weather Station (as of {obs_time}):"]
        result.append(f"📅 Retrieved: {retrieval_time}")
        result.append(f"🔗 Station ID: {station_id}")
        result.append("")
        
        if temp_f is not None:
            result.append(f"Temperature: {temp_f}°F ({temp_c:.1f}°C)")
        else:
            result.append("⚠️ Temperature: Not available")
            logger.warning("Temperature data not available in PWS response")
        
        if humidity is not None:
            result.append(f"Humidity: {humidity}%")
        else:
            result.append("⚠️ Humidity: Not available")
            logger.warning("Humidity data not available in PWS response")
        
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
        
        if rain_current is not None and rain_current > 0:
            result.append(f"🌧️ Current precipitation: {rain_current:.2f} inches")
        
        # Add daily rain accumulation
        rain_today = latest_obs.get('precip_accum_local_day')
        if rain_today is not None and rain_today > 0:
            result.append(f"🌧️ Rain today: {rain_today:.2f} inches")
        
        # Get forecast if requested
        if include_forecast:
            try:
                # Get station details for location (correct WeatherFlow API format)
                station_url = f"https://swd.weatherflow.com/swd/rest/stations/{station_id}"
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
        return f"WeatherFlow API request failed: {str(e)}"
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected WeatherFlow response format: {str(e)}")
        return f"WeatherFlow response format error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in get_home_weather: {str(e)}", exc_info=True)
        return f"WeatherFlow error: {str(e)}"


def get_what3words_address(address: str) -> str:
    """
    Convert a street address to a What3Words address
    
    Args:
        address: Street address to convert (e.g., "317 N Beaumont Ave, Catonsville, MD")
    
    Returns:
        What3Words address or error message
    """
    try:
        import requests
        import streamlit as st
        
        # Get API key
        api_key = st.secrets.get("WHAT3WORDS_API_KEY")
        if not api_key:
            return "❌ What3Words API key not configured"
        
        # First, we need to geocode the address to get coordinates
        # Using OpenStreetMap Nominatim for geocoding (free)
        geocode_url = "https://nominatim.openstreetmap.org/search"
        geocode_params = {
            "q": address,
            "format": "json",
            "limit": 1
        }
        
        # Add User-Agent header as required by Nominatim
        headers = {
            "User-Agent": "AI-Chat-MP/1.0 (https://github.com/ai-chat-mp)"
        }
        
        geocode_response = requests.get(geocode_url, params=geocode_params, headers=headers, timeout=10)
        
        if geocode_response.status_code != 200:
            return f"❌ Failed to geocode address: {address}"
        
        geocode_data = geocode_response.json()
        if not geocode_data:
            return f"❌ Address not found: {address}"
        
        # Extract coordinates
        lat = float(geocode_data[0]["lat"])
        lon = float(geocode_data[0]["lon"])
        
        # Now convert coordinates to What3Words
        w3w_url = "https://api.what3words.com/v3/convert-to-3wa"
        w3w_params = {
            "coordinates": f"{lat},{lon}",
            "key": api_key,
            "format": "json"
        }
        
        w3w_response = requests.get(w3w_url, params=w3w_params, timeout=10)
        
        if w3w_response.status_code == 200:
            w3w_data = w3w_response.json()
            
            if "words" in w3w_data:
                w3w_address = f"///{w3w_data['words']}"
                
                result = [f"📍 What3Words Address for: {address}"]
                result.append(f"🌍 W3W: {w3w_address}")
                result.append(f"📊 Coordinates: {lat:.4f}, {lon:.4f}")
                
                if "map" in w3w_data:
                    result.append(f"🗺️  Map: {w3w_data['map']}")
                
                return "\n".join(result)
            else:
                return f"❌ No W3W address returned for coordinates: {lat}, {lon}"
        
        elif w3w_response.status_code == 402:
            # API quota exceeded - provide fallback info
            result = [f"📍 Address geocoded successfully: {address}"]
            result.append(f"📊 Coordinates: {lat:.4f}, {lon:.4f}")
            result.append(f"❌ What3Words API quota exceeded")
            result.append(f"💡 To get W3W address:")
            result.append(f"   1. Visit: https://map.what3words.com/{lat},{lon}")
            result.append(f"   2. Or upgrade W3W API plan at: https://accounts.what3words.com/select-plan")
            return "\n".join(result)
        else:
            error_data = w3w_response.json() if w3w_response.content else {}
            error_msg = error_data.get("error", {}).get("message", "Unknown error")
            return f"❌ What3Words API error: {error_msg}"
            
    except requests.exceptions.Timeout:
        return "❌ Request timed out"
    except requests.exceptions.RequestException as e:
        return f"❌ Network error: {str(e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def debug_weather_tools() -> str:
    """Debug function to test weather tools and show raw responses"""
    try:
        from datetime import datetime
        
        result = [f"🔍 Weather Tools Debug Report - {datetime.now().strftime('%Y-%m-%d %I:%M %p')}"]
        result.append("=" * 60)
        
        # Test PWS tool
        result.append("\n📊 PWS Tool Test:")
        try:
            pws_result = get_pws_current_conditions()
            result.append(f"PWS Response: {pws_result}")
        except Exception as e:
            result.append(f"PWS Error: {str(e)}")
        
        # Test weather forecast
        result.append("\n🌍 Weather Forecast Test (Catonsville, MD):")
        try:
            forecast_result = get_weather_forecast("Catonsville,MD", 1)
            result.append(f"Forecast Response: {forecast_result}")
        except Exception as e:
            result.append(f"Forecast Error: {str(e)}")
        
        result.append("\n" + "=" * 60)
        return "\n".join(result)
        
    except Exception as e:
        return f"Debug function error: {str(e)}"


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

# Register query enhancement tool
tool_registry.register_tool(
    enhance_user_query,
    "enhance_user_query", 
    "Enhance and optimize user queries to better match available tools and capabilities.",
    params_schema={
        "type": "OBJECT",
        "properties": {
            "original_query": {
                "type": "string",
                "description": "The user's original question or request to enhance"
            }
        },
        "required": ["original_query"]
    }
)

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

# Register PWS tool with very specific description
tool_registry.register_tool(
    get_pws_current_conditions,
    "get_pws_current_conditions",
    "Get CURRENT temperature, humidity, wind speed, and weather conditions from the user's PERSONAL WeatherFlow Tempest weather station. Use this for PWS data, home weather readings, personal weather station data.",
    params_schema={
        "type": "OBJECT",
        "properties": {},
        "required": []
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

# Register W3W tool
tool_registry.register_tool(
    get_what3words_address,
    "get_what3words_address",
    "Convert any street address to a What3Words address (3 unique words that identify a precise 3m x 3m location). Use this when users ask for W3W addresses, precise location sharing, or emergency location identification.",
    params_schema={
        "type": "OBJECT",
        "properties": {
            "address": {
                "type": "string",
                "description": "Street address to convert (e.g., '317 N Beaumont Ave, Catonsville, MD' or 'Times Square, New York')"
            }
        },
        "required": ["address"]
    }
)

# Register debug tool
tool_registry.register_tool(
    debug_weather_tools,
    "debug_weather_tools",
    "Debug weather tools by testing PWS and weather forecast responses. Use this when weather readings seem incorrect.",
    params_schema={
        "type": "OBJECT",
        "properties": {},
        "required": []
    }
)

__all__ = [
    "enhance_user_query",
    "brave_search",
    "serper_search",
    "get_weather_forecast",
    "get_pws_current_conditions",
    "get_home_weather",
    "get_what3words_address",
    "debug_weather_tools",
    "tool_registry",
    "ToolRegistry",
]
