from .utils import get_csv_download_link
import pandas as pd
import streamlit as st

def delete_session(index):
    session = st.session_state.session_log[index]
    st.session_state.bankroll -= session['profit']
    st.session_state.session_log.pop(index)
    st.success(f"Session deleted: {session['date']} - {session['game']}")

def save_session(session_date, game_played, money_in, money_out, session_notes):
    profit = money_out - money_in
    st.session_state.session_log.append({
        "date": session_date.strftime("%Y-%m-%d"),
        "game": game_played,
        "money_in": money_in,
        "money_out": money_out,
        "profit": profit,
        "notes": session_notes
    })
    st.session_state.bankroll += profit
    st.success(f"Session added: ${profit:+,.2f} profit")

def render_session_tracker(game_df):
    st.subheader("Session Tracker")
    
    with st.expander("➕ Add New Session", expanded=True):
        with st.form("session_form"):
            col1, col2 = st.columns(2)
            with col1:
                session_date = st.date_input("📅 Date")
                money_in = st.number_input("💵 Money In", min_value=0.0, 
                                         value=st.session_state.bankroll / st.session_state.session_count)
            with col2:
                game_options = ["Select Game"] + list(game_df['game_name'].unique())
                game_played = st.selectbox("🎮 Game Played", options=game_options)
                money_out = st.number_input("💰 Money Out", min_value=0.0, value=0.0)
            
            session_notes = st.text_area("📝 Session Notes", 
                                        placeholder="Record observations or strategies...")
            
            submitted = st.form_submit_button("💾 Save Session")
            
            if submitted:
                if game_played == "Select Game":
                    st.warning("Please select a game")
                else:
                    save_session(session_date, game_played, money_in, money_out, session_notes)
    
    if st.session_state.session_log:
        st.subheader("Session History")
        sorted_sessions = sorted(st.session_state.session_log, 
                                key=lambda x: x['date'], reverse=True)
        
        for idx, session in enumerate(sorted_sessions):
            profit = session['profit']
            profit_class = "positive-profit" if profit >= 0 else "negative-profit"
            
            session_card = f"""
            <div class="session-card">
                <div><strong>📅 {session['date']}</strong> | 🎮 {session['game']}</div>
                <div>💵 In: ${session['money_in']:,.2f} | 💰 Out: ${session['money_out']:,.2f} | 
                <span class="{profit_class}">📈 Profit: ${profit:+,.2f}</span></div>
                <div><strong>📝 Notes:</strong> {session['notes']}</div>
                <div style="margin-top: 5px;">
                    <button onclick="deleteSession({idx})" style="background-color: #e74c3c; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">Delete</button>
                </div>
            </div>
            """
            st.markdown(session_card, unsafe_allow_html=True)
        
        st.markdown(f"""
        <script>
        function deleteSession(index) {{
            Streamlit.setComponentValue(JSON.stringify({{action: "delete", index: index}}));
        }}
        </script>
        """, unsafe_allow_html=True)
        
        st.subheader("Export Data")
        if st.button("💾 Export Session History to CSV"):
            session_df = pd.DataFrame(st.session_state.session_log)
            st.markdown(get_csv_download_link(session_df, "session_history.csv"), unsafe_allow_html=True)
    else:
        st.info("No sessions recorded yet. Add your first session above.")