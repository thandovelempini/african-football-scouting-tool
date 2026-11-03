import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app_data import ROLE_LABELS, cards, footer, hero, load_percentiles, style  # noqa: E402
from config import CURRENT_SEASON, MIN_MINUTES, PROFILE_SEASONS, ROLE_RULES_VERSION  # noqa: E402

st.set_page_config(page_title="Methodology", page_icon=":material/menu_book:", layout="wide")
style()

ROOT = Path(__file__).resolve().parent.parent
OVERRIDES = ROOT / "data" / "manual" / "role_overrides.csv"

pct = load_percentiles()
full = pct[pct["season"].isin(PROFILE_SEASONS)]
n_overrides = len(pd.read_csv(OVERRIDES)) if OVERRIDES.exists() else 0
first, last = min(PROFILE_SEASONS), max(PROFILE_SEASONS)

hero("Methodology",
     "How the roles, percentiles and scores are built, and where open data runs out",
     kicker=f"Betway Premiership · {first} to {CURRENT_SEASON}")

st.markdown(
    '<div class="steps">'
    '<a class="step" href="#data"><span>1</span>FBref data</a>'
    '<a class="step" href="#roles"><span>2</span>Roles</a>'
    '<a class="step" href="#percentiles"><span>3</span>Percentiles</a>'
    '<a class="step" href="#similarity"><span>4</span>Similarity</a>'
    '<a class="step" href="#fit-score"><span>5</span>Fit score</a>',
    unsafe_allow_html=True,
)

st.subheader("1. Data", anchor="data")
cards([
    ("Source", "FBref", "player and squad tables, exported by hand"),
    ("Full seasons", "2", f"{first} and {last} · {MIN_MINUTES[first]}+ minutes"),
    ("Current form", CURRENT_SEASON, f"{MIN_MINUTES[CURRENT_SEASON]}+ minutes, small sample"),
    ("Outfield player-seasons", f"{len(full):,}", "in the two full seasons"),
])
st.markdown(
    "- **Stats available:** Minutes, goals, assists, shots, shots on target, crosses, tackles "
    "won, interceptions, fouls committed and drawn, offsides, cards and on-pitch goal difference.\n"
    "- **Not in open data:** Passing, dribbling, duels, clearances and expected goals (xG).\n"
    "- **Why only FBref:** Richer sites such as Sofascore, FotMob and Transfermarkt don't allow "
    "their data to be reused. They were used only to check individual players by hand.\n"
    "- **Checks:** Each season's row counts, goal totals and spot-checked players match "
    "FBref's league pages."
)

st.subheader("2. Roles", anchor="roles")
st.markdown(
    f"FBref only gives broad positions (DF, MF, FW), so each player's scouting role is estimated "
    f"from their stats (rules {ROLE_RULES_VERSION.split()[0]}):"
)
st.markdown(
    "- **Six roles:** " + ", ".join(f"{k} ({v.lower()})" for k, v in ROLE_LABELS.items()) + ".\n"
    "- **The position sets the options.** A defender-midfielder can be a centre-back, full-back "
    "or defensive midfielder, but never a winger.\n"
    "- **Several stats decide together,** compared only with players in the same position group "
    "and season.\n"
    "- **Borderline** means the second-best role was close. It's shown on the player's card "
    "rather than hidden.\n"
    f"- **{n_overrides} manual corrections,** each with its evidence, fix clear errors "
    "(mostly from a player's match positions that season)."
)
st.info("**Check:** For 28 regular forwards, the model's role matched independently sourced "
        "positions in **24 of 28 (86%)**. Three of the four misses were already marked "
        "borderline.", icon=":material/fact_check:")

st.subheader("3. Percentiles", anchor="percentiles")
pools = (full.groupby("role")["player_id"].size().rename("Players in pool")
         .rename(index=ROLE_LABELS).sort_values(ascending=False).rename_axis("Role"))
