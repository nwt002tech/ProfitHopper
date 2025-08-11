from __future__ import annotations

import os
import re
import math
from functools import lru_cache
from typing import Tuple, Optional, List

import pandas as pd
import streamlit as st

# ---- Supabase (service role for writes) ----
try:
    from supabase import create_client
except Exception:
    create_client = None

# ---- Geocoding providers via geopy ----
try:
    from geopy.geocoders import Nominatim, ArcGIS
    from geopy.extra.rate_limiter import RateLimiter
except Exception:
    Nominatim = None
    ArcGIS = None
    RateLimiter = None

# global geocoders (lazy init)
_nom = None
_nom_rate = None
_arc = None
_arc_rate = None

# cache only successful lookups to avoid caching failures
_geo_cache: dict[str, tuple[float | None, float | None]] = {}

US_STATE_MAP = {
    # common variants → USPS code
    "la": "LA", "louisiana": "LA",
    "ms": "MS", "mississippi": "MS",
    "ok": "OK", "oklahoma": "OK",
    "tx": "TX", "texas": "TX",
    # add more here as needed
}

def _normalize_city_state(city: str, state: str) -> tuple[str, str]:
    # fix spacing and smart quotes
    c = (city or "").strip().replace("’", "'").replace("  ", " ")
    s = (state or "").strip().replace("’", "'").replace("  ", " ")
    # fix known city typos
    if c.lower().replace(" ", "") == "gulfport":
        c = "Gulfport"
    # normalize state to USPS
    key = s.lower()
    s = US_STATE_MAP.get(key, s.upper())
    if len(s) > 2 and s.lower() in US_STATE_MAP:
        s = US_STATE_MAP[s.lower()]
    return c, s

def _init_geocoders():
    global _nom, _nom_rate, _arc, _arc_rate
    if _nom is None and Nominatim is not None:
        _nom = Nominatim(user_agent="profithopper-admin/1.2")
        _nom_rate = RateLimiter(_nom.geocode, min_delay_seconds=1.2, swallow_exceptions=True)
    if _arc is None and ArcGIS is not None:
        _arc = ArcGIS(user_agent="profithopper-admin/arcgis")
        _arc_rate = RateLimiter(_arc.geocode, min_delay_seconds=1.0, swallow_exceptions=True)

@lru_cache(maxsize=1024)
def _norm_key(name: str, city: str, state: str, country: str) -> str:
    return "|".join([
        (name or "").strip().lower(),
        (city or "").strip().lower(),
        (state or "").strip().lower(),
        (country or "").strip().lower(),
    ])

def geocode_casino(name: str, city: str, state: str, country: str = "USA") -> tuple[float | None, float | None, str]:
    """
    Robust geocode with:
      - normalization,
      - multiple query candidates,
      - Nominatim first, ArcGIS fallback,
      - success-only caching,
      - returns (lat, lon, provider_used or reason).
    """
    if Nominatim is None and ArcGIS is None:
        return None, None, "no_geocoder"

    _init_geocoders()
    city, state = _normalize_city_state(city, state)
    nm = (name or "").strip()

    # Build candidate queries (most specific → least)
    queries = []
    if nm and city and state:
        queries.append(f"{nm}, {city}, {state}, {country}")
    if city and state:
        queries.append(f"{city}, {state}, {country}")
        queries.append(f"{city}, {state}")
    if state:
        queries.append(f"{state}, {country}")
    if nm:
        queries.append(f"{nm}, {country}")
        queries.append(nm)

    cache_key = _norm_key(nm, city, state, country or "")
    if cache_key in _geo_cache:
        lat, lon = _geo_cache[cache_key]
        return lat, lon, "cache"

    # Try Nominatim first
    if _nom_rate is not None:
        for q in queries:
            loc = _nom_rate(q)
            if loc:
                try:
                    lat, lon = float(loc.latitude), float(loc.longitude)
                    _geo_cache[cache_key] = (lat, lon)
                    return lat, lon, "nominatim"
                except Exception:
                    pass

    # Fallback: ArcGIS (often succeeds when Nominatim is down/blocked)
    if _arc_rate is not None:
        for q in queries:
            loc = _arc_rate(q)
            if loc:
                try:
                    lat, lon = float(loc.latitude), float(loc.longitude)
                    _geo_cache[cache_key] = (lat, lon)
                    return lat, lon, "arcgis"
                except Exception:
                    pass

    return None, None, "no_match"


