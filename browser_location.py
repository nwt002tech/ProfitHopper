from __future__ import annotations

import json
from typing import Optional, Dict

import streamlit as st
from streamlit.components.v1 import html as _html


def _install_payload_if_present(key: str) -> Optional[Dict[str, float]]:
    """
    If our mini-component has posted a JSON payload to session_state[key],
    parse it, stash into st.session_state['user_coords'], and return coords.
    Always clears the bridge key after use.
    """
    raw = st.session_state.get(key)
    if not raw:
        return None

    payload = None
    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        payload = None

    # Clear immediately to avoid re-processing on subsequent reruns
    st.session_state[key] = None

    if isinstance(payload, dict) and "lat" in payload and "lon" in payload:
        try:
            lat = float(payload["lat"])
            lon = float(payload["lon"])
        except Exception:
            return None

        st.session_state["user_coords"] = {"lat": lat, "lon": lon}
        st.session_state["geo_source"] = payload.get("src", "browser")
        return {"lat": lat, "lon": lon}
    else:
        # If there was an error, you can optionally stash it for debugging:
        if isinstance(payload, dict) and "error" in payload:
            st.session_state["location_error"] = str(payload["error"])
        return None


def request_location(key: str = "ph_geo_switch") -> None:
    """
    Invisible, immediate geolocation request. Call this right after turning the
    'near me' switch ON. If the browser grants permission, we save coords and rerun.
    """
    bridge_key = key  # the session_state key we’ll use to receive results

    # Invisible HTML/JS that runs once to request location
    _html(
        f"""
        <div id="{bridge_key}_wrap" style="height:0;overflow:hidden;"></div>
        <script>
          (function(){{
            function send(val){{
              window.parent.postMessage(
                {{
                  is_streamlit_message: true,
                  type: "streamlit:setComponentValue",
                  value: JSON.stringify(val),
                  key: "{bridge_key}"
                }},
                "*"
              );
            }}
            try {{
              if (!navigator.geolocation) {{
                send({{error: "Geolocation unsupported"}});
                return;
              }}
              navigator.geolocation.getCurrentPosition(
                function(pos){{
                  send({{
                    lat: pos.coords.latitude,
                    lon: pos.coords.longitude,
                    src: "browser"
                  }});
                }},
                function(err){{
                  send({{error: err && err.message ? err.message : "Permission denied"}});
                }},
                {{ enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }}
              );
            }} catch(e) {{
              send({{error: "JS exception requesting geolocation"}});
            }}
          }})();
        </script>
        """,
        height=0,
    )

    # If the browser already responded this run, capture and rerun to apply filters
    coords = _install_payload_if_present(bridge_key)
    if coords:
        st.rerun()


def render_geo_target(key: str = "ph_geo_btn") -> None:
    """
    Renders the blue target control (button). Clicking it requests location and
    stores coords in session_state['user_coords'] the same as request_location().
    """
    # A small, round blue target button
    st.markdown(
        f"""
        <button id="{key}_btn" class="ph-target-btn" title="Share your location"></button>
        <style>
          .ph-target-btn {{
            width: 36px; height: 36px; border-radius: 18px;
            border: none; cursor: pointer;
            background: radial-gradient(circle at center, #3b82f6 35%, #1d4ed8 36%);
            box-shadow: 0 0 0 2px rgba(29,78,216,.15);
          }}
          .ph-target-btn:active {{ transform: scale(.98); }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Attach a one-time click handler that requests geolocation and posts result
    _html(
        f"""
        <script>
          (function(){{
            const btn = window.parent.document.getElementById("{key}_btn");
            if (!btn) return;
            if (btn._ph_bound) return;  // avoid double binding on reruns
            btn._ph_bound = true;

            function send(val){{
              window.parent.postMessage(
                {{
                  is_streamlit_message: true,
                  type: "streamlit:setComponentValue",
                  value: JSON.stringify(val),
                  key: "{key}"
                }},
                "*"
              );
            }}

            btn.addEventListener("click", function(){{
              try {{
                if (!navigator.geolocation) {{
                  send({{error: "Geolocation unsupported"}});
                  return;
                }}
                navigator.geolocation.getCurrentPosition(
                  function(pos){{
                    send({{
                      lat: pos.coords.latitude,
                      lon: pos.coords.longitude,
                      src: "browser"
                    }});
                  }},
                  function(err){{
                    send({{error: err && err.message ? err.message : "Permission denied"}});
                  }},
                  {{ enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }}
                );
              }} catch(e) {{
                send({{error: "JS exception requesting geolocation"}});
              }}
            }});
          }})();
        </script>
        """,
        height=0,
    )

    # If a click just happened and the browser responded, capture and rerun
    coords = _install_payload_if_present(key)
    if coords:
        st.rerun()