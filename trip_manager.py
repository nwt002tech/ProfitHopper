from __future__ import annotations

import os
import math
from typing import List, Dict, Any, Optional
import streamlit as st

# ---- Robust geolocation import (supports both export names) ----
geolocation = None
try:
    from streamlit_geolocation import geolocation as _geo_func
    geolocation = _geo_func
except Exception:
    try:
        from streamlit_geolocation import streamlit_geolocation as _geo_func2
        geolocation = _geo_func2
    except Exception:
        geolocation = None

# ---- Feature flag: ENABLE_NEARBY from env OR secrets ----
def _truthy(val: Optional[str]) -> bool:
    if val is None:
        return False
    return str(val).strip().lower() in ("1", "true", "yes", "on", "y")

def _flag_from_env_or_secrets(key: str, default: bool=False) -> bool:
    if key in os.environ:
        return _truthy(os.environ.get(key))
    if hasattr(st, "secrets") and key in st.secrets:
        return _truthy(st.secrets.get(key))
    if hasattr(st, "secrets") and "general" in st.secrets and key in st.secrets["general"]:
        return _truthy(st.secrets["general"].get(key))
    return default

ENABLE_NEARBY = _flag_from_env_or_secrets("ENABLE_NEARBY", default=False)

# ---- Your data access (unchanged API) ----
try:
    # Preferred: full DF with columns incl. name, city, state, (lat/lon variants), is_active
    from data_loader_supabase import get_casinos_full  # -> DataFrame
except Exception:
    get_casinos_full = None

try:
    # Fallback: simple list[str] of names
    from data_loader_supabase import get_casinos  # -> List[str]
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


# =========================
# Helpers
# =========================
def _to_float_or_none(v):
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if s == "" or s.lower() == "nan":
            return None
        return float(s)
    except Exception:
        return None

def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    lat1 = _to_float_or_none(lat1)
    lon1 = _to_float_or_none(lon1)
    lat2 = _to_float_or_none(lat2)
    lon2 = _to_float_or_none(lon2)
    if None in (lat1, lon1, lat2, lon2):
        return float("inf")
    R = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def _normalize_coord_columns(df):
    """
    Ensure the dataframe has float columns 'latitude' and 'longitude',
    accepting common variants like 'lat'/'lng' and string values.
    """
    if "latitude" not in df.columns and "lat" in df.columns:
        df = df.rename(columns={"lat": "latitude"})
    if "longitude" not in df.columns and "lng" in df.columns:
        df = df.rename(columns={"lng": "longitude"})
    if "latitude" in df.columns:
        df["latitude"] = [_to_float_or_none(v) for v in df["latitude"]]
    if "longitude" in df.columns:
        df["longitude"] = [_to_float_or_none(v) for v in df["longitude"]]
    return df


def _load_casino_names_df():
    """
    Returns (names_list, df) where df may include:
    name, city, state, latitude, longitude, is_active.
    This function normalizes coord columns so downstream code always sees
    numeric 'latitude'/'longitude' if present at all.
    """
    df = None
    names = []
    # Prefer the rich DF
    if callable(get_casinos_full):
        try:
            df = get_casinos_full(active_only=True)
        except Exception:
            df = None
    # Fallback to names only
    if df is None and callable(get_casinos):
        try:
            names = [c for c in (get_casinos() or []) if c]
        except Exception:
            names = []

    # If we have a DF, normalize and pull names
    if df is not None and getattr(df, "empty", True) is False:
        # make sure we have a 'name' column
        if "name" in df.columns:
            # normalize coordinates (lat/lng -> latitude/longitude, to float)
            df = _normalize_coord_columns(df)
            # Respect is_active if present
            if "is_active" in df.columns:
                df = df[df["is_active"] == True].copy()
            names = df["name"].dropna().astype(str).tolist()
        else:
            # no 'name' column? fall back to names list if we had one
            df = None

    names = [n for n in names if n and n != "Other..."]
    return names, df