# ---- Games normalization (unchanged behavior) ----
EXPECTED_GAME_COLS = [
    "id","name","type","game_type","rtp","volatility","bonus_frequency","min_bet",
    "advantage_play_potential","best_casino_type","bonus_trigger_clues",
    "tips","image_url","source_url","updated_at",
    "is_hidden","is_unavailable","score"
]

def _norm_games(df: pd.DataFrame) -> pd.DataFrame:
    df = (df or pd.DataFrame()).copy()
    if df.empty:
        return pd.DataFrame(columns=EXPECTED_GAME_COLS)
    # normalize column names
    newcols = []
    for c in df.columns:
        c2 = re.sub(r"\W+", "_", str(c).strip()).lower()
        newcols.append(c2)
    df.columns = newcols
    # ensure required columns
    for c in EXPECTED_GAME_COLS:
        if c not in df.columns:
            if c in ("is_hidden","is_unavailable"):
                df[c] = False
            else:
                df[c] = None
    # dtypes
    for b in ("is_hidden","is_unavailable"):
        if b in df.columns:
            df[b] = df[b].fillna(False).astype(bool)
    for n in ("rtp","bonus_frequency","min_bet","score"):
        if n in df.columns:
            df[n] = pd.to_numeric(df[n], errors="coerce")
    for n in ("volatility","advantage_play_potential"):
        if n in df.columns:
            df[n] = pd.to_numeric(df[n], errors="coerce").astype("Int64")
    # order
    lead = [c for c in EXPECTED_GAME_COLS if c in df.columns]
    rest = [c for c in df.columns if c not in lead]
    return df[lead + rest]


# ---- Supabase clients ----
def _client_service():
    """Service-role client (needed for writes and admin tasks)."""
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    # Also check Streamlit secrets (root and [general])
    if not url and hasattr(st, "secrets"):
        url = st.secrets.get("SUPABASE_URL") or st.secrets.get("general", {}).get("SUPABASE_URL")

    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key and hasattr(st, "secrets"):
        key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY") or st.secrets.get("general", {}).get("SUPABASE_SERVICE_ROLE_KEY")

    if create_client is None:
        st.error("Supabase client not installed. Add 'supabase', 'postgrest', 'gotrue' to requirements.txt.")
        return None
    if not (url and key):
        st.error("Admin requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Failed to init Supabase client: {e}")
        return None


# ---- Casinos helpers ----
def _fetch_casinos_df(c) -> pd.DataFrame:
    try:
        cols = "id,name,city,state,latitude,longitude,is_active,inserted_at,updated_at"
        res = c.table("casinos").select(cols).order("name").execute()
        df = pd.DataFrame(res.data or [])
        # ensure columns exist
        for col in ["city","state","latitude","longitude","is_active","inserted_at","updated_at"]:
            if col not in df.columns:
                if col in ("latitude","longitude"):
                    df[col] = None
                elif col == "is_active":
                    df[col] = True
                else:
                    df[col] = ""
        return df
    except Exception:
        return pd.DataFrame(columns=["id","name","city","state","latitude","longitude","is_active","inserted_at","updated_at"])


def _fetch_games(c) -> pd.DataFrame:
    try:
        res = c.table("games").select("*").execute()
        return _norm_games(pd.DataFrame(res.data or []))
    except Exception:
        return pd.DataFrame(columns=EXPECTED_GAME_COLS)


def _upsert_games(c, df: pd.DataFrame):
    rows = df.to_dict(orient="records")
    for i in range(0, len(rows), 400):
        c.table("games").upsert(rows[i:i+400]).execute()


