with tab1:
    st.info("Find the best games for your bankroll based on RTP, volatility, and advantage play potential")
    
    game_df = load_game_data()
    
    if not game_df.empty:
        with st.expander("🔍 Game Filters", expanded=False):
            # ... (filter controls remain unchanged) ...
        
        # Apply filters
        filtered_games = game_df[
            (game_df['min_bet'] <= max_min_bet) &
            (game_df['rtp'] >= min_rtp)
        ]
        
        # ... (additional filters remain unchanged) ...
        
        if not filtered_games.empty:
            # Enhanced scoring algorithm
            # ... (scoring calculation remains unchanged) ...
            
            # Sort by score descending
            filtered_games = filtered_games.sort_values('Score', ascending=False)
            
            # Get recommended games for the number of sessions
            num_sessions = st.session_state.trip_settings['num_sessions']
            recommended_games = filtered_games.head(num_sessions)
            
            # Display bankroll suitability information
            ideal_bet = session_bankroll * 0.05
            acceptable_bet = session_bankroll * 0.1
            high_risk_threshold = session_bankroll * 0.1
            
            st.markdown(f"""
            <div class="trip-info-box">
                <h4>💰 Bankroll Suitability Guide</h4>
                <p>Game recommendations are optimized for your <strong>${session_bankroll:,.2f} session bankroll</strong>:</p>
                <ul>
                    <li><strong>Ideal min bet</strong>: ≤ ${ideal_bet:,.2f} (5% of session bankroll)</li>
                    <li><strong>Acceptable min bet</strong>: ≤ ${acceptable_bet:,.2f} (10% of session bankroll)</li>
                    <li><strong>High-risk min bet</strong>: > ${high_risk_threshold:,.2f} (10% of session bankroll)</li>
                </ul>
                <p>Games with min bets exceeding 10% of your session bankroll are penalized in scoring.</p>
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
                    from templates import game_card
                    st.markdown(game_card(row), unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No games match your current filters. Try adjusting your criteria.")
    else:
        st.error("Failed to load game data. Please check the CSV format and column names.")