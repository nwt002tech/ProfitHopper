import streamlit as st

def initialize_trip_state():
    if 'session_log' not in st.session_state:
        st.session_state.session_log = []
    if 'current_trip_id' not in st.session_state:
        st.session_state.current_trip_id = 1
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
    if 'trip_settings' not in st.session_state:
        st.session_state.trip_settings = {
            'casino': st.session_state.casino_list[0] if st.session_state.casino_list else "",
            'starting_bankroll': 100.0,  # CHANGED: $100 instead of $1000
            'num_sessions': 10
        }

def get_current_trip_sessions():
    if 'session_log' not in st.session_state:
        return []
    return [s for s in st.session_state.session_log 
            if s['trip_id'] == st.session_state.current_trip_id]

def get_trip_profit():
    sessions = get_current_trip_sessions()
    return sum(s['profit'] for s in sessions)

def get_current_bankroll():
    if not hasattr(st.session_state, 'trip_settings'):
        return 0
    return st.session_state.trip_settings['starting_bankroll'] + get_trip_profit()

def get_session_bankroll():
    current_bankroll = get_current_bankroll()
    remaining_sessions = max(1, st.session_state.trip_settings['num_sessions'] - len(get_current_trip_sessions()))
    return current_bankroll / remaining_sessions

def render_sidebar():
    with st.sidebar:
        st.header("Trip Manager")
        
        # Create new trip
        with st.expander("➕ New Trip", expanded=False):
            with st.form("new_trip_form"):
                casino = st.selectbox("Casino", options=st.session_state.casino_list)
                starting_bankroll = st.number_input("Starting Bankroll", 
                                                   min_value=1.0, 
                                                   value=100.0,  # CHANGED: $100 instead of $1000
                                                   step=1.0)
                num_sessions = st.number_input("Planned Sessions", min_value=1, value=10)
                
                if st.form_submit_button("Start New Trip"):
                    st.session_state.current_trip_id += 1
                    st.session_state.session_log = []
                    st.session_state.trip_settings = {
                        'casino': casino,
                        'starting_bankroll': starting_bankroll,
                        'num_sessions': num_sessions
                    }
                    st.rerun()
        
        # Trip summary
        st.subheader("Current Trip")
        if hasattr(st.session_state, 'trip_settings'):
            st.write(f"**Casino:** {st.session_state.trip_settings['casino']}")
            st.write(f"**Starting Bankroll:** ${st.session_state.trip_settings['starting_bankroll']:,.2f}")
            st.write(f"**Sessions:** {len(get_current_trip_sessions())}/{st.session_state.trip_settings['num_sessions']}")
            st.write(f"**Current Profit:** ${get_trip_profit():+,.2f}")
        else:
            st.info("No active trip")
        
        # End trip button
        if st.button("End Current Trip", key="end_trip"):
            st.session_state.session_log = [s for s in st.session_state.session_log 
                                          if s['trip_id'] != st.session_state.current_trip_id]
            st.success(f"Trip #{st.session_state.current_trip_id} ended")
            st.session_state.current_trip_id = max(1, st.session_state.current_trip_id - 1)
            st.rerun()