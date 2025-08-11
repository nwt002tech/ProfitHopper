from __future__ import annotations
import os
import pandas as pd
import streamlit as st
from supabase import create_client

REQUIRED_GAME_COLS = [
    "id","name","type","game_type","rtp","volatility","bonus_frequency","min_bet",
    "advantage_play_potential","best_casino_type","bonus_trigger_clues","tips",
    "image_url","source_url","is_hidden","is_unavailable"
]

def _client_readonly():
    url = os.environ.get("SUPABASE_URL") or (st.secrets.get("SUPABASE_URL") if hasattr(st, "secrets") else None)
    if not url and hasattr(st, "secrets") and "general" in st.secrets:
        url = st.secrets["general"].get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY") or (st.secrets.get("SUPABASE_ANON_KEY") if hasattr(st, "secrets") else None)
    if not key and hasattr(st, "secrets") and "general" in st.secrets:
        key = st.secrets["general"].get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise EnvironmentError("Missing SUPABASE_URL / SUPABASE_ANON_KEY for read access")
    return create_client(url, key)

@st.cache_data(ttl=300)
def get_casinos():
    """Return list of casino names from public.casinos (active only).
    Falls back to a small default set if the table doesn't exist or is empty.
    """
    try:
        client = _client_readonly()
    except Exception:
        return [
            "L’Auberge Lake Charles",
            "Coushatta Casino Resort",
            "Golden Nugget Lake Charles",
            "Horseshoe Bossier City",
            "Winstar World Casino",
            "Choctaw Durant",
            "Other..."
        ]
    try:
        res = client.table("casinos").select("name").eq("is_active", True).order("name").execute()
        names = [r.get("name") for r in (res.data or []) if r.get("name")]
        if not names:
            raise ValueError("No casinos found")
        return names + ["Other..."]
    except Exception:
        return [
            "L’Auberge Lake Charles",
            "Coushatta Casino Resort",
            "Golden Nugget Lake Charles",
            "Horseshoe Bossier City",
            "Winstar World Casino",
            "Choctaw Durant",
            "Other..."
        ]

def _norm_games(df: pd.DataFrame) -> pd.DataFrame:
    if "name" in df.columns and "game_name" not in df.columns:
        df = df.rename(columns={"name":"game_name"})
    for col in REQUIRED_GAME_COLS:
        if col not in df.columns:
            if col in ("is_hidden","is_unavailable"):
                df[col] = False
            else:
                df[col] = None
    for c in ["rtp","bonus_frequency","min_bet"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["volatility","advantage_play_potential"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    df["is_hidden"] = df["is_hidden"].astype(bool)
    df["is_unavailable"] = df["is_unavailable"].astype(bool)
    return df

def _fetch_availability(client, current_casino: str) -> pd.DataFrame:
    try:
        if not current_casino:
            return pd.DataFrame()
        res = client.table("game_availability").select("*").ilike("casino", current_casino).execute()
        rows = res.data or []
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        if "game_id" not in df.columns:
            return pd.DataFrame()
        if "is_unavailable" not in df.columns:
            df["is_unavailable"] = False
        df = df[["game_id","casino","is_unavailable"]].rename(columns={"is_unavailable":"unavailable_here"})
        df["unavailable_here"] = df["unavailable_here"].astype(bool)
        return df
    except Exception:
        return pd.DataFrame()

def load_game_data(current_casino: str | None = None) -> pd.DataFrame:
    client = _client_readonly()
    res = client.table("games").select("*").execute()
    data = res.data or []
    games = pd.DataFrame(data)
    if games.empty:
        return games
    games = _norm_games(games)

    if current_casino:
        avail = _fetch_availability(client, current_casino)
        if not avail.empty:
            games = games.merge(avail, how="left", left_on="id", right_on="game_id")
            games["unavailable_here"] = games["unavailable_here"].fillna(False).astype(bool)
        else:
            games["unavailable_here"] = False
    else:
        games["unavailable_here"] = False

    if "type" not in games.columns and "game_type" in games.columns:
        games["type"] = games["game_type"]

    return games