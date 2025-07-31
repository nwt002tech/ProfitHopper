import pandas as pd
import altair as alt
import streamlit as st
from utils import get_csv_download_link
from trip_manager import get_current_trip_sessions, get_trip_profit, get_current_bankroll

def render_analytics():
    st.info("Analyze your trip performance and track your bankroll growth")
    
    current_trip_sessions = get_current_trip_sessions()
    
    if not current_trip_sessions:
        st.info("No sessions recorded for this trip yet. Add sessions to see analytics.")
        return
    
    # Calculate cumulative values
    trip_profit = get_trip_profit()
    current_bankroll = get_current_bankroll()
    
    # Calculate performance metrics
    total_invested = sum(s['money_in'] for s in current_trip_sessions)
    roi = (trip_profit / total_invested) * 100 if total_invested > 0 else 0
    avg_session_profit = trip_profit / len(current_trip_sessions)
    
    # Display key metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Current Bankroll", f"${current_bankroll:,.2f}",
                 delta=f"${trip_profit:+,.2f}")
    with col2:
        st.metric("📈 Total Profit/Loss", f"${trip_profit:+,.2f}")
    with col3:
        st.metric("📊 ROI", f"{roi:.1f}%")
    
    # Bankroll growth chart
    bankroll_history = [st.session_state.trip_settings['starting_bankroll']]
    dates = [min(s['date'] for s in current_trip_sessions)]
    cumulative = 0
    
    for session in sorted(current_trip_sessions, key=lambda x: x['date']):
        cumulative += session['profit']
        bankroll_history.append(st.session_state.trip_settings['starting_bankroll'] + cumulative)
        dates.append(session['date'])
    
    st.subheader("Bankroll Growth")
    chart_data = pd.DataFrame({
        "Date": dates,
        "Bankroll": bankroll_history
    })
    st.line_chart(chart_data.set_index("Date"))
    
    # Game performance analysis
    st.subheader("Game Performance")
    game_performance = {}
    for session in current_trip_sessions:
        game = session['game']
        if game not in game_performance:
            game_performance[game] = {
                'sessions': 0,
                'total_profit': 0,
                'total_invested': 0
            }
        game_performance[game]['sessions'] += 1
        game_performance[game]['total_profit'] += session['profit']
        game_performance[game]['total_invested'] += session['money_in']
    
    # Create performance DataFrame
    perf_df = pd.DataFrame.from_dict(game_performance, orient='index')
    perf_df['ROI'] = (perf_df['total_profit'] / perf_df['total_invested']) * 100
    perf_df['Avg Profit'] = perf_df['total_profit'] / perf_df['sessions']
    perf_df = perf_df.sort_values('ROI', ascending=False)
    
    st.dataframe(perf_df[['sessions', 'total_profit', 'Avg Profit', 'ROI']].rename(columns={
        'sessions': 'Sessions',
        'total_profit': 'Total Profit',
        'Avg Profit': 'Avg Profit/Session',
        'ROI': 'ROI (%)'
    }).style.format({
        'Total Profit': '${:,.2f}',
        'Avg Profit/Session': '${:,.2f}',
        'ROI (%)': '{:.1f}%'
    }))
    
    # Win/Loss distribution using Altair
    st.subheader("Win/Loss Distribution")
    profits = [s['profit'] for s in current_trip_sessions]
    
    if profits:
        df = pd.DataFrame({
            'Profit': profits,
            'Type': ['Win' if p >= 0 else 'Loss' for p in profits]
        })
        
        chart = alt.Chart(df).mark_bar().encode(
            alt.X("Profit:Q", bin=alt.Bin(maxbins=20), title='Profit/Loss Amount'),
            alt.Y('count()', title='Frequency'),
            color=alt.Color('Type', scale=alt.Scale(
                domain=['Win', 'Loss'],
                range=['#27ae60', '#e74c3c']
            ))
        ).properties(
            title='Profit/Loss Distribution'
        )
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No profit data available")
        
    # Export analytics data
    st.subheader("Export Analytics")
    if st.button("📊 Export Trip Analytics to CSV"):
        analytics_df = pd.DataFrame({
            'Metric': ['Trip ID', 'Casino', 'Starting Bankroll', 'Current Bankroll', 
                      'Total Profit/Loss', 'ROI', 'Avg Session Profit', 'Sessions Completed'],
            'Value': [st.session_state.current_trip_id, st.session_state.trip_settings['casino'], 
                     st.session_state.trip_settings['starting_bankroll'], current_bankroll,
                     trip_profit, f"{roi}%", avg_session_profit, len(current_trip_sessions)]
        })
        st.markdown(get_csv_download_link(analytics_df, f"trip_{st.session_state.current_trip_id}_analytics.csv"), unsafe_allow_html=True)