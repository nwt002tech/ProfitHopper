
from __future__ import annotations
import streamlit as st
from typing import List, Dict, Any
import math

DEFAULT_CASINOS = [
    "L’Auberge Lake Charles",
    "Coushatta Casino Resort",
    "Golden Nugget Lake Charles",
    "Horseshoe Bossier City",
    "Winstar World Casino",
    "Choctaw Durant",
    "Other..."
]

def initialize_trip_state() -> None:
    if "trip_started" not in st.session_state:
        st.session_state.trip_started = False
    if "current_trip_id" not in st.session_state:
        st.session_state.current_trip_id = 0
    if "trip_settings" not in st.session_state:
        st.session_state.trip_settings = {
            "casino": "",
            "starting_bankroll": 200.0,
            "num_sessions": 3,
        }
    if "trip_bankrolls" not in st.session_state:
        st.session_state.trip_bankrolls: Dict[int, float] = {}
    if "session_log" not in st.session_state:
        st.session_state.session_log: List[Dict[str, Any]] = []
    if "blacklisted_games" not in st.session_state:
        st.session_state.blacklisted_games = set()
    if "recent_profits" not in st.session_state:
        st.session_state.recent_profits: List[float] = []

def _reset_trip_defaults() -> None:
    st.session_state.trip_settings = {
        "casino": "",
        "starting_bankroll": 200.0,
        "num_sessions": 3,
    }

def _casino_selector(disabled: bool) -> str:
    """Render a dropdown for casino with an 'Other...' option for custom entry."""
    current = st.session_state.trip_settings.get("casino", "").strip()
    # Build options, preserving current if it's custom
    options = [c for c in DEFAULT_CASINOS]
    if current and current not in options and current != "Other...":
        options = [current] + [c for c in options if c != current]
        default_index = 0
    else:
        # Default to current if present, else first item
        default_index = options.index(current) if current in options else 0

    sel = st.selectbox("Casino", options=options, index=default_index, disabled=disabled)
    custom_name = current if (current and current not in DEFAULT_CASINOS) else ""
    if sel == "Other...":
        custom_name = st.text_input("Custom Casino", value=custom_name, disabled=disabled)
        return custom_name.strip()
    return sel.strip()

def render_sidebar() -> None:
    initialize_trip_state()
    with st.sidebar:
        st.header("🎯 Trip Settings")

        disabled = st.session_state.trip_started

        casino_choice = _casino_selector(disabled=disabled)
        start_bankroll = st.number_input(
            "Total Trip Bankroll ($)",
            min_value=0.0,
            value=float(st.session_state.trip_settings.get("starting_bankroll", 200.0)),
            step=10.0,
            disabled=disabled,
        )
        num_sessions = st.number_input(
            "Number of Sessions",
            min_value=1,
            max_value=50,
            value=int(st.session_state.trip_settings.get("num_sessions", 3)),
            step=1,
            disabled=disabled,
        )

        col1, col2 = st.columns(2)
        with col1:
            start_clicked = st.button("🚀 Start New Trip", use_container_width=True, disabled=st.session_state.trip_started)
        with col2:
            stop_clicked = st.button("🛑 Stop Trip", use_container_width=True, disabled=not st.session_state.trip_started)

        if start_clicked and not st.session_state.trip_started:
            st.session_state.trip_settings["casino"] = casino_choice
            st.session_state.trip_settings["starting_bankroll"] = float(start_bankroll)
            st.session_state.trip_settings["num_sessions"] = int(num_sessions)

            st.session_state.trip_started = True
            st.session_state.current_trip_id += 1
            st.session_state.trip_bankrolls[st.session_state.current_trip_id] = float(start_bankroll)

            st.session_state.blacklisted_games = set()
            st.session_state.recent_profits = []

            st.success(f"Started Trip #{st.session_state.current_trip_id} at {st.session_state.trip_settings['casino'] or 'N/A'}")
            st.rerun()

        if stop_clicked and st.session_state.trip_started:
            st.session_state.trip_started = False
            _reset_trip_defaults()
            st.info("Trip stopped. Settings reset to defaults.")
            st.rerun()

        per_session = get_session_bankroll()
        st.caption(f"Per-session bankroll estimate: ${per_session:,.2f}")

def get_session_bankroll() -> float:
    ts = st.session_state.trip_settings
    total = float(ts.get("starting_bankroll", 0.0) or 0.0)
    n = int(ts.get("num_sessions", 1) or 1)
    n = max(1, n)
    return total / n

def get_current_bankroll() -> float:
    tid = st.session_state.get("current_trip_id", 0)
    if tid and tid in st.session_state.trip_bankrolls:
        return float(st.session_state.trip_bankrolls[tid])
    return float(st.session_state.trip_settings.get("starting_bankroll", 0.0))

def blacklist_game(name: str) -> None:
    st.session_state.blacklisted_games.add(name)

def get_blacklisted_games():
    return st.session_state.blacklisted_games

def get_win_streak_factor() -> float:
    profits = st.session_state.get("recent_profits", [])
    if not profits:
        return 1.0
    last = profits[-min(5, len(profits)):]
    avg = sum(last) / len(last)
    if avg > 0:
        return min(1.25, 1.0 + (avg / max(20.0, abs(avg)) * 0.25))
    if avg < 0:
        return max(0.85, 1.0 + (avg / max(40.0, abs(avg)) * 0.15))
    return 1.0

def get_volatility_adjustment() -> float:
    profits = st.session_state.get("recent_profits", [])
    if len(profits) < 3:
        return 1.0
    mean = sum(profits) / len(profits)
    var = sum((p - mean) ** 2 for p in profits) / len(profits)
    std = math.sqrt(var)
    std_clamped = min(200.0, std)
    return 1.1 - (std_clamped / 200.0) * 0.2

def get_current_trip_sessions() -> List[Dict[str, Any]]:
    tid = st.session_state.get("current_trip_id", 0)
    sessions = st.session_state.get("session_log", [])
    return [s for s in sessions if s.get("trip_id") == tid]

def record_session_performance(profit: float) -> None:
    arr = st.session_state.get("recent_profits", [])
    arr.append(float(profit))
    st.session_state.recent_profits = arr[-10:]
