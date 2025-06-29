import streamlit as st
from pymongo import MongoClient
from time import time as current_time, sleep
import config
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import sys
import os
import json
import requests
from providers import ProviderManager, initialize_provider_manager, generate_chat_response_with_providers


st.set_page_config(
    page_title="AI Chat - Google Gemini",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
    )

ss = st.session_state

def brave_search(query: str, num_results: int = 3) -> str:
    try:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": ss.brave_api_key,
        }
        params = {
            "q": query,
            "count": num_results,
        }
        
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params,
        )

        if response.status_code != 200:
            error_msg = f"Error: Brave API returned status code {response.status_code} - {response.text}"
            return error_msg

        search_results = response.json()
        
        # Format the search results
        formatted_results = []

        if "web" in search_results and "results" in search_results["web"]:
            for i, result in enumerate(search_results["web"]["results"][:num_results]):
                title = result.get("title", "No title")
                link = result.get("url", "No link")
                snippet = result.get("description", "No snippet")
                formatted_results.append(f"[{i+1}] {title}\nURL: {link}\n{snippet}\n")

        return "\n".join(formatted_results) if formatted_results else "No results found."
    
    except Exception as e:
        error_msg = f"Error during Brave search: {str(e)}"
        return error_msg

def serper_search(query: str, num_results: int = 3) -> str:
    try:
        response = requests.get(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": ss.serper_api_key,
                "Content-Type": "application/json"
            },
            params={
                "q": query,
                "num": num_results
            }
        )
        if response.status_code != 200:
            error_msg = f"Error: Search API returned status code {response.status_code}"
            error(error_msg) # Log the error
            return error_msg
        
        search_results = response.json()
        
        # Format the search results
        formatted_results = []
        
        if "answerBox" in search_results:
            answer_box = search_results["answerBox"]
            title = answer_box.get("title", "")
            answer = answer_box.get("answer", "")
            snippet = answer_box.get("snippet", "")
            if title or answer or snippet:
                formatted_results.insert(0, f"[Featured] {title}\n{answer}\n{snippet}\n")
        
        if "knowledgeGraph" in search_results:
            kg = search_results["knowledgeGraph"]
            title = kg.get("title", "")
            description = kg.get("description", "")
            if title or description:
                formatted_results.insert(0, f"[Knowledge] {title}\n{description}\n")

        if "organic" in search_results:
            for i, result in enumerate(search_results["organic"][:num_results]):
                title = result.get("title", "No title")
                link = result.get("link", "No link")
                snippet = result.get("snippet", "No snippet")
                formatted_results.append(f"[{i+1}] {title}\nURL: {link}\n{snippet}\n")
        
        return "\n".join(formatted_results)
    except Exception as e:
        error_msg = f"Error during web search: {str(e)}"
        error(error_msg, exc_info=True) # Log the exception details
        return error_msg

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
    """Determine if a search is needed for the given prompt."""
    messages = [
        {"role": "user", "parts": [config.SEARCH_GROUNDING_SYSTEM_PROMPT, f"User message: {prompt}"]},
    ]
    
    try:
        response = ss.decision_model.generate_content(contents=messages)
        decision = json.loads(response.text)
        needs_search = decision.get("needs_search", False)
        reasoning = decision.get("reasoning", "No reasoning provided.")
        print(f"Search decision: {needs_search}, Reason: {reasoning}")
        return needs_search, "serper" # Defaulting to serper
    except Exception as e:
        st.error(f"Error in grounding decision: {e}")
        return False, ""

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
    
    # Keep decision model for search grounding
    genai.configure(api_key=ss.gemini_api_key)
    set_decision_model()


def generate_chat_response(search_results: Optional[str] = None):
    """Generates a chat response from the Gemini model."""
    messages = ss.active_chat.get("messages", [])
    system_prompt = ss.active_chat.get("system_prompt", "")
    
    if not messages:
        return "I'm ready to chat! What can I help you with?"

    # Construct the history for the API call
    api_history = []
    
    # Prepend the system prompt if it exists
    if system_prompt:
        api_history.append({"role": "user", "parts": [f"System Prompt: {system_prompt}"]})
        api_history.append({"role": "model", "parts": ["Understood. I will follow those instructions."]})

    # Add all previous messages
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        api_history.append({"role": role, "parts": [msg["content"]]})

    # Add search results as a new user message for context
    if search_results:
        api_history.append({
            "role": "user",
            "parts": [f"Here are the search results to help you answer:\n\n{search_results}"]
        })

    try:
        response = ss.gen_model.generate_content(api_history)
        return response.text
    except Exception as e:
        st.error(f"Error generating response: {e}")
        return "Sorry, I encountered an error while generating a response."

def get_friendly_time(seconds_ago):
    time_actions = {
        lambda d: d < 60: lambda d: "Just now",
        lambda d: d < 3600: lambda d: f"{int(d / 60)}m ago",
        lambda d: d < 86400: lambda d: f"{int(d / 3600)}h ago",
        lambda d: d < 172800: lambda d: "Yesterday",
        lambda d: d < 604800: lambda d: f"{int(d / 86400)}d ago",
        lambda d: d < 2592000: lambda d: f"{int(d / 604800)}w ago",
        lambda d: True: lambda d: "Long ago"
    }
    for condition, action in time_actions.items():
        if condition(seconds_ago):
            return action(seconds_ago)

def format_chat_for_radio(chat_doc):
    if not chat_doc: return "No chat selected"
    if chat_doc["name"] == "Scratch Pad": return "Scratch Pad"
    last_update = chat_doc.get("updated_at", current_time())
    seconds_ago = current_time() - last_update
    friendly_time = get_friendly_time(seconds_ago)
    return f"{chat_doc['name']} ({friendly_time})"

def make_chat_list():
    scratch_pad_filter = {"name": "Scratch Pad", "archived": False}
    projection = {"name": 1, "updated_at": 1, "_id": 1, "messages": 1, "model": 1, "system_prompt": 1}
    scratch_pad_doc = ss.db.chats.find_one(scratch_pad_filter, projection)
    other_chats_filter = {"name": {"$ne": "Scratch Pad"}, "archived": False}
    other_chats_cursor = ss.db.chats.find(
        other_chats_filter, 
        projection
    ).sort("updated_at", -1)
    other_chats_list = list(other_chats_cursor)
    final_chat_list = [scratch_pad_doc] if scratch_pad_doc else []
    final_chat_list.extend(other_chats_list)
    return final_chat_list

def show_notification(message, type="success"):
    icon = "✅" if type == "success" else "❌"
    st.toast(message, icon=icon)

