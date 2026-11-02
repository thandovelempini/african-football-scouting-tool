import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from app_data import cards, footer, hero, style  # noqa: E402

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
c1, c2, c3 = st.columns(3)
with c1:
    with st.container(border=True):
        st.markdown("**Shortlist**")
        st.caption("Pick a role, weight what matters, and get a ranked list with a reason for every player")
        st.page_link("pages/1_Shortlist.py", label="Build a shortlist", icon=":material/format_list_numbered:")
with c2:
    with st.container(border=True):
        st.markdown("**Player Profile**")
        st.caption("Percentiles, role history, current form and the most similar players")
        st.page_link("pages/2_Player_Profile.py", label="Open a profile", icon=":material/person:")
with c3:
    with st.container(border=True):
        st.markdown("**Compare**")
        st.caption("Put two or three players side by side, as percentiles and per-90 values")
        st.page_link("pages/3_Compare.py", label="Compare players", icon=":material/compare_arrows:")

st.subheader("How it works")
st.markdown(
    "- **Roles** come from FBref positions plus several stats together, validated against "
    "independently checked positions and corrected with documented overrides.\n"
    "- **Percentiles** rank each player only against players in the same role, pooled across "
    "both full seasons.\n"
    "- **Fit score** is a weighted average of those percentiles on the stats you choose. "
    "It is not an overall rating or a probability of success."
)

with st.expander("Limitations"):
    st.markdown(
        "- **Open data only.** There's no passing, dribbling, duel or xG data, so creative, "
        "build-up and aerial strengths don't show up. Centre-back profiles are the thinnest.\n"
        "- **No possession adjustment.** The standard adjustment was tested, but it "
        "over-corrected every role in this league, so raw stats are used.\n"
        "- **Roles are estimated from stats**, not from watching matches. "
        "Borderline cases are marked.\n"
        "- **No goalkeepers yet.**"
    )

footer()