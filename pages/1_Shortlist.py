import sys
from html import escape
from pathlib import Path
from app_data import crest 

import pandas as pd
import streamlit as st
import re

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app_data import (FIT_SCORE_HELP, FORM_HELP, ROLE_LABELS, footer, hero,  # noqa: E402
                      load_percentiles, pill, style)
from config import PROFILE_SEASONS  # noqa: E402
from shortlist import DISCIPLINE, METRIC_LABELS, build_shortlist, default_priorities  # noqa: E402

st.set_page_config(page_title="Shortlist", page_icon=":material/format_list_numbered:", layout="wide")
style()

pct = load_percentiles()
latest_season = max(PROFILE_SEASONS)


def nice(metric: str) -> str:
    label = METRIC_LABELS.get(metric, metric)
    return label[0].upper() + label[1:]


def pct_col(df: pd.DataFrame, metric: str) -> str | None:
    col = f"pct_{metric}"
    return col if col in df.columns else None


def initials(name: str) -> str:
    return "".join(w[0] for w in name.split()[:2]).upper()


def why_html(text: str) -> str:
    items = []
    for part in text.split(";"):
        part = (part.strip().rstrip(".")
        .replace("the previous season", "last season")
        .replace("the other year", "in the other season"))
        if not part:
            continue
        if part.lower().startswith(("aged ", "current form score")):
            continue
        part = escape(part[0].upper() + part[1:])
        part = re.sub(r"^(Top \d+%)", r"<strong>\1</strong>", part)
        items.append(f"<li>{part}</li>")
    return f'<ul class="why">{"".join(items)}</ul>'

def age_text(a) -> str:
    return "Age unknown" if pd.isna(a) else f"Age {int(a)}"


with st.sidebar:
    st.subheader("Brief")
    role = st.selectbox("Role", list(ROLE_LABELS), format_func=lambda r: ROLE_LABELS[r])
    ages = pct["Age"].dropna()
    max_age = st.slider("Maximum age", int(ages.min()), int(ages.max()), int(ages.max()))
    min_minutes = st.slider("Minimum minutes", 900, 3000, 900, step=100)

    st.divider()
    st.caption("Priorities (weight) → 0 = ignore, 1 = normal, 3 = most important")
    priorities = {}
    for metric, weight in default_priorities(role).items():
        priorities[metric] = st.slider(nice(metric), 0.0, 3.0, float(weight), 0.25,
                                       key=f"{role}_{metric}")
    st.caption("Discipline stats default low: Few fouls can mean low involvement "
               "rather than good defending")

    with st.expander("More filters"):
        include_unknown_age = st.checkbox("Include players with unknown age", value=True)
        exclude = st.multiselect("Exclude clubs", sorted(pct["Squad"].dropna().unique()))
        recent_only = st.checkbox(f"Only players with a {latest_season} full season", value=False)
        top_n = st.slider("Players to show", 5, 30, 15)

priorities = {m: w for m, w in priorities.items() if w > 0}
if not priorities:
    hero(f"{ROLE_LABELS[role]}s", "Give at least one stat a weight above 0",
         kicker="Shortlist")
    st.stop()

full = build_shortlist(pct, role, priorities=priorities, exclude_clubs=exclude or None,
                       min_minutes=min_minutes, top_n=10_000)
keep = full["Age"] <= max_age
if include_unknown_age:
    keep |= full["Age"].isna()
result = full[keep]
if recent_only:
    result = result[result["season"] == latest_season]
total = len(result)
result = result.head(top_n).reset_index(drop=True)

hero(f"{ROLE_LABELS[role]}s",
     f"{total} players match your brief",
     kicker=f"Shortlist · full seasons {min(PROFILE_SEASONS)} to {latest_season}")

if result.empty:
    st.info("No players match these filters")
    footer()
    st.stop()

result.insert(0, "Rank", range(1, len(result) + 1))
result["recent"] = result["season"] == latest_season

