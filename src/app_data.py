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

BAND_COLORS = {"Below average (0-33)": "#f0a35e",
               "Average (34-66)": "#5d7366",
               "Strong (67-100)": "#d4f05a"}

PLAYER_COLORS = ["#d4f05a", "#5fc4e8", "#f0a35e"]

FIT_SCORE_HELP = ("Weighted average of the player's percentiles on the stats you prioritise, "
                  "compared with players in the same role. 0-100. Not an overall rating "
                  "or a probability of success.")
FORM_HELP = "2026-27 so far. Small sample: treat as an early signal, not a full-season verdict"
SIMILARITY_HELP = ("Profile similarity score: How close two players' percentile profiles are. "
                   "Use it to rank matches, not as a percentage of likeness.")
DATA_CREDIT = "Data: [FBref.com](https://fbref.com) (Betway Premiership player stats)."


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=Big+Shoulders+Stencil+Display:wght@700;800&display=swap');

/* ---- Tactics board tokens ---- */
:root {
  --bg: #0d1a14;          /* pitch at night */
  --surface: #102219;     /* card */
  --surface-2: #163024;   /* raised / hover */
  --line: rgba(233,240,234,0.16);
  --line-strong: rgba(233,240,234,0.30);
  --chalk: #e9f0ea;       /* main text, pitch lines */
  --soft: #c5d3c9;        /* secondary text */
  --muted: #9fb3a6;       /* labels */
  --lime: #d4f05a;        /* highlight: strong, selected, primary */
  --amber: #f0a35e;       /* caution */
  --radius: 6px;
  --stencil: 'Big Shoulders Stencil Display', sans-serif;
}

.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3,
.stApp input, .stApp button, .stApp textarea,
[data-testid="stMarkdownContainer"] {font-family: 'Archivo', sans-serif;}
.stApp {background: var(--bg);}
.block-container {padding-top: 3.5rem; max-width: 1360px;}
h1, h2, h3 {letter-spacing: -0.01em; color: var(--chalk);}
.stApp h2, .stApp h3 {font-weight: 700;}
.mono {font-variant-numeric: tabular-nums;}
[data-testid="stHeaderActionElements"] {display: none;}

/* Section headings read like board labels */
[data-testid="stHeading"] h3 {font-size: 0.95rem; letter-spacing: 0.1em; text-transform: uppercase;
                              color: var(--muted); font-weight: 700;}

/* Sidebar and Streamlit containers */
[data-testid="stSidebar"] {background: #0b160f; border-right: 1.5px solid var(--line);}
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"] details {
  border: 1.5px solid var(--line) !important; border-radius: var(--radius) !important;
  background: var(--surface);}
.stButton button, .stDownloadButton button, .stLinkButton a {
  border-radius: 4px !important; border: 1.5px solid var(--line-strong) !important;
  font-weight: 600 !important;}
.stButton button[kind="primary"] {background: var(--lime) !important; color: var(--bg) !important;
                                  border-color: var(--lime) !important;}
[data-testid="stAlert"] {border-radius: var(--radius);}

/* ---- Page header with centre-circle marking ---- */
.hero {position: relative; overflow: hidden; padding: 28px 32px 26px 32px; margin-bottom: 1.2rem;
       background: var(--surface); border: 1.5px solid var(--line-strong); border-radius: var(--radius);}
.hero::before {content: ""; position: absolute; right: -70px; top: 50%; width: 240px; height: 240px;
               transform: translateY(-50%); border: 2px solid rgba(233,240,234,0.10); border-radius: 50%;}
.hero::after {content: ""; position: absolute; right: 48px; top: 0; bottom: 0; width: 2px;
              background: rgba(233,240,234,0.10);}
.hero .kicker {display: inline-block; background: var(--lime); color: var(--bg); font-size: 0.72rem;
               font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
               padding: 3px 9px; border-radius: 3px; margin-bottom: 12px;}
.hero h1 {color: var(--chalk); margin: 0 0 0.4rem 0; font-size: 2.6rem; font-weight: 700;
          line-height: 1.05; padding: 0;}
.hero p {color: var(--soft); margin: 0; font-size: 1rem; line-height: 1.5; max-width: 760px;
         position: relative;}

/* ---- Stat cards: squad-board numbers ---- */
.cards {display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 14px; margin: 0.4rem 0 1.4rem 0;}
.card {background: var(--surface); border: 1.5px solid var(--line); border-radius: var(--radius);
       padding: 16px 18px;}
