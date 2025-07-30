import streamlit as st
import pandas as pd

def render_game_plan_tab():
    st.header("🎯 Game Plan")
    
    # Strategy form
    with st.form("game_plan_form"):
        st.subheader("Strategy Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            starting_bankroll = st.number_input("Starting Bankroll ($)", min_value=1, value=1000)
            unit_size = st.number_input("Unit Size ($)", min_value=1, value=50)
        with col2:
            max_units = st.number_input("Max Units at Risk", min_value=1, value=3)
            max_bets_per_day = st.number_input("Max Bets per Day", min_value=1, value=5)
        
        target_roi = st.slider("Target ROI (%)", min_value=1, max_value=100, value=15)
        
        submitted = st.form_submit_button("Save Strategy")
        if submitted:
            st.session_state.strategy = {
                "starting_bankroll": starting_bankroll,
                "unit_size": unit_size,
                "max_units": max_units,
                "target_roi": target_roi,
                "max_bets_per_day": max_bets_per_day
            }
            st.success("Strategy saved successfully!")
    
    # Professional strategy display
    if "strategy" in st.session_state:
        st.divider()
        st.subheader("Current Strategy")
        strategy = st.session_state.strategy
        
        # Strategy metrics in cards
        cols = st.columns(5)
        metrics = [
            ("Starting Bankroll", f"${strategy['starting_bankroll']}"),
            ("Unit Size", f"${strategy['unit_size']}"),
            ("Max Risk", f"{strategy['max_units']} units"),
            ("Target ROI", f"{strategy['target_roi']}%"),
            ("Max Bets/Day", strategy['max_bets_per_day'])
        ]
        
        for col, (label, value) in zip(cols, metrics):
            with col:
                st.metric(label, value)
        
        # Detailed strategy table
        st.subheader("Risk Management Parameters")
        risk_data = {
            "Bankroll %": [1, 2, 3],
            "Unit Size": [
                strategy["unit_size"],
                strategy["unit_size"] * 2,
                strategy["unit_size"] * 3
            ],
            "Max Risk ($)": [
                strategy["unit_size"],
                strategy["unit_size"] * 2,
                strategy["unit_size"] * 3
            ]
        }
        risk_df = pd.DataFrame(risk_data)
        st.dataframe(risk_df.style.format({
            "Unit Size": "${:,.0f}",
            "Max Risk ($)": "${:,.0f}"
        }), hide_index=True)
        
        # ROI visualization
        st.subheader("ROI Projection")
        roi = strategy["target_roi"] / 100
        days = st.slider("Projection Period (days)", 7, 365, 30)
        
        # Calculate projected growth
        daily_growth = [strategy["starting_bankroll"]]
        for day in range(1, days + 1):
            daily_growth.append(daily_growth[-1] * (1 + roi))
        
        # Display chart and metrics
        chart_col, metric_col = st.columns([3, 1])
        with chart_col:
            st.line_chart(daily_growth)
        with metric_col:
            growth_pct = (daily_growth[-1] / daily_growth[0] - 1) * 100
            st.metric("Projected Value", f"${daily_growth[-1]:,.0f}", 
                      f"{growth_pct:.1f}% growth")