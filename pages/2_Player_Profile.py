import sys
from pathlib import Path
from urllib.parse import quote_plus

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app_data import (FORM_HELP, ROLE_LABELS, SIMILARITY_HELP, footer,  # noqa: E402
                      load_percentiles, load_profiles, load_similar)
from config import CURRENT_SEASON, PROFILE_SEASONS  # noqa: E402
from percentiles import ROLE_KEY_METRICS  # noqa: E402
from shortlist import METRIC_LABELS  # noqa: E402

from app_data import (FORM_HELP, ROLE_LABELS, SHORT_LABELS, SIMILARITY_HELP, footer,  # noqa: E402
                      load_percentiles, load_profiles, load_similar)

st.set_page_config(page_title="Player profile", layout="wide")
st.title("Player Profile")

pct = load_percentiles()
profiles = load_profiles()
similar = load_similar()

latest = pct.sort_values("season", ascending=False).drop_duplicates("player_id")
latest["label"] = latest["Player"] + " (" + latest["Squad"] + ", " + latest["role"] + ")"
options = latest.sort_values("Player").set_index("player_id")["label"]

player_id = st.selectbox("Player", options.index, format_func=lambda p: options[p])
rows = pct[pct["player_id"] == player_id].sort_values("season", ascending=False)

full_seasons = [s for s in rows["season"] if s in PROFILE_SEASONS]
season = st.radio("Season", rows["season"].tolist(), horizontal=True,
                  index=rows["season"].tolist().index(full_seasons[0]) if full_seasons else 0)
row = rows[rows["season"] == season].iloc[0]
role = row["role"]

if season == CURRENT_SEASON:
    st.warning(f"{CURRENT_SEASON} is current form only ({int(row['Min'])} minutes). "
               "Percentiles compare it with full-season players, so treat it as an early signal.")

age = "—" if pd.isna(row["Age"]) else str(int(row["Age"]))
c1, c2, c3, c4 = st.columns(4)
c1.metric("Club", row["Squad"])
c2.metric("Role", ROLE_LABELS[role])
c3.metric("Age", age, help="Approximate: current year minus birth year. — = not listed on FBref.")
c4.metric("Minutes", f"{int(row['Min']):,}")

source = "reviewed manually" if row["role_source"] == "override" else "assigned by the model"
note = f" Borderline {row['role_alt']} profile." if row["role_confidence"] == "low" else ""
st.caption(f"Role {source}.{note}")

st.subheader(f"Percentiles vs other {ROLE_LABELS[role].lower()}s")
metrics = ROLE_KEY_METRICS[role]
raw = profiles[(profiles["player_id"] == player_id) & (profiles["season"] == season)]
bars = pd.DataFrame({
    "Stat": [METRIC_LABELS.get(m, m).capitalize() for m in metrics],
    "Percentile": [row[f"pct_{m}"] for m in metrics],
    "Value": [raw[m].iloc[0] if not raw.empty and m in raw else None for m in metrics],
})
bars["Band"] = pd.cut(bars["Percentile"], [-1, 33, 66, 100], labels=["Below average", "Average", "Strong"])
chart = (
    alt.Chart(bars.dropna(subset=["Percentile"]))
    .mark_bar()
    .encode(
        x=alt.X("Percentile:Q", scale=alt.Scale(domain=[0, 100])),
        y=alt.Y("Stat:N", sort=None, title=None, axis=alt.Axis(labelLimit=300)),
        color=alt.Color("Band:N", scale=alt.Scale(domain=["Below average", "Average", "Strong"],
                                                  range=["#c0392b", "#d4a017", "#2f8f5b"])),
        tooltip=["Stat", "Percentile", alt.Tooltip("Value:Q", format=".2f")],
    )
    .properties(height=40 * len(metrics))
)
st.altair_chart(chart, use_container_width=True)
st.caption("Compared with players in the same role across 2024-25 and 2025-26. "
           "On-pitch goal difference mostly reflects team strength.")

if season != CURRENT_SEASON and CURRENT_SEASON in rows["season"].values:
    form = rows[rows["season"] == CURRENT_SEASON].iloc[0]
    st.subheader("This season so far ⚠ small sample")
    st.caption(FORM_HELP)
    form_col = f"{CURRENT_SEASON} ({int(form['Min'])} min)"
    st.dataframe(pd.DataFrame({
        "Stat": bars["Stat"],
        season: [row[f"pct_{m}"] for m in metrics],
        form_col: [form[f"pct_{m}"] for m in metrics],
    }), hide_index=True, use_container_width=False,
            column_config={
            "Stat": st.column_config.TextColumn("Stat", width=220),
            season: st.column_config.NumberColumn(season, width=90, format="%.0f"),
            form_col: st.column_config.NumberColumn(form_col, width=140, format="%.0f"),
        })

st.subheader("Role history")
history = rows[["season", "Squad", "role", "role_source", "Min"]].rename(columns={
    "season": "Season", "Squad": "Club", "role": "Role", "role_source": "Source", "Min": "Minutes"})
history["Source"] = history["Source"].map({"override": "Reviewed", "model": "Model"})
st.dataframe(history, hide_index=True, use_container_width=False,
             column_config={
                 "Season": st.column_config.TextColumn("Season", width=90),
                 "Club": st.column_config.TextColumn("Club", width=180),
                 "Role": st.column_config.TextColumn("Role", width=70),
                 "Source": st.column_config.TextColumn("Source", width=90),
                 "Minutes": st.column_config.NumberColumn("Minutes", width=90, format="%d"),
             })

st.subheader("Most similar players")
st.caption(SIMILARITY_HELP)
matches = similar[(similar["player_id"] == player_id) & (similar["season"] == season)].head(5)
if matches.empty:
    st.info("No similarity results for this player-season.")
else:
    matches = matches.assign(closest_metrics=matches["closest_metrics"].map(
        lambda s: " · ".join(SHORT_LABELS.get(m.strip(), m.strip()) for m in str(s).split(","))))
    st.dataframe(
        matches[["similar_player", "similar_squad", "similar_season", "similarity", "closest_metrics"]],
        hide_index=True, use_container_width=True,
        column_config={
            "similar_player": "Player", "similar_squad": "Club", "similar_season": "Season",
            "similarity": st.column_config.ProgressColumn("Similarity", min_value=0,                                                          
                                                          max_value=100, format="%.0f",
                                                          help=SIMILARITY_HELP),
            "closest_metrics": "Closest on",
        },
    )

st.subheader("More on this player")
name = row["Player"]
st.markdown(
    f"- [FBref player page](https://fbref.com/en/players/{player_id}/)\n"
    f"- [Search Transfermarkt](https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={quote_plus(name)}) "
    "for market value and contract details"
)

footer()