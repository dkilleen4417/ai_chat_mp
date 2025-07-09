import streamlit as st
import os
from datetime import datetime
from typing import Dict, List, Optional
import re
from time import time as current_time
from logger import logger
from providers import ProviderManager

# Session state alias for consistency
ss = st.session_state

class ChatPublisher:
    def __init__(self, db, provider_manager: ProviderManager):
        self.db = db
        self.provider_manager = provider_manager
        self.publications_dir = "publications"
        
        # Ensure publications directory exists
        if not os.path.exists(self.publications_dir):
            os.makedirs(self.publications_dir)
    
    
    def format_chat_for_processing(self, chat: Dict) -> str:
        """Format chat messages for LLM processing"""
        chat_text = f"Chat Name: {chat.get('name', 'Untitled Chat')}\n"
        chat_text += f"Model Used: {chat.get('model', 'Unknown')}\n"
        chat_text += f"Created: {datetime.fromtimestamp(chat.get('created_at', current_time())).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        messages = chat.get('messages', [])
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', current_time())
            
            # Format timestamp
            time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
            
            if role == 'user':
                chat_text += f"[{time_str}] USER: {content}\n\n"
            elif role == 'assistant':
                chat_text += f"[{time_str}] ASSISTANT: {content}\n\n"
                
                # Include search results if available
                search_results = msg.get('search_results')
                if search_results:
                    chat_text += f"[Search Results Used: {search_results[:100]}...]\n\n"
        
        return chat_text
    
    def generate_podcast_prompt(self, host_name: str, guest_name: str) -> str:
        """Generate the system prompt for podcast conversion"""
        return f"""You are a skilled podcast editor and writer. Your task is to convert an AI chat conversation into a natural, engaging podcast-style dialogue between two humans.

CONVERSION REQUIREMENTS:
1. Transform the conversation into a dialogue between "{host_name}" (the human user) and "{guest_name}" (the AI assistant)
2. Make corrections for grammar, spelling, and clarity
3. Maintain the original meaning and key information
4. Make the conversation flow naturally as if between two humans
5. Add appropriate transitions and conversational elements
6. Remove any references to AI, artificial intelligence, or that one participant is an AI
7. Make "{guest_name}" sound like a knowledgeable human expert on the topics discussed

CRITICAL CONVERSATION IMPROVEMENTS:
- AVOID repetitive response patterns - vary how {guest_name} starts responses (don't always say "That's fascinating" or "Absolutely")
- {guest_name} should sometimes offer different perspectives or respectfully push back on ideas
- Include natural conversational elements like pauses, "you know," interruptions, and tangents
- {guest_name} should occasionally share personal anecdotes or experiences when relevant
- Make the tone mature and professional, not overly polite or academic
- Both speakers should sound like real people having a genuine conversation

FORMATTING REQUIREMENTS:
- Use markdown format
- Include a title and intro section
- Use **{host_name}:** and **{guest_name}:** for speaker labels
- Add topic section headers where appropriate
- Include timestamps in conversation flow format
- Add a brief outro section
- Use proper markdown formatting (bold, italics, lists, etc.)

TONE AND STYLE:
- Keep it conversational and natural - real people talking, not a textbook
- Maintain the informative nature of the content
- Make it sound like a professional podcast conversation between equals
- Ensure smooth transitions between topics
- Add brief contextual introductions where helpful

Please convert the following chat conversation into a podcast-style dialogue:"""

    def process_chat_with_llm(self, chat: Dict, host_name: str, guest_name: str) -> str:
        """Process chat using LLM to create podcast format"""
        try:
            # Hardcoded model for now
            model_name = "gpt-4o"
            logger.info(f"Using model {model_name} for chat processing")
            
            # Get model configuration from database
            model_config = self.db.models.find_one({"name": model_name})
            if not model_config:
                raise Exception(f"Model configuration not found for: {model_name}")
            
            # Format the chat for processing
            formatted_chat = self.format_chat_for_processing(chat)
            
            # Generate the processing prompt
            system_prompt = self.generate_podcast_prompt(host_name, guest_name)
            
            # Create full prompt
            full_prompt = f"{system_prompt}\n\n{formatted_chat}"
            
            # Get provider based on model's provider field
            provider_name = model_config.get("provider", "google")
            provider = self.provider_manager.get_provider(provider_name)
            if not provider:
                raise Exception(f"Provider {provider_name} not available")
            
            # Process with LLM using the provider's generate_response method
            response = provider.generate_response(
                messages=[{"role": "user", "content": full_prompt}],
                model_config=model_config
            )
            
            # Extract text from response
            if isinstance(response, dict) and "text" in response:
                return response["text"]
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Error processing chat with LLM: {str(e)}")
            raise Exception(f"Failed to process chat: {str(e)}")
    
    def generate_filename(self, chat: Dict, host_name: str, guest_name: str) -> str:
        """Generate a filename for the published chat"""
        chat_name = chat.get('name', 'Untitled Chat')
        
        # Clean up the chat name for filename
        safe_name = re.sub(r'[^\w\s-]', '', chat_name)
        safe_name = re.sub(r'[-\s]+', '-', safe_name)
        safe_name = safe_name.strip('-')
        
        # Create timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create filename
        filename = f"{timestamp}_{safe_name}_{host_name}_{guest_name}.md"
        return filename
    
    def publish_chat(self, chat: Dict, host_name: str, guest_name: str) -> str:
        """Main method to publish a chat as markdown"""
        try:
            # Process the chat with LLM
            with st.spinner("🤖 Processing chat with AI..."):
                processed_content = self.process_chat_with_llm(chat, host_name, guest_name)
            
            # Generate filename
            filename = self.generate_filename(chat, host_name, guest_name)
            filepath = os.path.join(self.publications_dir, filename)
            
            # Add metadata header
            metadata = f"""---
title: "{chat.get('name', 'Untitled Chat')}"
date: {datetime.now().strftime('%Y-%m-%d')}
host: {host_name}
guest: {guest_name}
original_model: {chat.get('model', 'Unknown')}
published: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---

"""
            
            # Write the file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(metadata + processed_content)
            
            logger.info(f"Chat published successfully to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error publishing chat: {str(e)}")
            raise Exception(f"Failed to publish chat: {str(e)}")