.card .label {font-size: 0.75rem; color: var(--muted); letter-spacing: 0.08em;
              text-transform: uppercase; font-weight: 600;}
.card .value {font-family: var(--stencil); font-size: 2.6rem; font-weight: 800; color: var(--chalk);
              margin-top: 4px; line-height: 1;}
.card .note {font-size: 0.82rem; color: var(--muted); margin-top: 6px; line-height: 1.4;}

/* ---- Tags ---- */
.pill {display: inline-block; padding: 3px 9px; border-radius: 3px; font-size: 0.75rem;
       font-weight: 600; margin-right: 6px; border: 1px solid transparent;}
.pill.ok {border-color: var(--line-strong); color: var(--chalk);}
.pill.warn {border: 1px dashed var(--amber); color: var(--amber);}
.pill.muted {background: var(--surface-2); color: var(--soft);}

/* ---- Shortlist pick cards ---- */
.picks {display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 16px; align-items: stretch; margin-bottom: 1rem;}
.pick {display: flex; flex-direction: column; background: var(--surface);
       border: 1.5px solid var(--line); border-radius: var(--radius); padding: 18px 20px; height: 100%;}
.pick.first {border-color: var(--lime);}
.pick .top {display: flex; justify-content: space-between; align-items: center;}
.pick .rank {font-size: 0.75rem; color: var(--muted); font-weight: 700; letter-spacing: 0.08em;
             text-transform: uppercase;}
.pick.first .rank {background: var(--lime); color: var(--bg); padding: 2px 8px; border-radius: 3px;}
.pick .name, .pick a.name {display: block; font-size: 1.2rem; font-weight: 700; color: var(--chalk);
                           margin-top: 8px; text-decoration: none;}
.pick a.name:hover {color: var(--lime); text-decoration: underline;}
.pick .meta {font-size: 0.85rem; color: var(--muted); margin-bottom: 10px;}
.pick .score {font-family: var(--stencil); font-size: 3.2rem; font-weight: 800; color: var(--chalk);
              line-height: 0.95;}
.pick.first .score {color: var(--lime);}
.pick .score span {font-family: 'Archivo', sans-serif; font-size: 0.75rem; font-weight: 600;
                   color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase;}
.pick .why {list-style: none; margin: 12px 0 0 0; padding: 12px 0 0 0;
            border-top: 1.5px dashed var(--line); display: flex; flex-direction: column; gap: 6px;}
.pick .why li {font-size: 0.86rem; color: var(--soft); line-height: 1.4; margin: 0;
               padding-left: 16px; position: relative;}
.pick .why li::before {content: ""; position: absolute; left: 0; top: 0.5em;
                       width: 7px; height: 7px; border: 1.5px solid var(--lime); border-radius: 50%;}
.pick .why strong {color: var(--chalk);}
.avatar {width: 40px; height: 40px; border-radius: 4px; background: var(--surface-2);
         color: var(--chalk); display: flex; align-items: center; justify-content: center;
         font-weight: 700; font-size: 0.85rem;}

.why-row {padding: 14px 0; border-bottom: 1.5px dashed var(--line);}
.why-row:last-child {border-bottom: 0;}
.why-head {display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 10px;}
.why-rank {font-family: var(--stencil); font-weight: 800; color: var(--lime); font-size: 1.1rem;
           min-width: 1.5rem;}
.why-name {font-weight: 700; color: var(--chalk);}
.why-meta {color: var(--muted); font-size: 0.85rem;}
.why-row .why {list-style: none; margin: 8px 0 0 2.1rem; padding: 0;
               display: flex; flex-direction: column; gap: 4px;}
.why-row .why li {font-size: 0.88rem; color: var(--soft); line-height: 1.4;
                  padding-left: 16px; position: relative;}
.why-row .why li::before {content: ""; position: absolute; left: 0; top: 0.5em;
                          width: 7px; height: 7px; border: 1.5px solid var(--lime); border-radius: 50%;}
.why-row .why strong {color: var(--chalk);}

/* ---- Player profile header ---- */
.player-head {position: relative; overflow: hidden; background: var(--surface);
              border: 1.5px solid var(--line-strong); border-radius: var(--radius);
              padding: 26px 28px; margin-bottom: 1rem; display: flex; flex-wrap: wrap;
              gap: 24px; align-items: center; justify-content: space-between;}
