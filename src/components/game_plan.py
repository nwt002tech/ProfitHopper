import streamlit as st

def render_game_plan_tab():
    st.header("🎯 Game Plan")
    
    # Basic input fields
    with st.form("game_plan_form"):
        st.subheader("Bankroll Management")
        starting_bankroll = st.number_input("Starting Bankroll ($)", min_value=1, value=1000)
        unit_size = st.number_input("Unit Size ($)", min_value=1, value=50)
        max_units = st.number_input("Max Units at Risk", min_value=1, value=3)
        
        st.subheader("Betting Strategy")
        target_roi = st.slider("Target ROI (%)", min_value=1, max_value=100, value=15)
        max_bets_per_day = st.number_input("Max Bets per Day", min_value=1, value=5)
        
        submitted = st.form_submit_button("Save Strategy")
        if submitted:
            st.session_state.strategy = {
                "starting_bankroll": starting_bankroll,
                "unit_size": unit_size,
                "max_units": max_units,
                "target_roi": target_roi,
                "max_bets_per_day": max_bets_per_day
            }
            st.success("Strategy saved!")
    
    # Display current strategy
    if "strategy" in st.session_state:
        st.divider()
        st.subheader("Current Strategy")
        st.json(st.session_state.strategy)