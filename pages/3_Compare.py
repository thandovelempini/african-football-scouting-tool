import sys
from html import escape
from pathlib import Path
from app_data import crest
from watchlist import watch_button

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app_data import (PLAYER_COLORS, ROLE_LABELS, SHORT_LABELS, footer, hero,  # noqa: E402
                      load_percentiles, load_profiles, pill, style)
from config import CURRENT_SEASON, PROFILE_SEASONS  # noqa: E402
from percentiles import METRICS, ROLE_KEY_METRICS  # noqa: E402

st.set_page_config(page_title="Compare Players", page_icon=":material/compare_arrows:",
                   layout="wide")
style()

pct = load_percentiles()
profiles = load_profiles()

RAW_LABELS = {**SHORT_LABELS, "Fls_p90": "Fouls", "CrdY_p90": "Cards", "Off_p90": "Offsides"}


def initials(name: str) -> str:
    return "".join(w[0] for w in str(name).split()[:2]).upper()


def fmt(metric: str, value) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.0f}%" if metric == "SoT%" else f"{value:.2f}"


hero("Compare Players",
     "Two or three players side by side, ranked against others in their role",
     kicker=f"Betway Premiership · {min(PROFILE_SEASONS)} to {CURRENT_SEASON}")

role_col, players_col = st.columns([1, 3])
roles = list(ROLE_LABELS)
link_role = st.query_params.get("role")
link_players = [p for p in st.query_params.get("players", "").split(",") if p]
link_seasons = dict(zip(link_players, st.query_params.get("seasons", "").split(",")))

with role_col:
    role = st.selectbox("Role", roles, format_func=lambda r: ROLE_LABELS[r],
                        index=roles.index(link_role) if link_role in roles else 0)

in_role = pct[pct["role"] == role]
latest = in_role.sort_values("season", ascending=False).drop_duplicates("player_id")
dupes = latest["Player"].duplicated(keep=False)
latest = latest.assign(label=latest["Player"].where(
    ~dupes, latest["Player"] + " (" + latest["Squad"] + ")"))
options = latest.sort_values("Player").set_index("player_id")["label"]
with players_col:
    selected = st.multiselect("Players", options.index, format_func=lambda p: options[p],
                              max_selections=3, placeholder="Pick two or three players",
                              default=[p for p in link_players if p in options.index][:3])

if len(selected) < 2:
    st.info(f"Pick at least two {ROLE_LABELS[role].lower()}s to compare.")
    footer()
    st.stop()

metrics = ROLE_KEY_METRICS[role]

cols = st.columns(len(selected))
chosen = []
for i, (col, pid) in enumerate(zip(cols, selected)):
    seasons = in_role[in_role["player_id"] == pid].sort_values("season", ascending=False)
    season_list = seasons["season"].tolist()
    full = [s for s in season_list if s in PROFILE_SEASONS]
    default = link_seasons.get(pid) if link_seasons.get(pid) in season_list else (
        full[0] if full else season_list[0])
    with col:
        card_slot = st.empty()            
        season = default
        if len(season_list) > 1:
            with st.container(key=f"seasonbox_{i}"):
                season = st.segmented_control(
                    "Season", season_list, default=default, key=f"season_{pid}",
                    label_visibility="collapsed") or default
        row = seasons[seasons["season"] == season].iloc[0]
        watch_button(pid, row["Player"], row["Squad"], role, season, key=f"watch_cmp_{pid}")
    chosen.append((i, card_slot, row))
    

lead_metrics = [m for m in metrics if m != "+/-90"]
leads = [0] * len(chosen)
for m in lead_metrics:
    values = [r[f"pct_{m}"] for _, _, r in chosen]
    valid = [v for v in values if pd.notna(v)]
    if valid and values.count(max(valid)) == 1:
        leads[values.index(max(valid))] += 1

def join_words(words: list[str]) -> str:
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def comparison_summary(chosen, lead_metrics) -> str:
    clauses = []
    for i, _, r in chosen:
        others = [o for j, _, o in chosen if j != i]
        wins = []
        for m in lead_metrics:
            v = r[f"pct_{m}"]
            ov = [o[f"pct_{m}"] for o in others]
            if pd.notna(v) and all(pd.notna(x) and v > x for x in ov):
                wins.append((v - max(ov), SHORT_LABELS.get(m, m).replace(" (%)", "").lower()))
        wins.sort(reverse=True)
        if wins:
            surname = escape(r["Player"].split()[-1])
            clauses.append(f"<strong>{surname}</strong> ranks higher for "
                           f"{join_words([w for _, w in wins[:3]])}")
    text = (", while ".join(clauses) if len(clauses) == 2 else ". ".join(clauses)) + "."

    small = [escape(r["Player"].split()[-1]) for _, _, r in chosen if r["season"] == CURRENT_SEASON]
    if small:
        text += (f" {join_words(small)}'s figures are from {CURRENT_SEASON}, a small sample, "
                 "so treat the comparison with caution.")
    if len({r["season"] for _, _, r in chosen}) > 1:
        text += " The players are compared across different seasons."
    return text

