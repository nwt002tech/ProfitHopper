# browser_location.py
import json
import streamlit as st
from streamlit.components.v1 import html as st_html

# Session keys used across the app
SS_COORDS = "nearby_user_coords"      # dict: {"lat": float, "lon": float, "src": "browser"}
SS_NEAR_ON = "nearby_enabled"         # bool
SS_NEAR_DBG = "nearby_debug"          # optional

def _write_coords_to_session(payload: dict | None):
    if not payload or "lat" not in payload or "lon" not in payload:
        return False
    st.session_state[SS_COORDS] = {"lat": float(payload["lat"]), "lon": float(payload["lon"]), "src": payload.get("src", "browser")}
    st.session_state[SS_NEAR_ON] = True
    return True

def clear_coords():
    st.session_state.pop(SS_COORDS, None)
    st.session_state[SS_NEAR_ON] = False

def coords_available() -> bool:
    return isinstance(st.session_state.get(SS_COORDS), dict) and "lat" in st.session_state[SS_COORDS] and "lon" in st.session_state[SS_COORDS]

def get_coords() -> dict | None:
    return st.session_state.get(SS_COORDS)

def inline_geobutton_with_label(label_text: str = "Locate casinos near me", key: str = "geo_inline_row"):
    """
    Renders a single-row, inline-flex geolocation button (blue target) with the label on the SAME line.
    When clicked, it requests browser geolocation and writes the result into session_state[SS_COORDS].
    Returns True if new coords were received during this run.
    """
    # A small, self-contained component that returns coords through Streamlit's setComponentValue bridge.
    component_id = f"{key}_bridge"
    height = 44  # stays compact and prevents wrapping
    js = f"""
    <div id="{key}_wrap" style="
      display:inline-flex; align-items:center; gap:10px;
      line-height:1; white-space:nowrap; user-select:none;">
      <button id="{key}_btn" title="Use my location" style="
        display:inline-flex; align-items:center; justify-content:center;
        width:36px; height:36px; border:none; border-radius:8px;
        background:#1e88e5; color:white; cursor:pointer;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M12 2v4M12 18v4M2 12h4M18 12h4" stroke="white" stroke-width="2" stroke-linecap="round"/>
          <circle cx="12" cy="12" r="3.5" stroke="white" stroke-width="2"/>
        </svg>
      </button>
      <span style="font-weight:600;">{label_text}</span>
    </div>
    <script>
      const btn = document.getElementById("{key}_btn");
      function sendValue(val) {{
        window.parent.postMessage({{
          is_streamlit_message: true,
          type: "streamlit:setComponentValue",
          value: JSON.stringify(val),
          key: "{component_id}"
        }}, "*");
      }}
      btn.addEventListener("click", () => {{
        if (!navigator.geolocation) {{
          sendValue({{ error: "Geolocation unsupported" }});
          return;
        }}
        navigator.geolocation.getCurrentPosition(
          (pos) => {{
            const v = {{
              lat: pos.coords.latitude,
              lon: pos.coords.longitude,
              src: "browser"
            }};
            sendValue(v);
          }},
          (err) => {{
            sendValue({{ error: err && err.message ? err.message : "Permission denied" }});
          }},
          {{ enableHighAccuracy: true, maximumAge: 0, timeout: 10000 }}
        );
      }});
    </script>
    """

    # Render the inline component
    st_html(js, height=height)

    # Read back the value if any was just sent
    # Streamlit exposes the posted value via a special query param channel; components.html
    # makes it available on rerun. We recover it from st.session_state via the dedicated key.
    # To keep things robust, we allow users to click multiple times; the last payload wins.
    payload_raw = st.session_state.get(component_id)
    got_new = False
    if payload_raw:
        try:
            payload = json.loads(payload_raw)
        except Exception:
            payload = None
        if isinstance(payload, dict) and "lat" in payload and "lon" in payload:
            got_new = _write_coords_to_session(payload)
        # clear the transient bridge value so we don't re-process on next rerun
        st.session_state[component_id] = None
    return got_new