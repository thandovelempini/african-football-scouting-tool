"""
Scouting watchlist: players a scout wants to follow up, with a status and a note
"""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST = ROOT / "data" / "watchlist.csv"

COLUMNS = ["player_id", "Player", "Squad", "role", "season", "status", "note", "added"]
STATUSES = ["To watch", "Watch live", "Shortlisted", "Rejected"]


def load() -> pd.DataFrame:
    if not WATCHLIST.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(WATCHLIST, dtype={"player_id": str, "note": str})
    for col in COLUMNS:
        if col not in df:
            df[col] = ""
    df["note"] = df["note"].fillna("")
    df["status"] = df["status"].where(df["status"].isin(STATUSES), STATUSES[0])
    return df[COLUMNS]


def save(df: pd.DataFrame) -> None:
    WATCHLIST.parent.mkdir(parents=True, exist_ok=True)
    df[COLUMNS].to_csv(WATCHLIST, index=False)


def contains(player_id: str) -> bool:
    return player_id in set(load()["player_id"])


def add(player_id: str, player: str, squad: str, role: str, season: str) -> None:
    df = load()
    if player_id in set(df["player_id"]):
        return
    new = pd.DataFrame([{
        "player_id": player_id, "Player": player, "Squad": squad, "role": role,
        "season": season, "status": STATUSES[0], "note": "", "added": date.today().isoformat(),
    }])
    save(pd.concat([df, new], ignore_index=True))


def remove(player_id: str) -> None:
    df = load()
    save(df[df["player_id"] != player_id])


def merge(other: pd.DataFrame) -> int:
    df = load()
    other = other.copy()
    other["player_id"] = other["player_id"].astype(str)
    for col in COLUMNS:
        if col not in other:
            other[col] = ""
    new = other[~other["player_id"].isin(df["player_id"])][COLUMNS]
    if not new.empty:
        save(pd.concat([df, new], ignore_index=True))
    return len(new)


def watch_button(player_id: str, player: str, squad: str, role: str, season: str,
                 key: str) -> None:
    if contains(player_id):
        st.button("On watchlist", icon=":material/bookmark_added:", key=key,
                  on_click=remove, args=(player_id,), help="Click to remove from the watchlist")
    else:
        st.button("Add to watchlist", icon=":material/bookmark_add:", key=key,
                  on_click=add, args=(player_id, player, squad, role, season))