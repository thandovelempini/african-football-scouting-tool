"""
Percentile ranks for each outfield player within their role.

Reference pool: every player in the same role across the profiling seasons
(2024-25 + 2025-26 pooled), so small roles like ST still have ~35 players.
Every player-season, including current-season form, is ranked against that
same pool, so a 2026-27 percentile means "compared with a normal full season".

Reads data/processed/profiles.csv
Writes data/processed/percentiles.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

from config import CURRENT_SEASON, PROFILE_SEASONS

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "data" / "processed" / "profiles.csv"
OUT = ROOT / "data" / "processed" / "percentiles.csv"

METRICS = {
    "Gls_p90": True, "G-PK_p90": True, "Ast_p90": True,
    "Sh_p90": True, "SoT_p90": True, "SoT%": True, "G/Sh": True,
    "Crs_p90": True, "Fld_p90": True, "Off_p90": False,
    "TklW_p90": True, "Int_p90": True, "Fls_p90": False, "CrdY_p90": False,
    "+/-90": True,
}

ROLE_KEY_METRICS = {
    "CB":   ["Int_p90", "TklW_p90", "Fls_p90", "CrdY_p90", "+/-90"],
    "FB":   ["Crs_p90", "TklW_p90", "Int_p90", "Ast_p90", "Fld_p90", "+/-90"],
    "DM":   ["TklW_p90", "Int_p90", "Fls_p90", "CrdY_p90", "+/-90"],
    "CM":   ["TklW_p90", "Int_p90", "Ast_p90", "Sh_p90", "Fld_p90", "+/-90"],
    "W/AM": ["Ast_p90", "Gls_p90", "Crs_p90", "Fld_p90", "Sh_p90", "SoT_p90", "+/-90"],
    "ST":   ["G-PK_p90", "Gls_p90", "Sh_p90", "SoT_p90", "SoT%", "G/Sh", "Fld_p90", "+/-90"],
}

MIN_SHOTS_FOR_RATES = 10
SMALL_POOL = 30


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["role"] != "GK"].copy()
    few_shots = df["Sh"] < MIN_SHOTS_FOR_RATES
    df.loc[few_shots, ["SoT%", "G/Sh"]] = np.nan
    return df


def percentile_against(values: pd.Series, reference: pd.Series, higher_is_better: bool) -> pd.Series:
    ref = np.sort(reference.dropna().to_numpy())
    if len(ref) == 0:
        return pd.Series(np.nan, index=values.index)

    v = values.to_numpy(dtype=float)
    below = np.searchsorted(ref, v, side="left")
    at_or_below = np.searchsorted(ref, v, side="right")
    pct = (below + at_or_below) / 2 / len(ref) * 100
    if not higher_is_better:
        pct = 100 - pct
    pct[np.isnan(v)] = np.nan
    return pd.Series(pct, index=values.index).round(0)


def build(df: pd.DataFrame) -> pd.DataFrame:
    id_cols = ["season", "player_id", "Player", "Squad", "Age", "Pos", "role",
               "role_alt", "role_confidence", "role_source", "Min"]
    out = df[id_cols].copy()
    reference = df[df["season"].isin(PROFILE_SEASONS)]

    for role, group in df.groupby("role"):
        ref_group = reference[reference["role"] == role]
        for metric, higher in METRICS.items():
            out.loc[group.index, f"pct_{metric}"] = percentile_against(
                group[metric], ref_group[metric], higher
            )
        out.loc[group.index, "pool_size"] = len(ref_group)

    out["small_sample"] = out["season"] == CURRENT_SEASON
    return out


def report(out: pd.DataFrame) -> None:
    print("Reference pool size per role (profiling seasons pooled)")
    sizes = out.groupby("role")["pool_size"].first().astype(int)
    for role, n in sizes.items():
        flag = "  <- small: treat percentiles as rough" if n < SMALL_POOL else ""
        print(f"  {role:<5} {n}{flag}")

    print("\nTop 3 per role on its first key metric, 2025-26")
    season = out[out["season"] == "2025-26"]
    for role, metrics in ROLE_KEY_METRICS.items():
        col = f"pct_{metrics[0]}"
        top = season[season["role"] == role].nlargest(3, col)
        names = ", ".join(f"{p} ({int(v)})" for p, v in zip(top["Player"], top[col]))
        print(f"  {role:<5} {metrics[0]:<9} {names}")

    print(f"\nRows: {len(out)} ({(~out['small_sample']).sum()} profiling, "
          f"{out['small_sample'].sum()} current-season form)")


if __name__ == "__main__":
    profiles = prepare(pd.read_csv(PROFILES))
    out = build(profiles)
    report(out)

    out.to_csv(OUT, index=False)
    print(f"\nSaved: {OUT}")