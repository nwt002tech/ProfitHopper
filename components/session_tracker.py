# components/session_tracker.py
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_loader import load_game_data
from utils.file_handling import get_csv_download_link
from session_manager import get_bankroll_metrics

def render_session_tracker_tab(current_bankroll):
    """Render the Session Tracker tab"""
    st.info("Track your gambling sessions to monitor performance and bankroll growth")
    
    # Trip info box
    st.markdown(f"""
    <div class="trip-info-box">
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <div><strong>Current Trip:</strong> #{st.session_state.current_trip_id}</div>
            <div><strong>Casino:</strong> {st.session_state.trip_settings['casino']}</div>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <div><strong>Starting Bankroll:</strong> ${st.session_state.trip_settings['starting_bankroll']:,.2f}</div>
            <div><strong>Current Bankroll:</strong> ${current_bankroll:,.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("Session Tracker")
    
    with st.expander("➕ Add New Session", expanded=True):
        with st.form("session_form"):
            col1, col2 = st.columns(2)
            with col1:
                session_date = st.date_input("📅 Date", value=datetime.today())
                money_in = st.number_input("💵 Money In", 
                                          min_value=0.0, 
                                          value=float(st.session_state.trip_settings['starting_bankroll'] / st.session_state.trip_settings['num_sessions']),
                                          step=5.0)  # Increment by $5
            with col2:
                game_df = load_game_data()
                game_options = ["Select Game"] + list(game_df['game_name'].unique()) if not game_df.empty else ["Select Game"]
                game_played = st.selectbox("🎮 Game Played", options=game_options)
                money_out = st.number_input("💰 Money Out", 
                                           min_value=0.0, 
                                           value=0.0,
                                           step=5.0)  # Increment by $5
            
            session_notes = st.text_area("📝 Session Notes", placeholder="Record any observations, strategies, or important events during the session...")
            
            submitted = st.form_submit_button("💾 Save Session")
            
            if submitted:
                if game_played == "Select Game":
                    st.warning("Please select a game")
                else:
                    profit = money_out - money_in
                    st.session_state.session_log.append({
                        "trip_id": st.session_state.current_trip_id,
                        "date": session_date.strftime("%Y-%m-%d"),
                        "casino": st.session_state.trip_settings['casino'],
                        "game": game_played,
                        "money_in": money_in,
                        "money_out": money_out,
                        "profit": profit,
                        "notes": session_notes
                    })
                    st.success(f"Session added: ${profit:+,.2f} profit")
    
    # Display current trip sessions
    current_trip_sessions = [s for s in st.session_state.session_log if s['trip_id'] == st.session_state.current_trip_id]
    
    if current_trip_sessions:
        st.subheader(f"Trip #{st.session_state.current_trip_id} Sessions")
        
        # Sort sessions by date descending
        sorted_sessions = sorted(current_trip_sessions, key=lambda x: x['date'], reverse=True)
        
        for idx, session in enumerate(sorted_sessions):
            profit = session['profit']
            profit_class = "positive-profit" if profit >= 0 else "negative-profit"
            
            session_card = f"""
            <div class="session-card">
                <div><strong>📅 {session['date']}</strong> | 🎮 {session['game']}</div>
                <div>💵 In: ${session['money_in']:,.2f} | 💰 Out: ${session['money_out']:,.2f} | 
                <span class="{profit_class}">📈 Profit: ${profit:+,.2f}</span></div>
                <div><strong>📝 Notes:</strong> {session['notes']}</div>
            </div>
            """
            st.markdown(session_card, unsafe_allow_html=True)
        
        # Export sessions to CSV
        st.subheader("Export Data")
        if st.button("💾 Export Session History to CSV", use_container_width=True):
            session_df = pd.DataFrame(current_trip_sessions)
            st.markdown(get_csv_download_link(session_df, f"trip_{st.session_state.current_trip_id}_sessions.csv"), unsafe_allow_html=True)
    else:
        st.info("No sessions recorded for this trip yet. Add your first session above.")