# trip_manager.py
# Version: 2025-08-13-minimal-2
# Changes:
#   - Removed the "Share your location (one‑time to enable near‑me)" text.
#   - Moved `from data_loader import load_trip_data` into render_sidebar() to avoid ImportError at import time.
# Everything else left as-is and simple.

import streamlit as st
from browser_location import request_location  # keep as before


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

    # 🚫 Removed the line:
    # st.sidebar.write("Share your location (one‑time to enable near‑me)")

    # Keep your original behavior of requesting location (no visible text)
    try:
        request_location()
    except Exception:
        pass  # never crash the sidebar for location issues

    # Lazy-import to avoid ImportError at module import time
    load_trip_data = None
    try:
        from data_loader import load_trip_data as _load_trip_data  # type: ignore
        load_trip_data = _load_trip_data
    except Exception:
        load_trip_data = None

    if load_trip_data:
        try:
            trip_data = load_trip_data()
            if trip_data is not None:
                st.sidebar.subheader("Trip Data")
                st.sidebar.dataframe(trip_data)
        except Exception:
            pass  # do not crash UI if loader throws


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
    # Placeholder logic unchanged
    return 1.0