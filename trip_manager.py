# trip_manager.py  (excerpt: sidebar + helpers — FULL SECTION)

import streamlit as st
import pandas as pd
from data_loader_supabase import get_casinos_full
from browser_location import (
    inline_geobutton_with_label,
    clear_coords,
    coords_available,
    get_coords,
    SS_NEAR_ON,
)

# ---------- Nearby filtering helpers ----------

def _haversine_miles(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, asin, sqrt
    R = 3958.7613
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

def _apply_nearby(df: pd.DataFrame, radius_miles: int) -> tuple[list[str], dict]:
    dbg = {}
    if df is None or df.empty:
        return [], {"reason": "no-casinos"}

    if "is_active" in df.columns:
        # ensure only active casinos
        if df["is_active"].dtype == bool:
            df = df[df["is_active"]]
        else:
            df = df[df["is_active"] == True]

    # must have coordinates
    if not {"latitude", "longitude"} <= set(df.columns):
        return sorted(df["casino"].tolist()), {"reason": "no-coord-cols"}

    coords = get_coords()
    if not coords:
        return sorted(df["casino"].tolist()), {"reason": "no-user-coords"}

    lat, lon = coords["lat"], coords["lon"]
    df = df.dropna(subset=["latitude", "longitude"]).copy()
    if df.empty:
        return [], {"reason": "all-missing-coords"}

    df["distance_mi"] = df.apply(
        lambda r: _haversine_miles(lat, lon, float(r["latitude"]), float(r["longitude"])),
        axis=1,
    )
    within = df[df["distance_mi"] <= float(radius_miles)]
    names = sorted(within["casino"].tolist())
    dbg = {
        "user_coords": coords,
        "radius_miles": radius_miles,
        "rows_with_coords": int(df.shape[0]),
        "results": int(within.shape[0]),
    }
    return names, dbg

# ---------- Sidebar UI ----------

def render_sidebar():
    st.sidebar.markdown(
        "<h3 style='margin:0 0 8px 0; display:flex; align-items:center; gap:8px;'>"
        "🎯 Trip Settings</h3>",
        unsafe_allow_html=True,
    )

    # Compact row: [ blue target (component) | 'Locate casinos near me' | radius slider | Clear ]
    with st.sidebar.container():
        # 1) Geobutton + inline label (always on one line)
        got_new = inline_geobutton_with_label("Locate casinos near me", key="geo_inline_row")

        # 2) Radius slider — small footprint
        radius = st.sidebar.slider(
            "Radius (mi)",
            min_value=10, max_value=300, step=10, value=int(st.session_state.get("nearby_radius", 30)),
            help="Filter casinos by distance from your current location.",
        )
        st.session_state["nearby_radius"] = int(radius)

        # 3) Clear action (does not remove the button; only clears coords & turns filter off)
        if st.sidebar.button("Clear location", use_container_width=True):
            clear_coords()
            st.session_state[SS_NEAR_ON] = False
            st.rerun()

    # ---------- Build casino list using filter (if coords exist) ----------
    df = get_casinos_full(active_only=True)  # uses your existing Supabase loader
    names_all = sorted(df["casino"].tolist()) if isinstance(df, pd.DataFrame) and "casino" in df.columns else []

    use_near = st.session_state.get(SS_NEAR_ON, False) and coords_available()
    if use_near:
        filtered, dbg = _apply_nearby(df, int(st.session_state.get("nearby_radius", 30)))
        names = filtered if filtered else names_all
        badge = f"📍 near-me: ON • radius: {int(st.session_state['nearby_radius'])} mi • results: {len(filtered)}"
    else:
        names = names_all
        badge = "📍 near-me: OFF"

    st.sidebar.caption(badge)

    # ---- The rest of your existing Trip Settings controls go here ----
    # Example (keep your original controls untouched below this line):
    casino_choice = st.sidebar.selectbox("Casino", names, index=0 if names else None)

    # ... continue with your existing sidebar fields / start/stop trip buttons, etc.