def render_new():
    """Render the new chat creation form."""
    st.title("Create New Chat")
    
    with st.form("new_chat_form"):
        # Chat name input
        new_chat_name = st.text_input(
            "Chat Name",
            placeholder="Enter chat name...",
            help="Enter a unique name for your new chat"
        ).strip()
        
        # Model selection
        try:
            db_models = list(ss.db.models.find({}, {"name": 1, "provider": 1, "_id": 0}))
            available_models = [
                (f"{model['name']} ({model.get('provider', 'Unknown Provider')})", model['name'])
                for model in db_models
            ]
            available_models = available_models if db_models else []
        except Exception as e:
            st.error(f"Error fetching models: {str(e)}")
            available_models = []
        
        model_mapping = {m[0]: m[1] for m in available_models} if available_models else {}
        selected_display = st.selectbox(
            "Select Model",
            options=list(model_mapping.keys()) if model_mapping else ["No models available"],
            format_func=lambda x: x,
            help="Choose model - different models have different capabilities"
        )
        model = model_mapping.get(selected_display) if model_mapping else None
        
        # System prompt selection
        try:
            db_prompts = list(ss.db.prompts.find())
            available_prompts = [(p["name"], p["content"]) for p in db_prompts]
        except Exception as e:
            st.error(f"Error fetching prompts: {str(e)}")
            available_prompts = []
            
        selected_prompt = st.selectbox(
            "Select System Prompt",
            options=[p[0] for p in available_prompts],
            help="Choose the system prompt that defines how the AI should behave"
        )
        
        if selected_prompt:
            prompt_content = next((p[1] for p in available_prompts if p[0] == selected_prompt), "")
            st.text_area("System Prompt Content", value=prompt_content, disabled=True, height=150)

        # Form submission
        submitted = st.form_submit_button("Create Chat", use_container_width=True)

        if submitted:
            if not new_chat_name:
                st.error("Please enter a chat name")
            elif ss.db.chats.find_one({"name": new_chat_name}):
                st.error("A chat with this name already exists")
            else:
                current_time_val = current_time()
                system_prompt = next((p[1] for p in available_prompts if p[0] == selected_prompt), "")
                new_chat_data = {
                    "name": new_chat_name,
                    "model": model,
                    "framework": "gemini",
                    "system_prompt": system_prompt,
                    "messages": [],
                    "created_at": current_time_val,
                    "updated_at": current_time_val,
                    "archived": False
                }
                results = ss.db.chats.insert_one(new_chat_data)
                new_chat_doc = ss.db.chats.find_one({"_id": results.inserted_id})
                if new_chat_doc:
                    ss.active_chat = new_chat_doc
                    show_notification(f"Created and activated '{new_chat_doc['name']}'!", "success")
                    ss.app_mode = "chat"
                    st.rerun()
    
    # Cancel button
    cancelled = st.button("Cancel", use_container_width=True)
    if cancelled:
        ss.app_mode = "chat"
        st.rerun()

def render_chat():
    st.title(f"💬 {ss.active_chat['name']}")
    message_container = st.container(height=600, border=True)

    # Display existing messages
    if "messages" in ss.active_chat:
        for msg in ss.active_chat["messages"]:
            avatar = ss.llm_avatar if msg["role"] == "assistant" else ss.user_avatar
            with message_container.chat_message(msg["role"], avatar=avatar):
                if "search_results" in msg:
                    with st.expander("🔍 View Search Results"):
                        st.markdown(msg["search_results"])
                st.markdown(msg["content"])

    # Handle new user input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to session state and display it
        user_message = {"role": "user", "content": prompt, "timestamp": current_time()}
        ss.active_chat["messages"].append(user_message)
        with message_container.chat_message("user", avatar=ss.user_avatar):
            st.markdown(prompt)

        # Determine if a search is needed
        needs_search, search_provider = apply_grounding(prompt)
        search_results_text = None

        if needs_search:
            with st.spinner(f"Searching with {search_provider.capitalize()}..."):
                if search_provider == 'brave':
                    search_results_text = brave_search(prompt)
                else:
                    search_results_text = serper_search(prompt)
        
        # Generate the AI response
        with st.spinner("🤖 Thinking..."):
            response_text = generate_chat_response_with_providers(search_results=search_results_text)

        # Display the AI response
        with message_container.chat_message("assistant", avatar=ss.llm_avatar):
            if search_results_text:
                with st.expander("🔍 View Search Results"):
                    st.markdown(search_results_text)
            st.markdown(response_text)
        
        # Add AI message to session state
        assistant_message = {
            "role": "assistant",
            "content": response_text,
            "timestamp": current_time()
        }
        if search_results_text:
            assistant_message["search_results"] = search_results_text
        ss.active_chat["messages"].append(assistant_message)

        # Update the database
        ss.db.chats.update_one(
            {"_id": ss.active_chat["_id"]},
            {
                "$set": {
                    "messages": ss.active_chat["messages"],
                    "updated_at": current_time()
                }
            }
        )
        st.rerun()

