# trip_manager.py  (only change: removed location text from sidebar)

import streamlit as st
from data_loader import load_trip_data
from browser_location import request_location

def initialize_trip_state():
    if "total_bankroll" not in st.session_state:
        st.session_state.total_bankroll = 0
    if "session_bankroll" not in st.session_state:
        st.session_state.session_bankroll = 0
    if "current_bankroll" not in st.session_state:
        st.session_state.current_bankroll = 0
    if "session_log" not in st.session_state:
        st.session_state.session_log = []
    if "blacklisted_games" not in st.session_state:
        st.session_state.blacklisted_games = set()

def render_sidebar():
    st.sidebar.header("🛠️ compact sidebar")

    # 🚫 Removed the line that displayed:
    # st.sidebar.write("Share your location (one-time to enable near-me)")

    request_location()

    trip_data = load_trip_data()

    if trip_data is not None:
        st.sidebar.subheader("Trip Data")
        st.sidebar.dataframe(trip_data)

def get_session_bankroll():
    return st.session_state.get("session_bankroll", 0)

def get_current_bankroll():
    return st.session_state.get("current_bankroll", 0)

def blacklist_game(game_name):
    st.session_state.blacklisted_games.add(game_name)

def get_blacklisted_games():
    return list(st.session_state.blacklisted_games)

def get_volatility_adjustment(volatility):
    if volatility == "Low":
        return 0.9
    elif volatility == "High":
        return 1.1
    return 1.0

def get_win_streak_factor():
    # Placeholder logic for win streak factor
    return 1.0