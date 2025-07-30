import streamlit as st
import os
import sys

# Resolve absolute paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
COMPONENTS_DIR = os.path.join(SRC_DIR, 'components')

# Add all critical directories to path
for path in [BASE_DIR, SRC_DIR, COMPONENTS_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import modules using absolute paths
from session_manager import init_session_state, get_bankroll_metrics
from header import render_header
from sidebar import render_sidebar
from game_plan import render_game_plan_tab
from bankroll import render_bankroll_tab
from tools import render_tools_tab
from about import render_about_tab

def main():
    init_session_state()
    
    st.set_page_config(
        page_title="ProfitHopper",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    render_header()
    metrics = get_bankroll_metrics()
    render_sidebar(metrics)
    
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