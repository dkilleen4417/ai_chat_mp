"""
Debug utilities for AI Chat MP application
Handles debug logging to avoid circular imports
"""

import streamlit as st
from datetime import datetime

# Session state alias for consistency
ss = st.session_state


def add_debug_log(message: str):
    """Add a message to the debug log panel"""
    if 'debug_logs' not in ss:
        ss.debug_logs = []
    
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    ss.debug_logs.append(f"[{timestamp}] {message}")
    
    # Keep only last 100 entries
    if len(ss.debug_logs) > 100:
        ss.debug_logs = ss.debug_logs[-100:]


def clear_debug_logs():
    """Clear all debug logs"""
    ss.debug_logs = []