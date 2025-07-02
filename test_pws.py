#!/usr/bin/env python3
"""
Standalone test script for WeatherFlow Tempest API
This will help debug PWS connection issues outside of Streamlit
"""

import requests
import json
from datetime import datetime

def test_weatherflow_api():
    print("=== WeatherFlow Tempest API Test ===\n")
    
    # Get credentials - you'll need to fill these in
    ACCESS_TOKEN = input("Enter your WEATHERFLOW_ACCESS_TOKEN: ").strip()
    STATION_ID = input("Enter your WEATHERFLOW_STATION_ID: ").strip()
    
    if not ACCESS_TOKEN or not STATION_ID:
        print("❌ Error: Both ACCESS_TOKEN and STATION_ID are required")
        return
    
    print(f"\n📡 Testing connection to station: {STATION_ID}")
    print(f"🔑 Using token: {ACCESS_TOKEN[:8]}...")
    
    # Test 1: Get stations list
    print("\n--- Test 1: Get Stations List ---")
    try:
        stations_url = "https://swd.weatherflow.com/swd/rest/stations"
        params = {"token": ACCESS_TOKEN}
        
        print(f"URL: {stations_url}")
        print(f"Params: {params}")
        
        response = requests.get(stations_url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
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
        print(f"Params: {params}")
        
        response = requests.get(obs_url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Observations API call successful!")
            print(f"Response keys: {list(data.keys())}")
            
            if "obs" in data and data["obs"]:
                latest_obs = data["obs"][0]
                print(f"Latest observation has {len(latest_obs)} fields:")
                
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
                    print(f"Raw data: {latest_obs}")
            else:
                print("⚠️  No observations found in response")
                
        else:
            print(f"❌ Observations API failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Observations API error: {e}")
    
    # Test 3: Get station details
    print(f"\n--- Test 3: Get Station {STATION_ID} Details ---")
    try:
        station_url = f"https://swd.weatherflow.com/swd/rest/stations/{STATION_ID}"
        params = {"token": ACCESS_TOKEN}
        
        print(f"URL: {station_url}")
        
        response = requests.get(station_url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Station details API call successful!")
            print(f"Response keys: {list(data.keys())}")
            
            if "stations" in data and data["stations"]:
                station = data["stations"][0]
                print(f"Station Name: {station.get('name', 'Unknown')}")
                print(f"Location: {station.get('latitude', 'Unknown')}, {station.get('longitude', 'Unknown')}")
                print(f"Timezone: {station.get('timezone', 'Unknown')}")
                
                if "devices" in station:
                    print(f"Devices: {len(station['devices'])}")
                    for device in station["devices"]:
                        print(f"  - {device.get('device_type', 'Unknown')} (ID: {device.get('device_id', 'Unknown')})")
        else:
            print(f"❌ Station details API failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Station details API error: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_weatherflow_api()