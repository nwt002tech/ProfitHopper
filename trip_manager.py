from __future__ import annotations

import math
from typing import List, Dict, Any, Optional, Tuple
import streamlit as st
import pandas as pd

from data_loader_supabase import get_casinos, get_casinos_full
from browser_location import request_location_inline, clear_location


# ---------- Session ----------
def initialize_trip_state() -> None:
    if "trip_started" not in st.session_state: st.session_state.trip_started = False
    if "current_trip_id" not in st.session_state: st.session_state.current_trip_id = 0
    if "trip_settings" not in st.session_state or not isinstance(st.session_state.trip_settings, dict):
        st.session_state.trip_settings = {
            "casino": "",
            "starting_bankroll": 200.0,
            "num_sessions": 3,
            "nearby_radius": 30,
        }
    if "trip_bankrolls" not in st.session_state: st.session_state.trip_bankrolls = {}
    if "blacklisted_games" not in st.session_state: st.session_state.blacklisted_games = set()
    if "recent_profits" not in st.session_state: st.session_state.recent_profits = []
    if "session_log" not in st.session_state: st.session_state.session_log = []


def _reset_trip_defaults() -> None:
    st.session_state.trip_settings = {
        "casino": "",
        "starting_bankroll": 200.0,
        "num_sessions": 3,
        "nearby_radius": 30,
    }


# ---------- Helpers ----------
def _to_float_or_none(v):
    try:
        if v is None: return None
        if isinstance(v, (int, float)): return float(v)
        s = str(v).strip()
        if s == "" or s.lower() in ("nan", "none", "null"): return None
        return float(s)
    except Exception:
        return None


def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    lat1=_to_float_or_none(lat1); lon1=_to_float_or_none(lon1)
    lat2=_to_float_or_none(lat2); lon2=_to_float_or_none(lon2)
    if None in (lat1, lon1, lat2, lon2): return float("inf")
    R=3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def _all_casino_names() -> List[str]:
    names = get_casinos() or []
    names = sorted({str(n).strip() for n in names if str(n).strip()}, key=lambda s: s.lower())
    if "Other..." not in names:
        names.append("Other...")
    return names


def _ensure_df(obj) -> Optional[pd.DataFrame]:
    if obj is None:
        return None
    if isinstance(obj, pd.DataFrame):
        return obj.copy()
    if isinstance(obj, list):
        if not obj:
            return pd.DataFrame()
        if isinstance(obj[0], dict):
            return pd.DataFrame(obj)
        return pd.DataFrame(obj, columns=["name"])
    if isinstance(obj, dict):
        return pd.DataFrame([obj])
    return None


def _pick_name_column(df: pd.DataFrame) -> Optional[str]:
    # Accept common variants
    for cand in ("name", "casino", "casino_name", "title"):
        if cand in df.columns:
            return cand
    # case-insensitive fallback
    low = {c.lower(): c for c in df.columns}
    for cand in ("name", "casino", "casino_name", "title"):
        if cand in low:
            return low[cand]
    return None


def _pick_coord_columns(df: pd.DataFrame) -> Optional[Tuple[str, str]]:
    low = {c.lower(): c for c in df.columns}
    for a, b in (("latitude", "longitude"), ("lat", "lon"), ("lat", "lng")):
        if a in low and b in low:
            return low[a], low[b]
    return None


def _filtered_casino_names_by_location(radius_mi: int) -> Tuple[List[str], dict]:
    dbg = {"have_user_coords": False, "rows": 0, "with_coords": 0, "in_range": 0}

    user_lat = st.session_state.get("client_lat")
    user_lon = st.session_state.get("client_lon")
    if user_lat is None or user_lon is None:
        return _all_casino_names(), dbg

    dbg["have_user_coords"] = True

    raw = get_casinos_full(active_only=True)
    df = _ensure_df(raw)
    if df is None or df.empty:
        return _all_casino_names(), dbg
    dbg["rows"] = int(len(df))

    if "is_active" in df.columns:
        df = df[df["is_active"] == True]

    name_col = _pick_name_column(df)
    coord_pair = _pick_coord_columns(df)
    if not name_col or not coord_pair:
        return _all_casino_names(), dbg
    lat_col, lon_col = coord_pair

    df = df[[name_col, lat_col, lon_col]].copy()
    df[lat_col] = df[lat_col].apply(_to_float_or_none)
    df[lon_col] = df[lon_col].apply(_to_float_or_none)
    df = df[df[lat_col].notna() & df[lon_col].notna()].copy()
    dbg["with_coords"] = int(len(df))
    if df.empty:
        return _all_casino_names(), dbg

    # Fix common US longitude sign issue
    try:
        pos_ratio = float((df[lon_col] > 0).sum()) / max(1.0, float(len(df)))
        if pos_ratio >= 0.8:
            df[lon_col] = df[lon_col].apply(lambda x: -abs(x) if x is not None else None)
    except Exception:
        pass

    df["distance_mi"] = df.apply(
        lambda r: _haversine_miles(user_lat, user_lon, r.get(lat_col), r.get(lon_col)), axis=1
    )
    within = df[df["distance_mi"].notna() & (df["distance_mi"] <= float(radius_mi))].copy()
    dbg["in_range"] = int(len(within))

    if within.empty:
        names = _all_casino_names()
    else:
        names = sorted(within[name_col].astype(str).tolist(), key=lambda s: s.lower())
        if "Other..." not in names:
            names.append("Other...")

    return names, dbg


