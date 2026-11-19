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
BAND_COLORS = {"Below average (0-33)": "#3F6A51",   
               "Average (34-66)":"#31a354",        
               "Strong (67-100)": "#b5cf3e"}       

PLAYER_COLORS = ["#d4f05a", "#31a354", "#addd8e",]  
CHART_COLORS = ["#c5e145", "#31a354","#addd8e",]   

FIT_SCORE_HELP = ("Weighted average of the player's percentiles on the stats you prioritise, "
                  "compared with players in the same role. 0-100. Not an overall rating "
                  "or a probability of success.")
FORM_HELP = "2026-27 so far. Small sample: treat as an early signal, not a full-season verdict"
SIMILARITY_HELP = ("**Profile similarity score:** How close two players' percentile profiles are. "
                   "Use it to rank matches, not as a percentage of likeness.")
DATA_CREDIT = "**Data**: [FBref.com](https://fbref.com) (Betway Premiership player stats)."


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
  --gold: #d6b45c;       /* caution */
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
.hero p {color: var(--soft); margin: 0; font-size: 0.93rem; line-height: 1.5; max-width: 760px;
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
.pill.warn {border: 1px dashed var(--gold); color: var(--gold);}
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
.player-head .meta {color: var(--soft); margin: 6px 0 10px 0; font-size: 0.90rem;}
.ph-main {display: flex; gap: 20px; align-items: center; flex: 1 1 380px;}
.ph-avatar {width: 72px; height: 72px; border-radius: 4px; background: var(--lime); color: var(--bg);
            font-size: 1.5rem; font-weight: 700; letter-spacing: 0.04em;
            display: flex; align-items: center; justify-content: center; flex-shrink: 0;}
.ph-avatar.small {font-size: 1.05rem;}
.ph-kicker {color: var(--muted); font-size: 0.70rem; font-weight: 700; letter-spacing: 0.1em;
            text-transform: uppercase; margin-bottom: 6px;}
.ph-pitch {flex: 0 1 230px; min-width: 190px;}
.ph-pitch svg {display: block; width: 100%; height: auto;}
.ph-stats {display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
           grid-template-rows: auto auto auto; flex: 1 1 340px;
           border-left: 1.5px solid var(--line);}
.hs {display: grid; grid-row: span 3; grid-template-rows: subgrid; row-gap: 4px;
     padding: 4px 18px; border-right: 1.5px solid var(--line);}
.hs:last-child {border-right: 0;}
.hs-label {font-size: 0.72rem; color: var(--muted); letter-spacing: 0.06em; text-transform: uppercase;
           font-weight: 600; align-self: end;}
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
.cmp-card {background: var(--surface); border: 1.5px solid var(--line); border-top: 4px solid var(--lime);
           border-radius: var(--radius); padding: 20px 22px; margin-bottom: 1rem;
           display: flex; flex-direction: column; gap: 14px;}
.cmp-tags {min-height: 26px;}
.cmp-main {display: flex; gap: 16px; align-items: center; min-width: 0; flex: 1 1 260px;}
.cmp-text {flex: 1; min-width: 0;}
.cmp-avatar {width: 55px; height: 55px; border-radius: 50%; border: 1px solid var(--line);
             background: var(--surface-2); color: var(--chalk); font-size: 1rem; font-weight: 700;
             display: flex; align-items: center; justify-content: center; flex-shrink: 0;}
.cmp-avatar .crest {display: block; margin: 0 !important;}
.cmp-kicker {font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
             margin-bottom: 2px; color: var(--muted);}
.cmp-name {font-size: 1.5rem; font-weight: 700; color: var(--chalk); line-height: 1.15;}
.cmp-meta {font-size: 0.88rem; color: var(--soft); margin: 4px 0 8px 0;}
.cmp-kicker, .cmp-meta {white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.cmp-stat {display: flex; align-items: baseline; gap: 12px; padding-top: 12px;
           border-top: 1.5px dashed var(--line);}
.cmp-stat-value {font-family: var(--stencil); font-size: 2.8rem; font-weight: 800; color: var(--chalk);
                 line-height: 1;}
.cmp-stat-value span {font-size: 1.4rem; color: var(--muted);}
.cmp-stat-label {font-size: 0.72rem; color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase;
                 font-weight: 600;}
.cmp-summary {background: var(--surface); border: 1.5px solid var(--line); border-left: 4px solid var(--lime);
              border-radius: var(--radius); padding: 14px 18px; color: var(--soft); font-size: 0.95rem;
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

/* ---- Top navigation ---- */
[data-testid="stHeader"] {background: transparent;}
/* Hide Streamlit's sidebar and its open/close button */
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"], [data-testid="stSidebarNav"] {display: none !important;}
/* Equal spacing between tabs: columns shrink to their label, fixed gap between them */
.st-key-topnav [data-testid="stHorizontalBlock"] {gap: 2.25rem !important; flex-wrap: nowrap;}
.st-key-topnav [data-testid="stColumn"] {flex: 0 0 auto !important; width: auto !important;
                                         min-width: 0 !important;}
.st-key-topnav [data-testid="stColumn"]:first-child {flex: 1 1 auto !important;}
.st-key-topnav {border: 0; margin: 0; padding: 0;}
.st-key-topnav [data-testid="stElementContainer"],
.st-key-topnav [data-testid="stMarkdownContainer"] p {margin: 0 !important;}

/* Centre whatever sits in each nav column in the same 44px band */
.st-key-topnav [data-testid="stColumn"] [data-testid="stVerticalBlock"] {
  height: 44px; justify-content: center; gap: 0 !important;}

/* Every item is the same 44px box, so they all line up */
.st-key-topnav .brand,
.st-key-topnav [data-testid="stPageLink"] a {
  height: 44px; display: flex !important; align-items: center; box-sizing: border-box;
  padding: 0 !important; margin: 0 !important; background: transparent !important;
  border: 0 !important; border-radius: 0 !important; white-space: nowrap;}

.st-key-topnav .brand {gap: 10px; font-weight: 700; color: var(--chalk);}
.st-key-topnav [data-testid="stPageLink"] p {color: var(--muted) !important; font-weight: 600;
  font-size: 0.95rem !important; line-height: 1; margin: 0 !important;}
.st-key-topnav [data-testid="stPageLink"] a:hover p {color: var(--chalk) !important;}

/* Current page: same link, white text and lime underline, not greyed out */
.st-key-navactive [data-testid="stPageLink"] a {
  opacity: 1 !important; cursor: default; width: fit-content;
  box-shadow: inset 0 -3px 0 var(--lime);}
.st-key-navactive [data-testid="stPageLink"] a p,
.st-key-navactive [data-testid="stPageLink"] a span {
  color: var(--chalk) !important; font-weight: 700 !important;}

/* The dividing line under the bar */
.nav-rule {height: 1.5px; background: var(--line); margin: -0.9rem 0 1.4rem 0;}

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
/* Icon inside st.info boxes, e.g. :material/fact_check: */
[data-testid="stAlert"] [data-testid="stIconMaterial"],
[data-testid="stAlertContainer"] [data-testid="stIconMaterial"],
[data-testid="stAlertContentInfo"] [data-testid="stIconMaterial"],
div[role="alert"] [data-testid="stIconMaterial"] {
  color: var(--lime) !important;
}

/* Icon in st.info boxes */
[data-testid="stAlertDynamicIcon"] {color: var(--lime) !important;}

/* Text and box colour for st.info (takes priority over the blue) */
[data-testid="stAlertContentInfo"] {color: var(--soft) !important;}
[data-testid="stAlertContentInfo"] strong {color: var(--chalk) !important;}
[data-testid="stAlertContainer"] {background: var(--surface) !important;
  border: 1.5px solid var(--line) !important; border-left: 4px solid var(--lime) !important;
  border-radius: var(--radius) !important;}

/* Selected-player tags in multiselects: dark green with white text */
[data-testid="stMultiSelect"] [data-tag] {
  background-color: #2e6b45 !important; border: 1px solid #3f8a5a !important;
  color: #ffffff !important;}
[data-testid="stMultiSelect"] [data-tag] span {color: #ffffff !important;}
[data-testid="stMultiSelect"] [data-tag] button svg,
[data-testid="stMultiSelect"] [data-tag] button path {fill: #ffffff !important; color: #ffffff !important;}

.season-spacer {height: 40px; margin-top: -0.5rem;}

/* Smaller, muted labels for all inputs (Player, Season, Role, Players, Show...) */
[data-testid="stWidgetLabel"] p {font-size: 0.8rem !important; color: var(--muted) !important;}

/* Compare cards: final layout (overrides older rules) */
.cmp-card {display: flex !important; flex-direction: column !important; flex-wrap: nowrap !important;
           align-items: stretch !important; justify-content: flex-start !important;
           align-content: normal !important; min-height: 0 !important; gap: 14px;}
.cmp-main {flex: 0 0 auto !important;}
.cmp-stat {border-left: 0 !important; padding-left: 0 !important; padding-top: 12px;
           border-top: 1.5px dashed var(--line); display: flex; align-items: baseline; gap: 12px;}
.cmp-meta {white-space: normal !important; overflow: visible !important; text-overflow: clip !important;}

/* ---- More breathing room on Compare ---- */
.hero {margin-bottom: 2rem;}                   
.cmp-card {margin-top: 1.25rem !important;}     
.cmp-summary {margin: 2rem 0 2.5rem 0 !important;}   
[class*="st-key-seasonbox"] {margin-top: 0 !important;}  

/* Heading in the top bar: white, bold, with the pitch icon */
.st-key-navbrand a,
.st-key-navbrand [data-testid="stPageLink-NavLink"] {
  display: flex !important; align-items: center; gap: 10px;}
.st-key-navbrand a p, .st-key-navbrand a span,
.st-key-navbrand [data-testid="stPageLink-NavLink"] p {
  color: var(--chalk) !important; font-weight: 700 !important; font-size: 1rem !important;}
.st-key-navbrand a::before,
.st-key-navbrand [data-testid="stPageLink-NavLink"]::before {
  content: ""; display: inline-block; flex-shrink: 0; width: 30px; height: 22px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 34 26'%3E%3Crect x='1' y='1' width='32' height='24' rx='2' fill='none' stroke='%23e9f0ea' stroke-width='1.6'/%3E%3Cline x1='17' y1='1' x2='17' y2='25' stroke='%23e9f0ea' stroke-width='1.6'/%3E%3Ccircle cx='17' cy='13' r='4.5' fill='none' stroke='%23d4f05a' stroke-width='1.6'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: center; background-size: contain;}

/* Season buttons (st.segmented_control): bold text */
[data-testid="stButtonGroup"] button p,
[data-testid="stButtonGroup"] button span,
[class*="st-key-seasonbox"] button p {font-weight: 700 !important;}

/* Line the crest up with the player's name */
.cmp-main {align-items: flex-start !important;}
.cmp-avatar {margin-top: 8px;}
                                                   
</style>
"""


def style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


NAV = [("Home", "Home.py"), ("Shortlist", "pages/1_Shortlist.py"),
       ("Player Profile", "pages/2_Player_Profile.py"), ("Compare", "pages/3_Compare.py"),
       ("Watchlist", "pages/4_Watchlist.py"), ("Methodology", "pages/5_Methodology.py")]


PITCH_ICON = ('<svg width="30" height="22" viewBox="0 0 34 26" aria-hidden="true">'
              '<rect x="1" y="1" width="32" height="24" rx="2" fill="none" stroke="#e9f0ea" stroke-width="1.6"/>'
              '<line x1="17" y1="1" x2="17" y2="25" stroke="#e9f0ea" stroke-width="1.6"/>'
              '<circle cx="17" cy="13" r="4.5" fill="none" stroke="#d4f05a" stroke-width="1.6"/></svg>')


def nav(active: str) -> None:
    for k in list(st.session_state):
        if k.startswith(("cmp_", "season_")):
            st.session_state[k] = st.session_state[k]

    with st.container(key="topnav"):
        cols = st.columns([3.2] + [1] * len(NAV), vertical_alignment="center")
        with cols[0]:
            with st.container(key="navbrand"):
                st.page_link("Home.py", label="African Football Scouting Tool")
        for col, (label, file) in zip(cols[1:], NAV):
            with col:
                if label == active:
                    with st.container(key="navactive"):
                        st.page_link(file, label=label, disabled=True)
                else:
                    st.page_link(file, label=label)
    st.markdown('<div class="nav-rule"></div>', unsafe_allow_html=True)


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


ROLE_ZONES = {
    "CB": [(18, 92, 90, 96)],
    "FB": [(18, 10, 120, 62), (18, 208, 120, 62)],
    "DM": [(118, 92, 72, 96)],
    "CM": [(176, 70, 92, 140)],
    "W/AM": [(268, 10, 130, 62), (268, 208, 130, 62), (272, 96, 60, 88)],
    "ST": [(334, 92, 76, 96)],
}
ROLE_LABEL_POS = {"CB": [(92, 146)], "FB": [(78, 46), (78, 244)], "DM": [(156, 146)],
                  "CM": [(222, 88)], "W/AM": [(333, 46), (333, 244)], "ST": [(374, 146)]}


def role_pitch(role: str) -> str:
    line = 'stroke="#e9f0ea" stroke-opacity="0.45" stroke-width="2" fill="none"'
    zones = "".join(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="#d4f05a" '
        f'fill-opacity="0.22" stroke="#d4f05a" stroke-width="2.5" stroke-dasharray="6 5"/>'
        for x, y, w, h in ROLE_ZONES.get(role, [])
    )
    labels = "".join(
        f'<text x="{x}" y="{y}" fill="{"#d4f05a" if r == role else "#e9f0ea"}" '
        f'fill-opacity="{1 if r == role else 0.75}" font-size="{24 if r == role else 17}" '
        f'stroke="#123024" stroke-width="6" stroke-linejoin="round" paint-order="stroke">{r}</text>'
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


CREST_CREDIT = ("**Club crests:** [FootyLogos](https://www.footylogos.com/competition/premier-soccer-league), "
                "[Brandfetch](https://brandfetch.com/) and "
                "[Orbit College FC](https://www.facebook.com/orbitsoccer/). Crests are the property of "
                "their respective clubs and are used for identification only.")


def footer() -> None:
    st.divider()
    st.caption(
        DATA_CREDIT + "  \n"
        "**Ages** are approximate.  \n"
        + CREST_CREDIT + "  \n"
        "Non-commercial portfolio project.  \n"
        "**Built by Thando Velempini**"
    )