
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "fbref"
OUT_DIR = ROOT / "data" / "processed"

TABLES = ["standard", "shooting", "playing_time", "misc"]
KEYS = ["player_id", "Squad"]
PER90 = ["Gls", "Ast", "G-PK", "Sh", "SoT", "Crs", "Int", "TklW",
         "Fls", "Fld", "Off", "CrdY"]
TEXT_COLS = {"Player", "Nation", "Pos", "primary_pos", "Squad", "Born", "player_id"}

CHECKS = {
    "2024-25": {"goals": 411, "player": ("Lucas Ribeiro", "Sundowns", {"Gls": 16})},
    "2025-26": {"goals": 468, "player": ("Sédé Junior Dion", "Golden Arrows", {"Gls": 14})},
    "2026-27": {"goals": 142, "player": ("Thando Ngwenya", "AmaZulu", {"Gls": 8, "SoT": 12, "Min": 599})},
}


def load_table(season: str, name: str) -> pd.DataFrame:
    path = RAW_DIR / f"{season}_{name}.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()

    def is_header(line: str) -> bool:
        return line.strip().strip('"').startswith("Rk")

    start = next((i for i, line in enumerate(lines) if is_header(line)), None)
    if start is None:
        preview = "\n    ".join(lines[:3]) or "(file is empty)"
        hint = (" This looks like the squad table: use 'View Player Stats' and export the player table."
                if any(line.strip().startswith("Squad") for line in lines[:3]) else "")
        raise ValueError(f"No 'Rk' header row in {path.name}.{hint}\n  First lines:\n    {preview}")

    df = pd.read_csv(path, skiprows=start, encoding="utf-8-sig")
    df = df[df["Player"] != "Player"].drop(
        columns=["Rk", "Matches", "On-Off", "PKwon", "PKcon"], errors="ignore"
    )
    df = df.rename(columns={"-9999": "player_id", "G+A-PK": "G+A-PK_p90_fbref"})
    return df.rename(columns={c: f"{c[:-2]}_p90_fbref" for c in df.columns if c.endswith(".1")})


def clean(df: pd.DataFrame) -> pd.DataFrame:
    if "Min" in df.columns:
        df["Min"] = pd.to_numeric(df["Min"].astype(str).str.replace(",", ""), errors="coerce")
    if "Age" in df.columns:
        df["Age"] = pd.to_numeric(df["Age"].astype(str).str.split("-").str[0], errors="coerce")
    if "Nation" in df.columns:
        df["Nation"] = df["Nation"].astype(str).str.split().str[-1].replace("nan", pd.NA)
    if "Pos" in df.columns:
        df["primary_pos"] = df["Pos"].astype(str).str[:2].replace("na", pd.NA)

    for col in df.columns:
        if col not in TEXT_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def build_season(season: str) -> pd.DataFrame:
    merged = None
    for name in TABLES:
        df = load_table(season, name)
        if merged is None:
            merged = df
        else:
            new_cols = KEYS + [c for c in df.columns if c not in merged.columns]
            merged = merged.merge(df[new_cols], on=KEYS, how="left")
    return clean(merged.reset_index(drop=True))


def add_per90(df: pd.DataFrame, season: str) -> pd.DataFrame:
    minutes = df["Min"].where(df["Min"] > 0)
    for col in PER90:
        if col in df.columns:
            df[f"{col}_p90"] = df[col] / minutes * 90
    df.insert(0, "season", season)
    return df


def check(df: pd.DataFrame, season: str) -> bool:
    passed = True

    def report(ok: bool, msg: str) -> None:
        nonlocal passed
        passed = passed and ok
        print(f"  {'OK' if ok else '!!'}  {msg}")

    print(f"\n{season}: {len(df)} player rows, {df['Squad'].nunique()} clubs")

    standard_rows = len(load_table(season, "standard"))
    report(len(df) == standard_rows, f"rows match standard export ({standard_rows})")

    dupes = df.duplicated(subset=KEYS).sum()
    report(dupes == 0, f"unique player_id + Squad (duplicates: {dupes})")

    multi_club = df.groupby("player_id")["Squad"].nunique()
    print(f"      players at 2+ clubs: {(multi_club > 1).sum()}")

    missing_min = df["Min"].isna().sum()
    report(missing_min == 0, f"no missing minutes (missing: {missing_min})")

    expected_goals = CHECKS[season]["goals"]
    total_goals = int(df["Gls"].sum())
    report(total_goals == expected_goals, f"total goals: expected={expected_goals} got={total_goals}")

    name, squad, expected = CHECKS[season]["player"]
    row = df[(df["Player"] == name) & (df["Squad"] == squad)]
    if row.empty:
        report(False, f"{name} ({squad}) not found")
    else:
        for key, value in expected.items():
            got = row[key].iloc[0]
            report(abs(float(got) - value) < 0.01, f"{name} {key}: expected={value} got={got}")

    return passed


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seasons, failed = [], []

    for season in CHECKS:
        df = add_per90(build_season(season), season)
        if not check(df, season):
            failed.append(season)
        df.to_csv(OUT_DIR / f"{season}_players.csv", index=False)
        seasons.append(df)

    combined = pd.concat(seasons, ignore_index=True)
    expected_rows = sum(len(df) for df in seasons)

    print(f"\nCombined: {len(combined)} rows across {combined['season'].nunique()} seasons")
    print(f"  {'OK' if len(combined) == expected_rows else '!!'}  "
          f"rows match sum of seasons ({expected_rows})")

    out = OUT_DIR / "players_all_seasons.csv"
    combined.to_csv(out, index=False)
    print(f"\nSaved: {out}")

    if failed:
        print(f"\n!! Checks failed for: {', '.join(failed)}")