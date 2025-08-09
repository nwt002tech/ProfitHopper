import os
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from supabase_client import get_supabase, fetch_games  # Supabase only
from admin_panel import show_admin_panel  # NEW: admin tab

# ──────────────────────────────────────────────────────────────────────────────
# Page config / Styles
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="🎯 Profit Hopper", layout="wide")

MOBILE_CSS = """
<style>
.block-container {padding-top: 0.75rem; padding-bottom: 4rem; max-width: 900px;}
.ph-summary {display: grid; grid-template-columns: 1fr 1fr; gap: .5rem; margin: .75rem 0;}
@media (min-width: 640px) { .ph-summary { grid-template-columns: repeat(4, 1fr); } }
.summary-card {background: #0e1117; border: 1px solid #222; border-radius: 10px; padding: .6rem .75rem; display:flex; align-items:center; gap:.6rem}
.summary-icon {font-size: 1.15rem; line-height:1;}
.summary-label {font-size:.80rem; opacity:.8}
.summary-value {font-weight:700}
.game-card {border:1px solid #222; border-radius:12px; padding:.8rem; margin-bottom:.6rem; background:#0e1117}
.game-title {font-size:1rem; font-weight:700; margin-bottom:.2rem}
.game-meta {font-size:.85rem; opacity:.9; margin-bottom:.4rem}
.game-actions {margin-top:.4rem; display:flex; gap:.6rem; flex-wrap:wrap}
.game-link a {text-decoration:none}
.chip {border:1px solid #2a2a2a; padding:.18rem .45rem; border-radius:999px; font-size:.75rem; opacity:.95}
.stop-loss {color:#ff6b6b; font-weight:700}
.stSelectbox label, .stNumberInput label {font-size:.85rem}
</style>
"""
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def safe_get(d: Dict[str, Any], *keys: str, default: Optional[Any] = None) -> Any:
    """Return first present value for any of the given keys (case-insensitive)."""
    if not d:
        return default
    if "_lc" not in d:
        d["_lc"] = {str(k).lower(): v for k, v in d.items()}
    for k in keys:
        v = d["_lc"].get(str(k).lower())
        if v not in (None, ""):
            return v
    return default

def normalized_game(row: Dict[str, Any]) -> Dict[str, Any]:
    """Standardize keys so the UI/logic never KeyErrors."""
    return {
        "name": safe_get(row, "game_name", "game_title", "name", "title", default="Unknown Game"),
        "type": safe_get(row, "type", "category", default="Slot"),
        "rtp": float(safe_get(row, "rtp", "RTP", default=0) or 0),
        "min_bet": float(safe_get(row, "min_bet", "minbet", "min", "Min_Bet", "MinBet", default=0) or 0),
        "volatility": safe_get(row, "volatility", "risk", default="Medium"),
        "denoms": safe_get(row, "denoms", "denominations", "denom_options", "Denoms", "Denominations", default=["$0.01"]),
        "image_url": safe_get(row, "image_url", "image", "Image_URL", "Image", default=None),
        "tips": safe_get(row, "tips", "notes", "Notes", default=""),
        "variant": safe_get(row, "variant", "version", "Version", default=None),
        "adv": safe_get(row, "advantage_play_potential", "ap_potential", "Advantage_Play_Potential", default=None),
    }

def get_game_image_url(name: str, image_url: Optional[str]) -> str:
    if image_url and isinstance(image_url, str) and image_url.strip():
        return image_url.strip()
    # neutral placeholder (no external deps)
    safe_text = (name or "Game").replace('"', "").replace("'", "")
    return f"https://via.placeholder.com/800x450?text={safe_text}"

def score_game(g: Dict[str, Any], session_bankroll: float, max_bet: float, stop_loss: float) -> float:
    """Simple scoring using RTP, volatility penalty, and feasibility of min bet."""
    rtp_component = g["rtp"] / 100.0
    vol = (g["volatility"] or "").lower()
    vol_pen = {"low": 0.0, "medium": -0.05, "high": -0.12}.get(vol, -0.03)
    min_bet = float(g["min_bet"] or 0)
    playable = 1.0 if (min_bet > 0 and min_bet <= max_bet and min_bet <= session_bankroll) else 0.5
    return rtp_component + vol_pen + 0.15 * playable

def calc_session_plan(total_bankroll: float, num_sessions: int) -> Dict[str, float]:
    num_sessions = max(1, int(num_sessions))
    session_bankroll = max(5.0, total_bankroll / num_sessions)
    # Max bet ~ 5% of session bankroll (ensures multiple spins/hands)
    max_bet = round(max(0.2, session_bankroll * 0.05), 2)
    # Stop-loss ~ 60% of session bankroll, never equal to the bankroll
    stop_loss = round(max(2.0, session_bankroll * 0.60), 2)
    if abs(stop_loss - session_bankroll) < 0.01:
        stop_loss -= 1.0
    return {
        "session_bankroll": round(session_bankroll, 2),
        "max_bet": round(max_bet, 2),
        "stop_loss": round(stop_loss, 2),
    }

def recommend_games(games: List[Dict[str, Any]], total_bankroll: float, num_sessions: int, top_n: int = 20) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    plan = calc_session_plan(total_bankroll, num_sessions)
    s_bank = plan["session_bankroll"]
    m_bet = plan["max_bet"]
    s_loss = plan["stop_loss"]

    normalized = [normalized_game(g) for g in games]

    # Keep all, but naturally favor playable ones
    for g in normalized:
        g["_score"] = score_game(g, s_bank, m_bet, s_loss)
        g["_session_bankroll"] = s_bank
        g["_max_bet"] = m_bet
        g["_stop_loss"] = s_loss

    normalized.sort(key=lambda x: x["_score"], reverse=True)
    return normalized[:top_n], plan

