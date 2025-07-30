import streamlit as st
import pandas as pd
from datetime import datetime
from data_loader import load_game_data
from session_manager import render_session_tracker
from analytics import render_analytics
from templates import get_css, game_card
from utils import map_advantage, map_volatility, map_bonus_freq

# Configure page
st.set_page_config(layout="wide", initial_sidebar_state="collapsed", 
                  page_title="Profit Hopper Casino Manager")

# Initialize session state
if 'session_log' not in st.session_state:
    st.session_state.session_log = []
if 'bankroll' not in st.session_state:
    st.session_state.bankroll = 1000.0
if 'session_count' not in st.session_state:
    st.session_state.session_count = 10

# Apply CSS
st.markdown(get_css(), unsafe_allow_html=True)

# Input panel
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        total_bankroll = st.number_input("💰 Total Bankroll", min_value=0.0, 
                                       value=st.session_state.bankroll,
                                       step=100.0, format="%.2f")
        st.session_state.bankroll = total_bankroll
    with col2:
        num_sessions = st.number_input("📅 Number of Sessions", min_value=1, 
                                     value=st.session_state.session_count, step=1)
        st.session_state.session_count = num_sessions

# Calculations
session_bankroll = total_bankroll / num_sessions
max_bet = session_bankroll * 0.25
stop_loss = session_bankroll * 0.6

# Sticky header
st.markdown(f"""
<div class="ph-sticky-header">
    <div style="display:flex; justify-content:space-around; text-align:center">
        <div><strong>💰 Total Bankroll</strong><br>${total_bankroll:,.2f}</div>
        <div><strong>📅 Session Bankroll</strong><br>${session_bankroll:,.2f}</div>
        <div><strong>💸 Max Bet</strong><br>${max_bet:,.2f}</div>
        <div><strong>🚫 Stop Loss</strong><br><span class="ph-stop-loss">${stop_loss:,.2f}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main tabs
tab1, tab2, tab3 = st.tabs(["🎮 Game Plan", "📊 Session Tracker", "📈 Bankroll Analytics"])

# Game Plan Tab
with tab1:
    game_df = load_game_data()
    
    if not game_df.empty:
        st.subheader("Game Filters")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_rtp = st.slider("Minimum RTP (%)", 85.0, 99.9, 92.0, step=0.1)
            game_type = st.selectbox("Game Type", ["All"] + list(game_df['type'].unique()))
            
        with col2:
            max_min_bet = st.slider("Max Min Bet", 
                                   float(game_df['min_bet'].min()), 
                                   float(game_df['min_bet'].max() * 2), 
                                   float(max_bet), 
                                   step=1.0)
            advantage_filter = st.selectbox("Advantage Play Potential", 
                                          ["All", "High (4-5)", "Medium (3)", "Low (1-2)"])
            
        with col3:
            volatility_filter = st.selectbox("Volatility", 
                                           ["All", "Low (1-2)", "Medium (3)", "High (4-5)"])
            search_query = st.text_input("Search Game Name")
        
        # Apply filters
        filtered_games = game_df[
            (game_df['min_bet'] <= max_min_bet) &
            (game_df['rtp'] >= min_rtp)
        ]
        
        if game_type != "All":
            filtered_games = filtered_games[filtered_games['type'] == game_type]
            
        if advantage_filter == "High (4-5)":
            filtered_games = filtered_games[filtered_games['advantage_play_potential'] >= 4]
        elif advantage_filter == "Medium (3)":
            filtered_games = filtered_games[filtered_games['advantage_play_potential'] == 3]
        elif advantage_filter == "Low (1-2)":
            filtered_games = filtered_games[filtered_games['advantage_play_potential'] <= 2]
            
        if volatility_filter == "Low (1-2)":
            filtered_games = filtered_games[filtered_games['volatility'] <= 2]
        elif volatility_filter == "Medium (3)":
            filtered_games = filtered_games[filtered_games['volatility'] == 3]
        elif volatility_filter == "High (4-5)":
            filtered_games = filtered_games[filtered_games['volatility'] >= 4]
            
        if search_query:
            filtered_games = filtered_games[
                filtered_games['game_name'].str.contains(search_query, case=False)
            ]
        
        if not filtered_games.empty:
            filtered_games['Score'] = (
                (filtered_games['rtp'] * 0.5) +
                (filtered_games['bonus_frequency'] * 0.2) +
                (filtered_games['advantage_play_potential'] * 0.2) +
                ((6 - filtered_games['volatility']) * 0.1)
            )
            
            filtered_games = filtered_games.sort_values('Score', ascending=False)
            
            st.subheader(f"Recommended Games ({len(filtered_games)} matches)")
            st.caption(f"Showing games with RTP ≥ {min_rtp}% and min bet ≤ ${max_min_bet:,.2f}")
            
            st.markdown('<div class="ph-game-grid">', unsafe_allow_html=True)
            
            for _, row in filtered_games.head(50).iterrows():
                st.markdown(game_card(row), unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No games match your current filters. Try adjusting your criteria.")
    else:
        st.error("Failed to load game data. Please check the CSV format and column names.")

# Session Tracker Tab
with tab2:
    render_session_tracker(game_df)

# Bankroll Analytics Tab
with tab3:
    render_analytics()

# Handle session deletion
if st.session_state.get('session_log'):
    from session_manager import delete_session
    if st.experimental_get_query_params().get('action'):
        action = st.experimental_get_query_params().get('action')[0]
        index = int(st.experimental_get_query_params().get('index')[0])
        delete_session(index)
        st.experimental_set_query_params()

if __name__ == "__main__":
    pass