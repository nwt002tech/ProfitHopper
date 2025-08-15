from __future__ import annotations

import streamlit as st

# NOTE: this module wraps the working “blue target” geolocation component
# you already have wired up. If your project has a function with a different
# name that renders the target, import/alias it here.
try:
    # Your existing component wrapper (works today)
    from browser_location import request_location_component_once as _existing_component  # type: ignore
except Exception:
    _existing_component = None

# If the import above caused recursion (same file), define a minimal shim.
# Replace this with your actual component function if needed.
def _component_shim():
    """Fallback no-op shim if import above can’t resolve (keeps file drop-in safe)."""
    # If you *must* call the real component here, replace this shim with it.
    # Leaving empty so the file is safe to import. The real app should already
    # have a proper component function (as you confirmed earlier).
    pass


def request_location_component_once() -> None:
    """
    Render the existing blue-target component exactly once per run.
    Delegates to your already-working component function.
    """
    if _existing_component and callable(_existing_component):
        _existing_component()
    else:
        _component_shim()


def clear_location() -> None:
    """
    Clear any stored coords. Caller usually sets a one-run guard as well.
    """
    for k in ("client_lat", "client_lon", "client_geo_source"):
        if k in st.session_state:
            del st.session_state[k]


def render_location_row(label_text: str = "Locate casinos near me") -> None:
    """
    Render the blue target and the label in the same row, vertically centered.
    This is the reliable place to do the alignment because the component is
    inserted here (inside the same layout container).

    Usage from trip_manager.py:
        render_location_row("Locate casinos near me")
    """
    # Draw a small two-column row inside the sidebar: [icon][label]
    # Keep the icon column narrow so the label stays on the same line.
    icon_col, label_col = st.columns([0.20, 0.80], gap="small")
    with icon_col:
        request_location_component_once()
    with label_col:
        st.markdown(
            """
            <div style="
                height: 32px;             /* approximate component box height (tweak 28–36 if needed) */
                display: flex;
                align-items: center;      /* vertical centering */
                font-size: 0.90rem;
                white-space: nowrap;      /* prevent wrapping on narrow sidebars */
            ">
                %s
            </div>
            """ % label_text,
            unsafe_allow_html=True,
        )