picks = []
for _, r in result.head(3).iterrows():
    first = r["Rank"] == 1
    status = pill("Recent", "ok") if r["recent"] else pill(f"{r['season']} only: Check status", "Warn")
    form = pill(f"Form {r['form_score']:.0f}", "muted") if pd.notna(r["form_score"]) else ""
    picks.append(
        f'<div class="pick{" first" if first else ""}">'
        f'<div class="top"><span class="rank">#{r["Rank"]}</span>'
        f'<span class="avatar">{escape(initials(r["Player"]))}</span></div>'
        f'<div class="name">{escape(r["Player"])}</div>'
        f'<div class="meta">{crest(r["Squad"])}{escape(r["Squad"])} · {age_text(r["Age"])} · '
        f'{int(r["Min"]):,} min</div>'
        f'<div class="score">{r["score"]:.0f}<span> fit</span></div>'
        f'<div style="margin-top:10px">{status}{form}</div>'
        f'{why_html(r["why"])}</div>'    
        )
st.markdown(f'<div class="picks">{"".join(picks)}</div>', unsafe_allow_html=True)

st.write("")
with st.container(border=True):
    st.markdown("**Full list**")
    st.caption("Fit score (0-100) shows how well a player matches your priorities, "
           "compared with others in the same role (it is not an overall rating)")

    ranked = sorted(priorities, key=lambda m: (m in DISCIPLINE, -priorities[m]))
    bar_metrics = [(m, f"pct_{m}") for m in ranked[:3]]

    table = result.copy()
    missing = [c for _, c in bar_metrics if c not in table.columns and c in pct.columns]
    if missing:
        keys = ["Player", "Squad", "season"]
        extra = pct[keys + missing].drop_duplicates(subset=keys)
        table = table.merge(extra, on=keys, how="left")
    bar_metrics = [(m, c) for m, c in bar_metrics if c in table.columns]

    table["Status"] = table["season"].map(lambda s: "Recent" if s == latest_season else s)
    table["form_score"] = table["form_score"].map(lambda v: "—" if pd.isna(v) else f"{v:.0f}")

    column_config = {
        "Rank": st.column_config.NumberColumn("#", width=45),
        "Player": st.column_config.TextColumn("Player", width=170),
        "Squad": st.column_config.TextColumn("Club", width=140),
        "Age": st.column_config.NumberColumn("Age", format="%d", width=50,
                                             help="Approximate current age. Blank = not listed"),
        "Min": st.column_config.NumberColumn("Min", format="localized", width=70),
        "Status": st.column_config.TextColumn("Status", width=100),
        "form_score": st.column_config.TextColumn("Form", width=60, help=FORM_HELP),
        "score": st.column_config.NumberColumn("Fit", format="%.0f", width=50,
                                               help=FIT_SCORE_HELP),
    }
    for m, c in bar_metrics:
        column_config[c] = st.column_config.ProgressColumn(
            nice(m).replace(" per 90", ""), min_value=0, max_value=100, format="%.0f",
            width=110, help=f"{nice(m)}: percentile among {ROLE_LABELS[role].lower()}s")


    columns = (["Rank", "Player", "Squad", "Age", "Min"] + [c for _, c in bar_metrics]
               + ["Status", "form_score", "score"])
    st.dataframe(table[columns], hide_index=True, use_container_width=True,
                 height=36 * (len(table) + 1) + 3, column_config=column_config)

with st.expander("Why each player is on the list"):
    rows = []
    for _, r in result.iterrows():
        rows.append(
            f'<div class="why-row">'
            f'<div class="why-head"><span class="why-rank">{r["Rank"]}</span>'
            f'<span class="why-name">{escape(r["Player"])}</span>'
            f'<span class="why-meta">{escape(r["Squad"])} · {r["season"]} · '
            f'{int(r["Min"]):,} min</span></div>'
            f'{why_html(r["why"])}</div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)

with st.sidebar:
    st.download_button("Download CSV", result.drop(columns="recent").to_csv(index=False),
                       file_name=f"shortlist_{role.replace('/', '-')}.csv", mime="text/csv",
                       icon=":material/download:", use_container_width=True)

footer()