for (i, card_slot, r), n in zip(chosen, leads):
    color = PLAYER_COLORS[i]
    age = "Age unknown" if pd.isna(r["Age"]) else f"Age {int(r['Age'])}"
    tags = pill("Current form: small sample", "warn") if r["season"] == CURRENT_SEASON else ""
    if r["role_confidence"] == "low":
        tags += pill(f"Borderline {r['role_alt']}", "warn")
    card_slot.markdown(
        f'<div class="cmp-card" style="border-top-color:{color}">'
        f'<div class="cmp-main">'
        f'<div class="cmp-avatar" style="border-color:{color}">{crest(r["Squad"], 34)}</div>'
        f'<div class="cmp-text">'
        f'<div class="cmp-kicker" style="color:{color}">{escape(role)} · {r["season"]}</div>'
        f'<div class="cmp-name">{escape(r["Player"])}</div>'
        f'<div class="cmp-meta">{escape(r["Squad"])} · {age} · {int(r["Min"]):,} min</div>'
        f'{tags}</div></div>'
        f'<div class="cmp-stat"><div class="cmp-stat-value">{n}<span>/{len(lead_metrics)}</span></div>'
        f'<div class="cmp-stat-label">key stats ahead</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

labels = [f'{r["Player"]} ({r["season"]})' for _, _, r in chosen]
st.markdown(f'<div class="cmp-summary">{comparison_summary(chosen, lead_metrics)}</div>',
            unsafe_allow_html=True)
chart_col, table_col = st.columns([3, 2], gap="large")

with chart_col:
    st.subheader("Percentiles",
                 help="Each player is ranked against players in their own role across "
                      f"{' and '.join(PROFILE_SEASONS)}, so comparisons work best within one role.")
    long = pd.DataFrame([
        {"Stat": SHORT_LABELS.get(m, m), "Player": label, "Percentile": r[f"pct_{m}"]}
        for m in metrics for label, (_, _, r) in zip(labels, chosen)
    ]).dropna(subset=["Percentile"])

    base = alt.Chart(long).encode(
        y=alt.Y("Stat:N", sort=[SHORT_LABELS.get(m, m) for m in metrics], title=None,
                axis=alt.Axis(labelColor="#e8ecf2", labelFontSize=13, labelLimit=220,
                              ticks=False, domain=False, labelPadding=10)),
        yOffset=alt.YOffset("Player:N", sort=labels),
        x=alt.X("Percentile:Q", scale=alt.Scale(domain=[0, 100]), title=None,
                axis=alt.Axis(values=[0, 25, 50, 75, 100], gridColor="#232b37",
                              labelColor="#93a0b2", domain=False, ticks=False)),
    )
    bars = base.mark_bar(cornerRadiusEnd=3, height=12).encode(
        color=alt.Color("Player:N", sort=labels,
                        scale=alt.Scale(domain=labels, range=PLAYER_COLORS[:len(labels)]),
                        legend=alt.Legend(orient="top", title=None, labelColor="#e8ecf2",
                                          labelLimit=320, labelFontSize=13)),
        tooltip=["Player", "Stat", alt.Tooltip("Percentile:Q", format=".0f")],
    )
    text = base.mark_text(align="left", dx=5, color="#c3ccd8", fontSize=11).encode(
        text=alt.Text("Percentile:Q", format=".0f"))
    per_stat = 16 * len(chosen) + 18
    st.altair_chart((bars + text).properties(height=per_stat * len(metrics))
                    .configure_view(strokeWidth=0), use_container_width=True)

with table_col:
    st.subheader("Per-90 values",
                 help="Finishing is goals per shot. Fouls, cards and offsides are raw rates, "
                      "so lower is better. Goal difference mostly reflects team strength.")

    raw_rows = []
    for _, _, r in chosen:
        prow = profiles[(profiles["player_id"] == r["player_id"])
                        & (profiles["season"] == r["season"])]
        raw_rows.append({m: (prow[m].iloc[0] if not prow.empty and m in prow else None)
                         for m in metrics})

    head = "".join(
        f'<th><span class="p90-dot" style="background:{PLAYER_COLORS[i]}"></span>'
        f'<span class="p90-name">{escape(r["Player"].split()[-1])}</span>'
        f'<span class="p90-season">{r["season"]}</span></th>'
        for i, _, r in chosen
    )
    body = []
    for m in metrics:
        values = [row[m] for row in raw_rows]
        valid = [v for v in values if v is not None and pd.notna(v)]
        best = None
        if valid and m != "+/-90":
            target = min(valid) if not METRICS.get(m, True) else max(valid)
            if values.count(target) == 1:
                best = values.index(target)
        cells = "".join(
            f'<td class="{"best" if j == best else ""}">{fmt(m, v)}</td>'
            for j, v in enumerate(values)
        )
        body.append(f'<tr><th scope="row">{escape(RAW_LABELS.get(m, m))}</th>{cells}</tr>')

    st.markdown(
        f'<div class="p90-wrap"><table class="p90"><thead><tr><th></th>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>',
        unsafe_allow_html=True,
    )
    st.caption("Green = best of the players shown")

footer()