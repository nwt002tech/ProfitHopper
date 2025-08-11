from __future__ import annotations

import os
from typing import Any, Optional, List
import pandas as pd

# Streamlit only for secrets + optional hints
try:
    import streamlit as st
except Exception:
    st = None  # type: ignore

try:
    from supabase import create_client, Client
except Exception:
    create_client = None
    Client = Any  # type: ignore


# -----------------------------
# Secrets / client
# -----------------------------
def _read_secret(key: str) -> Optional[str]:
    """Read env -> st.secrets root -> st.secrets['general']."""
    if key in os.environ:
        return os.environ.get(key)
    if st is not None and hasattr(st, "secrets"):
        val = st.secrets.get(key)
        if val:
            return val
        gen = st.secrets.get("general", {})
        if isinstance(gen, dict):
            val = gen.get(key)
            if val:
                return val
    return None


def _client() -> Optional["Client"]:
    """Anon client for reads (safe for public tables with RLS)."""
    if create_client is None:
        if st:
            st.error("Supabase client not installed. Make sure 'supabase', 'postgrest', and 'gotrue' are in requirements.")
        return None
    url = _read_secret("SUPABASE_URL") or _read_secret("NEXT_PUBLIC_SUPABASE_URL")
    key = _read_secret("SUPABASE_ANON_KEY") or _read_secret("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not (url and key):
        if st:
            st.error("Missing SUPABASE_URL or SUPABASE_ANON_KEY.")
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        if st:
            st.error(f"Failed to init Supabase client: {e}")
        return None


# -----------------------------
# Utilities
# -----------------------------
def _to_float_or_none(v):
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if s == "" or s.lower() == "nan":
            return None
        return float(s)
    except Exception:
        return None


def _safe_copy_df(df) -> pd.DataFrame:
    """Return a copy if df is a DataFrame; otherwise an empty DataFrame."""
    return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()


# -----------------------------
# Casinos (supports near‑me)
# -----------------------------
CASINO_COLS_SELECT = "id,name,city,state,latitude,longitude,is_active,inserted_at,updated_at"

def _ensure_casino_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Guarantee expected columns exist; normalize lat/lng aliases; coerce coords to float.
    This ensures near‑me filtering always finds numeric 'latitude'/'longitude'.
    """
    df = _safe_copy_df(df)

    # alias normalization
    if "latitude" not in df.columns and "lat" in df.columns:
        df = df.rename(columns={"lat": "latitude"})
    if "longitude" not in df.columns and "lng" in df.columns:
        df = df.rename(columns={"lng": "longitude"})

    expected = ["id", "name", "city", "state", "latitude", "longitude", "is_active", "inserted_at", "updated_at"]
    for col in expected:
        if col not in df.columns:
            if col in ("latitude", "longitude"):
                df[col] = None
            elif col == "is_active":
                df[col] = True
            else:
                df[col] = None

    # coerce coords to float
    df["latitude"]  = [_to_float_or_none(v) for v in df["latitude"]]
    df["longitude"] = [_to_float_or_none(v) for v in df["longitude"]]

    # strings for text fields
    df["name"] = df["name"].astype(str)
    if "city" in df.columns:
        df["city"] = df["city"].astype(str).fillna("")
    if "state" in df.columns:
        df["state"] = df["state"].astype(str).fillna("")

    return df


def get_casinos_full(active_only: bool = True) -> pd.DataFrame:
    """
    Returns a DataFrame with at least:
      id, name, city, state, latitude, longitude, is_active, inserted_at, updated_at
    Never raises on caller; returns a shaped (possibly empty) DataFrame.
    """
    c = _client()
    empty = pd.DataFrame(columns=["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"])
    if c is None:
        return empty
    try:
        res = c.table("casinos").select(CASINO_COLS_SELECT).order("name").execute()
        df = pd.DataFrame(res.data or [])
        df = _ensure_casino_cols(df)
        if active_only and ("is_active" in df.columns):
            df = df[df["is_active"] == True].copy()
        return df.reset_index(drop=True)
    except Exception as e:
        if st:
            st.info(f"[get_casinos_full] fallback: {e}")
        return empty


def get_casinos() -> List[str]:
    """Active casino names only."""
    df = get_casinos_full(active_only=True)
    if df.empty or "name" not in df.columns:
        return []
    return df["name"].dropna().astype(str).tolist()


# -----------------------------
# Games (restores your base loader)
# -----------------------------
_GAMES_COLS_SELECT = (
    "id,name,game_type,type,rtp,volatility,bonus_frequency,min_bet,"
    "advantage_play_potential,is_hidden,is_unavailable,image_url,source_url,"
    "tips,updated_at,score"
)

def _ensure_game_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize game columns & dtypes so the UI logic works."""
    df = _safe_copy_df(df)

    expected = [
        "id","name","type","game_type","rtp","volatility","bonus_frequency","min_bet",
        "advantage_play_potential","is_hidden","is_unavailable","image_url","source_url",
        "tips","updated_at","score"
    ]
    for col in expected:
        if col not in df.columns:
            if col in ("is_hidden","is_unavailable"):
                df[col] = False
            else:
                df[col] = None

    # dtypes
    def _to_float(v):
        try:
            if v is None or (isinstance(v, str) and v.strip() == ""):
                return None
            return float(v)
        except Exception:
            return None

    for col in ("rtp","bonus_frequency","min_bet","score"):
        if col in df.columns:
            df[col] = df[col].map(_to_float)

    for col in ("volatility","advantage_play_potential"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in ("is_hidden","is_unavailable"):
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)

    # strings for text fields
    for col in ("name","type","game_type","image_url","source_url","tips"):
        if col in df.columns:
            df[col] = df[col].astype(str)

    lead = [c for c in expected if c in df.columns]
    rest = [c for c in df.columns if c not in lead]
    return df[lead + rest]


def load_game_data(active_only: bool = True) -> pd.DataFrame:
    """
    Load games from Supabase and normalize columns to match the app’s expectations.
    """
    c = _client()
    if c is None:
        return _ensure_game_cols(pd.DataFrame())
    try:
        res = c.table("games").select(_GAMES_COLS_SELECT).order("name").execute()
        df = pd.DataFrame(res.data or [])
        df = _ensure_game_cols(df)
        if active_only and "is_hidden" in df.columns:
            df = df[df["is_hidden"] == False]
        return df.reset_index(drop=True)
    except Exception as e:
        if st:
            st.info(f"[load_game_data] fallback: {e}")
        return _ensure_game_cols(pd.DataFrame())