import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_csv_download_link
from trip_manager import get_current_trip_sessions, get_current_bankroll
from ui_templates import trip_info_box  # Changed import

def save_session(session_date, game_played, money_in, money_out, session_notes):
    profit = money_out - money_in
    new_session = {
        "trip_id": st.session_state.current_trip_id,
        "date": session_date.strftime("%Y-%m-%d"),
        "casino": st.session_state.trip_settings['casino'],
        "game": game_played,
        "money_in": money_in,
        "money_out": money_out,
        "profit": profit,
        "notes": session_notes
    }
    
    # Update session log
    st.session_state.session_log.append(new_session)
    
    # Update trip bankroll
    current_trip_id = st.session_state.current_trip_id
    if current_trip_id not in st.session_state.trip_bankrolls:
        st.session_state.trip_bankrolls[current_trip_id] = (
            st.session_state.trip_settings['starting_bankroll']
        )
    st.session_state.trip_bankrolls[current_trip_id] += profit
    
    # Force immediate rerun to update all displays
    st.session_state.last_session_added = datetime.now()
    st.rerun()

def render_session_tracker(game_df, session_bankroll):
    st.info("Track your gambling sessions to monitor performance and bankroll growth")
    
    # Trip info box
    current_bankroll = get_current_bankroll()
    
    st.markdown(trip_info_box(
        st.session_state.current_trip_id,
        st.session_state.trip_settings['casino'],
        st.session_state.trip_settings['starting_bankroll'],
        current_bankroll
    ), unsafe_allow_html=True)
    
    st.subheader("Session Tracker")
    
    with st.expander("➕ Add New Session", expanded=True):
        with st.form("session_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                session_date = st.date_input("📅 Date", value=datetime.today())
                money_in = st.number_input("💵 Money In", 
                                          min_value=0.0, 
                                          value=float(session_bankroll),
                                          step=5.0)
            with col2:
                game_options = ["Select Game"] + list(game_df['game_name'].unique()) if not game_df.empty else ["Select Game"]
                game_played = st.selectbox("🎮 Game Played", options=game_options)
                money_out = st.number_input("💰 Money Out", 
                                           min_value=0.0, 
                                           value=0.0,
                                           step=5.0)
            
            session_notes = st.text_area("📝 Session Notes", placeholder="Record any observations, strategies, or important events during the session...")
            
            submitted = st.form_submit_button("💾 Save Session")
            
            if submitted:
                if game_played == "Select Game":
                    st.warning("Please select a game")
                else:
                    save_session(session_date, game_played, money_in, money_out, session_notes)
    
    # Display current trip sessions
    current_trip_sessions = get_current_trip_sessions()
    
    if current_trip_sessions:
        st.subheader(f"Trip #{st.session_state.current_trip_id} Sessions")
        
        # Sort sessions by date descending
        sorted_sessions = sorted(current_trip_sessions, key=lambda x: x['date'], reverse=True)
        
        for session in sorted_sessions:
            profit = session['profit']
            profit_class = "positive-profit" if profit >= 0 else "negative-profit"
            
            session_card = f"""
            <div class="session-card">
                <div style="display: flex; justify-content: space-between; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 200px;">
                        <strong>📅 {session['date']}</strong> | 🎮 {session['game']}
                    </div>
                    <div style="flex: 1; min-width: 250px; text-align: right;">
                        <span>💵 ${session['money_in']:,.2f} → 💰 ${session['money_out']:,.2f}</span>
                        <span class="{profit_class}"> | 📈 ${profit:+,.2f}</span>
                    </div>
                </div>
                <div style="margin-top: 8px; font-size: 0.9em;">
                    <strong>📝 Notes:</strong> {session['notes']}
                </div>
            </div>
            """
            st.markdown(session_card, unsafe_allow_html=True)
        
        # Export sessions to CSV
        st.subheader("Export Data")
        if st.button("💾 Export Session History to CSV"):
            session_df = pd.DataFrame(current_trip_sessions)
            st.markdown(get_csv_download_link(session_df, f"trip_{st.session_state.current_trip_id}_sessions.csv"), unsafe_allow_html=True)
    else:
        st.info("No sessions recorded for this trip yet. Add your first session above.")