"""
Ranked recruitment shortlists with plain-language explanations.

A scout picks a role, filters (age, minutes, clubs to exclude) and the stats
that matter most. Each player is scored on their most recent profiling season,
with their other full season used to judge consistency and 2026-27 shown as
current form.

Reads data/processed/percentiles.csv
"""

from pathlib import Path

import pandas as pd

from config import CURRENT_SEASON, PROFILE_SEASONS
from percentiles import ROLE_KEY_METRICS

ROOT = Path(__file__).resolve().parent.parent
PERCENTILES = ROOT / "data" / "processed" / "percentiles.csv"

ROLE_NAMES = {"CB": "centre-backs", "FB": "full-backs", "DM": "defensive midfielders",
              "CM": "central midfielders", "W/AM": "wide/attacking midfielders", "ST": "strikers"}

METRIC_LABELS = {
    "Gls_p90": "goals per 90", "G-PK_p90": "non-penalty goals per 90", "Ast_p90": "assists per 90",
    "Sh_p90": "shots per 90", "SoT_p90": "shots on target per 90", "SoT%": "shot accuracy",
    "G/Sh": "goals per shot", "Crs_p90": "crosses per 90", "Fld_p90": "fouls drawn per 90",
    "Off_p90": "avoiding offsides", "TklW_p90": "tackles won per 90", "Int_p90": "interceptions per 90",
    "Fls_p90": "discipline (few fouls)", "CrdY_p90": "discipline (few cards)", "+/-90": "on-pitch goal difference",
}

DEFAULT_EXCLUDE = {"+/-90"}
STANDOUT = 80
CONSISTENT_GAP = 15
DISCIPLINE = {"Fls_p90", "CrdY_p90"}

def default_priorities(role: str) -> dict[str, float]:
    return {m: (0.25 if m in DISCIPLINE else 1.0)
            for m in ROLE_KEY_METRICS[role] if m not in DEFAULT_EXCLUDE}


def score(df: pd.DataFrame, priorities: dict[str, float]) -> pd.Series:
    total = sum(priorities.values())
    weighted = sum(df[f"pct_{m}"].fillna(50) * w for m, w in priorities.items())
    return (weighted / total).round(1)


def explain(row: pd.Series, role: str, priorities: dict[str, float]) -> str:
    standouts = sorted(
        ((m, row[f"pct_{m}"]) for m in priorities if pd.notna(row[f"pct_{m}"]) and row[f"pct_{m}"] >= STANDOUT),
        key=lambda x: (-priorities[x[0]], -x[1]),
    )[:3]
    core = [m for m, w in priorities.items() if w >= 1]

    parts = []
    if standouts:
        top = [f"top {max(1, int(100 - p))}% for {METRIC_LABELS.get(m, m)}" for m, p in standouts]
        parts.append(f"{'; '.join(top)} among {ROLE_NAMES[role]}")
        if not any(m in core for m, _ in standouts):
            parts.append("no standout in the main priority stats ("
                         + ", ".join(METRIC_LABELS.get(m, m) for m in core) + ")")
    else:
        parts.append(f"balanced profile with no single standout metric among {ROLE_NAMES[role]}")

    if pd.notna(row.get("other_score")):
        if abs(row["score"] - row["other_score"]) <= CONSISTENT_GAP:
            parts.append(f"consistent across both seasons ({row['other_score']:.0f} the other year)")
        elif row["score"] > row["other_score"]:
            parts.append(f"improving ({row['other_score']:.0f} the previous season)")
        else:
            parts.append(f"down on the other season ({row['other_score']:.0f})")
    else:
        parts.append("one qualifying full season only")

    if pd.notna(row.get("form_score")):
        parts.append(f"current form score {row['form_score']:.0f} (small sample)")
    if row["season"] != max(PROFILE_SEASONS):
        parts.append(f"last qualifying season {row['season']}: Check current status")
    if pd.notna(row.get("Age")):
        parts.append(f"aged {int(row['Age'])}")
    if row.get("role_confidence") == "low":
        parts.append(f"borderline {row['role_alt']} profile")
    text = "; ".join(parts)
    return text[0].upper() + text[1:] + "."


def build_shortlist(pct: pd.DataFrame, role: str, priorities: dict[str, float] | None = None,
                    min_age: int | None = None, max_age: int | None = None,
                    min_minutes: int | None = None, exclude_clubs: list[str] | None = None,
                    top_n: int = 15) -> pd.DataFrame:
    priorities = priorities or default_priorities(role)
    df = pct[pct["role"] == role].copy()
    df["score"] = score(df, priorities)

    full = df[df["season"].isin(PROFILE_SEASONS)].sort_values("season", ascending=False)
    latest = full.drop_duplicates("player_id", keep="first").copy()
    other = full[~full.index.isin(latest.index)].set_index("player_id")["score"]
    latest["other_score"] = latest["player_id"].map(other)

    form = df[df["season"] == CURRENT_SEASON].set_index("player_id")["score"]
    latest["form_score"] = latest["player_id"].map(form)

    if min_age is not None:
        latest = latest[latest["Age"] >= min_age]
    if max_age is not None:
        latest = latest[latest["Age"] <= max_age]
    if min_minutes is not None:
        latest = latest[latest["Min"] >= min_minutes]
    if exclude_clubs:
        latest = latest[~latest["Squad"].isin(exclude_clubs)]

    shortlist = latest.nlargest(top_n, "score").copy()
    shortlist["why"] = shortlist.apply(lambda r: explain(r, role, priorities), axis=1)
    cols = ["Player", "Squad", "season", "Age", "Min", "score", "other_score", "form_score", "why"]
    return shortlist[cols].reset_index(drop=True)


def show(title: str, sl: pd.DataFrame) -> None:
    print(f"\n{title}")
    for i, r in sl.iterrows():
        print(f"  {i + 1:>2}. {r['Player']} ({r['Squad']}, {r['season']}) score {r['score']:.0f}")
        print(f"      {r['why']}")


if __name__ == "__main__":
    pct = pd.read_csv(PERCENTILES, dtype={"player_id": str})

    show("Young ball-winning DMs (U25), excluding Sundowns and Pirates",
         build_shortlist(pct, "DM", priorities={"TklW_p90": 2, "Int_p90": 2, "Fls_p90": 0.5},
                         max_age=24, exclude_clubs=["Sundowns", "Orlando Pirates"], top_n=5))
    
    show("Strikers, scoring-first",
         build_shortlist(pct, "ST", priorities={"G-PK_p90": 2, "SoT_p90": 1, "G/Sh": 1}, top_n=5))

    show("Creative wide players (U24)",
         build_shortlist(pct, "W/AM", priorities={"Ast_p90": 2, "Crs_p90": 1, "Fld_p90": 1},
                         max_age=23, top_n=5))