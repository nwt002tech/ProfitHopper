import streamlit as st
from templates import get_css, get_header
from trip_manager import initialize_trip_state, render_sidebar, get_session_bankroll, get_current_bankroll
from data_loader import load_game_data
from analytics import render_analytics
from session_manager import render_session_tracker

# Configure page
st.set_page_config(layout="wide", initial_sidebar_state="expanded", 
                  page_title="Profit Hopper Casino Manager")

# Initialize trip state - MUST BE FIRST
initialize_trip_state()

# Apply CSS
st.markdown(get_css(), unsafe_allow_html=True)

# Header with logo and title
st.markdown(get_header(), unsafe_allow_html=True)

# Render sidebar - processes session additions
render_sidebar()

# Calculate values AFTER session processing
current_bankroll = get_current_bankroll()
session_bankroll = get_session_bankroll()
max_bet = session_bankroll * 0.25
stop_loss = session_bankroll * 0.6

# Sticky header with current values
st.markdown(f"""
<div class="ph-sticky-header">
    <div style="display:flex; justify-content:space-around; text-align:center">
        <div><strong>💰 Current Bankroll</strong><br>${current_bankroll:,.2f}</div>
        <div><strong>📅 Session Bankroll</strong><br>${session_bankroll:,.2f}</div>
        <div><strong>💸 Max Bet</strong><br>${max_bet:,.2f}</div>
        <div><strong>🚫 Stop Loss</strong><br><span class="ph-stop-loss">${stop_loss:,.2f}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main tabs
tab1, tab2, tab3 = st.tabs(["🎮 Game Plan", "📊 Session Tracker", "📈 Trip Analytics"])

# Game Plan Tab
with tab1:
    st.info("Find the best games for your bankroll based on RTP, volatility, and advantage play potential")
    
    game_df = load_game_data()
    
    if not game_df.empty:
        # ... (rest of tab1 code remains unchanged) ...

# Session Tracker Tab
with tab2:
    game_df = load_game_data()
    render_session_tracker(game_df, session_bankroll)

# Trip Analytics Tab
with tab3:
    render_analytics()