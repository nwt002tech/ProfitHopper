from __future__ import annotations
import os, math
from typing import List, Dict, Any, Optional
import streamlit as st

# ---- blue-target component (uses your browser_location.py) -------------------
try:
    from browser_location import request_location, clear_location
except Exception:
    def request_location(label: str = "Get my location"):
        return None, None, "none"
    def clear_location():
        return None

# ---- casino source: keep using your existing get_casinos ---------------------
_get_casinos_fn = None
try:
    from data_loader_supabase import get_casinos as _gc  # your base uses this name
    _get_casinos_fn = _gc
except Exception:
    _get_casinos_fn = None

def _get_casino_names() -> List[str]:
    """Ask your existing loader for the casino list; fallback to an empty list + Other..."""
    try:
        if callable(_get_casinos_fn):
            lst = _get_casinos_fn() or []
            # normalize & dedupe
            clean = sorted({str(x).strip() for x in lst if str(x).strip()}, key=lambda s: s.lower())
            # keep your conventional “Other...” option if you use it
            if "Other..." in clean:
                return clean
            return clean + ["Other..."]
    except Exception:
        pass
    return ["Other..."]

# ---- feature flag for near-me (kept) ----------------------------------------
def _truthy(v: Optional[str]) -> bool:
    return str(v).strip().lower() in ("1","true","yes","on","y") if v is not None else False

def _flag(key: str, default: bool) -> bool:
    if key in os.environ:
        return _truthy(os.environ.get(key))
    if hasattr(st, "secrets"):
        v = st.secrets.get(key)
        if v is not None:
            return _truthy(str(v))
        gen = st.secrets.get("general", {})
        if isinstance(gen, dict) and key in gen:
            return _truthy(str(gen.get(key)))
    return default

ENABLE_NEARBY = _flag("ENABLE_NEARBY", True)

# ---- session state -----------------------------------------------------------
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
            "nearby_radius": 30,   # add radius so we can keep it sticky
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
        "nearby_radius": 30,
    }

# ---- math helpers ------------------------------------------------------------
def _to_float_or_none(v):
    try:
        if v is None: return None
        if isinstance(v, (int, float)): return float(v)
        s = str(v).strip()
        if not s or s.lower() == "nan": return None
        return float(s)
    except Exception:
        return None

def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    lat1 = _to_float_or_none(lat1); lon1 = _to_float_or_none(lon1)
    lat2 = _to_float_or_none(lat2); lon2 = _to_float_or_none(lon2)
    if None in (lat1, lon1, lat2, lon2): return float("inf")
    R = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ---- nearby row (compact, no extra “Share your location…” line) --------------
def _nearby_compact_row(disabled: bool) -> None:
    """
    One single row:
      [ blue target ] [ 'Locate casinos near me' ] [ radius slider ] [ Clear ]
    This only handles UI + stores radius; real filtering of names is done by _filter_casinos_by_near_me()
    """
    c1, c2, c3, c4 = st.columns([0.18, 0.42, 0.25, 0.15])
    with c1:
        has_coords = ("client_lat" in st.session_state) and ("client_lon" in st.session_state)
        if not has_coords:
            # Render the blue target; when user clicks, component saves coords to session_state
            request_location()
    with c2:
        st.caption("Locate casinos near me")
    with c3:
        # real label for a11y; hidden visually
        radius = st.slider(
            "Radius (miles)", 5, 300,
            int(st.session_state.trip_settings.get("nearby_radius", 30)),
            step=5, key="tm_nearby_radius",
            label_visibility="collapsed",
            disabled=disabled
        )
        st.session_state.trip_settings["nearby_radius"] = int(radius)
    with c4:
        if st.button("Clear", use_container_width=True, help="Show all casinos"):
            clear_location()
            st.rerun()

