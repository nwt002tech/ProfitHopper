import os
os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'poll'

import streamlit as st
import numpy as np
from ui_templates import get_css, get_header
from trip_manager import initialize_trip_state, render_sidebar, render_trip_summary
from session_manager import render_session_tracker, persist_session_update
from data_loader_supabase import load_game_data
from analytics import render_analytics
from utils import map_volatility, map_advantage, map_bonus_freq, get_game_image_url
from admin_panel import show_admin_panel

st.set_page_config(layout="wide", initial_sidebar_state="expanded", 
                  page_title="Profit Hopper Casino Manager")

initialize_trip_state()

st.markdown(get_css(), unsafe_allow_html=True)
st.markdown(get_header(), unsafe_allow_html=True)

render_sidebar()

border_colors = {
    "Conservative": "#28a745",
    "Moderate": "#17a2b8", 
    "Standard": "#ffc107",
    "Aggressive": "#dc3545"
}

def bankroll_sizing(session_bankroll, style, volatility, win_streak):
    base = {
        "Conservative": 0.004,
        "Moderate": 0.006,
        "Standard": 0.008,
        "Aggressive": 0.010
    }[style]
    # volatility adjustment (lower bet for higher vol)
    vol_adj = {1:1.3, 2:1.1, 3:1.0, 4:0.84, 5:0.7}.get(int(volatility or 3), 1.0)
    # slight increase if on a win streak
    streak_adj = 1.0 + min(max((win_streak or 0), 0), 5) * 0.02
    bet = session_bankroll * base * vol_adj * streak_adj
    return max(0.01, round(bet, 2))

def compute_score(row, bankroll):
    rtp = float(row.get("rtp") or 0)
    adv = float(row.get("advantage_play_potential") or 0)
    vol = float(row.get("volatility") or 0)
    min_bet = float(row.get("min_bet") or 0)
    # normalize
    rtp_n = max(0.0, min(1.0, (rtp - 85.0) / (99.9 - 85.0))) if rtp else 0.0
    adv_n = max(0.0, min(1.0, adv / 5.0)) if adv else 0.0
    vol_pen = max(0.0, min(1.0, (5.0 - vol) / 5.0)) if vol else 0.5
    # penalize high min_bet vs bankroll
    ratio = (min_bet / bankroll) if bankroll and min_bet else 0.0
    min_pen = 1.0 - max(0.0, ratio - 0.03) * 6.0
    min_pen = max(0.0, min(1.0, min_pen))
    raw = (0.45 * rtp_n) + (0.35 * adv_n) + (0.20 * vol_pen)
    return round(raw * min_pen * 100.0, 2)

# ================== Load game data (Supabase ONLY) ==================
try:
    game_df = load_game_data()
except Exception as e:
    st.error(f"Error loading game data: {e}")
    st.stop()

# Ensure 'game_name' exists and filter hidden/unavailable
if 'game_name' not in game_df.columns and 'name' in game_df.columns:
    game_df['game_name'] = game_df['name']
else:
    if 'name' in game_df.columns and 'game_name' in game_df.columns:
        game_df['game_name'] = game_df['game_name'].fillna(game_df['name'])

if 'is_hidden' in game_df.columns:
    game_df = game_df[~game_df['is_hidden']]
if 'is_unavailable' in game_df.columns:
    game_df = game_df[~game_df['is_unavailable']]

# ================== Controls ==================
colA, colB, colC, colD = st.columns([1.2, 1, 1, 1])
with colA:
    session_bankroll = st.number_input("Session Bankroll ($)", min_value=20.0, value=200.0, step=10.0)
with colB:
    style = st.selectbox("Style", ["Conservative","Moderate","Standard","Aggressive"], index=2)
with colC:
    win_streak = st.number_input("Recent Win Streak (sessions)", min_value=0, value=0, step=1)
with colD:
    type_filter = st.multiselect("Game Types", ["slot","video keno","video poker","keno","table"], default=[])

# Apply type filter
if type_filter:
    game_df = game_df[game_df["game_type"].isin([t.lower() for t in type_filter])]

# Compute rec bet and score
df = game_df.copy()
df["RecommendedBet"] = df.apply(
    lambda r: bankroll_sizing(session_bankroll, style, r.get("volatility"), win_streak), axis=1
)
df["Score"] = df.apply(lambda r: compute_score(r, session_bankroll), axis=1)
df = df.sort_values(["Score","rtp","advantage_play_potential"], ascending=[False, False, False]).reset_index(drop=True)

# ================== Tabs ==================
tab1, tab2, tab3, tab4 = st.tabs(["Trip", "Games", "Analytics", "Admin"])

with tab1:
    render_trip_summary()

with tab2:
    st.subheader("🎰 Recommended Games")
    if df.empty:
        st.info("No games matched your filters. Try increasing bankroll or clearing filters.")
    else:
        # top table
        cols = ["game_name","game_type","rtp","volatility","min_bet","advantage_play_potential","RecommendedBet","tips"]
        show_cols = [c for c in cols if c in df.columns]
        table = df[show_cols].rename(columns={
            "game_name":"Game",
            "game_type":"Type",
            "rtp":"RTP %",
            "volatility":"Vol",
            "min_bet":"Min Bet",
            "advantage_play_potential":"Advantage",
            "RecommendedBet":"Rec Bet",
            "tips":"Tips"
        })
        st.dataframe(table, use_container_width=True, height=460)

        # top picks as cards
        st.markdown("---")
        st.subheader("Top Picks")
        for _, row in df.head(6).iterrows():
            name_display = row.get('game_name', row.get('name'))
            img_url = get_game_image_url(name_display, row.get('image_url'))
            vol_lbl = map_volatility(row.get("volatility"))
            rtp_txt = f"{row.get('rtp')}%" if row.get("rtp") else "—"
            tips_txt = str(row.get("tips") or "")

            st.markdown(
                f"""
<div style="border:1px solid #eee;border-radius:10px;padding:12px;margin-bottom:12px">
  <div style="display:flex;gap:12px;align-items:center;">
    <div style="width:80px;height:80px;overflow:hidden;border-radius:8px;border:1px solid #ddd;">
      <img src="{img_url}" style="width:100%;height:100%;object-fit:cover" />
    </div>
    <div style="flex:1">
      <div style="font-weight:700;font-size:1.05rem">🎰 <a href="{img_url}" target="_blank" style="text-decoration:none">{name_display}</a></div>
      <div style="color:#666">Type: {row.get('game_type','—').title()} • RTP: {rtp_txt} • Volatility: {vol_lbl}</div>
      <div style="margin-top:6px"><b>Recommended bet:</b> ${row['RecommendedBet']:,.2f}</div>
      <div style="color:#444;margin-top:6px">{tips_txt}</div>
    </div>
  </div>
</div>
                """,
                unsafe_allow_html=True
            )

with tab3:
    render_analytics()

with tab4:
    ADMIN_ENABLED = os.environ.get("ADMIN_ENABLED", "0") == "1"
    if not ADMIN_ENABLED:
        st.info("Admin is disabled. Set ADMIN_ENABLED=1 in secrets/env to enable.")
    else:
        ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
        pw = st.text_input("Admin password", type="password")
        if ADMIN_PASSWORD and pw != ADMIN_PASSWORD:
            st.error("Invalid password.")
        else:
            st.success("Admin unlocked.")
            show_admin_panel()

# footer
st.caption("Profit Hopper — bankroll‑first recommendations. Supabase‑backed. No CSV fallback.")