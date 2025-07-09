"""
Debug Panel - Shows internal agent conversations and routing decisions
"""

import streamlit as st
from typing import List
from llm_intelligent_router import usage_tracker

# Session state alias for consistency
ss = st.session_state

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
    
    # Routing Usage Statistics
    st.subheader("📊 Routing Usage Statistics")
    
    try:
        stats = usage_tracker.get_usage_stats()
        
        if stats['total_requests'] > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Requests", stats['total_requests'])
            
            with col2:
                st.metric("LLM Success", stats['llm_success_count'], 
                         f"{stats['llm_success_rate']:.1%}")
            
            with col3:
                st.metric("Backup Used", stats['backup_usage_count'], 
                         f"{stats['backup_usage_rate']:.1%}")
            
            with col4:
                if stats['last_backup_time']:
                    from datetime import datetime
                    last_backup = datetime.fromisoformat(stats['last_backup_time'])
                    st.metric("Last Backup", last_backup.strftime("%H:%M:%S"))
                else:
                    st.metric("Last Backup", "Never")
            
            # Show recent backup reasons if any
            if stats['recent_backup_reasons']:
                st.write("**Recent Backup Reasons:**")
                for reason in stats['recent_backup_reasons']:
                    st.write(f"• {reason}")
        else:
            st.info("No routing decisions recorded yet.")
            
    except Exception as e:
        st.error(f"Error loading usage statistics: {e}")
    
    st.divider()
    
    # Debug logs container
    if 'debug_logs' not in ss:
        ss.debug_logs = []
    
    if not ss.debug_logs:
        st.info("🤖 No debug logs yet. Send a message to see the internal agent conversation!")
        st.markdown("""
        **What you'll see here:**
        - 🧠 Router decisions and confidence scores
        - 🔧 Tool selection reasoning  
        - 🔍 Search vs direct tool usage
        - 📊 Confidence thresholds and fallbacks
        - 🔍 Context relevance analysis
        - ⚠️ Errors and exception handling
        """)
    else:
        # Show logs in a container
        with st.container(height=600, border=True):
            # Display logs (newest first if auto-scroll is off, oldest first if on)
            logs_to_show = ss.debug_logs
            if not auto_scroll:
                logs_to_show = reversed(logs_to_show)
            
            for log_entry in logs_to_show:
                # Handle separators
                if log_entry.startswith("==="):
                    st.divider()
                    continue
                
                # Color coding based on log content
                if "❌" in log_entry:
                    st.error(log_entry)
                elif "❓" in log_entry or "User Question" in log_entry:
                    st.markdown(f"**{log_entry}**")  # Bold for user questions
                elif "🧠" in log_entry or "Router Decision" in log_entry:
                    st.info(log_entry)
                elif "🔧" in log_entry or "Tool" in log_entry:
                    st.success(log_entry)
                elif "🔍" in log_entry or "Search" in log_entry:
                    st.warning(log_entry)
                elif "🤖 AI Response" in log_entry:
                    st.markdown(f"**{log_entry}**")  # Bold for AI responses
                elif "⚡" in log_entry or "📊" in log_entry:
                    st.caption(log_entry)  # Smaller text for metrics
                elif "📊" in log_entry or "Confidence" in log_entry:
                    st.metric("", log_entry.split("] ")[1] if "] " in log_entry else log_entry)
                else:
                    st.text(log_entry)
        
        # Auto-refresh option
        if st.button("🔄 Refresh Logs"):
            st.rerun()
        
        st.caption(f"📈 Total logs: {len(ss.debug_logs)} (last 100 kept)")

def add_debug_sidebar_controls():
    """Add minimal debug controls to sidebar"""
    
    # Just the live debug toggle - clean and simple
    debug_mode = st.sidebar.checkbox("🐛 Live Debug", help="Show debug info in chat messages", 
                                     value=ss.get('live_debug_mode', False))
    
    # Store the debug mode in session state
    if debug_mode != ss.get('live_debug_mode', False):
        ss.live_debug_mode = debug_mode
    
    return debug_mode