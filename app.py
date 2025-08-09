import os
os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'poll'

import streamlit as st
import numpy as np
from ui_templates import get_css, get_header
from trip_manager import initialize_trip_state, render_sidebar, get_session_bankroll, get_current_bankroll, blacklist_game, get_blacklisted_games, get_volatility_adjustment, get_win_streak_factor
# Prefer Supabase-integrated loader if available
from data_loader_supabase import load_game_data
from analytics import render_analytics
from session_manager import render_session_tracker
from utils import map_volatility, map_advantage, map_bonus_freq, get_game_image_url
from admin_panel import show_admin_panel

st.set_page_config(layout="wide", initial_sidebar_state="expanded",
                  page_title="Profit Hopper Casino Manager")

initialize_trip_state()

st.markdown(get_css(), unsafe_allow_html=True)
st.markdown(get_header(), unsafe_allow_html=True)

render_sidebar()

# Only proceed with main content if a trip has been started
if not st.session_state.get('trip_started', False):
    st.info("No active trip. Use the **Start New Trip** button in the sidebar to begin.")
else:
    border_colors = {
        "Very Conservative": "#28a745",
        "Conservative": "#28a745",
        "Moderate": "#17a2b8",
        "Standard": "#ffc107",
        "Aggressive": "#dc3545"
    }
    try:
        current_bankroll = get_current_bankroll()
        session_bankroll = get_session_bankroll()
        volatility_adjustment = get_volatility_adjustment()
        win_streak_factor = get_win_streak_factor()

        # Determine base strategy tiers based on session bankroll. These tiers
        # reflect conservative risk management recommendations from bankroll
        # management literature: smaller bankrolls warrant lower bet fractions
        # and tighter loss limits【3202499585933†L105-L133】【962936390273927†L110-L128】.
        if session_bankroll < 20:
            strategy_type = "Very Conservative"
            max_bet = max(0.01, session_bankroll * 0.05)
            stop_loss = session_bankroll * 0.30
            bet_unit = max(0.01, session_bankroll * 0.015)
        elif session_bankroll < 100:
            strategy_type = "Conservative"
            max_bet = session_bankroll * 0.10
            stop_loss = session_bankroll * 0.40
            bet_unit = max(0.05, session_bankroll * 0.02)
        elif session_bankroll < 500:
            strategy_type = "Moderate"
            max_bet = session_bankroll * 0.20
            stop_loss = session_bankroll * 0.50
            bet_unit = max(0.10, session_bankroll * 0.03)
        else:
            strategy_type = "Aggressive"
            max_bet = session_bankroll * 0.25
            stop_loss = session_bankroll * 0.60
            bet_unit = max(0.25, session_bankroll * 0.04)

        # Adjust betting parameters using win streak and volatility factors. A
        # winning streak justifies slightly larger bets and stop-losses, while
        # periods of poor performance or high volatility demand caution【829292623680176†L84-L98】.
        max_bet *= win_streak_factor * volatility_adjustment
        stop_loss *= (2 - win_streak_factor)
        bet_unit *= win_streak_factor * volatility_adjustment
        estimated_spins = int(session_bankroll / bet_unit) if bet_unit > 0 else 0

    except Exception as e:
        st.error(f"Error calculating strategy: {str(e)}")
        strategy_type = "Standard"
        max_bet = 25.0
        stop_loss = 100.0
        bet_unit = 5.0
        estimated_spins = 50

    st.markdown(f"""
    <div style='
        background: white;
        border-radius: 8px;
        padding: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border-left: 4px solid {border_colors.get(strategy_type, "#ffc107")};
        margin-bottom: 0;
    '>
        <div style='display:flex; align-items:center; justify-content:center;'>
            <div style='font-size:1.5rem; margin-right:15px;'>📊</div>
            <div style='text-align:center;'>
                <div style='font-size:1.1rem; font-weight:bold;'>{strategy_type} Strategy</div>
                <div style='font-size:0.8rem; color:#7f8c8d;'>
                    Max Bet: ${max_bet:,.2f} | Stop Loss: ${stop_loss:,.2f} | Spins: {estimated_spins}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Card styles
    st.markdown("""
    <style>
        .card-container {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 15px;
            margin-top: 0;
        }
        .metric-card {
            flex: 1;
            background: white;
            border-radius: 8px;
            padding: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            height: 100px;
        }
        .metric-icon {
            font-size: 1.5rem;
            margin-bottom: 5px;
        }
        .metric-label {
            font-size: 0.8rem;
            color: #7f8c8d;
        }
        .metric-value {
            font-size: 1.1rem;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="card-container">
        <div class="metric-card">
            <div class="metric-icon">💰</div>
            <div class="metric-label">Bankroll</div>
            <div class="metric-value">${current_bankroll:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">💵</div>
            <div class="metric-label">Session</div>
            <div class="metric-value">${session_bankroll:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-icon">🪙</div>
            <div class="metric-label">Unit</div>
            <div class="metric-value">${bet_unit:,.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if win_streak_factor > 1 or volatility_adjustment > 1 or win_streak_factor < 1 or volatility_adjustment < 1:
        indicators = []
        if win_streak_factor > 1:
            indicators.append(f"🔥 +{int((win_streak_factor-1)*100)}%")
        elif win_streak_factor < 1:
            indicators.append(f"❄️ -{int((1-win_streak_factor)*100)}%")
        if volatility_adjustment > 1:
            indicators.append(f"📈 +{int((volatility_adjustment-1)*100)}%")
        elif volatility_adjustment < 1:
            indicators.append(f"📉 -{int((1-volatility_adjustment)*100)}%")
        if indicators:
            st.markdown(f"""
            <div style='display:flex; gap:10px; margin:5px 0 15px; font-size:0.85rem; flex-wrap:wrap;'>
                <div style='font-weight:bold;'>Active Adjustments:</div>
                <div style='display:flex; gap:8px; flex-wrap:wrap;'>
                    {''.join([f'<div>{ind}</div>' for ind in indicators])}
                </div>
            </div>
            """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🎮 Game Plan", "📊 Session Tracker", "📈 Trip Analytics", "🛠️ Admin"])

    with tab1:
        st.info("Find the best games for your bankroll based on RTP, volatility, and advantage play potential")
        game_df = load_game_data()
        # Refine generic tip text after loading. If a tip starts with
        # "Play when bonus frequency", replace it with a more specific explanation
        # of what constitutes a high or low bonus frequency. High bonus frequency
        # implies bonus rounds occur roughly every 30–40 spins; low frequency means
        # 50+ spins per bonus【778567328630233†L105-L125】【555999948454253†L117-L121】.

def _is_admin_authenticated() -> bool:
    # Accept password from Streamlit secrets or environment
    expected = (
        st.secrets.get("ADMIN_PASS", None)
        if hasattr(st, "secrets") else None
    ) or os.environ.get("ADMIN_PASS")

    # Also require Supabase Service Role Key to be present for write ops
    has_service_key = bool(os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))

    with st.container():
        st.subheader("Admin Login")
        pwd = st.text_input("Enter admin password", type="password")
        ok = st.button("Log in")

    if ok:
        if not expected:
            st.error("ADMIN_PASS not configured in secrets or environment.")
            return False
        if not has_service_key:
            st.error("SUPABASE_SERVICE_ROLE_KEY is missing; admin write actions will fail.")
            # Still allow login, but warn. Return True so UI is visible.
            return pwd == expected
        return pwd == expected

    return False

        def refine_tip(tip: str) -> str:
            if isinstance(tip, str) and tip.strip().lower().startswith("play when bonus frequency"):
                return (
                    "Play when bonus frequency is high (≈30–40 spins per bonus). "
                    "If you find it takes more than about 50 spins to trigger a bonus, switch to a different game as the bonus is relatively rare."  # noqa: E501
                )
            return tip
        if not game_df.empty and 'tips' in game_df.columns:
            game_df['tips'] = game_df['tips'].apply(refine_tip)
        if not game_df.empty:
            with st.expander("🔍 Game Filters", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    min_rtp = st.slider("Minimum RTP (%)", 85.0, 99.9, 92.0, step=0.1)
                    game_type = st.selectbox("Game Type", ["All"] + list(game_df['type'].unique()))
                with col2:
                    max_min_bet = st.slider("Max Min Bet", 
                                           float(game_df['min_bet'].min()), 
                                           float(game_df['min_bet'].max() * 2), 
                                           float(max_bet), 
                                           step=1.0)
                    advantage_filter = st.selectbox("Advantage Play Potential", 
                                                  ["All", "High (4-5)", "Medium (3)", "Low (1-2)"])
                with col3:
                    volatility_filter = st.selectbox("Volatility", 
                                                   ["All", "Low (1-2)", "Medium (3)", "High (4-5)"])
                    search_query = st.text_input("Search Game Name")
            filtered_games = game_df[
                (game_df['min_bet'] <= max_min_bet) &
                (game_df['rtp'] >= min_rtp)
            ]
            if game_type != "All":
                filtered_games = filtered_games[filtered_games['type'] == game_type]
            if advantage_filter == "High (4-5)":
                filtered_games = filtered_games[filtered_games['advantage_play_potential'] >= 4]
            elif advantage_filter == "Medium (3)":
                filtered_games = filtered_games[filtered_games['advantage_play_potential'] == 3]
            elif advantage_filter == "Low (1-2)":
                filtered_games = filtered_games[filtered_games['advantage_play_potential'] <= 2]
            if volatility_filter == "Low (1-2)":
                filtered_games = filtered_games[filtered_games['volatility'] <= 2]
            elif volatility_filter == "Medium (3)":
                filtered_games = filtered_games[filtered_games['volatility'] == 3]
            elif volatility_filter == "High (4-5)":
                filtered_games = filtered_games[filtered_games['volatility'] >= 4]
            if search_query:
                filtered_games = filtered_games[
                    filtered_games['game_name'].str.contains(search_query, case=False)
                ]
            blacklisted = get_blacklisted_games()
            if blacklisted:
                filtered_games = filtered_games[~filtered_games['game_name'].isin(blacklisted)]
            if not filtered_games.empty:
                # Copy to avoid modifying original DataFrame
                games = filtered_games.copy()
                # Calculate suitability metrics for each game based on research:
                # - House edge: lower is better【412033640411085†L118-L170】
                # - Advantage play potential: gives player edge【935812346186569†L144-L160】
                # - Bonus frequency: more frequent bonuses add value【730932054797511†L135-L157】
                # - Volatility: lower volatility reduces risk, especially for smaller bankrolls【829292623680176†L107-L132】
                # - Min bet relative to recommended bet: ensure affordability

                def compute_score(row):
                    # House edge component
                    house_edge = 1.0 - row['rtp'] / 100.0
                    rtp_component = (1 - house_edge)  # higher is better
                    # Advantage play component scaled 0-1
                    adv_factor = max(0, (row['advantage_play_potential'] - 1) / 4)
                    # Bonus frequency (already 0-1)
                    bonus_component = row['bonus_frequency']
                    # Volatility risk component: lower risk = higher score
                    vol_factor = max(0, (5 - row['volatility']) / 4)
                    # Min bet penalty: compare to 3% of session bankroll
                    recommended_bet_base = session_bankroll * 0.03
                    ratio = row['min_bet'] / recommended_bet_base if recommended_bet_base > 0 else 1
                    bet_penalty = 1 / (1 + max(ratio - 1, 0))  # 1 if ratio <= 1, declines afterwards
                    # Additional volatility penalty for small bankroll + high volatility
                    volatility_penalty = 1.0
                    if session_bankroll < 50 and row['volatility'] >= 4:
                        volatility_penalty = 0.7
                    # Weighted sum; weights sum to 1
                    score = (
                        0.25 * rtp_component +
                        0.35 * adv_factor +
                        0.15 * bonus_component +
                        0.15 * vol_factor +
                        0.10 * bet_penalty
                    ) * volatility_penalty
                    return score

                def compute_recommended_bet(row):
                    # Base bet fraction (3% of bankroll) adjusted for volatility: higher volatility -> smaller bet
                    base_fraction = 0.03 * (3 / row['volatility'])
                    # Cap fraction to 5% for very low volatility
                    bet_fraction = min(max(base_fraction, 0.01), 0.05)
                    suggested = session_bankroll * bet_fraction
                    # Ensure bet meets the game's minimum
                    bet_amount = max(row['min_bet'], suggested)
                    # Don't exceed max_bet defined by strategy
                    bet_amount = min(bet_amount, max_bet)
                    return bet_amount

                # Compute scores and recommended bets
                games['Score'] = games.apply(compute_score, axis=1)
                games['RecommendedBet'] = games.apply(compute_recommended_bet, axis=1)
                # Sort games by score descending
                games = games.sort_values('Score', ascending=False)
                num_sessions = st.session_state.trip_settings['num_sessions']
                recommended_games = games.head(num_sessions)
                st.subheader(f"🎯 Recommended Play Order ({len(recommended_games)} games for {num_sessions} sessions)")
                st.info(f"Based on your **{strategy_type}** strategy and ${session_bankroll:,.2f} session bankroll:")
                st.caption("Recommendations prioritize high expected return, advantage play potential, affordability, and risk management.")
                st.caption("Games with high volatility or high minimum bets relative to your bankroll are automatically penalized.")
                st.caption("Don't see a game at your casino? Swipe left (click 'Not Available') to replace it")
                if not recommended_games.empty:
                    st.markdown('<div class="ph-game-grid">', unsafe_allow_html=True)
                    for i, (_, row) in enumerate(recommended_games.iterrows(), start=1):
                        # Determine risk label based on volatility
                        vol_label = map_volatility(int(row['volatility']))
                        # Format recommended bet
                        rec_bet_display = f"${row['RecommendedBet']:,.2f}"
                        session_card = f"""
                        <div class="ph-game-card" style="border-left: 6px solid #1976d2; position:relative;">
                            <div style="position:absolute; top:10px; right:10px; background:#1976d2; color:white; 
                                        border-radius:50%; width:30px; height:30px; display:flex; 
                                        align-items:center; justify-content:center; font-weight:bold;">
                                {i}
                            </div>
                            <div class="ph-game-title">
                                🎰 <a href="{get_game_image_url(row['game_name'], row.get('image_url'))}" 
                                    target="_blank" 
                                    style="color: #2c3e50; text-decoration: none;">
                                    {row['game_name']} 
                                    <span style="font-size:0.8em; color:#7f8c8d;">(view image ↗)</span>
                                </a>
                            </div>
                            <div class="ph-game-score">⭐ Score: {row['Score']*10:.1f}/10</div>
                            <div class="ph-game-detail">
                                <strong>📏 Recommended Bet:</strong> {rec_bet_display}
                            </div>
                            <div class="ph-game-detail">
                                <strong>🗂️ Type:</strong> {row['type']}
                            </div>
                            <div class="ph-game-detail">
                                <strong>💸 Min Bet:</strong> ${row['min_bet']:,.2f}
                            </div>
                            <div class="ph-game-detail">
                                <strong>🧠 Advantage Play:</strong> {map_advantage(int(row['advantage_play_potential']))}
                            </div>
                            <div class="ph-game-detail">
                                <strong>🎲 Volatility:</strong> {vol_label}
                            </div>
                            <div class="ph-game-detail">
                                <strong>🎁 Bonus Frequency:</strong> {map_bonus_freq(row['bonus_frequency'])}
                            </div>
                            <div class="ph-game-detail">
                                <strong>🔢 RTP:</strong> {row['rtp']:.2f}%
                            </div>
                            <div class="ph-game-detail">
                                <strong>💡 Tips:</strong> {row['tips']}
                            </div>
                        </div>
                        """
                        st.markdown(session_card, unsafe_allow_html=True)
                        if st.button(f"🚫 Not Available - {row['game_name']}", 
                                    key=f"not_available_{row['game_name']}_{i}",
                                    use_container_width=True,
                                    type="primary"):
                            blacklist_game(row['game_name'])
                            st.success(f"Replaced {row['game_name']} with a new recommendation")
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.warning("Not enough games match your criteria for all sessions")
                # Extra games suggestions
                extra_games = games[~games.index.isin(recommended_games.index)]
                if not extra_games.empty:
                    st.subheader(f"➕ {len(extra_games)} Additional Recommended Games")
                    st.caption("These games also match your criteria but aren't in your session plan:")
                    st.markdown('<div class="ph-game-grid">', unsafe_allow_html=True)
                    for _, row in extra_games.head(20).iterrows():
                        vol_label = map_volatility(int(row['volatility']))
                        rec_bet_display = f"${row['RecommendedBet']:,.2f}"
                        game_card = f"""
                        <div class="ph-game-card">
                            <div class="ph-game-title">
                                🎰 <a href="{get_game_image_url(row['game_name'], row.get('image_url'))}" 
                                    target="_blank" 
                                    style="color: #2c3e50; text-decoration: none;">
                                    {row['game_name']} 
                                    <span style="font-size:0.8em; color:#7f8c8d;">(view image ↗)</span>
                                </a>
                            </div>
                            <div class="ph-game-score">⭐ Score: {row['Score']*10:.1f}/10</div>
                            <div class="ph-game-detail">
                                <strong>📏 Recommended Bet:</strong> {rec_bet_display}
                            </div>
                            <div class="ph-game-detail">
                                <strong>🗂️ Type:</strong> {row['type']}
                            </div>
                            <div class="ph-game-detail">
                                <strong>💸 Min Bet:</strong> ${row['min_bet']:,.2f}
                            </div>
                            <div class="ph-game-detail">
                                <strong>🧠 Advantage Play:</strong> {map_advantage(int(row['advantage_play_potential']))}
                            </div>
                            <div class="ph-game-detail">
                                <strong>🎲 Volatility:</strong> {vol_label}
                            </div>
                            <div class="ph-game-detail">
                                <strong>🎁 Bonus Frequency:</strong> {map_bonus_freq(row['bonus_frequency'])}
                            </div>
                            <div class="ph-game-detail">
                                <strong>🔢 RTP:</strong> {row['rtp']:.2f}%
                            </div>
                            <div class="ph-game-detail">
                                <strong>💡 Tips:</strong> {row['tips']}
                            </div>
                        </div>
                        """
                        st.markdown(game_card, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("No games match your current filters. Try adjusting your criteria.")
        else:
            st.error("Failed to load game data. Please check the CSV format and column names.")
    with tab2:
        game_df = load_game_data()
        render_session_tracker(game_df, session_bankroll)
    with tab3:
        render_analytics()

    with tab4:
    st.info("Admin tools are protected. Configure ADMIN_PASS in secrets or env. "
            "Requires SUPABASE_SERVICE_ROLE_KEY for upserts.")

    if _is_admin_authenticated():
        show_admin_panel()
    else:
        st.stop()