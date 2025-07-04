import streamlit as st
from time import time as current_time, sleep
from logger import logger
from utils import format_response_metrics
from debug_utils import add_debug_log
import debug_panel
import config

def show_notification(message, type="success"):
    icon = "✅" if type == "success" else "❌"
    st.toast(message, icon=icon)

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

def render_new(db, provider_manager):
    """Render the new chat creation form."""
    st.title("Create New Chat")
    
    with st.form("new_chat_form"):
        new_chat_name = st.text_input(
            "Chat Name",
            placeholder="Enter chat name...",
            help="Enter a unique name for your new chat"
        ).strip()
        
        try:
            db_models = list(db.models.find({}, {"name": 1, "provider": 1, "_id": 0}))
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
        
        try:
            db_prompts = list(db.prompts.find())
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

        submitted = st.form_submit_button("Create Chat", use_container_width=True)

        if submitted:
            if not new_chat_name:
                st.error("Please enter a chat name")
            elif db.chats.find_one({"name": new_chat_name}):
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
                results = db.chats.insert_one(new_chat_data)
                new_chat_doc = db.chats.find_one({"_id": results.inserted_id})
                if new_chat_doc:
                    st.session_state.active_chat = new_chat_doc
                    show_notification(f"Created and activated '{new_chat_doc['name']}'!", "success")
                    st.session_state.app_mode = "chat"
                    st.rerun()
    
    cancelled = st.button("Cancel", use_container_width=True)
    if cancelled:
        st.session_state.app_mode = "chat"
        st.rerun()

