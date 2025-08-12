# browser_location.py updated
from __future__ import annotations
from typing import Optional, Tuple
import streamlit as st

_has_st_js = False
try:
    from streamlit_javascript import st_javascript  # pip: streamlit-javascript
    _has_st_js = True
except Exception:
    _has_st_js = False

_has_js_eval = False
try:
    from streamlit_js_eval import get_geolocation as _get_geolocation_js  # pip: streamlit-js-eval
    _has_js_eval = True
except Exception:
    _has_js_eval = False

_has_geo_component = False
_geocomp_fn = None
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
    """Return (lat, lon, source). Stores values in session_state when obtained."""
    lat = st.session_state.get("client_lat")
    lon = st.session_state.get("client_lon")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        return float(lat), float(lon), st.session_state.get("client_geo_source", "js")

    js_clicked = st.button("Get Location (browser)", key=f"{key}_jsbtn")
    if js_clicked and _has_st_js:
        try:
            result = st_javascript("""
                async function getLoc() {
                    if (!navigator.geolocation) { return null; }
                    return await new Promise((resolve) => {
                        navigator.geolocation.getCurrentPosition(
                            (pos) => resolve([pos.coords.latitude, pos.coords.longitude]),
                            (err) => resolve(null),
                            { enableHighAccuracy: true, maximumAge: 0, timeout: 30000 }
                        );
                    });
                }
                await getLoc();
            """)
        except Exception:
            result = None
        if isinstance(result, (list, tuple)) and len(result) == 2:
            la = _to_float_or_none(result[0]); lo = _to_float_or_none(result[1])
            if la is not None and lo is not None:
                st.session_state["client_lat"] = la
                st.session_state["client_lon"] = lo
                st.session_state["client_geo_source"] = "js"
                return la, lo, "js"

    if _has_js_eval:
        try:
            st.caption("Or use alt method (js-eval):")
            geo = _get_geolocation_js(timeout=30_000)
        except Exception:
            geo = None
        if isinstance(geo, dict) and "coords" in geo:
            c = geo["coords"] or {}
            la = _to_float_or_none(c.get("latitude"))
            lo = _to_float_or_none(c.get("longitude"))
            if la is not None and lo is not None:
                st.session_state["client_lat"] = la
                st.session_state["client_lon"] = lo
                st.session_state["client_geo_source"] = "js-eval"
                return la, lo, "js-eval"

    if _has_geo_component and callable(_geocomp_fn):
        st.caption("Or click the component button:")
        try:
            coords = _geocomp_fn(key=f"{key}_component")
        except Exception:
            coords = None
        if isinstance(coords, dict):
            la = _to_float_or_none(coords.get("latitude"))
            lo = _to_float_or_none(coords.get("longitude"))
            if la is not None and lo is not None:
                st.session_state["client_lat"] = la
                st.session_state["client_lon"] = lo
                st.session_state["client_geo_source"] = "component"
                return la, lo, "component"

    if not any([_has_st_js, _has_js_eval, _has_geo_component]):
        st.info(
            "To enable near‑me filtering, add at least one of these to requirements.txt:\n"
            "• streamlit-javascript (recommended)\n"
            "• streamlit-js-eval\n"
            "• streamlit-geolocation"
        )
    return None, None, "none"
