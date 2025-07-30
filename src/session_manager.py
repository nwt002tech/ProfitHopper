import streamlit as st

def init_session_state():
    # Initialize core session variables
    if 'bankroll' not in st.session_state:
        st.session_state.bankroll = {
            'current': 1000.00,
            'starting': 1000.00,
            'history': []
        }
    
    # Initialize strategy settings
    if 'strategy' not in st.session_state:
        st.session_state.strategy = {
            'unit_size': 50,
            'max_units': 3,
            'daily_target': 0.15
        }

def get_bankroll_metrics():
    """Return metrics as a dictionary"""
    try:
        return {
            'current': st.session_state.bankroll['current'],
            'starting': st.session_state.bankroll['starting'],
            'daily_profit': calculate_daily_profit(),
            'roi': calculate_roi()
        }
    except KeyError:
        # Return safe defaults if session state isn't initialized
        return {
            'current': 0.00,
            'starting': 0.00,
            'daily_profit': 0.00,
            'roi': 0.00
        }

def calculate_daily_profit():
    """Calculate today's profit (simplified example)"""
    if not st.session_state.bankroll['history']:
        return 0.00
    return st.session_state.bankroll['current'] - st.session_state.bankroll['history'][-1]

def calculate_roi():
    """Calculate ROI percentage (simplified example)"""
    if st.session_state.bankroll['starting'] == 0:
        return 0.00
    return ((st.session_state.bankroll['current'] - st.session_state.bankroll['starting']) 
            / st.session_state.bankroll['starting']) * 100