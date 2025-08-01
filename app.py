import streamlit as st
from templates import get_css, get_header
from trip_manager import initialize_trip_state, render_sidebar, get_session_bankroll, get_current_bankroll
from data_loader import load_game_data
from analytics import render_analytics
from session_manager import render_session_tracker
from utils import map_volatility

st.set_page_config(layout="wide", initial_sidebar_state="expanded", 
                  page_title="Profit Hopper Casino Manager")

initialize_trip_state()

st.markdown(get_css(), unsafe_allow_html=True)
st.markdown(get_header(), unsafe_allow_html=True)

render_sidebar()

current_bankroll = get_current_bankroll()
session_bankroll = get_session_bankroll()
max_bet = session_bankroll * 0.25
stop_loss = session_bankroll * 0.6

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
            filtered_games['Score'] = (
                (filtered_games['rtp'] * 0.5) +
                (filtered_games['bonus_frequency'] * 0.2) +
                (filtered_games['advantage_play_potential'] * 0.2) +
                ((6 - filtered_games['volatility']) * 0.1)
            )
            
            filtered_games = filtered_games.sort_values('Score', ascending=False)
            
            # Store recommendations in session state
            if 'recommended_games' not in st.session_state:
                st.session_state.recommended_games = filtered_games.head(
                    st.session_state.trip_settings['num_sessions']
                ).copy()
            
            # Recommended play order
            st.subheader("🎯 Recommended Play Order")
            num_sessions = st.session_state.trip_settings['num_sessions']
            
            if not st.session_state.recommended_games.empty:
                st.info(f"For optimal results during your {num_sessions} sessions, play games in this order:")
                st.warning("Don't see a recommended game at your casino? Use the substitution tool below!")
                st.markdown("---")
                
                # Display sessions in sequential order
                for i, (_, row) in enumerate(st.session_state.recommended_games.iterrows(), start=1):
                    # Create two columns: one for session number, one for game details
                    col1, col2 = st.columns([1, 5])
                    
                    with col1:
                        st.markdown(f"""
                        <div style="text-align:center; padding:15px; 
                                    background:#e3f2fd; border-radius:10px; border:2px solid #1976d2">
                            <div style="font-size:1.5rem; font-weight:bold;">
                                #{i}
                            </div>
                            <div style="font-size:1rem;">
                                Session
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f"""
                        <div style="padding:15px; background:#f8f9fa; border-radius:10px; 
                                    border-left:4px solid #4e89ae; margin-bottom:15px">
                            <div style="font-size:1.3rem; font-weight:bold; margin-bottom:8px;">
                                🎰 {row['game_name']}
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                                <div>
                                    <strong>⭐ Score:</strong> {row['Score']:.1f}/10
                                </div>
                                <div>
                                    <strong>🔢 RTP:</strong> {row['rtp']:.2f}%
                                </div>
                                <div>
                                    <strong>🎲 Volatility:</strong> {map_volatility(int(row['volatility']))}
                                </div>
                                <div>
                                    <strong>💸 Min Bet:</strong> ${row['min_bet']:,.2f}
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Game substitution tool
                st.subheader("🔁 Game Substitution Tool")
                st.info("If a recommended game isn't available at your casino, select it below and choose a substitute:")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    game_to_replace = st.selectbox("Select game to replace", 
                                                 options=st.session_state.recommended_games['game_name'].tolist())
                
                with col2:
                    # Get available substitutes (filtered games not already in recommendations)
                    available_games = filtered_games[
                        ~filtered_games['game_name'].isin(st.session_state.recommended_games['game_name'])
                    ]['game_name'].tolist()
                    
                    substitute_game = st.selectbox("Select substitute game", 
                                                 options=available_games)
                
                if st.button("Replace Game"):
                    # Find index of game to replace
                    idx = st.session_state.recommended_games[
                        st.session_state.recommended_games['game_name'] == game_to_replace
                    ].index[0]
                    
                    # Get substitute game data
                    new_game = filtered_games[filtered_games['game_name'] == substitute_game].iloc[0]
                    
                    # Replace in recommendations
                    st.session_state.recommended_games.loc[idx] = new_game
                    st.success(f"Replaced {game_to_replace} with {substitute_game} in your play order!")
                    st.rerun()
                
                if st.button("Reset to Original Recommendations"):
                    st.session_state.recommended_games = filtered_games.head(num_sessions).copy()
                    st.success("Play order reset to original recommendations!")
                    st.rerun()
            else:
                st.warning("Not enough games match your criteria for all sessions")
            
            st.subheader(f"🎮 Recommended Games ({len(filtered_games)} matches)")
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

with tab2:
    game_df = load_game_data()
    render_session_tracker(game_df, session_bankroll)

with tab3:
    render_analytics()