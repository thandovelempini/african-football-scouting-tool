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

SHORT_LABELS = {
    "Gls_p90": "Goals", "G-PK_p90": "Non-penalty goals", "Ast_p90": "Assists",
    "Sh_p90": "Shots", "SoT_p90": "Shots on target", "SoT%": "Shot accuracy",
    "G/Sh": "Finishing", "Crs_p90": "Crosses", "Fld_p90": "Fouls drawn",
    "Off_p90": "Offsides", "TklW_p90": "Tackles won", "Int_p90": "Interceptions",
    "Fls_p90": "Few fouls", "CrdY_p90": "Few cards", "+/-90": "Goal difference",
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


@st.cache_data
def load_profiles() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "profiles.csv", dtype={"player_id": str})


@st.cache_data
def load_similar() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "similar_players.csv",
                       dtype={"player_id": str, "similar_id": str})


def footer() -> None:
    st.divider()
    st.caption(DATA_CREDIT + " Ages are approximate (current year minus birth year).")