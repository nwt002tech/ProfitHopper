from __future__ import annotations
from typing import Optional, Tuple, Dict, Any
import streamlit as st

# We only use inline JS; we do not render the blue target component.
_HAS_ST_JS = False
try:
    from streamlit_javascript import st_javascript  # pip install streamlit-javascript
    _HAS_ST_JS = True
except Exception:
    _HAS_ST_JS = False


def _to_float_or_none(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _save_and_return(lat, lon, source: str) -> Tuple[Optional[float], Optional[float], str]:
    if lat is not None and lon is not None:
        st.session_state["client_lat"] = float(lat)
        st.session_state["client_lon"] = float(lon)
        st.session_state["client_geo_source"] = source
        return float(lat), float(lon), source
    return None, None, source


def get_browser_location(key: str = "browser_geo") -> Tuple[Optional[float], Optional[float], str]:
    """
    One-shot geolocation triggered by checking 'Use my location'.
    Uses inline JS only (true one-click). No component fallback is rendered.
    Returns (lat, lon, 'st-js' or 'none').
    """
    # Already captured this session?
    lat0 = st.session_state.get("client_lat")
    lon0 = st.session_state.get("client_lon")
    if isinstance(lat0, (int, float)) and isinstance(lon0, (int, float)):
        return float(lat0), float(lon0), st.session_state.get("client_geo_source", "st-js")

    if not _HAS_ST_JS:
        return None, None, "none"

    # Try to request immediately — this runs in response to the checkbox toggle (user gesture).
    try:
        result: Dict[str, Any] = st_javascript(
            """
            async function getLoc() {
              const out = {ok:false, lat:null, lon:null, acc:null, err:null, secure: window.isSecureContext};
              try {
                if (!('geolocation' in navigator)) { out.err='Geolocation not available.'; return out; }
                if (!window.isSecureContext) { out.err='Geolocation requires HTTPS.'; return out; }
                const pos = await new Promise((resolve) => {
                  navigator.geolocation.getCurrentPosition(
                    p => resolve(p),
                    e => resolve({ error: e && (e.code + ':' + e.message) }),
                    { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
                  );
                });
                if (pos && !pos.error) {
                  out.ok = true;
                  out.lat = pos.coords.latitude;
                  out.lon = pos.coords.longitude;
                  out.acc = pos.coords.accuracy;
                  return out;
                } else {
                  out.err = pos && pos.error ? String(pos.error) : 'Unknown geolocation error.';
                  return out;
                }
              } catch (e) {
                out.err = String(e);
                return out;
              }
            }
            return await getLoc();
            """,
            key=f"{key}_stjs_exec",
        ) or {}
    except Exception:
        result = {"ok": False}

    if isinstance(result, dict) and result.get("ok"):
        return _save_and_return(_to_float_or_none(result.get("lat")), _to_float_or_none(result.get("lon")), "st-js")

    return None, None, "none"