import sys
from html import escape
from pathlib import Path
from urllib.parse import quote_plus
from app_data import crest

import altair as alt
import pandas as pd
import streamlit as st


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app_data import (BAND_COLORS, FORM_HELP, ROLE_LABELS, SHORT_LABELS,  # noqa: E402
                      SIMILARITY_HELP, footer, hero, load_percentiles, load_profiles,
                      load_similar, pill, style)
from config import CURRENT_SEASON, PROFILE_SEASONS  # noqa: E402
from percentiles import ROLE_KEY_METRICS  # noqa: E402

st.set_page_config(page_title="Player Profile", page_icon=":material/person:", layout="wide")
style()

pct = load_percentiles()
profiles = load_profiles()
similar = load_similar()


def initials(name: str) -> str:
    return "".join(w[0] for w in str(name).split()[:2]).upper()


def per90_text(metric: str, value) -> str:
    if value is None or pd.isna(value):
        return ""
    if metric == "SoT%":
        return f"{value:.0f}% on target"
    if metric == "G/Sh":
        return f"{value:.2f} goals per shot"
    if metric.endswith("_p90"):
        return f"{value:.2f} per 90"
    return f"{value:.2f}"


latest = pct.sort_values("season", ascending=False).drop_duplicates("player_id")
latest["label"] = latest["Player"] + " (" + latest["Squad"] + ", " + latest["role"] + ")"
options = latest.sort_values("Player").set_index("player_id")["label"]

hero("Player Profile",
     "How a player ranks in their role, how they've changed and who's similar",
     kicker=f"Betway Premiership · {min(PROFILE_SEASONS)} to {CURRENT_SEASON}")

pick_col, season_col = st.columns([3, 2])
with pick_col:
    player_id = st.selectbox("Player", options.index, format_func=lambda p: options[p])
rows = pct[pct["player_id"] == player_id].sort_values("season", ascending=False)
full_seasons = [s for s in rows["season"] if s in PROFILE_SEASONS]
with season_col:
    season = st.segmented_control(
        "Season", rows["season"].tolist(),
        default=full_seasons[0] if full_seasons else rows["season"].iloc[0],
    ) or (full_seasons[0] if full_seasons else rows["season"].iloc[0])

row = rows[rows["season"] == season].iloc[0]
role = row["role"]
metrics = ROLE_KEY_METRICS[role]
raw = profiles[(profiles["player_id"] == player_id) & (profiles["season"] == season)]


def raw_value(metric: str):
    if raw.empty or metric not in raw:
        return None
    return raw[metric].iloc[0]


# Player card: identity on the left, three strongest stats on the right
age = "age unknown" if pd.isna(row["Age"]) else f"Age {int(row['Age'])}"
pills = pill("Reviewed role", "ok") if row["role_source"] == "override" else pill("Model role", "muted")
if row["role_confidence"] == "low":
    pills += pill(f"Borderline {row['role_alt']}", "warn")
if season == CURRENT_SEASON:
    pills += pill("Current form: small sample", "warn")

strongest = sorted(
    ((row[f"pct_{m}"], m) for m in metrics if m != "+/-90" and pd.notna(row[f"pct_{m}"])),
    reverse=True,
)[:3]
stats_html = "".join(
    f'<div class="hs"><div class="hs-label">{escape(SHORT_LABELS.get(m, m))}</div>'
    f'<div class="hs-value">{p:.0f}</div>'
    f'<div class="hs-note">{escape(per90_text(m, raw_value(m)))}</div></div>'
    for p, m in strongest
)

st.markdown(
    f'<div class="player-head">'
    f'<div class="ph-main"><div class="ph-avatar">{escape(initials(row["Player"]))}</div>'
    f'<div><div class="ph-kicker">{escape(ROLE_LABELS[role])} · {season}</div>'
    f'<div class="name">{escape(row["Player"])}</div>'
    f'<div class="meta">{crest(row["Squad"])}{escape(row["Squad"])} · {age} · '
    f'{int(row["Min"]):,} minutes</div>'
    f'{pills}</div></div>'
    f'<div class="ph-stats">{stats_html}</div></div>',
    unsafe_allow_html=True,
)

left, right = st.columns([3, 2], gap="large")

