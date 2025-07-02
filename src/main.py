import streamlit as st
from pymongo import MongoClient
from datetime import datetime
from time import time as current_time
from typing import Optional
import pytz
import config
import google.generativeai as genai
import json
from logger import logger
from providers import initialize_provider_manager, generate_chat_response_with_providers
from query_optimizer import optimize_search_query
from search_manager import SearchManager
import ui
from ui import (
    render_chat,
    render_new,
    render_clear,
    render_delete,
    render_archive,
    render_models,
    manage_UI,
)

st.set_page_config(
    page_title="AI Chat - Google Gemini",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

ss = st.session_state

def get_database():
    """Connects to MongoDB using credentials from config.py"""
    try:
        client = MongoClient(
            config.MONGO_LOCAL_URI,
            maxPoolSize=50,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            retryWrites=True
        )
        client.server_info()
        return client[config.MONGO_LOCAL_DB_NAME]
    except Exception as e:
        st.error(f"❌ Failed to connect to MongoDB: {e}")
        st.error(f"Please ensure MongoDB is running and accessible at {config.MONGO_LOCAL_URI}")
        st.stop()

def set_gen_model():
    model_name = ss.active_chat['model']
    model_config = ss.db.models.find_one({"name": model_name})
    ss.gen_model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": model_config["temperature"],
                "top_p": model_config["top_p"],
                "max_output_tokens": model_config.get("max_output_tokens")
            }
        )

def set_decision_model():
    """Initialize and set the decision model for search grounding."""
    ss.decision_model = genai.GenerativeModel(
        config.DECISION_MODEL,
        generation_config={
            "temperature": 0.2,
            "max_output_tokens": 200,
            "response_mime_type": "application/json"
        }
    )

def apply_grounding(prompt: str) -> tuple[bool, str]:
    """Determine if a search is needed for the given prompt and which provider to use."""
    messages = [
        {"role": "user", "parts": [config.SEARCH_GROUNDING_SYSTEM_PROMPT, f"User message: {prompt}"]},
    ]
    
    try:
        response = ss.decision_model.generate_content(contents=messages)
        decision = json.loads(response.text)
        needs_search = decision.get("needs_search", False)
        # Default to 'serper' if not specified
        search_provider = decision.get("search_provider", "serper").lower()
        # Ensure we only return valid providers
        if search_provider not in ["serper", "brave"]:
            search_provider = "serper"
        reasoning = decision.get("reasoning", "No reasoning provided.")
        logger.debug(f"Search decision: {needs_search}, Provider: {search_provider}, Reason: {reasoning}")
        return needs_search, search_provider
    except Exception as e:
        logger.error(f"Error in grounding decision: {e}")
        return True, "serper"  # Default to serper on error

def initialize():
    # ================ Session State Initialization ================
    ss.initialized = True
    ss.app_mode = "chat"
    ss.gemini_api_key = st.secrets.get("GEMINI_API_KEY")
    ss.serper_api_key = st.secrets.get("SERPER_API_KEY")
    ss.brave_api_key = st.secrets.get("BRAVE_API_KEY")       
    ss.db = get_database()
    ss.chats = list(ss.db.chats.find({"archived": False}))

    ss.active_chat = ss.db.chats.find_one({"name": "Scratch Pad"})
    if ss.active_chat and "timezone" not in ss.active_chat:
        # Set default timezone to user's local timezone or fallback to UTC
        try:
            import tzlocal
            default_tz = tzlocal.get_localzone().zone
        except:
            default_tz = "UTC"
            
        ss.db.chats.update_one(
            {"_id": ss.active_chat["_id"]},
            {"$set": {"timezone": default_tz}}
        )
        ss.active_chat["timezone"] = default_tz
    
    ss.llm_avatar = config.LLM_AVATAR
    ss.user_avatar = config.USER_AVATAR
    ss.models = list(ss.db.models.find())
    
    # Initialize provider manager instead of individual model setup
    initialize_provider_manager()
    
    # Keep decision model for search grounding
    genai.configure(api_key=ss.gemini_api_key)
    set_decision_model()
    ss.apply_grounding = apply_grounding


