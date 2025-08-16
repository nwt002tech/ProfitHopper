# trip_manager.py
# Full module with sidebar alignment fix (target icon + label on one line),
# resilient nearby filtering, and stable public API used by app.py/session_manager.py.

from __future__ import annotations

import math
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import streamlit as st

# --- Optional imports (don’t break if file isn’t present) --------------------
try:
    from data_loader_supabase import get_casinos_full  # returns casino DF with city/state/lat/lon/active
except Exception:
    get_casinos_full = None  # will fall back to empty

try:
    # Your browser location helper that renders the blue target and manages coords in session_state
    # Expected exported helpers (we guard each call below):
    #   - render_geo_target()
    #   - request_location()
    #   - clear_location()
    from browser_location import render_geo_target, request_location, clear_location  # type: ignore
except Exception:
    render_geo_target = None
    request_location = None
    clear_location = None


# =============================================================================
# Session keys (namespaced neatly to avoid collisions)
# =============================================================================
TRIP_KEY = "trip_settings"
NEAR_ME = "near_me_enabled"
NEAR_RADIUS = "nearby_radius"
USER_COORDS = "user_coords"          # dict: {"lat": float, "lon": float}
NEAR_FILTERED = "nearby_names_dbg"   # cache last filter debug (optional)


# =============================================================================
# Public API expected by app.py / session_manager.py
# =============================================================================
def initialize_trip_state() -> None:
    """Idempotent init of trip settings and related state."""
    st.session_state.setdefault(TRIP_KEY, {})
    trip = st.session_state[TRIP_KEY]

    trip.setdefault(NEAR_ME, False)
    trip.setdefault(NEAR_RADIUS, 30)  # miles
    trip.setdefault(USER_COORDS, None)

    # Optional extras used elsewhere in your app
    trip.setdefault("selected_casino", None)
    trip.setdefault("selected_game", None)
    trip.setdefault("bankroll", 0.0)
    trip.setdefault("blacklist", set())

    # convenience mirrors (optional)
    st.session_state.setdefault("win_streak_factor", 1.0)
    st.session_state.setdefault("volatility_adjustment", 1.0)
    st.session_state.setdefault("advantage_adjustment", 1.0)


def render_sidebar() -> None:
    """Draw the entire Trip Settings sidebar, including the aligned near-me row."""
    initialize_trip_state()
    trip: Dict[str, Any] = st.session_state[TRIP_KEY]

    with st.sidebar:
        _inject_compact_css()

        st.markdown("### 🎯 Trip Settings")

        # --- One row: [ blue target icon ] [ 'Locate casinos near me' label + toggle/clear ] ---
        _near_me_row()

        # --- Radius slider (tight, single line label) ---
        trip[NEAR_RADIUS] = st.slider(
            "Radius (miles)",
            min_value=5,
            max_value=500,
            step=5,
            value=int(trip.get(NEAR_RADIUS, 30)),
            key="radius_slider_trip",
        )

        # --- Casino list (filtered if near-me & coords available) ---
        names, dbg = _filtered_casino_names_by_location(trip[NEAR_RADIUS])
        st.session_state[NEAR_FILTERED] = dbg  # optional debug cache

        # Casino selector
        trip["selected_casino"] = st.selectbox(
            "Casino",
            options=names if names else ["(no casinos)"],
            index=0 if names else 0,
            key="casino_select_trip",
        )

        # Game selector (sorted alphabetically as requested)
        games = _load_games_sorted()
        trip["selected_game"] = st.selectbox(
            "Game",
            options=games if games else ["(no games)"],
            index=0 if games else 0,
            key="game_select_trip",
        )

        # Start/Stop on a single row
        c1, c2 = st.columns(2)
        with c1:
            st.button("▶️ Start Trip", use_container_width=True, key="start_trip_btn")
        with c2:
            st.button("⏹ Stop Trip", use_container_width=True, key="stop_trip_btn")

        # Badge showing current state
        st.caption(_nearby_badge_text(names, trip))


def get_session_bankroll() -> float:
    return float(st.session_state.get(TRIP_KEY, {}).get("bankroll", 0.0))


def get_current_bankroll() -> float:
    return get_session_bankroll()