with left:
    # Percentile bars
    st.subheader(f"Percentiles vs other {ROLE_LABELS[role].lower()}s")
    bars = pd.DataFrame({
        "Stat": [SHORT_LABELS.get(m, m) for m in metrics],
        "Percentile": [row[f"pct_{m}"] for m in metrics],
        "Per 90": [raw_value(m) for m in metrics],
    })
    bars["Band"] = pd.cut(bars["Percentile"], [-1, 33, 66, 100], labels=list(BAND_COLORS))
    shown = bars.dropna(subset=["Percentile"])

    base = alt.Chart(shown).encode(
        y=alt.Y("Stat:N", sort=None, title=None,
                axis=alt.Axis(labelLimit=220, labelColor="#e8ecf2", labelFontSize=13,
                              ticks=False, domain=False, labelPadding=10)),
        x=alt.X("Percentile:Q", scale=alt.Scale(domain=[0, 100]), title=None,
                axis=alt.Axis(values=[0, 25, 50, 75, 100], gridColor="#232b37",
                              labelColor="#93a0b2", domain=False, ticks=False)),
    )
    chart = base.mark_bar(cornerRadiusEnd=4, height=18).encode(
        color=alt.Color("Band:N", scale=alt.Scale(domain=list(BAND_COLORS),
                                                  range=list(BAND_COLORS.values())),
                        legend=alt.Legend(orient="bottom", title=None, labelColor="#c3ccd8")),
        tooltip=["Stat", "Percentile", alt.Tooltip("Per 90:Q", format=".2f")],
    ) + base.mark_text(align="left", dx=6, color="#e8ecf2", fontSize=13).encode(
        text=alt.Text("Percentile:Q", format=".0f"))
    st.altair_chart(chart.properties(height=44 * len(shown)).configure_view(strokeWidth=0),
                    use_container_width=True)
    st.caption(f"Compared with {ROLE_LABELS[role].lower()}s across "
               f"{' and '.join(PROFILE_SEASONS)}. Goal difference mostly reflects team strength.")

    # Similar players
    st.subheader(f"Most similar {ROLE_LABELS[role].lower()}s")
    st.caption(SIMILARITY_HELP)
    matches = similar[(similar["player_id"] == player_id) & (similar["season"] == season)].head(5)
    if matches.empty:
        st.info("No similarity results for this player-season.")
    else:
        sim_rows = []
        for _, m in matches.iterrows():
            closest = " · ".join(SHORT_LABELS.get(x.strip(), x.strip())
                                 for x in str(m["closest_metrics"]).split(","))
            strong = " strong" if m["similarity"] >= 85 else ""
            sim_rows.append(
                f'<div class="sim-row">'
                f'<span class="sim-ini">{escape(initials(m["similar_player"]))}</span>'
                f'<span><span class="sim-name">{escape(m["similar_player"])}</span><br>'
                f'<span class="sim-meta">{escape(m["similar_squad"])} · {m["similar_season"]}</span></span>'
                f'<span class="sim-close">{escape(closest)}</span>'
                f'<span class="sim-score{strong}">{m["similarity"]:.0f}</span></div>'
            )
        st.markdown(f'<div class="sim-list">{"".join(sim_rows)}</div>', unsafe_allow_html=True)

with right:
    st.subheader("Role history")
    history = rows[["season", "Squad", "role", "role_source", "Min"]].rename(columns={
        "season": "Season", "Squad": "Club", "role": "Role", "role_source": "Source"})
    history["Source"] = history["Source"].map({"override": "Reviewed", "model": "Model"})
    st.dataframe(history, hide_index=True, use_container_width=True,
                 height=35 * (len(history) + 1) + 3,
                 column_config={"Min": st.column_config.NumberColumn("Minutes",
                                                                    format="localized")})

    if season != CURRENT_SEASON and CURRENT_SEASON in rows["season"].values:
        form = rows[rows["season"] == CURRENT_SEASON].iloc[0]
        st.subheader("This season so far")
        st.caption(f"{CURRENT_SEASON}: {int(form['Min']):,} minutes. Small sample, "
                   "so treat it as an early signal.", help=FORM_HELP)
        then = [row[f"pct_{m}"] for m in metrics]
        now = [form[f"pct_{m}"] for m in metrics]
        form_table = pd.DataFrame({
            "Stat": bars["Stat"], season: then, CURRENT_SEASON: now,
            "Change": [n - t if pd.notna(n) and pd.notna(t) else None for t, n in zip(then, now)],
        })
        st.dataframe(form_table, hide_index=True, use_container_width=True,
                     height=35 * (len(form_table) + 1) + 3,
                     column_config={
                         season: st.column_config.NumberColumn(season, format="%.0f"),
                         CURRENT_SEASON: st.column_config.NumberColumn(CURRENT_SEASON, format="%.0f"),
                         "Change": st.column_config.NumberColumn("Change", format="%+.0f"),
                     })

    st.subheader("Check elsewhere")
    name = row["Player"]
    st.link_button("FBref player page", f"https://fbref.com/en/players/{player_id}/",
                   icon=":material/open_in_new:", use_container_width=True)
    st.link_button("Transfermarkt: value and contract",
                   "https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query="
                   + quote_plus(name),
                   icon=":material/open_in_new:", use_container_width=True)
    st.caption("No xG, passing, dribbling or market value in open data. " \
    "Watch the player in matches and check these links before going further.")

footer()