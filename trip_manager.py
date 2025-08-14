# trip_manager.py  (updated to remove location share text)

import streamlit as st
from browser_location import request_location
from data_loader import load_trip_data

def render_sidebar():
    st.sidebar.header("🛠️ compact sidebar")

    # Removed the line that displayed:
    # "Share your location (one-time to enable near-me)"
    # This was originally at the very top of the sidebar.

    # (Optional) If still using location detection internally, it can stay:
    # request_location()

    trip_data = load_trip_data()

    if trip_data is not None:
        st.sidebar.subheader("Trip Data")
        st.sidebar.dataframe(trip_data)

    # Add any other sidebar elements here...