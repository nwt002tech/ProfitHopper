# trip_manager.py
# Version: 2025-08-13-stable-2
# Changes in this version:
#   - get_volatility_adjustment now accepts an optional parameter (default None)
#     and falls back to st.session_state["volatility_bias"] if not provided.
#   - Still removes ONLY the "Share your location (one‑time to enable near‑me)" text.
#   - Keeps request_location behavior (no visible text).
#   - Provides all functions imported by app.py/session_manager.py.
#   - Lazy-imports load_trip_data inside render_sidebar() to avoid import-time errors.

import streamlit as st
from datetime import datetime, timezone

# Keep location behavior; we just won't show the old text line.
try:
    from browser_location import request_location
except Exception:
    request_location = None  # type: ignore


# -----------------------------
# Session State Setup
# -----------------------------

def initialize_trip_state():
    ss = st.session_state
    if "total_bankroll" not in ss:
        ss.total_bankroll = 0.0
    if "session_bankroll" not in ss:
        ss.session_bankroll = 0.0
    if "current_bankroll" not in ss:
        ss.current_bankroll = ss.total_bankroll
    if "num_sessions" not in ss:
        ss.num_sessions = 5
    if "session_log" not in ss:
        ss.session_log = []  # list of dicts
    if "blacklisted_games" not in ss:
        ss.blacklisted_games = set()
    if "volatility_bias" not in ss:
        ss.volatility_bias = "Medium"
    if "win_streak" not in ss:
        ss.win_streak = 0


# -----------------------------
# Sidebar (with requested text removed)
# -----------------------------

def render_sidebar():
    initialize_trip_state()

    with st.sidebar:
        st.header("🛠️ compact sidebar")

        # 🚫 Removed the line:
        # st.sidebar.write("Share your location (one‑time to enable near‑me)")

        # Quietly request location if available (no visible prompt text)
        try:
            if request_location:
                request_location()
        except Exception:
            pass  # never crash the UI for location issues

        # --- Trip data display (lazy import to avoid ImportError on module load) ---
        load_trip_data = None
        try:
            from data_loader import load_trip_data as _load_trip_data  # type: ignore
            load_trip_data = _load_trip_data
        except Exception:
            load_trip_data = None

        if load_trip_data:
            try:
                trip_data = load_trip_data()
                if trip_data is not None:
                    st.subheader("Trip Data")
                    st.dataframe(trip_data)
            except Exception:
                pass  # don't crash rendering if the loader throws


# -----------------------------
# Public API used by app.py / session_manager.py
# -----------------------------

def get_session_bankroll():
    return float(st.session_state.get("session_bankroll", 0.0))


def get_current_bankroll():
    # Falls back to total if current not yet set
    return float(st.session_state.get("current_bankroll", st.session_state.get("total_bankroll", 0.0)))


def blacklist_game(game_name: str):
    if "blacklisted_games" not in st.session_state:
        st.session_state.blacklisted_games = set()
    st.session_state.blacklisted_games.add(str(game_name))


def get_blacklisted_games():
    if "blacklisted_games" not in st.session_state:
        return []
    return list(st.session_state.blacklisted_games)


def get_volatility_adjustment(volatility: str | None = None):
    """
    Accepts an optional volatility string. If None, uses st.session_state['volatility_bias'].
    Returns a small multiplier used elsewhere in analytics/scoring.
    """
    if volatility is None:
        volatility = str(st.session_state.get("volatility_bias", "Medium"))

    v = str(volatility).strip().lower()
    if v.startswith("low"):
        return 0.9
    if v.startswith("high"):
        return 1.1
    return 1.0  # Medium/default


def get_win_streak_factor(streak: int | None = None):
    """
    Optional streak param. If None, uses st.session_state['win_streak'].
    Keep behavior gentle to avoid extreme swings.
    """
    if streak is None:
        streak = int(st.session_state.get("win_streak", 0))
    # Simple placeholder factor; safe and consistent
    return 1.0


def get_current_trip_sessions():
    """
    Return a simple list of sessions with status based on session_log and num_sessions.
    Each item: {"index": int, "status": "done" | "pending", "result": float | None}
    """
    initialize_trip_state()
    total = int(st.session_state.get("num_sessions", 0))
    log = list(st.session_state.get("session_log", []))
    sessions = []
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


def record_session_performance(delta: float, notes: str = ""):
    """
    Append a session result and update bankroll.
    delta > 0 = profit, delta < 0 = loss.
    """
    initialize_trip_state()
    # Update current bankroll
    st.session_state.current_bankroll = float(st.session_state.get("current_bankroll", 0.0)) + float(delta)

    # Log the session result
    entry = {
        "delta": float(delta),
        "notes": str(notes) if notes else "",
        "bankroll_after": float(st.session_state.current_bankroll),
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    st.session_state.session_log.append(entry)