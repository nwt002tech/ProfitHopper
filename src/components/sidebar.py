import streamlit as st

def render_sidebar(metrics=None):
    with st.sidebar:
        st.header("Bankroll Dashboard")
        
        # Safe metrics display
        if metrics:
            try:
                col1, col2, col3 = st.columns(3)
                col1.metric("Current Bankroll", f"${metrics.get('current', 0):.2f}")
                col2.metric("Today's Profit", f"${metrics.get('daily_profit', 0):.2f}")
                col3.metric("ROI", f"{metrics.get('roi', 0):.2f}%")
            except Exception as e:
                st.error(f"Error displaying metrics: {e}")
        else:
            st.warning("Bankroll metrics not available")
            
        st.divider()
        
        # Navigation
        st.subheader("Quick Navigation")
        if st.button("🏠 Dashboard"):
            st.session_state.current_tab = "Dashboard"
        if st.button("🎯 New Strategy"):
            st.session_state.current_tab = "Game Plan"
        if st.button("📊 Bankroll History"):
            st.session_state.current_tab = "Bankroll"
            
        st.divider()
        
        # User preferences
        st.subheader("Preferences")
        st.checkbox("Show Advanced Metrics", value=True, key="show_advanced")
        st.selectbox("Theme", ["Light", "Dark"], key="theme")