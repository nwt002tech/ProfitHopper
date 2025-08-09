import math
from typing import Any, Dict, List, Optional

import streamlit as st

from games_data import GAMES   # <-- in-memory dataset (no CSVs)

# -----------------------------
# Page / Styles
# -----------------------------
st.set_page_config(page_title="🎯 Profit Hopper", layout="wide")

MOBILE_CSS = """
<style>
/* Mobile-friendly container widths */
.block-container {padding-top: 0.75rem; padding-bottom: 4rem; max-width: 900px;}
/* Compact summary row */
.ph-summary {display: grid; grid-template-columns: 1fr 1fr; gap: .5rem; margin: .75rem 0;}
@media (min-width: 640px) { .ph-summary { grid-template-columns: repeat(4, 1fr); } }
.summary-card {background: #0e1117; border: 1px solid #222; border-radius: 10px; padding: .6rem .75rem; display:flex; align-items:center; gap:.6rem}
.summary-icon {font-size: 1.15rem; line-height:1;}
.summary-label {font-size:.80rem; opacity:.8}
.summary-value {font-weight:700}

/* Game list */
.game-card {border:1px solid #222; border-radius:12px; padding:.8rem; margin-bottom:.6rem; background:#0e1117}
.game-title {font-size:1rem; font-weight:700; margin-bottom:.2rem}
.game-meta {font-size:.85rem; opacity:.9; margin-bottom:.4rem}
.game-actions {margin-top:.4rem; display:flex; gap:.6rem; flex-wrap:wrap}
.game-link a {text-decoration:none}

/* Small chips */
.chip {border:1px solid #2a2a2a; padding:.18rem .45rem; border-radius:999px; font-size:.75rem; opacity:.95}
.stop-loss {color:#ff6b6b; font-weight:700}

/* Inputs compact */
.stSelectbox label, .stNumberInput label {font-size:.85rem}
</style>
"""
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

# -----------------------------
# Helpers
# -----------------------------
def safe_get(d: Dict[str, Any], *keys: str, default: Optional[Any] = None) -> Any:
    """Return the first present value for any of the given keys (case-insensitive)."""
    if not d:
        return default
    # build lowercase map once
    if "_lc" not in d:
        d["_lc"] = {k.lower(): v for k, v in d.items()}
    for k in keys:
        if k is None:
            continue
        v = d["_lc"].get(k.lower())
        if v is not None and v != "":
            return v
    return default

def normalized_game(row: Dict[str, Any]) -> Dict[str, Any]:
    """Standardize keys so the UI/logic never KeyErrors."""
    return {
        "name": safe_get(row, "game_name", "game_title", "name", "title", default="Unknown Game"),
        "type": safe_get(row, "type", "category", default="Slot"),
        "rtp": float(safe_get(row, "rtp", "RTP", default=0) or 0),
        "min_bet": float(safe_get(row, "min_bet", "minbet", "min", default=0) or 0),
        "volatility": safe_get(row, "volatility", "risk", default="Medium"),
        "denoms": safe_get(row, "denoms", "denominations", "denom_options", default=["$0.01"]),
        "image_url": safe_get(row, "image_url", "image", default=None),
        "tips": safe_get(row, "tips", "notes", default=""),
        "variant": safe_get(row, "variant", "version", default=None),
        "adv": safe_get(row, "advantage_play_potential", "ap_potential", default=None),
    }

def get_game_image_url(name: str, image_url: Optional[str]) -> str:
    """Return an image URL or a neutral placeholder that won't break."""
    if image_url and isinstance(image_url, str) and image_url.strip():
        return image_url.strip()
    # neutral placeholder
    safe_text = (name or "Game").replace('"', "").replace("'", "")
    return f"https://via.placeholder.com/800x450?text={safe_text}"

def score_game(g: Dict[str, Any], session_bankroll: float, max_bet: float, stop_loss: float) -> float:
    """Very simple scoring: prioritize higher RTP, lower volatility, and playable min bet."""
    # Base by RTP
    rtp_component = g["rtp"] / 100.0  # 0.85 .. 1.02 etc.
    # Volatility penalty
    vol = (g["volatility"] or "").lower()
    vol_pen = {"low": 0.0, "medium": -0.05, "high": -0.12}.get(vol, -0.03)
    # Min bet feasibility
    min_bet = float(g["min_bet"] or 0)
    playable = 1.0 if (min_bet > 0 and min_bet <= max_bet and min_bet <= session_bankroll) else 0.5
    return rtp_component + vol_pen + 0.15 * playable

def calc_session_plan(total_bankroll: float, num_sessions: int) -> Dict[str, float]:
    """Derive session bankroll, max bet, stop loss using conservative defaults."""
    num_sessions = max(1, int(num_sessions))
    session_bankroll = max(5.0, total_bankroll / num_sessions)

    # Max bet ~ 5% of session bankroll (ensures multiple spins / hands)
    max_bet = round(max(0.2, session_bankroll * 0.05), 2)

    # Stop-loss ~ 60% of session bankroll (but never equal to session bankroll)
    stop_loss = round(max(2.0, session_bankroll * 0.60), 2)
    if abs(stop_loss - session_bankroll) < 0.01:
        stop_loss -= 1.0  # ensure not equal

    return {
        "session_bankroll": round(session_bankroll, 2),
        "max_bet": round(max_bet, 2),
        "stop_loss": round(stop_loss, 2),
    }

def recommend_games(total_bankroll: float, num_sessions: int, top_n: int = 20) -> List[Dict[str, Any]]:
    plan = calc_session_plan(total_bankroll, num_sessions)
    s_bank = plan["session_bankroll"]
    m_bet = plan["max_bet"]
    s_loss = plan["stop_loss"]

    normalized = [normalized_game(g) for g in GAMES]

    # Filter: playable within limits
    playable = []
    for g in normalized:
        if g["min_bet"] and g["min_bet"] <= m_bet and g["min_bet"] <= s_bank:
            playable.append(g)
        else:
            # keep borderline options with smaller weight so list isn't tiny
            borderline = dict(g)
            playable.append(borderline)

    # Score and sort
    for g in playable:
        g["_score"] = score_game(g, s_bank, m_bet, s_loss)
    playable.sort(key=lambda x: x["_score"], reverse=True)

    # Attach plan numbers for display
    for g in playable:
        g["_session_bankroll"] = s_bank
        g["_max_bet"] = m_bet
        g["_stop_loss"] = s_loss

    return playable[:top_n], plan

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("🎛️ Session Settings")
total_bankroll = st.sidebar.number_input("💰 Total Trip Bankroll", min_value=10.0, value=100.0, step=5.0)
num_sessions = st.sidebar.number_input("🎯 Number of Sessions (games to play)", min_value=1, value=5, step=1)
list_size = st.sidebar.slider("📋 How many games to list", 5, 50, 20)

# -----------------------------
# Compute Plan + Recommendations
# -----------------------------
recs, plan = recommend_games(total_bankroll, num_sessions, top_n=list_size)

# -----------------------------
# Header + Summary
# -----------------------------
st.markdown("## 🐸 Profit Hopper — Game Plan")

col1, col2 = st.columns([1, 1], gap="small")
with col1:
    st.write("Based on your bankroll and target session count, here’s a compact plan and ranked games to build profit steadily.")

# Compact summary row (mobile)
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

# -----------------------------
# Recommendations List
# -----------------------------
st.markdown("### 🧠 Recommended Games (best chances to build bankroll)")

if not recs:
    st.info("No playable games matched your constraints. Try increasing sessions (smaller session bankroll), or lowering the min bet.")
else:
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