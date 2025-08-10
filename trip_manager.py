from __future__ import annotations

import os
import time
from typing import List, Tuple, Optional

import streamlit as st
import pandas as pd
import math

# Optional browser geolocation (for "Use my location")
try:
    from streamlit_geolocation import geolocation
except Exception:
    geolocation = None  # handled gracefully

# Supabase client for reads/writes
try:
    from supabase import create_client
except Exception:
    create_client = None


# =========================
# Defaults / Session Keys
# =========================
DEFAULTS = {
    "trip_started": False,
    "trip_number": 0,
    "trip_id": None,
    "trip_settings": {
        "casino": "",
        "use_my_location": False,
        "nearby_radius": 30,  # miles
    },
    # bankroll / sliders expected by app.py
    "session_bankroll": 200.0,
    "current_bankroll": 200.0,
    "volatility_adjustment": 1.0,  # 0.8 .. 1.2
    "win_streak_factor": 1.0,      # 0.8 .. 1.2
}

def _sb_client(with_service: bool = False):
    """Create a Supabase client. Use service role for writes."""
    if create_client is None:
        return None
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if with_service
        else (os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
    )
    if not (url and key):
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


# =========================
# Session state init (required by app.py)
# =========================
def initialize_trip_state():
    """Seed all session keys used across the app."""
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v if not isinstance(v, dict) else dict(v)
    # Ensure nested dict exists and contains keys
    if "trip_settings" not in st.session_state or not isinstance(st.session_state.trip_settings, dict):
        st.session_state.trip_settings = dict(DEFAULTS["trip_settings"])
    for k, v in DEFAULTS["trip_settings"].items():
        st.session_state.trip_settings.setdefault(k, v)


# =========================
# Values your app.py imports
# =========================
def get_session_bankroll() -> float:
    initialize_trip_state()
    try:
        return float(st.session_state.get("session_bankroll", DEFAULTS["session_bankroll"]))
    except Exception:
        return DEFAULTS["session_bankroll"]

def get_current_bankroll() -> float:
    initialize_trip_state()
    try:
        return float(st.session_state.get("current_bankroll", st.session_state.get("session_bankroll", DEFAULTS["session_bankroll"])))
    except Exception:
        return st.session_state.get("session_bankroll", DEFAULTS["session_bankroll"])

def get_volatility_adjustment() -> float:
    initialize_trip_state()
    try:
        return float(st.session_state.get("volatility_adjustment", 1.0))
    except Exception:
        return 1.0

def get_win_streak_factor() -> float:
    initialize_trip_state()
    try:
        return float(st.session_state.get("win_streak_factor", 1.0))
    except Exception:
        return 1.0


# =========================
# Nearby filtering helpers
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


# =========================
# Casinos loading / coords update
# =========================
def _get_casinos_df(active_only: bool = True) -> pd.DataFrame:
    c = _sb_client(with_service=False)
    if not c:
        return pd.DataFrame(columns=["id","name","city","state","latitude","longitude","is_active"])
    q = c.table("casinos").select("*")
    if active_only:
        q = q.eq("is_active", True)
    res = q.order("name").execute()
    df = pd.DataFrame(res.data or [])
    for col in ["city","state","latitude","longitude","is_active"]:
        if col not in df.columns:
            df[col] = None if col in ("latitude","longitude") else ""
    return df

def _update_coords(casino_id: str, lat: float, lon: float) -> bool:
    c = _sb_client(with_service=True)
    if not c:
        return False
    try:
        c.table("casinos").update({"latitude": lat, "longitude": lon}).eq("id", str(casino_id)).execute()
        return True
    except Exception:
        return False


# =========================
# Start/Stop Trip (compatible with your app)
# =========================
def _start_trip():
    initialize_trip_state()
    st.session_state["trip_number"] = int(st.session_state.get("trip_number", 0)) + 1
    st.session_state["trip_id"] = f"trip-{int(time.time())}"
    st.session_state["trip_started"] = True