def render_publish_interface():
    """Render the chat publication interface"""
    st.markdown("### 📝 Publish Chat as Podcast")
    st.markdown("Convert your chat conversation into a podcast-style dialogue between two humans.")
    st.divider()
    
    # Get all chats for selection
    all_chats = list(ss.db.chats.find({}).sort("updated_at", -1))
    
    if not all_chats:
        st.info("No chats available for publication.")
        return
    
    # Chat selection
    chat_options = {f"{chat['name']} ({datetime.fromtimestamp(chat.get('updated_at', current_time())).strftime('%Y-%m-%d %H:%M')})": chat for chat in all_chats}
    
    selected_chat_display = st.selectbox(
        "Select Chat to Publish",
        options=list(chat_options.keys()),
        help="Choose the chat conversation you want to convert to podcast format"
    )
    
    selected_chat = chat_options[selected_chat_display]
    
    # Show chat preview
    with st.expander("📖 Chat Preview"):
        messages = selected_chat.get('messages', [])
        if messages:
            st.write(f"**Messages:** {len(messages)}")
            st.write(f"**Model:** {selected_chat.get('model', 'Unknown')}")
            st.write(f"**Created:** {datetime.fromtimestamp(selected_chat.get('created_at', current_time())).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Show first few messages
            for i, msg in enumerate(messages[:3]):
                role = "🧑‍💻 User" if msg.get('role') == 'user' else "🤖 Assistant"
                content = msg.get('content', '')[:200] + "..." if len(msg.get('content', '')) > 200 else msg.get('content', '')
                st.write(f"**{role}:** {content}")
            
            if len(messages) > 3:
                st.write(f"... and {len(messages) - 3} more messages")
        else:
            st.write("No messages in this chat.")
    
    # Name configuration
    st.markdown("#### 👥 Podcast Participants")
    col1, col2 = st.columns(2)
    
    with col1:
        host_name = st.text_input(
            "Host Name (User)",
            value="Chip",
            help="Name for the human asking questions (originally the user)"
        )
    
    with col2:
        guest_name = st.text_input(
            "Guest Name (Expert)",
            value="Dale",
            help="Name for the expert answering questions (originally the AI)"
        )
    
    # Validation
    if not host_name.strip():
        st.error("Host name cannot be empty")
        return
    
    if not guest_name.strip():
        st.error("Guest name cannot be empty")
        return
    
    # Publication preview
    st.markdown("#### 📄 Publication Preview")
    st.info(f"**Title:** {selected_chat.get('name', 'Untitled Chat')}\n**Format:** Podcast dialogue between {host_name} and {guest_name}\n**Messages:** {len(selected_chat.get('messages', []))}")
    
    # Publish button
    if st.button("📝 Publish Chat", type="primary", use_container_width=True):
        if not selected_chat.get('messages'):
            st.error("Cannot publish empty chat")
            return
        
        try:
            publisher = ChatPublisher(ss.db, ss.provider_manager)
            filepath = publisher.publish_chat(selected_chat, host_name.strip(), guest_name.strip())
            
            st.success(f"✅ Chat published successfully!")
            st.info(f"📁 **File saved to:** `{filepath}`")
            
            # Show file content preview
            with st.expander("📖 Published Content Preview"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    st.markdown(content[:2000] + "..." if len(content) > 2000 else content)
                except Exception as e:
                    st.error(f"Error reading published file: {str(e)}")
            
        except Exception as e:
            st.error(f"❌ Error publishing chat: {str(e)}")
    
    # Publications folder info
    st.markdown("#### 📁 Publications Folder")
    publications_path = os.path.abspath("publications")
    st.info(f"All published chats are saved to: `{publications_path}`")
    
    # List existing publications
    try:
        published_files = [f for f in os.listdir("publications") if f.endswith('.md')]
        if published_files:
            st.markdown("**Recent Publications:**")
            for file in sorted(published_files, reverse=True)[:5]:
                st.write(f"• {file}")
        else:
            st.write("No publications yet.")
    except Exception as e:
        st.error(f"Error listing publications: {str(e)}")