from __future__ import annotations

import os
import math
from typing import List, Dict, Any, Optional
import streamlit as st
import requests

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

# ---- Data access
try:
    from data_loader_supabase import get_casinos_full  # DataFrame: name, city, state, latitude, longitude, is_active
except Exception:
    get_casinos_full = None

try:
    from data_loader_supabase import get_casinos  # List[str]
except Exception:
    get_casinos = None


# =========================
# Session state init
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
    Try browser geolocation (streamlit component). If not available,
    fall back to IP-based coarse geolocation (no user input).
    Returns (lat, lon, source) where source in {"browser","ip","none"}.
    """
    # 1) Browser geolocation via component
    if geolocation is not None:
        try:
            coords = geolocation(key="geo_widget")
            if coords and "latitude" in coords and "longitude" in coords:
                return float(coords["latitude"]), float(coords["longitude"]), "browser"
        except Exception:
            pass

    # 2) IP-based (coarse) geolocation — no keys needed
    try:
        resp = requests.get("https://ipapi.co/json/", timeout=2.0)
        if resp.ok:
            j = resp.json()
            lat = _to_float_or_none(j.get("latitude"))
            lon = _to_float_or_none(j.get("longitude"))
            if lat is not None and lon is not None:
                return lat, lon, "ip"
    except Exception:
        pass

    return None, None, "none"


def _nearby_filter_options(disabled: bool) -> List[str]:
    """
    Returns the casino list, optionally filtered by user location.
    Adds a debug expander and auto-fixes US longitude sign if they look positive.
    """
    all_names, df = _load_casino_names_df()
    info = {
        "enabled": ENABLE_NEARBY,
        "ui_enabled": not disabled,
        "use_my_location": bool(st.session_state.trip_settings.get("use_my_location", False)),
        "applied": False,
        "fallback_all": False,
        "geo_source": "none",
        "radius_miles": int(st.session_state.trip_settings.get("nearby_radius", 30)),
        "nearby_count": 0,
        "total": len(all_names),
        "with_coords": 0,
        "reason": "",
    }

    if not ENABLE_NEARBY:
        st.session_state["_nearby_info"] = info
        return all_names

    st.caption("Filter casinos near you")
    colA, colB = st.columns([1, 1])
    with colA:
        use_ml_now = st.checkbox("Use my location",
                                 value=info["use_my_location"],
                                 disabled=disabled)
    with colB:
        radius_now = st.slider("Radius (miles)", 5, 300,  # allow larger for quick sanity checks
                               info["radius_miles"], step=5, disabled=disabled)

    # persist
    st.session_state.trip_settings["use_my_location"] = bool(use_ml_now)
    st.session_state.trip_settings["nearby_radius"]   = int(radius_now)
    info["use_my_location"] = bool(use_ml_now)
    info["radius_miles"]    = int(radius_now)

    # Need coords to filter against
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

    # --- Auto-fix obvious US longitude sign mistakes (e.g., +93 instead of -93) ---
    # If most longitudes are positive while user will be in US (negative lon),
    # flip them to negative as a safe heuristic.
    try:
        pos_ratio = float((df["longitude"] > 0).sum()) / float(len(df))
        if pos_ratio >= 0.8:  # 80%+ positive longitudes → likely missing negative sign
            df["longitude"] = df["longitude"].apply(lambda x: -abs(x) if x is not None else None)
    except Exception:
        pass

    if not info["use_my_location"]:
        info["reason"] = "use_my_location_off"
        st.session_state["_nearby_info"] = info
        return all_names

    # Get user coords (browser → IP)
    user_lat = user_lon = None
    if geolocation is not None:
        try:
            coords = geolocation(key="geo_widget_sidebar_autorun")
            if coords and "latitude" in coords and "longitude" in coords:
                user_lat = _to_float_or_none(coords["latitude"])
                user_lon = _to_float_or_none(coords["longitude"])
                if user_lat is not None and user_lon is not None:
                    info["geo_source"] = "browser"
        except Exception:
            pass
    if user_lat is None or user_lon is None:
        try:
            import requests
            r = requests.get("https://ipapi.co/json/", timeout=2.0)
            if r.ok:
                j = r.json()
                user_lat = _to_float_or_none(j.get("latitude"))
                user_lon = _to_float_or_none(j.get("longitude"))
                if user_lat is not None and user_lon is not None:
                    info["geo_source"] = "ip"
        except Exception:
            pass

    if user_lat is None or user_lon is None:
        info["reason"] = "no_user_coords"
        st.session_state["_nearby_info"] = info
        return all_names

    # Compute distances
    info["applied"] = True
    df["distance_mi"] = df.apply(
        lambda r: _haversine_miles(r.get("latitude"), r.get("longitude"), user_lat, user_lon),
        axis=1
    )
    nearby = df[df["distance_mi"].notna()].sort_values("distance_mi")

    # ---- Debug: show what we’re seeing (top 10 closest) ----
    with st.expander("Nearby filter debug", expanded=False):
        st.write({
            "user_coords": {"lat": user_lat, "lon": user_lon},
            "geo_source": info["geo_source"],
            "radius_miles": info["radius_miles"],
            "rows_with_coords": int(info["with_coords"]),
            "closest_min_mi": float(nearby["distance_mi"].iloc[0]) if not nearby.empty else None,
        })
        st.dataframe(nearby[["name","city","state","latitude","longitude","distance_mi"]].head(10), use_container_width=True)

    # Apply radius
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

        # --- status badge that reflects actual filter state ---
                # --- accurate badge ---
                # --- accurate badge, no 'badge' variable ---
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
                    suffix = " (browser)" if source == "browser" else " (approx via IP)" if source == "ip" else ""
                    st.caption(f"📍 near‑me: ON • radius: {radius} mi • results: {nearby_count}{suffix}")
                elif applied and fallback_all:
                    st.caption(f"📍 near‑me: ON • radius: {radius} mi • 0 in range — showing all")
                else:
                    st.caption(f"📍 near‑me: ON • radius: {radius} mi • filter not applied")

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