#!/usr/bin/env python3
"""
Test script to get What3Words address for Drew's home
Tests W3W API integration and gets the 3-word address for the home coordinates
"""

import requests
import streamlit as st
import sys
import os

def test_w3w_api():
    """Test What3Words API and get Drew's home address"""
    print("🌍 Testing What3Words API")
    print("=" * 40)
    
    # Get API key
    try:
        api_key = st.secrets.get("WHAT3WORDS_API_KEY")
        if not api_key:
            api_key = os.getenv("WHAT3WORDS_API_KEY")
        
        if not api_key:
            print("❌ No What3Words API key found in secrets or environment")
            print("💡 Make sure WHAT3WORDS_API_KEY is in your .streamlit/secrets.toml")
            return None
        
        print("✅ API key found")
    except Exception as e:
        print(f"❌ Error accessing API key: {e}")
        return None
    
    # Drew's home coordinates (from user_profile.py)
    latitude = 39.2707
    longitude = -76.7351
    address = "317 N Beaumont Ave, Catonsville, Maryland 21228-4303"
    
    print(f"📍 Looking up W3W for:")
    print(f"   Address: {address}")
    print(f"   Coordinates: {latitude}, {longitude}")
    
    # Test convert-to-3wa endpoint
    print(f"\n🔄 Calling What3Words API...")
    
    try:
        url = "https://api.what3words.com/v3/convert-to-3wa"
        params = {
            "coordinates": f"{latitude},{longitude}",
            "key": api_key,
            "format": "json"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "words" in data:
                w3w_address = f"///{data['words']}"
                print(f"✅ Success!")
                print(f"📍 What3Words address: {w3w_address}")
                print(f"🌐 Map link: {data.get('map', 'N/A')}")
                
                # Verify coordinates match
                returned_coords = data.get("coordinates", {})
                returned_lat = returned_coords.get("lat")
                returned_lng = returned_coords.get("lng")
                
                if returned_lat and returned_lng:
                    lat_diff = abs(returned_lat - latitude)
                    lng_diff = abs(returned_lng - longitude)
                    print(f"🎯 Coordinate accuracy:")
                    print(f"   Input:  {latitude}, {longitude}")
                    print(f"   Returned: {returned_lat}, {returned_lng}")
                    print(f"   Difference: {lat_diff:.6f}, {lng_diff:.6f}")
                
                return w3w_address
            else:
                print(f"❌ No 'words' in API response: {data}")
                return None
        else:
            print(f"❌ API request failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Response text: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def test_reverse_lookup(w3w_address):
    """Test reverse lookup (3wa to coordinates)"""
    if not w3w_address:
        return
    
    print(f"\n🔄 Testing reverse lookup...")
    
    try:
        api_key = st.secrets.get("WHAT3WORDS_API_KEY")
        if not api_key:
            api_key = os.getenv("WHAT3WORDS_API_KEY")
        
        # Remove /// prefix if present
        words = w3w_address.replace("///", "")
        
        url = "https://api.what3words.com/v3/convert-to-coordinates"
        params = {
            "words": words,
            "key": api_key,
            "format": "json"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            coords = data.get("coordinates", {})
            if coords:
                print(f"✅ Reverse lookup successful!")
                print(f"   Words: {words}")
                print(f"   Coordinates: {coords.get('lat')}, {coords.get('lng')}")
                print(f"   Country: {data.get('country', 'Unknown')}")
                print(f"   Language: {data.get('language', 'Unknown')}")
            else:
                print(f"❌ No coordinates in reverse response: {data}")
        else:
            print(f"❌ Reverse lookup failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Reverse lookup error: {e}")

def main():
    """Main test function"""
    print("🏠 What3Words Test for Drew's Home Address")
    print("🎯 Goal: Get W3W address for 317 N Beaumont Ave, Catonsville, MD")
    print()
    
    # Test forward lookup
    w3w_address = test_w3w_api()
    
    # Test reverse lookup if forward was successful
    if w3w_address:
        test_reverse_lookup(w3w_address)
        
        print(f"\n✅ SUCCESS! Drew's W3W address: {w3w_address}")
        print(f"💡 Add this to user_profile.py: w3w: '{w3w_address}'")
    else:
        print(f"\n❌ Failed to get W3W address")
    
    print(f"\n🎯 Next steps:")
    print(f"   1. If successful: Update user profile with W3W address")
    print(f"   2. Create W3W tool for address-to-w3w conversion")
    print(f"   3. Register tool in tool_registry")

if __name__ == "__main__":
    main()