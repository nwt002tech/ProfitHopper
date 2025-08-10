from __future__ import annotations

import time
import streamlit as st

# Location capture (browser)
try:
    from streamlit_geolocation import geolocation
except Exception:
    geolocation = None  # gracefully handled

# Your data + utils
from data_loader_supabase import get_casinos_full, update_casino_coords
from utils import geocode_city_state, haversine_miles


# ----------------------------
# Defaults
# ----------------------------
DEFAULT_TRIP_SETTINGS = {
    "casino": "",
    "use_my_location": False,
    "nearby_radius": 30,  # miles
}

def _ensure_trip_state():
    """Initialize trip state & settings in session_state."""
    if "trip_settings" not in st.session_state or not isinstance(st.session_state.trip_settings, dict):
        st.session_state.trip_settings = dict(DEFAULT_TRIP_SETTINGS)
    for k, v in DEFAULT_TRIP_SETTINGS.items():
        st.session_state.trip_settings.setdefault(k, v)

    if "trip_active" not in st.session_state:
        st.session_state.trip_active = False

    if "trip_number" not in st.session_state:
        st.session_state.trip_number = 0  # will increment on first Start Trip

    if "trip_id" not in st.session_state:
        st.session_state.trip_id = None


# ----------------------------
# Public helpers
# ----------------------------
def get_trip_settings() -> dict:
    _ensure_trip_state()
    return st.session_state.trip_settings

def is_trip_active() -> bool:
    _ensure_trip_state()
    return bool(st.session_state.trip_active)

def start_trip():
    """Start a new trip; disable settings."""
    _ensure_trip_state()
    # increment trip number, create a simple trip_id (timestamp-based)
    st.session_state.trip_number += 1
    st.session_state.trip_id = f"trip-{int(time.time())}"
    st.session_state.trip_active = True

def stop_trip(reset_to_defaults: bool = True):
    """Stop active trip; optionally reset settings back to defaults."""
    _ensure_trip_state()
    st.session_state.trip_active = False
    st.session_state.trip_id = None
    if reset_to_defaults:
        st.session_state.trip_settings = dict(DEFAULT_TRIP_SETTINGS)

def get_trip_heading() -> str:
    """Return a heading like: 'Trip #N' and the selected casino name (for your Session Tracker tab)."""
    _ensure_trip_state()
    n = st.session_state.trip_number
    casino = st.session_state.trip_settings.get("casino", "")
    # Return plain strings so caller can style; many use st.markdown with small caption
    return f"Trip #{n or 1}", casino


# ----------------------------
# Trip Settings UI
# ----------------------------
def _render_trip_location_filter(disabled: bool) -> list[str]:
    """
    Render the 'Use my location' controls and return the filtered list of casino names.
    If location is not used or not granted, returns all active casinos.
    """
    casinos_df = get_casinos_full(active_only=True)
    all_names = casinos_df["name"].dropna().astype(str).tolist()

    if disabled:
        # When trip is active, do not filter; return the previously shown set
        return all_names

    st.caption("Filter casinos near you (requires location permission)")
    colA, colB = st.columns([1, 1])
    with colA:
        use_my_location = st.checkbox(
            "Use my location",
            value=st.session_state.trip_settings.get("use_my_location", False),
            key="use_my_location",
            disabled=disabled
        )
        st.session_state.trip_settings["use_my_location"] = use_my_location
    with colB:
        radius_miles = st.slider(
            "Radius (miles)",
            5, 100,
            st.session_state.trip_settings.get("nearby_radius", 30),
            step=5,
            key="nearby_radius",
            disabled=disabled
        )
        st.session_state.trip_settings["nearby_radius"] = int(radius_miles)

    if not use_my_location:
        return all_names

    if geolocation is None:
        st.info("Location library not installed. Add 'streamlit-geolocation' to requirements.txt or turn off 'Use my location'.")
        return all_names

    coords = geolocation("Get current location")
    if not (coords and "latitude" in coords and "longitude" in coords):
        st.info("Click the button above to grant location access, or uncheck 'Use my location'.")
        return all_names

    user_lat, user_lon = coords["latitude"], coords["longitude"]

    # Lazy enrich: geocode & save coordinates for casinos that are missing them
    missing = casinos_df[casinos_df["latitude"].isna() | casinos_df["longitude"].isna()]
    for _, row in missing.iterrows():
        cid = str(row["id"])
        city = (row.get("city") or "").strip()
        state = (row.get("state") or "").strip()
        if city or state:
            lat, lon = geocode_city_state(city, state)
            if lat is not None and lon is not None:
                update_casino_coords(cid, lat, lon)
                casinos_df.loc[casinos_df["id"] == row["id"], ["latitude", "longitude"]] = [lat, lon]

    # Compute distances
    casinos_df["distance_mi"] = casinos_df.apply(
        lambda r: haversine_miles(r.get("latitude"), r.get("longitude"), user_lat, user_lon),
        axis=1
    )
    nearby = casinos_df[casinos_df["distance_mi"] <= float(radius_miles)].sort_values("distance_mi")

    if nearby.empty:
        st.info(f"No casinos within {radius_miles} miles. Showing all.")
        return all_names

    st.success(f"Found {len(nearby)} nearby casino(s).")
    return nearby["name"].astype(str).tolist()


