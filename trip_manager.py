from __future__ import annotations

import os, math
from typing import List, Dict, Any, Optional
import streamlit as st

# Use the silent one-shot geolocator
try:
    from browser_location import get_browser_location
except Exception:
    def get_browser_location(key: str = "browser_geo"):
        return None, None, "none"

# === Feature flag ===
def _truthy(v: Optional[str]) -> bool:
    return str(v).strip().lower() in ("1","true","yes","on","y") if v is not None else False
def _flag(key: str, default: bool) -> bool:
    if key in os.environ: return _truthy(os.environ.get(key))
    if hasattr(st, "secrets"):
        v = st.secrets.get(key)
        if v is not None: return _truthy(str(v))
        gen = st.secrets.get("general", {})
        if isinstance(gen, dict) and key in gen: return _truthy(str(gen.get(key)))
    return default
ENABLE_NEARBY = _flag("ENABLE_NEARBY", True)

# === Data access (same API you already use) ===
get_casinos_full = None
get_casinos = None
try:
    from data_loader_supabase import get_casinos_full as _gcf
    get_casinos_full = _gcf
except Exception: pass
try:
    from data_loader_supabase import get_casinos as _gc
    get_casinos = _gc
except Exception: pass

# =========================
# Session state (unchanged)
# =========================
def initialize_trip_state() -> None:
    if "trip_started" not in st.session_state: st.session_state.trip_started = False
    if "current_trip_id" not in st.session_state: st.session_state.current_trip_id = 0
    if "trip_settings" not in st.session_state or not isinstance(st.session_state.trip_settings, dict):
        st.session_state.trip_settings = {
            "casino": "", "starting_bankroll": 200.0, "num_sessions": 3,
            "use_my_location": False, "nearby_radius": 30,
        }
    if "trip_bankrolls" not in st.session_state: st.session_state.trip_bankrolls = {}
    if "blacklisted_games" not in st.session_state: st.session_state.blacklisted_games = set()
    if "recent_profits" not in st.session_state: st.session_state.recent_profits = []
    if "session_log" not in st.session_state: st.session_state.session_log = []

def _reset_trip_defaults() -> None:
    st.session_state.trip_settings = {
        "casino": "", "starting_bankroll": 200.0, "num_sessions": 3,
        "use_my_location": False, "nearby_radius": 30,
    }

# =========================
# Helpers
# =========================
def _to_float_or_none(v):
    try:
        if v is None: return None
        if isinstance(v,(int,float)): return float(v)
        s = str(v).strip()
        if not s or s.lower()=="nan": return None
        return float(s)
    except Exception:
        return None

def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    lat1=_to_float_or_none(lat1); lon1=_to_float_or_none(lon1)
    lat2=_to_float_or_none(lat2); lon2=_to_float_or_none(lon2)
    if None in (lat1,lon1,lat2,lon2): return float("inf")
    R=3958.7613
    p1,p2=math.radians(lat1),math.radians(lat2)
    dphi=math.radians(lat2-lat1); dlmb=math.radians(lon2-lon1)
    a=math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2*R*math.asin(math.sqrt(a))

def _load_casino_names_df():
    df=None; names=[]
    if callable(get_casinos_full):
        try: df=get_casinos_full(active_only=True)
        except Exception: df=None
    if df is None and callable(get_casinos):
        try: names=[c for c in (get_casinos() or []) if c]
        except Exception: names=[]
    if df is not None and getattr(df,"empty",True) is False and "name" in df.columns:
        if "is_active" in df.columns: df=df[df["is_active"]==True].copy()
        for col in ("latitude","longitude"):
            if col in df.columns: df[col]=[_to_float_or_none(v) for v in df[col]]
        names=df["name"].dropna().astype(str).tolist()
    names=[n for n in names if n and n!="Other..."]
    names=sorted(names, key=lambda s: s.lower())  # A→Z
    return names, df