def get_temporal_context(timezone: str = "UTC") -> str:
    """Generate a temporal context string with timezone support.
    
    Args:
        timezone: Timezone string (e.g., 'America/New_York')
        
    Returns:
        Formatted string with current date/time information
    """
    try:
        # Get timezone object, default to UTC if invalid
        tz = pytz.timezone(timezone) if timezone in pytz.all_timezones else pytz.UTC
    except Exception:
        tz = pytz.UTC
        
    now = datetime.now(tz)
    
    # Format the temporal information
    return (
        f"Current Date and Time: {now.strftime('%Y-%m-%d %H:%M:%S')} ({tz.zone})\n"
        f"Day of Week: {now.strftime('%A')}\n"
        f"Day of Year: {now.strftime('%j')}\n"
        f"Week of Year: {now.strftime('%U')}\n"
        f"Timezone: {tz.zone} (UTC{now.strftime('%z')})\n"
        f"Is DST: {'Yes' if now.dst() else 'No'}"
    )

def generate_chat_response(search_results: Optional[str] = None):
    """Generates a chat response from the selected model."""
    messages = ss.active_chat.get("messages", [])
    model_config = ss.db.models.find_one({"name": ss.active_chat['model']})
    
    if not messages:
        return "I'm ready to chat! What can I help you with?"
    
    if not model_config:
        return "Error: Model configuration not found."

    try:
        # Get temporal context with timezone support
        user_timezone = ss.active_chat.get("timezone", "UTC")
        temporal_context = get_temporal_context(user_timezone)
        
        # Add temporal context to system prompt
        model_config = model_config.copy()  # Create a copy to avoid modifying the original
        system_prompt = model_config.get("system_prompt", "") + f"\n\nTemporal Context:\n{temporal_context}"
        model_config["system_prompt"] = system_prompt
        
        # Generate response using the provider system
        response = generate_chat_response_with_providers(search_results)
        return response
        
    except Exception as e:
        st.error(f"Error generating response: {e}")
        return "Sorry, I encountered an error while generating a response."






















    
def main():
    try:
        # Initialize the application if not already initialized
        if "initialized" not in ss:
            initialize()

        # Define page renderers
        page_renderer = {
            "chat": lambda: ui.render_chat(
                ss.db,
                ss.provider_manager,
                SearchManager(),
                apply_grounding,
                optimize_search_query,
                generate_chat_response_with_providers,
            ),
            "new_chat": lambda: ui.render_new(ss.db, ss.provider_manager),
            "clear_chat": lambda: ui.render_clear(ss.db),
            "delete_chat": lambda: ui.render_delete(ss.db),
            "archive": lambda: ui.render_archive(ss.db),
            "models": lambda: ui.render_models(ss.db),
        }

        # Render the main UI components
        ui.manage_UI(ss.db)
        
        # Render the current page
        current_page = ss.get('app_mode', 'chat')
        page_renderer.get(current_page, ui.render_chat)()
        
    except Exception as e:
        # Log the full exception with traceback
        import traceback
        logger.exception("Unhandled exception in main")
        
        # User-friendly error message
        st.error(f"An unexpected error occurred: {e}")
        
        # Show more detailed error in debug mode
        logger.error(f"Error in main: {e}")
        with st.expander("Error Details", expanded=False):
            st.code(traceback.format_exc(), language='python')
                
            # Add debug info
            st.write("### Debug Information")
            st.json({
                "app_mode": ss.get('app_mode', 'N/A'),
                "active_chat": ss.get('active_chat', {}).get('name', 'N/A') if ss.get('active_chat') else 'N/A',
                "messages_count": len(ss.get('active_chat', {}).get('messages', [])) if ss.get('active_chat') else 0
            })

if __name__ == "__main__":
    main()