def render_clear():
    # ================ Clear Chat Messages ================
    ss.db.chats.update_one(
        {"_id": ss.active_chat["_id"]},
        {"$set": {"messages": [], "updated_at": current_time()}}
    )
    ss.active_chat = ss.db.chats.find_one({"_id": ss.active_chat["_id"]})
    show_notification("Chat cleared successfully", "success")
    ss.app_mode = "chat"
    st.rerun()

def render_delete():
    if ss.active_chat['name'] == "Scratch Pad":
        show_notification("Cannot delete the default Scratch Pad chat", "error")
    else:
        # ================ Delete Chat ================
        ss.db.chats.delete_one({"_id": ss.active_chat["_id"]})
        ss.active_chat = ss.db.chats.find_one({"name": "Scratch Pad"})
        show_notification("Chat deleted successfully", "success")
    ss.app_mode = "chat"
    st.rerun()

def render_archive():
    st.markdown("### Archive Management 📂")
    st.markdown("Toggle archive status for your chats. Archived chats won't appear in the sidebar.")
    st.divider()
    
    all_chats = list(ss.db.chats.find({
        "name": {"$nin": ["Scratch Pad", ss.active_chat.get('name', '')]},
        "model": {"$regex": "gemini", "$options": "i"}
    }).sort("updated_at", -1))
    
    if not all_chats:
        st.info("No other chats available to archive.")
        return
    
    for chat in all_chats:
        col1, col2, col3 = st.columns([3, 3, 2])
        archived_status = chat.get('archived', False)
        with col1:
            st.markdown(f"**Chat Name:** :blue[{chat['name']}]")
        with col2:
            st.markdown(f"**Archived:** :blue[{archived_status}]")
        with col3:
            toggle = st.checkbox("Archived", value=archived_status, key=f"toggle_{chat['name']}", help="Check to archive this chat")
            if toggle != archived_status:
                ss.db.chats.update_one({"_id": chat["_id"]}, {"$set": {"archived": toggle}})
                st.rerun()