# ---- Casino CRUD with auto‑geocoding ----
def _add_casino(c, name: str, city: str, state: str, is_active: bool=True):
    payload = {
        "name": (name or "").strip(),
        "city": (city or "").strip(),
        "state": (state or "").strip(),
        "is_active": bool(is_active),
    }
    lat, lon, provider = geocode_casino(payload["name"], payload["city"], payload["state"])
    if lat is not None and lon is not None:
        payload["latitude"] = lat
        payload["longitude"] = lon
    try:
        res = c.table("casinos").insert(payload).select("id").execute()
        return True, f"Casino added. {'(coords via '+provider+')' if lat is not None else ''}", (res.data[0]["id"] if res and res.data else None)
    except Exception as e:
        return False, f"Add failed: {e}", None


def _update_casino(c, cid: str, name: str|None=None, city: str|None=None, state: str|None=None,
                   is_active: bool|None=None, force_geocode: bool=False):
    """Update fields; auto‑geocode when city/state change or coords missing, or when force_geocode=True."""
    # Read current row to compare
    try:
        cur = c.table("casinos").select("name,city,state,latitude,longitude").eq("id", str(cid)).single().execute()
        cur_row = (cur.data or {}) if cur else {}
    except Exception:
        cur_row = {}

    payload = {}
    if name is not None: payload["name"] = (name or "").strip()
    if city is not None: payload["city"] = (city or "").strip()
    if state is not None: payload["state"] = (state or "").strip()
    if is_active is not None: payload["is_active"] = bool(is_active)

    # Determine if geocode is needed
    city_to_use  = payload.get("city",  cur_row.get("city"))
    state_to_use = payload.get("state", cur_row.get("state"))
    name_to_use  = payload.get("name",  cur_row.get("name"))
    city_changed = ("city" in payload and (payload["city"] or "") != (cur_row.get("city") or ""))
    state_changed = ("state" in payload and (payload["state"] or "") != (cur_row.get("state") or ""))
    missing_coords = (cur_row.get("latitude") is None) or (cur_row.get("longitude") is None)
    need_geo = force_geocode or city_changed or state_changed or missing_coords

    if need_geo and (city_to_use or state_to_use or name_to_use):
        lat, lon, _provider = geocode_casino(name_to_use or "", city_to_use or "", state_to_use or "")
        if lat is not None and lon is not None:
            payload["latitude"] = lat
            payload["longitude"] = lon

    if not payload:
        return True, "No changes."
    try:
        c.table("casinos").update(payload).eq("id", str(cid)).execute()
        return True, "Updated."
    except Exception as e:
        return False, f"Update failed: {e}"


