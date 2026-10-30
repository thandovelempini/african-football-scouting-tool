"""
Explore minutes played per season to choose a minimum-minutes threshold.

"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed" / "players_all_seasons.csv"
OUT_DIR = ROOT / "outputs"

THRESHOLDS = [450, 600, 900, 1350, 1800]


def season_totals(df: pd.DataFrame) -> pd.DataFrame:
    """One row per player per season: players at two clubs have their minutes summed."""
    return (
        df.groupby(["season", "player_id"], as_index=False)
        .agg(Player=("Player", "first"), primary_pos=("primary_pos", "first"),
             Min=("Min", "sum"), clubs=("Squad", "nunique"))
    )


def summarise(totals: pd.DataFrame) -> None:
    print("Minutes per player-season")
    summary = totals.groupby("season")["Min"].describe(percentiles=[0.25, 0.5, 0.75])
    print(summary[["count", "25%", "50%", "75%", "max"]].round(0).to_string())

    print("\nPlayers at or above each threshold")
    counts = pd.DataFrame({
        f"{t}+": totals[totals["Min"] >= t].groupby("season").size() for t in THRESHOLDS
    }).fillna(0).astype(int)
    print(counts.to_string())

    print("\nBy position at 900+ minutes")
    by_pos = (
        totals[totals["Min"] >= 900]
        .pivot_table(index="season", columns="primary_pos", values="player_id",
                     aggfunc="count", fill_value=0)
    )
    print(by_pos.to_string())

    multi = totals[totals["clubs"] > 1]
    print(f"\nPlayer-seasons combining 2+ clubs: {len(multi)}")


def plot(totals: pd.DataFrame) -> None:
    seasons = sorted(totals["season"].unique())
    fig, axes = plt.subplots(1, len(seasons), figsize=(5 * len(seasons), 4), sharey=True)

    for ax, season in zip(axes, seasons):
        mins = totals.loc[totals["season"] == season, "Min"]
        ax.hist(mins, bins=30, color="#2f6f4f", edgecolor="white")
        for t in (900, 1350):
            ax.axvline(t, color="#c0392b", linestyle="--", linewidth=1)
            ax.text(t, ax.get_ylim()[1] * 0.95, f" {t}", color="#c0392b", fontsize=8)
        ax.set_title(season)
        ax.set_xlabel("Minutes played")
    axes[0].set_ylabel("Players")

    fig.suptitle("Betway Premiership: minutes per player-season")
    fig.tight_layout()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "minutes_distribution.png"
    fig.savefig(out, dpi=150)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    totals = season_totals(pd.read_csv(DATA))
    summarise(totals)
    plot(totals)