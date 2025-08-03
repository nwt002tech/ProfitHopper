"""
Module for rendering trip analytics in the Profit Hopper application.

This module exposes a single function, :func:`render_analytics`, which can be
called from the main application to display high‑level statistics about all
recorded trips. There is no top‑level Streamlit code execution here—importing
this module will not render anything. All rendering happens inside
``render_analytics`` when it is explicitly invoked.

The analytics presented are intentionally simple: for each trip recorded in
the session state, the function computes the number of sessions, total
profit, current bankroll and inferred starting bankroll. It then displays a
summary table and a bar chart of profits by trip. Streamlit's native
components are used throughout to avoid raw HTML markup.
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
    initialize_trip_state()

    session_log: List[Dict[str, Any]] = st.session_state.get("session_log", [])
    trip_bankrolls: Dict[int, float] = st.session_state.get("trip_bankrolls", {})

    if not trip_bankrolls:
        return pd.DataFrame(columns=[
            "trip_id", "num_sessions", "profit",
            "current_bankroll", "starting_bankroll", "casino"
        ])

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

    Builds a summary table of trips using :func:`_compute_trip_summaries` and
    displays it via Streamlit. Also plots a bar chart of trip profits. If no
    trips have been recorded yet, a friendly message is shown instead.
    """
    summary_df = _compute_trip_summaries()

    st.subheader("Trip Performance Overview")
    if summary_df.empty:
        st.info("No trip data available yet. Play some sessions to see analytics here.")
        return

    display_df = summary_df.copy()
    display_df["profit"] = display_df["profit"].map(lambda x: f"${x:,.2f}")
    display_df["current_bankroll"] = display_df["current_bankroll"].map(lambda x: f"${x:,.2f}")
    display_df["starting_bankroll"] = display_df["starting_bankroll"].map(lambda x: f"${x:,.2f}")

    st.dataframe(display_df.rename(columns={
        "trip_id": "Trip ID",
        "num_sessions": "Sessions",
        "profit": "Profit",
        "current_bankroll": "Current Bankroll",
        "starting_bankroll": "Starting Bankroll",
        "casino": "Casino",
    }), hide_index=True)

    chart_df = summary_df[["trip_id", "profit"]].set_index("trip_id")
    st.subheader("Profit by Trip")
    st.bar_chart(chart_df)