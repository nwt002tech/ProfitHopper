# trip_manager.py
# Version: 2025-08-13-4
# Changes:
# - Removed the “Share your location (one‑time to enable near‑me)” text from the sidebar.
# - Restores/guards original imports so prior behavior is preserved.
# - ADDS: get_current_trip_sessions(), record_session_performance() to satisfy session_manager.py.

from __future__ import annotations
from typing import List, Optional, Set, Callable, Dict, Any
from datetime import datetime, timezone

import streamlit as st

# --- Keep your original imports, but guard so ImportError won't crash the app ---
try:
    from data_loader import load_trip_data  # type: ignore
except Exception:
    load_trip_data = None  # type: ignore

try:
    from browser_location import request_location  # noqa: F401
except Exception:
    request_location = None  # type: ignore


# -----------------------------
# Session State Initialization
# -----------------------------

def initialize_trip_state(
    *,
    total_bankroll: Optional[float] = None,
    num_sessions: Optional[int] = None,
) -> None:
    """Ensure required session_state keys exist."""
    ss = st.session_state

    if "total_bankroll" not in ss:
        ss.total_bankroll = float(total_bankroll) if total_bankroll is not None else 100.0

    if "num_sessions" not in ss:
        ss.num_sessions = int(num_sessions) if num_sessions is not None else 5

    if "session_bankroll" not in ss:
        ss.session_bankroll = _safe_divide(ss.total_bankroll, max(ss.num_sessions, 1))

    if "max_bet" not in ss:
        # Default: ~10% of session bankroll, min $1 if tiny
        ss.max_bet = round(max(1.0, ss.session_bankroll * 0.1), 2)

    if "stop_loss" not in ss:
        # Default: ~40% of session bankroll; never full session bankroll
        ss.stop_loss = round(min(ss.session_bankroll * 0.4, ss.session_bankroll * 0.9), 2)

    if "current_bankroll" not in ss:
        ss.current_bankroll = float(ss.total_bankroll)

    if "session_log" not in ss:
        ss.session_log: List[dict] = []

    if "blacklisted_games" not in ss:
        ss.blacklisted_games: Set[str] = set()

    if "volatility_bias" not in ss:
        ss.volatility_bias = "Medium"

    if "win_streak" not in ss:
        ss.win_streak = 0


# -----------------------------
# Sidebar (compact; requested text removed)
# -----------------------------

def render_sidebar() -> None:
    """Render compact sidebar WITHOUT the 'Share your location…' text."""
    initialize_trip_state()

    with st.sidebar:
        st.header("🛠️ compact sidebar")  # keeping your label

        # 🚫 Removed the line that previously displayed:
        # "Share your location (one‑time to enable near‑me)"

        # --- Bankroll Controls ---
        total_bankroll = st.number_input(
            "Total Bankroll ($)",
            min_value=0.0,
            step=10.0,
            value=float(st.session_state.total_bankroll),
            key="total_bankroll",
        )

        num_sessions = st.number_input(
            "Number of Sessions",
            min_value=1,
            step=1,
            value=int(st.session_state.num_sessions),
            key="num_sessions",
        )

        # Recalculate derived fields
        st.session_state.session_bankroll = round(
            _safe_divide(total_bankroll, max(int(num_sessions), 1)),
            2
        )

        default_max_bet = round(max(1.0, st.session_state.session_bankroll * 0.1), 2)
        st.session_state.max_bet = st.number_input(
            "Max Bet per Session ($)",
            min_value=0.0,
            step=0.5,
            value=float(st.session_state.get("max_bet", default_max_bet)),
        )

        default_stop_loss = round(min(st.session_state.session_bankroll * 0.4,
                                      st.session_state.session_bankroll * 0.9), 2)
        st.session_state.stop_loss = st.number_input(
            "Stop Loss per Session ($)",
            min_value=0.0,
            step=1.0,
            value=float(st.session_state.get("stop_loss", default_stop_loss)),
        )

        st.markdown(
            _quick_kpis_html(
                session_bankroll=st.session_state.session_bankroll,
                max_bet=st.session_state.max_bet,
                stop_loss=st.session_state.stop_loss,
            ),
            unsafe_allow_html=True,
        )

        # Volatility preference
        st.session_state.volatility_bias = st.selectbox(
            "Volatility Preference",
            options=["Low", "Medium", "High"],
            index=_index_for(["Low", "Medium", "High"], st.session_state.volatility_bias),
        )

        st.session_state.win_streak = st.number_input(
            "Current Win Streak",
            min_value=0,
            max_value=20,
            step=1,
            value=int(st.session_state.win_streak),
        )

        # Optional: show any trip data you load (guarded)
        _maybe_show_trip_data(load_trip_data)

        # Blacklist management
        st.subheader("Blacklist a Game")
        with st.form("blacklist_form", clear_on_submit=True):
            name = st.text_input("Game name to blacklist")
            submitted = st.form_submit_button("Add to blacklist")
            if submitted and name.strip():
                blacklist_game(name.strip())
                st.success(f"Blacklisted: {name.strip()}")

        bl = get_blacklisted_games()
        if bl:
            st.caption("Currently blacklisted:")
            st.write(", ".join(sorted(bl)))


