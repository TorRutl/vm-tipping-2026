from __future__ import annotations

import html
import time
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from live_data import get_live_actual
from score import DATA_DIR, STAGE_LABELS, STAGE_ORDER, score_all

st.set_page_config(page_title="VM-tipping 2026", page_icon="🏆", layout="wide")

STAGE_SHORT = {
    "16_delsfinale": "16-dels",
    "8_delsfinale": "8-dels",
    "kvartfinale": "Kvart",
    "semifinale": "Semi",
    "finalist": "Finalistar",
    "vm_vinnar": "Vinnar",
    "solv": "2. plass",
    "bronse": "3. plass",
    "toppscorer": "Toppscorar",
}

@st.cache_data(ttl=300, show_spinner=False)
def load_live():
    return get_live_actual()

def actual_set(actual: pd.DataFrame, stage: str) -> set[str]:
    return set(actual.loc[actual["stage"] == stage, "actual"].dropna().astype(str))

def bracket_html(person: pd.DataFrame, actual: pd.DataFrame) -> str:
    def cards(stage: str, title: str) -> str:
        known = actual_set(actual, stage)
        picks = person[person["stage"] == stage].sort_values("slot")
        parts = [f'<section><h3>{html.escape(title)}</h3><div class="cards">']
        if picks.empty:
            parts.append('<div class="empty">Ingen tips</div>')
        for _, row in picks.iterrows():
            code = str(row["pick"])
            name = str(row["pick_name"])
            if code in known:
                css, symbol, label = "ok", "✓", "Riktig"
            elif not known:
                css, symbol, label = "pending", "•", "Ikkje avgjort"
            else:
                css, symbol, label = "wrong", "×", "Feil"
            parts.append(
                f'<div class="card {css}"><div class="line"><b>{html.escape(code)}</b>'
                f'<strong>{symbol}</strong></div><small>{html.escape(name)}</small>'
                f'<span>{label}</span></div>'
            )
        parts.append("</div></section>")
        return "".join(parts)

    body = (
        cards("16_delsfinale", "16-delsfinale")
        + cards("8_delsfinale", "8-delsfinale")
        + cards("kvartfinale", "Kvartfinale")
        + '<div class="stack">'
        + cards("semifinale", "Semifinale")
        + cards("finalist", "Finalistar")
        + '</div><div class="stack">'
        + cards("vm_vinnar", "VM-vinnar")
        + cards("solv", "2. plass")
        + cards("bronse", "3. plass")
        + cards("toppscorer", "Toppscorar")
        + "</div>"
    )

    return f"""
    <style>
    body{{background:#0e1117;color:#fafafa;font-family:system-ui;margin:0}}
    .legend{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}}
    .legend span{{padding:5px 10px;border:1px solid #3a3f4b;border-radius:999px}}
    .board{{display:grid;grid-template-columns:2.2fr 1.6fr 1.2fr 1fr 1fr;gap:14px;align-items:start}}
    h3{{margin:0 0 8px;font-size:19px}}
    .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(85px,1fr));gap:7px}}
    .card{{background:#171a22;border:1px solid #343947;border-radius:10px;padding:8px;min-height:65px}}
    .card.ok{{border-color:#2ecc71;background:rgba(46,204,113,.14)}}
    .card.wrong{{border-color:#e74c3c;background:rgba(231,76,60,.12);opacity:.72}}
    .card.pending{{border-color:#f1c40f;background:rgba(241,196,15,.10)}}
    .line{{display:flex;justify-content:space-between;font-size:16px}}
    small{{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:4px}}
    .card span{{display:block;font-size:11px;opacity:.7;margin-top:5px}}
    .stack{{display:grid;gap:14px}}
    .empty{{padding:10px;border:1px dashed #444;border-radius:8px;opacity:.65}}
    @media(max-width:900px){{.board{{grid-template-columns:1fr}}}}
    </style>
    <div class="legend"><span>✓ Riktig</span><span>× Feil</span><span>• Ikkje avgjort</span></div>
    <div class="board">{body}</div>
    """

