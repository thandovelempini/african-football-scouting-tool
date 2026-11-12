"""
List players with no birth year and add them to data/manual/birth_years.csv
so they can be filled in by hand. Rows already in that file are kept.

Reads data/processed/profiles.csv
Writes data/manual/birth_years.csv (player_id, Player, clubs, seasons, born, source)
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "data" / "processed" / "profiles.csv"
OUT = ROOT / "data" / "manual" / "birth_years.csv"

profiles = pd.read_csv(PROFILES, dtype={"player_id": str})
profiles = profiles[profiles["role"] != "GK"]

has_born = profiles.groupby("player_id")["Born"].apply(lambda s: s.notna().any())
missing_ids = has_born[~has_born].index

missing = (profiles[profiles["player_id"].isin(missing_ids)]
           .groupby("player_id")
           .agg(Player=("Player", "first"),
                clubs=("Squad", lambda s: " / ".join(sorted(s.unique()))),
                seasons=("season", lambda s: " / ".join(sorted(s.unique()))),
                minutes=("Min", "sum"))
           .sort_values("minutes", ascending=False)
           .reset_index())
missing["born"] = pd.NA
missing["source"] = ""

if OUT.exists():
    existing = pd.read_csv(OUT, dtype={"player_id": str})
    new = missing[~missing["player_id"].isin(existing["player_id"])]
    out = pd.concat([existing, new.drop(columns="minutes")], ignore_index=True)
else:
    new = missing
    out = missing.drop(columns="minutes")

out.to_csv(OUT, index=False)

filled = out["born"].notna().sum()
print(f"Players with no birth year: {len(missing)}")
print(f"In {OUT.name}: {len(out)} rows, {filled} filled, {len(out) - filled} still empty")
print(f"Added this run: {len(new)}\n")
print(missing[["player_id", "Player", "clubs", "seasons", "minutes"]].to_string(index=False))