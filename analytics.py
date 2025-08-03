"""
Module for rendering trip analytics in the Profit Hopper application.

This module exposes a single function, :func:`render_analytics`, which can be
called from the main application to display high‑level statistics about all
recorded trips. Unlike the previous version of this file, there is no top‑level
execution of Streamlit code here—importing this module will not cause any
markup to be displayed. Instead, all Streamlit calls are contained inside
``render_analytics``, ensuring that analytics content only appears when the
function is explicitly invoked.

The analytics presented are intentionally simple: for each trip recorded in the
session state, the function computes the number of sessions, total profit,
current bankroll and inferred starting bankroll. It then displays a summary
table and a bar chart of profits by trip. The design uses Streamlit's native
components rather than raw HTML to avoid accidentally rendering raw markup at
the top of the page.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from typing import List, Dict, Any

from trip_manager import initialize_trip_state


def _compute_trip_summaries() -> pd.DataFrame:
    """Aggregate session data into a DataFrame of trip summaries.

    This helper function looks at ``st.session_state.session_log`` and
    ``st.session_state.trip_bankrolls`` to build a summary for each trip. If
    there are no recorded trips yet, an empty DataFrame is returned.

    Returns
    -------
    pandas.DataFrame
        A DataFrame where each row corresponds to a trip and contains the
        following columns: ``trip_id``, ``num_sessions``, ``profit``,
        ``current_bankroll``, ``starting_bankroll`` and ``casino`` (where
        available).
    """
    # Ensure session state keys exist
    initialize_trip_state()

    session_log: List[Dict[str, Any]] = st.session_state.get("session_log", [])
    trip_bankrolls: Dict[int, float] = st.session_state.get("trip_bankrolls", {})

    if not trip_bankrolls:
        return pd.DataFrame(columns=[
            "trip_id",
            "num_sessions",
            "profit",
            "current_bankroll",
            "starting_bankroll",
            "casino",
        ])

    # Organise sessions by trip_id
    trips: Dict[int, List[Dict[str, Any]]] = {}
    for session in session_log:
        tid = session.get("trip_id")
        trips.setdefault(tid, []).append(session)

    data: List[Dict[str, Any]] = []
    for trip_id, current_bankroll in trip_bankrolls.items():
        sessions_for_trip = trips.get(trip_id, [])
        profit = sum(s.get("profit", 0.0) for s in sessions_for_trip)
        starting_bankroll = current_bankroll - profit
        num_sessions = len(sessions_for_trip)
        # Determine casino from first session if available
        casino = sessions_for_trip[0].get("casino") if sessions_for_trip else "N/A"
        data.append({
            "trip_id": trip_id,
            "num_sessions": num_sessions,
            "profit": profit,
            "current_bankroll": current_bankroll,
            "starting_bankroll": starting_bankroll,
            "casino": casino,
        })
    return pd.DataFrame(data)


def render_analytics() -> None:
    """Render a summary of all recorded trips and their performance.

    This function builds a summary table of trips and displays it using
    Streamlit. It also plots a bar chart of trip profits to help users quickly
    visualise which trips were profitable or not. If there are no trips
    recorded yet, it informs the user accordingly.

    Unlike a full Streamlit app, this function does not set the page
    configuration or load global CSS. Those responsibilities belong to the
    caller (typically the main ``app.py`` file). It only displays content in
    the location where it is called, making it safe to import in other
    modules without side effects.
    """
    # Compute the trip summary table
    summary_df = _compute_trip_summaries()

    st.subheader("Trip Performance Overview")
    if summary_df.empty:
        st.info("No trip data available yet. Play some sessions to see analytics here.")
        return

    # Format numeric columns for display
    display_df = summary_df.copy()
    display_df["profit"] = display_df["profit"].map(lambda x: f"${x:,.2f}")
    display_df["current_bankroll"] = display_df["current_bankroll"].map(lambda x: f"${x:,.2f}")
    display_df["starting_bankroll"] = display_df["starting_bankroll"].map(lambda x: f"${x:,.2f}")

    # Display the summary table
    st.dataframe(display_df.rename(columns={
        "trip_id": "Trip ID",
        "num_sessions": "Sessions",
        "profit": "Profit",
        "current_bankroll": "Current Bankroll",
        "starting_bankroll": "Starting Bankroll",
        "casino": "Casino",
    }), hide_index=True)

    # Plot profits by trip
    chart_df = summary_df[["trip_id", "profit"]].set_index("trip_id")
    st.subheader("Profit by Trip")
    # Streamlit bar_chart automatically uses the index as x-axis
    st.bar_chart(chart_df)