p_left, p_right = st.columns([3, 2], gap="large")
with p_left:
    st.markdown(
        f"- **Ranked only within the same role,** pooling {first} and {last} so every role has "
        "a reasonable comparison group.\n"
        f"- **{CURRENT_SEASON} players are ranked against that same full-season pool,** so their "
        "percentiles mean \"compared with a normal season\".\n"
        "- **Lower is better** for fouls, cards and offsides, so those percentiles are flipped.\n"
        "- **Shot accuracy and finishing** need at least 10 shots, otherwise they're left blank.\n"
        "- **Colours:** 0-33 below average, 34-66 average, 67-100 strong."
    )
with p_right:
        st.dataframe(
        pools.reset_index(), hide_index=True, use_container_width=True,
        height=35 * (len(pools) + 1) + 3,
        column_config={
            "Role": st.column_config.TextColumn("Role", width=200),
            "Players in pool": st.column_config.NumberColumn("Players", width=0,
                                                             help="Player-seasons across both full seasons"),
        },
    )

st.subheader("4. Similar players", anchor="similarity")
st.markdown(
    "- **Compares percentile profiles** between players in the same role, scored 0-100. "
    "Use it to rank matches, not as a percentage of likeness.\n"
    "- **Goal difference is left out,** because it says more about the team than the player."
    " With it included, players from strong clubs were mostly matched with each other.\n"
    "- **Discipline stats count a quarter,** so two centre-backs aren't matched mainly on "
    "rarely being booked.\n"
    "- **Each similar player appears once,** at their closest season."
)

st.subheader("5. Fit score", anchor="fit-score")
st.markdown(
    "- **A weighted average of a player's percentiles** on the stats the scout prioritises, "
    "0-100.\n"
    "- **Discipline stats default to a quarter weight,** because few fouls can mean low "
    "involvement rather than good defending.\n"
    "- **Scored on the player's most recent full season,** with consistency, current form "
    "and any \"check current status\" warning added to the explanation.\n"
    "- **It is not an overall rating** or a probability of success."
)

st.subheader("Tested and rejected: Possession adjustment")
t_left, t_right = st.columns([3, 2], gap="large")
with t_left:
    st.markdown(
        "A common adjustment scales tackles and interceptions to 50% possession, on the idea "
        "that players at dominant teams get fewer chances to defend. In this league, team "
        "possession had little link to defensive output to begin with, so the adjustment "
        "**over-corrected every role**.\n\n"
        "Defensive midfielders at dominant clubs actually made *more* defensive actions, "
        "which fits high pressing. The app therefore uses unadjusted stats."
    )
with t_right:
    st.dataframe(
        pd.DataFrame({
            "Role": ["Centre-back", "Full-back", "Defensive midfielder", "Central midfielder"],
            "Before": [-0.26, -0.18, 0.21, 0.03],
            "After adjustment": [0.22, 0.40, 0.65, 0.35],
        }),
        hide_index=True, use_container_width=True,
        column_config={
            "Before": st.column_config.NumberColumn(format="%+.2f",
                                                    help="Correlation with team possession"),
            "After adjustment": st.column_config.NumberColumn(format="%+.2f"),
        },
    )
    st.caption("Correlation between team possession and defensive actions per 90. "
               "Before adjusting, most roles were close to 0, meaning possession barely "
               "mattered. The adjustment pushed every role further from 0.")

st.subheader("Limitations")
st.markdown(
    "- **Open data only.** Creative, build-up and aerial strengths don't show up. Centre-back "
    "profiles are the thinnest.\n"
    "- **Fouls drawn stands in for ball-carrying,** which can pull target strikers towards the "
    "wide or attacking role.\n"
    "- **Set-piece crosses aren't separated** from open play, which can make central set-piece "
    "takers look like wide players.\n"
    "- **Roles are estimated from stats,** not from watching matches.\n"
    "- **Ages are approximate** (current year minus birth year).\n"
    "- **No goalkeepers yet.**\n\n"
    "The numbers are a starting point for scouting, not a replacement for watching players."
)

footer()