"""
User Profile Management System
Handles user metadata for personalized AI interactions
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pymongo import MongoClient
import streamlit as st
import config
from logger import logger

# Session state alias for consistency
ss = st.session_state

class UserProfileManager:
    """Manages user profile data and context injection"""
    
    def __init__(self, db):
        self.db = db
        self.users_collection = db.users
    
    def get_default_profile(self) -> Dict[str, Any]:
        """Get default user profile structure"""
        return {
            "user_id": "default_user",
            "name": "Drew",
            "personal_info": {
                "email": "",
                "phone": ""
            },
            "home_address": {
                "street": "317 N Beaumont Ave",
                "city": "Catonsville",
                "state": "Maryland",
                "zip": "21228-4303",
                "country": "US"
            },
            "coordinates": {
                "latitude": 39.2707,
                "longitude": -76.7351,
                "w3w": "boom.unable.habit",  # What3Words
                "accuracy": "address"
            },
            "timezone": "America/New_York",
            "weather_station": {
                "provider": "weatherflow",
                "station_id": st.secrets.get("WEATHERFLOW_STATION_ID", ""),
                "description": "Personal weather station",
                "enabled": bool(st.secrets.get("WEATHERFLOW_STATION_ID"))
            },
            "preferences": {
                "units": "imperial",  # or metric
                "temperature_unit": "fahrenheit",
                "default_model": "gemini-2.5-flash-lite-preview-06-17",
                "language": "en",
                "timezone_display": "local"
            },
            "ai_context": {
                "personality": "helpful and professional",
                "expertise_areas": [],
                "communication_style": "conversational"
            },
            "privacy": {
                "share_location": True,
                "share_weather_station": True,
                "share_name": True
            },
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "version": "1.0"
        }
    
    def get_user_profile(self, user_id: str = "default_user") -> Dict[str, Any]:
        """Get user profile, creating default if none exists"""
        profile = self.users_collection.find_one({"user_id": user_id})
        
        if not profile:
            logger.info(f"Creating default profile for user: {user_id}")
            default_profile = self.get_default_profile()
            default_profile["user_id"] = user_id
            self.users_collection.insert_one(default_profile)
            return default_profile
        
        return profile
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile with new data"""
        try:
            updates["updated_at"] = datetime.now()
            result = self.users_collection.update_one(
                {"user_id": user_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
            return False
    
    def generate_system_context(self, user_id: str = "default_user") -> str:
        """Generate system prompt context from user profile"""
        profile = self.get_user_profile(user_id)
        
        if not profile.get("privacy", {}).get("share_name", True):
            name = "User"
        else:
            name = profile.get("name", "User")
        
        context_parts = [f"You are {name}'s AI assistant."]
        
        # Add location context if privacy allows
        if profile.get("privacy", {}).get("share_location", True):
            home = profile.get("home_address", {})
            if home.get("city") and home.get("state"):
                context_parts.append(f"User's home: {home['city']}, {home['state']}")
            
            coords = profile.get("coordinates", {})
            if coords.get("latitude") and coords.get("longitude"):
                context_parts.append(
                    f"Home coordinates: {coords['latitude']:.4f}, {coords['longitude']:.4f}"
                )
            
            if coords.get("w3w"):
                context_parts.append(f"What3Words: {coords['w3w']}")
        
        # Add timezone and current date/time
        timezone = profile.get("timezone", "UTC")
        context_parts.append(f"User timezone: {timezone}")
        
        # Add current date/time in user's timezone
        try:
            import pytz
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
            context_parts.append(f"Current date/time: {current_time.strftime('%Y-%m-%d %I:%M %p %Z')}")
        except Exception:
            # Fallback to UTC if timezone conversion fails
            current_time = datetime.now()
            context_parts.append(f"Current date/time: {current_time.strftime('%Y-%m-%d %I:%M %p UTC')}")
        
        # Add weather station context if available and privacy allows
        if profile.get("privacy", {}).get("share_weather_station", True):
            weather = profile.get("weather_station", {})
            if weather.get("enabled") and weather.get("station_id"):
                context_parts.append(
                    f"Personal weather station: {weather['provider']} station {weather['station_id']}"
                )
                context_parts.append(
                    "When user asks about 'home weather' or 'personal weather station', use this station data."
                )
        
        # Add preferences
        prefs = profile.get("preferences", {})
        if prefs.get("units"):
            context_parts.append(f"Preferred units: {prefs['units']}")
        
        # Add AI personality context
        ai_context = profile.get("ai_context", {})
        if ai_context.get("personality"):
            context_parts.append(f"Communication style: {ai_context['personality']}")
        
        return "\n".join(context_parts)
    
    def get_location_for_weather(self, user_id: str = "default_user") -> Optional[str]:
        """Get location string for weather queries"""
        profile = self.get_user_profile(user_id)
        
        if not profile.get("privacy", {}).get("share_location", True):
            return None
        
        home = profile.get("home_address", {})
        if home.get("city") and home.get("state"):
            return f"{home['city']}, {home['state']}"
        
        coords = profile.get("coordinates", {})
        if coords.get("latitude") and coords.get("longitude"):
            return f"{coords['latitude']},{coords['longitude']}"
        
        return None
    
    def has_personal_weather_station(self, user_id: str = "default_user") -> bool:
        """Check if user has a personal weather station configured"""
        profile = self.get_user_profile(user_id)
        weather = profile.get("weather_station", {})
        return (
            weather.get("enabled", False) and 
            weather.get("station_id") and
            profile.get("privacy", {}).get("share_weather_station", True)
        )

def get_user_profile_manager():
    """Get user profile manager instance"""
    if 'user_profile_manager' not in ss:
        from main import get_database
        db = get_database()
        ss.user_profile_manager = UserProfileManager(db)
    
    return ss.user_profile_manager