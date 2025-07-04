"""
User Profile UI Components
Streamlit interface for managing user profiles
"""

import streamlit as st
from datetime import datetime
from user_profile import get_user_profile_manager
from logger import logger

def render_user_profile():
    """Render the user profile management interface"""
    st.title("👤 User Profile")
    st.markdown("Manage your personal information for more personalized AI interactions.")
    
    profile_manager = get_user_profile_manager()
    profile = profile_manager.get_user_profile()
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Basic Info", 
        "📍 Location", 
        "🌡️ Weather Station", 
        "⚙️ Preferences",
        "🔒 Privacy"
    ])
    
    with tab1:
        render_basic_info(profile_manager, profile)
    
    with tab2:
        render_location_info(profile_manager, profile)
    
    with tab3:
        render_weather_station(profile_manager, profile)
    
    with tab4:
        render_preferences(profile_manager, profile)
    
    with tab5:
        render_privacy_settings(profile_manager, profile)

def render_basic_info(profile_manager, profile):
    """Render basic user information form"""
    st.subheader("Basic Information")
    
    with st.form("basic_info_form"):
        name = st.text_input(
            "Name", 
            value=profile.get("name", ""),
            help="How should the AI address you?"
        )
        
        email = st.text_input(
            "Email (optional)", 
            value=profile.get("personal_info", {}).get("email", "")
        )
        
        phone = st.text_input(
            "Phone (optional)", 
            value=profile.get("personal_info", {}).get("phone", "")
        )
        
        personality = st.selectbox(
            "AI Communication Style",
            ["helpful and professional", "casual and friendly", "formal and precise", "creative and enthusiastic"],
            index=["helpful and professional", "casual and friendly", "formal and precise", "creative and enthusiastic"].index(
                profile.get("ai_context", {}).get("personality", "helpful and professional")
            )
        )
        
        if st.form_submit_button("💾 Save Basic Info"):
            updates = {
                "name": name,
                "personal_info.email": email,
                "personal_info.phone": phone,
                "ai_context.personality": personality
            }
            
            if profile_manager.update_user_profile("default_user", updates):
                st.success("✅ Basic information updated!")
                st.rerun()
            else:
                st.error("❌ Failed to update profile")

def render_location_info(profile_manager, profile):
    """Render location information form"""
    st.subheader("Home Location")
    st.info("This helps the AI understand references to 'home' and provide location-aware responses.")
    
    with st.form("location_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            street = st.text_input(
                "Street Address", 
                value=profile.get("home_address", {}).get("street", "")
            )
            city = st.text_input(
                "City", 
                value=profile.get("home_address", {}).get("city", "")
            )
            
        with col2:
            state = st.text_input(
                "State", 
                value=profile.get("home_address", {}).get("state", "")
            )
            zip_code = st.text_input(
                "ZIP Code", 
                value=profile.get("home_address", {}).get("zip", "")
            )
        
        country = st.selectbox(
            "Country",
            ["US", "CA", "UK", "AU", "Other"],
            index=["US", "CA", "UK", "AU", "Other"].index(
                profile.get("home_address", {}).get("country", "US")
            ) if profile.get("home_address", {}).get("country", "US") in ["US", "CA", "UK", "AU", "Other"] else 0
        )
        
        st.subheader("Coordinates (Optional)")
        col3, col4 = st.columns(2)
        
        with col3:
            latitude = st.number_input(
                "Latitude", 
                value=profile.get("coordinates", {}).get("latitude"),
                format="%.6f",
                help="Decimal degrees (e.g., 37.774929)"
            )
            
        with col4:
            longitude = st.number_input(
                "Longitude", 
                value=profile.get("coordinates", {}).get("longitude"),
                format="%.6f", 
                help="Decimal degrees (e.g., -122.419418)"
            )
        
        w3w = st.text_input(
            "What3Words (optional)",
            value=profile.get("coordinates", {}).get("w3w", ""),
            help="Three words that identify your location (e.g., filled.count.soap)"
        )
        
        timezone = st.selectbox(
            "Timezone",
            [
                "America/Los_Angeles", "America/Denver", "America/Chicago", "America/New_York",
                "America/Toronto", "Europe/London", "Europe/Paris", "Asia/Tokyo", "Australia/Sydney"
            ],
            index=[
                "America/Los_Angeles", "America/Denver", "America/Chicago", "America/New_York",
                "America/Toronto", "Europe/London", "Europe/Paris", "Asia/Tokyo", "Australia/Sydney"
            ].index(profile.get("timezone", "America/Los_Angeles")) if profile.get("timezone", "America/Los_Angeles") in [
                "America/Los_Angeles", "America/Denver", "America/Chicago", "America/New_York",
                "America/Toronto", "Europe/London", "Europe/Paris", "Asia/Tokyo", "Australia/Sydney"
            ] else 0
        )
        
        if st.form_submit_button("📍 Save Location"):
            updates = {
                "home_address": {
                    "street": street,
                    "city": city, 
                    "state": state,
                    "zip": zip_code,
                    "country": country
                },
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "w3w": w3w,
                    "accuracy": "user_provided"
                },
                "timezone": timezone
            }
            
            if profile_manager.update_user_profile("default_user", updates):
                st.success("✅ Location information updated!")
                st.rerun()
            else:
                st.error("❌ Failed to update location")

