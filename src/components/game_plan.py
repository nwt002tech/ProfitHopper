import streamlit as st
import pandas as pd
from src.utils.data_loader import load_game_data
from src.utils.helpers import map_advantage, map_volatility, map_bonus_freq

def render_game_plan_tab(session_bankroll, max_bet):
    """Render the Game Plan tab"""
    st.info("Find the best games for your bankroll based on RTP, volatility, and advantage play potential")
    
    # Load and filter games
    game_df = load_game_data()
    
    if not game_df.empty:
        # Game filters
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
            (game_df['rtp'] >= min_rtp) &
            (game_df['rtp'].notna())
        ]
        
        # Apply game type filter
        if game_type != "All":
            filtered_games = filtered_games[filtered_games['type'] == game_type]
                
        # Apply advantage filter
        if advantage_filter == "High (4-5)":
            filtered_games = filtered_games[filtered_games['advantage_play_potential'] >= 4]
        elif advantage_filter == "Medium (3)":
            filtered_games = filtered_games[filtered_games['advantage_play_potential'] == 3]
        elif advantage_filter == "Low (1-2)":
            filtered_games = filtered_games[filtered_games['advantage_play_potential'] <= 2]
                
        # Apply volatility filter
        if volatility_filter == "Low (1-2)":
            filtered_games = filtered_games[filtered_games['volatility'] <= 2]
        elif volatility_filter == "Medium (3)":
            filtered_games = filtered_games[filtered_games['volatility'] == 3]
        elif volatility_filter == "High (4-5)":
            filtered_games = filtered_games[filtered_games['volatility'] >= 4]
                
        # Apply search filter
        if search_query:
            filtered_games = filtered_games[
                filtered_games['game_name'].str.contains(search_query, case=False)
            ]
            
        if not filtered_games.empty:
            # Calculate score
            filtered_games['Score'] = (
                (filtered_games['rtp'] * 0.5) +
                (filtered_games['bonus_frequency'] * 0.2) +
                (filtered_games['advantage_play_potential'] * 0.2) +
                ((6 - filtered_games['volatility']) * 0.1)
            )
            
            # Sort and display
            filtered_games = filtered_games.sort_values('Score', ascending=False)
            
            st.subheader(f"Recommended Games ({len(filtered_games)} matches)")
            st.caption(f"Showing games with RTP ≥ {min_rtp}% and min bet ≤ ${max_min_bet:,.2f}")
            
            # Display games in a responsive grid
            st.markdown('<div class="ph-game-grid">', unsafe_allow_html=True)
            
            for _, row in filtered_games.head(50).iterrows():
                # Create the game card HTML
                game_card = f"""
                <div class="ph-game-card">
                    <div class="ph-game-title">🎰 {row['game_name']}</div>
                    <div class="ph-game-detail"><strong>🗂️ Type:</strong> {row['type']}</div>
                    <div class="ph-game-detail"><strong>💸 Min Bet:</strong> ${row['min_bet']:,.2f}</div>
                    <div class="ph-game-detail"><strong>🧠 Advantage Play:</strong> {map_advantage(int(row['advantage_play_potential']))}</div>
                    <div class="ph-game-detail"><strong>🎲 Volatility:</strong> {map_volatility(int(row['volatility']))}</div>
                    <div class="ph-game-detail"><strong>🎁 Bonus Frequency:</strong> {map_bonus_freq(row['bonus_frequency'])}</div>
                    <div class="ph-game-detail"><strong>🔢 RTP:</strong> {row['rtp']:.2f}%</div>
                    <div class="ph-game-detail"><strong>💡 Tips:</strong> {row['tips']}</div>
                </div>
                """
                
                # Render the game card with HTML interpretation
                st.markdown(game_card, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No games match your current filters. Try adjusting your criteria.")
    else:
        st.error("Failed to load game data. Please check the CSV format and column names.")