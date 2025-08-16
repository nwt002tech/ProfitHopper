# trip_manager.py
from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import streamlit as st

# Data
try:
    from data_loader_supabase import get_casinos_full
except Exception:
    get_casinos_full = None

# Distance: try your utils, else simple fallback
try:
    from utils import haversine_miles as _haversine
except Exception:
    from math import radians, sin, cos, asin, sqrt
    def _haversine(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
        R = 3958.7613
        dlat = radians(b_lat - a_lat); dlon = radians(b_lon - a_lon)
        a = sin(dlat/2)**2 + cos(radians(a_lat))*cos(radians(b_lat))*sin(dlon/2)**2
        return 2 * R * asin(sqrt(a))

# Geolocation component API
from browser_location import render_geo_target, request_location  # provided above


# ===================== Public API (kept stable) =====================

def initialize_trip_state() -> None:
    st.session_state.setdefault("trip_active", False)
    st.session_state.setdefault("current_trip_id", None)

    st.session_state.setdefault("trip_settings", {
        "near_me": False,
        "nearby_radius": 30,
        "selected_casino": None,
        "casino": None,               # for session_manager compatibility
        "selected_game": None,
        "starting_bankroll": 0.0,     # for session_manager compatibility
    })

    st.session_state.setdefault("user_coords", None)   # {"lat":..,"lon":..}
    st.session_state.setdefault("geo_source", None)
    st.session_state.setdefault("_ph_prev_nearme", False)

    # keep safe defaults used elsewhere
    st.session_state.setdefault("win_streak_factor", 1.0)
    st.session_state.setdefault("volatility_adjustment", 1.0)


def get_session_bankroll() -> float:
    return float(st.session_state.get("session_bankroll", 0.0))


def get_current_bankroll() -> float:
    return float(st.session_state.get("current_bankroll", 0.0))


def get_blacklisted_games() -> List[str]:
    return st.session_state.get("blacklist_games", []) or []


def blacklist_game(game_name: str) -> None:
    bl = set(st.session_state.get("blacklist_games", []))
    bl.add(game_name)
    st.session_state["blacklist_games"] = sorted(bl)


def get_volatility_adjustment() -> float:
    return float(st.session_state.get("volatility_adjustment", 1.0))


def get_win_streak_factor() -> float:
    return float(st.session_state.get("win_streak_factor", 1.0))


def get_current_trip_sessions() -> List[Dict[str, Any]]:
    return st.session_state.get("trip_sessions", []) or []


def record_session_performance(*_, **__) -> None:
    return


# ===================== Sidebar =====================

def render_sidebar() -> None:
    initialize_trip_state()
    ts: Dict[str, Any] = st.session_state["trip_settings"]

    with st.sidebar:
        _inject_compact_css()
        st.markdown("### 🎯 Trip Settings")

        _near_row_and_controls(ts)

        # Casino selector (filters if near-me + coords present)
        casino_choice = _casino_selector(ts)
        ts["selected_casino"] = casino_choice
        ts["casino"] = casino_choice  # mirror key used elsewhere

        # Game selector (leave your existing logic; placeholder keeps prior)
        prev_game = ts.get("selected_game")
        ts["selected_game"] = st.selectbox("Game", [prev_game] if prev_game else ["Select a game"], index=0)

        # Start / Stop on one line
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Start Trip", use_container_width=True):
                st.session_state["trip_active"] = True
                if not st.session_state.get("current_trip_id"):
                    st.session_state["current_trip_id"] = 1
                st.success("Trip started")
                st.rerun()
        with c2:
            if st.button("Stop Trip", type="secondary", use_container_width=True):
                st.session_state["trip_active"] = False
                st.info("Trip stopped")
                st.rerun()


def _near_row_and_controls(ts: Dict[str, Any]) -> None:
    # Icon (visual only)
    render_geo_target()

    # Same-line label
    st.markdown('<div class="ph-nearme-label">Locate casinos near me</div>', unsafe_allow_html=True)

    # Toggle → on transition, actively request location
    prev = bool(st.session_state.get("_ph_prev_nearme", False))
    ts["near_me"] = st.toggle("Use near-me filter", value=bool(ts.get("near_me", False)),
                              label_visibility="collapsed")
    st.session_state["_ph_prev_nearme"] = bool(ts["near_me"])

    if ts["near_me"] and not prev and st.session_state.get("user_coords") is None:
        # Prompt browser and store coords to session; reruns on success
        request_location()

    # Radius
    ts["nearby_radius"] = int(st.slider("Radius (mi)", 5, 300, int(ts.get("nearby_radius", 30)),
                                        step=5, label_visibility="collapsed"))

    # Clear
    if st.button("Clear", key="ph_clear_loc", use_container_width=True):
        ts["near_me"] = False
        st.session_state["user_coords"] = None
        st.session_state["geo_source"] = None
        st.session_state["_ph_prev_nearme"] = False
        st.rerun()

    # Badge
    if not ts["near_me"]:
        st.caption(f"📍 near-me: OFF • radius: {ts['nearby_radius']} mi")
    else:
        coords = st.session_state.get("user_coords")
        if not coords:
            st.caption(f"📍 near-me: ON • radius: {ts['nearby_radius']} mi • waiting for location")
        else:
            st.caption(f"📍 near-me: ON • radius: {ts['nearby_radius']} mi • filtering…")


# ===================== Filtering =====================

def _casinos_df() -> pd.DataFrame:
    try:
        if callable(get_casinos_full):
            df = get_casinos_full(active_only=False)
            if isinstance(df, pd.DataFrame):
                if "is_active" not in df.columns:
                    df["is_active"] = True
                return df
    except Exception as e:
        st.caption(f"[get_casinos_full] fallback: {e}")
    return pd.DataFrame(columns=["casino_name", "name", "casino", "city", "state", "latitude", "longitude", "is_active"])


def _name_col(df: pd.DataFrame) -> Optional[str]:
    for c in ("casino_name", "name", "casino"):
        if c in df.columns:
            return c
    return None


def _names_from_df(df: pd.DataFrame) -> List[str]:
    col = _name_col(df)
    if not col:
        return []
    return (
        df[col].dropna().astype(str).drop_duplicates().sort_values(key=lambda s: s.str.lower()).tolist()
    )


def _filtered_casino_names_by_location(radius_miles: int) -> Tuple[List[str], Dict[str, Any]]:
    df = _casinos_df()
    ncol = _name_col(df)
    if not ncol:
        return [], {"reason": "no-name-col"}

    if "is_active" in df.columns:
        if df["is_active"].dtype == bool:
            df = df[df["is_active"]]
        else:
            df = df[df["is_active"] == True]  # noqa: E712

    # coords present?
    coords = st.session_state.get("user_coords")
    if not coords:
        return _names_from_df(df), {"reason": "no-user-coords"}

    # coord columns
    lat_col = None; lon_col = None
    for a, b in (("latitude", "longitude"), ("lat", "lon")):
        if a in df.columns and b in df.columns:
            lat_col, lon_col = a, b; break
    if not lat_col or not lon_col:
        return _names_from_df(df), {"reason": "no-coord-cols"}

    df2 = df.dropna(subset=[lat_col, lon_col]).copy()
    if df2.empty:
        return _names_from_df(df), {"reason": "no-row-coords"}

    u_lat, u_lon = float(coords["lat"]), float(coords["lon"])
    df2["__mi"] = df2.apply(lambda r: _haversine(float(r[lat_col]), float(r[lon_col]), u_lat, u_lon), axis=1)
    within = df2[df2["__mi"] <= float(radius_miles)].sort_values("__mi")

    if within.empty:
        return _names_from_df(df), {"reason": "0-in-range-show-all"}

    names = within[ncol].dropna().astype(str).tolist()
    return names, {
        "radius_miles": int(radius_miles),
        "results": int(len(names)),
        "closest_min_mi": float(within["__mi"].min()) if not within.empty else None,
    }


def _casino_selector(ts: Dict[str, Any]) -> Optional[str]:
    df = _casinos_df()
    if ts.get("near_me") and st.session_state.get("user_coords"):
        names, _ = _filtered_casino_names_by_location(int(ts.get("nearby_radius", 30)))
        options = names if names else _names_from_df(df)
    else:
        options = _names_from_df(df)

    if not options:
        return None

    default = ts.get("selected_casino") or ts.get("casino")
    if default not in options:
        default = options[0]
    return st.selectbox("Casino", options, index=options.index(default))


# ===================== CSS =====================

def _inject_compact_css() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] .block-container {
          padding-top: 6px !important;
          padding-bottom: 6px !important;
        }
        .ph-nearme-label{
          position: relative;
          display: inline-block;
          white-space: nowrap;
          font-weight: 600;
          top: -28px;
          left: 48px;
          margin-bottom: -18px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )