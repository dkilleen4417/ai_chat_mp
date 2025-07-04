"""
Debug utilities for AI Chat MP application
Handles debug logging to avoid circular imports
"""

import streamlit as st
from datetime import datetime


def add_debug_log(message: str):
    """Add a message to the debug log panel"""
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []
    
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    st.session_state.debug_logs.append(f"[{timestamp}] {message}")
    
    # Keep only last 100 entries
    if len(st.session_state.debug_logs) > 100:
        st.session_state.debug_logs = st.session_state.debug_logs[-100:]


def clear_debug_logs():
    """Clear all debug logs"""
    st.session_state.debug_logs = []