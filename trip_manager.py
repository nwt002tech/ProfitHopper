import streamlit as st

def initialize_trip_state():
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
            'casino': st.session_state.casino_list[0] if st.session_state.casino_list else "",
            'starting_bankroll': 100.0,  # Fixed to $100
            'num_sessions': 10
        }

# ... rest of the file remains the same ...