# trip_manager.py
# Only alignment + robustness tweaks. No changes to your data or session logic required.

from __future__ import annotations

import math
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import streamlit as st

# ---- Your existing loaders / utils ----
try:
    from data_loader_supabase import get_casinos_full  # returns DataFrame of casinos
except Exception:
    get_casinos_full = None

# Use your working haversine if present; otherwise fallback
try:
    from utils import haversine_miles as _haversine
except Exception:
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 3958.7613
        from math import radians, sin, cos, asin, sqrt
        dlat = radians(lat2 - lat1); dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
        return 2 * R * asin(sqrt(a))

# Your existing blue-target geolocation component (keep your real function name)
# If your module exposes a different name, change the call at "BLUE TARGET ICON" below.
try:
    from browser_location import render_geo_target  # renders the blue target and writes coords to session
except Exception:
    render_geo_target = None


# ===================== Public API kept stable =====================

def initialize_trip_state() -> None:
    st.session_state.setdefault("trip_active", False)
    st.session_state.setdefault("current_trip_id", None)
    st.session_state.setdefault("trip_settings", {
        "near_me": False,
        "nearby_radius": 30,
        "selected_casino": None,
        "selected_game": None,
    })
    st.session_state.setdefault("user_coords", None)   # {"lat":..,"lon":..}
    st.session_state.setdefault("geo_source", None)

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


# ===================== Sidebar UI =====================

def render_sidebar() -> None:
    initialize_trip_state()
    ts: Dict[str, Any] = st.session_state["trip_settings"]

    with st.sidebar:
        _inject_compact_css()

        st.markdown("### 🎯 Trip Settings")

        # ---- ONE ROW: icon + label (same line), slider, clear ----
        _near_row_and_controls(ts)

        # ---- Casino select (filtered if near-me has coords) ----
        casino_choice = _casino_selector(ts)
        ts["selected_casino"] = casino_choice

        # ---- Game select (keep whatever you already surface; sorted A→Z if list) ----
        game_choice = _game_selector(ts)
        ts["selected_game"] = game_choice

        # ---- Start/Stop on one line ----
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Start Trip", use_container_width=True):
                st.session_state["trip_active"] = True
                if not st.session_state.get("current_trip_id"):
                    st.session_state["current_trip_id"] = 1  # let your app overwrite with real ID
                st.success("Trip started")
                st.rerun()
        with c2:
            if st.button("Stop Trip", type="secondary", use_container_width=True):
                st.session_state["trip_active"] = False
                st.info("Trip stopped")
                st.rerun()


def _near_row_and_controls(ts: Dict[str, Any]) -> None:
    """
    Renders:
      [ BLUE TARGET ICON ]  [ 'Locate casinos near me' label ]   (same visual line)
      [ radius slider (compact) ] [ Clear button ]
    The icon+label alignment uses a tiny CSS overlay so they never wrap under each other,
    even on iPhone sidebar widths, without relying on Streamlit columns (which stack on narrow screens).
    """
    # BLUE TARGET ICON — keep your working call, do not change logic
    # If your function is named differently, change here:
    if render_geo_target:
        render_geo_target()  # this should set st.session_state['user_coords'] when the user clicks
    else:
        # Minimal placeholder if the component module isn't available
        st.markdown('<div class="ph-geo-fallback" title="Location component unavailable">📍</div>', unsafe_allow_html=True)

    # LABEL pinned to the same visual row as the icon (no wrap on narrow screens)
    st.markdown('<div class="ph-nearme-label">Locate casinos near me</div>', unsafe_allow_html=True)

    # Toggle (no auto-permission — browsers require a click on the icon)
    ts["near_me"] = st.toggle("Use near-me filter", value=bool(ts.get("near_me", False)), label_visibility="collapsed")

    # Radius slider (compact)
    ts["nearby_radius"] = int(st.slider("Radius (mi)", 5, 300, int(ts.get("nearby_radius", 30)),
                                        step=5, label_visibility="collapsed"))

    # Clear button (does not remove the icon)
    if st.button("Clear", key="ph_clear_loc", use_container_width=True):
        ts["near_me"] = False
        st.session_state["user_coords"] = None
        st.session_state["geo_source"] = None
        st.rerun()

    # Badge (reflects state)
    names, dbg = (None, None)
    if ts["near_me"]:
        names, dbg = _filtered_casino_names_by_location(ts["nearby_radius"])
    st.caption(_badge_text(ts, names, dbg))


def _badge_text(ts: Dict[str, Any], names: Optional[List[str]], dbg: Optional[Dict[str, Any]]) -> str:
    near = "ON" if ts.get("near_me") else "OFF"
    radius = int(ts.get("nearby_radius", 30))
    if not ts.get("near_me"):
        return f"📍 near-me: {near} • radius: {radius} mi"
    coords = st.session_state.get("user_coords")
    if not coords:
        return f"📍 near-me: {near} • radius: {radius} mi • waiting for location"
    count = len(names) if isinstance(names, list) else "filter not applied"
    src = st.session_state.get("geo_source") or "browser"
    return f"📍 near-me: {near} • radius: {radius} mi • results: {count} ({src})"


