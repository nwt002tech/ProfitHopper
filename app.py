import streamlit as st
import numpy as np
from templates import get_css, get_header
from trip_manager import initialize_trip_state, render_sidebar, get_session_bankroll, get_current_bankroll
from data_loader import load_game_data
from analytics import render_analytics
from session_manager import render_session_tracker
from utils import map_volatility, map_advantage, map_bonus_freq

st.set_page_config(layout="wide", initial_sidebar_state="expanded", 
                  page_title="Profit Hopper Casino Manager")

initialize_trip_state()

st.markdown(get_css(), unsafe_allow_html=True)
st.markdown(get_header(), unsafe_allow_html=True)

render_sidebar()

current_bankroll = get_current_bankroll()
session_bankroll = get_session_bankroll()

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
else:
    strategy_type = "Standard"
    max_bet = session_bankroll * 0.25
    stop_loss = session_bankroll * 0.60
    bet_unit = max(0.10, session_bankroll * 0.05)

# Calculate session duration estimate
estimated_spins = int(session_bankroll / bet_unit) if bet_unit > 0 else 0

# Display compact session summary with icons
strategy_classes = {
    "Conservative": "strategy-conservative",
    "Moderate": "strategy-moderate",
    "Standard": "strategy-standard"
}

# Create the HTML content for the summary
summary_html = f"""
<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:10px;'>
    <div style='background:#fff;border-radius:10px;padding:8px;box-shadow:0 2px 5px rgba(0,0,0,0.05);border:1px solid #e0e0e0;text-align:center;'>
        <div style='font-size:1.5rem;margin-bottom:5px;'>💰</div>
        <div style='font-size:0.7rem;color:#7f8c8d;margin-bottom:3px;'>Bankroll</div>
        <div style='font-size:0.95rem;font-weight:bold;color:#2c3e50;'>${current_bankroll:,.2f}</div>
    </div>
    <div style='background:#fff;border-radius:10px;padding:8px;box-shadow:0 2px 5px rgba(0,0,0,0.05);border:1px solid #e0e0e0;text-align:center;'>
        <div style='font-size:1.5rem;margin-bottom:5px;'>💵</div>
        <div style='font-size:0.7rem;color:#7f8c8d;margin-bottom:3px;'>Session</div>
        <div style='font-size:0.95rem;font-weight:bold;color:#2c3e50;'>${session_bankroll:,.2f}</div>
    </div>
    <div style='background:#fff;border-radius:10px;padding:8px;box-shadow:0 2px 5px rgba(0,0,0,0.05);border:1px solid #e0e0e0;text-align:center;'>
        <div style='font-size:1.5rem;margin-bottom:5px;'>🪙</div>
        <div style='font-size:0.7rem;color:#7f8c8d;margin-bottom:3px;'>Unit</div>
        <div style='font-size:0.95rem;font-weight:bold;color:#2c3e50;'>{bet_unit:,.2f}</div>
    </div>
    <div style='background:#fff;border-radius:10px;padding:8px;box-shadow:0 2px 5px rgba(0,0,0,0.05);border:1px solid #e0e0e0;text-align:center;'>
        <div style='font-size:1.5rem;margin-bottom:5px;'>⬆️</div>
        <div style='font-size:0.7rem;color:#7f8c8d;margin-bottom:3px;'>Max Bet</div>
        <div style='font-size:0.95rem;font-weight:bold;color:#2c3e50;'>{max_bet:,.2f}</div>
    </div>
    <div style='background:#fff;border-radius:10px;padding:8px;box-shadow:0 2px 5px rgba(0,0,0,0.05);border:1px solid #e0e0e0;text-align:center;'>
        <div style='font-size:1.5rem;margin-bottom:5px;'>🛑</div>
        <div style='font-size:0.7rem;color:#e74c3c;margin-bottom:3px;'>Stop Loss</div>
        <div style='font-size:0.95rem;font-weight:bold;color:#e74c3c;'>{stop_loss:,.2f}</div>
    </div>
    <div style='background:#fff;border-radius:10px;padding:8px;box-shadow:0 2px 5px rgba(0,0,0,0.05);border:1px solid #e0e0e0;text-align:center;'>
        <div style='font-size:1.5rem;margin-bottom:5px;'>🌀</div>
        <div style='font-size:0.7rem;color:#7f8c8d;margin-bottom:3px;'>Spins</div>
        <div style='font-size:0.95rem;font-weight:bold;color:#2c3e50;'>{estimated_spins}</div>
    </div>
</div>
"""


