import pandas as pd
df = pd.read_csv("data/processed/profiles_adjusted.csv")
df = df[df["season"].isin(["2024-25", "2025-26"]) & (df["role"] != "GK")]
df["def_raw"] = df["TklW_p90"] + df["Int_p90"]

rows = []
for role, g in df.groupby("role"):
    rows.append({"role": role, "n": len(g),
                 "before": round(g["def_raw"].corr(g["team_poss"]), 2),
                 "after": round(g["def_actions_p90_padj"].corr(g["team_poss"]), 2)})
print(pd.DataFrame(rows).to_string(index=False))