.player-head .name {font-size: 2.4rem; font-weight: 700; color: var(--chalk); line-height: 1.05;}
.player-head .meta {color: var(--soft); margin: 6px 0 10px 0; font-size: 1rem;}
.ph-main {display: flex; gap: 20px; align-items: center; flex: 1 1 380px;}
.ph-avatar {width: 72px; height: 72px; border-radius: 4px; background: var(--lime); color: var(--bg);
            font-size: 1.5rem; font-weight: 700; letter-spacing: 0.04em;
            display: flex; align-items: center; justify-content: center; flex-shrink: 0;}
.ph-avatar.small {font-size: 1.05rem;}
.ph-kicker {color: var(--muted); font-size: 0.78rem; font-weight: 700; letter-spacing: 0.1em;
            text-transform: uppercase; margin-bottom: 6px;}
.ph-pitch {flex: 0 1 230px; min-width: 190px;}
.ph-pitch svg {display: block; width: 100%; height: auto;}
.ph-stats {display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); flex: 1 1 340px;
           border-left: 1.5px solid var(--line);}
.hs {padding: 4px 18px; border-right: 1.5px solid var(--line);}
.hs:last-child {border-right: 0;}
.hs-label {font-size: 0.72rem; color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase;
           font-weight: 600;}
.hs-value {font-family: var(--stencil); font-size: 3rem; font-weight: 800; color: var(--lime);
           line-height: 1;}
.hs-note {font-size: 0.78rem; color: var(--muted);}

/* ---- Similar players ---- */
.sim-list {background: var(--surface); border: 1.5px solid var(--line); border-radius: var(--radius);
           padding: 4px 16px;}
.sim-row {display: grid; grid-template-columns: 40px minmax(0, 1.2fr) minmax(0, 1.6fr) 52px;
          gap: 12px; align-items: center; padding: 12px 0; border-bottom: 1.5px dashed var(--line);}
.sim-row:last-child {border-bottom: 0;}
.sim-ini {width: 36px; height: 36px; border-radius: 4px; background: var(--surface-2); color: var(--soft);
          display: flex; align-items: center; justify-content: center; font-size: 0.78rem; font-weight: 700;}
.sim-name, a.sim-name {font-weight: 700; color: var(--chalk); font-size: 0.95rem; text-decoration: none;}
a.sim-name:hover {color: var(--lime); text-decoration: underline;}
.sim-meta {font-size: 0.78rem; color: var(--muted);}
.sim-close {font-size: 0.82rem; color: var(--soft);}
.sim-score {font-family: var(--stencil); font-size: 1.9rem; font-weight: 800; color: var(--soft);
            text-align: right; line-height: 1;}
.sim-score.strong {color: var(--lime);}

/* ---- Compare ---- */
.cmp-card {background: var(--surface); border: 1.5px solid var(--line); border-top: 4px solid var(--lime);
           border-radius: var(--radius); padding: 20px 22px; margin-bottom: 1rem;
           display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between;}
.cmp-main {display: flex; gap: 16px; align-items: center; min-width: 0; flex: 1 1 260px;}
.cmp-text {flex: 1; min-width: 0;}
.cmp-avatar {width: 64px; height: 64px; border-radius: 50%; border: 3px solid var(--lime);
             background: var(--surface-2); color: var(--chalk); font-size: 1.2rem; font-weight: 700;
             display: flex; align-items: center; justify-content: center; flex-shrink: 0;}
.cmp-avatar .crest {display: block; margin: 0 !important;}
.cmp-kicker {font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
             margin-bottom: 2px;}
