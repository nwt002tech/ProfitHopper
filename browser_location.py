from __future__ import annotations
from typing import Optional, Tuple, Any
import streamlit as st

# Try both exported names across package versions
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


def _to_float_or_none(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if not s or s.lower() in ("nan", "none", "null"):
            return None
        return float(s)
    except Exception:
        return None


def request_location_component_once() -> Tuple[Optional[float], Optional[float], str]:
    """
    Render the geolocation *component* and capture coords *if* the user clicks it.
    No label is passed (some versions don't support extra kwargs).
    Saves:
      - st.session_state['client_lat']
      - st.session_state['client_lon']
      - st.session_state['client_geo_source'] = 'component'
    Returns (lat, lon, 'component') if obtained this run else (None, None, 'none').
    """
    if _geocomp is None:
        return None, None, "none"

    # Some builds reject kwargs (like key/label). Call bare; Streamlit will handle identity by call site.
    try:
        data = _geocomp()
    except TypeError:
        # If the current build rejects kwargs OR bare calls, just swallow and return no coords.
        return None, None, "none"
    except Exception:
        return None, None, "none"

    if isinstance(data, dict):
        lat = _to_float_or_none(data.get("latitude"))
        lon = _to_float_or_none(data.get("longitude"))
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