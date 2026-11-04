"""Shared data loading, labels and styling for the Streamlit app."""

from datetime import date
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import re

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

ROLE_LABELS = {
    "ST": "Striker", "W/AM": "Winger / Attacking midfielder", "CM": "Central midfielder",
    "DM": "Defensive midfielder", "FB": "Full-back", "CB": "Centre-back",
}

SHORT_LABELS = {
    "Gls_p90": "Goals", "G-PK_p90": "Non-penalty goals", "Ast_p90": "Assists",
    "Sh_p90": "Shots", "SoT_p90": "Shots on target", "SoT%": "Shot accuracy (%)",
    "G/Sh": "Finishing", "Crs_p90": "Crosses", "Fld_p90": "Fouls drawn",
    "Off_p90": "Offsides", "TklW_p90": "Tackles won", "Int_p90": "Interceptions",
    "Fls_p90": "Few fouls", "CrdY_p90": "Few cards", "+/-90": "Goal difference",
}

BAND_COLORS = {"Below average (0-33)": "#d9a441",
               "Average (34-66)": "#5a6778",
               "Strong (67-100)": "#4c8fd9"}

PLAYER_COLORS = ["#4c8fd9", "#d4b03c", "#c3ccd8"]

FIT_SCORE_HELP = ("Weighted average of the player's percentiles on the stats you prioritise, "
                  "compared with players in the same role. 0-100. Not an overall rating "
                  "or a probability of success.")
FORM_HELP = "2026-27 so far. Small sample: treat as an early signal, not a full-season verdict"
SIMILARITY_HELP = ("Profile similarity score: How close two players' percentile profiles are. "
                   "Use it to rank matches, not as a percentage of likeness.")
