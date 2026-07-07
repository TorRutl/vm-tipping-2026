from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from score import DATA_DIR, STAGE_LABELS, STAGE_ORDER, score_all
try:
    from update_results_fotmob import main as update_fotmob_results
except Exception:
    update_fotmob_results = None

st.set_page_config(page_title="VM-tipping 2026", layout="wide")

STAGE_POINTS = {
    "16_delsfinale": 1,
    "8_delsfinale": 2,
    "kvartfinale": 3,
    "semifinale": 4,
    "finalist": 5,
    "vm_vinnar": 3,
    "solv": 2,
    "bronse": 1,
    "toppscorer": 3,
}

STAGE_SHORT = {
    "16_delsfinale": "16-dels",
    "8_delsfinale": "8-dels",
    "kvartfinale": "Kvart",
    "semifinale": "Semi",
    "finalist": "Finalist",
    "vm_vinnar": "VM",
    "solv": "Sølv",
    "bronse": "Bronse",
    "toppscorer": "Toppscorar",
}

def read_actual() -> pd.DataFrame:
    path = DATA_DIR / "actual.csv"
    if not path.exists():
        return pd.DataFrame(columns=["stage", "slot", "actual", "actual_name"])
    return pd.read_csv(path)

def actual_set(stage: str) -> set[str]:
    actual = read_actual()
    if actual.empty:
        return set()
    return set(actual.loc[actual["stage"] == stage, "actual"].dropna().astype(str))

def score_data():
    leaderboard, details = score_all(DATA_DIR)
    board = pd.DataFrame(leaderboard)
    details_df = pd.DataFrame(details)

    if board.empty:
        return board, details_df

    board = board.sort_values(["total", "name"], ascending=[False, True]).reset_index(drop=True)
    board["Plassering"] = board["total"].rank(method="min", ascending=False).astype(int)
    board["Bak leiar"] = int(board.iloc[0]["total"]) - board["total"]
    return board, details_df

def person_alive_count(name: str, details_df: pd.DataFrame) -> int:
    df = details_df[details_df["name"] == name]
    alive = 0
    for _, r in df.iterrows():
        stage = r["stage"]
        code = str(r["pick"])
        aset = actual_set(stage)
        if len(aset) == 0:
            # framtidig runde: tel som "i live" viss laget ikkje alt er slått ut frå turneringa
            alive += 1
        elif code in aset:
            alive += 1
    return alive

