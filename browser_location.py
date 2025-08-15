from __future__ import annotations
import inspect
import streamlit as st

# Try to import the component from either public name provided by streamlit-geolocation
_geocomp = None
try:
    from streamlit_geolocation import geolocation as _geo_fn  # type: ignore
    _geocomp = _geo_fn
except Exception:
    try:
        from streamlit_geolocation import streamlit_geolocation as _geo_fn2  # type: ignore
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
        if s == "" or s.lower() in ("nan", "none", "null"):
            return None
        return float(s)
    except Exception:
        return None


def component_available() -> bool:
    """Return True if the geolocation component is importable."""
    return callable(_geocomp)


def request_location_component_once(key: str = "geo_widget_in_sidebar") -> None:
    """
    Render the geolocation component (blue target) once per run.
    If it returns coords, save into session_state:
        client_lat, client_lon, client_geo_source="component"
    Always renders (even if coords already exist) so the icon stays visible.
    """
    if not callable(_geocomp):
        return

    result = None
    # Some versions of the component don't accept 'key'; call defensively.
    try:
        sig = inspect.signature(_geocomp)
        if "key" in sig.parameters:
            result = _geocomp(key=key)  # type: ignore
        else:
            result = _geocomp()  # type: ignore
    except TypeError:
        # Fallback without key if signature check wasn't accurate for this build
        try:
            result = _geocomp()  # type: ignore
        except Exception:
            result = None
    except Exception:
        result = None

    if isinstance(result, dict):
        lat = _to_float_or_none(result.get("latitude"))
        lon = _to_float_or_none(result.get("longitude"))
        if lat is not None and lon is not None:
            st.session_state["client_lat"] = float(lat)
            st.session_state["client_lon"] = float(lon)
            st.session_state["client_geo_source"] = "component"


def clear_location() -> None:
    """Remove any saved browser coordinates from the session."""
    for k in ("client_lat", "client_lon", "client_geo_source"):
        if k in st.session_state:
            del st.session_state[k]