def render_models():
    st.markdown("### Model Management 🤖")
    
    # Horizontal radio button for model actions
    model_action = st.radio(
        "Select Model Action", 
        ["Add", "Edit", "Delete"], 
        horizontal=True
    )
    
    # Add Model functionality
    if model_action == "Add":
        with st.form("add_model_form", clear_on_submit=True):
            # Basic Model Information
            model_name = st.text_input("Model Name", placeholder="Enter model name...")
            
            # Provider selection
            provider_options = ["google", "anthropic"]
            selected_provider = st.selectbox("Provider", provider_options)
            
            # Model Capabilities
            col1, col2 = st.columns(2)
            with col1:
                text_input = st.checkbox("Text Input", value=True)
                image_input = st.checkbox("Image Input")
                text_output = st.checkbox("Text Output", value=True)
                image_output = st.checkbox("Image Output")
            
            with col2:
                tools = st.checkbox("Tools")
                functions = st.checkbox("Functions")
                thinking = st.checkbox("Thinking")
                native_grounding = st.checkbox("Native Grounding")
            
            # Model Parameters
            col3, col4 = st.columns(2)
            with col3:
                temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
                top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=0.9, step=0.05)
            
            with col4:
                max_input_tokens = st.number_input("Max Input Tokens", min_value=0, value=131072)
                max_output_tokens = st.number_input("Max Output Tokens", min_value=0, value=8192)
            
            # Pricing
            col5, col6 = st.columns(2)
            with col5:
                input_price = st.number_input("Input Price (per million tokens)", min_value=0.0, value=2.0, format="%.2f")
            
            with col6:
                output_price = st.number_input("Output Price (per million tokens)", min_value=0.0, value=10.0, format="%.2f")
            
            submitted = st.form_submit_button("Add Model")
            
            if submitted:
                if not model_name:
                    st.error("Model Name is required!")
                else:
                    # Prepare model document
                    new_model = {
                        "name": model_name,
                        "provider": selected_provider,  # Use provider instead of framework
                        "temperature": temperature,
                        "top_p": top_p,
                        "input_price": input_price,
                        "output_price": output_price,
                        "text_input": text_input,
                        "image_input": image_input,
                        "text_output": text_output,
                        "image_output": image_output,
                        "tools": tools,
                        "functions": functions,
                        "thinking": thinking,
                        "native_grounding": native_grounding,
                        "max_output_tokens": max_output_tokens,
                        "max_input_tokens": max_input_tokens,
                        "created_at": current_time()
                    }
                    
                    # Check if model already exists
                    existing_model = ss.db.models.find_one({"name": model_name})
                    if existing_model:
                        st.error(f"Model '{model_name}' already exists!")
                    else:
                        # Insert new model
                        ss.db.models.insert_one(new_model)
                        st.success(f"Model '{model_name}' added successfully!")
                        st.balloons()
                        # Show message for 2 seconds before refresh
                        sleep(2)
                        st.rerun()
    
    # Edit Model functionality - Step 1: Select Model
    if model_action == "Edit":
        available_models = list(ss.db.models.find({}, {"name": 1, "_id": 0}))
        
        if not available_models:
            st.warning("No models available for editing.")
            return
            
        model_display_names = [model["name"] for model in available_models]
        model_name_map = {name: name for name in model_display_names}
            
        selected_display = st.selectbox(
            "Select a model to edit:",
            options=model_display_names,
            index=0,
            key="selected_model_display"
        )
        
        if st.button("Edit Selected Model"):
            ss.edit_model_name = model_name_map[selected_display]
            ss.edit_model_data = ss.db.models.find_one({"name": ss.edit_model_name})
            st.rerun()
            return
            
    # Step 2: Edit Form
    if 'edit_model_data' in ss and ss.edit_model_data is not None:
        current_model = ss.edit_model_data
        model_to_edit = ss.edit_model_name
        
        with st.form("edit_model_form"):
            # Model Capabilities
            st.subheader("Model Capabilities")
            col1, col2 = st.columns(2)
            with col1:
                text_input = st.checkbox("Text Input", value=current_model.get("text_input", False))
                image_input = st.checkbox("Image Input", value=current_model.get("image_input", False))
                text_output = st.checkbox("Text Output", value=current_model.get("text_output", True))
                image_output = st.checkbox("Image Output", value=current_model.get("image_output", False))
            
            with col2:
                tools = st.checkbox("Tools", value=current_model.get("tools", False))
                functions = st.checkbox("Functions", value=current_model.get("functions", False))
                thinking = st.checkbox("Thinking", value=current_model.get("thinking", False))
                native_grounding = st.checkbox("Native Grounding", value=current_model.get("native_grounding", False))
            
            # Model Parameters
            st.subheader("Model Parameters")
            col3, col4 = st.columns(2)
            with col3:
                temperature = st.slider(
                    "Temperature", 
                    min_value=0.0, 
                    max_value=1.0, 
                    value=current_model.get("temperature", 0.7), 
                    step=0.05
                )
                top_p = st.slider(
                    "Top P", 
                    min_value=0.0, 
                    max_value=1.0, 
                    value=current_model.get("top_p", 0.9), 
                    step=0.05
                )
            
            with col4:
                max_input_tokens = st.number_input(
                    "Max Input Tokens", 
                    min_value=0, 
                    value=current_model.get("max_input_tokens", 4096)
                )
                max_output_tokens = st.number_input(
                    "Max Output Tokens", 
                    min_value=0, 
                    value=current_model.get("max_output_tokens", 4096)
                )
            
            # Pricing
            st.subheader("Pricing")
            col5, col6 = st.columns(2)
            with col5:
                input_price = st.number_input(
                    "Input Price (per million tokens)", 
                    min_value=0.0, 
                    value=current_model.get("input_price", 0.0), 
                    format="%.2f"
                )
            
            with col6:
                output_price = st.number_input(
                    "Output Price (per million tokens)", 
                    min_value=0.0,
                    value=current_model.get("output_price", 0.0),
                    format="%.2f"
                )
            
            # Form actions
            col7, col8 = st.columns(2)
            with col7:
                if st.form_submit_button("Update Model"):
                    # Update model document
                    update_data = {
                        "framework": "gemini",
                        "temperature": temperature,
                        "top_p": top_p,
                        "input_price": input_price,
                        "output_price": output_price,
                        "text_input": text_input,
                        "image_input": image_input,
                        "text_output": text_output,
                        "image_output": image_output,
                        "tools": tools,
                        "functions": functions,
                        "thinking": thinking,
                        "native_grounding": native_grounding,
                        "max_output_tokens": max_output_tokens,
                        "max_input_tokens": max_input_tokens,
                        "updated_at": current_time()
                    }

                    # ================ Update Model ================
                    ss.db.models.update_one(
                        {"name": model_to_edit},
                        {"$set": update_data}
                    )
                    st.success(f"Model '{model_to_edit}' updated successfully!")
                    st.balloons()
                    ss.edit_model_name = None
                    ss.edit_model_data = None
                    st.rerun()
            
            with col8:
                if st.form_submit_button("Cancel"):
                    # ================ Cancel Model Edit ================
                    ss.edit_model_name = None
                    ss.edit_model_data = None
                    st.rerun()
    
    # Delete Model 
    if model_action == "Delete":
        # Get the scratch pad's model to protect it
        scratch_pad_chat = ss.db.chats.find_one({"name": "Scratch Pad"})
        scratch_pad_model = scratch_pad_chat.get("model") if scratch_pad_chat else None
        
        # Retrieve all models except protected ones
        protected_models = [DEFAULT_MODEL, DECISION_MODEL]
        if scratch_pad_model:
            protected_models.append(scratch_pad_model)
        
        # Remove duplicates
        protected_models = list(set(protected_models))
        
        available_models = list(ss.db.models.find(
            {"name": {"$nin": protected_models}}, 
            {"name": 1, "_id": 0}
        ))
        
        if not available_models:
            st.warning("No models available for deletion. All models are protected.")
        else:
            model_display_names = [model['name'] for model in available_models]
            model_name_map = {name: name for name in model_display_names}
            
            with st.form("delete_model_form", clear_on_submit=True):
                selected_display = st.selectbox(
                    "Select Model to Delete", 
                    model_display_names,
                    help=f"Protected models: {', '.join(protected_models)}"
                )
                model_to_delete = model_name_map[selected_display]
                
                submitted = st.form_submit_button("Delete Model")
                
                if submitted:
                    # Double-check protection (belt and suspenders)
                    if model_to_delete in protected_models:
                        st.error(f"Cannot delete protected model '{model_to_delete}'.")
                    else:
                        # Perform deletion
                        result = ss.db.models.delete_one({"name": model_to_delete})
                        
                        if result.deleted_count > 0:
                            # Clear any edit state if the deleted model was being edited
                            if ss.get('edit_model_name') == model_to_delete:
                                ss.edit_model_name = None
                                ss.edit_model_data = None
                            # Show success message and animation
                            st.success(f"Model '{model_to_delete}' deleted successfully!")
                            st.balloons()
                            # Show message for 2 seconds before refresh
                            sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Could not delete model '{model_to_delete}'.")

