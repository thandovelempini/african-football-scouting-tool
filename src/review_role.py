"""
Flag role assignments that need a human check.

Flags:
  - low confidence: the best and second-best role scores are close
  - role change: the player's role differs between seasons
    (a tactical change, a classification error, or different source positions)

Reads data/processed/profiles.csv
Writes outputs/role_review.csv (flagged profiling-season players, most minutes first)
"""

from pathlib import Path

import pandas as pd

from config import PROFILE_SEASONS

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed" / "profiles.csv"
OUT = ROOT / "outputs" / "role_review.csv"

CLUB_MIN = {"GK": 1, "CB": 1, "FB": 1}
CLUB_MAX = {"GK": 2, "ST": 4}
REVIEW_COLS = ["season", "Squad", "Player", "player_id", "Pos", "role", "role_alt",
               "role_margin", "role_source", "Min", "Crs_p90", "Sh_p90", "Fld_p90",
               "TklW_p90", "Int_p90", "Ast", "flags", "model_role", "model_role_alt", 
               "model_role_margin", "model_role_confidence",]


def role_changes(df: pd.DataFrame) -> pd.Series:
    history = (
        df.sort_values("season")
        .groupby("player_id")
        .apply(
            lambda g: " -> ".join(
                f"{r} ({p}, {s})"
                for s, r, p in zip(g["season"], g["model_role"], g["Pos"])
            )
        )
    )
    changed = df.groupby("player_id")["model_role"].nunique() > 1
    return df["player_id"].map(history[changed])



def build_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Create separate review flags for model uncertainty, role changes and overrides."""
    result = pd.DataFrame(index=df.index)

    result["low_confidence"] = (
        df["model_role_confidence"].eq("low")
        & df["role_source"].ne("override")
    )


    model_changes = (
        df.groupby("player_id")["role"]
        .transform("nunique")
        .gt(1)
    )
    
    result["model_role_change"] = model_changes

    result["manually_overridden"] = df["role_source"].eq("override")

    return result



def club_composition(df: pd.DataFrame) -> None:
    counts = pd.crosstab([df["season"], df["Squad"]], df["role"])
    problems = []
    for (season, club), row in counts.iterrows():
        for role, low in CLUB_MIN.items():
            if row.get(role, 0) < low:
                problems.append(f"{season} {club}: no {role}")
        for role, high in CLUB_MAX.items():
            if row.get(role, 0) > high:
                problems.append(f"{season} {club}: {row[role]} {role}s")

    print("Club squads with unusual role mixes")
    print("\n".join(f"  {p}" for p in problems) if problems else "  none")



if __name__ == "__main__":
    df = pd.read_csv(DATA)
    df = df[df["season"].isin(PROFILE_SEASONS)].copy()

    print("Profiling records:", len(df))
    print("Missing role margins:", df["role_margin"].isna().sum())
    print("Records with margins:", df["role_margin"].notna().sum())
    print("Goalkeeper records:", (df["role"] == "GK").sum())

    print("\nMissing margins by role:")
    print(
        df.loc[df["role_margin"].isna(), "role"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nRole margin distribution (profiling seasons)")
    print(
        df["role_margin"]
        .describe(percentiles=[0.1, 0.25, 0.5])
        .round(2)
        .to_string()
    )

    flags = build_flags(df)
    df = df.join(flags)

    club_composition(df)

    print("\nReview summary")
    print("Unresolved low-confidence records:", df["low_confidence"].sum())
    print("Model role-change records:", df["model_role_change"].sum())
    print("Manually overridden records:", df["manually_overridden"].sum())

    
    unresolved = df[
        (df["low_confidence"] | df["model_role_change"])
        & ~df["manually_overridden"]
    ].copy()

    # Remove player-seasons that have already been reviewed
    reviewed_path = ROOT / "data" / "manual" / "role_reviewed.csv"

    if reviewed_path.exists():
        reviewed = pd.read_csv(
            reviewed_path,
            dtype={"player_id": str, "season": str},
        )

        reviewed_keys = set(
            zip(reviewed["player_id"], reviewed["season"])
        )

        unresolved_keys = pd.MultiIndex.from_frame(
            unresolved[["player_id", "season"]]
        )

        unresolved = unresolved.loc[
            ~unresolved_keys.isin(reviewed_keys)
        ].copy()


    unresolved["priority"] = (
        unresolved["low_confidence"].astype(int)
        + unresolved["model_role_change"].astype(int)
    )

    unresolved = unresolved.sort_values(
        ["priority", "Min"], ascending=False
    )

    print("\nUnresolved records by final role")
    print(unresolved.groupby("role").size().to_string())

    
    # Separate role changes from low-confidence-only records
    role_changes_only = unresolved[
        unresolved["model_role_change"]
    ].copy()

    low_confidence_only = unresolved[
        unresolved["low_confidence"]
        & ~unresolved["model_role_change"]
    ].copy()

    print("\nRole changes to review:", len(role_changes_only))
    print(
        role_changes_only[
            ["season", "Player", "player_id", "role",
             "model_role", "model_role_alt", "Min"]
        ].to_string(index=False)
    )

    print("\nLow-confidence-only records:", len(low_confidence_only))
    print(
        low_confidence_only[
            ["season", "Player", "player_id", "role",
             "model_role", "model_role_alt",
             "model_role_margin", "Min"]
        ].to_string(index=False)
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    unresolved.to_csv(OUT, index=False)
    print(f"\nSaved: {OUT}")
