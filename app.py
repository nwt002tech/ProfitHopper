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
            # Calculate game scores
            filtered_games['Score'] = (
                (filtered_games['rtp'] * 0.5) +
                (filtered_games['bonus_frequency'] * 0.2) +
                (filtered_games['advantage_play_potential'] * 0.2) +
                ((6 - filtered_games['volatility']) * 0.1)
            )
            
            # Sort by score descending
            filtered_games = filtered_games.sort_values('Score', ascending=False)
            
            # Recommended play order
            st.subheader("🎯 Recommended Play Order")
            num_sessions = st.session_state.trip_settings['num_sessions']
            recommended_games = filtered_games.head(num_sessions)
            
            if not recommended_games.empty:
                st.info(f"For optimal results during your {num_sessions} sessions, play games in this order:")
                
                # Create columns for the play order
                cols = st.columns(3)
                for i, (_, row) in enumerate(recommended_games.iterrows()):
                    with cols[i % 3]:
                        st.markdown(f"""
                        <div style="text-align:center; margin-bottom:20px; padding:15px; 
                                    background:#f0f8ff; border-radius:10px; border:2px solid #4e89ae">
                            <div style="font-size:1.3rem; font-weight:bold; margin-bottom:10px;">
                                Session #{i+1}
                            </div>
                            <div style="font-size:1.1rem; margin-bottom:8px;">
                                🎰 {row['game_name']}
                            </div>
                            <div style="font-size:0.9rem;">
                                <div>⭐ Score: {row['Score']:.1f}/10</div>
                                <div>🔢 RTP: {row['rtp']:.2f}%</div>
                                <div>🎲 Volatility: {map_volatility(int(row['volatility']))}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
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