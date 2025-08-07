import streamlit as st
import numpy as np

def initialize_trip_state():
    """
    Initialize all necessary session state variables for trip management.
    Adds a `trip_started` flag to indicate whether a trip has been started.
    """
    # Ensure session_log is always initialized
    if 'session_log' not in st.session_state:
        st.session_state.session_log = []
    # Initialize current trip ID
    if 'current_trip_id' not in st.session_state:
        st.session_state.current_trip_id = 1
    # Initialize casino list
    if 'casino_list' not in st.session_state:
        st.session_state.casino_list = sorted([
            "L'auberge Lake Charles",
            "Golden Nugget Lake Charles",
            "Caesar's Horseshoe Lake Charles",
            "Delta Downs",
            "Island View",
            "Paragon Marksville",
            "Coushatta"
        ])
    # Initialize trip settings with proper defaults
    if 'trip_settings' not in st.session_state:
        st.session_state.trip_settings = {
            'casino': st.session_state.casino_list[0] if st.session_state.casino_list else "",
            'starting_bankroll': 100.0,
            'num_sessions': 10
        }
    # Initialize trip bankrolls tracking
    if 'trip_bankrolls' not in st.session_state:
        st.session_state.trip_bankrolls = {1: 100.0}
    # Initialize game blacklist
    if 'game_blacklist' not in st.session_state:
        st.session_state.game_blacklist = {}
    # Initialize session performance tracker
    if 'session_performance' not in st.session_state:
        st.session_state.session_performance = {}
    # Initialize trip_started flag
    if 'trip_started' not in st.session_state:
        st.session_state.trip_started = False

def get_current_trip_sessions():
    return [s for s in st.session_state.session_log 
            if s['trip_id'] == st.session_state.current_trip_id]

def get_trip_profit(trip_id=None):
    trip_id = trip_id or st.session_state.current_trip_id
    sessions = [s for s in st.session_state.session_log 
               if s['trip_id'] == trip_id]
    return sum(s['profit'] for s in sessions)

def get_current_bankroll():
    # Always calculate from scratch
    starting = st.session_state.trip_settings['starting_bankroll']
    return starting + get_trip_profit()

def get_session_bankroll():
    """Improved conservative bankroll allocation with profit protection"""
    current_bankroll = get_current_bankroll()
    completed_sessions = len(get_current_trip_sessions())
    remaining_sessions = max(1, st.session_state.trip_settings['num_sessions'] - completed_sessions)
    # Base session = 20% of starting bankroll
    base_session = st.session_state.trip_settings['starting_bankroll'] * 0.20
    # Progressive adjustment: Never risk more than 30% of profits
    if current_bankroll > st.session_state.trip_settings['starting_bankroll']:
        profit = current_bankroll - st.session_state.trip_settings['starting_bankroll']
        return min(base_session + (profit * 0.3), 500)  # Cap at $500
    # Loss protection: Never risk more than base session during losing streaks
    return min(base_session, current_bankroll / remaining_sessions)

def blacklist_game(game_name):
    trip_id = st.session_state.current_trip_id
    if trip_id not in st.session_state.game_blacklist:
        st.session_state.game_blacklist[trip_id] = set()
    st.session_state.game_blacklist[trip_id].add(game_name)
    st.rerun()

def get_blacklisted_games():
    trip_id = st.session_state.current_trip_id
    return st.session_state.game_blacklist.get(trip_id, set())

def get_volatility_adjustment():
    """Calculate volatility-based adjustment factor (0.7-1.3)"""
    sessions = get_current_trip_sessions()
    if len(sessions) < 3:
        return 1.0  # Neutral if not enough data
    # Calculate recent volatility (last 5 sessions)
    last_5_profits = [s['profit'] for s in sessions[-5:]]
    if not last_5_profits:
        return 1.0
    volatility = np.std(last_5_profits)
    avg_profit = np.mean(last_5_profits)
    # High volatility with negative returns -> reduce risk
    if volatility > abs(avg_profit) * 1.5 and avg_profit < 0:
        return 0.7
    # Low volatility with positive returns -> increase opportunity
    if volatility < abs(avg_profit) * 0.8 and avg_profit > 0:
        return 1.3
    return 1.0

def record_session_performance(profit):
    """Track session performance for streak analysis"""
    trip_id = st.session_state.current_trip_id
    if 'session_performance' not in st.session_state:
        st.session_state.session_performance = {}
    if trip_id not in st.session_state.session_performance:
        st.session_state.session_performance[trip_id] = []
    st.session_state.session_performance[trip_id].append(profit)

def get_win_streak_factor():
    """Calculate win streak multiplier (0.8-1.2)"""
    trip_id = st.session_state.current_trip_id
    if 'session_performance' not in st.session_state:
        return 1.0
    performances = st.session_state.session_performance.get(trip_id, [])
    if len(performances) < 3:
        return 1.0
    # Calculate last 5 session win rate
    last_5 = performances[-5:]
    win_rate = sum(1 for p in last_5 if p > 0) / len(last_5)
    # Adjust strategy based on recent performance
    if win_rate > 0.7:  # Winning streak
        return 1.2
    elif win_rate < 0.3:  # Losing streak
        return 0.8
    return 1.0