def blacklist_game(game_name: str) -> None:
    trip = st.session_state[TRIP_KEY]
    bl: set = trip.get("blacklist", set())
    bl.add(game_name)
    trip["blacklist"] = bl


def get_blacklisted_games() -> List[str]:
    trip = st.session_state[TRIP_KEY]
    return sorted(list(trip.get("blacklist", set())))


def get_volatility_adjustment() -> float:
    return float(st.session_state.get("volatility_adjustment", 1.0))


def get_win_streak_factor() -> float:
    return float(st.session_state.get("win_streak_factor", 1.0))


def get_current_trip_sessions() -> pd.DataFrame:
    """Return your live sessions DF. Replace stub with your real implementation if needed."""
    return pd.DataFrame(columns=["casino", "game", "start", "end", "profit"])


def record_session_performance(*args, **kwargs) -> None:
    """Persist a session performance entry. Replace with your real implementation."""
    return


# =============================================================================
# Nearby logic & UI
# =============================================================================
def _near_me_row() -> None:
    """
    Render the blue target component and the 'Locate casinos near me' label on ONE row,
    center-aligned vertically, mobile friendly.
    """
    trip = st.session_state[TRIP_KEY]

    # Row with 3 columns: [target icon] [label + toggle] [clear]
    left, middle, right = st.columns([0.18, 0.62, 0.20], vertical_alignment="center")

    with left:
        # Render your blue target component exactly where it should be.
        # If your browser_location module exposes render_geo_target(), use it.
        # Otherwise show a small button fallback that calls request_location().
        if render_geo_target:
            render_geo_target()  # component handles updating trip[USER_COORDS]
        else:
            # Fallback: a small icon button that triggers browser prompt (if your helper exists)
            if st.button("📍", help="Locate me", key="locate_me_fallback"):
                if request_location:
                    request_location()  # should set trip[USER_COORDS]
                trip[NEAR_ME] = True

    with middle:
        # Keep the label inline with the icon by staying in the same column.
        # Also include a compact toggle to actually enable/disable near-me filtering.
        row = st.container()
        with row:
            st.markdown(
                '<div class="near-label">Locate casinos near me</div>',
                unsafe_allow_html=True,
            )
            # Tiny toggle just below (still visually tight)
            trip[NEAR_ME] = st.toggle(
                "Use near-me filter",
                value=bool(trip.get(NEAR_ME, False)),
                label_visibility="collapsed",
                key="toggle_near_me",
            )

    with right:
        # Clear location (doesn't remove the icon; only clears coords & turns filter off)
        if st.button("Clear", key="clear_loc_btn", use_container_width=True):
            trip[NEAR_ME] = False
            trip[USER_COORDS] = None
            if clear_location:
                clear_location()
            # do NOT hide the target icon; user may click again immediately

    # If user enabled near-me but has no coords yet, try to request once
    if trip.get(NEAR_ME) and not trip.get(USER_COORDS) and request_location:
        # Non-blocking: let the component prompt the browser
        request_location()


def _filtered_casino_names_by_location(radius_miles: int) -> Tuple[List[str], Dict[str, Any]]:
    """
    Return (names, debug) filtered by distance if near-me is enabled and coordinates exist.
    """
    trip = st.session_state[TRIP_KEY]
    df = _casinos_df_safe()

    dbg = {
        "near_me": trip.get(NEAR_ME, False),
        "radius_miles": radius_miles,
        "rows_total": int(len(df)),
        "rows_with_coords": 0,
        "used_coords": trip.get(USER_COORDS),
        "in_range": 0,
    }

    # Filter active if column exists
    if "is_active" in df.columns:
        # accept bool or 0/1
        if df["is_active"].dtype == bool:
            df = df[df["is_active"]]
        else:
            df = df[df["is_active"] == True]  # noqa: E712

    # Standardize columns
    name_col = "casino_name" if "casino_name" in df.columns else "name" if "name" in df.columns else None
    lat_col = "latitude" if "latitude" in df.columns else "lat" if "lat" in df.columns else None
    lon_col = "longitude" if "longitude" in df.columns else "lon" if "lon" in df.columns else None

    if not name_col:
        return ([], {**dbg, "reason": "no name column"})

    df = df.copy()
    # Track coord availability
    if lat_col and lon_col:
        mask_has_coords = df[lat_col].notna() & df[lon_col].notna()
        dbg["rows_with_coords"] = int(mask_has_coords.sum())
    else:
        dbg["rows_with_coords"] = 0

    # If near-me off or we don’t have coords, return all names
    if not trip.get(NEAR_ME, False) or not trip.get(USER_COORDS) or not lat_col or not lon_col:
        names = df[name_col].dropna().astype(str).sort_values(key=lambda s: s.str.lower()).tolist()
        return (names, {**dbg, "in_range": len(names), "reason": "not filtering"})

    user = trip[USER_COORDS]
    u_lat, u_lon = float(user["lat"]), float(user["lon"])

    def _dist(row) -> float:
        try:
            return _haversine_miles(float(row[lat_col]), float(row[lon_col]), u_lat, u_lon)
        except Exception:
            return math.inf

    df["__mi"] = df.apply(_dist, axis=1)
    filtered = df[df["__mi"] <= float(radius_miles)].sort_values("__mi")
    dbg["in_range"] = int(len(filtered))

    if len(filtered) == 0:
        # Return all, but indicate nothing found
        names = df[name_col].dropna().astype(str).sort_values(key=lambda s: s.str.lower()).tolist()
        return (names, {**dbg, "reason": "0 in range — showing all"})
    else:
        names = filtered[name_col].dropna().astype(str).tolist()
        return (names, {**dbg, "reason": "filtered"})


