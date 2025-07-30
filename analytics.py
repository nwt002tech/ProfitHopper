import pandas as pd
import altair as alt
import streamlit as st
from utils import get_csv_download_link

def render_analytics():
    st.subheader("Bankroll Analytics")
    
    if not st.session_state.session_log:
        st.info("No sessions recorded yet. Add sessions to see analytics.")
        return
    
    cumulative_profit = sum(session['profit'] for session in st.session_state.session_log)
    current_bankroll = st.session_state.bankroll
    total_invested = sum(session['money_in'] for session in st.session_state.session_log)
    roi = (cumulative_profit / total_invested) * 100 if total_invested > 0 else 0
    avg_session_profit = cumulative_profit / len(st.session_state.session_log)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Current Bankroll", f"${current_bankroll:,.2f}",
                 delta=f"${cumulative_profit:+,.2f}")
    with col2:
        st.metric("📈 Total Profit/Loss", f"${cumulative_profit:+,.2f}")
    with col3:
        st.metric("📊 ROI", f"{roi:.1f}%")
    
    # Bankroll growth chart
    bankroll_history = [st.session_state.bankroll - cumulative_profit]
    dates = [min(session['date'] for session in st.session_state.session_log)]
    cumulative = 0
    
    for session in sorted(st.session_state.session_log, key=lambda x: x['date']):
        cumulative += session['profit']
        bankroll_history.append(st.session_state.bankroll - cumulative_profit + cumulative)
        dates.append(session['date'])
    
    st.subheader("Bankroll Growth")
    chart_data = pd.DataFrame({"Date": dates, "Bankroll": bankroll_history})
    st.line_chart(chart_data.set_index("Date"))
    
    # Game performance analysis
    st.subheader("Game Performance")
    game_performance = {}
    for session in st.session_state.session_log:
        game = session['game']
        if game not in game_performance:
            game_performance[game] = {'sessions': 0, 'total_profit': 0, 'total_invested': 0}
        game_performance[game]['sessions'] += 1
        game_performance[game]['total_profit'] += session['profit']
        game_performance[game]['total_invested'] += session['money_in']
    
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
    
    # Win/Loss distribution
    st.subheader("Win/Loss Distribution")
    profits = [s['profit'] for s in st.session_state.session_log]
    
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
        ).properties(title='Profit/Loss Distribution')
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No profit data available")
        
    # Export analytics data
    st.subheader("Export Analytics")
    if st.button("📊 Export Analytics Data to CSV"):
        analytics_df = pd.DataFrame({
            'Metric': ['Current Bankroll', 'Total Profit/Loss', 'ROI', 'Avg Session Profit'],
            'Value': [current_bankroll, cumulative_profit, f"{roi}%", avg_session_profit]
        })
        st.markdown(get_csv_download_link(analytics_df, "analytics_summary.csv"), unsafe_allow_html=True)