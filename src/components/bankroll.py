import streamlit as st

def render_bankroll_tab():
    st.header("💰 Bankroll Management")
    
    # Bankroll summary
    st.subheader("Current Bankroll")
    current_bankroll = st.number_input("Enter current bankroll", min_value=0.0, value=1000.0)
    
    # Bankroll history
    st.subheader("Bankroll History")
    st.line_chart([1000, 1200, 950, 1100, 1300])
    
    # Growth metrics
    st.metric("Total Growth", "$300 (30%)", "15% since last month")
    
    st.write("Bankroll management tools will be developed here...")