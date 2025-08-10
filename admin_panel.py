from __future__ import annotations

import os
import re
import pandas as pd
import streamlit as st

# --- Supabase client (service role) ---
try:
    from supabase import create_client
except Exception:
    create_client = None

from data_loader_supabase import get_casinos

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

# -------- Games helpers --------
def _fetch_all_games(client) -> pd.DataFrame:
    res = client.table("games").select("*").execute()
    data = res.data or []
    return _norm_cols(pd.DataFrame(data))

def _upsert_games_df(client, df: pd.DataFrame):
    rows = df.to_dict(orient="records")
    for i in range(0, len(rows), 400):
        client.table("games").upsert(rows[i:i+400]).execute()

def _score_row(row, default_bankroll=200.0):
    rtp = float(row.get("rtp") or 0)
    adv = float(row.get("advantage_play_potential") or 0)
    vol = float(row.get("volatility") or 0)
    min_bet = float(row.get("min_bet") or 0)
    rtp_n = max(0.0, min(1.0, (rtp - 85.0) / (99.9 - 85.0))) if rtp else 0.0
    adv_n = max(0.0, min(1.0, adv / 5.0)) if adv else 0.0
    vol_pen = max(0.0, min(1.0, (5.0 - vol) / 5.0)) if vol else 0.5
    minbet_pen = 1.0
    if default_bankroll > 0:
        ratio = min_bet / default_bankroll if min_bet else 0.0
        minbet_pen = 1.0 - max(0.0, ratio - 0.03) * 6.0
        minbet_pen = max(0.0, min(1.0, minbet_pen))
    raw = (0.45 * rtp_n) + (0.35 * adv_n) + (0.20 * vol_pen)
    return round(raw * minbet_pen * 100.0, 1)

def _safe_uuid(x):
    s = str(x).strip()
    return s if s and s.lower() != "nan" else None

# -------- Casinos helpers --------
def _fetch_casinos(client) -> pd.DataFrame:
    try:
        res = client.table("casinos").select("*").order("name").execute()
        data = res.data or []
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame(columns=["id","name","is_active","inserted_at","updated_at"])
        if "is_active" not in df.columns:
            df["is_active"] = True
        return df[["id","name","is_active","inserted_at","updated_at"]]
    except Exception:
        return pd.DataFrame(columns=["id","name","is_active","inserted_at","updated_at"])

def _add_casino(client, name: str, is_active: bool = True) -> tuple[bool,str]:
    try:
        client.table("casinos").insert({"name": name.strip(), "is_active": bool(is_active)}).execute()
        return True, "Casino added."
    except Exception as e:
        return False, f"Add failed: {e}"

def _update_casino(client, cid: str, name: str | None = None, is_active: bool | None = None) -> tuple[bool,str]:
    try:
        payload = {}
        if name is not None:
            payload["name"] = name.strip()
        if is_active is not None:
            payload["is_active"] = bool(is_active)
        if not payload:
            return True, "No changes."
        client.table("casinos").update(payload).eq("id", str(cid)).execute()
        return True, "Updated."
    except Exception as e:
        return False, f"Update failed: {e}"

