# supabase_client.py
# Tiny wrapper so the app can read from Supabase using the anon key.

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    # Supabase-py v2
    from supabase import create_client  # type: ignore
except Exception as e:  # pragma: no cover
    create_client = None  # handled below

# -----------------------------------------------------------------------------
# Secrets/env handling
# -----------------------------------------------------------------------------
def _get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Read Supabase settings from either Streamlit secrets or environment variables.
    Priority: st.secrets['supabase'][key] -> os.environ -> default
    """
    try:
        import streamlit as st  # local import to avoid hard dep if testing
        sec = (st.secrets.get("supabase") or {}) if hasattr(st, "secrets") else {}
        if key in sec and sec[key]:
            return str(sec[key])
    except Exception:
        pass
    return os.environ.get(key.upper()) or default


# -----------------------------------------------------------------------------
# Public API used by app.py
# -----------------------------------------------------------------------------
def get_supabase():
    """Return a Supabase client (read-only via anon key)."""
    if create_client is None:
        raise RuntimeError(
            "Supabase client is not installed. Add 'supabase', 'postgrest', and 'gotrue' to requirements.txt."
        )

    # Accept both styles:
    #   st.secrets["supabase"]["url"] / ["anon_key"]
    #   or env vars SUPABASE_URL / SUPABASE_ANON_KEY
    url = _get_secret("url") or os.environ.get("SUPABASE_URL")
    key = _get_secret("anon_key") or os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        return None  # app.py shows a friendly error and stops

    return create_client(url, key)


def fetch_games(client, table_name: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Fetch rows from the given Supabase table.
    Returns (rows, error_message). Filters out hidden/unavailable when columns exist.
    """
    try:
        query = client.table(table_name).select("*")
        # If these columns exist in the table, filter them out. If they don’t, Supabase
        # will throw—so we probe columns first.
        cols = _get_table_columns(client, table_name)
        if "is_hidden" in cols:
            query = query.eq("is_hidden", False)
        if "is_unavailable" in cols:
            query = query.eq("is_unavailable", False)

        res = query.execute()
        rows = res.data or []
        return rows, None
    except Exception as e:
        return [], f"{e}"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _get_table_columns(client, table_name: str) -> List[str]:
    """
    Best-effort way to learn columns: select 1 row and inspect keys.
    If table is empty, fall back to empty list (no filtering).
    """
    try:
        res = client.table(table_name).select("*").limit(1).execute()
        data = res.data or []
        if not data:
            return []
        return list(pd.DataFrame(data).columns)
    except Exception:
        return []