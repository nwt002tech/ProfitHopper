from __future__ import annotations
from typing import Optional, Tuple, Dict, Any
import streamlit as st

# --- Path 1: streamlit-javascript (can run JS inline) ---
_HAS_ST_JS = False
try:
    from streamlit_javascript import st_javascript  # pip: streamlit-javascript
    _HAS_ST_JS = True
except Exception:
    _HAS_ST_JS = False

# --- Path 2: streamlit-js-eval (some envs) ---
_HAS_JS_EVAL = False
try:
    from streamlit_js_eval import get_geolocation as _get_geolocation_js  # pip: streamlit-js-eval
    _HAS_JS_EVAL = True
except Exception:
    _HAS_JS_EVAL = False

# --- Path 3: streamlit-geolocation (your blue target button) ---
_HAS_GEO_COMPONENT = False
_geocomp_fn = None
try:
    # some versions export `geolocation`, others `streamlit_geolocation`
    from streamlit_geolocation import geolocation as _geo_fn
    _geocomp_fn = _geo_fn
    _HAS_GEO_COMPONENT = True
except Exception:
    try:
        from streamlit_geolocation import streamlit_geolocation as _geo_fn2
        _geocomp_fn = _geo_fn2
        _HAS_GEO_COMPONENT = True
    except Exception:
        _HAS_GEO_COMPONENT = False


def _to_float_or_none(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _normalize_return(lat, lon, source: str) -> Tuple[Optional[float], Optional[float], str]:
    if lat is not None and lon is not None:
        st.session_state["client_lat"] = float(lat)
        st.session_state["client_lon"] = float(lon)
        st.session_state["client_geo_source"] = source
        return float(lat), float(lon), source
    return None, None, source


def get_browser_location(key: str = "browser_geo") -> Tuple[Optional[float], Optional[float], str]:
    """
    Returns (lat, lon, source). Stores into st.session_state['client_lat'/'client_lon'] when found.
    Presents up to three explicit options (only if available):
      1) Get Location (JS)        -> streamlit-javascript
      2) Alt method (js-eval)     -> streamlit-js-eval (no timeout kw)
      3) Component button         -> streamlit-geolocation (blue target)
    """
    # Already captured this session?
    lat0 = st.session_state.get("client_lat")
    lon0 = st.session_state.get("client_lon")
    if isinstance(lat0, (int, float)) and isinstance(lon0, (int, float)):
        return float(lat0), float(lon0), st.session_state.get("client_geo_source", "browser")

    # ---------- Button 1: streamlit-javascript ----------
    if _HAS_ST_JS:
        btn_js = st.button("Get Location (JS)", key=f"{key}_stjs_btn")
        if btn_js:
            try:
                # Must return a JSON-serializable object
                result: Dict[str, Any] = st_javascript(
                    """
                    async function getLoc() {
                      const out = {ok:false, lat:null, lon:null, acc:null, err:null, secure: window.isSecureContext};
                      try {
                        if (!('geolocation' in navigator)) {
                          out.err = 'Geolocation API not available in this browser.';
                          return out;
                        }
                        if (!window.isSecureContext) {
                          out.err = 'Geolocation requires a secure context (https).';
                          return out;
                        }
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
            except Exception as e:
                result = {"ok": False, "err": f"st_javascript failed: {e}"}

            if isinstance(result, dict) and result.get("ok"):
                return _normalize_return(_to_float_or_none(result.get("lat")), _to_float_or_none(result.get("lon")), "st-js")
            else:
                err = (result or {}).get("err")
                if err:
                    st.caption(f"⚠️ JS path error: {err}")
    else:
        # Keep the UI quiet if not installed
        pass

    # ---------- Button 2: streamlit-js-eval (no timeout kw) ----------
    if _HAS_JS_EVAL:
        btn_eval = st.button("Alt method (js‑eval)", key=f"{key}_jseval_btn")
        if btn_eval:
            try:
                geo = _get_geolocation_js()  # <- no 'timeout' arg in your environment
            except Exception as e:
                geo = {"error": f"js-eval exception: {e}"}
            if isinstance(geo, dict) and "coords" in geo:
                c = geo["coords"] or {}
                lat = _to_float_or_none(c.get("latitude"))
                lon = _to_float_or_none(c.get("longitude"))
                if lat is not None and lon is not None:
                    return _normalize_return(lat, lon, "js-eval")
            else:
                st.caption(f"⚠️ js‑eval did not return coords: {geo!r}")
    else:
        # Keep the UI quiet if not installed
        pass

    # ---------- Button 3: streamlit-geolocation component (blue target) ----------
    if _HAS_GEO_COMPONENT and callable(_geocomp_fn):
        st.caption("Or click the component button:")
        try:
            coords = _geocomp_fn()  # some versions don't accept 'key' kwarg
        except Exception as e:
            coords = {"error": f"component exception: {e}"}
        if isinstance(coords, dict):
            lat = _to_float_or_none(coords.get("latitude"))
            lon = _to_float_or_none(coords.get("longitude"))
            if lat is not None and lon is not None:
                return _normalize_return(lat, lon, "component")
            if "error" in coords:
                st.caption(f"⚠️ component error: {coords.get('error')}")
    # else: hide if not installed

    return None, None, "none"