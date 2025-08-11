from __future__ import annotations

import os
import math
from typing import List, Dict, Any
import streamlit as st

# Optional geolocation; safe if package missing (feature is OFF by default)
try:
    from streamlit_geolocation import streamlit_geolocation as geolocation
except Exception:
    geolocation = None

# Toggle the feature on/off without touching code (default OFF)
ENABLE_NEARBY = os.environ.get("ENABLE_NEARBY", "0").lower() in ("1", "true", "yes", "on")

# --- Your existing data layer (no changes required elsewhere) ---
# Prefer richer casino fetch (name, city, state, latitude, longitude...)
try:
    from data_loader_supabase import get_casinos_full  # returns DataFrame with at least "name"
except Exception:
    get_casinos_full = None

# Fallback: names list
try:
    from data_loader_supabase import get_casinos  # returns List[str]
except Exception:
    get_casinos = None


# =========================
# Session state init (keep your existing API)
# =========================
def initialize_trip_state() -> None:
    if "trip_started" not in st.session_state:
        st.session_state.trip_started = False
    if "current_trip_id" not in st.session_state:
        st.session_state.current_trip_id = 0
    if "trip_settings" not in st.session_state or not isinstance(st.session_state.trip_settings, dict):
        st.session_state.trip_settings = {
            "casino": "",
            "starting_bankroll": 200.0,
            "num_sessions": 3,
            # fields used only when ENABLE_NEARBY is True
            "use_my_location": False,
            "nearby_radius": 30,  # miles
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


# =========================
# Helpers
# =========================
def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return float("inf")
    R = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def _load_casino_names_df():
    """
    Returns (names_list, df) where df may include columns: name, city, state, latitude, longitude, is_active.
    If get_casinos_full() isn’t available, df is None and names_list comes from get_casinos().
    """
    df = None
    names = []
    # Try full DF first
    if callable(get_casinos_full):
        try:
            df = get_casinos_full(active_only=True)
        except Exception:
            df = None
    # Names list fallback
    if (df is None) and callable(get_casinos):
        try:
            names = [c for c in (get_casinos() or []) if c]
        except Exception:
            names = []
    if df is not None and not df.empty and "name" in df.columns:
        names = df["name"].dropna().astype(str).tolist()
    # remove placeholder if present
    names = [n for n in names if n and n != "Other..."]
    return names, df


def _nearby_filter_options(disabled: bool) -> List[str]:
    """
    Returns the casino list, optionally filtered by user location.
    If ENABLE_NEARBY is off, or permission/coords are missing, gracefully returns all names.
    """
    all_names, df = _load_casino_names_df()
    if not ENABLE_NEARBY or disabled:
        return all_names

    st.caption("Filter casinos near you (requires location permission)")
    colA, colB = st.columns([1, 1])
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
        st.info("Click above to grant location access, or uncheck 'Use my location'.")
        return all_names

    user_lat, user_lon = coords["latitude"], coords["longitude"]

    # If we don’t have coords for casinos, we can’t compute distance — just return all
    if df is None or "latitude" not in df.columns or "longitude" not in df.columns:
        return all_names

    # Compute distances and filter
    df = df.copy()
    df["distance_mi"] = df.apply(
        lambda r: _haversine_miles(r.get("latitude"), r.get("longitude"), user_lat, user_lon),
        axis=1
    )
    nearby = df[df["distance_mi"] <= float(radius_miles)]
    if nearby.empty:
        st.info(f"No casinos within {int(radius_miles)} miles. Showing all.")
        return all_names

    nearby = nearby.sort_values("distance_mi")
    return nearby["name"].astype(str).tolist()


# =========================
# Sidebar (keeps your existing UI/logic)
# =========================
def render_sidebar() -> None:
    initialize_trip_state()
    with st.sidebar:
        st.header("🎯 Trip Settings")
        disabled = bool(st.session_state.trip_started)

        # Casino select (with optional nearby filtering)
        options = _nearby_filter_options(disabled=disabled)
        if not options:
            options = [st.session_state.trip_settings.get("casino", "")] if st.session_state.trip_settings.get("casino") else ["(select casino)"]

        current = st.session_state.trip_settings.get("casino", "")
        if current not in options and options:
            current = options[0]
        try:
            idx = options.index(current)
        except Exception:
            idx = 0

        sel = st.selectbox("Casino", options=options, index=idx, disabled=disabled)
        st.session_state.trip_settings["casino"] = "" if sel == "(select casino)" else sel

        # --- tiny status badge when near-me is enabled ---
        if ENABLE_NEARBY:
            # _nearby_filter_options writes these keys when the toggle UI is visible
            use_loc = bool(st.session_state.trip_settings.get("use_my_location", False))
            radius = int(st.session_state.trip_settings.get("nearby_radius", 30))
            nearby_count = len(options)
            badge = f"📍 near‑me: {'ON' if use_loc else 'OFF'}  •  radius: {radius} mi  •  results: {nearby_count}"
            st.caption(badge)

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


# =========================
# Bankroll & heuristics (same signatures your app imports)
# =========================
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


# =========================
# Simple blacklist stored in session (keeps your API)
# =========================
def get_blacklisted_games() -> List[str]:
    return sorted(list(st.session_state.blacklisted_games))

def blacklist_game(game_name: str) -> None:
    st.session_state.blacklisted_games.add(game_name)


# =========================
# Optional helpers your app may use
# =========================
def get_current_trip_sessions() -> List[Dict[str, Any]]:
    tid = st.session_state.get("current_trip_id", 0)
    sessions = st.session_state.get("session_log", [])
    return [s for s in sessions if s.get("trip_id") == tid]

def record_session_performance(profit: float) -> None:
    arr = st.session_state.get("recent_profits", [])
    arr.append(float(profit))
    st.session_state.recent_profits = arr[-10:]