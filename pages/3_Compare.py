import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app_data import ROLE_LABELS, SHORT_LABELS, footer, load_percentiles, load_profiles  # noqa: E402
from config import CURRENT_SEASON, PROFILE_SEASONS  # noqa: E402
from percentiles import ROLE_KEY_METRICS  # noqa: E402

st.set_page_config(page_title="Compare players", layout="wide")
st.title("Compare Players")
st.caption("Pick two or three players. Percentiles compare each player with others in "
           "their own role, so comparisons are most meaningful within the same role.")

pct = load_percentiles()
profiles = load_profiles()

latest = pct.sort_values("season", ascending=False).drop_duplicates("player_id")
latest["label"] = latest["Player"] + " (" + latest["Squad"] + ", " + latest["role"] + ")"
options = latest.sort_values("Player").set_index("player_id")["label"]

role_filter = st.selectbox("Limit choices to a role (optional)", ["Any"] + list(ROLE_LABELS),
                           format_func=lambda r: "Any role" if r == "Any" else ROLE_LABELS[r])
if role_filter != "Any":
    options = options[latest.set_index("player_id").loc[options.index, "role"] == role_filter]

chosen = st.multiselect("Players", options.index, format_func=lambda p: options[p], max_selections=3)
if len(chosen) < 2:
    st.info("Choose at least two players.")
    footer()
    st.stop()

picked = []
cols = st.columns(len(chosen))
for col, pid in zip(cols, chosen):
    rows = pct[pct["player_id"] == pid].sort_values("season", ascending=False)
    seasons = rows["season"].tolist()
    default = next((i for i, s in enumerate(seasons) if s in PROFILE_SEASONS), 0)
    with col:
        season = st.selectbox(f"{rows.iloc[0]['Player']}: season", seasons, index=default, key=pid)
    picked.append(rows[rows["season"] == season].iloc[0])

roles = {p["role"] for p in picked}
if len(roles) > 1:
    st.warning("These players have different roles, so each is ranked against a different "
               "group. Compare the shape of their profiles rather than the exact numbers.")
if any(p["season"] == CURRENT_SEASON for p in picked):
    st.warning(f"{CURRENT_SEASON} is a small sample: treat those percentiles as an early signal.")

metrics = list(dict.fromkeys(m for p in picked for m in ROLE_KEY_METRICS[p["role"]]))

summary = pd.DataFrame([{
    "Player": p["Player"], "Club": p["Squad"], "Season": p["season"],
    "Role": p["role"], "Age": "—" if pd.isna(p["Age"]) else int(p["Age"]), "Minutes": int(p["Min"]),
} for p in picked])
st.dataframe(summary, hide_index=True, width="content")

long = pd.DataFrame([{
    "Player": f"{p['Player']} ({p['season']})",
    "Stat": SHORT_LABELS.get(m, m),
    "Percentile": p[f"pct_{m}"],
} for p in picked for m in metrics]).dropna(subset=["Percentile"])

st.subheader("Percentiles")
chart = (
    alt.Chart(long)
    .mark_bar()
    .encode(
        y=alt.Y("Stat:N", sort=[SHORT_LABELS.get(m, m) for m in metrics], title=None,
                axis=alt.Axis(labelLimit=300)),
        yOffset="Player:N",
        x=alt.X("Percentile:Q", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("Player:N", legend=alt.Legend(orient="top", title=None),
                        scale=alt.Scale(range=["#e4572e", "#29a3a3", "#f2b134"])),
        tooltip=["Player", "Stat", "Percentile"],
    )
    .properties(height=28 * len(metrics) * len(picked))
)
st.altair_chart(chart, use_container_width=True)

st.subheader("Per-90 values")
values = []
for p in picked:
    raw = profiles[(profiles["player_id"] == p["player_id"]) & (profiles["season"] == p["season"])]
    values.append({SHORT_LABELS.get(m, m): (round(raw[m].iloc[0], 0 if m == "SoT%" else 2)
                                            if not raw.empty and m in raw else None)
                   for m in metrics} | {"Player": f"{p['Player']} ({p['season']})"})
table = pd.DataFrame(values).set_index("Player").T
st.dataframe(table, width="content")
st.caption("Finishing is goals per shot. Few fouls / few cards show the raw rate per 90 "
           "(lower is better). Goal difference mostly reflects team strength.")

footer()