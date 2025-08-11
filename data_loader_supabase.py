from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Streamlit is optional here; only used to read secrets and (optionally) show messages
try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

# Supabase client
try:
    from supabase import create_client, Client
except Exception:  # pragma: no cover
    create_client = None
    Client = Any  # type: ignore


# -----------------------------
# Supabase client helpers
# -----------------------------
def _read_secret(key: str) -> Optional[str]:
    """Read env -> st.secrets root -> st.secrets['general']"""
    if key in os.environ:
        return os.environ.get(key)
    if st is not None and hasattr(st, "secrets"):
        # root
        v = st.secrets.get(key)
        if v:
            return v
        # [general]
        gen = st.secrets.get("general", {})
        if isinstance(gen, dict):
            v = gen.get(key)
            if v:
                return v
    return None


def _client() -> Optional["Client"]:
    """Anon client for reads (safe for public tables with RLS)."""
    if create_client is None:
        if st:
            st.error("Supabase client not installed. Add 'supabase', 'postgrest', 'gotrue' to requirements.txt.")
        return None

    url = _read_secret("SUPABASE_URL") or _read_secret("NEXT_PUBLIC_SUPABASE_URL")
    key = _read_secret("SUPABASE_ANON_KEY") or _read_secret("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not (url and key):
        if st:
            st.error("Missing SUPABASE_URL or SUPABASE_ANON_KEY in environment/secrets.")
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        if st:
            st.error(f"Failed to init Supabase client: {e}")
        return None


# -----------------------------
# Casinos
# -----------------------------
CASINO_COLS_SELECT = "id,name,city,state,latitude,longitude,is_active,inserted_at,updated_at"

def _ensure_casino_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee expected columns exist; coerce coordinates to float; normalize lat/lng aliases."""
    df = (df or pd.DataFrame()).copy()

    # normalize potential aliases
    if "latitude" not in df.columns and "lat" in df.columns:
        df = df.rename(columns={"lat": "latitude"})
    if "longitude" not in df.columns and "lng" in df.columns:
        df = df.rename(columns={"lng": "longitude"})

    expected = ["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"]
    for col in expected:
        if col not in df.columns:
            # defaults
            if col in ("latitude","longitude"):
                df[col] = None
            elif col == "is_active":
                df[col] = True
            else:
                df[col] = None

    # coerce coords to float or None
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

    df["latitude"] = [ _to_float_or_none(v) for v in df["latitude"] ]
    df["longitude"] = [ _to_float_or_none(v) for v in df["longitude"] ]

    # ensure name is string
    df["name"] = df["name"].astype(str)

    return df


def get_casinos_full(active_only: bool = True) -> pd.DataFrame:
    """
    Returns a DataFrame with: id, name, city, state, latitude, longitude, is_active, inserted_at, updated_at.
    Ensures latitude/longitude exist and are floats (or None), even if DB uses lat/lng or strings.
    """
    c = _client()
    if c is None:
        return pd.DataFrame(columns=["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"])
    try:
        res = c.table("casinos").select(CASINO_COLS_SELECT).order("name").execute()
        df = pd.DataFrame(res.data or [])
        df = _ensure_casino_cols(df)
        if active_only and "is_active" in df.columns:
            df = df[df["is_active"] == True].copy()
        return df.reset_index(drop=True)
    except Exception as e:
        # Return empty but shaped DF; surface a tiny hint for debugging in Streamlit
        if st:
            st.info(f"[get_casinos_full] fallback (error fetching): {e}")
        return pd.DataFrame(columns=["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"])


def get_casinos() -> List[str]:
    """
    Backwards‑compatible helper: returns only the list of active casino names.
    """
    df = get_casinos_full(active_only=True)
    if df.empty or "name" not in df.columns:
        return []
    return df["name"].dropna().astype(str).tolist()


# -----------------------------
# (Optional) other helpers you might already have can live below
#  — nothing removed to avoid breaking imports elsewhere.
# -----------------------------

# Example placeholder: load_game_data still available if something imports it.
def load_game_data() -> pd.DataFrame:
    """
    Placeholder returning empty DF (keep to avoid import errors elsewhere).
    Your app likely uses other game-loading functions; leave this as-is if unused.
    """
    return pd.DataFrame()