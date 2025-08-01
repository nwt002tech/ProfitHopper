import streamlit as st
from templates import get_css, get_header
from trip_manager import initialize_trip_state, render_sidebar, get_session_bankroll, get_current_bankroll
from data_loader import load_game_data
from analytics import render_analytics
from session_manager import render_session_tracker

# Configure page
st.set_page_config(layout="wide", initial_sidebar_state="expanded", 
                  page_title="Profit Hopper Casino Manager")

# Initialize trip state
initialize_trip_state()

# Apply CSS
st.markdown(get_css(), unsafe_allow_html=True)

# Header with logo and title
st.markdown(get_header(), unsafe_allow_html=True)

# Render sidebar FIRST to process any session additions
render_sidebar()

# Get current bankroll AFTER sidebar processing
current_bankroll = get_current_bankroll()
session_bankroll = get_session_bankroll()
max_bet = session_bankroll * 0.25
stop_loss = session_bankroll * 0.6

# Sticky header - moved calculations here
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
        # Collapsible game filters (default to collapsed)
        with st.expander("🔍 Game Filters", expanded=False):
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
                from templates import game_card
                st.markdown(game_card(row), unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No games match your current filters. Try adjusting your criteria.")
    else:
        st.error("Failed to load game data. Please check the CSV format and column names.")

# Session Tracker Tab
with tab2:
    game_df = load_game_data()
    render_session_tracker(game_df, session_bankroll)

# Trip Analytics Tab
with tab3:
    render_analytics()