# app.py
import streamlit as st

st.set_page_config(layout="wide")
st.title("Profit Hopper Casino Manager")
st.success("Application is loading...")

# Add loading spinner
with st.spinner("Initializing application..."):
    import time
    time.sleep(3)  # Simulate loading time

# Main app will be loaded from src
from src.app import main

if __name__ == "__main__":
    main()