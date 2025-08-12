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
        val = st.secrets.get(key)
        if val:
            return val
        gen = st.secrets.get("general", {})
        if isinstance(gen, dict):
            val = gen.get(key)
            if val:
                return val
    return None


def _client() -> Optional['Client']:
    if create_client is None:
        if st:
            st.error("Supabase client not installed. Ensure 'supabase', 'postgrest', 'gotrue' in requirements.")
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


# --- New helper used by nearby filtering (non-breaking) ---
CASINO_COLS_SELECT = "id,name,city,state,latitude,longitude,is_active,inserted_at,updated_at"

def _to_float_or_none(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _ensure_casino_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # alias normalization
    if "latitude" not in df.columns and "lat" in df.columns:
        df = df.rename(columns={"lat": "latitude"})
    if "longitude" not in df.columns and "lng" in df.columns:
        df = df.rename(columns={"lng": "longitude"})
    expected = ["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"]
    for c in expected:
        if c not in df.columns:
            df[c] = None
    df["is_active"] = df.get("is_active", True)
    # numeric coercion
    df["latitude"]  = df["latitude"].map(_to_float_or_none)
    df["longitude"] = df["longitude"].map(_to_float_or_none)
    # strings
    for c in ("name","city","state"):
        if c in df.columns:
            df[c] = df[c].astype(str)
    return df

def get_casinos_full(active_only: bool=True) -> pd.DataFrame:
    c = _client()
    empty = pd.DataFrame(columns=["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"])
    if c is None:
        return empty
    try:
        res = c.table("casinos").select(CASINO_COLS_SELECT).order("name").execute()
        df = pd.DataFrame(res.data or [])
        df = _ensure_casino_cols(df)
        if active_only and "is_active" in df.columns:
            df = df[df["is_active"] == True].copy()
        return df.reset_index(drop=True)
    except Exception as e:
        if st:
            st.info(f"[get_casinos_full] fallback: {e}")
        return empty
