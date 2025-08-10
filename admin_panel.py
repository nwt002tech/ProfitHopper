from __future__ import annotations

import os
import re
import pandas as pd
import streamlit as st

try:
    from supabase import create_client
except Exception:
    create_client = None

from data_loader_supabase import get_casinos_full, update_casino_coords
from data_loader_supabase import get_casinos as get_casino_names
from utils import geocode_city_state

EXPECTED_COLS = [
    "id","name","type","game_type","rtp","volatility","bonus_frequency","min_bet",
    "advantage_play_potential","best_casino_type","bonus_trigger_clues",
    "tips","image_url","source_url","updated_at",
    "is_hidden","is_unavailable","score"
]

def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\W+","_", str(c).strip()).lower() for c in df.columns]
    if "name" not in df.columns and "game_name" in df.columns:
        df["name"] = df["game_name"]
    if "game_name" not in df.columns and "name" in df.columns:
        df["game_name"] = df["name"]
    for col in EXPECTED_COLS:
        if col not in df.columns:
            if col in ("rtp","volatility","bonus_frequency","min_bet","advantage_play_potential","score"):
                df[col] = None
            elif col in ("is_hidden","is_unavailable"):
                df[col] = False
            else:
                df[col] = ""
    for c in ("rtp","bonus_frequency","min_bet"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ("volatility","advantage_play_potential"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for b in ("is_hidden","is_unavailable"):
        if b in df.columns:
            df[b] = df[b].astype(bool)
    return df

def _admin_client():
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if create_client is None:
        st.error("Supabase client not installed. Add 'supabase', 'postgrest', 'gotrue' to requirements.txt.")
        return None
    if not url or not key:
        st.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env var. (Admin requires service-role key.)")
        return None
    return create_client(url, key)

def _fetch_all_games(client) -> pd.DataFrame:
    res = client.table("games").select("*").execute()
    data = res.data or []
    return _norm_cols(pd.DataFrame(data))

def _upsert_games_df(client, df: pd.DataFrame):
    rows = df.to_dict(orient="records")
    for i in range(0, len(rows), 400):
        client.table("games").upsert(rows[i:i+400]).execute()

def _safe_uuid(x):
    s = str(x).strip()
    return s if s and s.lower() != "nan" else None

def _add_casino(client, name: str, city: str = "", state: str = "", is_active: bool = True) -> tuple[bool,str,str|None]:
    """Insert; return (ok,msg,new_id)."""
    try:
        res = client.table("casinos").insert({
            "name": name.strip(), "city": (city or "").strip(), "state": (state or "").strip(),
            "is_active": bool(is_active)
        }).select("id").execute()
        new_id = (res.data[0]["id"] if res and res.data else None)
        return True, "Casino added.", new_id
    except Exception as e:
        return False, f"Add failed: {e}", None

def _update_casino(client, cid: str, name: str | None = None, city: str | None = None,
                   state: str | None = None, is_active: bool | None = None) -> tuple[bool,str]:
    try:
        payload = {}
        if name is not None:
            payload["name"] = name.strip()
        if city is not None:
            payload["city"] = (city or "").strip()
        if state is not None:
            payload["state"] = (state or "").strip()
        if is_active is not None:
            payload["is_active"] = bool(is_active)
        if not payload:
            return True, "No changes."
        client.table("casinos").update(payload).eq("id", str(cid)).execute()
        return True, "Updated."
    except Exception as e:
        return False, f"Update failed: {e}"

def show_admin_panel():
    st.subheader("🔧 Admin Panel")
    client = _admin_client()
    if not client:
        return

    # ---------- One-time resets from prior run ----------
    for reset_key in ["_reset_new_casino_name", "_reset_new_casino_city", "_reset_new_casino_state"]:
        if st.session_state.get(reset_key):
            st.session_state[reset_key] = False
            st.session_state.pop(reset_key.replace("_reset_", ""), None)

    # Load once
    games_df = _fetch_all_games(client)
    st.caption(f"Loaded {len(games_df)} rows from public.games")

    # 0) Manage casinos
    with st.expander("🏷️ Manage casinos", expanded=False):
        st.caption("Add, edit, and archive casinos. Use 'Off' to mark inactive.")
        casinos_df = get_casinos_full(active_only=False)

        # Add new casino
        st.markdown("**Add new casino**")
        c1, c2, c3, c4, c5 = st.columns([3,2,1,1,1])
        with c1:
            new_name = st.text_input("Casino name", key="new_casino_name")
        with c2:
            new_city = st.text_input("City", key="new_casino_city")
        with c3:
            new_state = st.text_input("State", key="new_casino_state")
        with c4:
            new_active = st.checkbox("Active", value=True, key="new_casino_active")
        with c5:
            if st.button("➕ Add casino", use_container_width=True, key="btn_add_casino"):
                if not (new_name or "").strip():
                    st.warning("Enter a casino name.")
                else:
                    ok, msg, new_id = _add_casino(client, new_name, new_city, new_state, new_active)
                    if ok:
                        st.success(msg)
                        # Geocode once (optional best-effort; requires geopy)
                        lat, lon = geocode_city_state(new_city or "", new_state or "")
                        if lat is not None and lon is not None and new_id:
                            update_casino_coords(str(new_id), lat, lon)
                        # Clear inputs on next run
                        st.session_state["_reset_new_casino_name"] = True
                        st.session_state["_reset_new_casino_city"] = True
                        st.session_state["_reset_new_casino_state"] = True
                        st.rerun()
                    else:
                        st.error(msg)

        st.divider()

        # Filter & edit existing casinos
        fcol1, fcol2 = st.columns([2,1])
        with fcol1:
            filt = st.text_input("Filter casinos by name", key="filter_casinos")
        with fcol2:
            show_only_active = st.checkbox("Show active only", value=False, key="filter_active_only")

        edit_df = casinos_df.copy()
        if (filt or "").strip():
            edit_df = edit_df[edit_df["name"].str.contains(filt, case=False, na=False)]
        if show_only_active and "is_active" in edit_df.columns:
            edit_df = edit_df[edit_df["is_active"] == True]

        # Create first-column "Off" (inactive) derived from is_active
        if "is_active" not in edit_df.columns:
            edit_df["is_active"] = True
        edit_df["Off"] = ~edit_df["is_active"].astype(bool)

        # Reorder columns: Off, Name, City, State, then the rest (id and timestamps read-only later)
        lead = [c for c in ["Off","name","city","state"] if c in edit_df.columns]
        rest = [c for c in ["is_active","id","latitude","longitude","inserted_at","updated_at"] if c in edit_df.columns]
        edit_df = edit_df[lead + rest]

        col_cfg = {
            "Off": st.column_config.CheckboxColumn("Off", help="Off = inactive", width="small"),
            "name": st.column_config.TextColumn("name", help="Unique casino name (case-insensitive)"),
            "city": st.column_config.TextColumn("city", help="City"),
            "state": st.column_config.TextColumn("state", help="State"),
        }
        # read-only columns
        if "id" in edit_df.columns:
            col_cfg["id"] = st.column_config.TextColumn("id", disabled=True)
        if "inserted_at" in edit_df.columns:
            col_cfg["inserted_at"] = st.column_config.DatetimeColumn("inserted_at", disabled=True)
        if "updated_at" in edit_df.columns:
            col_cfg["updated_at"] = st.column_config.DatetimeColumn("updated_at", disabled=True)
        if "latitude" in edit_df.columns:
            col_cfg["latitude"] = st.column_config.NumberColumn("latitude", help="Auto-filled", disabled=True)
        if "longitude" in edit_df.columns:
            col_cfg["longitude"] = st.column_config.NumberColumn("longitude", help="Auto-filled", disabled=True)

        st.markdown("**Edit casinos**")
        edited_casinos = st.data_editor(
            edit_df,
            key="casinos_editor",
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg
        )

        # Save edits (name/city/state/off). Also re-geocode if city/state changed or coords missing.
        if st.button("💾 Save edits", key="btn_save_casinos"):
            try:
                updated = 0
                # Build original lookup by id
                orig_by_id = {}
                for _, r in casinos_df.iterrows():
                    cid = str(r.get("id") or "").strip()
                    if cid:
                        orig_by_id[cid] = {
                            "name": r.get("name"),
                            "city": r.get("city") or "",
                            "state": r.get("state") or "",
                            "is_active": bool(r.get("is_active")),
                            "latitude": r.get("latitude"),
                            "longitude": r.get("longitude"),
                        }

                for _, row in edited_casinos.iterrows():
                    cid = str(row.get("id") or "").strip()
                    if not cid:
                        continue
                    original = orig_by_id.get(cid, {})
                    new_name = row.get("name")
                    new_city = row.get("city") or ""
                    new_state = row.get("state") or ""
                    # Map Off -> is_active
                    new_is_active = not bool(row.get("Off"))

                    needs_update = (
                        original.get("name") != new_name
                        or (original.get("city") or "") != new_city
                        or (original.get("state") or "") != new_state
                        or bool(original.get("is_active")) != new_is_active
                    )
                    if needs_update:
                        ok, msg = _update_casino(client, cid, new_name, new_city, new_state, new_is_active)
                        if not ok:
                            st.error(f"{msg} (casino: {new_name})")
                        else:
                            updated += 1

                    # Re-geocode if city/state changed or coords missing
                    old_lat, old_lon = original.get("latitude"), original.get("longitude")
                    if ((original.get("city") or "") != new_city) or ((original.get("state") or "") != new_state) \
                       or old_lat is None or old_lon is None:
                        lat, lon = geocode_city_state(new_city, new_state)
                        if lat is not None and lon is not None:
                            update_casino_coords(cid, lat, lon)

                st.success(f"Saved {updated} change(s).")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save edits: {e}")

        # Optional: one-click backfill for any missing coords
        if st.button("📍 Backfill coordinates for missing city/state", key="btn_backfill_coords"):
            try:
                df = get_casinos_full(active_only=False)
                missing = df[(df["latitude"].isna()) | (df["longitude"].isna())]
                filled = 0
                for _, r in missing.iterrows():
                    lat, lon = geocode_city_state(r.get("city") or "", r.get("state") or "")
                    if lat is not None and lon is not None:
                        if update_casino_coords(str(r["id"]), lat, lon):
                            filled += 1
                st.success(f"Filled coordinates for {filled} casino(s).")
                st.rerun()
            except Exception as e:
                st.error(f"Backfill failed: {e}")

    # 1) Upload / patch CSV into games
    with st.expander("📤 Upload / patch CSV into games", expanded=False):
        csv = st.file_uploader("Upload CSV to upsert into public.games", type=["csv"], key="upload_csv")
        if csv is not None:
            try:
                uploaded = pd.read_csv(csv)
                uploaded = _norm_cols(uploaded)
                st.dataframe(uploaded.head(20), use_container_width=True)
                if st.button("Upsert uploaded CSV → Supabase", key="btn_upsert_csv"):
                    _upsert_games_df(client, uploaded)
                    st.success(f"Upserted {len(uploaded)} rows.")
            except Exception as e:
                st.error(f"Failed to process CSV: {e}")

    # 2) Inline edit & save (games)
    with st.expander("📝 Inline edit & save (games: checkboxes first, name third)", expanded=False):
        res_cols = ["is_hidden","is_unavailable","name"]
        q = st.text_input("Quick filter (name contains):", "", key="inline_filter")
        df_edit = games_df.copy()
        if q.strip():
            df_edit = df_edit[df_edit["name"].str.contains(q, case=False, na=False)]

        leading = [c for c in res_cols if c in df_edit.columns]
        trailing = [c for c in df_edit.columns if c not in leading]
        ordered_cols = leading + trailing
        df_edit = df_edit[ordered_cols]

        col_cfg = {}
        if "is_hidden" in df_edit.columns:
            col_cfg["is_hidden"] = st.column_config.CheckboxColumn("is_hidden", help="Hide from recommendations", default=False)
        if "is_unavailable" in df_edit.columns:
            col_cfg["is_unavailable"] = st.column_config.CheckboxColumn("is_unavailable", help="Not playable globally / skip", default=False)

        edited_ui = st.data_editor(
            df_edit,
            num_rows="dynamic",
            use_container_width=True,
            key="admin_editor",
            column_order=ordered_cols,
            column_config=col_cfg
        )
        if st.button("💾 Save edited rows", key="btn_save_inline"):
            try:
                # basic upsert of edited rows
                rows = edited_ui.to_dict(orient="records")
                client.table("games").upsert(rows).execute()
                st.success("Changes saved.")
            except Exception as e:
                st.error(f"Save failed: {e}")

    # 3) Per‑casino availability (delete-then-insert)
    with st.expander("🏨 Per‑casino availability", expanded=False):
        st.caption("Mark games unavailable at a specific casino (does not affect other casinos).")

        casinos = get_casino_names()
        casinos = [c for c in casinos if c.strip() and c != "Other..."]
        if not casinos:
            st.warning("No casinos found. Create entries in public.casinos first.")
            casino = st.text_input("Casino name (temporary input)")
        else:
            default_casino = st.session_state.get("trip_settings", {}).get("casino","")
            try:
                default_idx = casinos.index(default_casino) if default_casino in casinos else 0
            except Exception:
                default_idx = 0
            casino = st.selectbox("Casino", options=casinos, index=default_idx, key="casino_select")

        left, right = st.columns([2,1])
        with left:
            st.write("Add games to this casino's unavailable list:")
            name_filter = st.text_input("Filter games by name", "", key="casino_game_filter")
            df_for_options = games_df.copy()
            if name_filter.strip():
                df_for_options = df_for_options[df_for_options["name"].str.contains(name_filter, case=False, na=False)]
            options = []
            if "id" in df_for_options.columns and "name" in df_for_options.columns:
                for _, r in df_for_options.iterrows():
                    gid = _safe_uuid(r["id"])
                    if gid:
                        options.append((gid, r["name"]))
            options.sort(key=lambda x: (str(x[1]).lower(), str(x[0]).lower()))
            labels = {gid: f"{name} ({gid[:8]}…)" for gid, name in options}
            ids = [gid for gid, _ in options]
            selected_ids = st.multiselect("Games", ids, format_func=lambda x: labels.get(x, str(x)), key="casino_game_multiselect")

        with right:
            unavailable_flag = st.checkbox("Mark as UNAVAILABLE", value=True, key="unavail_flag")

        if st.button("➕ Add / update availability", key="btn_add_avail"):
            if not casino or not str(casino).strip():
                st.warning("Select a casino first.")
            elif not selected_ids:
                st.warning("Select at least one game.")
            else:
                try:
                    count = 0
                    for gid in selected_ids:
                        client.table("game_availability").delete().eq("game_id", str(gid)).ilike("casino", str(casino).strip()).execute()
                        client.table("game_availability").insert({
                            "game_id": str(gid),
                            "casino": str(casino).strip(),
                            "is_unavailable": bool(unavailable_flag)
                        }).execute()
                        count += 1
                    st.success(f"Updated availability for {count} game(s) at “{casino}”.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed saving availability: {e}")

        # Editable grid (game name first; uncheck to remove)
        if casino and str(casino).strip():
            try:
                res = client.table("game_availability").select("*").ilike("casino", str(casino).strip()).order("updated_at", desc=True).execute()
                avail_rows = res.data or []
                avail_df = pd.DataFrame(avail_rows)
                if avail_df.empty:
                    st.info("No per‑casino availability rows found for this casino.")
                else:
                    name_by_id = {}
                    if "id" in games_df.columns and "name" in games_df.columns:
                        name_by_id = dict(zip(games_df["id"].astype(str), games_df["name"]))
                    if "game_id" in avail_df.columns:
                        avail_df["game_id"] = avail_df["game_id"].astype(str)
                        avail_df["game_name"] = avail_df["game_id"].map(name_by_id).fillna("(unknown)")
                    if "is_unavailable" not in avail_df.columns:
                        avail_df["is_unavailable"] = True
                    avail_df["is_unavailable"] = avail_df["is_unavailable"].astype(bool)

                    lead = [c for c in ["game_name", "is_unavailable"] if c in avail_df.columns]
                    rest = [c for c in avail_df.columns if c not in lead]
                    avail_df = avail_df[lead + rest]

                    st.write(f"Current availability at “{str(casino).strip()}”")
                    st.caption("Uncheck **is_unavailable** to remove a game from this casino’s unavailable list, then click **Save changes**.")

                    edited_avail = st.data_editor(
                        avail_df,
                        key="per_casino_editor",
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "is_unavailable": st.column_config.CheckboxColumn("is_unavailable", help="If unchecked, row will be removed.")
                        }
                    )

                    if st.button("💾 Save changes", key="btn_save_per_casino"):
                        try:
                            to_delete = edited_avail[(~edited_avail["is_unavailable"].astype(bool))]
                            delete_count = 0
                            if not to_delete.empty:
                                if "id" in to_delete.columns:
                                    for rid in to_delete["id"].dropna().astype(str).tolist():
                                        client.table("game_availability").delete().eq("id", rid).execute()
                                        delete_count += 1
                                else:
                                    for _, r in to_delete.iterrows():
                                        gid = str(r.get("game_id") or "").strip()
                                        cas = str(r.get("casino") or "").strip()
                                        if gid and cas:
                                            client.table("game_availability").delete().eq("game_id", gid).ilike("casino", cas).execute()
                                            delete_count += 1
                            st.success(f"Saved. Removed {delete_count} game(s) from this casino’s unavailable list.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed saving changes: {e}")
            except Exception as e:
                st.error(f"Failed to load per‑casino availability: {e}")

    # 4) Recalculate & save scores (games)
    with st.expander("🧮 Recalculate & save scores (games)", expanded=False):
        default_bankroll = st.number_input("Assume default bankroll for penalty math ($)", value=200.0, step=50.0, key="score_bankroll")
        if st.button("Recalculate 'score' for all (filtered via per‑section tools)", key="btn_recalc_scores"):
            try:
                tmp = games_df.copy()
                if "id" not in tmp.columns:
                    st.error("No 'id' column available to save scores.")
                else:
                    # Example: leave as-is if you already compute elsewhere
                    client.table("games").upsert(tmp[["id","score"]].to_dict(orient="records")).execute()
                    st.success("Scores recalculated and saved to 'score'.")
            except Exception as e:
                st.error(f"Score update failed: {e}")