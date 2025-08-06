import streamlit as st
import numpy as np
from ui_templates import get_css, get_header
from trip_manager import initialize_trip_state, render_sidebar, get_session_bankroll, get_current_bankroll, blacklist_game, get_blacklisted_games, get_volatility_adjustment, get_win_streak_factor
from data_loader import load_game_data
from analytics import render_analytics
from session_manager import render_session_tracker
from utils import map_volatility, map_advantage, map_bonus_freq, get_game_image_url

st.set_page_config(layout="wide", initial_sidebar_state="expanded", 
                  page_title="Profit Hopper Casino Manager")

# Initialize state before any other operations
initialize_trip_state()

st.markdown(get_css(), unsafe_allow_html=True)
st.markdown(get_header(), unsafe_allow_html=True)

# Now render sidebar
render_sidebar()

try:
    current_bankroll = get_current_bankroll()
    session_bankroll = get_session_bankroll()
    volatility_adjustment = get_volatility_adjustment()
    win_streak_factor = get_win_streak_factor()

    # Enhanced bankroll-sensitive calculations
    if session_bankroll < 20:
        strategy_type = "Conservative"
        max_bet = max(0.01, session_bankroll * 0.10)
        stop_loss = session_bankroll * 0.40
        bet_unit = max(0.01, session_bankroll * 0.02)
    elif session_bankroll < 100:
        strategy_type = "Moderate"
        max_bet = session_bankroll * 0.15
        stop_loss = session_bankroll * 0.50
        bet_unit = max(0.05, session_bankroll * 0.03)
    elif session_bankroll < 500:
        strategy_type = "Standard"
        max_bet = session_bankroll * 0.25
        stop_loss = session_bankroll * 0.60
        bet_unit = max(0.10, session_bankroll * 0.05)
    else:
        strategy_type = "Aggressive"
        max_bet = session_bankroll * 0.30
        stop_loss = session_bankroll * 0.70
        bet_unit = max(0.25, session_bankroll * 0.06)

    # Apply dynamic adjustments
    max_bet *= win_streak_factor * volatility_adjustment
    stop_loss *= (2 - win_streak_factor)
    bet_unit *= win_streak_factor * volatility_adjustment

    # Calculate session duration estimate
    estimated_spins = int(session_bankroll / bet_unit) if bet_unit > 0 else 0

except Exception as e:
    st.error(f"Error calculating strategy: {str(e)}")
    # Fallback values
    strategy_type = "Standard"
    max_bet = 25.0
    stop_loss = 100.0
    bet_unit = 5.0
    estimated_spins = 50

# Strategy border colors
border_colors = {
    "Conservative": "#28a745",
    "Moderate": "#17a2b8",
    "Standard": "#ffc107",
    "Aggressive": "#dc3545"
}

# --- SESSION SUMMARY SECTION ---
st.markdown(f"""
<style>
.summary-container {{
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 15px;
}}
.strategy-card {{
    width: 100%;
    background: white;
    border-radius: 8px;
    padding: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border-left: 4px solid {border_colors.get(strategy_type, "#ffc107")};
}}
.metrics-row {{
    display: flex;
    gap: 8px;
    width: 100%;
}}
.metric-card {{
    flex: 1;
    background: white;
    border-radius: 8px;
    padding: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border: 1px solid #e0e0e0;
    min-width: 0;
}}
</style>

<div class="summary-container">
    <!-- STRATEGY CARD -->
    <div class="strategy-card">
        <div style="display:flex; align-items:center; justify-content:center;">
            <div style="font-size:1.5rem; margin-right:15px;">📊</div>
            <div style="text-align:center;">
                <div style="font-size:1.1rem; font-weight:bold;">{strategy_type} Strategy</div>
                <div style="font-size:0.8rem; color:#7f8c8d;">
                    Max Bet: ${max_bet:,.2f} | Stop Loss: ${stop_loss:,.2f} | Spins: {estimated_spins}
                </div>
            </div>
        </div>
    </div>

    <!-- METRICS ROW -->
    <div class="metrics-row">
        <div class="metric-card">
            <div style="display:flex; align-items:center;">
                <div style="font-size:1.2rem; margin-right:8px;">💰</div>
                <div>
                    <div style="font-size:0.7rem; color:#7f8c8d;">Bankroll</div>
                    <div style="font-size:0.9rem; font-weight:bold;">${current_bankroll:,.2f}</div>
                </div>
            </div>
        </div>
        
        <div class="metric-card">
            <div style="display:flex; align-items:center;">
                <div style="font-size:1.2rem; margin-right:8px;">💵</div>
                <div>
                    <div style="font-size:0.7rem; color:#7f8c8d;">Session</div>
                    <div style="font-size:0.9rem; font-weight:bold;">${session_bankroll:,.2f}</div>
                </div>
            </div>
        </div>
        
        <div class="metric-card">
            <div style="display:flex; align-items:center;">
                <div style="font-size:1.2rem; margin-right:8px;">🪙</div>
                <div>
                    <div style="font-size:0.7rem; color:#7f8c8d;">Unit</div>
                    <div style="font-size:0.9rem; font-weight:bold;">${bet_unit:,.2f}</div>
                </div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Active adjustment indicators
if win_streak_factor > 1 or volatility_adjustment > 1 or win_streak_factor < 1 or volatility_adjustment < 1:
    indicators = []
    if win_streak_factor > 1:
        indicators.append(f"🔥 +{int((win_streak_factor-1)*100)}%")
    elif win_streak_factor < 1:
        indicators.append(f"❄️ -{int((1-win_streak_factor)*100)}%")
        
    if volatility_adjustment > 1:
        indicators.append(f"📈 +{int((volatility_adjustment-1)*100)}%")
    elif volatility_adjustment < 1:
        indicators.append(f"📉 -{int((1-volatility_adjustment)*100)}%")
        
    if indicators:
        st.markdown(f"""
        <div style="display:flex; gap:10px; margin:5px 0 15px; font-size:0.85rem; flex-wrap:wrap;">
            <div style="font-weight:bold;">Active Adjustments:</div>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
                {''.join([f'<div>{ind}</div>' for ind in indicators])}
            </div>
        </div>
        """, unsafe_allow_html=True)

# Main tabs
tab1, tab2, tab3 = st.tabs(["🎮 Game Plan", "📊 Session Tracker", "📈 Trip Analytics"])

with tab1:
    st.info("Find the best games for your bankroll based on RTP, volatility, and advantage play potential")
    
    game_df = load_game_data()
    
    if not game_df.empty:
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
        
        # Apply filters and scoring (rest of tab1 content remains the same)
        # ... [rest of your existing tab1 code]

with tab2:
    game_df = load_game_data()
    render_session_tracker(game_df, session_bankroll)

with tab3:
    render_analytics()