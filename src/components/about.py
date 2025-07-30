import streamlit as st

def render_about_tab():
    st.header("ℹ️ About ProfitHopper")
    st.write("""
    ### The Smart Bankroll Manager for Sports Bettors
    
    **ProfitHopper** helps you:
    - 📊 Track your betting bankroll
    - 🎯 Set and manage betting strategies
    - 📈 Analyze your betting performance
    - ⚖️ Manage risk with intelligent tools
    
    ### How It Works
    1. Set your bankroll and unit size
    2. Define your daily betting strategy
    3. Track your bets and results
    4. Analyze performance metrics
    
    ### Created By
    - [Your Name/Company]
    - Version 1.0
    - [Contact Information]
    
    *More features coming soon!*
    """)
    
    st.image("https://via.placeholder.com/600x200?text=ProfitHopper+Diagram", 
             caption="System Overview")