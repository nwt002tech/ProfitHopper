from __future__ import annotations

import os
import re
import pandas as pd
import streamlit as st

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

def _fetch_all(client) -> pd.DataFrame:
    res = client.table("games").select("*").execute()
    data = res.data or []
    return _norm_cols(pd.DataFrame(data))

def _upsert_df(client, df: pd.DataFrame):
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

def show_admin_panel():
    st.subheader("🔧 Admin Panel")

    client = _admin_client()
    if not client:
        return

    df = _fetch_all(client)
    st.write(f"Rows in DB: {len(df)}")

    # -- Upload / Upsert CSV --
    st.header("Upload/patch from CSV")
    csv = st.file_uploader("Upload CSV to upsert into public.games", type=["csv"])
    if csv is not None:
        try:
            uploaded = pd.read_csv(csv)
            uploaded = _norm_cols(uploaded)
            st.dataframe(uploaded.head(20), use_container_width=True)
            if st.button("Upsert uploaded CSV → Supabase"):
                _upsert_df(client, uploaded)
                st.success(f"Upserted {len(uploaded)} rows.")
        except Exception as e:
            st.error(f"Failed to process CSV: {e}")

    st.divider()

    # -- Inline edit & save (checkboxes first, name third) --
    st.header("Inline edit & save")
    q = st.text_input("Quick filter (name contains):", "")
    df_edit = df.copy()
    if q.strip():
        df_edit = df_edit[df_edit["name"].str.contains(q, case=False, na=False)]

    leading = [c for c in ["is_hidden","is_unavailable","name"] if c in df_edit.columns]
    trailing = [c for c in df_edit.columns if c not in leading]
    ordered_cols = leading + trailing
    df_edit = df_edit[ordered_cols]

    col_cfg = {}
    if "is_hidden" in df_edit.columns:
        col_cfg["is_hidden"] = st.column_config.CheckboxColumn("is_hidden", help="Hide from recommendations", default=False)
    if "is_unavailable" in df_edit.columns:
        col_cfg["is_unavailable"] = st.column_config.CheckboxColumn("is_unavailable", help="Not playable globally / skip", default=False)

    edited_default = df_edit.copy()
    edited_ui = st.data_editor(
        df_edit,
        num_rows="dynamic",
        use_container_width=True,
        key="admin_editor",
        column_order=ordered_cols,
        column_config=col_cfg
    )
    edited = edited_ui if isinstance(edited_ui, pd.DataFrame) else edited_default

    if st.button("Save edited rows"):
        try:
            _upsert_df(client, _norm_cols(edited))
            st.success("Changes saved.")
        except Exception as e:
            st.error(f"Save failed: {e}")

    st.divider()

    # -- Per‑casino availability (searchable dropdown + editable grid) --
    st.header("Per‑casino availability")
    st.caption("Mark games unavailable at the selected casino only (does not affect other casinos).")

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
        casino = st.selectbox("Casino", options=casinos, index=default_idx)

    left, right = st.columns([2,1])
    with left:
        st.write("Add games to this casino's unavailable list:")
        options = []
        if "id" in edited.columns and "name" in edited.columns:
            for _, r in edited.iterrows():
                gid = _safe_uuid(r["id"])
                if gid:
                    options.append((gid, r["name"]))
        # sort by game name, then id for stable UX
        options.sort(key=lambda x: (str(x[1]).lower(), str(x[0]).lower()))
        labels = {gid: f"{name} ({gid[:8]}…)" for gid, name in options}
        ids = [gid for gid, _ in options]
        selected_ids = st.multiselect("Games", ids, format_func=lambda x: labels.get(x, str(x)))
    with right:
        unavailable_flag = st.checkbox("Mark as UNAVAILABLE at this casino", value=True)

    if st.button("Add / update availability"):
        if not casino or not str(casino).strip():
            st.warning("Select a casino first.")
        elif not selected_ids:
            st.warning("Select at least one game.")
        else:
            rows = [{"game_id": gid, "casino": str(casino).strip(), "is_unavailable": bool(unavailable_flag)} for gid in selected_ids]
            try:
                client.table("game_availability").upsert(rows).execute()
                st.success(f"Updated availability for {len(rows)} game(s) at “{str(casino).strip()}”.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed saving availability: {e}")

    # -- Editable grid of current availability (game_name first, uncheck to remove) --
    if casino and str(casino).strip():
        try:
            res = client.table("game_availability") \
                        .select("*") \
                        .ilike("casino", str(casino).strip()) \
                        .order("updated_at", desc=True) \
                        .execute()
            avail_rows = res.data or []
            avail_df = pd.DataFrame(avail_rows)

            if not avail_df.empty:
                # map game_id -> name from df
                name_by_id = {}
                if "id" in df.columns and "name" in df.columns:
                    name_by_id = dict(zip(df["id"].astype(str), df["name"]))

                if "game_id" in avail_df.columns:
                    avail_df["game_id"] = avail_df["game_id"].astype(str)
                    avail_df["game_name"] = avail_df["game_id"].map(name_by_id).fillna("(unknown)")

                if "is_unavailable" not in avail_df.columns:
                    avail_df["is_unavailable"] = True
                avail_df["is_unavailable"] = avail_df["is_unavailable"].astype(bool)

                lead = [c for c in ["game_name", "is_unavailable"] if c in avail_df.columns]
                rest = [c for c in avail_df.columns if c not in lead]
                avail_df = avail_df[lead + rest]

                st.subheader(f"Current availability at “{str(casino).strip()}”")
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

                if st.button("💾 Save changes", key="save_per_casino_changes"):
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
            else:
                st.info("No per‑casino availability rows found for this casino.")
        except Exception as e:
            st.error(f"Failed to load per‑casino availability: {e}")

    st.divider()

    # -- Recalculate scores --
    st.header("Recalculate and save scores (optional)")
    default_bankroll = st.number_input("Assume default bankroll for penalty math ($)", value=200.0, step=50.0)
    if st.button("Recalculate 'score' for current filtered rows"):
        try:
            tmp = edited.copy()
            if "id" not in tmp.columns:
                st.error("No 'id' column available to save scores.")
            else:
                tmp["score"] = tmp.apply(lambda r: _score_row(r, default_bankroll=default_bankroll), axis=1)
                client.table("games").upsert(tmp[["id","score"]].to_dict(orient="records")).execute()
                st.success("Scores recalculated and saved to 'score'.")
        except Exception as e:
            st.error(f"Score update failed: {e}")