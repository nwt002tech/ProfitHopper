
from __future__ import annotations
import streamlit as st
from typing import List, Dict, Any
import math

# Optional browser geolocation
try:
    try:
    from streamlit_geolocation import streamlit_geolocation as geolocation
except Exception:
    geolocation = None
except Exception:
    geolocation = None  # handled gracefully

# Data access
try:
    # new richer fetch (name, city, state, lat, lon, is_active)
    from data_loader_supabase import get_casinos_full
except Exception:
    get_casinos_full = None
from data_loader_supabase import load_game_data  # used elsewhere

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
            # new nearby filtering fields
            "use_my_location": False,
            "nearby_radius": 30,  # miles
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
        "use_my_location": False,
        "nearby_radius": 30,
    }

# Nearby distance
def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return float("inf")
    R = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def _casino_selector(disabled: bool) -> str:
    # Use new richer fetch if present; fall back to legacy
    if get_casinos_full is not None:
        df = get_casinos_full(active_only=True)
        all_names = df["name"].dropna().astype(str).tolist()
        all_names = [n for n in all_names if n and n != "Other..."]
        # Nearby filter UI
        st.caption("Filter casinos near you (requires location permission)")
        cA, cB = st.columns([1,1])
        with cA:
            use_my_location = st.checkbox("Use my location",
                                          value=st.session_state.trip_settings.get("use_my_location", False),
                                          key="use_my_location",
                                          disabled=disabled)
            st.session_state.trip_settings["use_my_location"] = use_my_location
        with cB:
            radius_miles = st.slider("Radius (miles)", 5, 100,
                                     int(st.session_state.trip_settings.get("nearby_radius", 30)),
                                     step=5, key="nearby_radius", disabled=disabled)
            st.session_state.trip_settings["nearby_radius"] = int(radius_miles)

        options = list(all_names)
        if use_my_location and not disabled:
            if geolocation is None:
                st.info("Install 'streamlit-geolocation' to enable location filter.")
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
                # if no permission, fall back silently

        current = st.session_state.trip_settings.get("casino", "")
        if current not in options and options:
            # try to keep previously picked casino if still in all_names
            if current in all_names:
                pass  # will be added by options if not using filter
            else:
                current = options[0]
        try:
            default_index = options.index(current) if current in options else 0
        except Exception:
            default_index = 0
        sel = st.selectbox("Casino", options=options, index=default_index, disabled=disabled)
        return sel.strip()

    # Legacy simple list fallback (shouldn't be used now, but safe default)
    from data_loader_supabase import get_casinos
    casinos = [c for c in get_casinos() if c and c != "Other..."]
    current = st.session_state.trip_settings.get("casino", "")
    try:
        default_index = casinos.index(current) if current in casinos else 0
    except Exception:
        default_index = 0
    sel = st.selectbox("Casino", options=casinos, index=default_index, disabled=disabled)
    if sel == "Other...":
        return st.text_input("Custom Casino", value=current if current not in casinos else "", disabled=disabled).strip()
    return sel.strip()

def render_sidebar() -> None:
    initialize_trip_state()
    with st.sidebar:
        st.header("🎯 Trip Settings")
        disabled = st.session_state.trip_started

        casino_choice = _casino_selector(disabled=disabled)
        start_bankroll = st.number_input("Total Trip Bankroll ($)", min_value=0.0, step=10.0,
                                         value=float(st.session_state.trip_settings.get("starting_bankroll", 200.0)),
                                         disabled=disabled)
        num_sessions = st.number_input("Number of Sessions", min_value=1, step=1,
                                       value=int(st.session_state.trip_settings.get("num_sessions", 3)),
                                       disabled=disabled)

        # Save back
        st.session_state.trip_settings["casino"] = casino_choice
        st.session_state.trip_settings["starting_bankroll"] = float(start_bankroll)
        st.session_state.trip_settings["num_sessions"] = int(num_sessions)

        # Derived
        per_session = get_session_bankroll()
        st.caption(f"Per-session bankroll estimate: ${per_session:,.2f}")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Start New Trip", disabled=st.session_state.trip_started, use_container_width=True):
                st.session_state.trip_started = True
                st.session_state.current_trip_id += 1
                st.session_state.trip_bankrolls[st.session_state.current_trip_id] = float(start_bankroll)
                st.success("Trip started.")
                st.rerun()
        with c2:
            if st.button("Stop Trip", disabled=not st.session_state.trip_started, use_container_width=True):
                st.session_state.trip_started = False
                _reset_trip_defaults()
                st.info("Trip stopped and settings reset.")
                st.rerun()

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

def record_session_performance(profit: float) -> None:
    profits = st.session_state.get("recent_profits", [])
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
    import math as _m
    std = _m.sqrt(var)
    std_clamped = min(200.0, std)
    if std_clamped <= 20.0:
        return 1.05
    if std_clamped >= 120.0:
        return 0.9
    return 1.0

def get_current_trip_sessions() -> List[Dict[str, Any]]:
    return [s for s in st.session_state.session_log if s.get("trip_id") == st.session_state.current_trip_id]

def add_session_to_trip(session: Dict[str, Any]) -> None:
    st.session_state.session_log.append(session)

def get_blacklisted_games() -> List[str]:
    return sorted(list(st.session_state.blacklisted_games))

def blacklist_game(game_name: str) -> None:
    st.session_state.blacklisted_games.add(game_name)

def remove_blacklist(game_name: str) -> None:
    st.session_state.blacklisted_games.discard(game_name)

def spend_bankroll(amount: float) -> None:
    tid = st.session_state.get("current_trip_id", 0)
    st.session_state.trip_bankrolls[tid] = max(0.0, float(st.session_state.trip_bankrolls.get(tid, 0.0)) - float(amount))

def add_bankroll(amount: float) -> None:
    tid = st.session_state.get("current_trip_id", 0)
    st.session_state.trip_bankrolls[tid] = float(st.session_state.trip_bankrolls.get(tid, 0.0)) + float(amount)
