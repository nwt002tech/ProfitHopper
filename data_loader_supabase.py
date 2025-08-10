import os
import pandas as pd

try:
    from supabase import create_client
except Exception:
    create_client = None

def _client(with_service: bool = False):
    """Anon by default; service (write) when requested."""
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") if with_service
           else (os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")))
    if not (url and key) or create_client is None:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None

def get_casinos_full(active_only: bool = True) -> pd.DataFrame:
    """Return casinos with name, city, state, latitude, longitude, is_active."""
    c = _client()
    if not c:
        return pd.DataFrame(columns=["id","name","city","state","latitude","longitude","is_active"])
    q = c.table("casinos").select("*")
    if active_only:
        q = q.eq("is_active", True)
    res = q.order("name").execute()
    df = pd.DataFrame(res.data or [])
    for col in ["city","state","latitude","longitude","is_active"]:
        if col not in df.columns:
            df[col] = None if col in ("latitude","longitude") else ""
    # enforce column order
    keep = ["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"]
    return df[[c for c in keep if c in df.columns]]

def get_casinos() -> list[str]:
    """(Back‑compat) Return just the list of active casino names."""
    df = get_casinos_full(active_only=True)
    return df["name"].dropna().astype(str).tolist()

def update_casino_coords(casino_id: str, lat: float, lon: float) -> bool:
    """Write-back latitude/longitude for a casino (service-role key required)."""
    c = _client(with_service=True)
    if not c:
        return False
    try:
        c.table("casinos").update({"latitude": lat, "longitude": lon}).eq("id", str(casino_id)).execute()
        return True
    except Exception:
        return False