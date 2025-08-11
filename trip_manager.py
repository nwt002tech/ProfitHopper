from __future__ import annotations

import os
import math
from typing import List, Dict, Any, Optional
import streamlit as st

# Optional geolocation component (we only use browser coords from session)
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

# Enable/disable the nearby feature globally via env/secrets
ENABLE_NEARBY = _flag_from_env_or_secrets("ENABLE_NEARBY", default=True)


# ---- Data access: use your existing loader; do not modify it ----
try:
    from data_loader_supabase import get_casinos_full  # -> DataFrame
except Exception:
    get_casinos_full = None

try:
    from data_loader_supabase import get_casinos  # -> List[str]
except Exception:
    get_casinos = None


# =========================
# Session state init (unchanged API)
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


def _load_casino_names_df():
    """
    Returns (names_list, df) where df may include:
    name, city, state, latitude, longitude, is_active.
    """
    df = None
    names = []
    if callable(get_casinos_full):
        try:
            df = get_casinos_full(active_only=True)
        except Exception:
            df = None
    if df is None and callable(get_casinos):
        try:
            names = [c for c in (get_casinos() or []) if c]
        except Exception:
            names = []
    if df is not None and getattr(df, "empty", True) is False and "name" in df.columns:
        names = df["name"].dropna().astype(str).tolist()
        # ensure numeric coords
        for col in ("latitude", "longitude"):
            if col in df.columns:
                df[col] = [_to_float_or_none(v) for v in df[col]]
        if "is_active" in df.columns:
            df = df[df["is_active"] == True].copy()
    names = [n for n in names if n and n != "Other..."]
    return names, df


def _get_user_coords_auto() -> tuple[Optional[float], Optional[float], str]:
    """
    Use the browser coords captured in st.session_state by app.py.
    No IP fallback here (server IP can be wrong region).
    """
    lat = st.session_state.get("client_lat")
    lon = st.session_state.get("client_lon")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        return float(lat), float(lon), "browser"
    return None, None, "none"


def _nearby_filter_options(disabled: bool) -> List[str]:
    """
    Returns the casino list, optionally filtered by user location.
    Uses only browser coords saved in session (accurate per-user).
    """
    all_names, df = _load_casino_names_df()
    info = {
        "enabled": ENABLE_NEARBY,
        "ui_enabled": not disabled,
        "use_my_location": bool(st.session_state.trip_settings.get("use_my_location", False)),
        "applied": False,
        "fallback_all": False,
        "geo_source": "none",           # 'browser' | 'none'
        "radius_miles": int(st.session_state.trip_settings.get("nearby_radius", 30)),
        "nearby_count": 0,
        "total": len(all_names),
        "with_coords": 0,
        "reason": "",                   # debugging text
    }

    if not ENABLE_NEARBY:
        st.session_state["_nearby_info"] = info
        return all_names

    # UI controls
    st.caption("Filter casinos near you")
    colA, colB = st.columns([1, 1])
    with colA:
        use_ml = st.checkbox("Use my location", value=info["use_my_location"], key="use_my_location", disabled=disabled)
    with colB:
        radius = st.slider("Radius (miles)", 5, 300, info["radius_miles"], step=5, key="nearby_radius", disabled=disabled)
    info["use_my_location"] = bool(use_ml)
    info["radius_miles"] = int(radius)

    # Need DF with coords
    if df is None or "latitude" not in df.columns or "longitude" not in df.columns:
        info["reason"] = "no_casino_coords_df"
        st.session_state["_nearby_info"] = info
        return all_names
    df = df.copy()
    for col in ("latitude", "longitude"):
        df[col] = [_to_float_or_none(v) for v in df[col]]
    info["with_coords"] = int((df["latitude"].notna() & df["longitude"].notna()).sum())
    if info["with_coords"] == 0:
        info["reason"] = "no_casino_coords_rows"
        st.session_state["_nearby_info"] = info
        return all_names

    # If user opted out, do not filter
    if not info["use_my_location"]:
        info["reason"] = "use_my_location_off"
        st.session_state["_nearby_info"] = info
        return all_names

    # Get user coords (must come from sidebar 'Share your location' in app.py)
    user_lat, user_lon, source = _get_user_coords_auto()
    info["geo_source"] = source

    if user_lat is None or user_lon is None:
        info["reason"] = "waiting_for_browser_location"
        st.info("Click **Share your location** in the sidebar to enable near‑me.")
        st.session_state["_nearby_info"] = info
        return all_names

    # Compute distances and apply filter
    info["applied"] = True

    # Auto-fix obvious US longitude sign mistakes if data was entered as positive
    try:
        pos_ratio = float((df["longitude"] > 0).sum()) / float(len(df))
        if pos_ratio >= 0.8:
            df["longitude"] = df["longitude"].apply(lambda x: -abs(x) if x is not None else None)
    except Exception:
        pass

    df["distance_mi"] = df.apply(
        lambda r: _haversine_miles(r.get("latitude"), r.get("longitude"), user_lat, user_lon),
        axis=1
    )
    nearby = df[df["distance_mi"].notna()].sort_values("distance_mi")

    within = nearby[nearby["distance_mi"] <= float(info["radius_miles"])].copy()
    info["nearby_count"] = int(len(within))

    if within.empty:
        info["fallback_all"] = True
        info["reason"] = "no_matches"
        st.session_state["_nearby_info"] = info
        return all_names

    st.session_state["_nearby_info"] = info
    return within["name"].astype(str).tolist()


# =========================
# Sidebar + accurate badge
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

        # Accurate badge
        if ENABLE_NEARBY:
            info = st.session_state.get("_nearby_info", {}) or {}
            use_loc = bool(st.session_state.trip_settings.get("use_my_location", False))
            radius = int(st.session_state.trip_settings.get("nearby_radius", 30))

            if not use_loc:
                st.caption("📍 near‑me: OFF")
            else:
                applied = bool(info.get("applied"))
                fallback_all = bool(info.get("fallback_all"))
                nearby_count = int(info.get("nearby_count", 0)) if applied else 0
                source = (info.get("geo_source") or "none").lower()

                if applied and not fallback_all:
                    suffix = " (browser)" if source == "browser" else ""
                    st.caption(f"📍 near‑me: ON • radius: {radius} mi • results: {nearby_count}{suffix}")
                elif applied and fallback_all:
                    st.caption(f"📍 near‑me: ON • radius: {radius} mi • 0 in range — showing all")
                else:
                    st.caption(f"📍 near‑me: ON • radius: {radius} mi • waiting for location")

        # Your existing settings continue here
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