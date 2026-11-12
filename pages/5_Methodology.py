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
    "- **Available statistics:** Minutes, goals, assists, shots, shots on target, crosses, tackles "
    "won, interceptions, fouls committed and drawn, offsides, cards and on-pitch goal difference.\n"
    "- **Not available in open data:** Passing, dribbling, duels, clearances and expected goals (xG).\n"
    "- **Why only FBref:** Richer sources such as Sofascore, FotMob and Transfermarkt were not used as "
    " statistical data sources because I did not have permission to extract and reuse their data."
    "Sofascore was contacted directly and declined to provide data. "
    "These platforms were used only for manual reference checks of individual players.\n"
    "- **Data checks:** Each season's row counts, goal totals and spot-checked player records match "
    "FBref's league pages."
)

st.subheader("2. Roles", anchor="roles")
st.markdown(
    f"FBref only gives broad positions (DF, MF and FW), so each player's scouting role is estimated "
    f"from their statistics using rules {ROLE_RULES_VERSION.split()[0]}."
)
st.markdown(
    "- **Six roles:** " + ", ".join(f"{k} ({v.lower()})" for k, v in ROLE_LABELS.items()) + ".\n"
    "- **Source positions limit the options**. For example, a defender-midfielder can be "
    "classified as a centre-back, full-back or defensive midfielder, but not a winger.\n"
    "- **Several statistics determine each role**. Players are compared with others in "
    "the same source-position group and season.\n"
    "- **Borderline assignments are flagged**. This means the second-highest role "
    "score was close to the highest. These cases are shown on the player's profile rather than hidden.\n"
    f"- **{n_overrides} documented manual corrections** address clear classification errors, each "
    "supported by evidence, mostly from a player's positions during that season."
)
st.info("**Validation:** The forward classifier was checked against independently sourced "
        "main positions for 28 regular forwards. The model agreed in **24 of 28 cases (86%)**. "
        "Three of the four disagreements were already flagged as borderline.", icon=":material/fact_check:")

st.subheader("3. Percentiles", anchor="percentiles")
pools = (full.groupby("role")["player_id"].size().rename("Players in pool")
         .rename(index=ROLE_LABELS).sort_values(ascending=False).rename_axis("Role"))
p_left, p_right = st.columns([3, 2], gap="large")
with p_left:
    st.markdown(
        f"Players are ranked only against others in the same scouting role. The two full "
        "seasons are pooled to provide a larger comparison group.\n"
        f"\n**{CURRENT_SEASON}** players are ranked against that same full-season reference group. Their "
        "percentiles therefore show how their current performance compares with players"
        "across the two completed seasons.\n"
        "- Lower is better for fouls, cards and offsides, so those percentiles are reversed.\n"
        "- **Shot accuracy and finishing statistics** require at least 10 shots; otherwise, they are left blank.\n"
        "- **Colours:** 0-33 = below average; 34-66 = average; 67-100 = strong."
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
     "Similarity compares percentile profiles between players in the same role, "
     "producing a score from 0–100. Use it to rank potential matches, not as a "
     "percentage of likeness.\n"
    "- **Goal difference is excluded** because it reflects team performance more than "
    "individual ability. Including it caused players from stronger clubs to be matched "
    "disproportionately with one another.\n"
    "- **Discipline statistics receive a quarter of the usual weight** so two centre-backs "
    "aren't matched mainly because they are rarely booked.\n"
    "- **Each similar player appears once** using their closest-matching season."
)

st.subheader("5. Fit score", anchor="fit-score")
st.markdown(
    "The fit score is a weighted average of a player's percentiles for the statistics "
    "selected by the scout. It ranges from 0–100.\n"
    "- Discipline statistics default to a quarter of the usual weight because few fouls "
    "can indicate low involvement rather than goods defending.\n"
    "- Each player is scored using their most recent qualifying full season.\n"
    "- The explanation also highlights consistency across seasons, current form and "
    "any need to check the player's current status.\n"
    "\n**The fit score is not an overall player rating or a probability of success**. It "
    "measures how closely a player's statistical profile matches the scout's selected priorities."

)

st.subheader("Tested and rejected: Possession adjustment")
t_left, t_right = st.columns([3, 2], gap="large")
with t_left:
    st.markdown(
        "A common adjustment scales tackles and interceptions to a 50% possession baseline, "
        "based on the idea that players at dominant teams have fewer "
        "opportunities to defend.\n"
        "\nIn this league, team possession had little relationship with defensive output to "
        "begin with. Applying the adjustment therefore over-corrected every role.\n"
        "\nDefensive midfielders at dominant clubs actually recorded *more* defensive actions, "
        "which is consistent with high pressing. The app therefore uses unadjusted statistics."
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
    "- **Open data only.** Creative, build-up and aerial strengths are not captured. Centre-back "
    "profiles are particularly limited.\n"
    "- **Fouls drawn are used as a proxy for ball-carrying**. This can pull target "
    "strikers towards the wide or attacking midfield role.\n"
    "- **Set-piece crosses are not separated from open-play crosses**. This can make "
    "central set-piece takers look like wide players.\n"
    "- **Roles are estimated from statistics,** not from watching matches.\n"
    "- **Ages are approximate**, calculated using the current year minus birth year.\n"
    "- **Goalkeepers are not included.** FBref's open data has no shot-quality measure (post-shot xG), "
    "and a regular keeper faces only about 30-40 shots on target a season, too few to rank keepers fairly. "
    "Goals against and clean sheets mostly reflect the defence.\n\n"
    "The numbers are a starting point for scouting, not a replacement for watching players."
)

footer()