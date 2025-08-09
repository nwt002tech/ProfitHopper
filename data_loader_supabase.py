"""
Supabase-integrated data loader for Profit Hopper.

This module attempts to fetch game data from a Supabase table named
`games` using the Supabase anon key and URL provided via environment
variables (SUPABASE_URL and SUPABASE_ANON_KEY). If Supabase is
unavailable or empty, it falls back to loading the original CSV from
GitHub. It also normalizes columns and sanitizes game tips so that
inappropriate advice (e.g., keno strategies on slot games) does not
appear in the UI. Bonus frequency tips are clarified with concrete
spin ranges (30–40 spins for high frequency; 50+ spins for low).
"""

import os
import re
import pandas as pd
from typing import Optional

try:
    # supabase-py is optional; if not installed the loader will fall back
    from supabase import create_client
except Exception:
    create_client = None  # type: ignore

# URL of the CSV as a fallback data source
CSV_FALLBACK_URL = "https://raw.githubusercontent.com/nwt002tech/profit-hopper/main/extended_game_list.csv"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names to snake_case and ensure expected columns exist."""
    df = df.copy()
    # Normalize column names
    df.columns = [re.sub(r"\W+", "_", col.strip()).lower() for col in df.columns]
    # Ensure required and optional columns exist
    for col in [
        "tips",
        "type",
        "game_type",
        "rtp",
        "volatility",
        "bonus_frequency",
        "min_bet",
        "advantage_play_potential",
        "best_casino_type",
        "bonus_trigger_clues",
        "image_url",
        "source_url",
    ]:
        if col not in df.columns:
            if col in ("rtp", "volatility", "bonus_frequency", "min_bet", "advantage_play_potential"):
                df[col] = None
            else:
                df[col] = ""
    # Derive game_type if missing
    if "game_type" not in df.columns or df["game_type"].eq("").all():
        def norm_type(val: str) -> str:
            s = str(val).lower()
            if "keno" in s:
                return "video keno" if "video" in s else "keno"
            if "poker" in s:
                return "video poker"
            if "slot" in s or "reel" in s:
                return "slot"
            return "unknown"
        df["game_type"] = df["type"].apply(norm_type)
    return df


def _tip_sanity_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Clean up and clarify game tips based on game type and name."""
    df = df.copy()
    def refine(row: pd.Series) -> str:
        tip = str(row.get("tips", "") or "").strip()
        gtype = str(row.get("game_type", "")).lower()
        name = str(row.get("name", row.get("game_name", ""))).lower()
        # Slot-specific cleaning
        if gtype == "slot":
            # Remove keno/poker-specific advice
            if "overlapping pattern" in tip.lower() or "card" in tip.lower():
                tip = ""
            # Clarify bonus frequency
            if "bonus frequency" in tip.lower():
                tip = (
                    "High bonus frequency ≈ 1 bonus every 30–40 spins; 50+ spins without a "
                    "bonus is low — consider switching."
                )
            # Special-case: 88 Fortunes
            if "88 fortunes" in name:
                tip = (
                    "Use a bet level your bankroll supports; enabling Gold Symbols increases "
                    "jackpot eligibility but also cost. Fu Bat jackpots are random—don’t chase. "
                    "If 50+ spins pass without a bonus, switch."
                )
        # Keno-specific guidance
        elif gtype in ("video keno", "keno"):
            tip = (
                "Use overlapping number clusters across cards so one hit can pay on multiple cards. "
                "Keep total risk ≤2% of session bankroll per draw; rotate patterns that stay cold for "
                "20–30 draws."
            )
        # Video poker guidance
        elif gtype == "video poker":
            # Only override generic or missing tips
            if not tip or "bonus frequency" in tip.lower():
                tip = (
                    "Use the correct strategy card for the exact paytable; prefer full- or near-full-pay "
                    "versions. Keep one-hand bet ≤2% of session bankroll."
                )
        # Default fallback
        return tip or "Play within bankroll and follow the strategy shown."
    df["tips"] = df.apply(refine, axis=1)
    return df


def _load_from_supabase() -> Optional[pd.DataFrame]:
    """Attempt to load the games table from Supabase using anon credentials."""
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key or create_client is None:
        return None
    try:
        client = create_client(url, key)
        response = client.table("games").select("*").execute()
        df = pd.DataFrame(response.data)
        return df if not df.empty else None
    except Exception:
        return None


def load_game_data() -> pd.DataFrame:
    """Public interface: load game data from Supabase or fallback to CSV."""
    # Try Supabase first
    df = _load_from_supabase()
    if df is None or df.empty:
        # Fallback to CSV hosted on GitHub
        df = pd.read_csv(CSV_FALLBACK_URL)
    # Normalize columns and sanitize tips
    df = _normalize_columns(df)
    df = _tip_sanity_filter(df)
    return df