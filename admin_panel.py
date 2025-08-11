from __future__ import annotations

import os
import re
import pandas as pd
import streamlit as st

# Supabase client (service role for writes)
try:
    from supabase import create_client
except Exception:
    create_client = None

# Use only get_casinos_full (do NOT import get_casinos)
try:
    from data_loader_supabase import get_casinos_full
except Exception:
    get_casinos_full = None


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
    # normalize names
    newcols = []
    for c in df.columns:
        c2 = re.sub(r"\W+", "_", str(c).strip()).lower()
        newcols.append(c2)
    df.columns = newcols
    # required columns
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

def _client_service():
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not create_client:
        st.error("Supabase client not installed.")
        return None
    if not (url and key):
        st.error("Admin requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Failed to init Supabase client: {e}")
        return None

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

def _fetch_casinos_df() -> pd.DataFrame:
    if get_casinos_full is None:
        return pd.DataFrame(columns=["id","name","city","state","is_active","inserted_at","updated_at"])
    try:
        df = get_casinos_full(active_only=False)
        # ensure expected columns
        for col in ["city","state","is_active","inserted_at","updated_at"]:
            if col not in df.columns:
                df[col] = "" if col in ("city","state") else (True if col=="is_active" else None)
        keep = ["id","name","city","state","is_active","inserted_at","updated_at"]
        return df[[c for c in keep if c in df.columns]].copy()
    except Exception:
        return pd.DataFrame(columns=["id","name","city","state","is_active","inserted_at","updated_at"])

def _add_casino(c, name: str, city: str, state: str, is_active: bool=True):
    try:
        res = c.table("casinos").insert({
            "name": name.strip(),
            "city": (city or "").strip(),
            "state": (state or "").strip(),
            "is_active": bool(is_active),
        }).select("id").execute()
        return True, "Casino added.", (res.data[0]["id"] if res and res.data else None)
    except Exception as e:
        return False, f"Add failed: {e}", None

def _update_casino(c, cid: str, name: str|None=None, city: str|None=None, state: str|None=None, is_active: bool|None=None):
    try:
        payload = {}
        if name is not None: payload["name"] = name.strip()
        if city is not None: payload["city"] = (city or "").strip()
        if state is not None: payload["state"] = (state or "").strip()
        if is_active is not None: payload["is_active"] = bool(is_active)
        if not payload: return True, "No changes."
        c.table("casinos").update(payload).eq("id", str(cid)).execute()
        return True, "Updated."
    except Exception as e:
        return False, f"Update failed: {e}"

def show_admin_panel():
    st.subheader("🔧 Admin Panel")
    c = _client_service()
    if not c:
        return

    # ===== (1) Manage casinos (collapsed by default) =====
    with st.expander("🏷️ Manage casinos", expanded=False):
        st.caption("Add, edit, and archive casinos. Toggle Off to mark inactive.")

        casinos_df = _fetch_casinos_df()

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
        # Leading "Off" column for compactness
        edit_df["Off"] = ~edit_df["is_active"].astype(bool)

        lead = [c for c in ["Off","name","city","state"] if c in edit_df.columns]
        rest = [c for c in ["is_active","id","inserted_at","updated_at"] if c in edit_df.columns]
        edit_df = edit_df[lead + rest]

        col_cfg = {
            "Off": st.column_config.CheckboxColumn("Off", help="Off = inactive", width="small"),
            "name": st.column_config.TextColumn("name", help="Unique name"),
            "city": st.column_config.TextColumn("city"),
            "state": st.column_config.TextColumn("state"),
        }
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
                        ok, msg = _update_casino(c, cid, new_name, new_city, new_state, new_active)
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

        # Casino select (from casinos table only)
        casinos_df2 = _fetch_casinos_df()
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
            # Map game_id -> name, show name first column
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
                        # Prefer primary key if present
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