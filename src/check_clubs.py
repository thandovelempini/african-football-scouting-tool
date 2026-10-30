import pandas as pd
prof = pd.read_csv("data/processed/profiles.csv")
noop = prof[(prof["role_source"] == "override") & (prof["model_role"] == prof["role"])]
print(noop[["season", "player_id", "Player", "role"]].to_string())