def render_weather_station(profile_manager, profile):
    """Render weather station configuration"""
    st.subheader("Personal Weather Station")
    
    weather_config = profile.get("weather_station", {})
    
    with st.form("weather_station_form"):
        enabled = st.checkbox(
            "Enable Personal Weather Station",
            value=weather_config.get("enabled", False),
            help="Allow AI to access your personal weather station data"
        )
        
        provider = st.selectbox(
            "Weather Station Provider",
            ["weatherflow", "davis", "ambient", "other"],
            index=["weatherflow", "davis", "ambient", "other"].index(
                weather_config.get("provider", "weatherflow")
            ) if weather_config.get("provider", "weatherflow") in ["weatherflow", "davis", "ambient", "other"] else 0
        )
        
        station_id = st.text_input(
            "Station ID",
            value=weather_config.get("station_id", ""),
            help="Your weather station's unique identifier"
        )
        
        description = st.text_input(
            "Description",
            value=weather_config.get("description", "Personal weather station"),
            help="Brief description of your weather station setup"
        )
        
        if st.form_submit_button("🌡️ Save Weather Station"):
            updates = {
                "weather_station": {
                    "enabled": enabled,
                    "provider": provider,
                    "station_id": station_id,
                    "description": description
                }
            }
            
            if profile_manager.update_user_profile("default_user", updates):
                st.success("✅ Weather station configuration updated!")
                st.rerun()
            else:
                st.error("❌ Failed to update weather station config")

def render_preferences(profile_manager, profile):
    """Render user preferences"""
    st.subheader("AI Preferences")
    
    prefs = profile.get("preferences", {})
    
    with st.form("preferences_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            units = st.selectbox(
                "Measurement Units",
                ["imperial", "metric"],
                index=["imperial", "metric"].index(prefs.get("units", "imperial"))
            )
            
            temp_unit = st.selectbox(
                "Temperature Unit", 
                ["fahrenheit", "celsius"],
                index=["fahrenheit", "celsius"].index(prefs.get("temperature_unit", "fahrenheit"))
            )
            
        with col2:
            language = st.selectbox(
                "Language",
                ["en", "es", "fr", "de", "ja"],
                index=["en", "es", "fr", "de", "ja"].index(prefs.get("language", "en"))
            )
            
            timezone_display = st.selectbox(
                "Time Display",
                ["local", "utc", "both"],
                index=["local", "utc", "both"].index(prefs.get("timezone_display", "local"))
            )
        
        if st.form_submit_button("⚙️ Save Preferences"):
            updates = {
                "preferences": {
                    "units": units,
                    "temperature_unit": temp_unit,
                    "language": language,
                    "timezone_display": timezone_display
                }
            }
            
            if profile_manager.update_user_profile("default_user", updates):
                st.success("✅ Preferences updated!")
                st.rerun()
            else:
                st.error("❌ Failed to update preferences")

def render_privacy_settings(profile_manager, profile):
    """Render privacy settings"""
    st.subheader("Privacy Settings")
    st.info("Control what information the AI can access and use in responses.")
    
    privacy = profile.get("privacy", {})
    
    with st.form("privacy_form"):
        share_name = st.checkbox(
            "Share Name with AI",
            value=privacy.get("share_name", True),
            help="Allow AI to use your name in responses"
        )
        
        share_location = st.checkbox(
            "Share Location Information", 
            value=privacy.get("share_location", True),
            help="Allow AI to access your home address and coordinates"
        )
        
        share_weather_station = st.checkbox(
            "Share Weather Station Data",
            value=privacy.get("share_weather_station", True),
            help="Allow AI to access your personal weather station"
        )
        
        if st.form_submit_button("🔒 Save Privacy Settings"):
            updates = {
                "privacy": {
                    "share_name": share_name,
                    "share_location": share_location,
                    "share_weather_station": share_weather_station
                }
            }
            
            if profile_manager.update_user_profile("default_user", updates):
                st.success("✅ Privacy settings updated!")
                st.rerun()
            else:
                st.error("❌ Failed to update privacy settings")
    
    # Show current system context
    if st.checkbox("🔍 Preview AI Context", help="See what context is shared with the AI"):
        with st.expander("Current AI System Context"):
            context = profile_manager.generate_system_context()
            st.code(context, language="text")