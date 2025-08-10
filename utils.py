import math
from functools import lru_cache

# Geocoding (Option B auto-enrichment)
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
        # Put a real contact email if you have one
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