.cmp-name {font-size: 1.5rem; font-weight: 700; color: var(--chalk); line-height: 1.15;}
.cmp-meta {font-size: 0.88rem; color: var(--soft); margin: 4px 0 8px 0;}
.cmp-kicker, .cmp-meta {white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.cmp-stat {padding-left: 18px; border-left: 1.5px solid var(--line);}
.cmp-stat-value {font-family: var(--stencil); font-size: 2.8rem; font-weight: 800; color: var(--chalk);
                 line-height: 1;}
.cmp-stat-value span {font-size: 1.4rem; color: var(--muted);}
.cmp-stat-label {font-size: 0.72rem; color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase;
                 font-weight: 600;}
.cmp-summary {background: var(--surface); border: 1.5px solid var(--line); border-left: 4px solid var(--lime);
              border-radius: var(--radius); padding: 14px 18px; color: var(--soft); font-size: 0.98rem;
              line-height: 1.55; margin: 0.25rem 0 1.25rem 0;}
.cmp-summary strong {color: var(--chalk);}
[class*="st-key-seasonbox"] {margin-top: -0.5rem;}
[class*="st-key-seasonbox"] button {min-height: 32px; padding: 0 12px; font-size: 0.8rem;}

/* ---- Per-90 table ---- */
.p90-wrap {background: var(--surface); border: 1.5px solid var(--line); border-radius: var(--radius);
           overflow-x: auto; line-height: 0;}
.p90-wrap table {line-height: normal;}
.p90 {width: 100%; border-collapse: collapse; font-size: 0.95rem; margin: 0 !important;}
.p90 th, .p90 td {padding: 11px 16px; border: 0; border-bottom: 1.5px dashed var(--line);}
.p90 tbody tr:last-child th, .p90 tbody tr:last-child td {border-bottom: 0;}
.p90 thead th {text-align: center; vertical-align: bottom; white-space: nowrap;
               border-bottom: 1.5px solid var(--line-strong);}
.p90 thead th:first-child {text-align: left;}
.p90 tbody th, .p90 thead th:first-child {width: 1%; white-space: nowrap; padding-right: 28px;}
.p90 tbody th {text-align: left; font-weight: 500; color: var(--soft);}
.p90 td {text-align: center; font-variant-numeric: tabular-nums; font-weight: 600; color: var(--chalk);}
.p90 td.best {color: var(--lime); font-weight: 700;}
.p90-dot {display: block; width: 10px; height: 10px; border-radius: 50%; margin: 0 auto 6px auto;}
.p90-name {font-weight: 700; color: var(--chalk); font-size: 1rem;}
.p90-season {display: block; font-size: 0.75rem; color: var(--muted); font-weight: 500; margin-top: 2px;}

/* ---- Links, crests, buttons ---- */
.crest {object-fit: contain; vertical-align: -4px; margin-right: 6px;}
.action-link {display: inline-flex; align-items: center; min-height: 42px; padding: 0 18px;
              margin: 10px 0 4px 0; border: 1.5px solid var(--line-strong); border-radius: 4px;
              color: var(--chalk) !important; text-decoration: none !important; font-size: 0.92rem;
              font-weight: 700; background: transparent;}
.action-link:hover {border-color: var(--lime); color: var(--lime) !important;}

/* ---- Home start cards ---- */
.start-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
             gap: 16px; margin-bottom: 1.5rem;}
.start-card {display: flex; flex-direction: column; gap: 10px; padding: 20px 22px;
             background: var(--surface); border: 1.5px solid var(--line); border-radius: var(--radius);
             text-decoration: none !important;}
.start-card:hover {border-color: var(--lime); background: var(--surface-2);}
.start-title {font-weight: 700; font-size: 1.1rem; color: var(--chalk);}
.start-text {font-size: 0.9rem; color: var(--muted); line-height: 1.5; flex: 1;}
.start-link {font-size: 0.9rem; font-weight: 700; color: var(--lime);}

/* ---- Methodology steps ---- */
.steps {display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 1.5rem 0;}
.step {display: flex; align-items: center; gap: 8px; padding: 8px 14px; background: var(--surface);
       border: 1.5px solid var(--line); border-radius: 4px; font-size: 0.88rem; font-weight: 600;
       color: var(--soft) !important; text-decoration: none !important;}
.step:hover {border-color: var(--lime);}
.step span {display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px;
            border-radius: 3px; background: var(--lime); color: var(--bg); font-size: 0.75rem; font-weight: 800;}

/* ---- Top navigation (replaces the sidebar) ---- */
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"], [data-testid="stSidebarNav"] {display: none !important;}
.topnav {display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
         gap: 10px 24px; padding: 0 0 14px 0; margin: -1.5rem 0 1.4rem 0;
         border-bottom: 1.5px solid var(--line);}
.topnav .brand {display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1rem;
                color: var(--chalk); text-decoration: none !important; letter-spacing: 0.01em;}
.topnav .links {display: flex; flex-wrap: wrap; gap: 2px;}
.topnav .links a {padding: 10px 12px; font-weight: 600; font-size: 0.95rem; color: var(--muted) !important;
                  text-decoration: none !important; border-bottom: 3px solid transparent;}
.topnav .links a:hover {color: var(--chalk) !important;}
.topnav .links a.active {color: var(--chalk) !important; border-bottom-color: var(--lime);}

