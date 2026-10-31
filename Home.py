import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from app_data import footer  # noqa: E402

st.set_page_config(page_title="African Football Scouting Tool", layout="wide")

st.title("African Football Scouting Tool")
st.markdown(
    "**How can player performance data help identify promising recruitment targets "
    "in African football?** This tool starts with South Africa's Betway Premiership."
)

st.subheader("What you can do")
st.markdown(
    "- **Shortlist**: pick a role, set what matters most, and get a ranked list with a "
    "plain-language reason for every player.\n"
    "- More pages (player profiles, comparisons, similar players) are on the way."
)

st.subheader("How it works")
st.markdown(
    "- **Seasons**: 2024-25 and 2025-26 (full seasons, 900+ minutes) drive the rankings. "
    "2026-27 is shown separately as current form (450+ minutes).\n"
    "- **Roles**: assigned from FBref positions plus several stats together, validated "
    "against independently checked positions and corrected with documented overrides.\n"
    "- **Percentiles**: each player is ranked only against players in the same role, "
    "pooled across both full seasons.\n"
    "- **Fit score**: a weighted average of those percentiles on the stats you choose."
)

st.subheader("Limitations")
st.markdown(
    "- Open data only: no passing, dribbling, duel or xG data, so creative and "
    "build-up qualities are under-represented.\n"
    "- A standard possession adjustment was tested and rejected: it over-corrected "
    "every role in this league.\n"
    "- Goalkeepers are not yet included."
)

footer()