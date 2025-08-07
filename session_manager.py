import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_csv_download_link
from trip_manager import get_current_trip_sessions, get_current_bankroll, blacklist_game, get_blacklisted_games, record_session_performance
from ui_templates import trip_info_box

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
    # Record performance for streak analysis
    record_session_performance(profit)
    # Force immediate rerun to update all displays
    st.session_state.last_session_added = datetime.now()
    st.rerun()

def render_session_tracker(game_df, session_bankroll):
    """
    Render the session tracking interface. Sessions will not be pre-populated
    until the user explicitly clicks the "Start New Session" button. This avoids
    prematurely setting session information and bankroll allocation.
    """
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
    # Initialize the session_active flag if it doesn't exist
    if 'session_active' not in st.session_state:
        st.session_state.session_active = False
    # Only show the "Start New Session" button if no session is active
    if not st.session_state.session_active:
        if st.button("▶️ Start New Session", key="start_session_button"):
            # Mark session as active and store the session bankroll
            st.session_state.session_active = True
            st.session_state.session_bankroll = float(session_bankroll)
            st.rerun()
        st.info("Click 'Start New Session' to begin tracking a new gambling session.")
    else:
        # Session is active – display the form to add session details
        with st.expander("➕ Add New Session", expanded=True):
            with st.form("session_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    session_date = st.date_input("📅 Date", value=datetime.today())
                    # Use stored session bankroll as the default money_in value
                    default_money_in = st.session_state.get('session_bankroll', float(session_bankroll))
                    money_in = st.number_input("💵 Money In",
                                               min_value=0.0,
                                               value=default_money_in,
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
                        # Save the session and then mark session as inactive
                        save_session(session_date, game_played, money_in, money_out, session_notes)
                        # After saving, reset session_active flag so next session must be started manually
                        st.session_state.session_active = False
                        # Remove the stored bankroll for clarity
                        st.session_state.pop('session_bankroll', None)
                        st.success("Session saved! Start a new session when you're ready.")
                        st.rerun()
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
        # Calculate session analytics
        profits = [s['profit'] for s in sorted_sessions]
        avg_profit = sum(profits) / len(profits)
        max_drawdown = min(profits)
        win_rate = sum(1 for p in profits if p > 0) / len(profits) * 100
        st.markdown(f"""
        <div class="compact-summary" style="margin:20px 0;">
            <div class="summary-card">
                <div class="summary-icon">📊</div>
                <div class="summary-label">Avg Profit/Session</div>
                <div class="summary-value">${avg_profit:+,.2f}</div>
            </div>
            <div class="summary-card">
                <div class="summary-icon">📉</div>
                <div class="summary-label">Max Drawdown</div>
                <div class="summary-value">${max_drawdown:+,.2f}</div>
            </div>
            <div class="summary-card">
                <div class="summary-icon">🏆</div>
                <div class="summary-label">Win Rate</div>
                <div class="summary-value">{win_rate:.1f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        # Export sessions to CSV
        st.subheader("Export Data")
        if st.button("💾 Export Session History to CSV"):
            session_df = pd.DataFrame(current_trip_sessions)
            st.markdown(get_csv_download_link(session_df, f"trip_{st.session_state.current_trip_id}_sessions.csv"), unsafe_allow_html=True)
    else:
        st.info("No sessions recorded for this trip yet. Add your first session above.")