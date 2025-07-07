import streamlit as st
from pymongo import MongoClient
from datetime import datetime
from time import time as current_time
from typing import Optional
import config
import google.generativeai as genai
import json
from logger import logger
from providers import initialize_provider_manager, generate_chat_response_with_providers
from query_optimizer import optimize_search_query
from search_manager import SearchManager
from llm_intelligent_router import llm_intelligent_router as intelligent_router, RouteType
from debug_utils import add_debug_log, clear_debug_logs
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
from settings import render_settings

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

def apply_intelligent_routing(prompt: str) -> tuple[bool, str, str]:
    """Use intelligent router to determine the best approach for the query."""
    try:
        # Log the user question first
        add_debug_log("=" * 60)
        add_debug_log(f"❓ User Question: {prompt}")
        add_debug_log("=" * 60)
        
        # Get routing decision
        decision = intelligent_router.make_routing_decision(prompt)
        
        # Log to debug panel
        add_debug_log(f"🧠 Router Decision: {decision.route_type.value}")
        add_debug_log(f"🔧 Primary Tool: {decision.primary_tool or 'None'}")
        add_debug_log(f"📊 Confidence: {decision.confidence:.2f}")
        add_debug_log(f"💭 Reasoning: {decision.reasoning}")
        
        # Also log to regular logger
        logger.debug(f"Intelligent routing decision: {decision.route_type.value}")
        logger.debug(f"Primary tool: {decision.primary_tool}, Confidence: {decision.confidence:.2f}")
        logger.debug(f"Reasoning: {decision.reasoning}")
        
        # Check model capabilities for tool routing
        model_config = ss.db.models.find_one({"name": ss.active_chat['model']})
        model_capabilities = model_config.get("capabilities", []) if model_config else []
        
        # Convert routing decision to search parameters with capability awareness
        if decision.route_type == RouteType.SEARCH_FIRST:
            add_debug_log("🔍 Action: Search first, then maybe tools")
            return True, "serper", "search_first"
        elif decision.route_type == RouteType.TOOL_WITH_SEARCH:
            add_debug_log("🔍🔧 Action: Use tool but verify with search")
            return True, "serper", "tool_with_search"
        elif decision.route_type == RouteType.TOOL_DIRECT:
            # Check if model can actually handle function calling
            if "function_calling" in model_capabilities:
                add_debug_log("🔧 Action: Use tool directly (model supports function calling)")
                return False, "", "tool_direct"
            else:
                add_debug_log("⚠️ Model lacks function calling - fallback to search + context")
                return True, "serper", "tool_fallback_search"
        elif decision.route_type == RouteType.MODEL_KNOWLEDGE:
            add_debug_log("🤖 Action: Use model knowledge, no search or tools")
            return False, "", "model_knowledge"
        else:
            add_debug_log("🔄 Action: Fallback to combined approach")
            return False, "", "combined"
            
    except Exception as e:
        add_debug_log(f"❌ Router Error: {e}")
        logger.error(f"Error in intelligent routing: {e}")
        return False, "", "error_fallback"  # Default to no search on error

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
    
    ss.llm_avatar = config.LLM_AVATAR
    ss.user_avatar = config.USER_AVATAR
    ss.models = list(ss.db.models.find())
    
    # Initialize provider manager instead of individual model setup
    initialize_provider_manager()
    
    # Keep decision model for search grounding (legacy, now using intelligent router)
    genai.configure(api_key=ss.gemini_api_key)
    set_decision_model()
    ss.apply_intelligent_routing = apply_intelligent_routing



def generate_chat_response(search_results: Optional[str] = None):
    """Generates a chat response from the selected model with metrics."""
    try:
        # Generate response using the provider system (returns structured object)
        response_obj = generate_chat_response_with_providers(search_results)
        
        # Extract text for backward compatibility
        if isinstance(response_obj, dict) and "text" in response_obj:
            return response_obj["text"]
        else:
            # Fallback for old format
            return response_obj
        
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
                apply_intelligent_routing,
                optimize_search_query,
                generate_chat_response_with_providers,
            ),
            "new_chat": lambda: ui.render_new(ss.db, ss.provider_manager),
            "clear_chat": lambda: ui.render_clear(ss.db),
            "delete_chat": lambda: ui.render_delete(ss.db),
            "archive": lambda: ui.render_archive(ss.db),
            "models": lambda: ui.render_models(ss.db),
            "debug": lambda: ui.render_debug_panel(),
            "profile": lambda: ui.render_profile(),
            "settings": lambda: render_settings(),
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