def _nearby_filter_options(disabled: bool) -> List[str]:
    """
    Returns the casino list, optionally filtered by user location.
    Writes a diagnostic dict to st.session_state["_nearby_info"] so the badge
    can report whether the filter was actually applied.
    """
    all_names, df = _load_casino_names_df()
    info = {
        "enabled": ENABLE_NEARBY,
        "applied": False,
        "fallback_all": False,
        "geo_source": "none",
        "radius_miles": int(st.session_state.trip_settings.get("nearby_radius", 30)),
        "nearby_count": 0,
        "total": len(all_names),
        "with_coords": 0,
        "user_lat": None,
        "user_lon": None,
    }

    if not ENABLE_NEARBY or disabled:
        st.session_state["_nearby_info"] = info
        return all_names

    st.caption("Filter casinos near you")
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
        info["radius_miles"] = int(radius_miles)

    # Prepare DF with coords
    if df is None or "latitude" not in df.columns or "longitude" not in df.columns:
        st.info("No coordinates found for casinos yet — showing all.")
        st.session_state["_nearby_info"] = info
        return all_names
    df = df.copy()
    df = _normalize_coord_columns(df)
    info["with_coords"] = int((df["latitude"].notna() & df["longitude"].notna()).sum())

    if not use_my_location:
        st.session_state["_nearby_info"] = info
        return all_names

    # Get user coords
    user_lat = user_lon = None
    if geolocation is not None:
        coords = geolocation()
        if coords and "latitude" in coords and "longitude" in coords:
            user_lat, user_lon = coords["latitude"], coords["longitude"]
            info["geo_source"] = "browser"
    if user_lat is None or user_lon is None:
        st.info("Enter your location manually (browser location unavailable).")
        col1, col2 = st.columns(2)
        with col1:
            user_lat = st.number_input(
                "Your latitude", value=float(st.session_state.trip_settings.get("manual_lat") or 0.0),
                step=0.0001, format="%.6f"
            )
        with col2:
            user_lon = st.number_input(
                "Your longitude", value=float(st.session_state.trip_settings.get("manual_lon") or 0.0),
                step=0.0001, format="%.6f"
            )
        st.session_state.trip_settings["manual_lat"] = user_lat
        st.session_state.trip_settings["manual_lon"] = user_lon
        if user_lat != 0.0 or user_lon != 0.0:
            info["geo_source"] = "manual"

    info["user_lat"], info["user_lon"] = user_lat, user_lon

    # If we still have no coords, we cannot apply the filter
    if user_lat in (None, 0.0) and user_lon in (None, 0.0):
        st.session_state["_nearby_info"] = info
        return all_names

    # Compute distances and apply filter
    info["applied"] = True
    df["distance_mi"] = df.apply(
        lambda r: _haversine_miles(r.get("latitude"), r.get("longitude"), user_lat, user_lon),
        axis=1
    )
    nearby = df[df["distance_mi"] <= float(radius_miles)].copy()
    nearby = nearby[nearby["name"].notna()]
    info["nearby_count"] = int(len(nearby))

    if nearby.empty:
        info["fallback_all"] = True
        st.session_state["_nearby_info"] = info
        return all_names

    nearby = nearby.sort_values("distance_mi")
    st.session_state["_nearby_info"] = info
    return nearby["name"].astype(str).tolist()


# =========================
# Sidebar (keeps your existing UI/logic) + accurate badge
# =========================
def render_sidebar() -> None:
    initialize_trip_state()
    with st.sidebar:
        st.header("🎯 Trip Settings")
        disabled = bool(st.session_state.trip_started)

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

        # --- status badge that reflects actual filter state ---
        if ENABLE_NEARBY:
            info = st.session_state.get("_nearby_info", {}) or {}
            radius = int(st.session_state.trip_settings.get("nearby_radius", 30))
            applied = bool(info.get("applied"))
            fallback_all = bool(info.get("fallback_all"))
            nearby_count = int(info.get("nearby_count", 0)) if applied else 0

            if applied and not fallback_all:
                badge = f"📍 near‑me: ON  •  radius: {radius} mi  •  results: {nearby_count}"
            elif applied and fallback_all:
                badge = f"📍 near‑me: ON  •  radius: {radius} mi  •  0 in range — showing all"
            else:
                badge = f"📍 near‑me: ON  •  radius: {radius} mi  •  filter not applied"

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