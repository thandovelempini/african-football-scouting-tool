import pandas as pd
import sys
from pathlib import Path

import streamlit as st
import altair as alt


sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from app_data import cards, footer, hero, load_percentiles, style  # noqa: E402
from config import CURRENT_SEASON, MIN_MINUTES, PROFILE_SEASONS

st.set_page_config(page_title="African Football Scouting Tool", page_icon=":material/sports_soccer:",
                   layout="wide")
style()

hero("African Football Scouting Tool",
     "How can player performance data help identify promising recruitment targets in "
     "African football? Starting with South Africa's Betway Premiership",
     kicker="Open-data scouting · 2024-25 to 2026-27")

cards([
    ("Player-seasons", "573", "900+ minutes (450+ for 2026-27)"),
    ("Scouting roles", "6", "CB, FB, DM, CM, W/AM, ST"),
    ("Forward role check", "86%", "model agreement with checked positions"),
    ("Seasons", "2024-27", "two full seasons + current form"),
])

st.subheader("Start here")

START = [
    ("Shortlist", "Pick a role, weight what matters, and get a ranked list with a reason "
                  "for every player", "Shortlist", "Build a shortlist"),
    ("Player profile", "Percentiles, role history, current form and the most similar players",
     "Player_Profile", "Open a profile"),
    ("Compare", "Put two or three players side by side, as percentiles and per-90 values",
     "Compare", "Compare players"),
    ("Watchlist", "Keep track of players worth following up, with a status and notes",
     "Watchlist", "Open watchlist"),
]
st.markdown(
    '<div class="start-grid">' + "".join(
        f'<a class="start-card" href="{page}" target="_self">'
        f'<div class="start-title">{title}</div>'
        f'<div class="start-text">{text}</div>'
        f'<div class="start-link">{link} →</div></a>'
        for title, text, page, link in START
    ) + '</div>',
    unsafe_allow_html=True,
)

st.subheader("Data coverage",
             help="Outfield players who met the minutes threshold in each season. "
                  "Goalkeepers are not included yet.")


pct = load_percentiles()
seasons = sorted(pct["season"].unique())
coverage = (pct.assign(Club=pct["Squad"].str.split("/"))
            .explode("Club")
            .assign(Club=lambda d: d["Club"].str.strip())
            .groupby(["Club", "season"]).size().reset_index(name="Players"))

grid = (pd.MultiIndex.from_product([sorted(coverage["Club"].unique()), seasons],
                                   names=["Club", "season"])
        .to_frame(index=False).merge(coverage, how="left"))
grid["Label"] = grid["Players"].map(lambda v: "–" if pd.isna(v) else f"{int(v)}")

base = alt.Chart(grid).encode(
    x=alt.X("season:N", sort=seasons, title=None,
            axis=alt.Axis(orient="top", labelColor="#e8ecf2", labelFontSize=13,
                          labelAngle=0, ticks=False, domain=False)),
    y=alt.Y("Club:N", title=None,
            axis=alt.Axis(labelColor="#e8ecf2", labelFontSize=13, labelLimit=200,
                          ticks=False, domain=False)),
)
heat = base.mark_rect(cornerRadius=4, stroke="#0e1218", strokeWidth=3).encode(
    color=alt.Color("Players:Q", legend=None,
                    scale=alt.Scale(range=["#1c2b3f", "#4c8fd9"])),
    tooltip=["Club", alt.Tooltip("season:N", title="Season"),
             alt.Tooltip("Players:Q", title="Qualifying players")],
)
labels = base.mark_text(fontSize=13, font="IBM Plex Mono").encode(
    text="Label:N",
    color=alt.condition("datum.Players > 0", alt.value("#e8ecf2"), alt.value("#5a6778")),
)

chart_col, note_col = st.columns([3, 2], gap="large")
with chart_col:
    st.altair_chart((heat + labels).properties(height=30 * grid["Club"].nunique())
                    .configure_view(strokeWidth=0), use_container_width=True)
with note_col:
    totals = grid.groupby("season")["Players"].sum()
    cards([(s, f"{int(totals[s])}",
            "full season" if s in PROFILE_SEASONS else "current form, small sample")
           for s in seasons])
    st.caption(f"**Minimum minutes:** {MIN_MINUTES[seasons[0]]} for full seasons, "
               f"{MIN_MINUTES[CURRENT_SEASON]} for {CURRENT_SEASON}. "
               "A dash means the club was not in the league that season. "
               "Royal AM has no 2024-25 data on FBref.")

st.markdown(
    '<p style="color:#93a0b2">Roles, percentiles and fit scores are built from open FBref data. '
    '<a href="Methodology" target="_self" style="font-weight:600">How it works →</a></p>',
    unsafe_allow_html=True,
)

footer()