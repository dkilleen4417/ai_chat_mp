"""
Settings management for AI Chat MP
Handles app configuration, preferences, and housekeeping functions
"""

import streamlit as st
from pymongo import MongoClient
from config import MONGO_LOCAL_URI, MONGO_LOCAL_DB_NAME
from datetime import datetime
import json

# Default settings configuration
DEFAULT_SETTINGS = {
    # System Configuration
    "default_model": "gemini-2.5-flash-lite-preview-06-17",
    "request_timeout": 30,
    "max_retries": 3,
    
    # Search Configuration  
    "default_search_provider": "brave",
    "search_result_count": 5,
    "search_timeout": 10,
    
    # UI Preferences
    "theme": "auto",
    "debug_panel_default": False,
    "show_response_metrics": True,
    "auto_scroll_chat": True,
    
    # Data Management
    "chat_retention_days": 365,
    "auto_backup_enabled": True,
    "backup_frequency_hours": 24,
    "max_backup_files": 30,
    
    # Performance
    "enable_caching": True,
    "cache_ttl_minutes": 60,
    "concurrent_requests": 5,
    
    # Privacy & Security
    "log_level": "INFO",
    "anonymize_logs": False,
    "session_timeout_minutes": 480,  # 8 hours
}

class SettingsManager:
    """Manages application settings with MongoDB persistence"""
    
    def __init__(self):
        self.client = MongoClient(MONGO_LOCAL_URI)
        self.db = self.client[MONGO_LOCAL_DB_NAME]
        self.collection = self.db.app_settings
        
    def get_settings(self, user_id="default"):
        """Get settings for a user, with defaults for missing values"""
        settings_doc = self.collection.find_one({"user_id": user_id})
        
        if settings_doc:
            # Merge with defaults to ensure all keys exist
            settings = DEFAULT_SETTINGS.copy()
            settings.update(settings_doc.get("settings", {}))
            return settings
        
        return DEFAULT_SETTINGS.copy()
    
    def save_settings(self, settings, user_id="default"):
        """Save settings for a user"""
        settings_doc = {
            "user_id": user_id,
            "settings": settings,
            "updated_at": datetime.now().timestamp()
        }
        
        self.collection.replace_one(
            {"user_id": user_id},
            settings_doc,
            upsert=True
        )
        
        return True
    
    def reset_to_defaults(self, user_id="default"):
        """Reset settings to defaults"""
        return self.save_settings(DEFAULT_SETTINGS.copy(), user_id)
    
    def export_settings(self, user_id="default"):
        """Export settings as JSON string"""
        settings = self.get_settings(user_id)
        return json.dumps(settings, indent=2)
    
    def import_settings(self, json_string, user_id="default"):
        """Import settings from JSON string"""
        try:
            imported_settings = json.loads(json_string)
            # Validate against default keys
            valid_settings = {}
            for key in DEFAULT_SETTINGS.keys():
                if key in imported_settings:
                    valid_settings[key] = imported_settings[key]
            
            return self.save_settings(valid_settings, user_id)
        except json.JSONDecodeError:
            return False

