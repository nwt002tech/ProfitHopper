
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Dict, Optional

# ---------- Geocoding (Option B auto-enrichment support) ----------
try:
    from geopy.geocoders import Nominatim
    from geopy.extra.rate_limiter import RateLimiter
except Exception:
    Nominatim = None
    RateLimiter = None

_geocoder = None
_rate_limited_geocode = None

def _get_geocoder():
    """Create a rate-limited Nominatim geocoder (once)."""
    global _geocoder, _rate_limited_geocode
    if _geocoder is None and Nominatim is not None:
        _geocoder = Nominatim(user_agent="profithopper/1.0 (contact: your-email@example.com)")
        _rate_limited_geocode = RateLimiter(_geocoder.geocode, min_delay_seconds=1.1, swallow_exceptions=True)
    return _rate_limited_geocode

@lru_cache(maxsize=512)
def geocode_city_state(city: str, state: str):
    """Return (lat, lon) from city/state, or (None, None) if not found."""
    geo = _get_geocoder()
    if geo is None:
        return None, None
    q = ", ".join([s for s in [city or "", state or ""] if s])
    if not q.strip():
        return None, None
    loc = geo(q)
    if loc:
        return float(loc.latitude), float(loc.longitude)
    return None, None

def haversine_miles(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance between two points in miles."""
    if None in (lat1, lon1, lat2, lon2):
        return float("inf")
    R = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ---------- Safe coercions ----------
def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None or (isinstance(x, str) and not x.strip()):
            return None
        return float(x)
    except Exception:
        return None

def _to_int(x: Any) -> Optional[int]:
    try:
        if x is None or (isinstance(x, str) and not x.strip()):
            return None
        return int(float(x))
    except Exception:
        return None

# ---------- Mappers expected by app.py ----------
VOL_LABELS = {
    1: "Very Low",
    2: "Low",
    3: "Medium",
    4: "High",
    5: "Very High",
}

ADV_LABELS = {
    1: "Low",
    2: "Low‑Med",
    3: "Medium",
    4: "Med‑High",
    5: "High",
}

def map_volatility(value: Any) -> str:
    """
    Maps a volatility score to a readable label.
    Accepts ints (1‑5), floats, or strings like 'Low', 'Medium', 'High'.
    """
    if isinstance(value, str):
        t = value.strip().lower()
        if t in {"very low","low","medium","high","very high"}:
            return value  # already a label
        v = _to_float(value)
    else:
        v = _to_float(value)
    if v is None:
        return "Unknown"
    # Clamp 1..5
    v = max(1, min(5, int(round(v))))
    return VOL_LABELS.get(v, "Unknown")

def map_advantage(value: Any) -> str:
    """
    Maps 'advantage_play_potential' (usually 1‑5) to a label.
    """
    if isinstance(value, str) and value.strip().lower() in {s.lower() for s in ADV_LABELS.values()}:
        return value
    v = _to_float(value)
    if v is None:
        return "Unknown"
    v = max(1, min(5, int(round(v))))
    return ADV_LABELS.get(v, "Unknown")

def map_bonus_freq(value: Any) -> str:
    """
    Maps a 'bonus_frequency' numeric to a qualitative label.
    Heuristic buckets that work for counts/percents alike.
    """
    v = _to_float(value)
    if v is None or v <= 0:
        return "Unknown"
    # If it's a percent (<=1.0) scale heuristically
    vv = v
    if v <= 1.0:
        if vv <= 0.05: return "Very Rare"
        if vv <= 0.15: return "Rare"
        if vv <= 0.30: return "Occasional"
        if vv <= 0.60: return "Frequent"
        return "Very Frequent"
    # If it's a raw count per session/100spins/etc.
    if vv <= 1.0: return "Very Rare"
    if vv <= 3.0: return "Rare"
    if vv <= 7.0: return "Occasional"
    if vv <= 15.0: return "Frequent"
    return "Very Frequent"

# ---------- Image URL helper ----------
_PLACEHOLDERS = {
    "slots": "https://via.placeholder.com/300x200?text=Slots",
    "video poker": "https://via.placeholder.com/300x200?text=Video+Poker",
    "table": "https://via.placeholder.com/300x200?text=Table+Game",
    "default": "https://via.placeholder.com/300x200?text=Game",
}

def get_game_image_url(row: Dict[str, Any] | None = None, default: str | None = None) -> str:
    """
    Returns a usable image URL for a game.
    Priority: explicit image_url -> type-specific placeholder -> default placeholder.
    """
    if not row:
        return default or _PLACEHOLDERS["default"]
    # direct field
    img = (row.get("image_url") if isinstance(row, dict) else None) or None
    if img and str(img).strip():
        return str(img).strip()
    # by type
    gtype = ""
    for k in ("type", "game_type", "category"):
        if isinstance(row, dict) and k in row and row[k]:
            gtype = str(row[k]).strip().lower()
            break
    if "slot" in gtype:
        return _PLACEHOLDERS["slots"]
    if "poker" in gtype:
        return _PLACEHOLDERS["video poker"]
    if "table" in gtype or "blackjack" in gtype or "roulette" in gtype or "craps" in gtype:
        return _PLACEHOLDERS["table"]
    return default or _PLACEHOLDERS["default"]

# ---------- Back-compat: old CSV helper (no-op) ----------
def get_csv_download_link(*args, **kwargs):
    """Deprecated. Kept only so older modules can import without breaking."""
    return None