def _nearby_badge_text(names: List[str], trip: Dict[str, Any]) -> str:
    near = "ON" if trip.get(NEAR_ME) else "OFF"
    radius = int(trip.get(NEAR_RADIUS, 30))
    coords = trip.get(USER_COORDS)
    if trip.get(NEAR_ME) and not coords:
        return f"📍 near-me: {near} • radius: {radius} mi • waiting for location"
    if trip.get(NEAR_ME) and coords:
        last_dbg = st.session_state.get(NEAR_FILTERED, {})
        cnt = last_dbg.get("in_range", "?")
        return f"📍 near-me: {near} • radius: {radius} mi • results: {cnt}"
    return f"📍 near-me: {near} • radius: {radius} mi"


# =============================================================================
# Data & util helpers
# =============================================================================
def _casinos_df_safe() -> pd.DataFrame:
    """Safe wrapper around get_casinos_full(). Never throws; never returns None."""
    try:
        if callable(get_casinos_full):
            df = get_casinos_full(active_only=False)  # leave active filtering to us
            if isinstance(df, pd.DataFrame):
                return df
    except Exception:
        pass
    return pd.DataFrame(columns=["name", "city", "state", "is_active", "latitude", "longitude"])


def _load_games_sorted() -> List[str]:
    """
    Load your games from wherever you store them.
    If your app already loads games elsewhere, you can replace this with that call.
    """
    # If you already had a loader (e.g., data_loader_supabase.load_game_data()),
    # import and call it here, then sort unique game names alpha.
    try:
        from data_loader_supabase import load_game_data  # type: ignore
        gdf = load_game_data()
        if isinstance(gdf, pd.DataFrame) and "game_name" in gdf.columns:
            return (
                gdf["game_name"]
                .dropna()
                .astype(str)
                .drop_duplicates()
                .sort_values(key=lambda s: s.str.lower())
                .tolist()
            )
    except Exception:
        pass
    return []


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two lat/lon points in miles."""
    # Convert decimal degrees to radians
    from math import radians, sin, cos, asin, sqrt

    R = 3958.7613  # Radius of earth in miles
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2.0) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2.0) ** 2
    c = 2 * asin(sqrt(a))
    return R * c


def _inject_compact_css() -> None:
    """
    Tighten vertical spacing in sidebar and ensure the near-row items
    (icon + label) sit on the same line and are vertically centered.
    """
    st.markdown(
        """
        <style>
        /* compact the sidebar */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }
        /* label next to the icon should look like inline text */
        .near-label{
            display:inline-block;
            margin-left: .25rem;
            font-weight: 500;
            position: relative;
            top: 2px;  /* fine-tune baseline alignment with the icon */
            white-space: nowrap;  /* keep on one line on mobile */
        }
        /* Make columns in the near-me row align middle on all devices */
        [data-testid="stHorizontalBlock"] > div:has(div .near-label){
            display: flex;
            align-items: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )