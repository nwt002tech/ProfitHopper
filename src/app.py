# /mount/src/profithopper/src/app.py
import sys
from pathlib import Path
import streamlit as st

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import local modules
from session_manager import init_session_state, get_bankroll_metrics

# Rest of your application code
def main():
    st.title("Profit Hopper Casino Manager")
    st.write("Application is loading...")
    
    # Initialize session state
    init_session_state()
    
    # Example usage
    metrics = get_bankroll_metrics()
    st.write(f"Bankroll Metrics: {metrics}")
    
    # ... rest of your application logic

if __name__ == "__main__":
    main()