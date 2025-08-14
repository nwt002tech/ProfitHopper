from __future__ import annotations
from typing import Optional, Tuple, Any

import streamlit as st

# Optional JS helpers (both are in your requirements)
try:
    from streamlit_js_eval import streamlit_js_eval
except Exception:
    streamlit_js_eval = None

try:
    from streamlit_javascript import st_javascript
except Exception:
    st_javascript = None


def _to_float_or_none(v: Any) -> Optional[float]:
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


def _get_coords_with_st_javascript() -> Tuple[Optional[float], Optional[float]]:
    """Try geolocation via streamlit_javascript (Promise)."""
    if st_javascript is None:
        return None, None
    js = """
    const getPos = () => new Promise((resolve) => {
      if (!navigator.geolocation) { resolve(null); return; }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve([pos.coords.latitude, pos.coords.longitude]),
        () => resolve(null),
        {enableHighAccuracy:true, timeout:10000, maximumAge:0}
      );
    });
    await getPos();
    """
    try:
        res = st_javascript(js)
        if isinstance(res, (list, tuple)) and len(res) == 2:
            return _to_float_or_none(res[0]), _to_float_or_none(res[1])
    except Exception:
        pass
    return None, None


def _get_coords_with_js_eval() -> Tuple[Optional[float], Optional[float]]:
    """Fallback: geolocation via streamlit_js_eval."""
    if streamlit_js_eval is None:
        return None, None
    expr = (
        "await new Promise((resolve)=>{"
        " if(!navigator.geolocation){resolve(null);return;}"
        " navigator.geolocation.getCurrentPosition("
        "   (p)=>resolve([p.coords.latitude,p.coords.longitude]),"
        "   ()=>resolve(null),"
        "   {enableHighAccuracy:true,timeout:10000,maximumAge:0}"
        " );"
        "});"
    )
    try:
        res = streamlit_js_eval(js_expressions=expr, key="ph_js_geo_get")
        if isinstance(res, (list, tuple)) and len(res) == 2:
            return _to_float_or_none(res[0]), _to_float_or_none(res[1])
    except Exception:
        pass
    return None, None


def request_location_inline() -> Tuple[Optional[float], Optional[float], str]:
    """
    No UI. Just tries to fetch browser coords via JS and stores them:
      session_state['client_lat'], ['client_lon'], ['client_geo_source'] = 'js'
    Returns (lat, lon, 'js') if found, else (None, None, 'none').
    """
    # Try st_javascript first (usually more reliable on Streamlit Cloud)
    lat, lon = _get_coords_with_st_javascript()
    if lat is None or lon is None:
        lat, lon = _get_coords_with_js_eval()

    if lat is not None and lon is not None:
        st.session_state["client_lat"] = float(lat)
        st.session_state["client_lon"] = float(lon)
        st.session_state["client_geo_source"] = "js"
        return float(lat), float(lon), "js"

    return None, None, "none"


def clear_location() -> None:
    """Remove any saved browser coordinates from the session."""
    for k in ("client_lat", "client_lon", "client_geo_source"):
        if k in st.session_state:
            del st.session_state[k]