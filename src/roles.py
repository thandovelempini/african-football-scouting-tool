"""
Combine each player's season across clubs, apply minimum minutes,
and assign scouting roles.

Roles are scored from several stats together, and a player can only be
given a role that fits their FBref source position (e.g. DFMF -> CB, FB or DM).

Reads data/processed/players_all_seasons.csv
Writes data/processed/profiles.csv
"""

from pathlib import Path

import pandas as pd

from config import MIN_MINUTES

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed" / "players_all_seasons.csv"
OUT = ROOT / "data" / "processed" / "profiles.csv"
OVERRIDES = ROOT / "data" / "manual" / "role_overrides.csv"

COUNT_COLS = ["MP", "Starts", "Min", "Gls", "Ast", "G-PK", "PK", "PKatt", "CrdY", "CrdR",
              "2CrdY", "Sh", "SoT", "Fls", "Fld", "Off", "Crs", "Int", "TklW", "OG",
              "Subs", "unSub", "Compl", "onG", "onGA", "+/-"]
PER90 = ["Gls", "Ast", "G-PK", "Sh", "SoT", "Crs", "Int", "TklW", "Fls", "Fld", "Off", "CrdY"]

ROLE_OPTIONS = {
    "GK": ["GK"],
    "DF": ["CB", "FB"],
    "DFMF": ["CB", "FB", "DM"],
    "DFFW": ["FB", "W/AM"],
    "MFDF": ["FB", "DM", "CM"],
    "MF": ["DM", "CM", "W/AM"],
    "MFFW": ["CM", "W/AM"],
    "FWMF": ["W/AM", "ST"],
    "FWDF": ["FB", "W/AM", "ST"],
    "FW": ["W/AM", "ST"],
}


ROLE_WEIGHTS = {
    "CB":   {"Int_p90": 0.75, "Crs_p90": -1.5, "Sh_p90": -0.5, "Fld_p90": -0.5, "Ast_p90": -0.5},
    "FB":   {"Crs_p90": 1.25, "TklW_p90": 0.75, "Int_p90": 0.5, "Sh_p90": -0.5, "Off_p90": -0.5},
    "DM":   {"TklW_p90": 1.0, "Int_p90": 1.0, "Fls_p90": 0.5, "Sh_p90": -0.5, "Crs_p90": -0.5},
    "CM":   {"TklW_p90": 0.5, "Int_p90": 0.5, "Ast_p90": 0.5, "Sh_p90": 0.5,
             "Crs_p90": -0.5, "Off_p90": -0.5},
    "W/AM": {"Fld_p90": 0.5, "Ast_p90": 1.0, "Crs_p90": 0.75, "Sh_p90": 0.5, "Int_p90": -0.5},
    "ST":   {"Gls_p90": 1.0, "Sh_p90": 1.0, "Off_p90": 1.0, "SoT_p90": 0.75,
             "Crs_p90": -0.5, "TklW_p90": -0.5},
}


LOW_CONFIDENCE_MARGIN = 0.25
SOURCE_PRIOR = 0.15
CM_FLOOR = 0.15
PRIMARY_ROLES = {
    "DF": {"CB", "FB"},
    "MF": {"DM", "CM", "W/AM"},
    "FW": {"ST"},
}