/* ---- Info messages (st.info) ---- */
[data-testid="stAlertContainer"], [data-testid="stAlert"] > div {
  background: var(--surface) !important; border: 1.5px solid var(--line) !important;
  border-left: 4px solid var(--lime) !important; border-radius: var(--radius) !important;}
[data-testid="stAlertContainer"] p, [data-testid="stAlert"] p,
[data-testid="stAlertContainer"] [data-testid="stMarkdownContainer"] {color: var(--soft) !important;}
[data-testid="stAlertContainer"] strong, [data-testid="stAlert"] strong {color: var(--chalk) !important;}
[data-testid="stAlertContainer"] svg, [data-testid="stAlert"] svg,
[data-testid="stAlertContainer"] [data-testid="stIconMaterial"] {color: var(--lime) !important;
                                                                 fill: var(--lime) !important;}
                                                                
</style>
"""


def style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


NAV = [("Home", ""), ("Shortlist", "Shortlist"), ("Player Profile", "Player_Profile"),
       ("Compare", "Compare"), ("Watchlist", "Watchlist"), ("Methodology", "Methodology")]
PITCH_ICON = ('<svg width="30" height="22" viewBox="0 0 34 26" aria-hidden="true">'
              '<rect x="1" y="1" width="32" height="24" rx="2" fill="none" stroke="#e9f0ea" stroke-width="1.6"/>'
              '<line x1="17" y1="1" x2="17" y2="25" stroke="#e9f0ea" stroke-width="1.6"/>'
              '<circle cx="17" cy="13" r="4.5" fill="none" stroke="#d4f05a" stroke-width="1.6"/></svg>')


def nav(active: str) -> None:
    """Top navigation bar. `active` is the page's label in NAV."""
    links = "".join(
        f'<a class="{"active" if label == active else ""}" href="/{path}" target="_self"'
        f'{" aria-current=page" if label == active else ""}>{label}</a>'
        for label, path in NAV
    )
    st.markdown(
        f'<nav class="topnav" aria-label="Pages">'
        f'<a class="brand" href="/" target="_self">{PITCH_ICON}African Football Scouting Tool</a>'
        f'<div class="links">{links}</div></nav>',
        unsafe_allow_html=True,
    )


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


# Zones on a pitch drawn 420 x 280, attacking to the right: (x, y, width, height)
ROLE_ZONES = {
    "CB": [(18, 92, 90, 96)],
    "FB": [(18, 10, 120, 62), (18, 208, 120, 62)],
    "DM": [(118, 92, 72, 96)],
    "CM": [(176, 70, 92, 140)],
    "W/AM": [(268, 10, 130, 62), (268, 208, 130, 62), (272, 96, 60, 88)],
    "ST": [(334, 92, 76, 96)],
}
ROLE_LABEL_POS = {"CB": [(63, 145)], "FB": [(78, 46), (78, 244)], "DM": [(154, 145)],
                  "CM": [(222, 112)], "W/AM": [(333, 46), (333, 244)], "ST": [(372, 145)]}


def role_pitch(role: str) -> str:
    """Small pitch diagram with the player's role zone highlighted."""
    line = 'stroke="#e9f0ea" stroke-opacity="0.45" stroke-width="2" fill="none"'
    zones = "".join(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="#d4f05a" '
        f'fill-opacity="0.22" stroke="#d4f05a" stroke-width="2.5" stroke-dasharray="6 5"/>'
        for x, y, w, h in ROLE_ZONES.get(role, [])
    )
    labels = "".join(
        f'<text x="{x}" y="{y}" fill="{"#d4f05a" if r == role else "#e9f0ea"}" '
        f'fill-opacity="{1 if r == role else 0.4}" font-size="{26 if r == role else 18}">{r}</text>'
        for r, spots in ROLE_LABEL_POS.items() for x, y in spots
    )
    return (
        f'<svg viewBox="0 0 420 280" role="img" '
        f'aria-label="Pitch with the {escape(role)} zone highlighted">'
        f'<rect x="4" y="4" width="412" height="272" rx="3" fill="#123024" {line}/>'
        f'<line x1="210" y1="4" x2="210" y2="276" {line}/>'
        f'<circle cx="210" cy="140" r="36" {line}/>'
        f'<rect x="4" y="72" width="60" height="136" {line}/>'
        f'<rect x="356" y="72" width="60" height="136" {line}/>'
        f'{zones}'
        f'<g font-family="Archivo, sans-serif" font-weight="700" text-anchor="middle">{labels}</g>'
        f'</svg>'
    )

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