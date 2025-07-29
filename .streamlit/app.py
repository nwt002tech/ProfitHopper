import streamlit as st
from src.session_manager import init_session_state, get_bankroll_metrics
from src.components.header import render_header
from src.components.sidebar import render_sidebar
from src.components.game_plan import render_game_plan_tab
from src.components.session_tracker import render_session_tracker_tab
from src.components.analytics import render_analytics_tab

def main():
    # Initialize session state
    init_session_state()
    
    # Get bankroll metrics
    session_bankroll, max_bet, stop_loss, current_bankroll = get_bankroll_metrics()
    
    # Render header with CSS
    render_header()
    
    # Render sidebar
    render_sidebar()
    
    # Render sticky header with metrics
    st.markdown(f"""
    <div class="ph-sticky-header">
        <div style="display:flex; justify-content:space-around; text-align:center; flex-wrap: wrap;">
            <div style="padding: 10px; min-width: 150px;"><strong>💰 Current Bankroll</strong><br>${current_bankroll:,.2f}</div>
            <div style="padding: 10px; min-width: 150px;"><strong>📅 Session Bankroll</strong><br>${session_bankroll:,.2f}</div>
            <div style="padding: 10px; min-width: 150px;"><strong>💸 Max Bet</strong><br>${max_bet:,.极2f}</div>
            <div style="padding: 10px; min-width: 150px;"><strong>🚫 Stop Loss</strong><br><span class="ph-stop-loss">${stop_loss:,.2f}</span></div>
        </极div>
    </div>
    """, unsafe_allow_html=True)
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🎮 Game Plan", "📊 Session Tracker", "📈 Trip Analytics"])
    
    with tab1:
        render_game_plan_tab(session_bankroll, max_bet)
    
    with tab2:
        render_session_tracker_tab(current_bankroll)
    
    with tab3:
        render_analytics_tab()

if __name__ == "__main__":
    main()