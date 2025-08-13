from __future__ import annotations
from typing import Optional, Tuple

import streamlit as st

# Try both names that exist in the wild
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
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if not s or s.lower() == "nan":
            return None
        return float(s)
    except Exception:
        return None

def request_location(label: str = "Get my location") -> Tuple[Optional[float], Optional[float], str]:
    """
    Renders the geolocation component (blue target button by default).
    On success, stores coords in session_state:
      - client_lat
      - client_lon
      - client_geo_source = "component"
    Returns (lat, lon, source). If no coords yet, returns (None, None, "none").
    """
    if _geocomp is None:
        return None, None, "none"

    coords = _geocomp(key="geo_widget_in_sidebar")
    if coords and isinstance(coords, dict):
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