# Render the HTML summary
st.markdown(summary_html, unsafe_allow_html=True)

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
            # When assigning new columns on a filtered DataFrame, pandas can raise
            # a ``SettingWithCopyWarning`` because the filtered result may be a view
            # on the original ``game_df``. Make a shallow copy to ensure
            # modifications don't propagate unintendedly and avoid the warning.
            filtered_games = filtered_games.copy()

            # Enhanced scoring algorithm
            # Normalize factors to comparable scales
            rtp_normalized = (filtered_games['rtp'] - 85) / (99.9 - 85)
            bonus_normalized = filtered_games['bonus_frequency']  # Already 0-1
            app_normalized = filtered_games['advantage_play_potential'] / 5
            volatility_normalized = (5 - filtered_games['volatility']) / 4  # Invert scale
            
            # Bankroll-adjusted factors
            bankroll_factor = np.log10(session_bankroll) / 3  # Scale based on bankroll size
            
            # Risk-adjusted bet comfort
            bet_comfort = np.clip((max_bet - filtered_games['min_bet']) / max_bet, 0, 1)
            
            # Calculate score with dynamic weights
            filtered_games['Score'] = (
                (rtp_normalized * 0.35) + 
                (bonus_normalized * 0.20) +
                (app_normalized * 0.20) +
                (volatility_normalized * 0.15) +
                (bet_comfort * 0.10)
            ) * 10
            
            # Penalize games that don't fit bankroll strategy
            # Higher penalty for small bankrolls
            bankroll_penalty_factor = 1.5 if session_bankroll < 20 else 1.0
            
            # Min bet penalty
            min_bet_penalty = np.where(
                filtered_games['min_bet'] > max_bet * 0.5,
                0.6 * bankroll_penalty_factor,
                1.0
            )
            
            # Volatility penalty
            volatility_penalty = np.where(
                (session_bankroll < 50) & (filtered_games['volatility'] >= 4),
                0.7,
                1.0
            )
            
            # Apply penalties
            filtered_games['Score'] = filtered_games['Score'] * min_bet_penalty
            filtered_games['Score'] = filtered_games['Score'] * volatility_penalty
            
            # Sort by score descending
            filtered_games = filtered_games.sort_values('Score', ascending=False)
            
            # Get recommended games for the number of sessions
            num_sessions = st.session_state.trip_settings['num_sessions']
            recommended_games = filtered_games.head(num_sessions)
            
            # Display bankroll management strategy
            st.markdown(f"""
            <div class="trip-info-box">
                <h4>💰 Bankroll Management Strategy ({strategy_type})</h4>
                <p>Recommendations optimized for your <strong>${session_bankroll:,.2f} session bankroll</strong>:</p>
                <ul>
                    <li><strong>Strategy Type</strong>: {strategy_type}</li>
                    <li><strong>Max Bet</strong>: ${max_bet:,.2f} ({max_bet/session_bankroll:.0%} of bankroll)</li>
                    <li><strong>Stop Loss</strong>: ${stop_loss:,.2f} ({stop_loss/session_bankroll:.0%} of bankroll)</li>
                    <li><strong>Bet Unit</strong>: ${bet_unit:,.2f} (Recommended bet size)</li>
                    <li><strong>Estimated Spins</strong>: {estimated_spins} (at unit size)</li>
                </ul>
                <p>Games with min bets > ${max_bet * 0.5:,.2f} or high volatility are penalized for small bankrolls.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Consolidated game recommendations
            st.subheader(f"🎯 Recommended Play Order ({len(recommended_games)} games for {num_sessions} sessions)")
            st.info("Play games in this order for optimal results:")
            
            if not recommended_games.empty:
                # Display games in play order with session numbers
                st.markdown('<div class="ph-game-grid">', unsafe_allow_html=True)
                for i, (_, row) in enumerate(recommended_games.iterrows(), start=1):
                    # Add session number to game card
                    session_card = f"""
                    <div class="ph-game-card" style="border-left: 6px solid #1976d2; position:relative;">
                        <div style="position:absolute; top:10px; right:10px; background:#1976d2; color:white; 
                                    border-radius:50%; width:30px; height:30px; display:flex; 
                                    align-items:center; justify-content:center; font-weight:bold;">
                            {i}
                        </div>
                        <div class="ph-game-title">🎰 {row['game_name']} <span style="font-size:0.9rem; color:#27ae60;">⭐ Score: {row['Score']:.1f}/10</span></div>
                        <div class="ph-game-detail">
                            <strong>🗂️ Type:</strong> {row['type']}
                        </div>
                        <div class="ph-game-detail">
                            <strong>💸 Min Bet:</strong> ${row['min_bet']:,.2f}
                        </div>
                        <div class="ph-game-detail">
                            <strong>🧠 Advantage Play:</strong> {map_advantage(int(row['advantage_play_potential']))}
                        </div>
                        <div class="ph-game-detail">
                            <strong>🎲 Volatility:</strong> {map_volatility(int(row['volatility']))}
                        </div>
                        <div class="ph-game-detail">
                            <strong>🎁 Bonus Frequency:</strong> {map_bonus_freq(row['bonus_frequency'])}
                        </div>
                        <div class="ph-game-detail">
                            <strong>🔢 RTP:</strong> {row['rtp']:.2f}%
                        </div>
                        <div class="ph-game-detail">
                            <strong>💡 Tips:</strong> {row['tips']}
                        </div>
                    </div>
                    """
                    st.markdown(session_card, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("Not enough games match your criteria for all sessions")
            
            # Show additional matching games
            extra_games = filtered_games[~filtered_games.index.isin(recommended_games.index)]
            if not extra_games.empty:
                st.subheader(f"➕ {len(extra_games)} Additional Recommended Games")
                st.caption("These games also match your criteria but aren't in your session plan:")
                
                st.markdown('<div class="ph-game-grid">', unsafe_allow_html=True)
                for _, row in extra_games.head(20).iterrows():
                    # Create a standard game card for additional games
                    game_card = f"""
                    <div class="ph-game-card">
                        <div class="ph-game-title">🎰 {row['game_name']} <span style="font-size:0.9rem; color:#27ae60;">⭐ Score: {row['Score']:.1f}/10</span></div>
                        <div class="ph-game-detail">
                            <strong>🗂️ Type:</strong> {row['type']}
                        </div>
                        <div class="ph-game-detail">
                            <strong>💸 Min Bet:</strong> ${row['min_bet']:,.2f}
                        </div>
                        <div class="ph-game-detail">
                            <strong>🧠 Advantage Play:</strong> {map_advantage(int(row['advantage_play_potential']))}
                        </div>
                        <div class="ph-game-detail">
                            <strong>🎲 Volatility:</strong> {map_volatility(int(row['volatility']))}
                        </div>
                        <div class="ph-game-detail">
                            <strong>🎁 Bonus Frequency:</strong> {map_bonus_freq(row['bonus_frequency'])}
                        </div>
                        <div class="ph-game-detail">
                            <strong>🔢 RTP:</strong> {row['rtp']:.2f}%
                        </div>
                        <div class="ph-game-detail">
                            <strong>💡 Tips:</strong> {row['tips']}
                        </div>
                    </div>
                    """
                    st.markdown(game_card, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No games match your current filters. Try adjusting your criteria.")
    else:
        st.error("Failed to load game data. Please check the CSV format and column names.")

with tab2:
    game_df = load_game_data()
    render_session_tracker(game_df, session_bankroll)

with tab3:
    render_analytics()
