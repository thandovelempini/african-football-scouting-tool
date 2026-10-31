"""Shared data loading and labels for the Streamlit app."""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

ROLE_LABELS = {
    "ST": "Striker", "W/AM": "Winger / attacking midfielder", "CM": "Central midfielder",
    "DM": "Defensive midfielder", "FB": "Full-back", "CB": "Centre-back",
}

FIT_SCORE_HELP = ("Weighted average of the player's percentiles on the stats you prioritise, "
                  "compared with players in the same role. 0-100. Not an overall rating "
                  "or a probability of success.")
FORM_HELP = "2026-27 so far. Small sample: treat as an early signal, not a full-season verdict."
SIMILARITY_HELP = ("Profile similarity score: how close two players' percentile profiles are. "
                   "Use it to rank matches, not as a percentage of likeness.")
DATA_CREDIT = "Data: [FBref.com](https://fbref.com) (Betway Premiership player stats)."


@st.cache_data
def load_percentiles() -> pd.DataFrame:
    pct = pd.read_csv(PROCESSED / "percentiles.csv", dtype={"player_id": str})
    profiles = pd.read_csv(PROCESSED / "profiles.csv", dtype={"player_id": str},
                           usecols=["player_id", "Born"])
    born = pd.to_numeric(profiles.dropna(subset=["Born"]).drop_duplicates("player_id")
                         .set_index("player_id")["Born"], errors="coerce")
    pct["season_age"] = pct["Age"]
    pct["Age"] = date.today().year - pct["player_id"].map(born)
    return pct


def footer() -> None:
    st.divider()
    st.caption(DATA_CREDIT + " Ages are approximate (current year minus birth year).")