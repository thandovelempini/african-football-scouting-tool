"""
Build one player-season from FBref CSV exports and sanity-check it.

Expects these files in data/raw/fbref/ (from Share & Export > Get table as CSV):
    2026-27_standard.csv, 2026-27_shooting.csv,
    2026-27_playing_time.csv, 2026-27_misc.csv
"""

from pathlib import Path

import pandas as pd

SEASON = "2026-27"
PLAYER = "Thando Ngwenya"
SQUAD = "AmaZulu"

RAW_DIR = Path("data/raw/fbref")
OUT_DIR = Path("data/processed")

TABLES = ["standard", "shooting", "playing_time", "misc"]
EXPECTED = {"Gls": 8, "SoT": 12, "Gls_p90_fbref": 1.20}
PER90 = ["Gls", "Ast", "G-PK", "Sh", "SoT", "Crs", "Int", "TklW",
         "Fls", "Fld", "Off", "CrdY"]
TEXT_COLS = {"Player", "Nation", "Pos", "primary_pos", "Squad", "Born", "player_id"}


def load_table(name: str) -> pd.DataFrame:
    path = RAW_DIR / f"{SEASON}_{name}.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()

    def is_header(line: str) -> bool:
        return line.strip().strip('"').startswith("Rk")

    start = next((i for i, line in enumerate(lines) if is_header(line)), None)
    if start is None:
        preview = "\n    ".join(lines[:3]) or "(file is empty)"
        hint = (" This looks like the squad table: use 'View Player Stats' first."
                if lines and lines[0].strip().startswith("Squad") else "")
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
        df["Nation"] = df["Nation"].astype(str).str.split().str[-1]
    if "Pos" in df.columns:
        df["primary_pos"] = df["Pos"].astype(str).str[:2]

    for col in df.columns:
        if col not in TEXT_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def build_player_row() -> pd.DataFrame:
    keys = ["player_id", "Squad"]
    merged = None
    for name in TABLES:
        df = load_table(name)
        df = df[(df["Player"] == PLAYER) & (df["Squad"] == SQUAD)]
        if df.empty:
            raise ValueError(f"{PLAYER} ({SQUAD}) not found in {name} table")
        if merged is None:
            merged = df
        else:
            new_cols = keys + [c for c in df.columns if c not in merged.columns]
            merged = merged.merge(df[new_cols], on=keys, how="left")
    return clean(merged.reset_index(drop=True))


def add_per90(row: pd.DataFrame) -> pd.DataFrame:
    minutes = row["Min"].iloc[0]
    if not minutes or pd.isna(minutes):
        raise ValueError("Minutes missing or zero")
    for col in PER90:
        if col in row.columns:
            row[f"{col}_p90"] = row[col] / minutes * 90
    row.insert(0, "season", SEASON)
    return row


def check(row: pd.DataFrame) -> None:
    print(f"\n{PLAYER} ({SQUAD}) {SEASON}: {int(row['Min'].iloc[0])} minutes")
    for key, expected in EXPECTED.items():
        got = row[key].iloc[0] if key in row.columns else None
        ok = got is not None and abs(float(got) - expected) < 0.01
        print(f"  {'OK' if ok else '!!'}  {key:<14} expected={expected:<5} got={got}")

    if {"Gls_p90", "Gls_p90_fbref"} <= set(row.columns):
        diff = abs(row["Gls_p90"].iloc[0] - row["Gls_p90_fbref"].iloc[0])
        print(f"  {'OK' if diff < 0.02 else '!!'}  Gls/90 vs FBref: diff={diff:.3f}")


if __name__ == "__main__":
    row = add_per90(build_player_row())
    check(row)
    print("\nColumns:", list(row.columns))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{SEASON}_{PLAYER.lower().replace(' ', '_')}.csv"
    row.to_csv(out, index=False)
    print(f"\nSaved: {out}")