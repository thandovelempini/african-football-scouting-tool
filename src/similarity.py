"""
"Who plays like X?" - most similar players within the same role.

Each player is a vector of percentiles on their role's key metrics.
Similarity = 100 * (1 - distance / max possible distance), so 100 is an
identical profile and 0 is the opposite on every metric.

Candidates come from the profiling seasons only (full-season samples).
Queries can be any player-season, including current-season form.
A player is never matched with himself (any season).

Reads data/processed/percentiles.csv
Writes data/processed/similar_players.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

from config import PROFILE_SEASONS
from percentiles import ROLE_KEY_METRICS

ROOT = Path(__file__).resolve().parent.parent
PERCENTILES = ROOT / "data" / "processed" / "percentiles.csv"
OUT = ROOT / "data" / "processed" / "similar_players.csv"

TOP_N = 10
SIMILARITY_EXCLUDE = {"+/-90"}
CLOSEST_SHOWN = 3
EXAMPLES = [("Iqraam Rayners", "2025-26"), ("Kamogelo Sebelebele", "2025-26"),
            ("Riaan Hanamub", "2025-26"), ("Relebohile Mofokeng", "2025-26")]


def role_matrix(df: pd.DataFrame, role: str) -> tuple[pd.DataFrame, list[str]]:
    cols = [f"pct_{m}" for m in ROLE_KEY_METRICS[role] if m not in SIMILARITY_EXCLUDE]
    group = df[df["role"] == role]
    return group, cols


def similar_to(df: pd.DataFrame, player_id: str, season: str, n: int = TOP_N) -> pd.DataFrame:
    query = df[(df["player_id"] == player_id) & (df["season"] == season)]
    if query.empty:
        raise ValueError(f"No row for {player_id} in {season}")
    query = query.iloc[0]
    role = query["role"]
    if role not in ROLE_KEY_METRICS:
        return pd.DataFrame()

    group, cols = role_matrix(df, role)
    candidates = group[group["season"].isin(PROFILE_SEASONS) & (group["player_id"] != player_id)]

    q = query[cols].astype(float).fillna(50).to_numpy() / 100
    c = candidates[cols].astype(float).fillna(50).to_numpy() / 100
    diffs = np.abs(c - q)
    distance = np.sqrt((diffs ** 2).sum(axis=1))
    similarity = 100 * (1 - distance / np.sqrt(len(cols)))

    result = candidates[["player_id", "season", "Player", "Squad", "Age", "Min"]].copy()
    result["similarity"] = similarity.round(1)
    metric_names = [c.removeprefix("pct_") for c in cols]
    result["closest_metrics"] = [
        ", ".join(metric_names[j] for j in np.argsort(row)[:CLOSEST_SHOWN]) for row in diffs
    ]
    result = result.sort_values("similarity", ascending=False).drop_duplicates("player_id")
    return result.head(n).reset_index(drop=True)

def build_all(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, q in df[df["role"].isin(ROLE_KEY_METRICS)].iterrows():
        sims = similar_to(df, q["player_id"], q["season"])
        sims = sims.rename(columns={
            "player_id": "similar_id", "season": "similar_season", "Player": "similar_player",
            "Squad": "similar_squad", "Age": "similar_age", "Min": "similar_min",
        })
        sims.insert(0, "rank", range(1, len(sims) + 1))
        for col in ["role", "Squad", "Player", "season", "player_id"]:
            sims.insert(0, col, q[col])
        rows.append(sims)
    return pd.concat(rows, ignore_index=True)


def report(df: pd.DataFrame, out: pd.DataFrame) -> None:
    for name, season in EXAMPLES:
        row = df[(df["Player"] == name) & (df["season"] == season)]
        if row.empty:
            print(f"\n{name} {season}: not found")
            continue
        r = row.iloc[0]
        print(f"\nMost similar to {name} ({r['Squad']}, {r['role']}, {season})")
        top = similar_to(df, r["player_id"], season, n=5)
        for _, s in top.iterrows():
            print(f"  {s['similarity']:5.1f}  {s['Player']} ({s['Squad']}, {s['season']})"
                  f"  - closest on: {s['closest_metrics']}")

    best = out[out["rank"] == 1].groupby("role")["similarity"].median()
    print("\nMedian similarity of each player's closest match, by role")
    print(best.round(1).to_string())


if __name__ == "__main__":
    pct = pd.read_csv(PERCENTILES, dtype={"player_id": str})
    out = build_all(pct)
    report(pct, out)

    out.to_csv(OUT, index=False)
    print(f"\nSaved: {OUT} ({len(out)} rows)")