# African Football Scouting Tool

A Streamlit app that helps scouts and recruitment analysts find, compare and shortlist players in South Africa's **Betway Premiership**, using open data only.

**Live app:** 

![Shortlist page](data/images/shortlist.png)

---

## Research question

**How can player performance data help identify promising recruitment targets in African football?**

African leagues get little public analytics coverage, and most advanced data sits behind commercial providers. This project asks how far open data can take a recruitment workflow, and is explicit about where it runs out.

## What the app does

| Page | Purpose |
|---|---|
| **Shortlist** | Pick a role, weight the stats that matter, filter by age, minutes and club, and get a ranked list with a plain-language reason for every player. |
| **Player profile** | Role percentiles, role history, current-season form and the five most statistically similar players. |
| **Compare** | Two or three players side by side, as percentiles and per-90 values. |

Example explanation from the Shortlist page:

> *Yanela Mbuthuma (Orlando Pirates, 2025-26, 1238 min): Top 4% for shots per 90; top 7% for shots on target per 90; top 13% for fouls drawn per 90 among strikers; improving (40 the previous season); aged 24.*

---

## Data

- **Source:** [FBref](https://fbref.com) player and squad tables, exported manually with FBref's own CSV export tools. Data provided to FBref by Data Sports Group.
- **Seasons:**
  - **2024-25 and 2025-26**: full seasons, used for all rankings (900+ minutes).
  - **2026-27**: shown as current form only (450+ minutes) and flagged as a small sample.
- **Volume:** 1,532 player-season rows before filtering; 573 after minimum minutes; 408 outfield player-seasons in the two profiling seasons.
- **Checks:** every season's row counts, goal totals and spot-checked players match FBref's league pages.

**Available stats:** minutes, goals, assists, shots, shots on target, crosses, tackles won, interceptions, fouls committed and drawn, offsides, cards and on-pitch goal difference.

**Not available in open data:** passing, dribbling, duels, clearances and expected goals (xG).

### Why only FBref?

Richer sources (Sofascore, FotMob, Transfermarkt) prohibit automated extraction or reuse without permission. Sofascore was asked directly and declined to provide data. These sites were used only for **manual reference checks** of individual players, never as data sources. Raw FBref exports are not included in this repository.

---

## Method

```
one_season.py  →  roles.py  →  percentiles.py  →  similarity.py  →  shortlist.py  →  Streamlit app
```

### 1. Building the dataset (`one_season.py`)
Merges four FBref player tables per season on FBref's player ID and club, computes per-90 stats, and checks each season against FBref's totals. Players at two clubs in a season are combined before the minutes filter.

### 2. Role classification (`roles.py`), rules v1.0
FBref only gives broad positions (GK/DF/MF/FW), so scouting roles are inferred: **CB, FB, DM, CM, W/AM (wide or attacking midfielder) and ST**.

- **The source position sets the allowed roles.** A `DFMF` can be CB, FB or DM, but never a winger.
- **Several stats decide together.** Each role has a weighted score built from multiple stats, standardised within each season and position group (defenders against defenders, and so on).
- **The source position is the starting point.** Roles matching a player's first-listed position get a small head start; CM is the default for midfielders unless their stats clearly point to DM or W/AM.
- **Every assignment has a confidence margin.** Near-ties are flagged and shown as "borderline" in the app.
- **36 documented manual overrides** correct clear errors, each with its evidence (mostly season-level position appearances).

**Validation:** forward roles were checked against independently sourced main positions for 28 regular forwards. The classifier alone agreed in **24 of 28 (86%)**. Three of the four disagreements were already flagged as low confidence, so the confidence score works as intended. One disagreement (Ndlondlo, 2025-26) is supported by his season-level appearances at centre-forward, despite his career main position being attacking midfield. Every club in both full seasons also passes a squad-composition check.

### 3. Possession adjustment: tested and rejected
A standard adjustment (scaling tackles and interceptions to 50% opponent possession) was tested. In this league, team possession had little relationship with defensive output:

| Role | Correlation before | After adjustment |
|---|---|---|
| CB | -0.26 | +0.22 |
| FB | -0.18 | +0.40 |
| DM | **+0.21** | +0.65 |
| CM | 0.03 | +0.35 |

The adjustment over-corrected every role. Defensive midfielders at dominant clubs actually make *more* defensive actions, consistent with high pressing. **v1 therefore uses unadjusted stats.** The test is kept in `possession.py`.

### 4. Percentiles (`percentiles.py`)
Each player is ranked **only against players in the same role**, pooled across both full seasons (pools of 35–94 players). The pool includes the player being ranked, which moves a percentile by at most a few points. Current-season players are ranked against the same full-season pool. For fouls, cards and offsides, lower is better. Shot accuracy and goals per shot are left blank for players with fewer than 10 shots.

The top-ranked players per role match FBref's own 2025-26 league leaders (e.g. tackles won, interceptions, crosses, assists per 90).

### 5. Similar players (`similarity.py`)
Weighted distance between percentile profiles within the same role, shown as a **profile similarity score** (0–100). It ranks matches; it is not a percentage of likeness.

- **On-pitch goal difference is excluded**, because it mostly reflects team strength. Including it clustered players from dominant clubs together.
- **Discipline stats are down-weighted (0.25)**, so two centre-backs aren't matched mainly on rarely being booked.
- A player is never matched with himself, and each similar player appears once (their closest season).

### 6. Shortlists (`shortlist.py`)
The **fit score** is the weighted average of a player's percentiles on the stats the scout prioritises. It is not an overall rating or a probability of success. Discipline stats default to a quarter weight, because few fouls can mean low involvement rather than good defending. Each player is scored on their most recent full season, and the explanation covers:

- their standout stats (leading with the scout's priorities)
- consistency with their other full season
- current form, flagged as a small sample
- whether their last qualifying season was 2024-25 ("check current status")

---

## Findings

- **Thin markets show up quickly.** Outside Sundowns and Orlando Pirates, there are only about three genuine young ball-winning defensive midfielders in the two seasons; after that, candidates no longer fit the profile.
- **Possession doesn't work the way the standard adjustment assumes in this league**, especially for defensive midfielders.
- **Role versatility is common.** Several players change role between seasons (e.g. wide to central forward), which the role history makes visible.

## Limitations

- **No passing, dribbling, duel or xG data.** Creative, build-up and aerial qualities are under-represented. **Centre-back profiles are the thinnest** (interceptions, tackles, fouls and cards only).
- **Fouls drawn stands in for ball-carrying**, which can pull target strikers towards the wide/attacking role.
- **Set-piece crosses aren't separated** from open-play crosses, which can make central set-piece takers look like wide players.
- **Roles are inferred**, not tagged from video. Borderline cases are flagged rather than hidden.
- **Ages are approximate** (current year minus birth year), and some players have no listed birth date.
- **Goalkeepers are not yet included.**

## Future work

- Goalkeeper profiles from FBref's goalkeeping tables
- Other African leagues, using within-league percentiles (raw stats aren't comparable across leagues of different strength)
- A partial possession adjustment calibrated for centre-backs only
- Scout-weighted similarity
- Contract and market-value data, if a licensed or permitted source becomes available

---

## Project structure

```
african_scouting_tool/
├── Home.py                     # app home page
├── pages/
│   ├── 1_Shortlist.py
│   ├── 2_Player_profile.py
│   └── 3_Compare.py
├── src/
│   ├── config.py               # seasons, minute thresholds, rules version
│   ├── one_season.py           # build and verify each season
│   ├── roles.py                # role classification (v1.0)
│   ├── review_roles.py         # flags borderline roles for review
│   ├── validate_forwards.py    # forward role validation
│   ├── possession.py           # possession adjustment test (not used in v1)
│   ├── percentiles.py
│   ├── similarity.py
│   ├── shortlist.py
│   └── app_data.py             # shared app loading and labels
├── data/
│   ├── manual/                 # role overrides and review log
│   └── processed/              # pipeline outputs
└── requirements.txt
```

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run Home.py
```

To rebuild the data, export the FBref player tables into `data/raw/fbref/` (see the docstring in `src/one_season.py`), then run the pipeline scripts in order.

---

Data: [FBref.com](https://fbref.com). This is a non-commercial portfolio project.