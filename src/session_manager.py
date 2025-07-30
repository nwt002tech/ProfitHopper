# /mount/src/profithopper/src/session_manager.py
import streamlit as st

def init_session_state():
    """Initialize Streamlit session state variables"""
    if 'bankroll' not in st.session_state:
        st.session_state.bankroll = 10000  # Default starting bankroll
    if 'sessions' not in st.session_state:
        st.session_state.sessions = []
    # Add other session variables as needed

def get_bankroll_metrics():
    """Calculate and return bankroll metrics"""
    # Add your actual bankroll calculation logic here
    return {
        'current_bankroll': st.session_state.bankroll,
        'growth': 0,
        'sessions_count': len(st.session_state.sessions)
    }