with st.sidebar:
    st.header("Live")
    if st.button("🔄 Hent på nytt no", use_container_width=True):
        load_live.clear()
        st.rerun()
    auto = st.toggle("Oppdater sida automatisk", value=False)
    seconds = st.selectbox("Intervall", [60, 120, 300], index=2)

if "refreshed_at" not in st.session_state:
    st.session_state.refreshed_at = time.time()
if auto and time.time() - st.session_state.refreshed_at > seconds:
    st.session_state.refreshed_at = time.time()
    load_live.clear()
    st.rerun()

live = load_live()
actual = live.actual
board, details = score_all(actual)

st.title("🏆 VM-tipping 2026")
st.caption("Live-versjon: resultat blir henta i minnet. Appen skriv ikkje over CSV-filer i skyen.")

if live.source == "fotmob":
    st.success(live.message)
else:
    st.warning(live.message + " Brukar trygg baseline.")

if board.empty:
    st.error("Fann ingen tips.")
    st.stop()

leader_score = int(board.iloc[0]["total"])
leaders = board.loc[board["total"] == leader_score, "name"].tolist()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leiar", ", ".join(leaders))
c2.metric("Poeng", leader_score)
if "Torstein" in set(board["name"]):
    tor = board[board["name"] == "Torstein"].iloc[0]
    c3.metric("Torstein", int(tor["total"]), f"Plass {int(tor['plass'])}")
    c4.metric("Bak leiar", int(tor["bak_leiar"]))
else:
    c3.metric("Deltakarar", len(board))
    c4.metric("Fasitlinjer", len(actual))

tabs = st.tabs(["🏁 Teten", "👤 Deltakar", "✅ Fasit", "⚙️ Diagnostikk"])

with tabs[0]:
    cols = ["plass", "name", "total"] + STAGE_ORDER + ["bak_leiar"]
    rename = {"plass":"Plass","name":"Namn","total":"Sum","bak_leiar":"Bak leiar"}
    rename.update({s: STAGE_SHORT[s] for s in STAGE_ORDER})
    st.dataframe(board[cols].rename(columns=rename), use_container_width=True, hide_index=True)

with tabs[1]:
    names = list(board["name"])
    default = names.index("Torstein") if "Torstein" in names else 0
    selected = st.selectbox("Vel deltakar", names, index=default)
    row = board[board["name"] == selected].iloc[0]
    a, b, c = st.columns(3)
    a.metric("Poeng", int(row["total"]))
    b.metric("Plass", int(row["plass"]))
    c.metric("Bak leiar", int(row["bak_leiar"]))

    person = details[details["name"] == selected]
    visual, table = st.tabs(["Sluttspelvisning", "Tips-tabell"])
    with visual:
        components.html(bracket_html(person, actual), height=950, scrolling=True)
    with table:
        st.dataframe(
            person[["stage_label","slot","pick","pick_name","status","points"]]
            .rename(columns={
                "stage_label":"Runde","slot":"Nr","pick":"Kode",
                "pick_name":"Tips","status":"Status","points":"Poeng"
            }),
            use_container_width=True,
            hide_index=True,
        )

with tabs[2]:
    counts = actual.groupby("stage").size().reindex(STAGE_ORDER, fill_value=0).reset_index(name="Antal")
    counts["Runde"] = counts["stage"].map(STAGE_LABELS)
    st.dataframe(counts[["Runde","Antal"]], use_container_width=True, hide_index=True)
    st.dataframe(
        actual[["stage","slot","actual","actual_name"]].rename(columns={
            "stage":"Runde","slot":"Nr","actual":"Kode","actual_name":"Lag"
        }),
        use_container_width=True,
        hide_index=True,
    )

with tabs[3]:
    st.write("Kjelde:", live.source)
    st.write("Melding:", live.message)
    st.write("FotMob-rundelabelar som vart funne:")
    st.code("\n".join(live.labels_found) if live.labels_found else "Ingen")
    st.write("Poengreglar:")
    st.dataframe(pd.read_csv(DATA_DIR / "points.csv"), use_container_width=True, hide_index=True)