# ──────────────────────────────────────────────────────────────────────────────
# Admin auth helper
# ──────────────────────────────────────────────────────────────────────────────
def _is_admin() -> bool:
    if st.session_state.get("_ph_is_admin") is True:
        return True
    required = (
        st.secrets.get("admin_password")
        or os.environ.get("ADMIN_PASSWORD")
        or ""
    )
    if not required:
        st.info("Admin password not set. Add `admin_password` in Streamlit secrets or `ADMIN_PASSWORD` env var to enable the Admin tab.")
        return False
    pw = st.session_state.get("_ph_admin_pw") or ""
    if not pw:
        return False
    ok = str(pw) == str(required)
    if ok:
        st.session_state["_ph_is_admin"] = True
    return ok

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar / Inputs
# ──────────────────────────────────────────────────────────────────────────────
st.sidebar.header("🎛️ Session Settings")
total_bankroll = st.sidebar.number_input("💰 Total Trip Bankroll", min_value=10.0, value=100.0, step=5.0)
num_sessions = st.sidebar.number_input("🎯 Number of Sessions (games to play)", min_value=1, value=5, step=1)
list_size = st.sidebar.slider("📋 How many games to list", 5, 50, 20)

# Admin password UI in sidebar
with st.sidebar.expander("🔐 Admin Login"):
    st.session_state["_ph_admin_pw"] = st.text_input("Admin password", type="password", value=st.session_state.get("_ph_admin_pw", ""))

# ──────────────────────────────────────────────────────────────────────────────
# Data (Supabase only) + Recommendations
# ──────────────────────────────────────────────────────────────────────────────
client = get_supabase()
if client is None:
    st.error("❌ Supabase credentials not found. Add `SUPABASE_URL` and `SUPABASE_ANON_KEY` to Streamlit secrets or env vars.")
    st.stop()

# You can set the table name in Streamlit secrets: st.secrets["supabase"]["games_table"]
GAMES_TABLE = st.secrets.get("supabase", {}).get("games_table", "games")

games, fetch_err = fetch_games(client, GAMES_TABLE)
if fetch_err:
    st.error(f"❌ Failed to fetch games from Supabase table `{GAMES_TABLE}`: {fetch_err}")
    st.stop()
if not games:
    st.warning(f"ℹ️ Supabase returned 0 games from `{GAMES_TABLE}`. Add rows and refresh.")
    st.stop()

recs, plan = recommend_games(games, total_bankroll, num_sessions, top_n=list_size)

# ──────────────────────────────────────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────────────────────────────────────
tab_plan, tab_admin = st.tabs(["🧭 Game Plan", "🛠️ Admin"])

with tab_plan:
    st.markdown("## 🐸 Profit Hopper — Game Plan")
    st.write("Based on your bankroll and target session count, here’s a compact plan and ranked games to build profit steadily.")

    st.markdown(
        f"""
    <div class="ph-summary">
      <div class="summary-card"><div class="summary-icon">💵</div><div><div class="summary-label">Session</div><div class="summary-value">${plan['session_bankroll']:.2f}</div></div></div>
      <div class="summary-card"><div class="summary-icon">🪙</div><div><div class="summary-label">Unit</div><div class="summary-value">${max(.20, round(plan['max_bet']/5, 2)):.2f}</div></div></div>
      <div class="summary-card"><div class="summary-icon">⬆️</div><div><div class="summary-label">Max Bet</div><div class="summary-value">${plan['max_bet']:.2f}</div></div></div>
      <div class="summary-card"><div class="summary-icon">🛑</div><div><div class="summary-label">Stop Loss</div><div class="summary-value stop-loss">${plan['stop_loss']:.2f}</div></div></div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🧠 Recommended Games (best chances to build bankroll)")
    for g in recs:
        name = g.get("name") or "Unknown Game"
        gtype = g.get("type") or "Slot"
        rtp = g.get("rtp") or 0
        vol = g.get("volatility") or "Medium"
        variant = g.get("variant")
        tips = g.get("tips") or ""
        min_bet = g.get("min_bet") or 0.0
        img = get_game_image_url(name, g.get("image_url"))

        meta_bits = [f"🎰 {gtype}", f"💵 Min Bet: ${min_bet:.2f}", f"📈 RTP: {rtp:.2f}%"]
        if vol:
            meta_bits.append(f"⚖️ Vol: {vol.capitalize()}")
        if variant:
            meta_bits.append(f"🧩 {variant}")
        meta_line = " | ".join(meta_bits)

        st.markdown('<div class="game-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="game-title">{name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="game-meta">{meta_line}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
    <div class="game-actions">
      <span class="chip">🎯 Session: ${g['_session_bankroll']:.2f}</span>
      <span class="chip">⬆️ Max Bet: ${g['_max_bet']:.2f}</span>
      <span class="chip">🛑 Stop: ${g['_stop_loss']:.2f}</span>
      <span class="chip game-link">🖼️ <a href="{img}" target="_blank">View</a></span>
    </div>
    """,
            unsafe_allow_html=True,
        )
        if tips:
            st.markdown(f"**💡 Tips:** {tips}")
        st.markdown("</div>", unsafe_allow_html=True)

with tab_admin:
    st.markdown("## 🛠️ Admin")
    if _is_admin():
        show_admin_panel()
    else:
        st.warning("Enter the Admin password in the sidebar to access this tab.")