def render_settings():
    """Render the settings UI"""
    st.title("⚙️ Settings")
    
    # Initialize settings manager
    settings_manager = SettingsManager()
    current_settings = settings_manager.get_settings()
    
    # Create tabs for different setting categories
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔧 System", 
        "🔍 Search", 
        "🎨 Interface", 
        "💾 Data", 
        "🔐 Privacy"
    ])
    
    # System Configuration Tab
    with tab1:
        st.subheader("System Configuration")
        
        # Default Model Selection
        st.write("**Default AI Model**")
        # TODO: Get available models from database
        default_model = st.selectbox(
            "Choose default model for new chats",
            options=["gemini-2.5-flash-lite-preview-06-17", "claude-3-5-sonnet-20241022", "gpt-4o"],
            index=0 if current_settings["default_model"] == "gemini-2.5-flash-lite-preview-06-17" else 0,
            help="This model will be pre-selected when creating new chats"
        )
        
        # Timeouts and Performance
        col1, col2 = st.columns(2)
        with col1:
            request_timeout = st.slider(
                "Request Timeout (seconds)",
                min_value=10, max_value=120, 
                value=current_settings["request_timeout"],
                help="How long to wait for AI responses"
            )
        with col2:
            max_retries = st.slider(
                "Max Retries",
                min_value=1, max_value=5,
                value=current_settings["max_retries"],
                help="Number of retry attempts for failed requests"
            )
    
    # Search Configuration Tab  
    with tab2:
        st.subheader("Search Configuration")
        
        search_provider = st.radio(
            "Default Search Provider",
            options=["brave", "serper"],
            index=0 if current_settings["default_search_provider"] == "brave" else 1,
            help="Brave: Privacy-focused | Serper: Google results"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            search_result_count = st.slider(
                "Search Results Count",
                min_value=3, max_value=15,
                value=current_settings["search_result_count"],
                help="Number of search results to retrieve"
            )
        with col2:
            search_timeout = st.slider(
                "Search Timeout (seconds)",
                min_value=5, max_value=30,
                value=current_settings["search_timeout"]
            )
    
    # Interface Tab
    with tab3:
        st.subheader("User Interface")
        
        theme = st.radio(
            "Theme",
            options=["auto", "light", "dark"],
            index=["auto", "light", "dark"].index(current_settings["theme"]),
            help="Auto follows system theme"
        )
        
        debug_panel_default = st.checkbox(
            "Show Debug Panel by Default",
            value=current_settings["debug_panel_default"],
            help="Debug panel will be visible when opening the app"
        )
        
        show_response_metrics = st.checkbox(
            "Show Response Metrics",
            value=current_settings["show_response_metrics"],
            help="Display timing and token information after responses"
        )
        
        auto_scroll_chat = st.checkbox(
            "Auto-scroll Chat",
            value=current_settings["auto_scroll_chat"],
            help="Automatically scroll to latest message"
        )
    
    # Data Management Tab
    with tab4:
        st.subheader("Data Management")
        
        col1, col2 = st.columns(2)
        with col1:
            chat_retention_days = st.number_input(
                "Chat Retention (days)",
                min_value=1, max_value=3650,
                value=current_settings["chat_retention_days"],
                help="How long to keep chat history (0 = forever)"
            )
        with col2:
            max_backup_files = st.number_input(
                "Max Backup Files",
                min_value=5, max_value=100,
                value=current_settings["max_backup_files"]
            )
        
        auto_backup_enabled = st.checkbox(
            "Enable Automatic Backups",
            value=current_settings["auto_backup_enabled"]
        )
        
        if auto_backup_enabled:
            backup_frequency_hours = st.slider(
                "Backup Frequency (hours)",
                min_value=1, max_value=168,  # 1 week max
                value=current_settings["backup_frequency_hours"]
            )
        else:
            backup_frequency_hours = current_settings["backup_frequency_hours"]
    
    # Privacy & Security Tab
    with tab5:
        st.subheader("Privacy & Security")
        
        log_level = st.selectbox(
            "Log Level",
            options=["DEBUG", "INFO", "WARNING", "ERROR"],
            index=["DEBUG", "INFO", "WARNING", "ERROR"].index(current_settings["log_level"]),
            help="Amount of detail in application logs"
        )
        
        anonymize_logs = st.checkbox(
            "Anonymize Logs",
            value=current_settings["anonymize_logs"],
            help="Remove personal information from log files"
        )
        
        session_timeout_minutes = st.slider(
            "Session Timeout (minutes)",
            min_value=30, max_value=1440,  # 24 hours max
            value=current_settings["session_timeout_minutes"],
            help="Auto-logout after inactivity"
        )
    
    # Save Settings
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("💾 Save Settings", type="primary", use_container_width=True):
            # Collect all settings
            new_settings = {
                "default_model": default_model,
                "request_timeout": request_timeout,
                "max_retries": max_retries,
                "default_search_provider": search_provider,
                "search_result_count": search_result_count,
                "search_timeout": search_timeout,
                "theme": theme,
                "debug_panel_default": debug_panel_default,
                "show_response_metrics": show_response_metrics,
                "auto_scroll_chat": auto_scroll_chat,
                "chat_retention_days": chat_retention_days,
                "auto_backup_enabled": auto_backup_enabled,
                "backup_frequency_hours": backup_frequency_hours,
                "max_backup_files": max_backup_files,
                "log_level": log_level,
                "anonymize_logs": anonymize_logs,
                "session_timeout_minutes": session_timeout_minutes,
            }
            
            if settings_manager.save_settings(new_settings):
                st.success("✅ Settings saved successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to save settings")
    
    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            if settings_manager.reset_to_defaults():
                st.success("✅ Settings reset to defaults!")
                st.rerun()
            else:
                st.error("❌ Failed to reset settings")
    
    with col3:
        if st.button("📤 Export Settings", use_container_width=True):
            exported = settings_manager.export_settings()
            st.download_button(
                "Download settings.json",
                data=exported,
                file_name="ai_chat_mp_settings.json",
                mime="application/json"
            )