def html_escape(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

def card_html(code: str, name: str, cls: str, mark: str, label: str) -> str:
    return (
        f'<div class="pick-card {cls}">'
        f'<div class="topline"><span class="code">{html_escape(code)}</span><span class="mark">{mark}</span></div>'
        f'<div class="team">{html_escape(name)}</div>'
        f'<div class="status">{label}</div>'
        f'</div>'
    )

def cards_for(person_df: pd.DataFrame, stage: str, title: str) -> str:
    aset = actual_set(stage)
    sub = person_df[person_df["stage"] == stage].sort_values("slot")
    out = [f'<section class="round"><h3>{html_escape(title)}</h3><div class="cards">']
    if sub.empty:
        out.append('<div class="empty">Ingen tips</div>')
    for _, r in sub.iterrows():
        code = str(r["pick"])
        name = str(r["pick_name"])
        if code in aset:
            cls, mark, label = "ok", "✓", "Riktig"
        elif len(aset) == 0:
            cls, mark, label = "pending", "•", "Ikkje avgjort"
        else:
            cls, mark, label = "wrong", "×", "Feil"
        out.append(card_html(code, name, cls, mark, label))
    out.append("</div></section>")
    return "\n".join(out)

def visual_bracket(person_name: str, details_df: pd.DataFrame):
    person_df = details_df[details_df["name"] == person_name].copy()

    html = """
    <!doctype html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
    html,body{margin:0;padding:0;background:#0e1117;color:#fafafa;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    .wrap{padding:8px}
    .legend{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;font-size:14px}
    .pill{border-radius:999px;padding:5px 10px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12)}
    .board{display:grid;grid-template-columns:2.25fr 1.65fr 1.2fr .95fr .95fr;gap:16px;align-items:start}
    .round h3{margin:0 0 8px 0;font-size:20px;color:#fff}
    .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(82px,1fr));gap:8px}
    .pick-card{border:1px solid rgba(255,255,255,.18);background:#171a22;border-radius:11px;min-height:70px;padding:8px;box-sizing:border-box;box-shadow:0 1px 0 rgba(255,255,255,.05) inset}
    .pick-card.ok{border-color:rgba(46,204,113,.95);background:linear-gradient(180deg,rgba(46,204,113,.22),rgba(46,204,113,.10))}
    .pick-card.wrong{border-color:rgba(231,76,60,.95);background:linear-gradient(180deg,rgba(231,76,60,.22),rgba(231,76,60,.10));opacity:.76}
    .pick-card.pending{border-color:rgba(241,196,15,.9);background:linear-gradient(180deg,rgba(241,196,15,.16),rgba(241,196,15,.07))}
    .topline{display:flex;justify-content:space-between;align-items:center;font-weight:800;letter-spacing:.4px;font-size:16px}
    .mark{font-size:19px;line-height:1}
    .team{font-size:12px;opacity:.88;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .status{font-size:11px;opacity:.7;margin-top:6px}
    .mini-stack{display:grid;gap:14px}
    .empty{padding:12px;color:rgba(255,255,255,.6);border:1px dashed rgba(255,255,255,.18);border-radius:10px}
    @media(max-width:1000px){.board{grid-template-columns:1fr}}
    </style>
    </head>
    <body><div class="wrap">
    <div class="legend"><span class="pill">✓ Riktig</span><span class="pill">× Feil</span><span class="pill">• Ikkje avgjort</span></div>
    <div class="board">
    """
    html += cards_for(person_df, "16_delsfinale", "16-delsfinale")
    html += cards_for(person_df, "8_delsfinale", "8-delsfinale")
    html += cards_for(person_df, "kvartfinale", "Kvartfinale")
    html += '<div class="mini-stack">'
    html += cards_for(person_df, "semifinale", "Semifinale")
    html += cards_for(person_df, "finalist", "Finalistar")
    html += '</div><div class="mini-stack">'
    html += cards_for(person_df, "vm_vinnar", "VM-vinnar")
    html += cards_for(person_df, "solv", "Sølv")
    html += cards_for(person_df, "bronse", "Bronse")
    html += cards_for(person_df, "toppscorer", "Toppscorar")
    html += "</div></div></div></body></html>"

    components.html(html, height=900, scrolling=True)

def delta_since_last_update(details_df: pd.DataFrame) -> pd.DataFrame:
    """Enkel visning: siste runde med fasit viser kven som fekk poeng der."""
    actual = read_actual()
    stages_with_actual = [s for s in STAGE_ORDER if s in set(actual["stage"]) and len(actual_set(s)) > 0]
    if not stages_with_actual:
        return pd.DataFrame()
    latest = stages_with_actual[-1]
    df = details_df[details_df["stage"] == latest].copy()
    if df.empty:
        return pd.DataFrame()
    return (
        df.groupby("name", as_index=False)["points"]
        .sum()
        .sort_values(["points", "name"], ascending=[False, True])
        .rename(columns={"name": "Namn", "points": f"Poeng i {STAGE_SHORT.get(latest, latest)}"})
    )

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Oppdatering")
    auto_fetch = st.toggle("Hent FotMob automatisk", value=True)
    auto_refresh = st.toggle("Auto-refresh av sida", value=False)
    interval = st.number_input("Auto-refresh-intervall i sekund", min_value=30, max_value=900, value=120, step=30)

    if st.button("Hent siste resultat frå FotMob no"):
        if update_fotmob_results is not None:
            with st.spinner("Hentar frå FotMob..."):
                try:
                    update_fotmob_results()
                    st.success("Fasit oppdatert.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Klarte ikkje hente frå FotMob: {e}")
        else:
            st.error("Fant ikkje update_results_fotmob.py")

    if st.button("Oppdater sida no"):
        st.rerun()

    st.caption("På mobil: opne berre nettsida. Når automatisk FotMob-henting er på, oppdaterer appen fasiten sjølv.")

@st.cache_data(ttl=300, show_spinner=False)
def cached_fotmob_update():
    if update_fotmob_results is None:
        return "Fant ikkje update_results_fotmob.py"
    try:
        update_fotmob_results()
        return "OK"
    except Exception as e:
        return f"FEIL: {e}"

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if auto_fetch:
    result = cached_fotmob_update()
    if result != "OK":
        st.sidebar.warning(result)

if auto_refresh and time.time() - st.session_state.last_refresh > interval:
    st.session_state.last_refresh = time.time()
    st.rerun()

# ---------- Data ----------
board, details_df = score_data()
actual = read_actual()

st.title("🏆 VM-tipping 2026")
st.caption("Live poengtavle basert på tipsa de har levert. Sissel og Eli er hoppa over. Cloud-versjon: opnast frå mobil og kan hente FotMob automatisk.")

if board.empty:
    st.error("Fann ingen poengdata.")
    st.stop()

leader_score = int(board.iloc[0]["total"])
leaders = board.loc[board["total"] == leader_score, "name"].tolist()

# ---------- Dashboard ----------
st.subheader("Live status")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Leiar", ", ".join(leaders), f"{leader_score} poeng")
c2.metric("Delt leiing", len(leaders))
if "Torstein" in set(board["name"]):
    tor = board[board["name"] == "Torstein"].iloc[0]
    c3.metric("Torstein", f"{int(tor['total'])} p", f"Plass {int(tor['Plassering'])}")
    c4.metric("Bak leiar", int(tor["Bak leiar"]))
else:
    c3.metric("Deltakarar", len(board))
    c4.metric("Rundar med fasit", actual["stage"].nunique() if not actual.empty else 0)

st.subheader("🥇 Teten akkurat no")
top_n = st.slider("Vis topp", 3, len(board), min(10, len(board)))
top = board.head(top_n)[["Plassering", "name", "total", "Bak leiar"]].rename(
    columns={"Plassering": "Plass", "name": "Namn", "total": "Poeng"}
)
st.dataframe(top, use_container_width=True, hide_index=True)

st.subheader("📊 Poeng per runde")
show_cols = ["Plassering", "name", "total"] + STAGE_ORDER + ["Bak leiar"]
rename = {"Plassering": "Plass", "name": "Namn", "total": "Sum"}
rename.update({s: STAGE_SHORT.get(s, s) for s in STAGE_ORDER})
st.dataframe(board[show_cols].rename(columns=rename), use_container_width=True, hide_index=True)

st.subheader("🔥 Flest tips framleis i live / riktige")
alive_rows = []
for name in board["name"]:
    alive_rows.append({"Namn": name, "I live/riktige": person_alive_count(name, details_df)})
alive_df = pd.DataFrame(alive_rows).sort_values(["I live/riktige", "Namn"], ascending=[False, True]).head(10)
st.dataframe(alive_df, use_container_width=True, hide_index=True)

delta = delta_since_last_update(details_df)
if not delta.empty:
    st.subheader("⚽ Poeng i siste oppdaterte runde")
    st.dataframe(delta, use_container_width=True, hide_index=True)

st.divider()

# ---------- Person view ----------
st.subheader("👤 Deltakarvisning")
names = list(board["name"])
default_index = names.index("Torstein") if "Torstein" in names else 0
selected = st.selectbox("Vel deltakar", names, index=default_index)

selected_row = board[board["name"] == selected].iloc[0]
m1, m2, m3 = st.columns(3)
m1.metric("Poeng", int(selected_row["total"]))
m2.metric("Plass", int(selected_row["Plassering"]))
m3.metric("Bak leiar", int(selected_row["Bak leiar"]))

tab_visual, tab_table, tab_fasit, tab_rules = st.tabs(["Sluttspelvisning", "Tips-tabell", "Fasit", "Poengreglar"])

with tab_visual:
    visual_bracket(selected, details_df)

with tab_table:
    person = details_df[details_df["name"] == selected].copy()
    st.dataframe(
        person[["stage_label", "slot", "pick", "pick_name", "correct", "points"]]
        .rename(columns={
            "stage_label": "Runde",
            "slot": "Nr",
            "pick": "Kode",
            "pick_name": "Tips",
            "correct": "Riktig",
            "points": "Poeng",
        }),
        use_container_width=True,
        hide_index=True,
    )

with tab_fasit:
    if actual.empty:
        st.info("Ingen fasit ligg inne enno.")
    else:
        counts = actual.groupby("stage").size().reset_index(name="Antal fasitlinjer")
        st.dataframe(counts.rename(columns={"stage": "Runde"}), use_container_width=True, hide_index=True)
        st.dataframe(
            actual[["stage", "slot", "actual", "actual_name"]].rename(columns={
                "stage": "Runde",
                "slot": "Nr",
                "actual": "Kode",
                "actual_name": "Lag",
            }),
            use_container_width=True,
            hide_index=True,
        )

with tab_rules:
    points = pd.read_csv(DATA_DIR / "points.csv")
    labels = {
        "16_delsfinale": "16-delsfinale",
        "8_delsfinale": "8-delsfinale",
        "kvartfinale": "Kvartfinale",
        "semifinale": "Semifinale",
        "finalist": "Finalist",
        "vm_vinnar": "VM-vinnar",
        "solv": "2. plass / sølv",
        "bronse": "3. plass / bronse",
        "toppscorer": "Toppscorar",
    }
    points["Runde"] = points["stage"].map(labels)
    st.dataframe(
        points[["Runde", "points_per_correct"]].rename(columns={"points_per_correct": "Poeng per riktig"}),
        use_container_width=True,
        hide_index=True,
    )
