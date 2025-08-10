
from __future__ import annotations

import os
import time
from typing import List, Dict, Any
import math
import pandas as pd
import streamlit as st

# Toggle to completely disable the "near me" feature unless explicitly enabled
ENABLE_NEARBY = os.environ.get("ENABLE_NEARBY", "0").lower() in ("1","true","yes","on")

# Optional browser geolocation (guarded + aliased)
try:
    from streamlit_geolocation import streamlit_geolocation as geolocation
except Exception:
    geolocation = None  # gracefully handled

# Supabase data helpers
try:
    from data_loader_supabase import get_casinos_full
except Exception:
    get_casinos_full = None

# ----------------------------
# Session defaults
# ----------------------------
DEFAULTS = {
    "trip_started": False,
    "current_trip_id": 0,
    "trip_settings": {
        "casino": "",
        "starting_bankroll": 200.0,
        "num_sessions": 3,
        # nearby filter controls (used only when ENABLE_NEARBY is true)
        "use_my_location": False,
        "nearby_radius": 30,
    },
    "trip_bankrolls": {},           # trip_id -> bankroll
    "blacklisted_games": set(),
    "recent_profits": [],
}

def initialize_trip_state() -> None:
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v if not isinstance(v, dict) else (v.copy() if not isinstance(v, set) else set())
    # ensure nested settings exist
    if "trip_settings" not in st.session_state or not isinstance(st.session_state.trip_settings, dict):
        st.session_state.trip_settings = dict(DEFAULTS["trip_settings"])

def _reset_trip_defaults() -> None:
    st.session_state.trip_settings = dict(DEFAULTS["trip_settings"])

# ----------------------------
# Nearby distance
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

# ----------------------------
# Casino selector (with optional nearby filtering)
# ----------------------------
def _casino_selector(disabled: bool) -> str:
    # Fallback list if loader not available
    names_fallback: List[str] = []

    if get_casinos_full is not None:
        df = get_casinos_full(active_only=True)
        all_names = df["name"].dropna().astype(str).tolist()
        all_names = [n for n in all_names if n and n != "Other..."]

        # Default to "show all"
        options = list(all_names)

        # Only render/use nearby UI if the toggle is enabled
        if ENABLE_NEARBY:
            st.caption("Filter casinos near you (requires location permission)")
            cA, cB = st.columns([1,1])
            with cA:
                use_my_location = st.checkbox(
                    "Use my location",
                    value=st.session_state.trip_settings.get("use_my_location", False),
                    key="use_my_location",
                    disabled=disabled
                )
                st.session_state.trip_settings["use_my_location"] = use_my_location
            with cB:
                radius_miles = st.slider(
                    "Radius (miles)", 5, 100,
                    int(st.session_state.trip_settings.get("nearby_radius", 30)),
                    step=5, key="nearby_radius", disabled=disabled
                )
                st.session_state.trip_settings["nearby_radius"] = int(radius_miles)

            if use_my_location and not disabled:
                if geolocation is None:
                    st.info("Location component not installed. Add 'streamlit-geolocation' to requirements or turn off 'Use my location'.")
                else:
                    coords = geolocation()
                    if coords and "latitude" in coords and "longitude" in coords:
                        ulat, ulon = coords["latitude"], coords["longitude"]
                        if "latitude" in df.columns and "longitude" in df.columns:
                            df["distance_mi"] = df.apply(lambda r: _haversine_miles(
                                r.get("latitude"), r.get("longitude"), ulat, ulon
                            ), axis=1)
                            nearby = df[df["distance_mi"] <= float(radius_miles)].sort_values("distance_mi")
                            if not nearby.empty:
                                st.success(f"Found {len(nearby)} nearby casino(s).")
                                options = nearby["name"].astype(str).tolist()
                            else:
                                st.info(f"No casinos within {radius_miles} miles. Showing all.")
                    # if permission denied or coords missing: silently keep 'options' = all_names

        # Keep current selection if present
        current = st.session_state.trip_settings.get("casino", "")
        if current not in options and options:
            current = options[0]
        try:
            default_index = options.index(current) if current in options else 0
        except Exception:
            default_index = 0
        sel = st.selectbox("Casino", options=options, index=default_index, disabled=disabled)
        return sel.strip()

    # Legacy fallback (if loader missing)
    try:
        from data_loader_supabase import get_casinos
        names_fallback = [c for c in get_casinos() if c and c != "Other..."]
    except Exception:
        names_fallback = []
    current = st.session_state.trip_settings.get("casino", "")
    try:
        default_index = names_fallback.index(current) if current in names_fallback else 0
    except Exception:
        default_index = 0
    sel = st.selectbox("Casino", options=names_fallback, index=default_index, disabled=disabled)
    return sel.strip()

# ----------------------------
# Sidebar (Trip Settings + start/stop)
# ----------------------------
def render_sidebar() -> None:
    initialize_trip_state()
    with st.sidebar:
        st.header("🎯 Trip Settings")
        disabled = bool(st.session_state.trip_started)

        # Casino select (with optional nearby filter)
        casino_choice = _casino_selector(disabled=disabled)

        # Core settings
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

        # Save back
        st.session_state.trip_settings["casino"] = casino_choice
        st.session_state.trip_settings["starting_bankroll"] = float(start_bankroll)
        st.session_state.trip_settings["num_sessions"] = int(num_sessions)

        # Derived
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
# Bankroll & heuristics (used by app)
# ----------------------------
def get_session_bankroll() -> float:
    ts = st.session_state.trip_settings
    total = float(ts.get("starting_bankroll", 0.0) or 0.0)
    n = max(1, int(ts.get("num_sessions", 1) or 1))
    return total / n

def get_current_bankroll() -> float:
    tid = st.session_state.get("current_trip_id", 0)
    if tid in st.session_state.trip_bankrolls:
        return float(st.session_state.trip_bankrolls[tid])
    return float(st.session_state.trip_settings.get("starting_bankroll", 0.0))

def record_session_performance(profit: float) -> None:
    profits = list(st.session_state.get("recent_profits", []))
    profits.append(float(profit))
    if len(profits) > 20:
        profits = profits[-20:]
    st.session_state.recent_profits = profits

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
# Blacklist (local, UI-level fallback — per-casino table is handled server-side elsewhere)
# ----------------------------
def get_blacklisted_games() -> List[str]:
    return sorted(list(st.session_state.blacklisted_games))

def blacklist_game(game_name: str) -> None:
    st.session_state.blacklisted_games.add(game_name)

# ----------------------------
# Trip/session helpers that other modules may call
# ----------------------------
def get_current_trip_sessions() -> List[Dict[str, Any]]:
    return [s for s in st.session_state.get("session_log", []) if s.get("trip_id") == st.session_state.get("current_trip_id")]

def add_session_to_trip(session: Dict[str, Any]) -> None:
    st.session_state.session_log.append(session)

def spend_bankroll(amount: float) -> None:
    tid = st.session_state.get("current_trip_id", 0)
    st.session_state.trip_bankrolls[tid] = max(0.0, float(st.session_state.trip_bankrolls.get(tid, 0.0)) - float(amount))

def add_bankroll(amount: float) -> None:
    tid = st.session_state.get("current_trip_id", 0)
    st.session_state.trip_bankrolls[tid] = float(st.session_state.trip_bankrolls.get(tid, 0.0)) + float(amount)
