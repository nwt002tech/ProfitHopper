from __future__ import annotations

import os
from typing import Optional, List, Dict, Any
import pandas as pd

# Supabase client
try:
    from supabase import create_client
except Exception:
    create_client = None


# ----------------------------
# Supabase client helper
# ----------------------------
def _client(with_service: bool = False):
    """
    Create a Supabase client.
    - anon key for reads
    - service role key for writes/privileged ops (admin panel, coord updates)
    """
    if create_client is None:
        return None
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if with_service
        else (os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
    )
    if not (url and key):
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


# ----------------------------
# Casinos API
# ----------------------------
def get_casinos_full(active_only: bool = True) -> pd.DataFrame:
    """
    Return casinos with: id, name, city, state, latitude, longitude, is_active, inserted_at, updated_at.
    """
    c = _client()
    if not c:
        return pd.DataFrame(columns=["id","name","city","state","latitude","longitude","is_active"])
    q = c.table("casinos").select("*")
    if active_only:
        q = q.eq("is_active", True)
    res = q.order("name").execute()
    df = pd.DataFrame(res.data or [])
    # Ensure expected columns exist
    for col in ["city","state","latitude","longitude","is_active","inserted_at","updated_at"]:
        if col not in df.columns:
            df[col] = None if col in ("latitude","longitude") else (False if col == "is_active" else "")
    keep = ["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"]
    return df[[c for c in keep if c in df.columns]]

def get_casinos() -> List[str]:
    """Back‑compat: return active casino names (string list)."""
    df = get_casinos_full(active_only=True)
    return df["name"].dropna().astype(str).tolist()

def update_casino_coords(casino_id: str, lat: float, lon: float) -> bool:
    """Write lat/lon for a casino (service role key required)."""
    c = _client(with_service=True)
    if not c:
        return False
    try:
        c.table("casinos").update({"latitude": float(lat), "longitude": float(lon)}).eq("id", str(casino_id)).execute()
        return True
    except Exception:
        return False


# ----------------------------
# Games API (+ per‑casino availability merge)
# ----------------------------
_GAMES_COLS_ORDER = [
    "id","name","type","game_type","rtp","volatility","bonus_frequency","min_bet",
    "advantage_play_potential","best_casino_type","bonus_trigger_clues",
    "tips","image_url","source_url","updated_at",
    "is_hidden","is_unavailable","score"
]

def _norm_games_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=_GAMES_COLS_ORDER)
    # Ensure expected columns
    for c in _GAMES_COLS_ORDER:
        if c not in df.columns:
            df[c] = None
    # Types
    for b in ["is_hidden","is_unavailable"]:
        if b in df.columns:
            df[b] = df[b].fillna(False).astype(bool)
    for n in ["rtp","bonus_frequency","min_bet","score"]:
        if n in df.columns:
            df[n] = pd.to_numeric(df[n], errors="coerce")
    for n in ["volatility","advantage_play_potential"]:
        if n in df.columns:
            df[n] = pd.to_numeric(df[n], errors="coerce").astype("Int64")
    # Order
    cols = [c for c in _GAMES_COLS_ORDER if c in df.columns] + [c for c in df.columns if c not in _GAMES_COLS_ORDER]
    return df[cols]

def load_game_data(
    casino: Optional[str] = None,
    include_availability: bool = True,
    limit: Optional[int] = None,
    only_visible: bool = False,
    additional_filters: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Load games from public.games. Optionally merge per‑casino availability
    as 'is_unavailable_at_casino' for the given casino.
    """
    c = _client()
    if not c:
        return pd.DataFrame(columns=_GAMES_COLS_ORDER)

    q = c.table("games").select("*")
    if only_visible:
        q = q.eq("is_hidden", False)
    if additional_filters:
        for k, v in additional_filters.items():
            if v is None:
                continue
            q = q.eq(k, v)
    if limit:
        q = q.limit(int(limit))

    res = q.execute()
    games = pd.DataFrame(res.data or [])
    games = _norm_games_df(games)

    # Merge per‑casino availability
    if include_availability and casino:
        try:
            q2 = c.table("game_availability").select("game_id, casino, is_unavailable").ilike("casino", str(casino).strip())
            res2 = q2.execute()
            avail = pd.DataFrame(res2.data or [])
            if not avail.empty:
                avail = avail[["game_id","is_unavailable"]].rename(columns={"is_unavailable": "is_unavailable_at_casino"})
                avail["game_id"] = avail["game_id"].astype(str)
                games["id"] = games["id"].astype(str)
                games = games.merge(avail, left_on="id", right_on="game_id", how="left")
                games.drop(columns=["game_id"], inplace=True)
                games["is_unavailable_at_casino"] = games["is_unavailable_at_casino"].fillna(False).astype(bool)
            else:
                games["is_unavailable_at_casino"] = False
        except Exception:
            games["is_unavailable_at_casino"] = False

    return games

def get_games(limit: Optional[int] = None) -> pd.DataFrame:
    """Shorthand for load_game_data without availability join."""
    return load_game_data(casino=None, include_availability=False, limit=limit, only_visible=False)

def get_visible_games(casino: Optional[str] = None, limit: Optional[int] = None) -> pd.DataFrame:
    """Visible (not hidden) games, optionally with per‑casino availability."""
    return load_game_data(casino=casino, include_availability=True, limit=limit, only_visible=True)