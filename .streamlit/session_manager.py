import streamlit as st

def init_session_state():
    """Initialize all session state variables"""
    if 'session_log' not in st.session_state:
        st.session_state.session_log = []
    if 'current_trip_id' not in st.session_state:
        st.session_state.current_trip_id = 1
    if 'casino_list' not in st.session_state:
        st.session_state.casino_list = sorted([
            "L'auberge Lake Charles",
            "Golden Nugget Lake Charles",
            "Caesar's Horseshoe Lake Charles",
            "Delta Downs",
            "Island View",
            "Paragon Marksville",
            "Coushatta"
        ])
    if 'trip_settings' not in st.session_state:
        st.session_state.trip_settings = {
            'casino': st.session_state.casino_list[0],
            'starting_bankroll': 1000.0,
            'num_sessions': 10
        }

def get_bankroll_metrics():
    """Calculate key bankroll metrics"""
    # Calculations
    session_bankroll = st.session_state.trip_settings['starting_bankroll'] / st.session_state.trip_settings['num_sessions']
    max_bet = session_bankroll * 0.25
    stop_loss = session_bankroll * 0.6
    
    # Current trip sessions
    current_trip_sessions = [s for s in st.session_state.session_log if s['trip_id'] == st.session_state.current_trip_id]
    trip_profit = sum(s['profit'] for s in current_trip_sessions)
    current_bankroll = st.session_state.trip_settings['starting_bankroll'] + trip_profit
    
    return session_bankroll, max_bet, stop_loss, current_bankroll