def render_trip_settings_section():
    """
    Render the Trip Settings UI.
    - When a trip is active: widgets are disabled.
    - When you stop a trip: settings reset to defaults.
    """
    _ensure_trip_state()

    st.subheader("Trip Settings")

    disabled = bool(st.session_state.trip_active)

    # Location filter + options list
    casino_options = _render_trip_location_filter(disabled=disabled)

    # Keep previous selection if still available
    current_sel = st.session_state.trip_settings.get("casino", "")
    if current_sel not in casino_options and casino_options:
        current_sel = casino_options[0]

    casino = st.selectbox(
        "Casino",
        options=casino_options,
        index=casino_options.index(current_sel) if current_sel in casino_options else 0,
        key="trip_casino_select",
        disabled=disabled
    )
    st.session_state.trip_settings["casino"] = casino

    st.divider()

    # Start / Stop Trip controls
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("▶️ Start Trip", disabled=is_trip_active(), use_container_width=True):
            start_trip()
            st.success(f"Trip started at {st.session_state.trip_settings.get('casino') or 'selected casino'}")
            st.rerun()

    with col2:
        if st.button("⏹ Stop Trip", disabled=not is_trip_active(), use_container_width=True):
            stop_trip(reset_to_defaults=True)
            st.info("Trip stopped. Settings reset to defaults.")
            st.rerun()


# ----------------------------
# Optional: Sidebar wrapper
# ----------------------------
def render_sidebar():
    """Call this from your app's sidebar to render Trip Settings."""
    with st.sidebar:
        render_trip_settings_section()


# ----------------------------
# Optional: Heading helper for Session Tracker tab
# ----------------------------
def render_trip_heading():
    """
    Render a heading for the Session Tracker tab:
    Shows 'Trip #N' and the casino name in smaller text beneath.
    """
    title, casino = get_trip_heading()
    st.markdown(f"### {title}")
    if casino:
        st.caption(casino)

# -------- Back-compat exports & aliases (put at the end of trip_manager.py) --------

# Some apps import slightly different function names. Provide aliases:
# If your app imports render_trip_settings, point it to the new section function.
try:
    render_trip_settings
except NameError:
    render_trip_settings = render_trip_settings_section  # alias

# If your app imports get_trip_state or similar, map to get_trip_settings
try:
    get_trip_state
except NameError:
    get_trip_state = get_trip_settings  # alias

# If your app imports trip_active instead of is_trip_active
try:
    trip_active
except NameError:
    trip_active = is_trip_active  # alias

# If your app imports trip_start / trip_stop
try:
    trip_start
except NameError:
    trip_start = start_trip  # alias

try:
    trip_stop
except NameError:
    trip_stop = stop_trip  # alias

# Some code expects render_sidebar() to exist.
try:
    render_sidebar
except NameError:
    def render_sidebar():
        import streamlit as st
        with st.sidebar:
            render_trip_settings_section()

# Some code expects render_trip_header() instead of render_trip_heading()
try:
    render_trip_header
except NameError:
    render_trip_header = render_trip_heading  # alias

# Explicit export list so "from trip_manager import (...)" works reliably
__all__ = [
    "get_trip_settings",
    "is_trip_active",
    "start_trip",
    "stop_trip",
    "get_trip_heading",
    "render_trip_heading",
    "render_trip_settings_section",
    "render_trip_settings",     # alias
    "render_sidebar",
    "get_trip_state",           # alias
    "trip_active",              # alias
    "trip_start",               # alias
    "trip_stop",                # alias
    "render_trip_header",       # alias
]