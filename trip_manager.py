from __future__ import annotations

import math
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html

# ======== Data loader ========
try:
    from data_loader_supabase import get_casinos_full  # must return a DataFrame
except Exception:
    get_casinos_full = None

# Optional: haversine from utils; else fallback
try:
    from utils import haversine_miles as _haversine
except Exception:
    def _haversine(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
        from math import radians, sin, cos, asin, sqrt
        R = 3958.7613
        dlat = radians(b_lat - a_lat); dlon = radians(b_lon - a_lon)
        a = sin(dlat/2)**2 + cos(radians(a_lat))*cos(radians(b_lat))*sin(dlon/2)**2
        return 2 * R * asin(sqrt(a))

# Optional: your blue target renderer (kept for UX continuity)
try:
    from browser_location import render_geo_target  # renders icon only; not required anymore
except Exception:
    render_geo_target = None


# ========== Public API used by app.py / session_manager.py ==========
def initialize_trip_state() -> None:
    st.session_state.setdefault("trip_active", False)
    st.session_state.setdefault("current_trip_id", None)
    st.session_state.setdefault("trip_settings", {
        "near_me": False,
        "nearby_radius": 30,
        "selected_casino": None,
        "casino": None,           # keep for session_manager.py
        "selected_game": None,
    })
    # coordinate stores (support BOTH shapes, since your app has used both)
    st.session_state.setdefault("user_coords", None)   # {"lat":..,"lon":..}
    st.session_state.setdefault("client_lat", None)    # float
    st.session_state.setdefault("client_lon", None)    # float
    st.session_state.setdefault("geo_source", None)

    # track last toggle state to detect ON transitions
    st.session_state.setdefault("_ph_prev_nearme", False)

    # optional analytics knobs used elsewhere
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

        # --- top row: icon + label (same line), toggle triggers geolocation + filter ---
        _near_row_and_controls(ts)

        # --- casino selector (filtered if near_me + coords present) ---
        casino_choice = _casino_selector(ts)
        ts["selected_casino"] = casino_choice
        ts["casino"] = casino_choice  # keep session_manager happy

        # --- game selector (preserve your current behavior; placeholder A→Z if you supply list) ---
        prev_game = ts.get("selected_game")
        ts["selected_game"] = st.selectbox("Game", [prev_game] if prev_game else ["Select a game"], index=0)

        # --- Start/Stop on one line ---
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
    # 1) Render your icon (visual only). The switch will actually trigger geolocation.
    if render_geo_target:
        render_geo_target()
    else:
        st.markdown('<div class="ph-geo-fallback" title="Location component">📍</div>', unsafe_allow_html=True)

    # 2) Label on the same line (CSS keeps it beside the icon)
    st.markdown('<div class="ph-nearme-label">Locate casinos near me</div>', unsafe_allow_html=True)

    # 3) Toggle — when turned ON, immediately request browser geolocation and filter
    prev = bool(st.session_state.get("_ph_prev_nearme", False))
    ts["near_me"] = st.toggle("Use near-me filter", value=bool(ts.get("near_me", False)),
                              label_visibility="collapsed")
    st.session_state["_ph_prev_nearme"] = bool(ts["near_me"])

    # If switched ON and we don't yet have coords, request them now (user gesture just happened)
    if ts["near_me"] and not prev and (_get_coords() is None):
        _request_coords_via_switch()  # sets coords into session if permission granted

    # 4) Radius slider (compact)
    ts["nearby_radius"] = int(st.slider("Radius (mi)", 5, 300, int(ts.get("nearby_radius", 30)),
                                        step=5, label_visibility="collapsed"))

    # 5) Clear — disables filter and erases cached coords (but keeps icon visible)
    if st.button("Clear", key="ph_clear_loc", use_container_width=True):
        ts["near_me"] = False
        st.session_state["user_coords"] = None
        st.session_state["client_lat"] = None
        st.session_state["client_lon"] = None
        st.session_state["geo_source"] = None
        st.session_state["_ph_prev_nearme"] = False
        st.rerun()

    # 6) Badge
    if not ts["near_me"]:
        st.caption(f"📍 near-me: OFF • radius: {ts['nearby_radius']} mi")
    else:
        coords = _get_coords()
        if not coords:
            st.caption(f"📍 near-me: ON • radius: {ts['nearby_radius']} mi • waiting for location")
        else:
            st.caption(f"📍 near-me: ON • radius: {ts['nearby_radius']} mi • filtering…")


def _request_coords_via_switch() -> None:
    """
    Inline, invisible component that immediately requests browser geolocation
    when the switch is turned ON (this runs as part of the same user gesture).
    On success, it writes a JSON payload back via Streamlit's component bridge,
    which we read from session_state and store in user_coords.
    """
    component_key = "ph_geo_switch_bridge"
    js = f"""
    <div id="{component_key}_wrap" style="height:0;overflow:hidden;"></div>
    <script>
      (function(){{
        function send(val){{
          window.parent.postMessage({{
            is_streamlit_message: true,
            type: "streamlit:setComponentValue",
            value: JSON.stringify(val),
            key: "{component_key}"
          }}, "*");
        }}
        if (!navigator.geolocation){{
          send({{error:"Geolocation unsupported"}});
          return;
        }}
        navigator.geolocation.getCurrentPosition(
          function(pos){{
            send({{lat: pos.coords.latitude, lon: pos.coords.longitude, src: "browser"}});
          }},
          function(err){{
            send({{error: err && err.message ? err.message : "Permission denied"}});
          }},
          {{ enableHighAccuracy: true, maximumAge: 0, timeout: 10000 }}
        );
      }})();
    </script>
    """
    # Render the auto-run JS (height 0 = invisible)
    st_html(js, height=0)

    # If the payload comes back in this run, capture and store it.
    raw = st.session_state.get(component_key)
    if raw:
        try:
            import json
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            payload = None

        if isinstance(payload, dict) and "lat" in payload and "lon" in payload:
            st.session_state["user_coords"] = {"lat": float(payload["lat"]), "lon": float(payload["lon"])}
            st.session_state["geo_source"] = payload.get("src", "browser")
            # clear bridge to avoid reprocessing
            st.session_state[component_key] = None
            # Rerun so the filtered list appears immediately
            st.rerun()
        else:
            # clear on error too
            st.session_state[component_key] = None


# ===================== Casino / filtering =====================

def _get_coords() -> Optional[Dict[str, float]]:
    """
    Return coords from either storage style:
      - st.session_state['user_coords'] = {'lat':..,'lon':..}
      - st.session_state['client_lat'], st.session_state['client_lon']
    """
    uc = st.session_state.get("user_coords")
    if isinstance(uc, dict) and "lat" in uc and "lon" in uc and uc["lat"] is not None and uc["lon"] is not None:
        try:
            return {"lat": float(uc["lat"]), "lon": float(uc["lon"])}
        except Exception:
            pass

    clat = st.session_state.get("client_lat")
    clon = st.session_state.get("client_lon")
    try:
        if clat is not None and clon is not None:
            return {"lat": float(clat), "lon": float(clon)}
    except Exception:
        pass

    return None


def _casino_selector(ts: Dict[str, Any]) -> Optional[str]:
    df = _casinos_df()
    if ts.get("near_me") and _get_coords():
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


def _names_from_df(df: pd.DataFrame) -> List[str]:
    col = _name_col(df)
    if not col:
        return []
    return (
        df[col]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .sort_values(key=lambda s: s.str.lower())
        .tolist()
    )


def _name_col(df: pd.DataFrame) -> Optional[str]:
    for c in ("casino_name", "name", "casino"):
        if c in df.columns:
            return c
    return None


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


def _filtered_casino_names_by_location(radius_miles: int) -> Tuple[List[str], Dict[str, Any]]:
    df = _casinos_df()
    ncol = _name_col(df)
    if not ncol:
        return [], {"reason": "no-name-col"}

    # Active filtering (if present)
    if "is_active" in df.columns:
        if df["is_active"].dtype == bool:
            df = df[df["is_active"]]
        else:
            df = df[df["is_active"] == True]  # noqa: E712

    # Coord columns
    lat_col = None
    lon_col = None
    for a, b in (("latitude", "longitude"), ("lat", "lon")):
        if a in df.columns and b in df.columns:
            lat_col, lon_col = a, b
            break
    if not lat_col or not lon_col:
        return _names_from_df(df), {"reason": "no-coord-cols"}

    coords = _get_coords()
    if not coords:
        return _names_from_df(df), {"reason": "no-user-coords"}

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


# ===================== CSS =====================

def _inject_compact_css() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] .block-container {
          padding-top: 6px !important;
          padding-bottom: 6px !important;
        }
        .ph-geo-fallback{
          display:inline-flex; align-items:center; justify-content:center;
          width:36px; height:36px; border-radius:8px; background:#eef3ff; color:#1e88e5;
          font-size:18px; line-height:1; margin-bottom:0;
        }
        .ph-nearme-label{
          position: relative;
          display: inline-block;
          white-space: nowrap;
          font-weight: 600;
          top: -28px;       /* keep beside icon */
          left: 48px;
          margin-bottom: -18px;
        }
        @media (max-width: 420px){
          .ph-nearme-label{ top: -30px; left: 50px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )