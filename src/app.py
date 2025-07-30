import streamlit as st
import os
import sys

# Get current directory (src/)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add src directory to Python path
sys.path.insert(0, current_dir)

# Now import using the components package
from components.header import render_header
from components.sidebar import render_sidebar
from components.game_plan import render_game_plan_tab
from components.bankroll import render_bankroll_tab
from components.tools import render_tools_tab
from components.about import render_about_tab
from session_manager import init_session_state, get_bankroll_metrics

def main():
    # Initialize session state
    init_session_state()
    
    # Page configuration
    st.set_page_config(
        page_title="ProfitHopper",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Render header
    render_header()
    
    # Get bankroll metrics
    metrics = get_bankroll_metrics()
    
    # Render sidebar
    render_sidebar(metrics)
    
    # Setup tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Game Plan", "💰 Bankroll", "⚙️ Tools", "ℹ️ About"])
    
    with tab1:
        render_game_plan_tab()
        
    with tab2:
        render_bankroll_tab()
        
    with tab3:
        render_tools_tab()
        
    with tab4:
        render_about_tab()

if __name__ == "__main__":
    main()