def _stop_trip(reset_to_defaults: bool = True):
    initialize_trip_state()
    st.session_state["trip_started"] = False
    st.session_state["trip_id"] = None
    if reset_to_defaults:
        st.session_state["trip_settings"] = dict(DEFAULTS["trip_settings"])
        st.session_state["session_bankroll"] = DEFAULTS["session_bankroll"]
        st.session_state["current_bankroll"] = DEFAULTS["current_bankroll"]
        st.session_state["volatility_adjustment"] = DEFAULTS["volatility_adjustment"]
        st.session_state["win_streak_factor"] = DEFAULTS["win_streak_factor"]


# =========================
# Sidebar UI (Trip Settings + bankroll controls)
# =========================
def render_sidebar():
    """
    Renders:
      - Trip Settings (casino select, optional 'Use my location', radius)
      - Bankroll controls
      - Start New Trip / Stop Trip buttons
    Uses st.session_state['trip_started'] flag exactly like your app expects.
    """
    initialize_trip_state()

    with st.sidebar:
        st.subheader("Trip Settings")

        trip_started = bool(st.session_state.get("trip_started", False))

        # Location filter controls
        st.caption("Filter casinos near you (requires location permission)")
        colA, colB = st.columns([1, 1])
        with colA:
            use_my_location = st.checkbox(
                "Use my location",
                value=st.session_state.trip_settings.get("use_my_location", False),
                key="use_my_location",
                disabled=trip_started
            )
            st.session_state.trip_settings["use_my_location"] = use_my_location
        with colB:
            radius_miles = st.slider(
                "Radius (miles)",
                5, 100, int(st.session_state.trip_settings.get("nearby_radius", 30)),
                step=5, key="nearby_radius", disabled=trip_started
            )
            st.session_state.trip_settings["nearby_radius"] = int(radius_miles)

        # Load casinos
        casinos_df = _get_casinos_df(active_only=True)
        all_names = casinos_df["name"].dropna().astype(str).tolist()
        casino_options = all_names

        # Apply nearby filter if enabled
        if use_my_location and not trip_started:
            if geolocation is None:
                st.info("Install 'streamlit-geolocation' to enable location filter.")
            else:
                coords = geolocation("Get current location")
                if coords and "latitude" in coords and "longitude" in coords:
                    user_lat, user_lon = coords["latitude"], coords["longitude"]

                    # If coords present, compute distances
                    casinos_df["distance_mi"] = casinos_df.apply(
                        lambda r: _haversine_miles(r.get("latitude"), r.get("longitude"), user_lat, user_lon),
                        axis=1
                    )
                    nearby = casinos_df[casinos_df["distance_mi"] <= float(radius_miles)].sort_values("distance_mi")
                    if not nearby.empty:
                        st.success(f"Found {len(nearby)} nearby casino(s).")
                        casino_options = nearby["name"].astype(str).tolist()
                    else:
                        st.info(f"No casinos within {radius_miles} miles. Showing all.")
                else:
                    st.info("Click above to grant location access, or uncheck 'Use my location'.")

        # Keep previous selection if still available
        current_sel = st.session_state.trip_settings.get("casino", "")
        if current_sel not in casino_options and casino_options:
            current_sel = casino_options[0]

        casino = st.selectbox(
            "Casino",
            options=casino_options,
            index=casino_options.index(current_sel) if current_sel in casino_options else 0,
            key="trip_casino_select",
            disabled=trip_started
        )
        st.session_state.trip_settings["casino"] = casino

        st.divider()

        # Bankroll controls
        st.subheader("Bankroll")
        c1, c2 = st.columns(2)
        with c1:
            session_bankroll = st.number_input(
                "Session bankroll ($)", min_value=0.0, step=10.0,
                value=float(st.session_state.get("session_bankroll", DEFAULTS["session_bankroll"])),
                disabled=trip_started
            )
            st.session_state["session_bankroll"] = float(session_bankroll)
        with c2:
            current_bankroll = st.number_input(
                "Current bankroll ($)", min_value=0.0, step=10.0,
                value=float(st.session_state.get("current_bankroll", session_bankroll)),
                disabled=trip_started
            )
            st.session_state["current_bankroll"] = float(current_bankroll)

        c3, c4 = st.columns(2)
        with c3:
            st.session_state["win_streak_factor"] = float(st.slider(
                "Win streak factor", 0.8, 1.2,
                float(st.session_state.get("win_streak_factor", 1.0)), step=0.05,
                disabled=trip_started
            ))
        with c4:
            st.session_state["volatility_adjustment"] = float(st.slider(
                "Volatility adj.", 0.8, 1.2,
                float(st.session_state.get("volatility_adjustment", 1.0)), step=0.05,
                disabled=trip_started
            ))

        st.divider()

        # Start / Stop buttons (keep your wording)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Start New Trip", disabled=trip_started, use_container_width=True):
                _start_trip()
                st.success(f"Trip started at {st.session_state.trip_settings.get('casino') or 'selected casino'}")
                st.rerun()
        with b2:
            if st.button("Stop Trip", disabled=not trip_started, use_container_width=True):
                _stop_trip(reset_to_defaults=True)
                st.info("Trip stopped. Settings reset.")
                st.rerun()


