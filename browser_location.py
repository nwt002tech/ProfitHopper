from __future__ import annotations
from typing import Optional, Tuple

import streamlit as st

# Prefer the component API name "geolocation", but support "streamlit_geolocation"
_geocomp = None
try:
    from streamlit_geolocation import geolocation as _geo_fn
    _geocomp = _geo_fn
except Exception:
    try:
        from streamlit_geolocation import streamlit_geolocation as _geo_fn2
        _geocomp = _geo_fn2
    except Exception:
        _geocomp = None


def _to_float_or_none(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def request_location(label: str = "Get my location") -> Tuple[Optional[float], Optional[float], str]:
    """
    Renders the blue target component button.
    When clicked by the user, returns (lat, lon, 'component') and stores them in session_state.
    If component unavailable, returns (None, None, 'none').
    """
    if _geocomp is None:
        return None, None, "none"

    # Render the component (it shows a button/target that the user clicks)
    try:
        coords = _geocomp()
    except Exception:
        coords = None

    if isinstance(coords, dict):
        lat = _to_float_or_none(coords.get("latitude"))
        lon = _to_float_or_none(coords.get("longitude"))
        if lat is not None and lon is not None:
            st.session_state["client_lat"] = float(lat)
            st.session_state["client_lon"] = float(lon)
            st.session_state["client_geo_source"] = "component"
            return float(lat), float(lon), "component"

    return None, None, "none"


def clear_location() -> None:
    """Remove any saved browser coordinates from the session."""
    for k in ("client_lat", "client_lon", "client_geo_source"):
        if k in st.session_state:
            del st.session_state[k]