def combine_clubs(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("Min", ascending=False)
    counts = [c for c in COUNT_COLS if c in df.columns]

    totals = df.groupby(["season", "player_id"], as_index=False)[counts].sum(min_count=1)
    info = df.groupby(["season", "player_id"], as_index=False).agg(
        Player=("Player", "first"), Nation=("Nation", "first"), Pos=("Pos", "first"),
        primary_pos=("primary_pos", "first"), Age=("Age", "max"), Born=("Born", "first"),
        Squad=("Squad", "first"), clubs=("Squad", lambda s: " / ".join(s)),
    )
    out = info.merge(totals, on=["season", "player_id"])

    minutes = out["Min"].where(out["Min"] > 0)
    for col in PER90:
        if col in out.columns:
            out[f"{col}_p90"] = out[col] / minutes * 90
    out["+/-90"] = out["+/-"] / minutes * 90
    out["SoT%"] = (out["SoT"] / out["Sh"].where(out["Sh"] > 0)) * 100
    out["G/Sh"] = out["Gls"] / out["Sh"].where(out["Sh"] > 0)
    out["Mn/Start"] = out["Min"] / out["Starts"].where(out["Starts"] > 0)
    return out


def standardise(df: pd.DataFrame) -> pd.DataFrame:
    """z-scores within each season and source position group (DF/MF/FW), clipped to +/-3."""
    stats = sorted({s for w in ROLE_WEIGHTS.values() for s in w})
    group = df["Pos"].astype(str).str[:2]
    outfield = group.isin(["DF", "MF", "FW"])
    z = pd.DataFrame(0.0, index=df.index, columns=stats)

    for _, idx in df[outfield].groupby([df["season"], group]).groups.items():
        block = df.loc[idx, stats]
        z.loc[idx] = ((block - block.mean()) / block.std(ddof=0)).clip(-3, 3).fillna(0)
    return z


def role_scores(z: pd.DataFrame) -> pd.DataFrame:
    scores = pd.DataFrame(index=z.index)
    for role, weights in ROLE_WEIGHTS.items():
        total = sum(abs(w) for w in weights.values())
        scores[role] = sum(z[stat] * w for stat, w in weights.items()) / total
    return scores


def options_for(pos: str) -> list[str]:
    pos = str(pos)
    return ROLE_OPTIONS.get(pos) or ROLE_OPTIONS.get(pos[:2], [])


def assign_roles(df: pd.DataFrame) -> pd.DataFrame:
    scores = role_scores(standardise(df))
    roles, alts, margins = [], [], []

    for i, pos in df["Pos"].items():
        options = options_for(pos)
        if not options:
            roles.append("Unknown"); alts.append(None); margins.append(None)
            continue
        if len(options) == 1:
            roles.append(options[0]); alts.append(None); margins.append(None)
            continue

        primary = set() if str(pos).startswith("FWDF") else PRIMARY_ROLES.get(str(pos)[:2], set())

        adjusted = scores.loc[i, options] + [SOURCE_PRIOR if r in primary else 0 for r in options]
        ranked = adjusted.sort_values(ascending=False)

        if "CM" in options and ranked.index[0] != "CM" and scores.loc[i, ranked.index[0]] < CM_FLOOR:
            ranked = pd.concat([ranked[["CM"]], ranked.drop("CM")])

        roles.append(ranked.index[0])
        alts.append(ranked.index[1])
        margins.append(abs(ranked.iloc[0] - ranked.iloc[1]))


    df["role"] = roles
    df["role_alt"] = alts
    df["role_margin"] = margins
    df["role_confidence"] = pd.cut(
        df["role_margin"], [-float("inf"), LOW_CONFIDENCE_MARGIN, float("inf")],
        labels=["low", "high"],
    ).astype(object).fillna("high")
    df["role_source"] = "model"

    for role in ROLE_WEIGHTS:
        df[f"score_{role}"] = scores[role].round(3)
    df["model_role"] = df["role"]
    df["model_role_alt"] = df["role_alt"]
    df["model_role_margin"] = df["role_margin"]
    df["model_role_confidence"] = df["role_confidence"]

    return df



def apply_overrides(df: pd.DataFrame) -> pd.DataFrame:
    if not OVERRIDES.exists():
        return df

    overrides = pd.read_csv(OVERRIDES, dtype=str)
    applied = 0

    for _, o in overrides.iterrows():
        hit = df["player_id"] == o["player_id"]

        if pd.notna(o.get("season")) and o["season"]:
            hit &= df["season"] == o["season"]

        if not hit.any():
            continue

        df.loc[hit, "role"] = o["role"]
        df.loc[hit, "role_source"] = "override"
        df.loc[hit, "role_confidence"] = "high"
        applied += hit.sum()

    print(f"Applied {applied} manual role overrides")
    return df


def report(df: pd.DataFrame) -> None:
    print("Players per role and season")
    print(pd.crosstab(df["role"], df["season"], margins=True).to_string())

    print("\nLow-confidence roles per season")
    print(pd.crosstab(df["role_confidence"], df["season"]).to_string())

    print("\nTop 5 by minutes in each role, 2025-26")
    season = df[df["season"] == "2025-26"]
    for role, group in season.groupby("role"):
        top = group.nlargest(5, "Min")
        names = ", ".join(f"{p} ({pos})" for p, pos in zip(top["Player"], top["Pos"]))
        print(f"  {role:<5} {names}")


if __name__ == "__main__":
    players = combine_clubs(pd.read_csv(DATA))
    before = len(players)

    players = players[players["Min"] >= players["season"].map(MIN_MINUTES)].copy()
    print(f"Player-seasons: {before} -> {len(players)} after minimum minutes\n")

    players = apply_overrides(assign_roles(players))

    names_path = ROOT / "data" / "manual" / "name_overrides.csv"
    if names_path.exists():
        names = pd.read_csv(names_path).set_index("player_id")["display_name"]
        players["Player"] = players["player_id"].map(names).fillna(players["Player"])

    report(players)

    players.to_csv(OUT, index=False)
    print(f"\nSaved: {OUT}")