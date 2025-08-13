from __future__ import annotations

import math
from typing import List, Dict, Any, Optional
import streamlit as st

# --- Use your existing casino loader (names only) ---
try:
    from data_loader_supabase import get_casinos as _get_casinos
except Exception:
    _get_casinos = None

# --- Component (blue target) from your project ---
try:
    from browser_location import request_location, clear_location
except Exception:
    def request_location(label: str = "Get my location"):
        return None, None, "none"
    def clear_location():
        return None

# =========================
# Session state
# =========================
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

# =========================
# Helpers
# =========================
def _load_casino_names() -> List[str]:
    names: List[str] = []
    try:
        if callable(_get_casinos):
            names = _get_casinos() or []
    except Exception:
        names = []
    # normalize + dedupe + sort
    names = sorted({str(n).strip() for n in names if str(n).strip()}, key=lambda s: s.lower())
    if "Other..." not in names:
        names.append("Other...")
    return names

# =========================
# Sidebar (COMPACT)
# =========================
def render_sidebar() -> None:
    initialize_trip_state()
    with st.sidebar:
        # marker so you can confirm this file is active
        st.caption("🛠️ compact sidebar — trip_manager.py")

        st.markdown("### 🎯 Trip Settings")

        disabled = bool(st.session_state.trip_started)

        # Row 1: [blue target] [Locate casinos near me] [radius slider] [Clear]
        c1, c2, c3, c4 = st.columns([0.18, 0.42, 0.25, 0.15])
        with c1:
            has_coords = ("client_lat" in st.session_state) and ("client_lon" in st.session_state)
            if not has_coords:
                request_location()
        with c2:
            st.caption("Locate casinos near me")
        with c3:
            radius = st.slider(
                "Radius (miles)",
                min_value=5, max_value=300, step=5,
                value=int(st.session_state.trip_settings.get("nearby_radius", 30)),
                key="tm_nearby_radius",
                label_visibility="collapsed",
                disabled=disabled,
            )
            st.session_state.trip_settings["nearby_radius"] = int(radius)
        with c4:
            if st.button("Clear", use_container_width=True):
                clear_location()
                st.rerun()

        # Casino select directly below (no distance filter in this change)
        options = _load_casino_names() or ["(select casino)"]
        current = st.session_state.trip_settings.get("casino", "")
        if current not in options and options:
            current = options[0]
        try:
            idx = options.index(current)
        except Exception:
            idx = 0
        sel = st.selectbox("Casino", options=options, index=idx, disabled=disabled)
        st.session_state.trip_settings["casino"] = "" if sel == "(select casino)" else sel

        # Near‑me badge single line (no extra “Share your location…” anywhere)
        has_coords = ("client_lat" in st.session_state) and ("client_lon" in st.session_state)
        if has_coords:
            st.caption(f"📍 near‑me: ON • radius: {int(st.session_state.trip_settings.get('nearby_radius',30))} mi")
        else:
            st.caption("📍 near‑me: OFF")

        # Bankroll + sessions on one row
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

        # Start / Stop on one row
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

# =========================
# Public API (kept compatible)
# =========================
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