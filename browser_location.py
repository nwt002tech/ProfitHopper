from __future__ import annotations
from typing import Optional, Tuple
import streamlit as st

# Prefer streamlit-js-eval (best UX). Fallback to streamlit-geolocation.
_has_js_eval = False
try:
    from streamlit_js_eval import get_geolocation as _get_geolocation_js  # pip: streamlit-js-eval
    _has_js_eval = True
except Exception:
    _has_js_eval = False

_has_geo_component = False
_geocomp_fn = None
if not _has_js_eval:
    try:
        from streamlit_geolocation import geolocation as _geo_fn  # pip: streamlit-geolocation
        _geocomp_fn = _geo_fn
        _has_geo_component = True
    except Exception:
        try:
            from streamlit_geolocation import streamlit_geolocation as _geo_fn2
            _geocomp_fn = _geo_fn2
            _has_geo_component = True
        except Exception:
            _has_geo_component = False


def _to_float_or_none(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def get_browser_location(key: str = "browser_geo") -> Tuple[Optional[float], Optional[float], str]:
    """
    Returns (lat, lon, source). No manual fields.
    Stores values in st.session_state['client_lat'/'client_lon'] when obtained.
    source: 'js-eval' | 'component' | 'none'
    """
    # Already saved this session?
    lat = st.session_state.get("client_lat")
    lon = st.session_state.get("client_lon")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        return float(lat), float(lon), st.session_state.get("client_geo_source", "js-eval")

    # Method A: streamlit-js-eval
    if _has_js_eval:
        try:
            st.caption("Allow your browser to share your location (one‑time).")
            geo = _get_geolocation_js(timeout=30 * 1000)  # ms
        except Exception:
            geo = None
        if isinstance(geo, dict) and "coords" in geo:
            c = geo["coords"] or {}
            lat = _to_float_or_none(c.get("latitude"))
            lon = _to_float_or_none(c.get("longitude"))
            if lat is not None and lon is not None:
                st.session_state["client_lat"] = lat
                st.session_state["client_lon"] = lon
                st.session_state["client_geo_source"] = "js-eval"
                return lat, lon, "js-eval"

    # Method B: streamlit-geolocation
    if _has_geo_component and callable(_geocomp_fn):
        st.caption("Click the button below to share your location.")
        try:
            coords = _geocomp_fn(key=f"{key}_component")
        except Exception:
            coords = None
        if isinstance(coords, dict):
            lat = _to_float_or_none(coords.get("latitude"))
            lon = _to_float_or_none(coords.get("longitude"))
            if lat is not None and lon is not None:
                st.session_state["client_lat"] = lat
                st.session_state["client_lon"] = lon
                st.session_state["client_geo_source"] = "component"
                return lat, lon, "component"

    # Neither installed or user hasn’t granted
    if not _has_js_eval and not _has_geo_component:
        st.info(
            "To enable near‑me filtering, add at least one of these to requirements.txt:\n"
            "• streamlit-js-eval  (recommended)\n"
            "• streamlit-geolocation"
        )
    return None, None, "none"