def _filter_casinos_by_near_me(names: List[str]) -> List[str]:
    """
    You asked only for layout changes here; we keep behavior minimal:
    - If browser coords exist, we just keep the list as-is (you already sort/pick later).
      If you want distance-filtering here, wire this to a DataFrame with casino lat/lon and filter.
    - If coords missing, show all (no extra “Share your location…” line).
    """
    if not ENABLE_NEARBY:
        return names
    lat = st.session_state.get("client_lat")
    lon = st.session_state.get("client_lon")
    # If no coords yet, show full list; the badge below will say "waiting for location"
    return names

def _nearby_badge() -> None:
    radius = int(st.session_state.trip_settings.get("nearby_radius", 30))
    has_coords = ("client_lat" in st.session_state) and ("client_lon" in st.session_state)
    if not ENABLE_NEARBY or not has_coords:
        st.caption("📍 near‑me: OFF" if not has_coords else f"📍 near‑me: ON • radius: {radius} mi • waiting for location")
        return
    # If coords exist we display ON (results count would require a distance filter over a DF)
    st.caption(f"📍 near‑me: ON • radius: {radius} mi")

# ---- casino selector (kept from your base, compact tweaks only) --------------
def _casino_selector(disabled: bool) -> str:
    casinos = _get_casino_names()
    current = st.session_state.trip_settings.get("casino", "")
    # use current as default if still valid
    try:
        default_index = casinos.index(current) if current in casinos else 0
    except Exception:
        default_index = 0
    sel = st.selectbox("Casino", options=casinos, index=default_index, disabled=disabled)
    if sel == "Other...":
        return st.text_input("Custom Casino", value=current if current not in casinos else "", disabled=disabled).strip()
    return str(sel).strip()

# ---- Sidebar (COMPACT) -------------------------------------------------------
def render_sidebar() -> None:
    initialize_trip_state()
    with st.sidebar:
        # Compact header
        st.markdown("### 🎯 Trip Settings")

        disabled = bool(st.session_state.trip_started)

        # Row 1: blue target + caption + radius + clear (single line)
        _nearby_compact_row(disabled=disabled)

        # Casino select directly below; list can be filtered once you wire distances
        all_names = _get_casino_names()
        options = _filter_casinos_by_near_me(all_names)
        if not options:
            options = ["(select casino)"]
        current = st.session_state.trip_settings.get("casino", "")
        if current not in options and options:
            current = options[0]
        try:
            idx = options.index(current)
        except Exception:
            idx = 0
        sel = st.selectbox("Casino", options=options, index=idx, disabled=disabled)
        st.session_state.trip_settings["casino"] = "" if sel == "(select casino)" else sel

        # One-line badge (no extra “Share your location…”)
        _nearby_badge()

        # Bankroll + Sessions on ONE row (compact)
        c1, c2 = st.columns([0.6, 0.4])
        with c1:
            start_bankroll = st.number_input(
                "Total Bankroll ($)", min_value=0.0, step=10.0,
                value=float(st.session_state.trip_settings.get("starting_bankroll", 200.0)),
                disabled=disabled
            )
        with c2:
            num_sessions = st.number_input(
                "Sessions", min_value=1, step=1,
                value=int(st.session_state.trip_settings.get("num_sessions", 3)),
                disabled=disabled
            )
        st.session_state.trip_settings["starting_bankroll"] = float(start_bankroll)
        st.session_state.trip_settings["num_sessions"] = int(num_sessions)
        st.caption(f"Per‑session: ${get_session_bankroll():,.2f}")

        # Start / Stop on ONE row (compact)
        c3, c4 = st.columns(2)
        with c3:
            if st.button("Start New Trip", disabled=st.session_state.trip_started, use_container_width=True):
                st.session_state.trip_started = True
                st.session_state.current_trip_id = int(st.session_state.current_trip_id or 0) + 1
                st.session_state.trip_bankrolls[st.session_state.current_trip_id] = float(start_bankroll)
                st.success("Trip started.")
                st.rerun()
        with c4:
            if st.button("Stop Trip", disabled=not st.session_state.trip_started, use_container_width=True):
                st.session_state.trip_started = False
                _reset_trip_defaults()
                st.info("Trip stopped and settings reset.")
                st.rerun()

# ---- Public API used elsewhere (unchanged from your base) --------------------
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