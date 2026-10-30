"""
Possession-adjust defensive stats so players at low- and high-possession
clubs can be compared fairly.

    adjusted = stat_p90 * 50 / opponent possession
    opponent possession = 100 - team possession

Players at two clubs in a season get a minutes-weighted team possession.

Reads:
    data/processed/profiles.csv
    data/processed/players_all_seasons.csv   (minutes per club)
    data/raw/fbref/<season>_squad_standard.csv  (Squad Standard Stats, Squad Stats tab)
Writes:
    data/processed/profiles_adjusted.csv
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "fbref"
PROFILES = ROOT / "data" / "processed" / "profiles.csv"
ALL_SEASONS = ROOT / "data" / "processed" / "players_all_seasons.csv"
OUT = ROOT / "data" / "processed" / "profiles_adjusted.csv"

ADJUST = ["TklW_p90", "Int_p90"]


def load_squad_possession(season: str) -> pd.DataFrame:
    path = RAW_DIR / f"{season}_squad_standard.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip().strip('"').startswith("Squad,")), None)
    if start is None:
        raise ValueError(f"No 'Squad' header row in {path.name}: is this the squad standard table?")

    df = pd.read_csv(path, skiprows=start, encoding="utf-8-sig")
    df = df[~df["Squad"].astype(str).str.startswith("vs ")]
    df["Poss"] = pd.to_numeric(df["Poss"], errors="coerce")
    if df["Poss"].isna().any():
        missing = ", ".join(df.loc[df["Poss"].isna(), "Squad"])
        raise ValueError(f"{season}: missing possession for {missing}")
    return df[["Squad", "Poss"]].assign(season=season)


def player_possession(seasons: list[str]) -> pd.DataFrame:
    poss = pd.concat([load_squad_possession(s) for s in seasons], ignore_index=True)

    stints = pd.read_csv(ALL_SEASONS, usecols=["season", "player_id", "Squad", "Min"])
    stints = stints[stints["season"].isin(seasons)].merge(poss, on=["season", "Squad"], how="left")

    unmatched = stints[stints["Poss"].isna()][["season", "Squad"]].drop_duplicates()
    if not unmatched.empty:
        raise ValueError(f"Clubs with no possession match:\n{unmatched.to_string(index=False)}")

    stints["poss_x_min"] = stints["Poss"] * stints["Min"]
    weighted = stints.groupby(["season", "player_id"], as_index=False)[["poss_x_min", "Min"]].sum()
    weighted["team_poss"] = weighted["poss_x_min"] / weighted["Min"]
    return weighted[["season", "player_id", "team_poss"]], poss


def adjust(df: pd.DataFrame) -> pd.DataFrame:
    df["opp_poss"] = 100 - df["team_poss"]
    factor = 50 / df["opp_poss"]
    for col in ADJUST:
        df[f"{col}_padj"] = df[col] * factor
    df["def_actions_p90_padj"] = df[[f"{c}_padj" for c in ADJUST]].sum(axis=1)
    return df


def check(df: pd.DataFrame, poss: pd.DataFrame) -> None:
    print("Team possession by season")
    print(poss.pivot(index="Squad", columns="season", values="Poss").round(1).to_string())

    outfield = df[df["role"] != "GK"]
    raw = outfield["TklW_p90"] + outfield["Int_p90"]
    corr_before = raw.corr(outfield["team_poss"])
    corr_after = outfield["def_actions_p90_padj"].corr(outfield["team_poss"])
    print("\nCorrelation of tackles + interceptions with team possession (outfield)")
    print(f"  before adjustment: {corr_before:+.2f}")
    print(f"  after adjustment:  {corr_after:+.2f}   (closer to 0 = possession effect removed)")

    print(f"\nMissing possession: {df['team_poss'].isna().sum()} players")


if __name__ == "__main__":
    profiles = pd.read_csv(PROFILES)
    seasons = sorted(profiles["season"].unique())

    team_poss, poss = player_possession(seasons)
    profiles = adjust(profiles.merge(team_poss, on=["season", "player_id"], how="left"))
    check(profiles, poss)

    profiles.to_csv(OUT, index=False)
    print(f"\nSaved: {OUT}")