#!/usr/bin/env python3
"""
One-time script to upload the Profit Hopper game data into a Supabase table.

This script fetches the latest `extended_game_list.csv` from the Profit Hopper
GitHub repository, normalizes column names, infers the `game_type` if missing,
ensures required columns exist, and then performs an upsert into the
`public.games` table using the Supabase Service Role key. The script chunks
records to avoid hitting API limits and prints progress as it uploads.

Environment variables required:
  SUPABASE_URL: Base URL of your Supabase instance (e.g. https://xxxx.supabase.co)
  SUPABASE_SERVICE_ROLE_KEY: Secret service role key with write privileges

Usage:
  python seed_supabase.py

Note: Running this script will modify your Supabase database. Confirm before use.
"""

import os
import io
import requests
import pandas as pd
from supabase import create_client

RAW_CSV_URL = "https://raw.githubusercontent.com/nwt002tech/profit-hopper/main/extended_game_list.csv"


def normalize_type(value: str) -> str:
    value = str(value).lower()
    if "keno" in value:
        return "video keno" if "video" in value else "keno"
    if "poker" in value:
        return "video poker"
    if "slot" in value or "reel" in value:
        return "slot"
    return "unknown"


def load_data() -> pd.DataFrame:
    """Load and normalize the raw game data from the CSV."""
    csv_text = requests.get(RAW_CSV_URL, timeout=30).text
    df = pd.read_csv(io.StringIO(csv_text))
    # Normalize column names to snake_case
    df = df.rename(columns={c: c.strip().lower().replace(" ", "_") for c in df.columns})
    # Derive game_type if missing
    if "game_type" not in df.columns:
        df["game_type"] = df.get("type", "").apply(normalize_type)
    # Ensure necessary text and numeric columns exist
    for col in ["tips", "best_casino_type", "bonus_trigger_clues", "image_url", "source_url"]:
        if col not in df.columns:
            df[col] = ""
    for col in ["rtp", "volatility", "bonus_frequency", "min_bet", "advantage_play_potential"]:
        if col not in df.columns:
            df[col] = None
    # Convert numeric columns to appropriate types
    # Volatility: cast to integer (1-5) where possible
    df["volatility"] = pd.to_numeric(df["volatility"], errors="coerce").astype("Int64")
    # Advantage play potential: original CSV uses 0-1 scale (e.g., 0.3, 0.6, 1.0).
    # Convert to integer 1-5 scale by multiplying by 5 and rounding. Missing values become NA.
    adv_raw = pd.to_numeric(df["advantage_play_potential"], errors="coerce")
    df["advantage_play_potential"] = (adv_raw * 5).round().astype("Int64")
    # RTP, bonus_frequency, min_bet should be numeric floats
    df["rtp"] = pd.to_numeric(df["rtp"], errors="coerce")
    df["bonus_frequency"] = pd.to_numeric(df["bonus_frequency"], errors="coerce")
    df["min_bet"] = pd.to_numeric(df["min_bet"], errors="coerce")
    return df


def upsert_to_supabase(df: pd.DataFrame) -> None:
    """Upsert the game data into Supabase using the service role key."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the environment"
        )
    client = create_client(url, key)
    # Keep only columns that exist in the database schema. Extra columns
    # (like 'has_bonus' or 'recommended_denomination') will cause an API error
    # because the table does not have those fields.
    allowed_cols = {
        "name",
        "type",
        "game_type",
        "rtp",
        "volatility",
        "bonus_frequency",
        "min_bet",
        "advantage_play_potential",
        "best_casino_type",
        "bonus_trigger_clues",
        "tips",
        "image_url",
        "source_url",
    }
    records = [
        {k: v for k, v in row.items() if k in allowed_cols}
        for row in df.to_dict(orient="records")
    ]
    total = len(records)
    for i in range(0, total, 500):
        chunk = records[i : i + 500]
        client.table("games").upsert(chunk).execute()
        print(f"Upserted {min(i + len(chunk), total)} / {total}")


def main():
    df = load_data()
    upsert_to_supabase(df)


if __name__ == "__main__":
    main()