def manage_UI():
    st.sidebar.markdown("### :blue[Active Chat] 🎯")
    st.sidebar.markdown(f"**Chat Name:** :blue[{ss.active_chat.get('name', 'N/A')}]")
    st.sidebar.markdown(f"**Model:** :blue[{ss.active_chat.get('model', 'N/A')}]")
    
    # Search provider selection is now handled automatically by apply_grounding()
    # Keeping the code commented in case we want to re-enable manual selection later
    # if hasattr(ss, 'serper_api_key') and hasattr(ss, 'brave_api_key') and ss.serper_api_key and ss.brave_api_key:
    #     st.sidebar.divider()
    #     st.sidebar.markdown("### Search Provider")
    #     
    #     # Define available search providers with display names and values
    #     search_providers = [
    #         ("Serper", 'serper'),
    #         ("Brave Search", 'brave')
    #     ]
    #     
    #     # Get current provider, default to 'serper' if not set
    #     current_provider = ss.get('search_provider', 'serper')
    #     
    #     # Create radio buttons for provider selection
    #     selected_provider = st.sidebar.radio(
    #         "Select search provider",
    #         options=[val for name, val in search_providers],
    #         format_func=lambda x: next(name for name, val in search_providers if val == x),
    #         index=next((i for i, (_, val) in enumerate(search_providers) if val == current_provider), 0),
    #         help="Choose which search provider to use for web searches"
    #     )
    #     ss.search_provider = selected_provider
    st.sidebar.divider()

    col1, col2, col3 = st.sidebar.columns(3)
    if col1.button("💬", help="Chat with Gemini", use_container_width=True): ss.app_mode = "chat"
    if col2.button("🧹", help="Clear active chat history", use_container_width=True): ss.app_mode = "clear_chat"
    if col3.button("🗑️", help="Delete active chat", use_container_width=True): ss.app_mode = "delete_chat"

    colA, colB, colC = st.sidebar.columns(3)
    if colA.button("🆕", help="New chat", use_container_width=True): ss.app_mode = "new_chat"
    if colB.button("⚙️", help="Manage models", use_container_width=True): ss.app_mode = "models"
    if colC.button("📂", help="Manage chat archiving", use_container_width=True): ss.app_mode = "archive"

    chat_docs_for_options = make_chat_list()
    st.sidebar.markdown("### Select Chat")
    
    try:
        chat_names = [chat['name'] for chat in chat_docs_for_options]
        default_index = chat_names.index(ss.active_chat['name'])
    except (ValueError, KeyError, AttributeError):
        default_index = 0

    def handle_chat_selection():
        print(f"DEBUG: Chat selection triggered")
        print(f"DEBUG: Selected chat name: {ss.chat_selector_name}")
        print(f"DEBUG: Current active_chat before change: {ss.active_chat.get('name', 'None') if ss.active_chat else 'None'}")
        
        ss.app_mode = "chat"
        # Find the selected chat from the list
        selected_chat_name = ss.chat_selector_name
        for chat in chat_docs_for_options:
            if chat['name'] == selected_chat_name:
                print(f"DEBUG: Found chat document: {chat.keys()}")
                print(f"DEBUG: Chat has messages field: {'messages' in chat}")
                ss.active_chat = chat
                break
    
    print(f"DEBUG: Active chat after change: {ss.active_chat.get('name', 'None') if ss.active_chat else 'None'}")

    st.sidebar.radio(
        "Available Chats", options=[doc['name'] for doc in chat_docs_for_options], 
        format_func=lambda name: next(format_chat_for_radio(doc) for doc in chat_docs_for_options if doc['name'] == name),
        index=default_index, key="chat_selector_name", on_change=handle_chat_selection,
        label_visibility="collapsed"
    )
    
def main():
    try:
        # Initialize the application if not already initialized
        if "initialized" not in ss:
            initialize()

        # Define page renderers
        page_renderer = {
            "chat": render_chat,
            "new_chat": render_new,
            "clear_chat": render_clear,
            "delete_chat": render_delete,
            "archive": render_archive,
            "models": render_models,
        }

        # Render the main UI components
        manage_UI()
        
        # Render the current page
        current_page = ss.get('app_mode', 'chat')
        page_renderer.get(current_page, render_chat)()
        
    except Exception as e:
        # Log the full exception with traceback
        import traceback
        print(f"Unhandled exception in main: {e}")
        
        # User-friendly error message
        st.error(f"An unexpected error occurred: {e}")
        
        # Show more detailed error in debug mode
        print(f"Error in main: {e}")
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