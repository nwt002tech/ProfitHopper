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
    """Anon client for reads."""
    if create_client is None:
        if st:
            st.error("Supabase client not installed. Add 'supabase', 'postgrest', 'gotrue' to requirements.txt.")
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


def _ensure_casino_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee expected columns exist; normalize lat/lng aliases; coerce coords to float."""
    df = (df or pd.DataFrame()).copy()

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
    df["latitude"]  = [ _to_float_or_none(v) for v in df["latitude"] ]
    df["longitude"] = [ _to_float_or_none(v) for v in df["longitude"] ]

    # strings for name/city/state
    df["name"]  = df["name"].astype(str)
    if "city" in df.columns:  df["city"]  = df["city"].astype(str).fillna("")
    if "state" in df.columns: df["state"] = df["state"].astype(str).fillna("")

    return df


CASINO_COLS_SELECT = "id,name,city,state,latitude,longitude,is_active,inserted_at,updated_at"

def get_casinos_full(active_only: bool = True) -> pd.DataFrame:
    """
    Returns a DataFrame with at least:
      id, name, city, state, latitude, longitude, is_active, inserted_at, updated_at
    Never raises on caller; returns a shaped (possibly empty) DataFrame.
    """
    c = _client()
    if c is None:
        return pd.DataFrame(columns=["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"])
    try:
        res = c.table("casinos").select(CASINO_COLS_SELECT).order("name").execute()
        df = pd.DataFrame(res.data or [])
        df = _ensure_casino_cols(df)
        if active_only and ("is_active" in df.columns):
            df = df[df["is_active"] == True].copy()
        return df.reset_index(drop=True)
    except Exception as e:
        # Never return a boolean-evaluable DataFrame here (no if df: etc.)
        if st:
            st.info(f"[get_casinos_full] fallback: {e}")
        return pd.DataFrame(columns=["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"])


def get_casinos() -> List[str]:
    """Back‑compatible helper: active casino names only."""
    df = get_casinos_full(active_only=True)
    if df.empty or "name" not in df.columns:
        return []
    return df["name"].dropna().astype(str).tolist()