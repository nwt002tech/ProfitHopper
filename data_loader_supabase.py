# data_loader_supabase.py — Supabase ONLY (no CSV fallback)
# Updated to support:
# - load_game_data(current_casino=...) with per‑casino availability merge
# - get_casinos_full(), get_casinos()
# - update_casino_coords(casino_id, lat, lon) (no‑op if columns not present)

import os, re
import pandas as pd
from typing import Optional, Dict, Any, List

try:
    from supabase import create_client
except Exception as e:
    create_client = None

# --- helpers ---------------------------------------------------------------

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\W+", "_", c.strip()).lower() for c in df.columns]
    # friendly aliases
    if "name" in df.columns and "game_name" not in df.columns:
        df["game_name"] = df["name"]
    if "is_unavailable_at_casino" in df.columns and "unavailable_here" not in df.columns:
        df["unavailable_here"] = df["is_unavailable_at_casino"]
    # types
    bool_cols = ["is_hidden","is_unavailable","unavailable_here"]
    for b in bool_cols:
        if b in df.columns:
            df[b] = df[b].fillna(False).astype(bool)
    # score field always present
    if "score" not in df.columns:
        df["score"] = None
    return df

def _tip_sanity_filter(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "tips" in df.columns:
        df["tips"] = df["tips"].fillna("").astype(str)
        df["tips"] = df["tips"].apply(lambda t: t if len(t) <= 1000 else t[:1000] + "…")
    return df

def _client(with_service: bool = False):
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if with_service
        else (os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
    )
    if create_client is None:
        raise RuntimeError("Supabase client not installed. Add 'supabase', 'postgrest', 'gotrue' to requirements.txt.")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY. Set env vars or Streamlit secrets before running.")
    return create_client(url, key)

# --- base loaders ----------------------------------------------------------
def _load_games() -> pd.DataFrame:
    client = _client(False)
    res = client.table("games").select("*").execute()
    data = res.data or []
    df = pd.DataFrame(data)
    if df.empty:
        raise RuntimeError("Supabase query returned 0 rows from table 'games'. Seed data or check RLS/policies.")
    return df

def _load_availability_for(casino: str) -> pd.DataFrame:
    client = _client(False)
    res = client.table("game_availability").select("game_id, casino, is_unavailable").ilike("casino", casino).execute()
    return pd.DataFrame(res.data or [])

def _load_casinos(active_only: bool = True) -> pd.DataFrame:
    client = _client(False)
    q = client.table("casinos").select("*")
    if active_only:
        q = q.eq("is_active", True)
    res = q.order("name").execute()
    df = pd.DataFrame(res.data or [])
    # normalize expected columns
    for c in ["city","state","latitude","longitude","is_active","inserted_at","updated_at"]:
        if c not in df.columns:
            df[c] = None if c in ("latitude","longitude") else (False if c == "is_active" else "")
    return df

# --- public API ------------------------------------------------------------

def load_game_data(
    current_casino: Optional[str] = None,
    only_visible: bool = False,
    limit: Optional[int] = None,
    additional_filters: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Load games from Supabase and (optionally) merge per‑casino availability.

    Returns columns including:
      - name, game_name
      - is_hidden
      - unavailable_here (bool) when current_casino provided
      - score (if present in DB; otherwise None)
    """
    df = _load_games()
    if only_visible and "is_hidden" in df.columns:
        df = df[df["is_hidden"] != True]

    # Simple equality filters if requested
    if additional_filters:
        for k, v in additional_filters.items():
            if k in df.columns and v is not None:
                df = df[df[k] == v]

    if limit:
        df = df.head(int(limit))

    # Merge per‑casino availability
    if current_casino:
        try:
            avail = _load_availability_for(str(current_casino).strip())
            if not avail.empty:
                avail = avail.rename(columns={"is_unavailable": "is_unavailable_at_casino"})
                avail["game_id"] = avail["game_id"].astype(str)
                if "id" in df.columns:
                    df["id"] = df["id"].astype(str)
                    df = df.merge(avail[["game_id","is_unavailable_at_casino"]], left_on="id", right_on="game_id", how="left")
                    if "game_id" in df.columns:
                        df.drop(columns=["game_id"], inplace=True)
                    df["is_unavailable_at_casino"] = df["is_unavailable_at_casino"].fillna(False).astype(bool)
                    df["unavailable_here"] = df["is_unavailable_at_casino"]
        except Exception:
            # ignore availability if join fails
            pass

    df = _normalize_columns(df)
    df = _tip_sanity_filter(df)
    return df

def get_casinos_full(active_only: bool = True) -> pd.DataFrame:
    df = _load_casinos(active_only=active_only)
    # Keep common columns in expected order if present
    keep = ["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"]
    return df[[c for c in keep if c in df.columns]]

def get_casinos() -> List[str]:
    df = get_casinos_full(active_only=True)
    return df["name"].dropna().astype(str).tolist()

def update_casino_coords(casino_id: str, lat: float, lon: float) -> bool:
    """Write lat/lon for a casino (no‑op if columns not present)."""
    try:
        client = _client(True)
        client.table("casinos").update({"latitude": float(lat), "longitude": float(lon)}).eq("id", str(casino_id)).execute()
        return True
    except Exception:
        return False
