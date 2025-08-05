from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Any

from trip_manager import initialize_trip_state

def _compute_trip_summaries() -> pd.DataFrame:
    """Aggregate session data into a DataFrame of trip summaries with advanced metrics."""
    initialize_trip_state()

    session_log: List[Dict[str, Any]] = st.session_state.get("session_log", [])
    trip_bankrolls: Dict[int, float] = st.session_state.get("trip_bankrolls", {})

    if not trip_bankrolls:
        return pd.DataFrame(columns=[
            "trip_id", "num_sessions", "profit", "current_bankroll", 
            "starting_bankroll", "casino", "avg_return", "max_drawdown", "sharpe"
        ])

    trips: Dict[int, List[Dict[str, Any]]] = {}
    for session in session_log:
        tid = session.get("trip_id")
        trips.setdefault(tid, []).append(session)

    data: List[Dict[str, Any]] = []
    for trip_id, current_bankroll in trip_bankrolls.items():
        sessions_for_trip = trips.get(trip_id, [])
        profits = [s.get("profit", 0.0) for s in sessions_for_trip]
        num_sessions = len(sessions_for_trip)
        
        profit = sum(profits)
        starting_bankroll = current_bankroll - profit
        casino = sessions_for_trip[0].get("casino") if sessions_for_trip else "N/A"
        
        # Calculate advanced metrics
        avg_return = profit / num_sessions if num_sessions > 0 else 0
        max_drawdown = min(profits) if profits else 0
        
        # Sharpe Ratio (risk-adjusted return)
        if num_sessions > 1:
            returns_std = np.std(profits)
            sharpe = avg_return / returns_std if returns_std > 0 else 0
        else:
            sharpe = 0
        
        data.append({
            "trip_id": trip_id,
            "num_sessions": num_sessions,
            "profit": profit,
            "current_bankroll": current_bankroll,
            "starting_bankroll": starting_bankroll,
            "casino": casino,
            "avg_return": avg_return,
            "max_drawdown": max_drawdown,
            "sharpe": sharpe
        })
    return pd.DataFrame(data)

def render_analytics() -> None:
    """Render a comprehensive summary of all recorded trips with advanced analytics."""
    summary_df = _compute_trip_summaries()

    st.subheader("Trip Performance Overview")
    if summary_df.empty:
        st.info("No trip data available yet. Play some sessions to see analytics here.")
        return

    # Format display dataframe
    display_df = summary_df.copy()
    display_df["profit"] = display_df["profit"].map(lambda x: f"${x:+,.2f}")
    display_df["current_bankroll"] = display_df["current_bankroll"].map(lambda x: f"${x:,.2f}")
    display_df["starting_bankroll"] = display_df["starting_bankroll"].map(lambda x: f"${x:,.2f}")
    display_df["avg_return"] = display_df["avg_return"].map(lambda x: f"${x:+,.2f}")
    display_df["max_drawdown"] = display_df["max_drawdown"].map(lambda x: f"${x:+,.2f}")
    display_df["sharpe"] = display_df["sharpe"].map(lambda x: f"{x:.2f}")

    # Display dataframe with metrics
    st.dataframe(display_df.rename(columns={
        "trip_id": "Trip ID",
        "num_sessions": "Sessions",
        "profit": "Profit",
        "current_bankroll": "Current Bankroll",
        "starting_bankroll": "Starting Bankroll",
        "casino": "Casino",
        "avg_return": "Avg Return",
        "max_drawdown": "Max Drawdown",
        "sharpe": "Sharpe Ratio"
    }), hide_index=True)

    # Profit chart
    chart_df = summary_df[["trip_id", "profit"]].set_index("trip_id")
    st.subheader("Profit by Trip")
    st.bar_chart(chart_df)
    
    # Risk-adjusted performance chart
    if len(summary_df) > 1:
        st.subheader("Risk-Adjusted Performance")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Best Sharpe Ratio", 
                      f"{summary_df['sharpe'].max():.2f}",
                      summary_df.loc[summary_df['sharpe'].idxmax(), 'casino'])
        with col2:
            st.metric("Worst Drawdown", 
                      f"${summary_df['max_drawdown'].min():,.2f}",
                      summary_df.loc[summary_df['max_drawdown'].idxmin(), 'casino'])
        
        # Sharpe ratio visualization
        sharpe_df = summary_df[["trip_id", "sharpe"]].set_index("trip_id")
        st.line_chart(sharpe_df)