# ---- Main Admin Panel ----
def show_admin_panel():
    st.subheader("🔧 Admin Panel")
    c = _client_service()
    if not c:
        return

    # ===== (1) Manage casinos (collapsed by default) =====
    with st.expander("🏷️ Manage casinos", expanded=False):
        st.caption("Add, edit, and archive casinos. City/State will auto‑fill coordinates when saved.")

        casinos_df = _fetch_casinos_df(c)

        # Add new casino row
        col1, col2, col3, col4, col5 = st.columns([3,2,1,1,1])
        with col1:
            new_name = st.text_input("Casino name", key="new_cas_name")
        with col2:
            new_city = st.text_input("City", key="new_cas_city")
        with col3:
            new_state = st.text_input("State", key="new_cas_state")
        with col4:
            new_active = st.checkbox("Active", value=True, key="new_cas_active")
        with col5:
            if st.button("➕ Add casino", use_container_width=True, key="btn_add_cas"):
                if not (new_name or "").strip():
                    st.warning("Enter a casino name.")
                else:
                    ok, msg, _ = _add_casino(c, new_name, new_city, new_state, new_active)
                    if ok:
                        st.success(msg)
                        # clear fields
                        for k in ("new_cas_name","new_cas_city","new_cas_state"):
                            if k in st.session_state: del st.session_state[k]
                        st.rerun()
                    else:
                        st.error(msg)

        st.divider()
        f1, f2 = st.columns([2,1])
        with f1:
            ftxt = st.text_input("Filter by name", key="cas_filter")
        with f2:
            only_active = st.checkbox("Show active only", value=False, key="cas_only_active")

        edit_df = casinos_df.copy()
        if (ftxt or "").strip():
            edit_df = edit_df[edit_df["name"].str.contains(ftxt, case=False, na=False)]
        if only_active and "is_active" in edit_df.columns:
            edit_df = edit_df[edit_df["is_active"] == True]

        if "is_active" not in edit_df.columns:
            edit_df["is_active"] = True
        # Leading "Off" column for compactness (Off = inactive)
        edit_df["Off"] = ~edit_df["is_active"].astype(bool)

        lead = [c for c in ["Off","name","city","state"] if c in edit_df.columns]
        rest = [c for c in ["is_active","latitude","longitude","id","inserted_at","updated_at"] if c in edit_df.columns]
        edit_df = edit_df[lead + rest]

        col_cfg = {
            "Off": st.column_config.CheckboxColumn("Off", help="Off = inactive", width="small"),
            "name": st.column_config.TextColumn("name", help="Unique name"),
            "city": st.column_config.TextColumn("city"),
            "state": st.column_config.TextColumn("state"),
        }
        # lat/lon are display-only; they auto-fill
        if "latitude" in edit_df.columns:
            col_cfg["latitude"] = st.column_config.NumberColumn("latitude", disabled=True)
        if "longitude" in edit_df.columns:
            col_cfg["longitude"] = st.column_config.NumberColumn("longitude", disabled=True)
        if "id" in edit_df.columns:
            col_cfg["id"] = st.column_config.TextColumn("id", disabled=True)
        if "inserted_at" in edit_df.columns:
            col_cfg["inserted_at"] = st.column_config.DatetimeColumn("inserted_at", disabled=True)
        if "updated_at" in edit_df.columns:
            col_cfg["updated_at"] = st.column_config.DatetimeColumn("updated_at", disabled=True)

        st.markdown("**Edit casinos**")
        edited = st.data_editor(
            edit_df, key="casinos_editor", use_container_width=True, hide_index=True, column_config=col_cfg
        )

        if st.button("💾 Save casino edits", key="btn_save_casinos"):
            try:
                changed = 0
                orig = {str(r["id"]): r for _, r in casinos_df.iterrows() if str(r.get("id") or "").strip()}
                for _, r in edited.iterrows():
                    cid = str(r.get("id") or "").strip()
                    if not cid:
                        continue
                    old = orig.get(cid, {})
                    new_name = r.get("name")
                    new_city = r.get("city") or ""
                    new_state = r.get("state") or ""
                    new_active = not bool(r.get("Off"))

                    if (
                        old.get("name") != new_name or
                        (old.get("city") or "") != new_city or
                        (old.get("state") or "") != new_state or
                        bool(old.get("is_active")) != new_active
                    ):
                        ok, msg = _update_casino(
                            c, cid, new_name, new_city, new_state, new_active,
                            # will geocode if city/state changed or coords missing
                            force_geocode=False
                        )
                        if not ok:
                            st.error(f"{msg} (casino: {new_name})")
                        else:
                            changed += 1
                st.success(f"Saved {changed} change(s).")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")

    # ===== (2) Upload / patch CSV into games =====
    with st.expander("📤 Upload / patch CSV into games", expanded=False):
        csv = st.file_uploader("Upload CSV to upsert into public.games", type=["csv"], key="upload_games_csv")
        if csv is not None:
            try:
                uploaded = pd.read_csv(csv)
                uploaded = _norm_games(uploaded)
                st.dataframe(uploaded.head(20), use_container_width=True)
                if st.button("Upsert uploaded CSV → games", key="btn_upsert_games"):
                    _upsert_games(c, uploaded)
                    st.success(f"Upserted {len(uploaded)} rows.")
            except Exception as e:
                st.error(f"Failed to process CSV: {e}")

    # ===== (3) Inline edit & save (games) =====
    with st.expander("📝 Inline edit & save (games)", expanded=False):
        games_df = _fetch_games(c)
        q = st.text_input("Quick filter (name contains)", "", key="games_inline_filter")
        df_edit = games_df.copy()
        if q.strip():
            df_edit = df_edit[df_edit["name"].str.contains(q, case=False, na=False)]

        # Put hidden/unavailable first, name third
        leading = [col for col in ["is_hidden","is_unavailable","name"] if col in df_edit.columns]
        trailing = [col for col in df_edit.columns if col not in leading]
        df_edit = df_edit[leading + trailing]

        col_cfg = {}
        if "is_hidden" in df_edit.columns:
            col_cfg["is_hidden"] = st.column_config.CheckboxColumn("is_hidden", help="Hide from recommendations")
        if "is_unavailable" in df_edit.columns:
            col_cfg["is_unavailable"] = st.column_config.CheckboxColumn("is_unavailable", help="Globally not playable")

        edited_games = st.data_editor(
            df_edit, key="games_editor", use_container_width=True, column_config=col_cfg, num_rows="dynamic"
        )
        if st.button("💾 Save edited games", key="btn_save_inline_games"):
            try:
                _upsert_games(c, _norm_games(edited_games))
                st.success("Game changes saved.")
            except Exception as e:
                st.error(f"Save failed: {e}")

    # ===== (4) Per‑casino availability =====
    with st.expander("🏨 Per‑casino availability", expanded=False):
        st.caption("Mark specific games unavailable at a selected casino. Unchecking removes them from that list.")

        casinos_df2 = _fetch_casinos_df(c)
        casino_names = casinos_df2["name"].dropna().astype(str).tolist()
        if not casino_names:
            st.warning("No casinos in table. Add some above.")
            return

        default_casino = st.session_state.get("trip_settings", {}).get("casino","")
        try:
            default_idx = casino_names.index(default_casino) if default_casino in casino_names else 0
        except Exception:
            default_idx = 0
        casino = st.selectbox("Casino", options=casino_names, index=default_idx, key="per_casino_select")

        # Left: add games by name with filter
        left, right = st.columns([2,1])
        with left:
            name_filter = st.text_input("Filter games by name", "", key="per_casino_game_filter")
            games_df_all = _fetch_games(c)
            if name_filter.strip():
                games_df_all = games_df_all[games_df_all["name"].str.contains(name_filter, case=False, na=False)]

            options = []
            if "id" in games_df_all.columns and "name" in games_df_all.columns:
                for _, r in games_df_all.iterrows():
                    gid = str(r["id"])
                    if gid and gid.lower() != "nan":
                        options.append((gid, r["name"]))
            options.sort(key=lambda x: (str(x[1]).lower(), str(x[0]).lower()))
            labels = {gid: f"{nm}  •  {gid[:8]}…" for gid, nm in options}
            ids = [gid for gid, _ in options]
            selected_ids = st.multiselect("Games", ids, format_func=lambda x: labels.get(x, str(x)), key="per_casino_add_ids")

        with right:
            unavailable_flag = st.checkbox("Mark as UNAVAILABLE", value=True, key="per_casino_unavail_flag")

        if st.button("➕ Add / update availability", key="btn_add_per_casino"):
            if not casino or not str(casino).strip():
                st.warning("Select a casino first.")
            elif not selected_ids:
                st.warning("Select at least one game.")
            else:
                try:
                    count = 0
                    for gid in selected_ids:
                        c.table("game_availability").delete().eq("game_id", str(gid)).ilike("casino", str(casino).strip()).execute()
                        c.table("game_availability").insert({
                            "game_id": str(gid),
                            "casino": str(casino).strip(),
                            "is_unavailable": bool(unavailable_flag)
                        }).execute()
                        count += 1
                    st.success(f"Updated availability for {count} game(s) at “{casino}”.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed saving availability: {e}")

        # Existing rows for this casino
        try:
            res = c.table("game_availability").select("*").ilike("casino", str(casino).strip()).order("updated_at", desc=True).execute()
            avail_df = pd.DataFrame(res.data or [])
        except Exception:
            avail_df = pd.DataFrame()

        if avail_df.empty:
            st.info("No per‑casino availability rows for this casino.")
        else:
            games_df_all = _fetch_games(c)
            name_map = {}
            if not games_df_all.empty and "id" in games_df_all.columns and "name" in games_df_all.columns:
                name_map = dict(zip(games_df_all["id"].astype(str), games_df_all["name"]))
            avail_df["game_id"] = avail_df.get("game_id", "").astype(str)
            avail_df["game_name"] = avail_df["game_id"].map(name_map).fillna("(unknown)")
            if "is_unavailable" not in avail_df.columns:
                avail_df["is_unavailable"] = True
            avail_df["is_unavailable"] = avail_df["is_unavailable"].astype(bool)

            lead = [c for c in ["game_name","is_unavailable"] if c in avail_df.columns]
            rest = [c for c in avail_df.columns if c not in lead]
            avail_df = avail_df[lead + rest]

            st.write(f"Current availability at “{casino}”")
            st.caption("Uncheck **is_unavailable** to remove a game from this casino’s unavailable list, then click **Save changes**.")
            edited_avail = st.data_editor(
                avail_df, key="per_casino_editor", use_container_width=True, hide_index=True,
                column_config={"is_unavailable": st.column_config.CheckboxColumn("is_unavailable")}
            )

            if st.button("💾 Save changes", key="btn_save_per_casino"):
                try:
                    to_delete = edited_avail[(~edited_avail["is_unavailable"].astype(bool))]
                    delete_count = 0
                    if not to_delete.empty:
                        if "id" in to_delete.columns:
                            for rid in to_delete["id"].dropna().astype(str).tolist():
                                c.table("game_availability").delete().eq("id", rid).execute()
                                delete_count += 1
                        else:
                            for _, r in to_delete.iterrows():
                                gid = str(r.get("game_id") or "").strip()
                                cas = str(r.get("casino") or "").strip() or casino
                                if gid and cas:
                                    c.table("game_availability").delete().eq("game_id", gid).ilike("casino", cas).execute()
                                    delete_count += 1
                    st.success(f"Saved. Removed {delete_count} game(s) from this casino’s unavailable list.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed saving changes: {e}")

    # ===== (5) 📍 Geocode casinos (auto‑fill lat/lon) =====
    with st.expander("📍 Geocode casinos (auto‑fill lat/lon)", expanded=False):
        if (Nominatim is None and ArcGIS is None) or RateLimiter is None:
            st.error("geopy or geocoders not installed. Add `geopy` to requirements.txt and redeploy.")
        else:
            _init_geocoders()
            if _nom_rate is None and _arc_rate is None:
                st.error("No geocoder available (Nominatim/ArcGIS init failed). Try again later.")

        st.caption("Uses Nominatim first, then ArcGIS as fallback. Writes only when values change.")

        def _is_missing(v):
            if v is None:
                return True
            if isinstance(v, str):
                return v.strip() == ""
            if isinstance(v, float) and math.isnan(v):
                return True
            return False

        df = _fetch_casinos_df(c)
        if df.empty:
            st.info("No casinos found.")
        else:
            df["needs_coords"] = df.apply(lambda r: _is_missing(r.get("latitude")) or _is_missing(r.get("longitude")), axis=1)
            missing = df[df["needs_coords"] == True]
            st.write(f"Casinos missing coords: **{len(missing)}**")
            st.button("↻ Re-scan", on_click=lambda: st.rerun(), key="geo_rescan_btn")

            options, labels = [], {}
            for _, r in df.iterrows():
                cid = str(r.get("id") or "")
                nm  = str(r.get("name") or "")
                city = r.get("city") or ""
                state = r.get("state") or ""
                lat, lon = r.get("latitude"), r.get("longitude")
                tag = f"{nm} — {city}, {state}".strip(" —,")
                if not _is_missing(lat) and not _is_missing(lon):
                    try:
                        tag += f"  (lat={float(lat):.5f}, lon={float(lon):.5f})"
                    except Exception:
                        pass
                labels[cid] = tag
                options.append(cid)

            default_ids = [str(x) for x in (missing["id"].dropna().astype(str).tolist()[:10])]
            selected = st.multiselect(
                "Select casinos to geocode",
                options=options,
                format_func=lambda cid: labels.get(cid, cid),
                default=default_ids,
                key="geo_selected_casinos",
            )

            force_country = st.checkbox("Force country = USA in lookup", value=True, key="geo_force_country")

            st.caption("Preview (first 10 selected):")
            st.dataframe(df[df["id"].astype(str).isin(selected)].head(10)[["name","city","state","latitude","longitude"]], use_container_width=True)

            def _geocode_and_update(ids: list[str], only_missing: bool) -> int:
                updated = 0
                for cid in ids:
                    row = df[df["id"].astype(str) == str(cid)]
                    if row.empty:
                        st.write(f"• skip: id {cid} not found")
                        continue
                    r = row.iloc[0]
                    nm   = r.get("name")
                    city = (r.get("city") or "").strip()
                    state = (r.get("state") or "").strip()

                    # Try name-based lookup if city/state blank
                    lat_new = lon_new = None
                    provider = ""
                    if city or state or nm:
                        lat_new, lon_new, provider = geocode_casino(nm or "", city, state, country=("USA" if force_country else ""))

                    if lat_new is None or lon_new is None:
                        st.write(f"• skip: {nm} — no match for “{(nm+', ') if nm else ''}{city}{(', '+state) if state else ''}{', USA' if force_country else ''}”")
                        continue

                    lat_old, lon_old = r.get("latitude"), r.get("longitude")
                    try:
                        if not _is_missing(lat_old) and not _is_missing(lon_old):
                            if float(lat_old) == float(lat_new) and float(lon_old) == float(lon_new):
                                st.write(f"• skip: {nm} — coords unchanged")
                                continue
                    except Exception:
                        pass

                    try:
                        # primary write
                        resp = c.table("casinos").update(
                            {"latitude": float(lat_new), "longitude": float(lon_new)}
                        ).eq("id", str(cid)).execute()

                        # upsert fallback (some deployments don’t return data on update)
                        if not getattr(resp, "data", None):
                            c.table("casinos").upsert({
                                "id": str(cid),
                                "latitude": float(lat_new),
                                "longitude": float(lon_new),
                            }).execute()

                        # verify
                        check = c.table("casinos").select("latitude,longitude").eq("id", str(cid)).single().execute()
                        lat_chk = (check.data or {}).get("latitude")
                        lon_chk = (check.data or {}).get("longitude")
                        if lat_chk is None or lon_chk is None:
                            st.write(f"• failed to persist: {nm} — wrote lat={lat_new:.5f}, lon={lon_new:.5f}, but readback is NULL")
                        else:
                            st.write(f"• updated: {nm} → lat={float(lat_chk):.5f}, lon={float(lon_chk):.5f}  ({provider})")
                            updated += 1
                    except Exception as e:
                        st.write(f"• failed: {nm} — {e}")
                return updated

            c1, c2 = st.columns([1,1])
            with c1:
                if st.button("Geocode selected", key="btn_geo_selected"):
                    if not selected:
                        st.warning("Pick at least one casino.")
                    else:
                        n = _geocode_and_update(selected, only_missing=False)
                        st.success(f"Geocoded {n} casino(s).")
                        st.rerun()
            with c2:
                if st.button("Geocode ALL missing", key="btn_geo_all_missing"):
                    ids_missing = df[df["needs_coords"] == True]["id"].dropna().astype(str).tolist()
                    if not ids_missing:
                        st.info("Nothing to do — no missing coordinates.")
                    else:
                        n = _geocode_and_update(ids_missing, only_missing=True)
                        st.success(f"Geocoded {n} casino(s).")
                        st.rerun()