
# admin_panel.py
import os
import re
import streamlit as st

try:
    from supabase import create_client
except Exception:
    create_client = None

EXPECTED_COLS = [
    "id","name","type","game_type","rtp","volatility","bonus_frequency","min_bet",
    "advantage_play_potential","best_casino_type","bonus_trigger_clues",
    "tips","image_url","source_url","updated_at",
    "is_hidden","is_unavailable","score"
]

def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\W+","_",c.strip()).lower() for c in df.columns]
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


def show_admin_panel():
    st.subheader("🔧 Admin Panel")

    client = _admin_client()
    if not client:
        return

    df = _fetch_all(client)
    st.write(f"Rows in DB: {len(df)}")

    # Upload / Upsert
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

    # Inline edit
    st.header("Inline edit & save")
    q = st.text_input("Quick filter (name contains):", "")
    df_edit = df.copy()
    if q.strip():
        df_edit = df_edit[df_edit["name"].str.contains(q, case=False, na=False)]
    edited = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True, key="admin_editor")
    if st.button("Save edited rows"):
        try:
            _upsert_df(client, _norm_cols(edited))
            st.success("Changes saved.")
        except Exception as e:
            st.error(f"Save failed: {e}")

    st.divider()

    # Bulk flags
    st.header("Bulk flags: hidden / unavailable")
    if isinstance(edited, pd.DataFrame) and "id" in edited.columns:
        ids = edited["id"].tolist()
    else:
        ids = df_edit.get("id", []).tolist() if hasattr(df_edit, 'get') else []
    if ids:
        selection = st.multiselect("Select rows by ID", ids)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Mark selected: is_hidden = true"):
                _upsert_df(client, pd.DataFrame([{"id": i, "is_hidden": True} for i in selection]))
                st.success(f"Updated {len(selection)} rows.")
        with col2:
            if st.button("Mark selected: is_unavailable = true"):
                _upsert_df(client, pd.DataFrame([{"id": i, "is_unavailable": True} for i in selection]))
                st.success(f"Updated {len(selection)} rows.")
        with col3:
            if st.button("Clear flags on selected"):
                _upsert_df(client, pd.DataFrame([{"id": i, "is_hidden": False, "is_unavailable": False} for i in selection]))
                st.success(f"Updated {len(selection)} rows.")

    st.divider()

    # Recalc score
    st.header("Recalculate and save scores (optional)")
    default_bankroll = st.number_input("Assume default bankroll for penalty math ($)", value=200.0, step=50.0)
    if st.button("Recalculate 'score' for filtered set"):
        try:
            tmp = (edited if isinstance(edited, pd.DataFrame) else df_edit).copy()
            tmp["score"] = tmp.apply(lambda r: _score_row(r, default_bankroll=default_bankroll), axis=1)
            _upsert_df(client, _norm_cols(tmp[["id","score"]]))
            st.success("Scores recalculated and saved to 'score'.")
        except Exception as e:
            st.error(f"Score update failed: {e}")