def render_chat(db, provider_manager, search_manager, apply_intelligent_routing, optimize_search_query, generate_chat_response_with_providers):
    st.title(f"💬 {st.session_state.active_chat['name']}")
    message_container = st.container(height=600, border=True)

    if "messages" in st.session_state.active_chat:
        for msg in st.session_state.active_chat["messages"]:
            avatar = st.session_state.llm_avatar if msg["role"] == "assistant" else st.session_state.user_avatar
            with message_container.chat_message(msg["role"], avatar=avatar):
                if "search_results" in msg:
                    with st.expander("🔍 View Search Results"):
                        st.markdown(msg["search_results"])
                st.markdown(msg["content"])

    if prompt := st.chat_input("Type your message here..."):
        # Clear previous response metrics before new message
        if hasattr(st.session_state, 'last_response_metrics'):
            delattr(st.session_state, 'last_response_metrics')
        
        user_message = {"role": "user", "content": prompt, "timestamp": current_time()}
        st.session_state.active_chat["messages"].append(user_message)
        with message_container.chat_message("user", avatar=st.session_state.user_avatar):
            st.markdown(prompt)

        needs_search, search_provider, routing_type = apply_intelligent_routing(prompt)
        search_results_text = None

        if needs_search:
            add_debug_log(f"🔍 Search initiated for: '{prompt[:50]}...'")
            
            with st.spinner(f"Optimizing search query..."):
                optimized_prompt = optimize_search_query(prompt)
                logger.debug(f"Original query: {prompt} -> Optimized: {optimized_prompt}")
                add_debug_log(f"📝 Query optimized: '{optimized_prompt[:50]}...'")
                
            with st.spinner("Searching for best results..."):
                search_results, score, engine_used = search_manager.search_with_fallback(optimized_prompt)
                add_debug_log(f"🔍 Search engine: {engine_used}, Score: {score:.1f}/10")
                
                if score < 3.0:
                    logger.debug("Poor search results, trying original query")
                    add_debug_log("⚠️ Poor results, retrying with original query")
                    search_results, score, engine_used = search_manager.search_with_fallback(prompt)
                    add_debug_log(f"🔄 Retry result: {engine_used}, Score: {score:.1f}/10")
                
                logger.info(f"Best result from {engine_used} with score {score:.1f}/10")
                search_results_text = search_results if score > 2.0 else "No relevant search results found."
                add_debug_log(f"✅ Search completed: {'Results found' if score > 2.0 else 'No relevant results'}")
        
        with st.spinner("🤖 Thinking..."):
            add_debug_log("🤖 Generating AI response...")
            response_obj = generate_chat_response_with_providers(search_results=search_results_text)
            add_debug_log("✅ AI response generated successfully")

        # Handle structured response format
        if isinstance(response_obj, dict) and "text" in response_obj:
            response_text = response_obj["text"]
        else:
            # Fallback for old format
            response_text = response_obj
        
        # Log the AI response to debug panel
        add_debug_log(f"🤖 AI Response: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
        
        # Log response metrics if available
        if isinstance(response_obj, dict) and response_obj.get("metrics"):
            metrics = response_obj["metrics"]
            add_debug_log(f"⚡ Response Time: {metrics.get('response_time', 0):.2f}s")
            add_debug_log(f"📊 Tokens: {metrics.get('input_tokens', 0)} in, {metrics.get('output_tokens', 0)} out")
        
        add_debug_log("=" * 60)

        with message_container.chat_message("assistant", avatar=st.session_state.llm_avatar):
            if search_results_text:
                with st.expander("🔍 View Search Results"):
                    st.markdown(search_results_text)
            st.markdown(response_text)
        
        assistant_message = {
            "role": "assistant",
            "content": response_text,
            "timestamp": current_time()
        }
        if search_results_text:
            assistant_message["search_results"] = search_results_text
        st.session_state.active_chat["messages"].append(assistant_message)

        db.chats.update_one(
            {"_id": st.session_state.active_chat["_id"]},
            {
                "$set": {
                    "messages": st.session_state.active_chat["messages"],
                    "updated_at": current_time()
                }
            }
        )
        st.rerun()

    # Display response metrics outside the message container (ephemeral)
    if hasattr(st.session_state, 'last_response_metrics') and st.session_state.last_response_metrics:
        metrics_text = format_response_metrics(st.session_state.last_response_metrics)
        st.info(metrics_text)

def render_clear(db):
    db.chats.update_one(
        {"_id": st.session_state.active_chat["_id"]},
        {"$set": {"messages": [], "updated_at": current_time()}}
    )
    st.session_state.active_chat = db.chats.find_one({"_id": st.session_state.active_chat["_id"]})
    show_notification("Chat cleared successfully", "success")
    st.session_state.app_mode = "chat"
    st.rerun()

def render_delete(db):
    if st.session_state.active_chat['name'] == "Scratch Pad":
        show_notification("Cannot delete the default Scratch Pad chat", "error")
    else:
        db.chats.delete_one({"_id": st.session_state.active_chat["_id"]})
        st.session_state.active_chat = db.chats.find_one({"name": "Scratch Pad"})
        show_notification("Chat deleted successfully", "success")
    st.session_state.app_mode = "chat"
    st.rerun()

def render_archive(db):
    st.markdown("### Archive Management 📂")
    st.markdown("Toggle archive status for your chats. Archived chats won't appear in the sidebar.")
    st.divider()
    
    all_chats = list(db.chats.find({
        "name": {"$nin": ["Scratch Pad", st.session_state.active_chat.get('name', '')]},
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
                db.chats.update_one({"_id": chat["_id"]}, {"$set": {"archived": toggle}})
                st.rerun()

def render_models(db):
    st.markdown("### Model Management 🤖")
    
    model_action = st.radio(
        "Select Model Action", 
        ["Add", "Edit", "Delete"], 
        horizontal=True
    )
    
    if model_action == "Add":
        with st.form("add_model_form", clear_on_submit=True):
            model_name = st.text_input("Model Name", placeholder="Enter model name...")
            provider_options = ["google", "anthropic"]
            selected_provider = st.selectbox("Provider", provider_options)
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
            col3, col4 = st.columns(2)
            with col3:
                temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
                top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=0.9, step=0.05)
            with col4:
                max_input_tokens = st.number_input("Max Input Tokens", min_value=0, value=131072)
                max_output_tokens = st.number_input("Max Output Tokens", min_value=0, value=8192)
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
                    new_model = {
                        "name": model_name,
                        "provider": selected_provider,
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
                    
                    existing_model = db.models.find_one({"name": model_name})
                    if existing_model:
                        st.error(f"Model '{model_name}' already exists!")
                    else:
                        db.models.insert_one(new_model)
                        st.success(f"Model '{model_name}' added successfully!")
                        st.balloons()
                        sleep(2)
                        st.rerun()
    
    if model_action == "Edit":
        available_models = list(db.models.find({}, {"name": 1, "_id": 0}))
        
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
            st.session_state.edit_model_name = model_name_map[selected_display]
            st.session_state.edit_model_data = db.models.find_one({"name": st.session_state.edit_model_name})
            st.rerun()
            return
            
    if 'edit_model_data' in st.session_state and st.session_state.edit_model_data is not None:
        current_model = st.session_state.edit_model_data
        model_to_edit = st.session_state.edit_model_name
        
        with st.form("edit_model_form"):
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
            
            col7, col8 = st.columns(2)
            with col7:
                if st.form_submit_button("Update Model"):
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

                    db.models.update_one(
                        {"name": model_to_edit},
                        {"$set": update_data}
                    )
                    st.success(f"Model '{model_to_edit}' updated successfully!")
                    st.balloons()
                    st.session_state.edit_model_name = None
                    st.session_state.edit_model_data = None
                    st.rerun()
            
            with col8:
                if st.form_submit_button("Cancel"):
                    st.session_state.edit_model_name = None
                    st.session_state.edit_model_data = None
                    st.rerun()
    
    if model_action == "Delete":
        scratch_pad_chat = db.chats.find_one({"name": "Scratch Pad"})
        scratch_pad_model = scratch_pad_chat.get("model") if scratch_pad_chat else None
        
        protected_models = [config.DEFAULT_MODEL, config.DECISION_MODEL]
        if scratch_pad_model:
            protected_models.append(scratch_pad_model)
        
        protected_models = list(set(protected_models))
        
        available_models = list(db.models.find(
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
                    if model_to_delete in protected_models:
                        st.error(f"Cannot delete protected model '{model_to_delete}'.")
                    else:
                        result = db.models.delete_one({"name": model_to_delete})
                        
                        if result.deleted_count > 0:
                            if st.session_state.get('edit_model_name') == model_to_delete:
                                st.session_state.edit_model_name = None
                                st.session_state.edit_model_data = None
                            st.success(f"Model '{model_to_delete}' deleted successfully!")
                            st.balloons()
                            sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Could not delete model '{model_to_delete}'.")

def manage_UI(db):
    st.sidebar.markdown("### :blue[Active Chat] 🎯")
    st.sidebar.markdown(f"**Chat Name:** :blue[{st.session_state.active_chat.get('name', 'N/A')}]")
    st.sidebar.markdown(f"**Model:** :blue[{st.session_state.active_chat.get('model', 'N/A')}]")
    st.sidebar.divider()

    col1, col2, col3 = st.sidebar.columns(3)
    if col1.button("💬", help="Chat with Gemini", use_container_width=True): st.session_state.app_mode = "chat"
    if col2.button("🧹", help="Clear active chat history", use_container_width=True): st.session_state.app_mode = "clear_chat"
    if col3.button("🗑️", help="Delete active chat", use_container_width=True): st.session_state.app_mode = "delete_chat"

    # First row - 4 buttons
    colA, colB, colC, colD = st.sidebar.columns(4)
    if colA.button("🆕", help="New chat", use_container_width=True): st.session_state.app_mode = "new_chat"
    if colB.button("⚙️", help="Manage models", use_container_width=True): st.session_state.app_mode = "models"
    if colC.button("📂", help="Manage chat archiving", use_container_width=True): st.session_state.app_mode = "archive"
    if colD.button("🐞", help="Debug panel - View internal agent conversations", use_container_width=True): st.session_state.app_mode = "debug"
    
    # Second row - User profile button (centered)
    col_spacer1, col_profile, col_spacer2 = st.sidebar.columns([1, 2, 1])
    with col_profile:
        if st.button("👤 Profile", help="Manage user profile and personalization", use_container_width=True): 
            st.session_state.app_mode = "profile"

    chat_docs_for_options = make_chat_list(db)
    st.sidebar.markdown("### Select Chat")
    
    try:
        chat_names = [chat['name'] for chat in chat_docs_for_options]
        default_index = chat_names.index(st.session_state.active_chat['name'])
    except (ValueError, KeyError, AttributeError):
        default_index = 0

    def handle_chat_selection():
        logger.debug("Chat selection triggered")
        logger.debug(f"Selected chat name: {st.session_state.chat_selector_name}")
        logger.debug(f"Current active_chat before change: {st.session_state.active_chat.get('name', 'None') if st.session_state.active_chat else 'None'}")
        
        st.session_state.app_mode = "chat"
        selected_chat_name = st.session_state.chat_selector_name
        for chat in chat_docs_for_options:
            if chat['name'] == selected_chat_name:
                logger.debug(f"Found chat document keys: {list(chat.keys())}")
                logger.debug(f"Chat has messages field: {'messages' in chat}")
                st.session_state.active_chat = chat
                break
    
    logger.debug(f"Active chat after change: {st.session_state.active_chat.get('name', 'None') if st.session_state.active_chat else 'None'}")

    st.sidebar.radio(
        "Available Chats", options=[doc['name'] for doc in chat_docs_for_options], 
        format_func=lambda name: next(format_chat_for_radio(doc) for doc in chat_docs_for_options if doc['name'] == name),
        index=default_index, key="chat_selector_name", on_change=handle_chat_selection,
        label_visibility="collapsed"
    )
    

def render_debug_panel():
    """Render the debug panel"""
    debug_panel.render_debug_panel()

def render_profile():
    """Render the user profile management interface"""
    import profile_ui
    profile_ui.render_user_profile()

def make_chat_list(db):
    scratch_pad_filter = {"name": "Scratch Pad", "archived": False}
    projection = {"name": 1, "updated_at": 1, "_id": 1, "messages": 1, "model": 1, "system_prompt": 1}
    scratch_pad_doc = db.chats.find_one(scratch_pad_filter, projection)
    other_chats_filter = {"name": {"$ne": "Scratch Pad"}, "archived": False}
    other_chats_cursor = db.chats.find(
        other_chats_filter, 
        projection
    ).sort("updated_at", -1)
    other_chats_list = list(other_chats_cursor)
    final_chat_list = [scratch_pad_doc] if scratch_pad_doc else []
    final_chat_list.extend(other_chats_list)
    return final_chat_list