# ---------- Sidebar ----------
def render_sidebar() -> None:
    initialize_trip_state()
    with st.sidebar:
        st.markdown("### 🎯 Trip Settings")
        disabled = bool(st.session_state.trip_started)

        # Row 1: single-line control + radius + clear
        col_btn, col_radius, col_clear = st.columns([0.62, 0.23, 0.15])

        with col_btn:
            if st.button("🎯 Locate casinos near me", use_container_width=True, disabled=disabled, key="ph_locate_btn"):
                request_location_inline()
                st.rerun()

        with col_radius:
            radius = st.slider(
                "Radius (miles)", 5, 300,
                value=int(st.session_state.trip_settings.get("nearby_radius", 30)),
                step=5, key="tm_nearby_radius", label_visibility="collapsed",
                disabled=disabled,
            )
            st.session_state.trip_settings["nearby_radius"] = int(radius)

        with col_clear:
            if st.button("Clear", use_container_width=True, key="ph_clear_btn"):
                clear_location()
                st.session_state.trip_settings["casino"] = ""
                st.rerun()

        # Casino select (filtered if coords present)
        names, dbg = _filtered_casino_names_by_location(int(st.session_state.trip_settings.get("nearby_radius", 30)))
        if not names:
            names = ["(select casino)"]

        current = st.session_state.trip_settings.get("casino", "")
        if current not in names and names:
            current = names[0]
        try:
            idx = names.index(current)
        except Exception:
            idx = 0
        choice = st.selectbox("Casino", options=names, index=idx, disabled=disabled)
        st.session_state.trip_settings["casino"] = "" if choice == "(select casino)" else choice

        # Badge with a tiny debug tail (so we can see if it's filtering)
        have_coords = ("client_lat" in st.session_state) and ("client_lon" in st.session_state)
        if have_coords:
            count = len([n for n in names if n != "Other..."])
            st.caption(
                f"📍 near‑me: ON • radius: {int(st.session_state.trip_settings.get('nearby_radius',30))} mi • results: {count} "
                f"• rows:{dbg.get('rows')} coords:{dbg.get('with_coords')} in:{dbg.get('in_range')}"
            )
        else:
            st.caption("📍 near‑me: OFF")

        # Bankroll + Sessions row
        c5, c6 = st.columns([0.6, 0.4])
        with c5:
            start_bankroll = st.number_input(
                "Total Bankroll ($)", min_value=0.0, step=10.0,
                value=float(st.session_state.trip_settings.get("starting_bankroll", 200.0)),
                disabled=disabled
            )
        with c6:
            num_sessions = st.number_input(
                "Sessions", min_value=1, step=1,
                value=int(st.session_state.trip_settings.get("num_sessions", 3)),
                disabled=disabled
            )
        st.session_state.trip_settings["starting_bankroll"] = float(start_bankroll)
        st.session_state.trip_settings["num_sessions"] = int(num_sessions)
        st.caption(f"Per‑session: ${get_session_bankroll():,.2f}")

        # Start / Stop row
        c7, c8 = st.columns(2)
        with c7:
            if st.button("Start New Trip", disabled=st.session_state.trip_started, use_container_width=True):
                st.session_state.trip_started = True
                st.session_state.current_trip_id = int(st.session_state.current_trip_id or 0) + 1
                st.session_state.trip_bankrolls[st.session_state.current_trip_id] = float(start_bankroll)
                st.success("Trip started.")
                st.rerun()
        with c8:
            if st.button("Stop Trip", disabled=not st.session_state.trip_started, use_container_width=True):
                st.session_state.trip_started = False
                _reset_trip_defaults()
                st.info("Trip stopped and settings reset.")
                st.rerun()


# ---------- Public API ----------
def get_session_bankroll() -> float:
    ts = st.session_state.trip_settings
    total = float(ts.get("starting_bankroll", 0.0) or 0.0)
    n = int(ts.get("num_sessions", 1) or 1)
    return total / max(1, n)

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
    std_clamped = min(200.0, std)
    return 1.1 - (std_clamped / 200.0) * 0.2

def get_blacklisted_games() -> List[str]:
    return sorted(list(st.session_state.blacklisted_games))

def blacklist_game(game_name: str) -> None:
    st.session_state.blacklisted_games.add(game_name)

def get_current_trip_sessions() -> List[Dict[str, Any]]:
    tid = st.session_state.get("current_trip_id", 0)
    sessions = st.session_state.get("session_log", [])
    return [s for s in sessions if s.get("trip_id") == tid]

def record_session_performance(profit: float) -> None:
    arr = st.session_state.get("recent_profits", [])
    arr.append(float(profit))
    st.session_state.recent_profits = arr[-10:]