# -------- UI --------
def show_admin_panel():
    st.subheader("🔧 Admin Panel")
    client = _admin_client()
    if not client:
        return

    # ---------- One-time resets from previous run (before any widgets) ----------
    if st.session_state.get("_reset_new_casino_name"):
        st.session_state["_reset_new_casino_name"] = False
        st.session_state.pop("new_casino_name", None)

    # Load once so all sections can use it
    games_df = _fetch_all_games(client)
    st.caption(f"Loaded {len(games_df)} rows from public.games")

    # =========================
    # 0) Manage casinos
    # =========================
    with st.expander("🏷️ Manage casinos", expanded=False):
        st.caption("Add, rename, and activate/archive casinos used throughout the app.")
        casinos_df = _fetch_casinos(client)

        # Add new casino
        st.markdown("**Add new casino**")
        c1, c2, c3 = st.columns([3,1,1])
        with c1:
            new_name = st.text_input("Casino name", key="new_casino_name")
        with c2:
            new_active = st.checkbox("Active", value=True, key="new_casino_active")
        with c3:
            if st.button("➕ Add casino", use_container_width=True, key="btn_add_casino"):
                if not (new_name or "").strip():
                    st.warning("Enter a casino name.")
                else:
                    ok, msg = _add_casino(client, new_name, new_active)
                    if ok:
                        st.success(msg)
                        # Trigger clearing the input on the next run (safe with widget keys)
                        st.session_state["_reset_new_casino_name"] = True
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

        # Put editable columns first
        lead = [c for c in ["name","is_active"] if c in edit_df.columns]
        rest = [c for c in ["id","inserted_at","updated_at"] if c in edit_df.columns]
        edit_df = edit_df[lead + rest]

        col_cfg = {
            "id": st.column_config.TextColumn("id", help="Primary key", disabled=True),
            "inserted_at": st.column_config.DatetimeColumn("inserted_at", disabled=True),
            "updated_at": st.column_config.DatetimeColumn("updated_at", disabled=True),
            "name": st.column_config.TextColumn("name", help="Displayed name (must be unique, case-insensitive)"),
            "is_active": st.column_config.CheckboxColumn("is_active", help="Uncheck to archive (hide from pickers)")
        }

        st.markdown("**Edit casinos**")
        edited_casinos = st.data_editor(
            edit_df,
            key="casinos_editor",
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg
        )

        # Save edits (rename / toggle active)
        if st.button("💾 Save edits", key="btn_save_casinos"):
            try:
                updated = 0
                orig_by_id = {str(r["id"]): r for _, r in casinos_df.iterrows() if str(r.get("id") or "").strip()}
                for _, row in edited_casinos.iterrows():
                    cid = str(row.get("id") or "").strip()
                    if not cid:
                        continue
                    original = orig_by_id.get(cid, {})
                    new_name = row.get("name")
                    new_active = bool(row.get("is_active"))
                    if (original.get("name") != new_name) or (bool(original.get("is_active")) != new_active):
                        ok, msg = _update_casino(client, cid, new_name, new_active)
                        if not ok:
                            st.error(f"{msg} (casino: {new_name})")
                        else:
                            updated += 1
                st.success(f"Saved {updated} change(s).")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save edits: {e}")

    # =========================
    # 1) Upload / patch CSV into games
    # =========================
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

    # =========================
    # 2) Inline edit & save (games)
    # =========================
    with st.expander("📝 Inline edit & save (games: checkboxes first, name third)", expanded=False):
        q = st.text_input("Quick filter (name contains):", "", key="inline_filter")
        df_edit = games_df.copy()
        if q.strip():
            df_edit = df_edit[df_edit["name"].str.contains(q, case=False, na=False)]

        leading = [c for c in ["is_hidden","is_unavailable","name"] if c in df_edit.columns]
        trailing = [c for c in df_edit.columns if c not in leading]
        ordered_cols = leading + trailing
        df_edit = df_edit[ordered_cols]

        col_cfg = {}
        if "is_hidden" in df_edit.columns:
            col_cfg["is_hidden"] = st.column_config.CheckboxColumn(
                "is_hidden", help="Hide from recommendations", default=False
            )
        if "is_unavailable" in df_edit.columns:
            col_cfg["is_unavailable"] = st.column_config.CheckboxColumn(
                "is_unavailable", help="Not playable globally / skip", default=False
            )

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
                _upsert_games_df(client, _norm_cols(edited_ui))
                st.success("Changes saved.")
            except Exception as e:
                st.error(f"Save failed: {e}")

    # =========================
    # 3) Per‑casino availability (delete-then-insert to respect unique index)
    # =========================
    with st.expander("🏨 Per‑casino availability", expanded=False):
        st.caption("Mark games unavailable at a specific casino (does not affect other casinos).")

        casinos = get_casinos()
        casinos = [c for c in casinos if c.strip() and c != "Other..."]
        if not casinos:
            st.warning("No casinos found. Create entries in public.casinos first.")
            casino = st.text_input("Casino name (temporary input)")
        else:
            default_casino = st.session_state.trip_settings.get("casino","")
            try:
                default_idx = casinos.index(default_casino) if default_casino in casinos else 0
            except Exception:
                default_idx = 0
            casino = st.selectbox("Casino", options=casinos, index=default_idx, key="casino_select")

        # Add to unavailable list
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
                casino_norm = str(casino).strip()
                try:
                    count = 0
                    for gid in selected_ids:
                        client.table("game_availability").delete() \
                              .eq("game_id", str(gid)) \
                              .ilike("casino", casino_norm) \
                              .execute()
                        client.table("game_availability").insert({
                            "game_id": str(gid),
                            "casino": casino_norm,
                            "is_unavailable": bool(unavailable_flag)
                        }).execute()
                        count += 1
                    st.success(f"Updated availability for {count} game(s) at “{casino_norm}”.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed saving availability: {e}")

        # Editable grid (game name first; uncheck to remove)
        if casino and str(casino).strip():
            try:
                res = client.table("game_availability") \
                            .select("*") \
                            .ilike("casino", str(casino).strip()) \
                            .order("updated_at", desc=True) \
                            .execute()
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
                            "is_unavailable": st.column_config.CheckboxColumn(
                                "is_unavailable", help="If unchecked, row will be removed."
                            )
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
                                            client.table("game_availability").delete() \
                                                  .eq("game_id", gid).ilike("casino", cas).execute()
                                            delete_count += 1
                            st.success(f"Saved. Removed {delete_count} game(s) from this casino’s unavailable list.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed saving changes: {e}")
            except Exception as e:
                st.error(f"Failed to load per‑casino availability: {e}")

    # =========================
    # 4) Recalculate & save scores (games)
    # =========================
    with st.expander("🧮 Recalculate & save scores (games)", expanded=False):
        default_bankroll = st.number_input("Assume default bankroll for penalty math ($)", value=200.0, step=50.0, key="score_bankroll")
        if st.button("Recalculate 'score' for all (filtered via per‑section tools)", key="btn_recalc_scores"):
            try:
                tmp = games_df.copy()
                if "id" not in tmp.columns:
                    st.error("No 'id' column available to save scores.")
                else:
                    tmp["score"] = tmp.apply(lambda r: _score_row(r, default_bankroll=default_bankroll), axis=1)
                    client.table("games").upsert(tmp[["id","score"]].to_dict(orient="records")).execute()
                    st.success("Scores recalculated and saved to 'score'.")
            except Exception as e:
                st.error(f"Score update failed: {e}")