
from __future__ import annotations

import os
import math
from typing import List, Dict, Any
import streamlit as st

# Optional geolocation; safe if package missing
try:
    from streamlit_geolocation import streamlit_geolocation as geolocation
except Exception:
    geolocation = None

# Toggle the feature on/off without touching code
ENABLE_NEARBY = os.environ.get("ENABLE_NEARBY", "0").lower() in ("1","true","yes","on")

# Data access
try:
    from data_loader_supabase import get_casinos_full
except Exception:
    get_casinos_full = None
from data_loader_supabase import get_casinos  # always exists in your base

# ----------------------------
# Session init
# ----------------------------
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
            # new fields (harmless if not used)
            "use_my_location": False,
            "nearby_radius": 30,
        }
    if "trip_bankrolls" not in st.session_state:
        st.session_state.trip_bankrolls = {}
    if "blacklisted_games" not in st.session_state:
        st.session_state.blacklisted_games = set()
    if "recent_profits" not in st.session_state:
        st.session_state.recent_profits = []
    if "session_log" not in st.session_state:
        st.session_state.session_log = []

def _reset_trip_defaults() -> None:
    st.session_state.trip_settings = {
        "casino": "",
        "starting_bankroll": 200.0,
        "num_sessions": 3,
        "use_my_location": False,
        "nearby_radius": 30,
    }

# ----------------------------
# Utilities
# ----------------------------
def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return float("inf")
    R = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def _nearby_filter_options(disabled: bool) -> List[str]:
    """
    Returns list of casino names, filtered by location if ENABLE_NEARBY + user opted-in.
    Falls back to all names if geolocation not available or permission denied.
    """
    # Get full DF if available
    df = None
    if get_casinos_full is not None:
        try:
            df = get_casinos_full(active_only=True)
        except Exception:
            df = None

    if df is None or df.empty or "name" not in df.columns:
        # Fall back to simple names
        return [c for c in get_casinos() if c and c != "Other..."]

    all_names = [n for n in df["name"].dropna().astype(str).tolist() if n and n != "Other..."]

    # If the feature is off or trip is active, just return all
    if not ENABLE_NEARBY or disabled:
        return all_names

    st.caption("Filter casinos near you (requires location permission)")
    colA, colB = st.columns([1,1])
    with colA:
        use_my_location = st.checkbox(
            "Use my location",
            value=bool(st.session_state.trip_settings.get("use_my_location", False)),
            key="use_my_location",
            disabled=disabled
        )
        st.session_state.trip_settings["use_my_location"] = use_my_location
    with colB:
        radius_miles = st.slider(
            "Radius (miles)", 5, 100,
            int(st.session_state.trip_settings.get("nearby_radius", 30)),
            step=5, key="nearby_radius", disabled=disabled
        )
        st.session_state.trip_settings["nearby_radius"] = int(radius_miles)

    if not use_my_location:
        return all_names

    if geolocation is None:
        st.info("Location component not installed. Add 'streamlit-geolocation' or turn off 'Use my location'.")
        return all_names

    coords = geolocation()
    if not (coords and "latitude" in coords and "longitude" in coords):
        st.info("Click the button above to grant location access, or uncheck 'Use my location'.")
        return all_names

    user_lat, user_lon = coords["latitude"], coords["longitude"]
    # Only filter if df has coordinates
    if "latitude" not in df.columns or "longitude" not in df.columns:
        return all_names

    df["distance_mi"] = df.apply(lambda r: _haversine_miles(r.get("latitude"), r.get("longitude"), user_lat, user_lon), axis=1)
    nearby = df[df["distance_mi"] <= float(radius_miles)].sort_values("distance_mi")
    if nearby.empty:
        st.info(f"No casinos within {radius_miles} miles. Showing all.")
        return all_names
    st.success(f"Found {len(nearby)} nearby casino(s).")
    return nearby["name"].astype(str).tolist()

# ----------------------------
# Sidebar UI (keeps your existing behavior)
# ----------------------------
def render_sidebar() -> None:
    initialize_trip_state()
    with st.sidebar:
        st.header("🎯 Trip Settings")
        disabled = bool(st.session_state.trip_started)

        # Casino select (with optional nearby filter)
        options = _nearby_filter_options(disabled=disabled)
        current = st.session_state.trip_settings.get("casino", "")
        if current not in options and options:
            current = options[0]
        idx = options.index(current) if current in options else 0
        sel = st.selectbox("Casino", options=options, index=idx, disabled=disabled)
        st.session_state.trip_settings["casino"] = sel

        start_bankroll = st.number_input(
            "Total Trip Bankroll ($)", min_value=0.0, step=10.0,
            value=float(st.session_state.trip_settings.get("starting_bankroll", 200.0)),
            disabled=disabled
        )
        num_sessions = st.number_input(
            "Number of Sessions", min_value=1, step=1,
            value=int(st.session_state.trip_settings.get("num_sessions", 3)),
            disabled=disabled
        )

        st.session_state.trip_settings["starting_bankroll"] = float(start_bankroll)
        st.session_state.trip_settings["num_sessions"] = int(num_sessions)

        st.caption(f"Per-session bankroll estimate: ${get_session_bankroll():,.2f}")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Start New Trip", disabled=st.session_state.trip_started, use_container_width=True):
                st.session_state.trip_started = True
                st.session_state.current_trip_id = int(st.session_state.current_trip_id or 0) + 1
                st.session_state.trip_bankrolls[st.session_state.current_trip_id] = float(start_bankroll)
                st.success("Trip started.")
                st.rerun()
        with c2:
            if st.button("Stop Trip", disabled=not st.session_state.trip_started, use_container_width=True):
                st.session_state.trip_started = False
                _reset_trip_defaults()
                st.info("Trip stopped and settings reset.")
                st.rerun()

# ----------------------------
# Bankroll & simple heuristics (existing API your app imports)
# ----------------------------
def get_session_bankroll() -> float:
    ts = st.session_state.trip_settings
    total = float(ts.get("starting_bankroll", 0.0) or 0.0)
    n = int(ts.get("num_sessions", 1) or 1)
    n = max(1, n)
    return total / n

def get_current_bankroll() -> float:
    tid = st.session_state.get("current_trip_id", 0)
    if tid in st.session_state.trip_bankrolls:
        return float(st.session_state.trip_bankrolls[tid])
    return float(st.session_state.trip_settings.get("starting_bankroll", 0.0))

def get_win_streak_factor() -> float:
    profits = st.session_state.get("recent_profits", [])
    if len(profits) < 3:
        return 1.0
    last = profits[-5:]
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
    if std <= 20.0:
        return 1.05
    if std >= 120.0:
        return 0.9
    return 1.0

# ----------------------------
# Simple blacklist stored in session (your app already uses these)
# ----------------------------
def get_blacklisted_games() -> List[str]:
    return sorted(list(st.session_state.blacklisted_games))

def blacklist_game(game_name: str) -> None:
    st.session_state.blacklisted_games.add(game_name)

# ----------------------------
# Session log helpers
# ----------------------------
def get_current_trip_sessions() -> List[Dict[str, Any]]:
    tid = st.session_state.get("current_trip_id", 0)
    sessions = st.session_state.get("session_log", [])
    return [s for s in sessions if s.get("trip_id") == tid]

def record_session_performance(profit: float) -> None:
    arr = st.session_state.get("recent_profits", [])
    arr.append(float(profit))
    st.session_state.recent_profits = arr[-10:]
