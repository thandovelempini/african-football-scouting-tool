"""
Validate forward role assignments against independently checked positions.

First run: creates data/manual/forward_validation.csv with one row per regular
forward (FW/FWMF, 1,200+ minutes, profiling seasons) and an empty tm_position column.
Fill tm_position by hand (e.g. "Centre-Forward", "Left Winger"), then run again
to get the agreement rate and the list of disagreements.

Keep forward_validation.csv out of the public repo: it holds third-party content.
"""

from pathlib import Path

import pandas as pd

from config import PROFILE_SEASONS

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "data" / "processed" / "profiles.csv"
VALIDATION = ROOT / "data" / "manual" / "forward_validation.csv"

MIN_MINUTES = 1200
TEMPLATE_COLS = ["player_id", "season", "Player", "Squad", "Pos", "Min", "tm_position"]

TM_TO_ROLE = {
    "centre-forward": "ST",
    "center-forward": "ST",
    "second striker": "ST",
    "left winger": "W/AM",
    "right winger": "W/AM",
    "attacking midfield": "W/AM",
    "left midfield": "W/AM",
    "right midfield": "W/AM",
    "central midfield": "CM",
    "defensive midfield": "DM",
    "left-back": "FB",
    "right-back": "FB",
    "centre-back": "CB",
    "center-back": "CB",
}


def forward_pool() -> pd.DataFrame:
    df = pd.read_csv(PROFILES)
    pos = df["Pos"].astype(str)
    keep = (
        df["season"].isin(PROFILE_SEASONS)
        & pos.str.startswith("FW")
        & ~pos.str.startswith("FWDF")
        & (df["Min"] >= MIN_MINUTES)
    )
    return df[keep].sort_values("Min", ascending=False)


def create_or_extend_template(pool: pd.DataFrame) -> None:
    rows = pool[TEMPLATE_COLS[:-1]].copy()
    rows["tm_position"] = ""

    if VALIDATION.exists():
        existing = pd.read_csv(VALIDATION, dtype={"tm_position": str})
        keys = set(zip(existing["player_id"], existing["season"]))
        new = rows[[(p, s) not in keys for p, s in zip(rows["player_id"], rows["season"])]]
        if new.empty:
            return
        pd.concat([existing, new], ignore_index=True).to_csv(VALIDATION, index=False)
        print(f"Added {len(new)} new forwards to {VALIDATION.name}")
        return

    VALIDATION.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(VALIDATION, index=False)
    print(f"Created {VALIDATION} with {len(rows)} forwards.")
    print("Fill in tm_position for each row, then run this script again.")


def evaluate(pool: pd.DataFrame) -> None:
    checked = pd.read_csv(VALIDATION, dtype={"tm_position": str})
    checked = checked[checked["tm_position"].fillna("").str.strip() != ""]
    if checked.empty:
        print("No tm_position values filled in yet.")
        return

    checked["expected"] = checked["tm_position"].str.strip().str.lower().map(TM_TO_ROLE)
    unknown = checked[checked["expected"].isna()]
    if not unknown.empty:
        print("Unrecognised tm_position values (add them to TM_TO_ROLE):")
        print("  " + ", ".join(sorted(unknown["tm_position"].unique())))
    checked = checked.dropna(subset=["expected"])
    
    model_col = "model_role" if "model_role" in pool.columns else "role"
    
    model_data = pool[
        ["player_id", "season", "role", "role_alt", "role_margin"]
    ].copy()
    
    model_data["model"] = (
        
        pool["model_role"] if "model_role" in pool.columns else pool["role"]
    )
    
    model_data = model_data.rename(columns={
        "role": "final_role",
        "role_alt": "model_alt",
        "role_margin": "model_margin",
    }).drop_duplicates(subset=["player_id", "season"])
    
    merged = checked.merge(
        model_data,
        on=["player_id", "season"],
        how="inner",
        validate="one_to_one",
    )

    total = len(merged)
    
    model_ok = (merged["model"] == merged["expected"]).sum()
    final_ok = (merged["final_role"] == merged["expected"]).sum()

    print(f"\nForwards checked: {total}")
    if total:
        print(f"  model alone agrees:    {model_ok}/{total} ({model_ok / total:.0%})")
        print(f"  with overrides agrees: {final_ok}/{total} ({final_ok / total:.0%})")
    else:
        print("No matching player-season records found.")

    print("\nModel role vs checked position")
    print(pd.crosstab(merged["model"], merged["expected"],
                      rownames=["model"], colnames=["checked"]).to_string())

    misses = merged[merged["model"] != merged["expected"]]
    if not misses.empty:
        too_wide = ((misses["model"] == "W/AM") & (misses["expected"] == "ST")).sum()
        too_central = ((misses["model"] == "ST") & (misses["expected"] == "W/AM")).sum()
        print(f"\nModel misses: {len(misses)}"
              f"  (strikers sent to W/AM: {too_wide}, wide players sent to ST: {too_central})")
        show = ["season", "Player", "Squad", "Pos", "Min", "tm_position", "model",
                "final_role", "model_alt", "model_margin"]
        print(misses[show].round(2).to_string(index=False))


if __name__ == "__main__":
    pool = forward_pool()
    create_or_extend_template(pool)
    if VALIDATION.exists():
        evaluate(pool)