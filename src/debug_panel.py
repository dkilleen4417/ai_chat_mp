"""
Debug Panel - Shows internal agent conversations and routing decisions
"""

import streamlit as st
from typing import List

def render_debug_panel():
    """Render the debug panel showing internal agent conversations"""
    st.title("🔍 Debug Panel - Internal Agent Conversations")
    
    # Control buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🗑️ Clear Logs", help="Clear all debug logs"):
            from main import clear_debug_logs
            clear_debug_logs()
            st.rerun()
    
    with col2:
        auto_scroll = st.checkbox("📜 Auto-scroll", value=True, help="Auto-scroll to latest logs")
    
    with col3:
        st.markdown("**Live view of routing decisions, tool selections, and AI reasoning**")
    
    st.divider()
    
    # Debug logs container
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []
    
    if not st.session_state.debug_logs:
        st.info("🤖 No debug logs yet. Send a message to see the internal agent conversation!")
        st.markdown("""
        **What you'll see here:**
        - 🧠 Router decisions and confidence scores
        - 🔧 Tool selection reasoning  
        - 🔍 Search vs direct tool usage
        - 📊 Confidence thresholds and fallbacks
        - ⚠️ Errors and exception handling
        """)
    else:
        # Show logs in a container
        with st.container(height=600, border=True):
            # Display logs (newest first if auto-scroll is off, oldest first if on)
            logs_to_show = st.session_state.debug_logs
            if not auto_scroll:
                logs_to_show = reversed(logs_to_show)
            
            for log_entry in logs_to_show:
                # Color coding based on log content
                if "❌" in log_entry:
                    st.error(log_entry)
                elif "🧠" in log_entry or "Router Decision" in log_entry:
                    st.info(log_entry)
                elif "🔧" in log_entry or "Tool" in log_entry:
                    st.success(log_entry)
                elif "🔍" in log_entry or "Search" in log_entry:
                    st.warning(log_entry)
                elif "📊" in log_entry or "Confidence" in log_entry:
                    st.metric("", log_entry.split("] ")[1] if "] " in log_entry else log_entry)
                else:
                    st.text(log_entry)
        
        # Auto-refresh option
        if st.button("🔄 Refresh Logs"):
            st.rerun()
        
        st.caption(f"📈 Total logs: {len(st.session_state.debug_logs)} (last 100 kept)")

def add_debug_sidebar_controls():
    """Add minimal debug controls to sidebar"""
    
    # Just the live debug toggle - clean and simple
    debug_mode = st.sidebar.checkbox("🐛 Live Debug", help="Show debug info in chat messages", 
                                     value=st.session_state.get('live_debug_mode', False))
    
    # Store the debug mode in session state
    if debug_mode != st.session_state.get('live_debug_mode', False):
        st.session_state.live_debug_mode = debug_mode
    
    return debug_mode