# -----------------------------
# Public API used by app.py / session_manager.py
# -----------------------------

def get_session_bankroll() -> float:
    return float(st.session_state.get("session_bankroll", 0.0))


def get_current_bankroll() -> float:
    return float(st.session_state.get("current_bankroll", st.session_state.get("total_bankroll", 0.0)))


def blacklist_game(game_name: str) -> None:
    if "blacklisted_games" not in st.session_state:
        st.session_state.blacklisted_games = set()
    st.session_state.blacklisted_games.add(game_name)


def get_blacklisted_games() -> List[str]:
    if "blacklisted_games" not in st.session_state:
        return []
    return list(st.session_state.blacklisted_games)


def get_volatility_adjustment(volatility: Optional[str]) -> float:
    """Return a small factor based on volatility preference."""
    v = (volatility or st.session_state.get("volatility_bias", "Medium")).strip().lower()
    if v.startswith("low"):
        return 0.92
    if v.startswith("high"):
        return 1.08
    return 1.00  # medium/default


def get_win_streak_factor(streak: Optional[int] = None) -> float:
    """Return a small factor (>1 for positive streak)."""
    if streak is None:
        streak = int(st.session_state.get("win_streak", 0))
    bump = min(max(streak, 0), 10) * 0.01  # gentle, capped
    return 1.00 + bump


def get_current_trip_sessions() -> List[Dict[str, Any]]:
    """
    Return a simple list of sessions with status derived from session_log and num_sessions.
    Each item: {"index": int, "status": "done"|"pending", "result": float|None}
    """
    initialize_trip_state()
    total = int(st.session_state.get("num_sessions", 0))
    log: List[dict] = list(st.session_state.get("session_log", []))
    sessions: List[Dict[str, Any]] = []

    # Mark completed sessions based on log length; associate results where present
    for i in range(total):
        if i < len(log):
            entry = log[i] if isinstance(log[i], dict) else {}
            sessions.append({
                "index": i + 1,
                "status": "done",
                "result": float(entry.get("delta", 0.0))
            })
        else:
            sessions.append({
                "index": i + 1,
                "status": "pending",
                "result": None
            })
    return sessions


def record_session_performance(delta: float, notes: str = "") -> None:
    """
    Append a session result and update bankroll.
    delta > 0 = profit, delta < 0 = loss.
    """
    initialize_trip_state()
    # Update bankroll
    st.session_state.current_bankroll = float(st.session_state.get("current_bankroll", 0.0)) + float(delta)

    # Log entry
    entry = {
        "delta": float(delta),
        "notes": str(notes) if notes else "",
        "bankroll_after": float(st.session_state.current_bankroll),
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if "session_log" not in st.session_state:
        st.session_state.session_log = []
    st.session_state.session_log.append(entry)


# -----------------------------
# Helpers
# -----------------------------

def _safe_divide(a: float, b: float) -> float:
    return float(a) / float(b) if float(b) != 0.0 else 0.0


def _index_for(options: List[str], value: str) -> int:
    try:
        return options.index(value)
    except Exception:
        return 1  # default "Medium"


def _quick_kpis_html(session_bankroll: float, max_bet: float, stop_loss: float) -> str:
    # Compact, mobile-friendly row of KPIs
    return f"""
    <div class="ph-kpis" style="display:flex;gap:8px;flex-wrap:wrap">
      <div style="flex:1;min-width:110px;border:1px solid #eee;border-radius:8px;padding:8px;">
        <div style="font-size:14px;opacity:0.7;">🎯 Session</div>
        <div style="font-size:18px;font-weight:600;">${session_bankroll:,.2f}</div>
      </div>
      <div style="flex:1;min-width:110px;border:1px solid #eee;border-radius:8px;padding:8px;">
        <div style="font-size:14px;opacity:0.7;">⬆️ Max Bet</div>
        <div style="font-size:18px;font-weight:600;">${max_bet:,.2f}</div>
      </div>
      <div style="flex:1;min-width:110px;border:1px solid #eee;border-radius:8px;padding:8px;">
        <div style="font-size:14px;opacity:0.7;">🛑 Stop Loss</div>
        <div style="font-size:18px;font-weight:600;">${stop_loss:,.2f}</div>
      </div>
    </div>
    """


def _maybe_show_trip_data(loader: Optional[Callable] = None) -> None:
    """Safely call a provided loader and show results if available."""
    if loader is None:
        return
    try:
        trip_data = loader()
        if trip_data is not None:
            st.subheader("Trip Data")
            st.dataframe(trip_data)
    except Exception:
        # Non-fatal if loader is wired differently in your setup
        pass