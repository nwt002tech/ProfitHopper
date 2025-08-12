from __future__ import annotations
import os
from typing import Any, Optional, List
import pandas as pd

try:
    import streamlit as st
except Exception:
    st = None  # type: ignore

try:
    from supabase import create_client, Client
except Exception:
    create_client = None
    Client = Any  # type: ignore


def _read_secret(key: str) -> Optional[str]:
    if key in os.environ:
        return os.environ.get(key)
    if st is not None and hasattr(st, "secrets"):
        v = st.secrets.get(key)
        if v:
            return v
        gen = st.secrets.get("general", {})
        if isinstance(gen, dict):
            v = gen.get(key)
            if v:
                return v
    return None

def _client() -> Optional["Client"]:
    if create_client is None:
        if st: st.error("Supabase client not installed.")
        return None
    url = _read_secret("SUPABASE_URL") or _read_secret("NEXT_PUBLIC_SUPABASE_URL")
    key = _read_secret("SUPABASE_ANON_KEY") or _read_secret("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not (url and key):
        if st: st.error("Missing SUPABASE_URL or SUPABASE_ANON_KEY.")
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        if st: st.error(f"Failed to init Supabase client: {e}")
        return None

def _safe_copy_df(df) -> pd.DataFrame:
    return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()

def _to_float_or_none(v):
    try:
        if v is None: return None
        if isinstance(v, (int, float)): return float(v)
        s = str(v).strip()
        if not s or s.lower() == "nan": return None
        return float(s)
    except Exception:
        return None


# -------- Casinos --------
CASINO_COLS_SELECT = "id,name,city,state,latitude,longitude,is_active,inserted_at,updated_at"

def _ensure_casino_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = _safe_copy_df(df)
    if "latitude" not in df.columns and "lat" in df.columns:
        df = df.rename(columns={"lat": "latitude"})
    if "longitude" not in df.columns and "lng" in df.columns:
        df = df.rename(columns={"lng": "longitude"})
    expected = ["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"]
    for col in expected:
        if col not in df.columns:
            df[col] = None if col not in ("is_active",) else True
    df["latitude"]  = [_to_float_or_none(v) for v in df["latitude"]]
    df["longitude"] = [_to_float_or_none(v) for v in df["longitude"]]
    df["name"] = df["name"].astype(str)
    if "city" in df.columns: df["city"] = df["city"].astype(str).fillna("")
    if "state" in df.columns: df["state"] = df["state"].astype(str).fillna("")
    return df

def get_casinos_full(active_only: bool = True) -> pd.DataFrame:
    c = _client()
    empty = pd.DataFrame(columns=["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"])
    if c is None: return empty
    try:
        res = c.table("casinos").select(CASINO_COLS_SELECT).order("name").execute()
        df = pd.DataFrame(res.data or [])
        df = _ensure_casino_cols(df)
        if active_only and ("is_active" in df.columns):
            df = df[df["is_active"] == True].copy()
        return df.reset_index(drop=True)
    except Exception as e:
        if st: st.info(f"[get_casinos_full] fallback: {e}")
        return empty

def get_casinos() -> List[str]:
    df = get_casinos_full(active_only=True)
    if df.empty or "name" not in df.columns:
        return []
    return df["name"].dropna().astype(str).tolist()


# -------- Games --------
_GAMES_COLS_SELECT = (
    "id,name,game_type,type,rtp,volatility,bonus_frequency,min_bet,"
    "advantage_play_potential,is_hidden,is_unavailable,image_url,source_url,"
    "tips,updated_at,score"
)

def _ensure_game_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = _safe_copy_df(df)
    expected = [
        "id","name","type","game_type","rtp","volatility","bonus_frequency","min_bet",
        "advantage_play_potential","is_hidden","is_unavailable","image_url","source_url",
        "tips","updated_at","score"
    ]
    for col in expected:
        if col not in df.columns:
            df[col] = False if col in ("is_hidden","is_unavailable") else None
    def _to_float(v):
        try:
            if v is None or (isinstance(v, str) and not v.strip()):
                return None
            return float(v)
        except Exception:
            return None
    for col in ("rtp","bonus_frequency","min_bet","score"):
        if col in df.columns: df[col] = df[col].map(_to_float)
    for col in ("volatility","advantage_play_potential"):
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ("is_hidden","is_unavailable"):
        if col in df.columns: df[col] = df[col].fillna(False).astype(bool)
    for col in ("name","type","game_type","image_url","source_url","tips"):
        if col in df.columns: df[col] = df[col].astype(str)
    if "game_name" not in df.columns and "name" in df.columns:
        df["game_name"] = df["name"].astype(str)
    lead = [c for c in expected if c in df.columns]
    rest = [c for c in df.columns if c not in lead]
    return df[lead + rest]

def load_game_data(active_only: bool = True) -> pd.DataFrame:
    c = _client()
    if c is None:
        return _ensure_game_cols(pd.DataFrame())
    try:
        res = c.table("games").select(_GAMES_COLS_SELECT).order("name").execute()
        df = pd.DataFrame(res.data or [])
        df = _ensure_game_cols(df)
        if active_only and "is_hidden" in df.columns:
            df = df[df["is_hidden"] == False]
        # enforce A→Z by name at the end (UI consistency)
        if "name" in df.columns:
            df = df.sort_values("name", kind="mergesort").reset_index(drop=True)
        return df
    except Exception as e:
        if st: st.info(f"[load_game_data] fallback: {e}")
        return _ensure_game_cols(pd.DataFrame())