def render_sidebar():
    # Ensure state is initialized before accessing
    initialize_trip_state()
    with st.sidebar:
        st.header("Trip Settings")
        # Trip ID display
        st.markdown(f"""
        <div style="display:flex; align-items:center; margin-bottom:20px;">
            <span style="font-weight:bold; margin-right:10px;">Current Trip ID:</span>
            <span class="trip-id-badge">{st.session_state.current_trip_id}</span>
        </div>
        """, unsafe_allow_html=True)
        # Casino selection
        # New casino text input: simply add to the casino list but do not modify trip settings yet
        new_casino = st.text_input("Add New Casino")
        if new_casino and new_casino not in st.session_state.casino_list:
            st.session_state.casino_list.append(new_casino)
            st.session_state.casino_list.sort()
            st.success(f"Added {new_casino} to casino list")
        # Use the previously selected casino from trip_settings as the default index for the selectbox
        default_casino_idx = 0
        if st.session_state.trip_settings.get('casino') in st.session_state.casino_list:
            default_casino_idx = st.session_state.casino_list.index(st.session_state.trip_settings['casino'])
        # Present the casino selection widget but avoid writing to trip_settings on every rerender
        selected_casino = st.selectbox(
            "Casino",
            options=st.session_state.casino_list,
            index=default_casino_idx,
            key='casino_select'
        )
        # Bankroll and sessions inputs
        # These widgets use keys to maintain internal state; do not update trip_settings on each rerender
        default_bankroll = st.session_state.trip_settings.get('starting_bankroll', 100.0)
        starting_bankroll = st.number_input(
            "Starting Bankroll ($)",
            min_value=0.0,
            value=default_bankroll,
            step=100.0,
            format="%.2f",
            key='bankroll_input'
        )
        default_sessions = st.session_state.trip_settings.get('num_sessions', 10)
        num_sessions = st.number_input(
            "Number of Sessions",
            min_value=1,
            value=int(default_sessions),
            step=1,
            key='session_count_input'
        )
        # Start new trip button with trip_started logic
        if st.button("Start New Trip"):
            # When the user starts a new trip, commit the selected values to trip_settings
            st.session_state.trip_settings['casino'] = selected_casino
            st.session_state.trip_settings['starting_bankroll'] = float(starting_bankroll)
            st.session_state.trip_settings['num_sessions'] = int(num_sessions)
            if not st.session_state.trip_started:
                # First time starting a trip
                st.session_state.trip_started = True
                # Initialize bankroll for current trip
                st.session_state.trip_bankrolls[st.session_state.current_trip_id] = (
                    st.session_state.trip_settings['starting_bankroll']
                )
                st.success(f"Started trip! Trip ID: {st.session_state.current_trip_id}")
            else:
                # Subsequent trips increment trip ID and reset logs
                st.session_state.current_trip_id += 1
                st.session_state.session_log = []
                # Initialize session performance for the new trip
                if 'session_performance' not in st.session_state:
                    st.session_state.session_performance = {}
                st.session_state.session_performance[st.session_state.current_trip_id] = []
                # Initialize bankroll for new trip
                st.session_state.trip_bankrolls[st.session_state.current_trip_id] = (
                    st.session_state.trip_settings['starting_bankroll']
                )
                st.success(f"Started new trip! Trip ID: {st.session_state.current_trip_id}")
            st.rerun()
        st.markdown("---")
        # Trip summary only if trip has started
        st.subheader("Trip Summary")
        if st.session_state.trip_started:
            trip_sessions = get_current_trip_sessions()
            trip_profit = get_trip_profit()
            current_bankroll = get_current_bankroll()
            st.markdown(f"**Casino:** {st.session_state.trip_settings['casino']}")
            st.markdown(f"**Starting Bankroll:** ${st.session_state.trip_settings['starting_bankroll']:,.2f}")
            st.markdown(f"**Current Bankroll:** ${current_bankroll:,.2f}")
            st.markdown(f"**Sessions Completed:** {len(trip_sessions)}/{st.session_state.trip_settings['num_sessions']}")
            # Win streak indicator
            if trip_sessions:
                last_5 = [s['profit'] for s in trip_sessions[-5:]]
                if last_5:
                    win_rate = sum(1 for p in last_5 if p > 0) / len(last_5) * 100
                    streak_status = "🔥 Hot Streak!" if win_rate > 70 else "❄️ Cold Streak" if win_rate < 30 else "➖ Neutral"
                    st.markdown(f"**Recent Win Rate:** {win_rate:.0f}% ({streak_status})")
        else:
            st.info("No active trip yet. Use the button above to start a trip.")
        st.markdown("---")
        st.warning("""
        **Gambling Risk Notice:**  
        - These strategies don't guarantee profits  
        - Never gamble with money you can't afford to lose  
        - Set strict loss limits before playing  
        - Gambling addiction help: 1-800-522-4700
        """)