# =========================
# Nearby filter
# =========================
def _nearby_filter_options(disabled: bool) -> List[str]:
    all_names, df = _load_casino_names_df()
    info = {"enabled": ENABLE_NEARBY, "applied": False, "fallback_all": False,
            "geo_source":"none","radius_miles":int(st.session_state.trip_settings.get("nearby_radius",30)),
            "nearby_count":0,"total":len(all_names),"with_coords":0,"reason":""}

    if not ENABLE_NEARBY:
        st.session_state["_nearby_info"]=info
        return all_names

    st.caption("Filter casinos near you")
    colA,colB=st.columns([1,1])
    with colA:
        use_loc = st.checkbox("Use my location",
                              value=bool(st.session_state.trip_settings.get("use_my_location",False)),
                              key="tm_use_my_location", disabled=disabled)
    with colB:
        radius = st.slider("Radius (miles)", 5, 300,
                           int(st.session_state.trip_settings.get("nearby_radius",30)),
                           step=5, key="tm_nearby_radius", disabled=disabled)

    st.session_state.trip_settings["use_my_location"]=bool(use_loc)
    st.session_state.trip_settings["nearby_radius"]=int(radius)
    info["radius_miles"]=int(radius)

    if not st.session_state.trip_settings["use_my_location"]:
        info["reason"]="use_my_location_off"
        st.session_state["_nearby_info"]=info
        return all_names

    if df is None or "latitude" not in df.columns or "longitude" not in df.columns:
        info["reason"]="no_casino_coords_df"
        st.session_state["_nearby_info"]=info
        return all_names

    df=df.copy()
    for col in ("latitude","longitude"):
        df[col]=[_to_float_or_none(v) for v in df[col]]
    info["with_coords"]=int((df["latitude"].notna() & df["longitude"].notna()).sum())
    if info["with_coords"]==0:
        info["reason"]="no_casino_coords_rows"
        st.session_state["_nearby_info"]=info
        return all_names

    # Auto-request location immediately (no extra UI). If JS fails, the blue target appears.
    lat, lon, src = get_browser_location(key="trip_sidebar_geo")
    info["geo_source"]=st.session_state.get("client_geo_source", src or "none")
    user_lat = st.session_state.get("client_lat") if st.session_state.get("client_lat") is not None else lat
    user_lon = st.session_state.get("client_lon") if st.session_state.get("client_lon") is not None else lon

    if user_lat is None or user_lon is None:
        info["reason"]="waiting_for_browser_location"
        st.session_state["_nearby_info"]=info
        return all_names

    # Fix obviously positive US longitudes
    try:
        pos_ratio=float((df["longitude"]>0).sum())/float(len(df))
        if pos_ratio>=0.8: df["longitude"]=df["longitude"].apply(lambda x: -abs(x) if x is not None else None)
    except Exception: pass

    info["applied"]=True
    df["distance_mi"]=df.apply(lambda r: _haversine_miles(r.get("latitude"),r.get("longitude"),user_lat,user_lon), axis=1)
    nearby=df[df["distance_mi"].notna()].sort_values("distance_mi")
    within=nearby[nearby["distance_mi"]<=float(info["radius_miles"])].copy()
    info["nearby_count"]=int(len(within))

    if within.empty:
        info["fallback_all"]=True; info["reason"]="no_matches"
        st.session_state["_nearby_info"]=info
        return all_names

    st.session_state["_nearby_info"]=info
    return sorted(within["name"].astype(str).tolist(), key=lambda s: s.lower())  # A→Z

# =========================
# Sidebar (public API your app imports)
# =========================
def render_sidebar() -> None:
    initialize_trip_state()
    with st.sidebar:
        st.header("🎯 Trip Settings")
        disabled=bool(st.session_state.trip_started)

        options=_nearby_filter_options(disabled=disabled)
        if not options:
            options=[st.session_state.trip_settings.get("casino","")] if st.session_state.trip_settings.get("casino") else ["(select casino)"]

        current=st.session_state.trip_settings.get("casino","")
        if current not in options and options: current=options[0]
        try: idx=options.index(current)
        except Exception: idx=0

        sel=st.selectbox("Casino", options=options, index=idx, disabled=disabled)
        st.session_state.trip_settings["casino"] = "" if sel=="(select casino)" else sel

        info=st.session_state.get("_nearby_info",{}) or {}
        use_loc=bool(st.session_state.trip_settings.get("use_my_location",False))
        radius=int(st.session_state.trip_settings.get("nearby_radius",30))
        if not ENABLE_NEARBY or not use_loc:
            st.caption("📍 near‑me: OFF" if not use_loc else f"📍 near‑me: ON • radius: {radius} mi • waiting for location")
        else:
            applied=bool(info.get("applied"))
            fallback=bool(info.get("fallback_all"))
            cnt=int(info.get("nearby_count",0)) if applied else 0
            if applied and not fallback:
                st.caption(f"📍 near‑me: ON • radius: {radius} mi • results: {cnt} (browser)")
            elif applied and fallback:
                st.caption(f"📍 near‑me: ON • radius: {radius} mi • 0 in range — showing all")
            else:
                st.caption(f"📍 near‑me: ON • radius: {radius} mi • waiting for location")

# =========================
# Rest of your public API (unchanged)
# =========================
def get_session_bankroll() -> float:
    ts=st.session_state.trip_settings
    total=float(ts.get("starting_bankroll",0.0) or 0.0)
    n=int(ts.get("num_sessions",1) or 1)
    n=max(1,n)
    return total/n

def get_current_bankroll() -> float:
    tid=st.session_state.get("current_trip_id",0)
    if tid in st.session_state.trip_bankrolls:
        return float(st.session_state.trip_bankrolls[tid])
    return float(st.session_state.trip_settings.get("starting_bankroll",0.0))

def get_win_streak_factor() -> float:
    profits=st.session_state.get("recent_profits",[])
    if len(profits)<3: return 1.0
    last=profits[-5:]; avg=sum(last)/len(last)
    if avg>0: return min(1.25, 1.0 + (avg/max(20.0,abs(avg))*0.25))
    if avg<0: return max(0.85, 1.0 + (avg/max(40.0,abs(avg))*0.15))
    return 1.0

def get_volatility_adjustment() -> float:
    profits=st.session_state.get("recent_profits",[])
    if len(profits)<3: return 1.0
    mean=sum(profits)/len(profits)
    var=sum((p-mean)**2 for p in profits)/len(profits)
    std=math.sqrt(var)
    if std<=20.0: return 1.05
    if std>=120.0: return 0.9
    return 1.0

def get_blacklisted_games() -> List[str]:
    return sorted(list(st.session_state.blacklisted_games))
def blacklist_game(game_name: str) -> None:
    st.session_state.blacklisted_games.add(game_name)