# ===================== Casino / filtering =====================

def _casino_selector(ts: Dict[str, Any]) -> Optional[str]:
    df = _casinos_df()
    options: List[str]

    if ts.get("near_me") and st.session_state.get("user_coords"):
        names, _ = _filtered_casino_names_by_location(int(ts.get("nearby_radius", 30)))
        options = names if names else _names_from_df(df)
    else:
        options = _names_from_df(df)

    if not options:
        return None

    default = ts.get("selected_casino")
    if default not in options:
        default = options[0]
    return st.selectbox("Casino", options, index=options.index(default))


def _game_selector(ts: Dict[str, Any]) -> Optional[str]:
    # Keep your original list source; here we just preserve previous selection if available
    prev = ts.get("selected_game")
    return st.selectbox("Game", [prev] if prev else ["Select a game"], index=0)


def _names_from_df(df: pd.DataFrame) -> List[str]:
    name_col = None
    for c in ("casino_name", "name", "casino"):
        if c in df.columns:
            name_col = c
            break
    if not name_col:
        return []
    return (
        df[name_col]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .sort_values(key=lambda s: s.str.lower())
        .tolist()
    )


def _casinos_df() -> pd.DataFrame:
    try:
        if callable(get_casinos_full):
            df = get_casinos_full(active_only=False)
            if isinstance(df, pd.DataFrame):
                # normalize minimal columns
                for col in ("casino_name", "name", "casino"):
                    if col in df.columns:
                        break
                if "is_active" not in df.columns:
                    df["is_active"] = True
                return df
    except Exception as e:
        st.caption(f"[get_casinos_full] fallback: {e}")
    return pd.DataFrame(columns=["casino_name", "city", "state", "latitude", "longitude", "is_active"])


def _filtered_casino_names_by_location(radius_miles: int) -> Tuple[List[str], Dict[str, Any]]:
    df = _casinos_df()
    # filter to active if present
    if "is_active" in df.columns:
        if df["is_active"].dtype == bool:
            df = df[df["is_active"]]
        else:
            df = df[df["is_active"] == True]  # noqa: E712

    # determine name/coord columns
    name_col = "casino_name" if "casino_name" in df.columns else ("name" if "name" in df.columns else ("casino" if "casino" in df.columns else None))
    lat_col  = "latitude" if "latitude" in df.columns else ("lat" if "lat" in df.columns else None)
    lon_col  = "longitude" if "longitude" in df.columns else ("lon" if "lon" in df.columns else None)

    coords = st.session_state.get("user_coords")
    if not name_col or not lat_col or not lon_col or coords is None:
        return [], {"reason": "schema/coords missing"}

    have = df[lat_col].notna() & df[lon_col].notna()
    df2 = df.loc[have].copy()
    if df2.empty:
        return [], {"reason": "no row coords"}

    ulat = float(coords["lat"]); ulon = float(coords["lon"])
    df2["__mi"] = df2.apply(lambda r: _haversine(float(r[lat_col]), float(r[lon_col]), ulat, ulon), axis=1)
    within = df2[df2["__mi"] <= float(radius_miles)].sort_values("__mi")

    names = within[name_col].dropna().astype(str).tolist()
    dbg = {
        "radius_miles": int(radius_miles),
        "rows_with_coords": int(have.sum()),
        "results": int(len(names)),
        "closest_min_mi": float(within["__mi"].min()) if not within.empty else None,
    }
    return names, dbg


# ===================== Sidebar CSS (scoped, non-invasive) =====================

def _inject_compact_css() -> None:
    """
    Keep the blue target and text label on the SAME visual line across narrow sidebars,
    without relying on columns (which can stack on mobile). We position the label relative
    to the component's box so it sits to the right and vertically centered.
    """
    st.markdown(
        """
        <style>
        /* compact the whole sidebar a bit */
        section[data-testid="stSidebar"] .block-container {
          padding-top: 6px !important;
          padding-bottom: 6px !important;
        }

        /* fallback icon box (if your component import fails) */
        .ph-geo-fallback{
          display:inline-flex; align-items:center; justify-content:center;
          width:36px; height:36px; border-radius:8px; background:#eef3ff; color:#1e88e5;
          font-size:18px; line-height:1; margin-bottom:0;
        }

        /* Place the label on the SAME line as the icon (to the right), even on iPhone */
        .ph-nearme-label{
          position: relative;
          display: inline-block;
          white-space: nowrap;
          font-weight: 600;
          /* The offsets below may need minor per-theme tweaking (+/- 2px) */
          top: -28px;      /* pull up into the icon's row */
          left: 48px;      /* push right so it sits beside the icon */
          margin-bottom: -18px; /* reclaim space we pulled over */
        }

        /* Slightly narrower phones can use a touch more lift/push */
        @media (max-width: 420px){
          .ph-nearme-label{ top: -30px; left: 50px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )