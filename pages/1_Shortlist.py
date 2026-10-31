import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app_data import (FIT_SCORE_HELP, FORM_HELP, ROLE_LABELS, footer,  # noqa: E402
                      load_percentiles)
from config import PROFILE_SEASONS  # noqa: E402
from shortlist import METRIC_LABELS, build_shortlist, default_priorities  # noqa: E402

st.set_page_config(page_title="Shortlist", layout="wide")
st.title("Recruitment shortlist")

pct = load_percentiles()
latest_season = max(PROFILE_SEASONS)

with st.sidebar:
    st.header("Profile")
    role = st.selectbox("Role", list(ROLE_LABELS), format_func=lambda r: ROLE_LABELS[r])

    st.header("Filters")
    ages = pct["Age"].dropna()
    age_range = st.slider("Age (approximate)", int(ages.min()), int(ages.max()),
                          (int(ages.min()), int(ages.max())))
    include_unknown_age = st.checkbox("Include players with unknown age", value=True)
    min_minutes = st.number_input("Minimum minutes in that season", 900, 3000, 900, step=100)
    clubs = sorted(pct["Squad"].dropna().unique())
    exclude = st.multiselect("Exclude clubs", clubs)
    recent_only = st.checkbox(f"Only players with a {latest_season} full season", value=False)
    top_n = st.slider("Players to show", 5, 30, 15)

st.subheader(f"What matters most for a {ROLE_LABELS[role].lower()}?")
st.caption("0 = ignore, 1 = normal, 3 = most important. Discipline stats default low: "
           "few fouls can mean low involvement rather than good defending.")

defaults = default_priorities(role)
cols = st.columns(min(len(defaults), 4))
priorities = {}
for i, (metric, weight) in enumerate(defaults.items()):
    with cols[i % len(cols)]:
        label = METRIC_LABELS.get(metric, metric)
        priorities[metric] = st.slider(label[0].upper() + label[1:], 0.0, 3.0,
                                       float(weight), 0.25, key=f"{role}_{metric}")
priorities = {m: w for m, w in priorities.items() if w > 0}

if not priorities:
    st.warning("Give at least one stat a weight above 0.")
    st.stop()

full = build_shortlist(pct, role, priorities=priorities, exclude_clubs=exclude or None,
                       min_minutes=min_minutes, top_n=10_000)

in_range = full["Age"].between(*age_range)
if include_unknown_age:
    in_range |= full["Age"].isna()
result = full[in_range]
if recent_only:
    result = result[result["season"] == latest_season]
result = result.head(top_n).reset_index(drop=True)

if result.empty:
    st.info("No players match these filters.")
    footer()
    st.stop()

result.insert(0, "Rank", range(1, len(result) + 1))
result["Status"] = result["season"].map(
    lambda s: "Recent" if s == latest_season else f"⚠ {s} only: check status"
)
result["Age"] = result["Age"].map(lambda a: "—" if pd.isna(a) else str(int(a)))

st.caption(f"{len(result)} players shown. **Fit score**: {FIT_SCORE_HELP}")

for col in ["other_score", "form_score"]:
    result[col] = result[col].map(lambda v: "—" if pd.isna(v) else f"{v:.0f}")

st.dataframe(
    result[["Rank", "Player", "Squad", "Age", "Status", "score", "other_score", "form_score"]],
    hide_index=True,
    use_container_width=True,
    column_config={
        "Squad": "Club",
        "Age": st.column_config.TextColumn("Age", help="Approximate current age. — = not listed on FBref."),
        "score": st.column_config.ProgressColumn("Fit score", min_value=0, max_value=100,
                                                 format="%.0f", help=FIT_SCORE_HELP),
        "other_score": st.column_config.TextColumn("Other full season"),
        "form_score": st.column_config.TextColumn("Current form ⚠", help=FORM_HELP),
    },
)

st.subheader("Why each player is on the list")
for _, r in result.iterrows():
    st.markdown(f"**{r['Rank']}. {r['Player']}** ({r['Squad']}, {r['season']}, "
                f"{int(r['Min'])} min): {r['why']}")

st.download_button("Download shortlist (CSV)", result.to_csv(index=False),
                   file_name=f"shortlist_{role.replace('/', '-')}.csv", mime="text/csv")

footer()