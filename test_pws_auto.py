#!/usr/bin/env python3
"""
Standalone test script for WeatherFlow Tempest API - Auto version
Reads credentials from .streamlit/secrets.toml
"""

import requests
import json
import toml
from datetime import datetime
from pathlib import Path

def load_secrets():
    """Load secrets from Streamlit secrets file"""
    secrets_path = Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        print(f"❌ Secrets file not found: {secrets_path}")
        return None, None
    
    try:
        secrets = toml.load(secrets_path)
        access_token = secrets.get("WEATHERFLOW_ACCESS_TOKEN")
        station_id = secrets.get("WEATHERFLOW_STATION_ID")
        
        print(f"📁 Loaded secrets from: {secrets_path}")
        print(f"🔑 Token found: {'Yes' if access_token else 'No'}")
        print(f"🆔 Station ID found: {'Yes' if station_id else 'No'}")
        
        return access_token, station_id
    except Exception as e:
        print(f"❌ Error reading secrets: {e}")
        return None, None

def test_weatherflow_api():
    print("=== WeatherFlow Tempest API Test (Auto) ===\n")
    
    # Load credentials from secrets file
    ACCESS_TOKEN, STATION_ID = load_secrets()
    
    if not ACCESS_TOKEN or not STATION_ID:
        print("❌ Error: Both ACCESS_TOKEN and STATION_ID are required in secrets.toml")
        print("Make sure your .streamlit/secrets.toml contains:")
        print("WEATHERFLOW_ACCESS_TOKEN = \"your-token-here\"")
        print("WEATHERFLOW_STATION_ID = \"your-station-id\"")
        return
    
    print(f"\n📡 Testing connection to station: {STATION_ID}")
    print(f"🔑 Using token: {ACCESS_TOKEN[:8]}...")
    
    # Test 1: Get stations list
    print("\n--- Test 1: Get Stations List ---")
    try:
        stations_url = "https://swd.weatherflow.com/swd/rest/stations"
        params = {"token": ACCESS_TOKEN}
        
        print(f"URL: {stations_url}")
        
        response = requests.get(stations_url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Stations API call successful!")
            print(f"Response keys: {list(data.keys())}")
            
            if "stations" in data:
                print(f"Found {len(data['stations'])} station(s):")
                for station in data["stations"]:
                    print(f"  - Station {station.get('station_id', 'Unknown')}: {station.get('name', 'Unnamed')}")
            else:
                print("⚠️  No 'stations' key in response")
                print(f"Full response: {json.dumps(data, indent=2)[:500]}...")
        else:
            print(f"❌ Stations API failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Stations API error: {e}")
    
    # Test 2: Get station observations
    print(f"\n--- Test 2: Get Station {STATION_ID} Observations ---")
    try:
        obs_url = f"https://swd.weatherflow.com/swd/rest/observations/station/{STATION_ID}"
        params = {"token": ACCESS_TOKEN}
        
        print(f"URL: {obs_url}")
        
        response = requests.get(obs_url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Observations API call successful!")
            print(f"Response keys: {list(data.keys())}")
            
            if "obs" in data and data["obs"]:
                latest_obs = data["obs"][0]
                print(f"Latest observation has {len(latest_obs)} fields")
                
                # Parse observation data (WeatherFlow format)
                if len(latest_obs) >= 18:
                    timestamp = latest_obs[0]
                    wind_avg = latest_obs[2]
                    wind_gust = latest_obs[3]
                    wind_direction = latest_obs[4]
                    pressure = latest_obs[6]
                    temp_c = latest_obs[7]
                    humidity = latest_obs[8]
                    uv = latest_obs[10]
                    rain_prev_min = latest_obs[12]
                    
                    # Convert to readable format
                    obs_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    temp_f = (temp_c * 9/5) + 32 if temp_c is not None else None
                    
                    print(f"\n🌡️  Temperature: {temp_f:.1f}°F ({temp_c:.1f}°C)")
                    print(f"💧 Humidity: {humidity}%")
                    print(f"💨 Wind: {wind_avg:.1f} mph (gusts: {wind_gust:.1f})")
                    print(f"🧭 Wind Direction: {wind_direction}°")
                    print(f"📊 Pressure: {pressure:.1f} mb")
                    print(f"☀️  UV Index: {uv}")
                    print(f"🌧️  Rain (last min): {rain_prev_min} inches")
                    print(f"⏰ Observation Time: {obs_time}")
                else:
                    print("⚠️  Observation data format unexpected")
                    print(f"Data length: {len(latest_obs)}")
                    print(f"Raw data: {latest_obs}")
            else:
                print("⚠️  No observations found in response")
                print(f"Full response: {json.dumps(data, indent=2)[:500]}...")
                
        else:
            print(f"❌ Observations API failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Observations API error: {e}")
    
    print("\n=== Test Complete ===")
    print("\nIf this worked, your PWS credentials and API calls are fine.")
    print("If not, we found the exact issue to fix in the chat app!")

if __name__ == "__main__":
    test_weatherflow_api()