# =========================
# Blacklist (per-casino "Not Available")
# =========================
def _get_current_casino_name() -> str:
    initialize_trip_state()
    return (st.session_state.get("trip_settings") or {}).get("casino", "") or ""

def blacklist_game(game_name: str) -> bool:
    """
    Called by Game Plan tab when clicking 'Not Available – {game}'.
    Inserts/updates public.game_availability for the current casino.
    """
    casino = _get_current_casino_name().strip()
    if not casino or not (game_name or "").strip():
        return False
    c = _sb_client(with_service=True)
    if not c:
        return False
    try:
        # resolve game id by name (case-insensitive)
        res = c.table("games").select("id,name").ilike("name", game_name).limit(1).execute()
        rows = res.data or []
        if not rows:
            res = c.table("games").select("id,name").eq("name", game_name).limit(1).execute()
            rows = res.data or []
        if not rows:
            return False
        gid = str(rows[0]["id"])

        # delete-then-insert to respect unique index (game_id, lower(casino))
        c.table("game_availability").delete().eq("game_id", gid).ilike("casino", casino).execute()
        c.table("game_availability").insert({
            "game_id": gid,
            "casino": casino,
            "is_unavailable": True
        }).execute()
        return True
    except Exception:
        return False

def get_blacklisted_games() -> List[str]:
    """
    Return list of game names blacklisted (is_unavailable) for the current casino.
    """
    casino = _get_current_casino_name().strip()
    if not casino:
        return []
    c = _sb_client(with_service=False)
    if not c:
        return []
    try:
        res = c.table("game_availability").select("game_id,is_unavailable,casino").ilike("casino", casino).execute()
        rows = [r for r in (res.data or []) if r.get("is_unavailable")]
        if not rows:
            return []
        ids = [str(r["game_id"]) for r in rows if r.get("game_id")]
        if not ids:
            return []
        res2 = c.table("games").select("id,name").in_("id", ids).execute()
        m = {str(r["id"]): r.get("name") for r in (res2.data or [])}
        names = [m.get(i) for i in ids if m.get(i)]
        return list(sorted(set([n for n in names if n])))
    except Exception:
        return []


# =========================
# Optional helpers other pages may use
# =========================
def get_trip_heading() -> tuple[str, str]:
    initialize_trip_state()
    n = int(st.session_state.get("trip_number") or 1)
    casino = (st.session_state.get("trip_settings") or {}).get("casino", "")
    return f"Trip #{n}", casino

def render_trip_heading():
    title, casino = get_trip_heading()
    st.markdown(f"### {title}")
    if casino:
        st.caption(casino)


# Explicit exports to keep star‑imports predictable
__all__ = [
    # required by your app.py
    "initialize_trip_state",
    "render_sidebar",
    "get_session_bankroll",
    "get_current_bankroll",
    "blacklist_game",
    "get_blacklisted_games",
    "get_volatility_adjustment",
    "get_win_streak_factor",
    # optional helpers
    "get_trip_heading",
    "render_trip_heading",
]