DATA_CREDIT = "Data: [FBref.com](https://fbref.com) (Betway Premiership player stats)."


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3,
.stApp input, .stApp button, .stApp textarea,
[data-testid="stMarkdownContainer"] {font-family: 'IBM Plex Sans', sans-serif;}
.block-container {padding-top: 3.5rem; max-width: 1360px;}
h1, h2, h3 {letter-spacing: -0.01em; color: #e8ecf2;}
.mono {font-family: 'IBM Plex Mono', monospace;}

.hero {padding: 4px 0 18px 0; margin-bottom: 1rem;}
.hero .kicker {color: #d4b03c; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
               text-transform: uppercase; margin-bottom: 6px;}
.hero h1 {color: #e8ecf2; margin: 0 0 0.35rem 0; font-size: 2rem; padding: 0;}
.hero p {color: #93a0b2; margin: 0; font-size: 0.95rem; line-height: 1.5;}

.cards {display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 14px; margin: 0.4rem 0 1.4rem 0;}
.card {background: #161c25; border: 1px solid #232b37; border-radius: 14px; padding: 16px 18px;}
.card .label {font-size: 0.78rem; color: #93a0b2;}
.card .value {font-family: 'IBM Plex Mono', monospace; font-size: 1.6rem; font-weight: 600;
              color: #e8ecf2; margin-top: 4px; line-height: 1.2;}
.card .note {font-size: 0.8rem; color: #93a0b2; margin-top: 4px; line-height: 1.4;}

.pill {display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 0.75rem;
       font-weight: 600; margin-right: 6px;}
.pill.ok {background: #17324f; color: #a9cbf2;}
.pill.warn {background: #3a3112; color: #ecd27a;}
.pill.muted {background: #222b37; color: #c3ccd8;}

.player-head {background: #161c25; border: 1px solid #232b37; border-radius: 14px;
              padding: 24px 26px; margin-bottom: 1rem;}
.player-head .name {font-size: 2rem; font-weight: 700; color: #e8ecf2;}
.player-head .meta {color: #b6c1d0; margin: 4px 0 10px 0; font-size: 0.95rem;}

.pick {background: #161c25; border: 1px solid #232b37; border-top: 3px solid #4c8fd9;
       border-radius: 14px; padding: 18px 20px; height: 100%;}
.pick.first {border-top-color: #d4b03c;}
.pick .rank {font-size: 0.78rem; color: #4c8fd9; font-weight: 700;}
.pick.first .rank {color: #d4b03c;}
.pick .name {font-size: 1.15rem; font-weight: 700; color: #e8ecf2; margin-top: 6px;}
.pick .meta {font-size: 0.85rem; color: #93a0b2; margin-bottom: 10px;}
.pick .score {font-family: 'IBM Plex Mono', monospace; font-size: 2.1rem; font-weight: 600;
              color: #4c8fd9; line-height: 1;}
.pick .score span {font-family: 'IBM Plex Sans', sans-serif; font-size: 0.8rem;
                   font-weight: 400; color: #93a0b2;}
.pick .why {list-style: none; margin: 12px 0 0 0; padding: 10px 0 0 0;
            border-top: 1px solid #232b37; display: flex; flex-direction: column; gap: 6px;}
.pick .why li {font-size: 0.85rem; color: #c3ccd8; line-height: 1.4; margin: 0;
               padding-left: 14px; position: relative;}
.pick .why li::before {content: ""; position: absolute; left: 0; top: 0.55em;
                       width: 6px; height: 6px; border-radius: 50%; background: #4c8fd9;}
.pick .why strong {color: #e8ecf2;}

[data-testid="stSidebar"] {border-right: 1px solid #232b37;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color: #232b37 !important; border-radius: 14px;}

.pick .top {display: flex; justify-content: space-between; align-items: center;}
.avatar {width: 40px; height: 40px; border-radius: 50%; background: #222b37; color: #e8ecf2;
         display: flex; align-items: center; justify-content: center;
         font-weight: 600; font-size: 0.85rem;}

.picks {display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 16px; align-items: stretch; margin-bottom: 1rem;}
.pick {display: flex; flex-direction: column;}

.why-row {padding: 14px 0; border-bottom: 1px solid #232b37;}
.why-row:last-child {border-bottom: 0;}
.why-head {display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 10px;}
.why-rank {font-family: 'IBM Plex Mono', monospace; color: #93a0b2; font-size: 0.85rem;
           min-width: 1.5rem;}
.why-name {font-weight: 600; color: #e8ecf2;}
.why-meta {color: #93a0b2; font-size: 0.85rem;}
.why-row .why {list-style: none; margin: 8px 0 0 2.1rem; padding: 0;
               display: flex; flex-direction: column; gap: 4px;}
.why-row .why li {font-size: 0.88rem; color: #c3ccd8; line-height: 1.4;
                  padding-left: 14px; position: relative;}
.why-row .why li::before {content: ""; position: absolute; left: 0; top: 0.55em;
                          width: 6px; height: 6px; border-radius: 50%; background: #4c8fd9;}
.why-row .why strong {color: #e8ecf2;}

.player-head {background: #161c25; border: 1px solid #232b37; border-radius: 14px;
              padding: 24px 26px; margin-bottom: 1rem; display: flex; flex-wrap: wrap;
              gap: 24px; align-items: center; justify-content: space-between;}
.player-head .name {font-size: 2rem; font-weight: 700; color: #e8ecf2; line-height: 1.1;}
.player-head .meta {color: #b6c1d0; margin: 6px 0 10px 0; font-size: 0.95rem;}
.ph-main {display: flex; gap: 20px; align-items: center; flex: 1 1 420px;}
.ph-avatar {width: 84px; height: 84px; border-radius: 50%; border: 3px solid #d4b03c;
            background: #1f2834; color: #e8ecf2; font-size: 1.6rem; font-weight: 700;
            display: flex; align-items: center; justify-content: center; flex-shrink: 0;}
.ph-avatar.small {font-size: 1.15rem;}
.ph-kicker {color: #d4b03c; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
            text-transform: uppercase; margin-bottom: 4px;}
.ph-stats {display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); flex: 1 1 380px;
           border-left: 1px solid #232b37;}
.hs {padding: 4px 18px; border-right: 1px solid #232b37;}
.hs:last-child {border-right: 0;}
.hs-label {font-size: 0.78rem; color: #93a0b2;}
.hs-value {font-family: 'IBM Plex Mono', monospace; font-size: 1.8rem; font-weight: 600;
           color: #e8ecf2; line-height: 1.3;}
.hs-note {font-size: 0.78rem; color: #93a0b2;}

.sim-list {background: #161c25; border: 1px solid #232b37; border-radius: 14px; padding: 4px 16px;}
.sim-row {display: grid; grid-template-columns: 40px minmax(0, 1.2fr) minmax(0, 1.6fr) 48px;
          gap: 12px; align-items: center; padding: 12px 0; border-bottom: 1px solid #1d2530;}
.sim-row:last-child {border-bottom: 0;}
.sim-ini {width: 36px; height: 36px; border-radius: 50%; background: #222b37; color: #c3ccd8;
          display: flex; align-items: center; justify-content: center;
          font-size: 0.8rem; font-weight: 600;}
.sim-name {font-weight: 600; color: #e8ecf2; font-size: 0.92rem;}
.sim-meta {font-size: 0.78rem; color: #93a0b2;}
.sim-close {font-size: 0.82rem; color: #b6c1d0;}
.sim-score {font-family: 'IBM Plex Mono', monospace; font-size: 1.25rem; font-weight: 600;
            color: #c3ccd8; text-align: right;}
.sim-score.strong {color: #3fae72;}

.cmp-head {display: flex; align-items: center; gap: 10px; margin-bottom: 4px;}
.cmp-dot {width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0;}
.cmp-name {font-size: 1.15rem; font-weight: 700; color: #e8ecf2;}
.cmp-meta {font-size: 0.85rem; color: #93a0b2; margin-top: 2px;}
.cmp-lead {font-size: 0.85rem; color: #c3ccd8; margin: 6px 0 8px 0;}
.cmp-lead strong {font-family: 'IBM Plex Mono', monospace; color: #e8ecf2; font-size: 1rem;}

.cmp-card {background: #161c25; border: 1px solid #232b37; border-top: 3px solid #4c8fd9;
           border-radius: 14px; padding: 20px 22px; margin-bottom: 1rem;
           display: flex; flex-wrap: wrap; gap: 16px; align-items: center;
           justify-content: space-between;}
.cmp-main {display: flex; gap: 16px; align-items: center; min-width: 0; flex: 1 1 260px;}
.cmp-avatar {width: 64px; height: 64px; border-radius: 50%; border: 3px solid #4c8fd9;
             background: #1f2834; color: #e8ecf2; font-size: 1.25rem; font-weight: 700;
             display: flex; align-items: center; justify-content: center; flex-shrink: 0;}
.cmp-avatar .crest {display: block; margin: 0 !important;}
.cmp-kicker {font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
             text-transform: uppercase; margin-bottom: 2px;}
.cmp-name {font-size: 1.45rem; font-weight: 700; color: #e8ecf2; line-height: 1.15;}
.cmp-meta {font-size: 0.88rem; color: #b6c1d0; margin: 4px 0 8px 0;}
.cmp-stat {padding-left: 18px; border-left: 1px solid #232b37;}
.cmp-stat-value {font-family: 'IBM Plex Mono', monospace; font-size: 1.8rem; font-weight: 600;
                 color: #e8ecf2; line-height: 1.1;}
.cmp-stat-value span {font-size: 1rem; color: #93a0b2;}
.cmp-stat-label {font-size: 0.78rem; color: #93a0b2;}

.p90-wrap {background: #161c25; border: 1px solid #232b37; border-radius: 14px;
           overflow-x: auto;}
.p90 {width: 100%; border-collapse: collapse; font-size: 0.92rem;}
.p90 th, .p90 td {padding: 11px 16px; border-bottom: 1px solid #1d2530; border-left: 0;
                  border-right: 0; border-top: 0;}
.p90 tbody tr:last-child th, .p90 tbody tr:last-child td {border-bottom: 0;}
.p90 thead th {text-align: right; vertical-align: bottom; border-bottom: 1px solid #2a3442;}
.p90 tbody th {text-align: left; font-weight: 400; color: #b6c1d0;}
.p90 td {text-align: right; font-family: 'IBM Plex Mono', monospace; color: #e8ecf2;}
.p90 td.best {color: #3fae72; font-weight: 600;}
.p90-dot {display: inline-block; width: 10px; height: 10px; border-radius: 50%;
          margin-right: 6px;}
.p90-name {font-weight: 700; color: #e8ecf2; font-size: 1rem;}
.p90-season {display: block; font-size: 0.75rem; color: #93a0b2; font-weight: 400;
             margin-top: 2px;}
[class*="st-key-seasonbox"] {margin-top: -0.5rem;}
[class*="st-key-seasonbox"] button {min-height: 32px; padding: 0 12px; font-size: 0.8rem;}
.p90 tbody th, .p90 thead th:first-child {width: 1%; white-space: nowrap; padding-right: 28px;}

.p90 {margin: 1 !important;}
.p90-wrap {line-height: 0;}
.p90-wrap table {line-height: normal;}

.crest {object-fit: contain; vertical-align: -4px; margin-right: 6px;}

.pick a.name {display: block; color: #e8ecf2; text-decoration: none;}
.pick a.name:hover {color: #7fb0e8; text-decoration: underline;}

.cmp-summary {background: #161c25; border: 1px solid #232b37; border-radius: 14px;
              padding: 14px 18px; color: #c3ccd8; font-size: 0.95rem; line-height: 1.55;
              margin: 0.25rem 0 1.25rem 0;}
.cmp-summary strong {color: #e8ecf2;}

a.sim-name {color: #e8ecf2; text-decoration: none;}
a.sim-name:hover {color: #7fb0e8; text-decoration: underline;}

[data-testid="stHeaderActionElements"] {display: none;}

.action-link {display: inline-flex; align-items: center; min-height: 40px; padding: 0 16px;
              margin: 10px 0 4px 0; border: 1px solid #2a3442; border-radius: 8px;
              color: #e8ecf2 !important; text-decoration: none !important; font-size: 0.9rem;
              font-weight: 500; background: #161c25;}
.action-link:hover {border-color: #4c8fd9; color: #ffffff !important;}

.cmp-text {flex: 1; min-width: 0;}
.cmp-kicker, .cmp-meta {white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}

.p90 thead th {text-align: center;}
.p90-dot {display: block; margin: 0 auto 6px auto;}

.start-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
             gap: 16px; margin-bottom: 1.5rem;}
.start-card {display: flex; flex-direction: column; gap: 10px; padding: 18px 20px;
             background: #161c25; border: 1px solid #232b37; border-radius: 14px;
             text-decoration: none !important;}
.start-card:hover {border-color: #4c8fd9;}
.start-title {font-weight: 700; font-size: 1.05rem; color: #e8ecf2;}
.start-text {font-size: 0.9rem; color: #93a0b2; line-height: 1.5; flex: 1;}
.start-link {font-size: 0.9rem; font-weight: 600; color: #7fb0e8;}

.steps {display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 1.5rem 0;}
.step {display: flex; align-items: center; gap: 8px; padding: 8px 14px; background: #161c25;
       border: 1px solid #232b37; border-radius: 999px; font-size: 0.88rem; color: #c3ccd8 !important;
       text-decoration: none !important;}
.step:hover {border-color: #4c8fd9;}
.step span {display: inline-flex; align-items: center; justify-content: center; width: 22px;
            height: 22px; border-radius: 50%; background: #4c8fd9; color: #0e1218;
            font-size: 0.75rem; font-weight: 700;}

            .p90 thead th {text-align: center; vertical-align: bottom; border-bottom: 1px solid #2a3442;
               white-space: nowrap;}
.p90 thead th:first-child {text-align: left;}
.p90 td {text-align: center; font-family: 'IBM Plex Mono', monospace; color: #e8ecf2;}
.p90-dot {display: block; margin: 0 auto 6px auto;}
            

</style>
"""


def style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, kicker: str = "Betway Premiership · recruitment") -> None:
    st.markdown(f'<div class="hero"><div class="kicker">{escape(kicker)}</div>'
                f'<h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>',
                unsafe_allow_html=True)


def cards(items: list[tuple[str, str, str]]) -> None:
    html = "".join(
        f'<div class="card"><div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>'
        + (f'<div class="note">{escape(note)}</div>' if note else "") + "</div>"
        for label, value, note in items
    )
    st.markdown(f'<div class="cards">{html}</div>', unsafe_allow_html=True)


def pill(text: str, kind: str = "muted") -> str:
    return f'<span class="pill {kind}">{escape(text)}</span>'

CRESTS = ROOT / "static" / "crests"


def crest(club: str, size: int = 20) -> str:
    """Small crest image for a club, or nothing if the file isn't there."""
    first = str(club).split("/")[0].strip()          # players at two clubs: use the first
    name = re.sub(r"[^a-z0-9]+", "-", first.lower()).strip("-") + ".png"
    if not (CRESTS / name).exists():
        return ""
    return (f'<img class="crest" src="app/static/crests/{name}" alt="" '
            f'width="{size}" height="{size}">')


MANUAL = ROOT / "data" / "manual"


@st.cache_data
def load_percentiles() -> pd.DataFrame:
    pct = pd.read_csv(PROCESSED / "percentiles.csv", dtype={"player_id": str})
    profiles = pd.read_csv(PROCESSED / "profiles.csv", dtype={"player_id": str},
                           usecols=["player_id", "Born"])
    born = pd.to_numeric(profiles.dropna(subset=["Born"]).drop_duplicates("player_id")
                         .set_index("player_id")["Born"], errors="coerce")

    manual_file = MANUAL / "birth_years.csv"
    if manual_file.exists():
        manual = pd.read_csv(manual_file, dtype={"player_id": str}).dropna(subset=["born"])
        manual_born = pd.to_numeric(manual.set_index("player_id")["born"], errors="coerce")
        born = born.combine_first(manual_born)

    pct["season_age"] = pct["Age"]
    pct["Age"] = date.today().year - pct["player_id"].map(born)
    return pct


@st.cache_data
def load_profiles() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "profiles.csv", dtype={"player_id": str})


@st.cache_data
def load_similar() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "similar_players.csv",
                       dtype={"player_id": str, "similar_id": str})


CREST_CREDIT = ("Club crests via [FootyLogos](https://www.footylogos.com/competition/premier-soccer-league), "
                "[Brandfetch](https://brandfetch.com/) and "
                "[Orbit College FC](https://www.facebook.com/orbitsoccer/). Crests are the property of "
                "their respective clubs and are used for identification only.")


def footer() -> None:
    st.divider()
    st.caption(DATA_CREDIT + " Ages are approximate. " + CREST_CREDIT +
               " Non-commercial portfolio project.")