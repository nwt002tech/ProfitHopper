# data_loader_supabase.py — Supabase ONLY (no CSV fallback)

import os, re
import pandas as pd
from typing import Optional

try:
    from supabase import create_client
except Exception as e:
    create_client = None

# --- helpers ---------------------------------------------------------------

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\W+", "_", c.strip()).lower() for c in df.columns]

    # Ensure both name and game_name exist for compatibility
    if "name" not in df.columns and "game_name" in df.columns:
        df["name"] = df["game_name"]
    if "game_name" not in df.columns and "name" in df.columns:
        df["game_name"] = df["name"]

    # Ensure expected fields exist so UI never crashes
    expected = [
        "tips","type","game_type","rtp","volatility","bonus_frequency","min_bet",
        "advantage_play_potential","best_casino_type","bonus_trigger_clues","image_url","source_url"
    ]
    for col in expected:
        if col not in df.columns:
            if col in ("rtp","volatility","bonus_frequency","min_bet","advantage_play_potential"):
                df[col] = None
            else:
                df[col] = ""

    # Derive game_type if missing
    if "game_type" not in df.columns or df["game_type"].eq("").all():
        def norm_type(val: str) -> str:
            s = str(val).lower()
            if "keno" in s:  return "video keno" if "video" in s else "keno"
            if "poker" in s: return "video poker"
            if "slot" in s or "reel" in s: return "slot"
            return "unknown"
        df["game_type"] = df["type"].apply(norm_type)

    return df

def _tip_sanity_filter(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    def refine(row):
        t = str(row.get("tips","") or "").strip()
        g = str(row.get("game_type","")).lower()
        name = str(row.get("game_name", row.get("name",""))).lower()

        if g == "slot":
            if "overlapping pattern" in t.lower() or "card" in t.lower():
                t = ""
            if "bonus frequency" in t.lower():
                t = "High bonus frequency ≈ 1 bonus every 30–40 spins; 50+ spins without a bonus is low — consider switching."
            if "88 fortunes" in name:
                t = ("Use a bet level your bankroll supports; enabling Gold Symbols increases jackpot eligibility "
                     "but also cost. Fu Bat jackpots are random—don’t chase. If 50+ spins pass without bonus, switch.")
        if g in ("video keno","keno"):
            t = ("Use overlapping number clusters across cards so one hit can pay on multiple cards. "
                 "Keep total risk ≤2% of session bankroll per draw; rotate patterns that stay cold for 20–30 draws.")
        if g == "video poker" and (not t or "bonus frequency" in t.lower()):
            t = ("Use the correct strategy card for the exact paytable; prefer full- or near-full-pay. "
                 "Keep one-hand bet ≤2% of session bankroll.")
        return t or "Play within bankroll and follow the strategy shown."
    df["tips"] = df.apply(refine, axis=1)
    return df

def _load_from_supabase() -> pd.DataFrame:
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

    if create_client is None:
        raise RuntimeError("Supabase client not installed. Add 'supabase', 'postgrest', 'gotrue' to requirements.txt.")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY. Set env vars or Streamlit secrets before running.")

    client = create_client(url, key)
    res = client.table("games").select("*").execute()
    data = res.data or []
    df = pd.DataFrame(data)
    if df.empty:
        raise RuntimeError("Supabase query returned 0 rows from table 'games'. Seed data or check RLS/policies.")
    return df

# --- public API ------------------------------------------------------------

def load_game_data() -> pd.DataFrame:
    df = _load_from_supabase()                         # Supabase only
    df = _normalize_columns(df)
    df = _tip_sanity_filter(df)
    return df

# ---- Added: richer casino fetch for nearby filtering ----
def get_casinos_full(active_only: bool = True) -> pd.DataFrame:
    """
    Returns a DataFrame with at least 'name'. If your 'casinos' table has
    city/state/latitude/longitude, those columns are included too.
    Falls back to name-only if fields or table are missing.
    """
    client = _client_readonly()
    if client is None:
        # Fall back to simple names
        names = get_casinos()
        import pandas as _pd
        return _pd.DataFrame({"name": names})
    try:
        cols = ["id","name","city","state","latitude","longitude","is_active"]
        q = client.table("casinos").select(",".join(cols))
        if active_only:
            q = q.eq("is_active", True)
        res = q.order("name").execute()
        import pandas as _pd
        df = _pd.DataFrame(res.data or [])
        if df.empty:
            return _pd.DataFrame({"name": get_casinos()})
        # Ensure name present
        if "name" not in df.columns:
            df["name"] = ""
        return df
    except Exception:
        import pandas as _pd
        return _pd.DataFrame({"name": get_casinos()})
